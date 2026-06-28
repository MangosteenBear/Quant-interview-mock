# API 参考文档

> 量化面试刷题题库平台 — 后端 API 完整文档
> 版本：v1.0 | 更新日期：2026-06-29 | 对应代码：`backend/app/api/`
> 交互式文档：启动后端后访问 `http://localhost:8000/docs`（Swagger UI）

---

## 一、通用约定

### 1.1 Base URL

| 环境 | URL |
|------|-----|
| 直接访问 | `http://localhost:8000/api` |
| H5 前端（经 vite 代理） | `/api`（vite.config.ts 代理到 :8000） |

### 1.2 分页规范

所有列表接口统一分页：

| 参数 | 类型 | 默认 | 约束 | 说明 |
|------|------|------|------|------|
| `page` | int | 1 | ≥1 | 页码，从 1 开始 |
| `page_size` | int | 20 | 1~100 | 每页数量 |

**分页响应结构**（`PageResponse<T>`）：

```json
{
  "items": [...],
  "total": 15,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 1.3 错误响应格式

后端有两种错误响应格式，前端需兼容：

| 场景 | HTTP 状态码 | 响应格式 |
|------|------------|---------|
| 业务错误（HTTPException） | 404 / 422 | `{"detail": "题目 X 不存在"}` |
| 服务器内部错误 | 500 | `{"code": 500, "message": "服务器内部错误", "detail": "..."}` |

> 500 错误的 `detail` 字段仅在 `DEBUG=True` 时返回具体信息。

### 1.4 鉴权

一期**匿名模式**，无 token/cookie。所有需要用户标识的接口通过请求体/查询参数传递 `device_id`（≤64 字符），由前端生成并持久化（`crypto.randomUUID()` 优先）。

---

## 二、端点总览

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | GET | `/api/health` | 健康检查 |
| 2 | GET | `/api/questions` | 题目列表（分页+筛选） |
| 3 | GET | `/api/questions/{id}` | 题目详情 |
| 4 | GET | `/api/questions/search/all` | 关键词搜索 |
| 5 | POST | `/api/questions/{id}/attempt` | 提交作答 |
| 6 | POST | `/api/favorites` | 切换收藏（toggle） |
| 7 | GET | `/api/favorites` | 收藏列表 |
| 8 | GET | `/api/sources` | 来源书目列表 |
| 9 | GET | `/api/tags` | 标签列表 |

---

## 三、端点详解

### 3.1 GET `/api/health` — 健康检查

**响应示例**：
```json
{
  "status": "ok",
  "app": "量化面试刷题题库平台",
  "version": "0.1.0"
}
```

---

### 3.2 GET `/api/questions` — 题目列表

**查询参数**：

| 参数 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `source_id` | int | 否 | — | 按来源书目筛选 |
| `book_chapter` | string | 否 | 精确匹配 | 按章节筛选 |
| `question_type` | string | 否 | choice/fill/short/proof | 按题型筛选 |
| `difficulty` | int | 否 | 1-5 | 按难度筛选 |
| `status` | string | 否 | 默认 `published` | 状态筛选 |
| `page` | int | 否 | ≥1，默认 1 | 页码 |
| `page_size` | int | 否 | 1-100，默认 20 | 每页数量 |

**响应**：`PageResponse<QuestionListItem>`

**响应示例**：
```json
{
  "items": [
    {
      "id": 1,
      "stem_markdown": "两枚公平骰子同时掷出，求两枚骰子点数之和为 7 的概率。\n\n$$P(\\text{sum}=7) = ?$$",
      "question_type": "choice",
      "difficulty": 1,
      "status": "published",
      "book_chapter": "Probability Basics",
      "source": {
        "id": 1,
        "book_title": "Heard on the Street: Quantitative Questions from Wall Street Job Interviews",
        "author": "Timothy Falcon Crack"
      },
      "tags": [
        {"id": 1, "name": "概率论", "type": "knowledge"},
        {"id": 12, "name": "量化研究", "type": "position"}
      ]
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

> **注意**：`book_chapter` 是精确匹配（非模糊），前端筛选用下拉选择更合适。

---

### 3.3 GET `/api/questions/{id}` — 题目详情

**路径参数**：`id`（int）

**响应**：`QuestionDetail`（比列表多 `options`/`solutions`/`book_page`/`updated_at`）

**⚠️ 安全提示**：响应中 `options[].is_correct` **包含正确答案标记**。前端 API 层（`api/question.ts`）会剥离该字段返回 `SafeQuestionDetail`。直接调后端 API 可绕过前端拿到答案。详见 [is_correct 安全机制](#五is_correct-安全机制)。

**响应示例**：
```json
{
  "id": 1,
  "stem_markdown": "两枚公平骰子同时掷出...",
  "question_type": "choice",
  "difficulty": 1,
  "status": "published",
  "book_page": 12,
  "book_chapter": "Probability Basics",
  "source": {"id": 1, "book_title": "...", "author": "..."},
  "options": [
    {"id": 1, "label": "A", "content_markdown": "$\\frac{1}{9}$", "is_correct": false},
    {"id": 2, "label": "B", "content_markdown": "$\\frac{1}{6}$", "is_correct": true},
    {"id": 3, "label": "C", "content_markdown": "$\\frac{5}{36}$", "is_correct": false},
    {"id": 4, "label": "D", "content_markdown": "$\\frac{7}{36}$", "is_correct": false}
  ],
  "solutions": [
    {"id": 1, "content_markdown": "点数和为 7 的组合有...", "version": 1}
  ],
  "tags": [...],
  "updated_at": "2026-06-23T12:00:00"
}
```

**错误**：404 `{"detail": "题目 1 不存在"}`

---

### 3.4 GET `/api/questions/search/all` — 关键词搜索

**查询参数**：

| 参数 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `q` | string | 是 | min_length=1 | 搜索关键词 |
| `page` | int | 否 | ≥1 | 页码 |
| `page_size` | int | 否 | 1-100 | 每页数量 |

**实现**：`stem_markdown ILIKE '%q%'`（开发 SQLite 用 LIKE；生产切 PG FTS + pg_jieba）。自动限定 `status='published'`。

**响应**：`PageResponse<QuestionListItem>`

> **路由注意**：路径为 `/search/all`（非 `/{id}`），因 `question_id` 为 int 类型，FastAPI 自动跳过不匹配的路由。

---

### 3.5 POST `/api/questions/{id}/attempt` — 提交作答

**请求体**（`AttemptRequest`）：

```json
{
  "device_id": "abc123-def456",
  "answer": "B",
  "duration_ms": 42000
}
```

| 字段 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `device_id` | string | 是 | 1-64 字符 | 匿名设备标识 |
| `answer` | string | 是 | — | 用户作答内容 |
| `duration_ms` | int | 否 | ≥0 | 作答耗时（毫秒） |

**响应**（`AttemptResponse`）：

```json
{
  "is_correct": true,
  "correct_answer": "B",
  "explanation": "点数和为 7 的组合有 (1,6),(2,5),(3,4),(4,3),(5,2),(6,1) 共 6 种..."
}
```

**作答判定逻辑**（详见 [§四](#四作答判定逻辑)）：

---

### 3.6 POST `/api/favorites` — 切换收藏（toggle）

**请求体**（`FavoriteRequest`）：

```json
{
  "device_id": "abc123-def456",
  "question_id": 1
}
```

**响应**（`FavoriteResponse`）：

```json
{
  "favorited": true,
  "question_id": 1
}
```

**语义**：**幂等 toggle** — 已收藏则删除返回 `favorited:false`，未收藏则新增返回 `favorited:true`。受 `favorites` 表唯一约束 `uq_device_question` 保护。

**错误**：404 题目不存在

---

### 3.7 GET `/api/favorites` — 收藏列表

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device_id` | string | 是 | 设备标识 |
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页数量 |

**响应**：`PageResponse<QuestionListItem>`，按 `created_at` 降序（最近收藏在前），仅返回 `status='published'` 题目。

---

### 3.8 GET `/api/sources` — 来源书目列表

**无参数**

**响应**：`list[SourceBrief]`

```json
[
  {"id": 1, "book_title": "Heard on the Street...", "author": "Timothy Falcon Crack"},
  {"id": 2, "book_title": "QuantitativePrimer", "author": "Unknown"},
  {"id": 3, "book_title": "A Practical Guide to Quantitative Finance Interviews", "author": "Xinfeng Zhou"}
]
```

> **注意**：响应只含 `id`/`book_title`/`author`，不含 `edition`/`file_hash`/`notes`。

---

### 3.9 GET `/api/tags` — 标签列表

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 否 | knowledge/position/topic，按类型筛选 |

**响应**：`list[TagBrief]`，按 `type` + `id` 排序

---

## 四、作答判定逻辑

对应代码：`backend/app/api/questions.py` 的 `submit_attempt` 函数。

| 题型 | 判定方式 | `is_correct` | `correct_answer` | `explanation` |
|------|---------|-------------|-----------------|---------------|
| `choice` | 用户答案标签集合 == 正确选项标签集合；答案支持 `"A"` 或 `"A,C"`（中文逗号 `，` 兼容） | `bool` | 正确标签排序拼接（如 `"B"` 或 `"A,C"`） | `solutions[0].content_markdown` |
| `fill` | `answer.strip() == solutions[0].content_markdown.strip()`（去空格精确比对） | `bool` | 参考答案 | 解析 |
| `short` | **不自动判错** | `null` | 参考答案 | 解析 |
| `proof` | **不自动判错** | `null` | 参考答案 | 解析 |

**前端交互建议**：
- choice：点击选项高亮，提交时拼成 `"A,C"` 格式
- fill：单行输入框，提交时 `answer.trim()`
- short/proof：textarea，提交后展示参考答案供自评，不显示"对/错"

---

## 五、is_correct 安全机制

### 当前架构

```
后端 GET /questions/{id}
  └─ 返回 OptionOut（含 is_correct: bool）  ← ⚠️ 正确答案标记
      └─ 前端 api/question.ts getQuestionDetail()
          └─ 剥离 is_correct，返回 SafeQuestionDetail  ← UI 层拿不到答案
              └─ Store / Page / Component（安全）
```

### 安全缺口（TODO）

**后端接口本身仍下发 `is_correct`**。任意用户直接调 `GET /api/questions/{id}` 即可拿到选择题答案，绕过前端剥离。

**建议修复方案**：
1. 新增 `OptionSafe` Schema（去掉 `is_correct` 字段）
2. `QuestionDetail` 响应中 `options` 使用 `OptionSafe` 类型
3. `is_correct` 仅在作答后通过 `AttemptResponse.correct_answer` 返回

**当前状态**：前端已剥离（`SafeQuestionDetail` / `SafeOption` 类型），后端待修复。

---

## 六、数据模型 Schema 速查

### 响应模型

| 模型 | 字段 | 说明 |
|------|------|------|
| `QuestionListItem` | id, stem_markdown, question_type, difficulty, status, book_chapter, source, tags | 列表精简项 |
| `QuestionDetail` | + book_page, options, solutions, updated_at | 详情完整 |
| `OptionOut` | id, label, content_markdown, **is_correct** | 选项（⚠️ 含答案） |
| `SolutionOut` | id, content_markdown, version | 解析 |
| `SourceBrief` | id, book_title, author | 来源简要 |
| `TagBrief` | id, name, type | 标签 |
| `AttemptResponse` | is_correct, correct_answer, explanation | 作答结果 |
| `FavoriteResponse` | favorited, question_id | 收藏结果 |
| `PageResponse<T>` | items, total, page, page_size, total_pages | 分页响应 |

### 请求模型

| 模型 | 字段 | 说明 |
|------|------|------|
| `AttemptRequest` | device_id, answer, duration_ms? | 作答请求 |
| `FavoriteRequest` | device_id, question_id | 收藏请求 |
