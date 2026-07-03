# vision_lab —— 基于视觉大模型的入库模块

> **A/B 验证完成，已正式作为扫描版主流水线。** 与主 pipeline 物理隔离（不改主 pipeline 代码）；
> 先抽取到影子库 `output/vision_lab/quantquiz_vision.db`，通过质检后用 `merge_book.py` 并入主库，
> 同时将旧正则版设为 `pending`（替换策略，不删除）。

## 为什么做这个

主 pipeline 对扫描 / 双列书有两个结构性问题：
1. **排版错乱**——双列 PDF OCR 逐行交叉，题干散落；
2. **整本坍缩成十几题**——正则切题脆弱 + 过滤/去重过狠（如 Zhou 188p 从 112 个 Solution 锚点最终只入库 8 题）。

这两个问题的根子是「OCR 出纯文本 → 正则切题」这条路线本身，且每本新书都要手写一个 splitter，很吃人力。
本模块换思路：**把整页图直接交给 Claude 视觉模型,让它一步完成 OCR + 版面理解 + 语义切题**,
双列自动读对、切题靠语义而非正则锚点、公式出 LaTeX,一套 prompt 通吃各书。

## 设计原则：只替换中间三步

整条链只有「视觉抽取 + 跨页合并」是新写的；前面 render、后面 dedup/ingest/质检全部复用主 pipeline。
新模块产出的 JSON 与主 pipeline `questions_linked.json` **schema 兼容**,从而无缝接入现有 dedup/ingest。

```
                         原始书籍 PDF
                              │
                    book_analyzer 判断类型（复用）
                       │                    │
              文字版 → 走原 pipeline      扫描 / 双列
              （本模块不接管）                │
                                    ┌─────────┴──────────┐
                          [复用]    render 页面渲染       │  PDF → 页面图
                                             │
                        ╭──────── vision_lab 实验模块 ────────╮
                        │  [新增] vision_extract 视觉抽取      │  滑窗 + Opus 4.8
                        │            │                        │  + 结构化输出
                        │  [新增] window_merger 跨页合并       │  拼接 + 去重叠
                        ╰────────────┼───────────────────────╯
                          [复用]    dedup 去重                    SimHash · 跨版本
                                     │
                          [复用]    ingest 入库 → 影子库          A/B 对比
                                     │
                          [复用]    quant-qa-reviewer 质检        全量扫描 + 报告
```

复用（import，不修改）：`pdf_renderer.py` · `dedup.py` · `ingest.py`（指向影子库）· `logger.py` ·
`~/.claude/agents/quant-qa-reviewer.md`。

## 文件

| 文件 | 职责 |
|------|------|
| `vision_config.py` | 模型 / DPI / 窗口大小·重叠 / Batch 开关 / 成本上限 / 影子库 / 定价 |
| `prompts/extract_prompt.md` | 抽取指令，作为 prompt cache 前缀，逐窗复用 |
| `vision_extractor.py` | 核心：页面图 → 结构化题目 JSON（滑窗 + 视觉 + 结构化输出，支持 Batch） |
| `window_merger.py` | 跨页窗口拼接 + 去除重叠重复，输出 `questions_linked` 兼容 JSON |
| `vision_cli.py` | 独立入口：render→extract→merge→dedup→ingest→report |
| `requirements.txt` | 额外依赖（anthropic、Pillow） |

## 工作原理（关键点）

- **滑动窗口**：每次取连续 `window_size` 页（默认 **5**，overlap 1）。5 页窗口能装下更长解答，步长 4 比 size=3 窗数更少、开销更低；重叠产生的重复由 `window_merger` 去掉。
- **结构化输出**：`output_config.format` + JSON schema,每题产出
  `{marker, stem_markdown, stem_latex, answer_markdown, book_page_start/end, confidence, needs_review, notes}`。
- **模型参数(默认=省钱档)**：`claude-sonnet-4-6` + 关闭 thinking + effort low + 图片 1500px；数学出 LaTeX；题号/答案配对由模型语义判断。密集数学/手写严重的书可临时切 Opus 档(见下)。
- **跨页合并**：相同题号 + 页码重叠 → 判为同题（跨页碎片）；无题号则靠文本 Jaccard 相似度。择优保留更长题干、更全答案，页码取并集，`needs_review` 取并、confidence 取低（保守）。
- **成本控制**：抽取指令走 prompt cache 前缀；整批可走 Batch API（-50%）；`vision_config.max_cost_usd` 单本累计上限,超限告警/终止。
- **可追溯**：每窗原始响应落盘 `vision_raw.jsonl`,合并/去重可离线复跑,不必重调 API。

## 成本参考 & 档位选择（Zhou 188p 前 20 页 A/B 实测）

| 档位 | 配置 | 20 页成本(sync) | 题数 | 有答案 | 失败窗 |
|------|------|----------------|------|--------|--------|
| Opus 档 | opus-4-8 + thinking + effort high + 图2000px | $1.00 | 27 | 25/27 | 1(内容过滤) |
| **省钱档(默认)** | **sonnet-4-6 + 无thinking + effort low + 图1500px** | **$0.32** | 24 | **24/24** | **0** |

结论:省钱档便宜约 **68%**,质量与 Opus 档持平(题数 24 vs 27,有答案率反而更高),且更不易触发内容过滤——已设为默认。
密集数学/手写严重的书若质量不够,再临时切 Opus 档(`vision_config.py` 改 `model`/`use_thinking`/`effort`/`max_image_long_edge` 与对应 `price_*`)。

**成本拆解**(单窗约各半):图片输入 ≈50% / 输出(含 thinking)≈50%,缓存基本不计。故省钱的两个主杠杆是 **换 Sonnet + 关 thinking**(砍输出)和 **降图片分辨率 + Batch**(砍输入)。

**全书外推(~188 页)**:省钱档 sync ≈ $3;**省钱档 + Batch(-50%)≈ $1.5**(推荐)。文字版书继续走原 pipeline,不走视觉。

## 安装

```bash
.venv/bin/pip install -r pipeline/vision_lab/requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## 用法

```bash
# 小样验证（先跑前 20 页，确认格式与成本）
.venv/bin/python -m pipeline.vision_lab run --book /path/to/book.pdf --pages 1-20

# 全书 + Batch API（-50%）
.venv/bin/python -m pipeline.vision_lab run --book /path/to/book.pdf --batch

# 分步（调试 / 复跑）
.venv/bin/python -m pipeline.vision_lab extract --book book.pdf --out-dir output/vision_lab
.venv/bin/python -m pipeline.vision_lab merge --raw output/vision_lab/<book>/vision_raw.jsonl \
    --out output/vision_lab/<book>/vision_questions.json
```

入库后**必须**跑 `quant-qa-reviewer` agent 对 `vision_deduped.json` 全量质检（与主 pipeline 一致）。

## 产物

```
output/vision_lab/<book>/
├── pages/                  # render 产物（页面 PNG + render_meta.json，复用）
├── vision_raw.jsonl        # 每窗原始 LLM 响应（可追溯 / 复跑）
├── vision_questions.json   # 合并后，schema 兼容 questions_linked.json
├── vision_deduped.json     # dedup 后（入库用）
└── extraction_report.md    # 题数 / 置信度分布 / 成本 / needs_review 清单
output/vision_lab/quantquiz_vision.db   # 影子库（schema 同主库）
```

## A/B 验证结论（已完成，v1.7）

以 Zhou 188p 为试点（正则版仅 8 题，对比信号最强）：

| 指标 | 正则版（src5+6） | 视觉版（src7） |
|------|---------------|--------------|
| base 题数 | 138（正则+去重后实际仅约 8 道新题） | **165** |
| 有效有答案率 | ~75%（含 OCR 噪声） | **~98%** |
| 双列排版混叠 | 严重 | 无 |
| 公式质量 | 文本近似（sigma 代替 σ） | LaTeX 输出 |

**验证达标**，已对所有扫描版书籍执行替换策略（见下）。

## 已并入主库书籍

用 `output/vision_lab/_ops/merge_book.py` 执行并入 + 旧版下架：

| 书名 | shadow source | 主库 source_id | 下架旧版 | 并入 base 题 | 实际成本 |
|------|--------------|---------------|---------|------------|--------|
| A Practical Guide (Zhou 188p) | shadow src1 | **src7** | src5, src6 | 165 short | ≈$1.5 |
| Heard on the Street | shadow src2 | **src8** | src3 | 147 short | ≈$3.0 |
| Quantitative Primer | shadow src3 | **src9** | src4 | 53 short | ≈$1.5 |

## 新书入库标准流程

```bash
# 1. 视觉抽取 → 影子库
python output/vision_lab/_ops/run_<book>_vision.py

# 2. 质检（quant-qa-reviewer agent，传入 shadow source_id）

# 3. 并入主库 + 下架旧版
python output/vision_lab/_ops/merge_book.py \
    --shadow-src N --title "书名 [vision]" --retire "旧source_id"

# 4. 生成变体（quant-transformer agent，传入新 source_id）
```

## 边界

- 不修改主 pipeline 任何文件、不写前端 / backend。
- 新书默认先入影子库质检，通过后再 merge_book.py 并入主库。
