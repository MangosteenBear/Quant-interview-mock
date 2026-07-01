"""书籍结构分析器 — OCR 前调用

在 render 之后、OCR 之前运行，输出 book_profile.json：
  - 推荐的 splitter 格式
  - 题目/答案/参考文献的页码范围
  - 各章节估算
  - 需要过滤的噪声段落类型

目前支持识别的书籍格式：
  heard-crack   Question N.M: / Answer N.M: (Heard on the Street)
  wilmott-faq   问题标题以 ? 结尾 + Short answer 段落 (FAQ Quant Interview)
  auto          通用数字题号 (QuantitativePrimer 等)
  unknown       无法识别，需人工确认
"""
import json
import re
from pathlib import Path
from typing import Any

from pipeline.logger import logger

# ── 格式特征正则 ─────────────────────────────────────────────

# heard-crack: Question 1.1: / Answer 2.13:
_CRACK_Q = re.compile(r"\bQuestion\s+\d+\.\d+\s*:", re.IGNORECASE)
_CRACK_A = re.compile(r"\bAnswer\s+\d+\.\d+\s*:", re.IGNORECASE)

# wilmott-faq: 行末 ? + 后续段落含 "Short answer"
_WILMOTT_Q = re.compile(r"\?\s*\nShort answer\b", re.MULTILINE)

# primer: Question N: (整数编号) + (Answer on page X)
_PRIMER_Q = re.compile(r"\bQuestion\s+\d+\s*:", re.IGNORECASE)
_PRIMER_A_REF = re.compile(r"\(Answer on page \d+\)")

# 通用题号: 1. / Q1. / Question 1:
_GENERIC_NUM = re.compile(r"(?:^|\n)(?:Q\d+[\.:]\s|Question\s+\d+\s*:\s|\d{1,3}[\.、．]\s)", re.MULTILINE)

# 参考文献: "N. Lastname, Firstname, YEAR, ..."
_BIB_ENTRY = re.compile(r"^\d{1,3}\.\s+[A-Z][a-z]+,\s+[A-Z]", re.MULTILINE)

# 非量化噪声段落
_NOISE_SECTIONS = {
    "horror_stories": re.compile(r"Interview Horror Stories", re.IGNORECASE),
    "non_quantitative": re.compile(r"Non-Quantitative Questions", re.IGNORECASE),
    "preface": re.compile(r"^Preface\b|^Foreword\b", re.MULTILINE | re.IGNORECASE),
    "table_of_contents": re.compile(r"^Table of Contents|^Contents\b", re.MULTILINE | re.IGNORECASE),
}

# 章节标题
_CHAPTER_RE = re.compile(
    r"^(?:Chapter|CHAPTER|Appendix|APPENDIX)\s+(\d+|[A-Z])\b[^\n]*",
    re.MULTILINE,
)


def _page_text(p: dict) -> str:
    return p.get("text", "")


def _scan_pages(pages: list[dict]) -> dict[str, Any]:
    """逐页扫描，收集各类信号计数和首次出现页码。"""
    signals: dict[str, Any] = {
        "crack_q_pages": [],
        "crack_a_pages": [],
        "wilmott_pages": [],
        "primer_q_pages": [],
        "primer_aref_pages": [],
        "generic_q_pages": [],
        "bib_pages": [],
        "noise_pages": {k: [] for k in _NOISE_SECTIONS},
        "chapter_pages": [],
        "total_pages": len(pages),
    }

    # 滑动窗口检测 wilmott（跨页需要合并文本）
    concat = ""
    page_breaks: list[tuple[int, int]] = []  # (offset, page_no)

    for p in pages:
        txt = _page_text(p)
        pg = p["page"]

        if _CRACK_Q.search(txt):
            signals["crack_q_pages"].append(pg)
        if _CRACK_A.search(txt):
            signals["crack_a_pages"].append(pg)
        if _PRIMER_Q.search(txt):
            signals["primer_q_pages"].append(pg)
        if _PRIMER_A_REF.search(txt):
            signals["primer_aref_pages"].append(pg)
        if _GENERIC_NUM.search(txt):
            signals["generic_q_pages"].append(pg)
        if _BIB_ENTRY.search(txt) and pg > len(pages) * 0.7:
            signals["bib_pages"].append(pg)
        for key, pat in _NOISE_SECTIONS.items():
            if pat.search(txt):
                signals["noise_pages"][key].append(pg)
        for m in _CHAPTER_RE.finditer(txt):
            signals["chapter_pages"].append((pg, m.group(0).strip()))

        page_breaks.append((len(concat), pg))
        concat += txt + "\n"

    # 全文检测 wilmott（跨页标题）
    for m in _WILMOTT_Q.finditer(concat):
        pos = m.start()
        for i in range(len(page_breaks) - 1, -1, -1):
            if pos >= page_breaks[i][0]:
                pg = page_breaks[i][1]
                if pg not in signals["wilmott_pages"]:
                    signals["wilmott_pages"].append(pg)
                break

    return signals


def _detect_format(signals: dict[str, Any]) -> str:
    crack_q = len(signals["crack_q_pages"])
    crack_a = len(signals["crack_a_pages"])
    wilmott = len(signals["wilmott_pages"])
    primer_q = len(signals["primer_q_pages"])
    primer_aref = len(signals["primer_aref_pages"])
    generic = len(signals["generic_q_pages"])

    # heard-crack: 大量 Question N.M: 且有对应 Answer N.M:
    if crack_q >= 5 and crack_a >= 3:
        return "heard-crack"
    # wilmott-faq: 找到 ? + Short answer 信号
    if wilmott >= 3:
        return "wilmott-faq"
    # primer: Question N: (整数) + (Answer on page X) 页码引用
    if primer_q >= 5 and primer_aref >= 5 and crack_q == 0:
        return "primer"
    # 通用题号
    if generic >= 5:
        return "auto"
    return "unknown"


def _estimate_page_ranges(signals: dict[str, Any], total_pages: int) -> dict[str, Any]:
    """推断题目区、答案区、参考文献区的页码范围。"""
    ranges: dict[str, Any] = {}

    q_pages = signals["crack_q_pages"] or signals["wilmott_pages"] or signals["generic_q_pages"]
    if q_pages:
        ranges["question_section"] = [min(q_pages), max(q_pages)]

    a_pages = signals["crack_a_pages"]
    if a_pages:
        ranges["answer_section"] = [min(a_pages), max(a_pages)]

    bib = signals["bib_pages"]
    if bib:
        ranges["bibliography_section"] = [min(bib), total_pages]

    return ranges


def analyze_book(
    meta_path: str,
    out_path: str | None = None,
) -> dict[str, Any]:
    """
    分析书籍结构，输出 book_profile.json。

    Args:
        meta_path:  render_meta.json 路径（render 步骤产出）
        out_path:   输出路径（默认与 meta_path 同目录的 book_profile.json）

    Returns:
        profile dict
    """
    meta_file = Path(meta_path)
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    pages = meta.get("pages", [])
    total = len(pages)

    logger.info(f"开始书籍结构分析：{meta_file.name}，共 {total} 页", extra={"stage": "analyze"})

    signals = _scan_pages(pages)
    fmt = _detect_format(signals)
    page_ranges = _estimate_page_ranges(signals, total)

    # 章节列表去重
    chapters = []
    seen_chapters: set[str] = set()
    for pg, title in signals["chapter_pages"]:
        if title not in seen_chapters:
            chapters.append({"page": pg, "title": title})
            seen_chapters.add(title)

    # 噪声段落
    noise_found = {k: v for k, v in signals["noise_pages"].items() if v}

    # 估算题目数量
    q_count = max(
        len(signals["crack_q_pages"]) * 3,  # 每页平均约 3 题
        len(signals["wilmott_pages"]) * 1,
        len(signals["generic_q_pages"]) * 2,
    )

    profile: dict[str, Any] = {
        "source_file": meta.get("source", str(meta_file)),
        "total_pages": total,
        "is_scanned_pdf": meta.get("is_scanned_pdf", False),
        "detected_format": fmt,
        "recommended_splitter": fmt,
        "page_ranges": page_ranges,
        "chapters": chapters,
        "noise_sections": noise_found,
        "estimated_questions": q_count,
        "signals": {
            "crack_question_pages": len(signals["crack_q_pages"]),
            "crack_answer_pages": len(signals["crack_a_pages"]),
            "wilmott_qa_pages": len(signals["wilmott_pages"]),
            "generic_numbered_pages": len(signals["generic_q_pages"]),
            "bibliography_pages": len(signals["bib_pages"]),
        },
    }

    if out_path is None:
        out_path = str(meta_file.parent / "book_profile.json")

    Path(out_path).write_text(json.dumps(profile, ensure_ascii=False, indent=2))
    logger.info(
        f"书籍分析完成：格式={fmt}，推荐解析器={fmt}，估算题数≈{q_count}",
        extra={"stage": "analyze"},
    )
    return profile
