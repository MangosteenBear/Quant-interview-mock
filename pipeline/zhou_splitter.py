"""
Xinfeng Zhou "A Practical Guide to Quantitative Finance Interviews" 专用解析器

结构特征：
- 2 列 PDF，OCR 将两列逐行交叉合并（左列奇数行，右列偶数行），导致文字混排
- 题目格式：[题目标题（短 Title-Case 行）] [多行问题描述] Solution: [答案正文]
- 章节共 7 章，每章 15-35 道题，共 ~153 道
- 答案标记：行首 "Solution:" （严格行首，区分正文中的 "solution"）

提取策略：
1. 用 "Solution:" 作为 Q/A 分界锚点
2. 对分界点之前的文本，找最近一个 "题目标题行"（短 Title-Case 行）作为 stem 的起点
3. 截取从标题到 Solution: 之间的文字作为 stem（含 2 列交叉噪声，可接受）
4. Solution: 之后到下一个标题/Solution: 之前的文字作为 answer
"""
import json
import re
from pathlib import Path
from typing import Any


# ── 噪声过滤 ──────────────────────────────────────────────────
_PAGE_HEADER = re.compile(
    r"^(?:Brain Teasers|Calculus and Linear Algebra|Probability Theory"
    r"|Stochastic Process.*|Finance|Algorithms.*|General Principles"
    r"|A Practical Guide.*)\s*$",
    re.MULTILINE,
)
_SECTION_HEADER = re.compile(r"^\d+\.\d+\s+\w[^\n]+$", re.MULTILINE)

# ── Solution 锚点（严格行首）────────────────────────────────────
_SOL_RE = re.compile(r"(?:^|\n)Solution:\s*", re.MULTILINE)

# ── 章节标题（用于判断当前 chapter）────────────────────────────
_CHAPTER_RE = re.compile(
    r"Chapter\s+(\d+)\s+([A-Z][^\n]{3,50})", re.MULTILINE
)

# ── 题目标题特征 ─────────────────────────────────────────────
# 短行（2-8 词），Title Case 或首字大写，不含数字开头，不含句号结尾
_TITLE_RE = re.compile(
    r"^([A-Z][a-z][^\n]{1,50})$",
    re.MULTILINE,
)
# 需要额外过滤的噪声行
_TITLE_NOISE = re.compile(
    r"^(?:Brain Teasers|Calculus|Probability|Stochastic|Finance|Algorithms"
    r"|General Principles|A Practical Guide|Chapter|Solution|Hint|Note"
    r"|Figure|Table|Appendix|References?|Index|Applying|Following|Using"
    r"|Consider|Since|Therefore|However|Notice|Recall)\b",
    re.IGNORECASE,
)
# 题目标题不含特殊结尾或逗号（日期列表等）
_TITLE_BAD_END = re.compile(r"[,;:()\[\]{}]$")
_MONTH_IN_TITLE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b")

# 词数范围：2-8 词为有效标题
def _is_title(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    words = line.split()
    if not (2 <= len(words) <= 8):
        return False
    if not _TITLE_RE.match(line):
        return False
    if _TITLE_NOISE.match(line):
        return False
    if _TITLE_BAD_END.search(line):
        return False
    if _MONTH_IN_TITLE.search(line):  # 过滤日期行
        return False
    if "," in line:  # 含逗号的不是题目标题
        return False
    # 不能全大写（非表头）
    if line.isupper():
        return False
    # 包含数字开头，排除（页码、序号）
    if re.match(r"^\d", line):
        return False
    return True


def _clean(text: str) -> str:
    # 去除页眉
    text = _PAGE_HEADER.sub("", text)
    # 去除章节小标题（N.M ...）
    text = _SECTION_HEADER.sub("", text)
    # 清理控制字符
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # 合并多个空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _build_full_text(pages: list[dict]) -> tuple[str, list[tuple[int, int]]]:
    parts, offsets, pos = [], [], 0
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


def _chapter_at(offset: int, chapter_map: list[tuple[int, str]]) -> str:
    """给定字符偏移，返回当前章节名。"""
    ch = "Unknown"
    for start, name in chapter_map:
        if start <= offset:
            ch = name
        else:
            break
    return ch


def split_zhou(meta_path: str, out_path: str) -> list[dict[str, Any]]:
    meta = json.loads(Path(meta_path).read_text())
    pages = meta["pages"]
    full, offsets = _build_full_text(pages)

    # 建立章节 offset 映射
    chapter_map: list[tuple[int, str]] = []
    for m in _CHAPTER_RE.finditer(full):
        chapter_map.append((m.start(), f"Ch{m.group(1)} {m.group(2).strip()[:50]}"))

    # 找到所有 Solution: 位置
    sol_positions = [m.start() for m in _SOL_RE.finditer(full)]

    questions: list[dict[str, Any]] = []

    for i, sol_start in enumerate(sol_positions):
        # 前一个 Solution: 的结束位置（或文本起点）
        if i == 0:
            block_start = 0
        else:
            prev_sol = sol_positions[i - 1]
            # 上一个答案结束在下一个"标题"附近
            block_start = prev_sol

        # 当前 Solution: 之前的文本块
        pre_block = full[block_start:sol_start]

        # 在 pre_block 中找最后一个题目标题行
        title = None
        title_pos_in_block = 0
        for line_m in re.finditer(r"^([^\n]+)$", pre_block, re.MULTILINE):
            line = line_m.group(1).strip()
            if _is_title(line):
                title = line
                title_pos_in_block = line_m.start()

        # 回退策略：如果 pre_block 内找不到标题，向前多看 1000 字符（跨页情况）
        if title is None and i > 0:
            extra_start = max(0, block_start - 1000)
            extra_block = full[extra_start:sol_start]
            for line_m in re.finditer(r"^([^\n]+)$", extra_block, re.MULTILINE):
                line = line_m.group(1).strip()
                if _is_title(line):
                    title = line
                    title_pos_in_block = extra_block.rfind(title)
                    pre_block = extra_block  # 更新为扩展块

        # 最终回退：取 Solution: 之前最后一个以 "?" 结尾的段落作为 stem
        if title is None:
            q_match = re.search(r"([^\n]{20,}\?)\s*$", pre_block.rstrip())
            if q_match:
                title = f"[Q{i+1}]"
                title_pos_in_block = q_match.start()

        if title is None:
            continue

        # stem = 从标题到 Solution: 之间
        stem_raw = pre_block[title_pos_in_block:]
        stem = _clean(stem_raw)
        if len(stem) < 20:
            continue

        # answer = 从 Solution: 到下一个题目标题（或下一个 Solution: - 200 chars）
        sol_end = sol_start + len(_SOL_RE.search(full[sol_start:sol_start+20]).group())
        if i + 1 < len(sol_positions):
            next_sol = sol_positions[i + 1]
            # 找 next_sol 之前的最近标题
            between = full[sol_end:next_sol]
            ans_end = sol_end + len(between)
            for line_m in re.finditer(r"^([^\n]+)$", between, re.MULTILINE):
                line = line_m.group(1).strip()
                if _is_title(line):
                    ans_end = sol_end + line_m.start()
                    break
        else:
            ans_end = min(sol_end + 3000, len(full))

        answer = _clean(full[sol_end:ans_end])

        chapter = _chapter_at(sol_start, chapter_map)
        page = _offset_to_page(sol_start, offsets)

        questions.append({
            "id": f"zhou_{i+1:03d}",
            "question_marker": f"Zhou-{title}",
            "chapter": chapter,
            "source_pages": [page] if page else [],
            "raw_text": stem,
            "answer_text": answer if len(answer) > 30 else None,
        })

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(questions, ensure_ascii=False, indent=2))
    return questions
