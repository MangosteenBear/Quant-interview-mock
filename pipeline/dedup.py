"""去重（A8）

算法：SimHash（64 bit）+ 汉明距离阈值过滤，纯 Python 实现，无外部依赖。

对于量化题库规模（数百到数千题），O(n²) 两两比较完全够用。
若后续规模超过 1 万题，可启用 datasketch MinHash LSH（已在 requirements.txt 注释备用）。

输入：questions_linked.json（或任意含 raw_text 的 questions JSON）
输出：questions_deduped.json — 去掉近重题后的列表，每题增加 simhash 字段
"""
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from pipeline.logger import logger

# 汉明距离阈值：<=3 视为近重复（64 bit 中允许 3 bit 不同 ≈ 95% 相似）
_HAMMING_THRESHOLD = 3

# 分词：按中英文单词 + 数字切分，去停用词
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+|[一-鿿]")


def _tokenize(text: str) -> list[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    # 2-gram 字符窗口增强短文本鲁棒性
    bigrams = [tokens[i] + tokens[i + 1] for i in range(len(tokens) - 1)]
    return tokens + bigrams


def _simhash(text: str, bits: int = 64) -> int:
    """计算文本的 SimHash 指纹。"""
    v = [0] * bits
    for token in _tokenize(text):
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        for i in range(bits):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    fingerprint = 0
    for i in range(bits):
        if v[i] > 0:
            fingerprint |= 1 << i
    return fingerprint


def _hamming(a: int, b: int, bits: int = 64) -> int:
    x = (a ^ b) & ((1 << bits) - 1)
    return bin(x).count("1")


def dedup_questions(
    questions_path: str,
    out_path: str = "./output/questions_deduped.json",
    hamming_threshold: int = _HAMMING_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    对题目列表执行 SimHash 近重复检测，保留每组重复题中最长的一题。

    Returns:
        去重后的题目列表（同写入文件）
    """
    questions: list[dict] = json.loads(Path(questions_path).read_text(encoding="utf-8"))
    n = len(questions)
    logger.info(f"开始去重，共 {n} 题，汉明阈值={hamming_threshold}", extra={"stage": "dedup"})

    # 计算每题 SimHash
    hashes: list[int] = []
    for q in questions:
        text = q.get("raw_text", "") + " " + (q.get("answer_text") or "")
        hashes.append(_simhash(text))

    # 标记重复：Union-Find 合并近重复组
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    dup_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            if _hamming(hashes[i], hashes[j]) <= hamming_threshold:
                union(i, j)
                dup_pairs += 1

    # 每组保留 raw_text 最长的题
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

    kept: list[dict[str, Any]] = []
    removed = 0
    for root, members in groups.items():
        if len(members) == 1:
            rep = members[0]
        else:
            rep = max(members, key=lambda i: len(questions[i].get("raw_text", "")))
            removed += len(members) - 1
            logger.info(
                f"重复组 {[questions[i]['id'] for i in members]} → 保留 {questions[rep]['id']}",
                extra={"stage": "dedup"},
            )
        kept.append({**questions[rep], "simhash": hex(hashes[rep])})

    # 按原始顺序排列
    order = {q["id"]: idx for idx, q in enumerate(questions)}
    kept.sort(key=lambda q: order.get(q["id"], 0))

    logger.info(
        f"去重完成：{n} → {len(kept)} 题，移除 {removed} 题（近重复对={dup_pairs}）",
        extra={"stage": "dedup"},
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(kept, ensure_ascii=False, indent=2))
    return kept
