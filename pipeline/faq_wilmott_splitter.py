"""FAQ Quant Interview (Wilmott) 专用解析器

书籍结构：
  [页眉噪声] + 问题标题（以 ? 结尾）
  Short answer
  [简洁答案段落]
  Example（可选）
  [例子]
  Long answer
  [详细答案]
  References and Further Reading
  [参考文献]

每道题跨越若干页，标题可能因分页被页眉打断。
"""
import json
import re
from pathlib import Path
from typing import Any

from pipeline.logger import logger

# 页眉噪声模式（出现在标题行中需要剥离）
_PAGE_NOISE_RE = re.compile(
    r"(?:\d+\s*)?(?:Frequently Asked Questions in Quantitative Finance|Chapter \d+[:\s]+FAQs?\s*\d*)\s*",
    re.IGNORECASE,
)

# 题目起始标记：任意文本行末尾有 ? 后紧跟 Short answer
_QUESTION_START_RE = re.compile(
    r"((?:[^\n]+\n){0,3}[^\n]+\?)\s*\nShort answer\b",
    re.MULTILINE,
)

# 答案内部分节
_SHORT_ANSWER_RE = re.compile(r"\nShort answer\s*\n")
_EXAMPLE_RE      = re.compile(r"\nExample\s*\n")
_LONG_ANSWER_RE  = re.compile(r"\nLong answer\s*\n")
_REFERENCES_RE   = re.compile(r"\nReferences and Further Reading\b")


def _clean_title(raw: str) -> str:
    """去除标题中的页眉噪声，提取纯问题文本。"""
    cleaned = _PAGE_NOISE_RE.sub(" ", raw)
    # 折叠多空格、去掉行首行尾空白
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    # 折叠跨行（标题因分页被换行打断）
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned)
    return cleaned


def _extract_short_answer(block: str) -> str:
    """从题目块中提取 Short answer 段落（到 Example 或 Long answer 为止）。"""
    m = _SHORT_ANSWER_RE.search(block)
    if not m:
        return ""
    start = m.end()
    # 终止在下一个段落标志
    for stopper in (_EXAMPLE_RE, _LONG_ANSWER_RE, _REFERENCES_RE):
        stop_m = stopper.search(block, start)
        if stop_m:
            return block[start:stop_m.start()].strip()
    return block[start:].strip()


def _extract_full_answer(block: str) -> str:
    """提取 Short answer + Example + Long answer 全部，止于 References。"""
    m = _SHORT_ANSWER_RE.search(block)
    if not m:
        return ""
    start = m.end()
    ref_m = _REFERENCES_RE.search(block, start)
    end = ref_m.start() if ref_m else len(block)
    return block[start:end].strip()


def split_faq_wilmott(
    meta_path: str,
    out_path: str = "./output/questions.json",
    answer_mode: str = "short",   # "short" | "full"
) -> list[dict[str, Any]]:
    """
    解析 FAQ Quant Interview 格式的 render_meta.json / ocr_meta.json。

    Args:
        meta_path:   render_meta.json 或 ocr_meta.json 路径
        out_path:    输出 questions.json 路径
        answer_mode: "short" 只保留 Short answer；"full" 保留完整答案

    Returns:
        questions list
    """
    meta_file = Path(meta_path)
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    pages = meta.get("pages", [])

    # 拼接全文并记录页偏移
    full_text = ""
    page_offsets: list[tuple[int, int]] = []
    for p in pages:
        start = len(full_text)
        full_text += p.get("text", "") + "\n"
        page_offsets.append((start, p["page"]))

    def _offset_to_page(offset: int) -> int:
        for i in range(len(page_offsets) - 1, -1, -1):
            if offset >= page_offsets[i][0]:
                return page_offsets[i][1]
        return 1

    # 找所有题目起始位置
    starts = [(m.start(), m.group(1)) for m in _QUESTION_START_RE.finditer(full_text)]
    if not starts:
        logger.warning("未找到任何 FAQ 格式题目", extra={"stage": "split"})
        return []

    logger.info(f"检测到 {len(starts)} 道 FAQ 题目", extra={"stage": "split"})

    questions: list[dict[str, Any]] = []
    for i, (pos, raw_title) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(full_text)
        block = full_text[pos:end]

        title = _clean_title(raw_title)
        if not title.endswith("?"):
            # 标题清洗后不含问号，跳过（页眉误匹配）
            continue

        if answer_mode == "short":
            answer = _extract_short_answer(block)
        else:
            answer = _extract_full_answer(block)

        start_page = _offset_to_page(pos)
        end_page   = _offset_to_page(end - 1)

        questions.append({
            "id": f"p{start_page:03d}_q{i+1:03d}",
            "source_pages": list(range(start_page, end_page + 1)),
            "question_marker": f"FAQ Q{i+1}",
            "raw_text": title,
            "answer_text": answer or None,
        })

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(questions, ensure_ascii=False, indent=2))
    logger.info(f"切题完成：{len(questions)} 道题 → {out_file}", extra={"stage": "split"})
    return questions
