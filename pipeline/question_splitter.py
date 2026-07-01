"""题目边界识别（A6）

输入：OCR 结果目录（含 ocr_meta.json）或 render_meta.json（文字版 PDF 直通）
输出：questions.json — List[Question]

Question 结构：
{
  "id": "p003_q002",          // 页码_题序（临时 id，ingest 时替换）
  "source_pages": [3, 4],     // 跨页题目的所有页码
  "raw_text": "...",          // 原始拼接文本
  "question_marker": "3.",    // 识别到的题号原文
}
"""
import json
import re
from pathlib import Path
from typing import Any

from pipeline.logger import logger

# 量化书籍常见题号模式（按优先级排列）
_QUESTION_PATTERNS = [
    re.compile(r"^(?:第\s*)?(\d+)\s*题", re.MULTILINE),     # 第1题 / 第 1 题
    re.compile(r"^例\s*(\d+)", re.MULTILINE),               # 例1 / 例 1
    re.compile(r"^([1-9]\d*)\s*(?:[、．]|\.(?!\d))\s*\S", re.MULTILINE),  # 1. / 1、（排除小数 1.23）
    re.compile(r"^Q\s*(\d+)\s*[\.:]", re.MULTILINE),        # Q1. / Q1:
    re.compile(r"^Question\s+(\d+)\s*:", re.MULTILINE),      # Question 6:
    re.compile(r"^\[(\d+)\]", re.MULTILINE),                 # [1]
]

# 答案/解析起始标记（遇到则终止题目收集）
_ANSWER_PATTERNS = [
    re.compile(r"^(?:答案|解答|解析|Answer|Solution)\s*[:：]?", re.MULTILINE),
    re.compile(r"^Answer\s+\d+\s*:", re.MULTILINE),           # Answer 6: (带题号)
    re.compile(r"^(?:第.+章\s*)?参考答案", re.MULTILINE),
]

# 目录条目特征：标题行后紧跟页码（正文前无实质内容）
_TOC_ENTRY_RE = re.compile(
    r"^[^\n]{5,120}\n\d{1,4}\s*(?:\n[^\n]{0,40})*$",  # 1-2行标题 + 页码行
)
_MIN_QUESTION_CHARS = 150  # 低于此长度的切片大概率是目录/标题


def _is_toc_entry(text: str) -> bool:
    """判断切片是否为目录条目或章节标题，而非真实题目。"""
    stripped = text.strip()
    if len(stripped) < _MIN_QUESTION_CHARS:
        return True
    # 短于400字符且末尾行为纯数字（页码）→ 目录
    if len(stripped) < 400 and re.search(r"\n\s*\d{1,4}\s*$", stripped):
        return True
    return False


def _detect_question_starts(text: str) -> list[tuple[int, str]]:
    """返回 (char_offset, marker_text) 列表，按位置排序。"""
    hits: list[tuple[int, str]] = []
    for pat in _QUESTION_PATTERNS:
        for m in pat.finditer(text):
            hits.append((m.start(), m.group(0).strip()))
    # 去重（同位置保留第一个匹配），按位置排序
    hits.sort(key=lambda x: x[0])
    deduped: list[tuple[int, str]] = []
    prev_pos = -1
    for pos, marker in hits:
        if pos != prev_pos:
            deduped.append((pos, marker))
            prev_pos = pos
    return deduped


def _is_answer_section(text: str) -> bool:
    return any(p.search(text) for p in _ANSWER_PATTERNS)


def split_questions(
    meta_path: str,
    out_path: str = "./output/questions.json",
) -> list[dict[str, Any]]:
    """
    从 render_meta.json 或 ocr_meta.json 切分题目。

    - 文字版 PDF：直接使用 render_meta.json 中每页的 text 字段
    - 扫描版 PDF：需先跑 ocr，使用 ocr_meta.json 中的 text 字段

    Returns:
        questions list（同写入文件的内容）
    """
    meta_file = Path(meta_path)
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    pages = meta.get("pages", [])
    if not pages:
        logger.warning("元数据中无页面数据", extra={"stage": "split"})
        return []

    # 拼接全文，记录每页的起始偏移
    full_text = ""
    page_offsets: list[tuple[int, int]] = []  # (start_offset, page_number)
    for p in pages:
        start = len(full_text)
        full_text += p.get("text", "") + "\n"
        page_offsets.append((start, p["page"]))

    def _offset_to_page(offset: int) -> int:
        for i in range(len(page_offsets) - 1, -1, -1):
            if offset >= page_offsets[i][0]:
                return page_offsets[i][1]
        return 1

    starts = _detect_question_starts(full_text)
    if not starts:
        logger.warning("未检测到任何题号，请确认 PDF 格式或调整识别模式", extra={"stage": "split"})
        return []

    # 如果文档中 "Question N:" 格式出现足够多（≥5 个不同题号），
    # 认为这是 Question-format 书，丢弃低优先级的 N. 格式避免噪声
    _Q_NUM_RE = re.compile(r"^Question\s+(\d+)\s*:", re.MULTILINE)
    _q_nums = set(_Q_NUM_RE.findall(full_text))
    if len(_q_nums) >= 10:
        _LOW_PRI = re.compile(r"^[1-9]\d*\s*(?:[、．]|\.(?!\d))\s*\S")
        starts = [(pos, m) for pos, m in starts if not _LOW_PRI.match(m)]

    logger.info(f"检测到 {len(starts)} 个题目起始标记", extra={"stage": "split"})

    questions: list[dict[str, Any]] = []
    for i, (pos, marker) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(full_text)
        raw = full_text[pos:end].strip()

        # 遇到答案区块截断
        for ap in _ANSWER_PATTERNS:
            m = ap.search(raw)
            if m and m.start() > 0:
                raw = raw[: m.start()].strip()
                break

        if not raw or _is_toc_entry(raw):
            continue

        start_page = _offset_to_page(pos)
        end_page = _offset_to_page(end - 1)
        source_pages = list(range(start_page, end_page + 1))

        questions.append({
            "id": f"p{start_page:03d}_q{i+1:03d}",
            "source_pages": source_pages,
            "question_marker": marker,
            "raw_text": raw,
        })

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(questions, ensure_ascii=False, indent=2))
    logger.info(f"切题完成：{len(questions)} 道题 → {out_file}", extra={"stage": "split"})

    return questions
