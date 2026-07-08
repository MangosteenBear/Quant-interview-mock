# Changelog

所有版本变更记录。版本号格式：`vMAJOR.MINOR`，MINOR 表示功能迭代，MAJOR 表示破坏性变更。

---

## v2.5 — 2026-07-08

### M4（前三项）：筛选 URL 持久化、搜索相关性排序、模考模式

- **D01 筛选 UI**：列表页原有 题型/知识点/难度/来源 筛选补齐「URL 持久化」——筛选状态写入地址栏 query，H5 刷新不丢失，可直接分享带筛选的链接
- **D02 搜索升级**：PG 环境用 `pg_trgm similarity()` 做相关性排序（GIN 索引已建），SQLite 开发环境自动回退 id 排序；新增 `migrations/002_m4_search.sql` 给 solutions 表补 trgm 索引
- **D03 模考模式**：
  - 新增 `exam_sessions` 表（启动自动建表）
  - `POST /api/exam/start`（题数 5-50 / choice/fill/mixed / 可选限时）+ `POST /api/exam/{id}/submit`（服务端统一判分，防重复提交、防他人代交）
  - 前端 `/pages/exam` 三态一页：配置 → 顺序作答（进度条 + 倒计时 + 预取下一题）→ 成绩报告（分数/正确率/用时/错题明细可跳详情）
  - 限时到点自动交卷；模考作答计入 attempt_logs（错题本/统计联动）
  - 首页新增 📝 模考入口
- 后端模考冒烟测试 7 项全过

> 部署备注（累积）：① JWT_SECRET ② 001+002 迁移 SQL ③ update.sh

## v2.4 — 2026-07-08

### M5 学习深化：每日一题、笔记、智能刷题、已掌握

产品定位复盘后补齐「每日惯性、深度加工、巩固效率」三个留存环节（详见 PRD M5 章节）：

- **每日一题**：`GET /api/questions/daily` 按日期 hash 确定性选题，全站当天同一道；首页卡片升级为服务端版，完成后显示 ✅
- **题目笔记**：新增 `notes` 表；`GET/PUT /api/questions/{id}/note`（空内容即删除，上限 5000 字）；详情页折叠笔记区
- **智能刷题**：`/api/questions/random?mode=smart` 三级回退（最近答错 > 未做过 > 全随机）；首页新增 🧠 智能刷题入口
- **已掌握标记**：新增 `mastered_questions` 表；错题本每题可标记移出，答错自动清除标记回归错题本；智能刷题同样排除已掌握
- 全部功能匿名（device_id）与登录（user_id）双身份可用
- request 层支持 PUT；后端 M5 冒烟测试 11 项全过

> 部署备注：新表由应用启动 create_all 自动创建，本版本无需手动迁移 SQL

## v2.3 — 2026-07-08

### M2+M3：账号体系 + 学习闭环

- **账号**（M2）：手机验证码登录（dev provider 可插拔，ICP 后切腾讯云短信）、JWT access 7d/refresh 30d、401 静默刷新、登录自动绑定设备历史记录
- **学习闭环**（M3）：错题本（最近作答为准，答对自动移出）、学习统计（正确率/今日/streak/题型分布）、「我的」个人中心 tab（替代设置 tab）、昵称编辑、随机刷题悬浮按钮
- 新增表：`users`、`verification_codes`；`attempt_logs`/`favorites`/`question_reports` 加 `user_id` 列（迁移脚本 `backend/migrations/001_m2_users.sql`）
- 匿名用户统计/错题本按 device_id 可用，登录后跨设备

> 部署备注（累积待执行）：服务器需 ① `.env` 加 `JWT_SECRET` ② 跑 001 迁移 SQL ③ update.sh

## v2.2 — 2026-07-08

### 全栈上线腾讯云 CVM（Beta 可对外访问）

- **访问地址**：`http://124.221.191.102`（Nginx 80 端口，安全组仅放行 80）
- **后端**：systemd 服务 `quantquiz`，uvicorn 2 workers 监听 `127.0.0.1:8000`，Nginx 反代 `/api/`
- **前端**：`npm run build:h5` 产物由 Nginx 静态托管（`frontend/dist/build/h5`）；新增 `frontend/.env.production`，`VITE_API_BASE` 留空走同域反代
- **部署脚本**（新增 `deploy/` 目录）：
  - `setup_cvm.sh` — 首次部署（依赖安装、venv、systemd 注册）
  - `update.sh` — 日常更新（git pull + pip + 重启后端 + 前端构建）
  - `quantquiz.service` — systemd 单元
  - `nginx-quantquiz.conf` — Nginx 站点配置
- **更新流程确立**：本地 push main → 服务器执行 `bash deploy/update.sh`
- **踩坑记录**：
  - `.env` 中 `CORS_ORIGINS` 必须为 JSON 数组格式 `["*"]`
  - `/home/ubuntu` 需 `chmod o+x`，否则 Nginx www-data 无法读取静态文件
  - 服务器 Node 20 安装前需先卸载系统残留的 `libnode72`
  - psql 连接需 `-h 127.0.0.1 -U quantquiz` 强制 TCP（peer auth 会失败）
- **待办**：域名 + ICP 备案 + HTTPS（certbot）

---

## v2.1 — 2026-07-07

### 数据库迁移至腾讯云 CVM

- 生产数据库从本地 SQLite 迁移至腾讯云 CVM PostgreSQL 16（`124.221.191.102:5432`）
- `backend/.env` 切换 `DATABASE_URL` 为 `postgresql+asyncpg://...`
- SQLite 文件（`backend/quantquiz.db`）保留本地作为备用/离线快照
- 更新 `docs/architecture.md` 反映新部署状态

---

## v2.0 — 2026-07-03

### 新书入库：150 Most Frequently Asked Questions

- vision_lab 抽取（220p 彩色扫描，900px 降分辨率绕开 Batch 256MB 限制），$1.01
- 质检发现系统性重复（99 道题被抽取两遍），清理后保留 146 published / 48 review / 94 rejected
- 并入主库 source_id=12，生成变体（并发 20 线程）
- 变体：short 194 + choice 190 + fill 190 = **574 题**
- 修复 src10/11/12 options 表未写入的问题（补全所有选项），并均匀化 ABCD 分布

### 所有待处理书籍全部完成

**题库现状（发布）**：

| source_id | 书名 | short | choice | fill | 小计 |
|-----------|------|-------|--------|------|------|
| 2 | FAQ Quant Interview (Wilmott) | 60 | 60 | 60 | 180 |
| 7 | Zhou vision | 165 | 173 | 165 | 503 |
| 8 | Heard vision | 147 | 147 | 147 | 441 |
| 9 | Primer vision | 53 | 53 | 53 | 159 |
| 10 | Probability & Stochastic Calculus [vision] | 271 | 272 | 269 | 812 |
| 11 | Mark Joshi Q&A [vision] | 426 | 424 | 419 | 1269 |
| 12 | 150 Most FAQ [vision] | 194 | 190 | 190 | 574 |
| **合计** | | **1316** | **1319** | **1303** | **3938** |

---

## v1.9 — 2026-07-03

### 新书入库：Mark Joshi Q&A

- vision_lab 抽取（329p 扫描版，省钱档+Batch）→ 452 题原始，$2.01
- 质检：206 published / 225 review（无答案/引用图表等）/ 21 rejected
- 并入主库 source_id=11，生成变体（并发 20 线程）
- 变体：short 426 + choice 424 + fill 419 = **1269 题**

**题库现状（发布）**：

| source_id | 书名 | short | choice | fill | 小计 |
|-----------|------|-------|--------|------|------|
| 2 | FAQ Quant Interview (Wilmott) | 60 | 60 | 60 | 180 |
| 7 | Zhou vision | 165 | 173 | 165 | 503 |
| 8 | Heard vision | 147 | 147 | 147 | 441 |
| 9 | Primer vision | 53 | 53 | 53 | 159 |
| 10 | Probability & Stochastic Calculus [vision] | 271 | 272 | 269 | 812 |
| 11 | Mark Joshi Q&A [vision] | 426 | 424 | 419 | 1269 |
| **合计** | | **1122** | **1129** | **1113** | **3364** |

---

## v1.8 — 2026-07-03

### 新书入库：Probability & Stochastic Calculus

- vision_lab 抽取（326p 扫描版，省钱档+Batch）→ 278 题原始，$1.98
- 质检：138 published / 138 review（无答案，书籍题目与解答分章节）/ 2 rejected
- 并入主库 source_id=10，生成变体
- 变体：short 271 + choice 272 + fill 269 = **812 题**

**题库现状（发布）**：

| source_id | 书名 | short | choice | fill | 小计 |
|-----------|------|-------|--------|------|------|
| 2 | FAQ Quant Interview (Wilmott) | 60 | 60 | 60 | 180 |
| 7 | Zhou vision | 165 | 173 | 165 | 503 |
| 8 | Heard vision | 147 | 147 | 147 | 441 |
| 9 | Primer vision | 53 | 53 | 53 | 159 |
| 10 | Probability & Stochastic Calculus [vision] | 271 | 272 | 269 | 812 |
| **合计** | | **696** | **705** | **694** | **2095** |

---

## v1.7 — 2026-07-03

### 视觉大模型全面替换正则流水线（扫描版）

**替换策略**：扫描版书籍全部弃用 PaddleOCR + 正则 splitter，改用 vision_lab 视觉版，旧版设为 `status='pending'`（不删除，可回滚）。

| 操作 | 书名 | 旧 source | 新 source | 下架题数 | 并入题数（base） |
|------|------|----------|----------|---------|----------------|
| 重做 + 替换 | Heard on the Street | src3 (Crack) | src8 | 408 → pending | 147 short |
| 重做 + 替换 | Quantitative Primer | src4 (Bester) | src9 | 126 → pending | 53 short |
| 替换 | A Practical Guide (Zhou) | src5 + src6 | src7 | 414 → pending | 165 short |

- Zhou 188p 视觉版已在 v1.6 抽取，本版正式并入主库并下架旧版
- window_size 固定为 5（overlap 1），Batch API(-50%)，成本：Zhou ≈$1.5，Heard ≈$3，Primer ≈$1.5

### 变体扩充（视觉 base 全量）

为 src7/8/9 共 **365** 道 published short 题批量生成 MCQ + FITB 变体：
- 新增 choice：365 道（src7=173，src8=147，src9=53；含 8 道修正数量差异）
- 新增 fill：365 道
- 正确答案 ABCD 分布：A:230 / B:182 / C:161 / D:168（无明显集中偏向）
- 变体写入 `questions` 表，`parent_question_id` 关联原 short 题，`status='published'`

**题库现状（发布）**：

| source_id | 书名 | short | choice | fill | 小计 |
|-----------|------|-------|--------|------|------|
| 2 | FAQ Quant Interview (Wilmott) | 60 | 60 | 60 | 180 |
| 7 | Zhou vision | 165 | 173 | 165 | 503 |
| 8 | Heard vision | 147 | 147 | 147 | 441 |
| 9 | Primer vision | 53 | 53 | 53 | 159 |
| **合计** | | **425** | **433** | **425** | **1283** |

> 旧正则版 src3/4/5/6 共 948 道题保留在库中（`status='pending'`），不参与展示，可随时回滚。

---

## v1.6 — 2026-07-02

### 实验模块 vision_lab 调优
- 默认 `window_size` 3→5(overlap 1):质检发现主流问题是超长解答跨过 3 页窗口被截断；5 页窗口能装下更长解答，且步长 4 比 size3 窗口更少、开销略降
- Zhou 188p 全书质检 + 回填:175 题中 121 直接可用(69%)、加修可用 98%；真损坏仅约 4 道
  - window=5 重抽问题页,修复 4 道:巧克力题(补回缺失答案)、futures>forward(283→1222 补全截断)、代码题、vol smile(跨页错配纠正)
  - 大量「needs_review 截断」经 window=5 复验为**误报**(原答案本就完整)
  - 影子库现状:published 121 / review 52 / rejected 2

---

## v1.5 — 2026-07-01

### 实验性功能
- 新增 `pipeline/vision_lab/` —— 基于 Claude 视觉大模型的实验性入库模块,与主 pipeline 物理隔离
  - 整页图 → 结构化题目 JSON(滑窗 + Opus 4.8 + 结构化输出),绕开 PaddleOCR + 正则切题,解决扫描/双列书排版错乱与整本坍缩成十几题的问题
  - 复用 render / dedup / ingest / quant-qa-reviewer,仅替换「视觉抽取 + 跨页合并」两步
  - 入库写独立影子库 `output/vision_lab/quantquiz_vision.db`,主库 `quantquiz.db` 不受影响,用于 A/B 对比
  - 支持 Batch API(-50%)、prompt caching、单本成本上限;产出 `extraction_report.md`(题数/置信度/成本/需复核清单)
  - Zhou 188p 前 20 页 A/B 实测:视觉版 24–27 题 vs 正则版整本仅 8 题
  - 成本调优:默认改为「省钱档」sonnet-4-6 + 关 thinking + effort low + 图1500px,较 Opus 档便宜 ~68%($0.32 vs $1.00/20页)且质量持平,全书 Batch ≈ $1.5
- 主 pipeline 代码与数据零改动

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
