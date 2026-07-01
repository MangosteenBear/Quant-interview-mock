"""Heard on the Street (Crack) 专用解析器

书籍结构：
  Pages  23- 68: 题目区  —— "Question N.M: <题干>" (Chapter 1-4 为量化题, Chapter 5 为非量化题)
  Pages  71-242: 答案区  —— "Answer N.M: <答案>"
  Pages 243-274: 参考文献（排除）

格式：Question / Answer 均使用 "X.Y:" 编号，其中 X=章节, Y=题号。
Chapter 5 为 soft interview questions，默认跳过。
"""
import json
import re
from pathlib import Path
from typing import Any

from pipeline.logger import logger

# 题目：Question 1.1: / Question 2.13:
_Q_RE = re.compile(r"Question\s+(\d+)\.(\d+):\s*(.*?)(?=Question\s+\d+\.\d+:|Answer\s+\d+\.\d+:|$)",
                   re.DOTALL)
# 答案：Answer 1.1: ...
_A_RE = re.compile(r"Answer\s+(\d+)\.(\d+):\s*(.*?)(?=Answer\s+\d+\.\d+:|Question\s+\d+\.\d+:|$)",
                   re.DOTALL)

# 参考文献开始标志
_BIB_RE = re.compile(r"^References for Further\b|^Bibliography\b", re.MULTILINE | re.IGNORECASE)

# 已知噪声段落（Horror Stories 等）
_NOISE_SECTION_RE = re.compile(
    r"Interview Horror Stories|Non-Quantitative Questions",
    re.IGNORECASE,
)


def _build_full_text(pages: list[dict], max_page: int) -> tuple[str, list[tuple[int, int]]]:
    """拼接页面文本，记录页偏移，截止 max_page（含）。"""
    full_text = ""
    offsets: list[tuple[int, int]] = []
    for p in pages:
        if p["page"] > max_page:
            break
        start = len(full_text)
        full_text += p.get("text", "") + "\n"
        offsets.append((start, p["page"]))
    return full_text, offsets


def _offset_to_page(offset: int, offsets: list[tuple[int, int]]) -> int:
    for i in range(len(offsets) - 1, -1, -1):
        if offset >= offsets[i][0]:
            return offsets[i][1]
    return 1


def _find_bib_start_page(pages: list[dict]) -> int:
    """返回参考文献起始页（找不到则返回 len(pages)+1）。"""
    for p in pages:
        if _BIB_RE.search(p.get("text", "")) and p["page"] > 200:
            return p["page"]
    return len(pages) + 1


def split_heard_crack(
    meta_path: str,
    out_path: str = "./output/questions.json",
    skip_chapter5: bool = True,
) -> list[dict[str, Any]]:
    """
    解析 Heard on the Street (Crack) 的 ocr_meta.json。

    Args:
        meta_path:      render_meta.json 或 ocr_meta.json 路径
        out_path:       输出 questions.json 路径
        skip_chapter5:  是否跳过 Chapter 5 非量化 soft questions（默认 True）

    Returns:
        questions list
    """
    meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    pages = meta.get("pages", [])

    bib_start = _find_bib_start_page(pages)
    logger.info(f"参考文献起始页: {bib_start}", extra={"stage": "split"})

    # --- 提取题目（pages 1 ~ bib_start-1）---
    q_text, q_offsets = _build_full_text(pages, bib_start - 1)

    raw_questions: dict[str, dict] = {}  # key = "N.M"
    for m in _Q_RE.finditer(q_text):
        chapter, num, body = m.group(1), m.group(2), m.group(3).strip()
        if skip_chapter5 and chapter == "5":
            continue
        key = f"{chapter}.{num}"
        start_page = _offset_to_page(m.start(), q_offsets)
        raw_questions[key] = {
            "key": key,
            "chapter": int(chapter),
            "num": int(num),
            "raw_text": body,
            "start_page": start_page,
        }

    logger.info(f"识别到 {len(raw_questions)} 道题目", extra={"stage": "split"})

    # --- 提取答案（pages 1 ~ bib_start-1）---
    raw_answers: dict[str, str] = {}
    for m in _A_RE.finditer(q_text):
        chapter, num, body = m.group(1), m.group(2), m.group(3).strip()
        if skip_chapter5 and chapter == "5":
            continue
        key = f"{chapter}.{num}"
        raw_answers[key] = body

    logger.info(f"识别到 {len(raw_answers)} 条答案", extra={"stage": "split"})

    # --- 组装 ---
    questions: list[dict[str, Any]] = []
    for key, q in sorted(raw_questions.items(), key=lambda x: (x[1]["chapter"], x[1]["num"])):
        answer = raw_answers.get(key)
        q_id = f"p{q['start_page']:03d}_c{q['chapter']}_q{q['num']:03d}"
        questions.append({
            "id": q_id,
            "source_pages": [q["start_page"]],
            "question_marker": f"Question {key}",
            "raw_text": q["raw_text"],
            "answer_text": answer or None,
        })

    matched = sum(1 for q in questions if q["answer_text"])
    logger.info(f"答案匹配: {matched}/{len(questions)}", extra={"stage": "split"})

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(questions, ensure_ascii=False, indent=2))
    logger.info(f"切题完成: {len(questions)} 道题 → {out_file}", extra={"stage": "split"})
    return questions
