# 数据流水线 — PDF 处理 CLI

> 影印 PDF 量化电子书 → 结构化题库的批量处理流水线

## ⚠️ 当前状态：脚手架阶段

**6 个命令 + `run` 全部为 TODO 占位**。仅 `logger.py`（JSON 结构化日志）与 CLI 框架可用。

## CLI 命令

```bash
cd /workspace
python -m pipeline --help                    # 查看帮助
python -m pipeline render --pdf book.pdf     # 渲染 PDF
python -m pipeline run --pdf book.pdf        # 完整流水线
```

| 命令 | 作用 | 关键参数 | 对应看板 | 状态 |
|------|------|---------|---------|------|
| `render` | PDF 渲染与扫描版判定 | `--pdf`(必填) `--dpi`(300) `--out` | A2 | TODO |
| `ocr` | 版面分析 + 分流 OCR | `--pages-dir` `--out` | A3/A4 | TODO |
| `split` | 题目边界识别 | `--ocr-dir` `--out` | A6 | TODO |
| `link` | 答案关联 | `--questions` | A7 | TODO |
| `dedup` | 去重（SimHash + MinHash） | `--questions` | A8 | TODO |
| `ingest` | 入库 | `--questions` `--db-url` | A10 | TODO |
| `run` | 完整流水线串联 | `--pdf` `--db-url` | — | TODO |

## 依赖

**已声明（轻量，可装）**：click / PyMuPDF / pdfplumber / opencv-python / numpy

**注释待装（重依赖，执行时再启）**：
- paddlepaddle + paddleocr（PP-OCRv4 + PP-StructureV3 + PP-FormulaNet-S）
- simhash + datasketch（去重）
- latex2mathml（LaTeX 校验）

## 日志

`logger.py` 输出 JSON 结构化日志，支持附加字段：`source_file` / `page` / `question_id` / `stage`。

## 后续实现路线

```
A2(渲染) → A3(版面分析) → A4(分流OCR) → A5(LaTeX重建)
→ A6(切题) → A7(答案关联) → A8(去重) → A9(审核后台) → A10(入库)
```

## 未创建的模块文件（TODO）

PRD 规划但尚未创建的 7 个模块：

| 文件 | 职责 | TODO |
|------|------|------|
| `pdf_renderer.py` | PDF 渲染与扫描版判定 | A2 |
| `layout_analyzer.py` | 版面分析 + 多栏重组 | A3 |
| `ocr_dispatcher.py` | 分流 OCR（文字/公式/表格） | A4 |
| `latex_builder.py` | LaTeX 重建与中间格式 | A5 |
| `question_splitter.py` | 题目边界识别 | A6 |
| `answer_linker.py` | 答案关联 | A7 |
| `dedup.py` | 去重机制 | A8 |

详见 [产品设计文档 §三 数据流水线](../docs/product-design.md) 和 [架构文档](../docs/architecture.md)
