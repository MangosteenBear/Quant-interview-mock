"""
答案匹配工具模块

覆盖：
- 选择题：标签归一化（空格、中文逗号、大小写）
- 填空题：文本归一化 + 数值等价 + 备选值展开 + 多空逐项判定
"""
import re
from fractions import Fraction


# ─────────────────────────────────────────────
# 文本归一化
# ─────────────────────────────────────────────

def normalize_text(s: str) -> str:
    """
    统一化单个答案文本：
    - 去序号前缀（1. / ① 等）
    - 去 LaTeX 行内包裹（$...$ / \(...\)）
    - 去首尾标点
    - 合并空格、转小写
    """
    s = s.strip()
    # 序号前缀：`.` 后必须跟空格（避免误删 0.5 里的 0.）
    s = re.sub(r'^\d+\.\s+', '', s)
    s = re.sub(r'^\d+[\)、]\s*', '', s)
    s = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', s)
    # LaTeX 行内包裹
    s = re.sub(r'^\$(.+)\$$', r'\1', s.strip())
    s = re.sub(r'^\\\((.+)\\\)$', r'\1', s.strip())
    # 首尾标点
    s = re.sub(r'[.,;:!?。，；：！？]+$', '', s)
    s = re.sub(r'^[.,;:!?。，；：！？]+', '', s)
    # 合并空格、转小写
    return re.sub(r'\s+', ' ', s).strip().lower()


# ─────────────────────────────────────────────
# 数值等价
# ─────────────────────────────────────────────

def to_number(s: str) -> float | None:
    """
    尝试将字符串解析为浮点数，支持：
    - 分数：1/2 → 0.5
    - 百分比：50% → 0.5
    - 普通小数/整数
    返回 None 表示无法解析为数字。
    """
    s = s.strip()
    is_pct = s.endswith('%')
    base = s.rstrip('%').strip()
    try:
        val = float(Fraction(base))
        return val / 100.0 if is_pct else val
    except (ValueError, ZeroDivisionError):
        return None


# ─────────────────────────────────────────────
# 备选值展开
# ─────────────────────────────────────────────

def expand_alternatives(ref: str) -> list[str]:
    """
    将参考答案展开为所有可接受的候选值（归一化后）。

    处理规则（按优先级）：
    1. 括号备选：'a lot (lots)' → ['a lot', 'lots', 'a lot']
    2. or 连接：'increase or decrease' → ['increase', 'decrease', 原始]
    3. 空格斜杠：'yes / no' → ['yes', 'no']（有空格才拆，避免误拆 1/2）
    """
    base = normalize_text(ref)
    alts: set[str] = {base}

    # 括号备选
    m = re.search(r'\(([^)]+)\)', base)
    if m:
        alts.add(normalize_text(m.group(1)))
        alts.add(normalize_text(re.sub(r'\s*\([^)]+\)', '', base)))

    # or 连接
    if ' or ' in base:
        for part in base.split(' or '):
            alts.add(normalize_text(part))

    # 空格斜杠（' / '），避免误拆数学分数
    if ' / ' in base:
        for part in base.split(' / '):
            alts.add(normalize_text(part))

    return [a for a in alts if a]


# ─────────────────────────────────────────────
# 单空匹配
# ─────────────────────────────────────────────

def blank_match(user: str, ref: str) -> bool:
    """
    单个填空匹配：
    1. 文本完全相等（归一化后）
    2. 数值等价（1/2 == 0.5 == 50%）
    """
    u = normalize_text(user)
    for candidate in expand_alternatives(ref):
        if u == candidate:
            return True
        # 数值比较
        nu, nc = to_number(u), to_number(candidate)
        if nu is not None and nc is not None and abs(nu - nc) < 1e-9:
            return True
    return False


# ─────────────────────────────────────────────
# 选择题判定
# ─────────────────────────────────────────────

def judge_choice(user_answer: str, correct_labels: set[str]) -> bool:
    """
    选择题判定。
    user_answer：逗号分隔的标签字符串，如 "A" / "A,C" / "A, C" / "A，C"
    correct_labels：正确标签集合，如 {"A"} / {"A", "C"}
    """
    user_labels = {
        label.strip().upper()
        for label in user_answer.replace("，", ",").split(",")
        if label.strip()
    }
    return user_labels == correct_labels


# ─────────────────────────────────────────────
# 填空题判定
# ─────────────────────────────────────────────

def judge_fill(user_answer: str, ref_raw: str) -> tuple[bool, list[bool]]:
    """
    填空题判定。

    参数：
    - user_answer：用 | 分隔多空，如 "delta | 0.5"
    - ref_raw：参考答案，用 | 分隔多空，如 "$\\delta$ | 1/2"

    返回：
    - (overall_correct, per_blank_results)
      overall_correct：所有空都对才为 True
      per_blank_results：每空是否正确的列表（用于前端逐空反馈）
    """
    ref_parts = [p.strip() for p in ref_raw.split('|') if p.strip()]
    user_parts = [p.strip() for p in user_answer.strip().split('|')]

    if not ref_parts:
        return False, []

    # 数量不够时补空
    while len(user_parts) < len(ref_parts):
        user_parts.append('')

    per_blank = [blank_match(user_parts[i], ref_parts[i]) for i in range(len(ref_parts))]
    return all(per_blank), per_blank


# ─────────────────────────────────────────────
# 展示格式化
# ─────────────────────────────────────────────

def format_fill_answer(ref_raw: str) -> str:
    """
    清理填空题参考答案用于展示：
    - 去序号前缀
    - 多空用 ' | ' 分隔
    """
    parts = [p.strip() for p in ref_raw.split('|') if p.strip()]
    cleaned = []
    for p in parts:
        p = re.sub(r'^\d+\.\s+', '', p)
        p = re.sub(r'^\d+[\)、]\s*', '', p)
        p = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', p)
        cleaned.append(p.strip())
    return ' | '.join(cleaned)
