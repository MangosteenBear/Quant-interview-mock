"""答案关联（A7）

将 split 产出的 questions.json 与答案块关联，填充每题的 answer_text 字段。

设计：
  量化书籍答案常见两种布局：
  1. 题目内嵌答案：答案紧跟题干（"答：..." / "解：..."），split 已截断题干，
     答案存于同段落后续文本 —— 这种情况由 split 时已记录的截断位置重新提取。
  2. 集中答案区：答案在书末或章末，按题号索引 —— 这里处理这种情况。

输入：
  questions.json（split 产出）+ render_meta.json 或 ocr_meta.json（含原始文本）

输出：
  questions_linked.json — 在每道题上增加 answer_text 字段
"""
import json
import re
from pathlib import Path
from typing import Any

from pipeline.logger import logger

# 答案区块起始标记
_ANSWER_SECTION_RE = re.compile(
    r"^(?:答案|解答|解析|参考答案|Answer|Solution)[s]?\s*[:：]?\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# 内嵌答案标记（题干内部）：答：/ 解：/ Answer: / Solution:
_INLINE_ANSWER_RE = re.compile(
    r"(?:^|\n)\s*(?:答案?|解答?|解析|Answer|Solution)\s*[:：]\s*",
    re.MULTILINE | re.IGNORECASE,
)

# 题号匹配（用于集中答案区解析）—— 与 question_splitter 保持一致
_ANS_MARKER_RE = re.compile(
    r"^(?:(?:第\s*)?(\d+)\s*题|例\s*(\d+)|(\d+)\s*[\.、．]|Q\s*(\d+)\s*[\.:]|\[(\d+)\])",
    re.MULTILINE,
)


def _extract_number(marker: str) -> int | None:
    """从题号原文提取数字，如 '第3题' → 3，'例4' → 4，'2.' → 2，'Question 7:' → 7。"""
    m = re.search(r"\d+", marker)
    return int(m.group()) if m else None


_SCATTERED_ANS_RE = re.compile(
    r"^Answer\s+(\d+)\s*:",
    re.MULTILINE,
)


def _parse_answer_pool(text: str) -> dict[int, str]:
    """
    解析集中答案区，返回 {题号: 答案文本} 映射。
    支持两种格式：
    1. 书末/章末单一答案区（"Answers" 标题后按题号切分）
    2. 散布全书的 "Answer N:" 条目（如 QuantitativePrimer）
    """
    # 策略 1：散布式 Answer N:（优先，检测到则直接用）
    scattered = list(_SCATTERED_ANS_RE.finditer(text))
    if scattered:
        pool: dict[int, str] = {}
        for i, m in enumerate(scattered):
            num = int(m.group(1))
            start = m.end()
            end = scattered[i + 1].start() if i + 1 < len(scattered) else len(text)
            # 截断到下一个题目起始（避免把后续题干混入答案）
            pool[num] = text[start:end].strip()
        return pool

    # 策略 2：集中答案区块（原有逻辑）
    section_m = _ANSWER_SECTION_RE.search(text)
    if not section_m:
        return {}

    answer_text = text[section_m.end():]
    hits = list(_ANS_MARKER_RE.finditer(answer_text))
    if not hits:
        return {}

    pool = {}
    for i, m in enumerate(hits):
        num = next((int(g) for g in m.groups() if g is not None), None)
        if num is None:
            continue
        start = m.end()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(answer_text)
        pool[num] = answer_text[start:end].strip()

    return pool


def _extract_inline_answer(raw_text: str) -> tuple[str, str]:
    """
    从题干文本中分离内嵌答案。
    返回 (question_body, answer_text)；若无内嵌答案则 answer_text 为空。
    """
    m = _INLINE_ANSWER_RE.search(raw_text)
    if not m:
        return raw_text, ""
    return raw_text[: m.start()].strip(), raw_text[m.end():].strip()


def link_answers(
    questions_path: str,
    meta_path: str,
    out_path: str = "./output/questions_linked.json",
) -> list[dict[str, Any]]:
    """
    关联答案，产出 questions_linked.json。

    策略（按优先级）：
    1. 先从题干提取内嵌答案（答：/ 解：）
    2. 再从集中答案区按题号匹配
    3. 均未命中则 answer_text 为 null
    """
    questions: list[dict] = json.loads(Path(questions_path).read_text(encoding="utf-8"))
    meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))

    # 拼接全文供答案池解析
    full_text = "\n".join(p.get("text", "") for p in meta.get("pages", []))
    answer_pool = _parse_answer_pool(full_text)
    logger.info(
        f"集中答案池：{len(answer_pool)} 条",
        extra={"stage": "link"},
    )

    linked: list[dict[str, Any]] = []
    inline_count = 0
    pool_count = 0

    for q in questions:
        raw = q.get("raw_text", "")
        marker = q.get("question_marker", "")
        num = _extract_number(marker)

        # 策略 1：内嵌答案
        body, ans = _extract_inline_answer(raw)
        if ans:
            inline_count += 1
        elif num is not None and num in answer_pool:
            # 策略 2：集中答案池
            body = raw
            ans = answer_pool[num]
            pool_count += 1
        else:
            body = raw
            ans = ""

        linked.append({**q, "raw_text": body, "answer_text": ans or None})

    logger.info(
        f"答案关联完成：内嵌={inline_count}，集中池={pool_count}，"
        f"未命中={len(linked) - inline_count - pool_count}",
        extra={"stage": "link"},
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(linked, ensure_ascii=False, indent=2))
    return linked
