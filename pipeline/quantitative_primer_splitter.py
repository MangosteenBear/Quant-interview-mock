"""
Quantitative Primer (Bester) 专用解析器

题目来源共两类：

A. 编号题（Chapter 1）
   - 题目格式：行首 `Question N:` 正文 `(Answer on page X)`
   - 子题格式：`N.a)` / `N.b)` / `N.c)` 正文 `(Answer on page X)`
   - 答案格式：`Answer N:` 或 `Answer N.a):` 紧跟答案正文
   - 答案区与题目区跨页交叉分布，需全文扫描

B. 章节嵌入题（Chapter 2 "Old friends"）
   - 特征：在 `N.M\n[章节标题]` 之后，出现以完整疑问句结尾的缩进引用块
   - 信号短语：`"The question is usually presented as follows:"` /
              `"This question is sometimes called"` 等引语后跟问题陈述
   - 答案：从信号短语到下一个章节头之间的全部解析文本
   - 已知实例：
       - 2.1 Air Force One（醉汉乘客，100 人登机）—— 未在 Q1-41 中
       - 2.2 Stick breaking —— 等同于 Q21，已入库，不重复提取
"""
import json
import re
from pathlib import Path
from typing import Any


# ── 噪声过滤 ────────────────────────────────────────────────────
_NOISE = re.compile(
    r"\(Answer on page \d+\)"
    r"|\(Question on page \d+\)"
    r"|\n\s*\d{1,3}\s*\n"
    r"|\n\d+\.\d+\s*\n[^\n]+\n",
    re.MULTILINE,
)

# ── 答案识别 ─────────────────────────────────────────────────────
_A_SUB_RE = re.compile(
    r"Answer\s+(\d+)\.([a-z])\)\s*:\s*(.*?)(?=Answer\s+\d+|$)",
    re.DOTALL | re.IGNORECASE,
)
_A_MAIN_RE = re.compile(
    r"Answer\s+(\d+)\s*:\s*(.*?)(?=Answer\s+\d+|$)",
    re.DOTALL | re.IGNORECASE,
)

# ── stem 截断：切除夹在两个 Question 之间的其他题目答案（Answer N: 非子题格式）──
# 匹配 "Answer N:" 但不匹配 "Answer N.a):" 子题格式
_STEM_STOP_RE = re.compile(r"\nAnswer\s+\d+\s*(?![\.\w])[:\n]")

# ── 编号题识别（行首大写 Question，区分大小写防止正文中 "question 2:" 误触发）──
_Q_MAIN_RE = re.compile(
    r"(?:^|\n)Question\s+(\d+)\s*:\s*(.*?)(?=(?:^|\n)Question\s+\d+\s*:|$)",
    re.DOTALL,
)
_Q_SUB_RE = re.compile(
    r"(\d+)\.([a-z])\)\s*(.*?)(?=\d+\.[a-z]\)|$)",
    re.DOTALL,
)

# ── 章节嵌入题识别（Chapter 2 Old friends）────────────────────
# 用于找到章节标题后紧跟的引用块题目
# 信号：章节标题 `2.N\n[Name]\n` 后出现完整疑问句块
_CHAPTER_SECTION_RE = re.compile(
    r"\n2\.(\d+)\s*\n([^\n]+)\n(.*?)(?=\n2\.\d+\s*\n|\n3\s*\n|\Z)",
    re.DOTALL,
)
# 从章节文本中提取引用块题目（以 ? 结尾的完整段落）
_BLOCK_Q_RE = re.compile(
    r"(?:The question is[^\n]*?follows?[:\s]*\n|"
    r"This question is sometimes called[^\n]*?\n|"
    r"is usually presented as follows[:\s]*\n)"
    r"((?:[^\n]+\n){1,10}[^\n]+\?)",  # 1-10行，末行以?结尾
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    text = _NOISE.sub("\n", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)  # 控制字符
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _build_full_text(pages: list[dict]) -> tuple[str, list[tuple[int, int]]]:
    parts: list[str] = []
    offsets: list[tuple[int, int]] = []
    pos = 0
    for p in pages:
        txt = p.get("text", "")
        offsets.append((p["page"], pos))
        parts.append(txt)
        pos += len(txt) + 1
    return "\n".join(parts), offsets


def _offset_to_page(offset: int, offsets: list[tuple[int, int]]) -> int | None:
    lo, hi = 0, len(offsets) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if offsets[mid][1] <= offset:
            lo = mid + 1
        else:
            hi = mid - 1
    idx = lo - 1
    return offsets[idx][0] if idx >= 0 else None


def _extract_chapter_questions(
    full: str, offsets: list[tuple[int, int]]
) -> list[dict[str, Any]]:
    """
    提取 Chapter 2 'Old friends' 中以缩进引用块形式出现的嵌入题目。

    规则：
    1. 找到 `2.N  [Title]` 章节头
    2. 在章节体内搜索信号短语（"The question is...", "usually presented as follows:" 等）
    3. 提取紧跟信号短语的多行引用块（以 ? 结尾）作为题干
    4. 提取信号短语之后到下一章节之前的解析文本作为答案
    5. 如果题干与已有 Q1-41 完全相同（如 Q21 Stick Breaking），跳过不重复入库
    """
    SKIP_STEMS = {
        # Q21 Stick Breaking 与 Chapter 2.2 完全相同，跳过
        "break a 1",
        "break a 1 metre stick",
    }

    results: list[dict[str, Any]] = []

    for sec_m in _CHAPTER_SECTION_RE.finditer(full):
        sec_num = sec_m.group(1)
        sec_title = sec_m.group(2).strip()
        sec_body = sec_m.group(3)
        sec_page = _offset_to_page(sec_m.start(), offsets)

        # 在章节体里找引用块题目
        block_m = _BLOCK_Q_RE.search(sec_body)
        if not block_m:
            continue

        stem_raw = block_m.group(1).strip()
        stem_first_words = stem_raw.lower()[:30]

        # 跳过与已编号题重复的
        if any(skip in stem_first_words for skip in SKIP_STEMS):
            continue

        stem = _clean(stem_raw)
        if len(stem) < 20:
            continue

        # 答案 = 引用块之后到章节结束
        answer_start = block_m.end()
        answer_raw = sec_body[answer_start:]
        answer = _clean(answer_raw)

        results.append(
            {
                "id": f"primer_ch2_{sec_num}",
                "question_marker": f"Ch2.{sec_num}_{sec_title.replace(' ', '_')}",
                "source_pages": [sec_page] if sec_page else [],
                "raw_text": stem,
                "answer_text": answer if len(answer) > 50 else None,
            }
        )

    return results


def split_quantitative_primer(meta_path: str, out_path: str) -> list[dict[str, Any]]:
    meta = json.loads(Path(meta_path).read_text())
    pages = meta["pages"]
    full, offsets = _build_full_text(pages)

    # ── 1. 提取所有 Answer N: 答案 ──────────────────────────────
    answers: dict[str, str] = {}

    for m in _A_SUB_RE.finditer(full):
        key = f"{m.group(1)}.{m.group(2)}"
        answers[key] = _clean(m.group(3))

    for m in _A_MAIN_RE.finditer(full):
        key = m.group(1)
        if key not in answers:
            answers[key] = _clean(m.group(2))

    # ── 2. 提取编号题 Q1-Q41 ────────────────────────────────────
    questions: list[dict[str, Any]] = []

    for m in _Q_MAIN_RE.finditer(full):
        qnum = m.group(1)
        q_block = m.group(2)

        # 截断：切除夹在两道题之间的其他题目答案（Answer N: 不含子题格式）
        stop = _STEM_STOP_RE.search(q_block)
        if stop:
            q_block = q_block[: stop.start()]
        q_page = _offset_to_page(m.start(), offsets)

        sub_matches = list(_Q_SUB_RE.finditer(q_block))

        main_stem = q_block[: sub_matches[0].start()] if sub_matches else q_block
        main_stem = _clean(main_stem)
        if len(main_stem) < 8:
            continue

        sub_stems: list[str] = []
        for sm in sub_matches:
            sub_stems.append(f"{qnum}.{sm.group(2)}) {_clean(sm.group(3))}")

        full_stem = f"Question {qnum}:\n{main_stem}"
        if sub_stems:
            full_stem += "\n\n" + "\n\n".join(sub_stems)

        answer_parts: list[str] = []
        if qnum in answers:
            answer_parts.append(answers[qnum])
        for sm in sub_matches:
            sub_key = f"{qnum}.{sm.group(2)}"
            if sub_key in answers:
                answer_parts.append(f"Answer {sub_key}):\n{answers[sub_key]}")

        questions.append(
            {
                "id": f"primer_q{qnum}",
                "question_marker": f"Q{qnum}",
                "source_pages": [q_page] if q_page else [],
                "raw_text": full_stem,
                "answer_text": "\n\n".join(answer_parts) or None,
            }
        )

    # ── 3. 提取章节嵌入题（Chapter 2 Old friends）──────────────
    chapter_qs = _extract_chapter_questions(full, offsets)
    questions.extend(chapter_qs)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(questions, ensure_ascii=False, indent=2))
    return questions
