# 数据流水线 — PDF 处理 CLI

> 扫描版 / 文字版量化面试 PDF → 结构化题库的批量处理流水线

---

## 完整工作流

```
┌─────────────────────────────┐
│      ① PDF 原文件           │  扫描版 / 文字版
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        ② render             │  逐页渲染，初步判定扫描/文字版
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        ③ analyze            │  书籍结构分析 → book_profile.json
│                             │  检测格式 / 估算题目数量
└──────────────┬──────────────┘
               │ 扫描版
               ▼
┌─────────────────────────────┐
│         ④ ocr               │  PaddleOCR PP-OCRv6 → ocr_meta.json
│   （文字版跳过此步骤）       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐        ┌───────────────────────────┐
│         ⑤ split             │──────▶ │       Splitter 路由        │
│  按格式调用专用 splitter     │        │ primer  → primer_splitter  │
└──────────────┬──────────────┘        │ heard-crack → crack_split  │
               │                       │ wilmott-faq → faq_split    │
               ▼                       │ zhou    → zhou_splitter    │
┌─────────────────────────────┐        └───────────────────────────┘
│          ⑥ link             │  stem ↔ answer 关联匹配
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│         ⑦ dedup             │  SimHash 64-bit，Hamming ≤ 3 去重
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│         ⑧ ingest            │  幂等写入 SQLite → 返回 source_id
└──────────────┬──────────────┘
               │
               ▼
╔═════════════════════════════╗
║    ⑨ 全量质检（强制）        ║  quant-qa-reviewer 逐题扫描
║                             ║  ⚠️  → status = 'review'
║                             ║  ❌  → status = 'rejected'
╚══════════════┤══════════════╝
               │ ✅ ok
               ▼
┌─────────────────────────────┐
│          ⑩ 打标             │  quant-tagger → topic + difficulty
└──────────────┬──────────────┘
               │
               ▼
╔═════════════════════════════╗
║    ⑪ 题型转换（强制）        ║  quant-transformer 批量生成变体
║                             ║  每题生成 MCQ（选择题）+ FITB（填空题）
║                             ║  写入 question_variants 表（临时暂存）
╚══════════════╤══════════════╝
               │
               ▼
┌─────────────────────────────┐
│     ⑫ 变体质检              │  quant-qa-reviewer 核验 MCQ/FITB
│                             │  检查正确答案数学准确性、干扰项合理性
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│     ⑬ 变体迁移入库          │  将 question_variants 迁移进 questions 表
│                             │  MCQ → question_type='choice' + options 表
│                             │  FITB → question_type='fill' + solutions 表
│                             │  parent_question_id 关联原题
└──────────────┬──────────────┘
               │
               ▼
         题库更新完成 ✓
    （原题 + MCQ + FITB 混合呈现）
```

---

## 当前入库状态（v1.7，2026-07-03）

> 扫描版书籍已全面切换至 vision_lab 视觉版（替换策略）。旧正则版保留为 `pending`，可回滚。

### 已发布（含 MCQ + FITB 变体）

| source_id | 书名 | 入库方式 | short | choice | fill | 合计 |
|-----------|------|---------|-------|--------|------|------|
| 2 | FAQ Quant Interview (Wilmott) | 原 pipeline（文字版） | 60 | 60 | 60 | **180** |
| 7 | A Practical Guide (Zhou 188p vision) | vision_lab | 165 | 173 | 165 | **503** |
| 8 | Heard on the Street [vision] | vision_lab | 147 | 147 | 147 | **441** |
| 9 | Quantitative Primer [vision] | vision_lab | 53 | 53 | 53 | **159** |
| **合计** | | | **425** | **433** | **425** | **1283** |

### 已退役（status='pending'，不展示）

| source_id | 书名 | 退役原因 |
|-----------|------|---------|
| 3 | Heard on the Street (Crack, 正则版) | 被 src8 视觉版替换 |
| 4 | Quantitative Primer (Bester, 正则版) | 被 src9 视觉版替换 |
| 5 | A Practical Guide (Zhou 96p, 正则版) | 被 src7 视觉版替换 |
| 6 | A Practical Guide (Zhou 188p, 正则版) | 被 src7 视觉版替换 |

### 待处理书籍

| 书名 | 页数 | 状态 |
|------|------|------|
| Probability & Stochastic Calculus | 326p | 待开始（vision_lab） |
| Mark Joshi Q&A | 329p | 待开始（vision_lab） |
| 150 Most FAQ | 220p | 待开始（最难，96MB 彩色扫描） |

---

## 快速开始

```bash
# 分步执行（标准流程）
python -m pipeline render  --pdf book.pdf --out ./output/BookName
python -m pipeline analyze --pages-dir ./output/BookName
python -m pipeline ocr     --pages-dir ./output/BookName          # 扫描版专用
python -m pipeline split   --ocr-dir ./output/BookName --out ./output/BookName/questions.json
python -m pipeline link    --questions ./output/BookName/questions.json \
                           --meta ./output/BookName/render_meta.json \
                           --out ./output/BookName/questions_linked.json
python -m pipeline dedup   --questions ./output/BookName/questions_linked.json \
                           --out ./output/BookName/questions_deduped.json
python -m pipeline ingest  --questions ./output/BookName/questions_deduped.json \
                           --db-url sqlite:///./backend/quantquiz.db \
                           --source-title "书名"
# 然后在 Claude Code 中调用 quant-qa-reviewer agent（传入 source_id）
# 最后调用 quant-tagger agent 打标
```

---

## CLI 命令参考

| 命令 | 作用 | 关键参数 |
|------|------|---------|
| `render` | PDF 渲染与扫描版判定，输出 `render_meta.json` | `--pdf` `--dpi`(300) `--out` |
| `analyze` | 书籍结构分析，输出 `book_profile.json` | `--pages-dir` `--out` |
| `ocr` | PaddleOCR 扫描版，产出 `ocr_meta.json` | `--pages-dir` `--out` |
| `split` | 题目边界识别，按 `--format` 选 splitter | `--ocr-dir` `--out` `--format`(auto) |
| `link` | 答案关联（内嵌 + 散布 + 集中三策略） | `--questions` `--meta` `--out` |
| `dedup` | SimHash 64-bit 近重复检测 | `--questions` `--out` `--threshold`(3) |
| `ingest` | 幂等入库（simhash 相同自动跳过） | `--questions` `--db-url` `--source-title` |
| `run` | 完整流水线串联（不含质检/打标） | `--pdf` `--out-dir` `--db-url` `--source-title` |

---

## 中间产物

```
output/BookName/
  ├── page_0001.png … page_NNNN.png   ← render 产出
  ├── render_meta.json                 ← 页面信息 + 扫描版判定
  ├── ocr_meta.json                    ← OCR 文本（扫描版专用）
  ├── book_profile.json                ← 格式 / 估算题数 / 推荐 splitter
  ├── questions.json                   ← split 原始提取
  ├── questions_linked.json            ← link 答案关联后
  └── questions_deduped.json           ← dedup 去重后（入库用）
```

---

## 专用 Splitter

| Splitter | 适用格式 | 代表书 |
|----------|----------|--------|
| `quantitative_primer_splitter.py` | `Question N:` + 答案区跨页，含章节嵌入题 | Quantitative Primer (Bester) |
| `faq_wilmott_splitter.py` | 完整问句作标题 + `Short answer` 段落 | FAQ Quant Interview (Wilmott) |
| `heard_crack_splitter.py` | `Question N.M:` / `Answer N.M:`，题答分离，书末参考文献 | Heard on the Street (Crack) |
| `zhou_splitter.py` | 2 列 PDF，`Solution:` 作 Q/A 锚点，Title-Case 行作题名 | A Practical Guide (Zhou) |
| `question_splitter.py` | 通用：`N.` / `QN.` / `第N题` 等 6 种格式 | 其他 |

---

## 质检与打标（⑨⑩ 步骤）

### quant-qa-reviewer（全量质检）

- **时机**：每次 ingest 后立即执行，**不可跳过**
- **范围**：该 source_id 下**所有**题目（无数量上限）
- **写回**：`⚠️ → status='review'`，`❌ → status='rejected'`，`✅` 不改动
- **调用**：在 Claude Code 中传入 `db_path` + `source_id`

### quant-tagger（批量打标）

- **时机**：质检完成后
- **输出**：`tags` + `question_tags` 表，每题 1-3 个 topic 标签 + 1 个 difficulty 标签
- **标签体系**：概率论 / 随机过程 / 统计学 / 线性代数 / 微积分 / 数论与组合 / 逻辑推理 / 金融衍生品 / 固定收益 / 量化策略 / 编程算法 / 软性面试

---

## 已知局限

- **Zhou 2列OCR**：`zhou_splitter.py` 用 `Solution:` 锚点提取，stem 含邻列噪声。当前 130 题中约 33% 为 `⚠️` 级别。
- **数学公式**：PaddleOCR 输出文本近似（`sigma` 代替 σ），不影响质检判断，但无精确 LaTeX。如需精确公式需集成 PP-FormulaNet-S。
- **大规模去重**：当前 SimHash O(n²) 对 1 万题内无压力，超出后可换 `datasketch` MinHash LSH。

---

## 模块文件

| 文件 | 职责 |
|------|------|
| `pdf_renderer.py` | PDF 渲染与扫描版判定 |
| `book_analyzer.py` | 书籍结构分析（格式检测 / 估题数 / 推荐 splitter） |
| `ocr_dispatcher.py` | PaddleOCR 扫描版文字提取 |
| `question_splitter.py` | 通用题目边界识别（6 种格式） |
| `quantitative_primer_splitter.py` | Primer 专用解析器 |
| `faq_wilmott_splitter.py` | FAQ Wilmott 专用解析器 |
| `heard_crack_splitter.py` | Heard on the Street 专用解析器 |
| `zhou_splitter.py` | Zhou 2列PDF 专用解析器 |
| `answer_linker.py` | 答案关联（内嵌 / 散布 / 集中三策略） |
| `dedup.py` | SimHash 64-bit 近重复检测 |
| `ingest.py` | 幂等批量入库 |
| `cli.py` | Click CLI 入口 |
| `logger.py` | JSON 结构化日志 |

**Agents**：`~/.claude/agents/quant-qa-reviewer.md`，`~/.claude/agents/quant-tagger.md`

---

## 实验性功能 · vision_lab（视觉大模型入库）

> 独立实验模块,与本主 pipeline 隔离——只新增、不修改现有代码,入库写独立影子库,主库不受影响。

针对扫描 / 双列书「排版错乱」和「整本坍缩成十几题」的结构性问题,`vision_lab` 换一条路线:
把整页图直接交给 Claude 视觉模型,一步完成 OCR + 版面理解 + 语义切题,绕开 PaddleOCR + 正则切题。
它复用主 pipeline 的 `render` / `dedup` / `ingest` / `quant-qa-reviewer`,仅替换中间的
「视觉抽取 + 跨页合并」。

详见 [`vision_lab/README.md`](vision_lab/README.md)（含工作流图、成本、CLI 用法、A/B 对比方法）。

```bash
.venv/bin/pip install -r pipeline/vision_lab/requirements.txt
.venv/bin/python -m pipeline.vision_lab run --book /path/to/book.pdf --pages 1-20
```
