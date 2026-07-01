# Changelog

所有版本变更记录。版本号格式：`vMAJOR.MINOR`，MINOR 表示功能迭代，MAJOR 表示破坏性变更。

---

## v1.4 — 2026-07-01

### 数据入库
- Zhou lulu.com 188p 扫描版 OCR 完成（291K 字符，188 页）
- 与 source_id=5（Zhou 96p）去重后补录 **8 道新题**（source_id=6）
- 修复 8 题 OCR 噪声与跨题内容混入问题
- 为 8 题生成 MCQ + FITB 变体，共 16 道，全部发布
- 题库总量：1128 题（原题 376 + 变体 752），发布 1065 题

### 基础设施
- `.gitignore` 新增 `output/`（OCR 大文件）和 `.claude/` 排除规则

---

## v1.3 — 2026-07-01

### 后台管理
- 题目列表加「题型」筛选下拉（choice / fill / short / proof）
- 行内「下架/发布」快捷按钮，无需打开编辑抽屉
- 批量操作：复选框多选 + 批量发布/下架
- 举报管理 Tab：查看用户举报，支持一键下架问题题目或忽略举报

### 前端用户端
- 题目详情页底部加「⚑ 题目有问题」举报入口
- 举报 bottom sheet：4 类原因（答案有误 / 选项有问题 / 乱码排版 / 其他）
- 选择题提交后正确答案显示格式改为「正确答案 A：选项全文」
- 填空题支持多空输入（stem 中 `___①___` 数量自动决定输入框个数）

### 数据库
- `questions` 表新增 `parent_question_id` 列（自引用 FK，关联原简答题）
- 新增 `question_reports` 表（用户举报）
- 新增 `question_variants` 表（题型转换暂存，pipeline 中间产物）

### 数据
- 下架 21 道无选项选择题（OCR 分割错误）及其对应 42 道填空变体，共 63 题

---

## v1.2 — 2026-07-01

### 题库扩容：题型多样化
- 为 368 道原始简答题批量生成 MCQ（选择题）+ FITB（填空题）变体
- 写入 `question_variants` 表，再迁移为 `questions` 表正式题目
- 题库从 368 题扩展至 **1104 题**（简答 347 + 选择 389 + 填空 368，扣除下架）
- MCQ 正确答案位置随机分布（A:99 / B:100 / C:86 / D:83）
- 通过 `quant-qa-reviewer` 核验，修复 5 个错误（q312 灭绝概率、q131 Delta 条件、q253 数字不一致）

### 后端
- `questions.parent_question_id` 关联原题
- 选择题 `attempt` 接口 `correct_answer` 返回「正确答案 A：全文」格式
- 选择题解析（explanation）优先取 version=2（原题完整解析）

### Pipeline 文档
- 工作流扩展为 13 步，新增 ⑪ 题型转换、⑫ 变体质检、⑬ 变体迁移入库

---

## v1.1 — 2026-06-30

### Pipeline：全量质检强制化
- `book-question-extractor` skill 第 7 步改为全量质检（强制），不再是 15 题抽检
- 新增第 8 步：`quant-tagger` 批量打标
- `quant-qa-reviewer` agent 支持 `status` 写回数据库（⚠️→`review`，❌→`rejected`）

### 数据入库
- Heard on the Street (Crack) — 136 题（source_id=3）
- Quantitative Primer (Bester) — 42 题（source_id=4）
- A Practical Guide to Quant Finance (Zhou 96p) — 130 题（source_id=5）
- 合计入库 368 题（含 FAQ Wilmott 60 题）

### 题库工作流图
- 新增 10 步工作流 ASCII 图（pipeline/README.md）
- analyze 步骤独立为第 ③ 步（原流程漏标）

---

## v1.0 — 2026-06-29

### 初始发布
- FAQ Quant Interview (Wilmott) 60 题入库（source_id=2）
- 后端：FastAPI + SQLite + SQLAlchemy async
- 前端：uni-app H5，题目列表 / 详情 / 作答 / 收藏
- 管理后台：单页 HTML（Alpine.js + Tailwind），题目 CRUD + 标签管理
- Pipeline：PDF render → OCR → split → link → dedup → ingest
- 支持题型：`short`（简答）/ `choice`（选择）/ `fill`（填空）/ `proof`（证明）
