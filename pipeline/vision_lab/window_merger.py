"""跨页窗口合并（vision_lab 核心新增）

相邻窗口重叠一页，同一道题可能在两个窗口各出现一次；跨页题也可能在某窗被截断、
在下一窗完整出现。本模块把这些重复/碎片合并为一条，并产出与主 pipeline
questions_linked.json **兼容** 的 schema，从而无缝接入现有 dedup / ingest。

兼容映射：
  stem_markdown   → raw_text        （ingest 用作 stem_markdown / dedup 用作指纹）
  answer_markdown → answer_text
  [page_start..page_end] → source_pages
额外字段（stem_latex/confidence/needs_review/notes/marker）原样保留，下游用 .get 忽略。
"""
import json
import re
from pathlib import Path
from typing import Any

from pipeline.logger import logger
from pipeline.vision_lab.vision_config import DEFAULT, VisionConfig

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+|[一-鿿]")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _page_overlap(q1: dict, q2: dict) -> bool:
    s1, e1 = q1.get("book_page_start", 0) or 0, q1.get("book_page_end", 0) or 0
    s2, e2 = q2.get("book_page_start", 0) or 0, q2.get("book_page_end", 0) or 0
    if not (s1 and s2):
        return False
    return not (e1 < s2 or e2 < s1)


def _is_same(q1: dict, q2: dict, threshold: float) -> bool:
    """两条抽取结果是否为同一道题（窗口重叠导致的重复 / 跨页碎片）。"""
    m1, m2 = (q1.get("marker") or "").strip(), (q2.get("marker") or "").strip()
    sim = _jaccard(_tokens(q1.get("stem_markdown")), _tokens(q2.get("stem_markdown")))
    # 相同非空题号 + 页码重叠(跨页碎片) 或 文本略有交集(重叠重复)
    if m1 and m1 == m2 and (_page_overlap(q1, q2) or sim >= 0.3):
        return True
    # 无题号时纯靠文本高相似
    return sim >= threshold


def _pick(q1: dict, q2: dict) -> dict:
    """两条同题结果择优合并：题干取更长的一条，答案取非空/更长的一条。"""
    stem1, stem2 = q1.get("stem_markdown") or "", q2.get("stem_markdown") or ""
    base = q1 if len(stem1) >= len(stem2) else q2
    merged = dict(base)
    # 答案：优先更长的非空
    a1, a2 = q1.get("answer_markdown") or "", q2.get("answer_markdown") or ""
    merged["answer_markdown"] = a1 if len(a1) >= len(a2) else a2
    # 页码并集（忽略缺失的 0）
    starts = [s for s in (q1.get("book_page_start"), q2.get("book_page_start")) if s]
    ends = [e for e in (q1.get("book_page_end"), q2.get("book_page_end")) if e]
    merged["book_page_start"] = min(starts) if starts else 0
    merged["book_page_end"] = max(ends) if ends else merged["book_page_start"]
    # needs_review 取并；confidence 取低者（更保守）
    merged["needs_review"] = bool(q1.get("needs_review") or q2.get("needs_review"))
    merged["confidence"] = min(q1.get("confidence", 1.0), q2.get("confidence", 1.0))
    seen, uniq = set(), []
    for n in (q1.get("notes"), q2.get("notes")):
        n = (n or "").strip()
        if n and n not in seen:
            seen.add(n)
            uniq.append(n)
    merged["notes"] = "; ".join(uniq)
    return merged


def merge_windows(
    vision_raw_path: str,
    out_path: str,
    cfg: VisionConfig = DEFAULT,
) -> list[dict[str, Any]]:
    """
    读取 vision_raw.jsonl，合并跨窗重复/碎片，输出 questions_linked 兼容 JSON。

    Returns: 合并后的题目列表（同写入文件）
    """
    windows = [json.loads(l) for l in Path(vision_raw_path).read_text(encoding="utf-8").splitlines() if l.strip()]

    merged: list[dict] = []
    dup = 0
    for win in windows:
        for q in win.get("questions", []):
            if not (q.get("stem_markdown") or "").strip():
                continue
            hit = None
            # 只与最近若干条比较即可（同题只可能出现在相邻窗口）
            for existing in reversed(merged[-30:]):
                if _is_same(existing, q, cfg.merge_sim_threshold):
                    hit = existing
                    break
            if hit is not None:
                idx = merged.index(hit)
                merged[idx] = _pick(hit, q)
                dup += 1
            else:
                merged.append(dict(q))

    # 转成 questions_linked 兼容 schema
    out_list: list[dict] = []
    for i, q in enumerate(merged):
        ps = q.get("book_page_start") or 0
        pe = q.get("book_page_end") or ps
        pages = list(range(ps, pe + 1)) if ps else []
        out_list.append({
            "id": f"vp{ps:04d}_q{i:03d}",
            "raw_text": q.get("stem_markdown", ""),
            "answer_text": q.get("answer_markdown") or None,
            "source_pages": pages,
            "question_marker": q.get("marker", ""),
            # 视觉抽取额外元数据（下游 .get 忽略，报告/复核用）
            "stem_latex": q.get("stem_latex", ""),
            "confidence": q.get("confidence"),
            "needs_review": bool(q.get("needs_review")),
            "notes": q.get("notes", ""),
        })

    logger.info(
        f"跨页合并：原始 {sum(len(w.get('questions', [])) for w in windows)} → {len(out_list)} 题"
        f"（合并 {dup} 处重叠/碎片）",
        extra={"stage": "window_merge"},
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_list, ensure_ascii=False, indent=2))
    return out_list
