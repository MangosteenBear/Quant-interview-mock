# 数据库设计文档

> 量化面试刷题题库平台 — 数据库表结构与关系设计
> 版本：v1.0 | 更新日期：2026-06-29 | 对应代码：`backend/app/models/`

---

## 一、ER 关系图

```mermaid
erDiagram
    sources ||--o{ questions : "1:N source_id"
    sources ||--o{ solutions : "1:N 多版本解析"
    questions ||--o{ options : "1:N CASCADE"
    questions ||--o{ solutions : "1:N CASCADE"
    questions ||--o{ attempt_logs : "1:N CASCADE"
    questions ||--o{ favorites : "1:N CASCADE"
    questions }o--o{ tags : "N:M via question_tags"

    sources {
        int id PK
        string book_title
        string author
        string edition
        string file_hash
        text notes
    }
    questions {
        int id PK
        text stem_markdown
        text stem_latex_normalized
        string question_type
        int difficulty
        string simhash
        int source_id FK
        int book_page
        string book_chapter
        string status
        datetime ingested_at
        datetime updated_at
    }
    options {
        int id PK
        int question_id FK
        string label
        text content_markdown
        bool is_correct
    }
    solutions {
        int id PK
        int question_id FK
        text content_markdown
        int source_id FK
        int version
    }
    tags {
        int id PK
        string name
        string type
    }
    question_tags {
        int question_id PK
        int tag_id PK
    }
    attempt_logs {
        int id PK
        string device_id
        int question_id FK
        text answer
        bool is_correct
        int duration_ms
        datetime created_at
    }
    favorites {
        int id PK
        string device_id
        int question_id FK
        datetime created_at
    }
```

---

## 二、表字段详解

### 2.1 `sources` — 来源书目表

| 字段 | 类型 | 可空 | 默认 | 说明 |
|------|------|------|------|------|
| `id` | Integer | 否 | 自增 | 主键 |
| `book_title` | String(500) | 否 | — | 书名 |
| `author` | String(200) | 是 | — | 作者 |
| `edition` | String(100) | 是 | — | 版次 |
| `file_hash` | String(64) | 是 | — | PDF 文件哈希（去重溯源） |
| `notes` | Text | 是 | — | 备注 |

**关联**：→ questions（1:N）、→ solutions（1:N，多版本解析来源区分）

### 2.2 `questions` — 题目主表

| 字段 | 类型 | 可空 | 默认 | 说明 |
|------|------|------|------|------|
| `id` | Integer | 否 | 自增 | 主键 |
| `stem_markdown` | Text | 否 | — | 题干（Markdown，含 `$...$`/`$$...$$` LaTeX） |
| `stem_latex_normalized` | Text | 是 | — | 归一化文本（去重/搜索索引用，前端不展示） |
| `question_type` | String(20) | 否 | — | 题型：`choice`/`fill`/`short`/`proof` |
| `difficulty` | Integer | 是 | — | 难度 1-5 |
| `simhash` | String(64) | 是 | — | 64 位 SimHash 去重指纹 |
| `source_id` | Integer FK→sources | 是 | — | 来源书目 ID |
| `book_page` | Integer | 是 | — | 原书页码 |
| `book_chapter` | String(200) | 是 | — | 原书章节 |
| `status` | String(20) | 否 | `published` | 状态：`pending`/`reviewing`/`published`/`rejected` |
| `ingested_at` | DateTime | 否 | `now()` | 入库时间 |
| `updated_at` | DateTime | 否 | `now()` | 更新时间（`onupdate=now()`） |

**关联**：→ source（1:1）、→ options（1:N CASCADE，按 label 排序）、→ solutions（1:N CASCADE）、↔ tags（N:M via question_tags）

### 2.3 `options` — 选择题选项表

| 字段 | 类型 | 可空 | 默认 | 说明 |
|------|------|------|------|------|
| `id` | Integer | 否 | 自增 | 主键 |
| `question_id` | Integer FK→questions | 否 | — | 级联删除 `ON DELETE CASCADE` |
| `label` | String(10) | 否 | — | 选项标签：A/B/C/D |
| `content_markdown` | Text | 否 | — | 选项内容（Markdown 含 LaTeX） |
| `is_correct` | Boolean | 否 | `false` | **是否正确选项（⚠️ 后端直接下发，前端 API 层剥离）** |

### 2.4 `solutions` — 解析表（1 题 N 版本）

| 字段 | 类型 | 可空 | 默认 | 说明 |
|------|------|------|------|------|
| `id` | Integer | 否 | 自增 | 主键 |
| `question_id` | Integer FK→questions | 否 | — | 级联删除 `ON DELETE CASCADE` |
| `content_markdown` | Text | 否 | — | 解析内容（Markdown 含 LaTeX） |
| `source_id` | Integer FK→sources | 是 | — | 解析来源（多版本时区分） |
| `version` | Integer | 否 | `1` | 版本号 |

### 2.5 `tags` — 标签表

| 字段 | 类型 | 可空 | 默认 | 说明 |
|------|------|------|------|------|
| `id` | Integer | 否 | 自增 | 主键 |
| `name` | String(100) | 否 | — | 标签名称 |
| `type` | String(20) | 否 | — | 类型：`knowledge`（知识点）/`position`（岗位）/`topic`（主题） |

### 2.6 `question_tags` — 题目-标签关联表（多对多）

| 字段 | 类型 | 说明 |
|------|------|------|
| `question_id` | Integer FK→questions | 复合主键 + 级联删除 |
| `tag_id` | Integer FK→tags | 复合主键 + 级联删除 |

### 2.7 `attempt_logs` — 作答记录表（匿名）

| 字段 | 类型 | 可空 | 默认 | 说明 |
|------|------|------|------|------|
| `id` | Integer | 否 | 自增 | 主键 |
| `device_id` | String(64) | 否 | — | 匿名设备标识 |
| `question_id` | Integer FK→questions | 否 | — | 级联删除 |
| `answer` | Text | 是 | — | 用户作答内容 |
| `is_correct` | Boolean | 是 | — | 是否正确（简答/证明为 `null`） |
| `duration_ms` | Integer | 是 | — | 作答耗时（毫秒） |
| `created_at` | DateTime | 否 | `now()` | 作答时间 |

### 2.8 `favorites` — 收藏表（匿名）

| 字段 | 类型 | 可空 | 默认 | 说明 |
|------|------|------|------|------|
| `id` | Integer | 否 | 自增 | 主键 |
| `device_id` | String(64) | 否 | — | 匿名设备标识 |
| `question_id` | Integer FK→questions | 否 | — | 级联删除 |
| `created_at` | DateTime | 否 | `now()` | 收藏时间 |

**唯一约束**：`uq_device_question(device_id, question_id)` — 防止重复收藏

---

## 三、约束与索引

### 3.1 约束

| 类型 | 表 | 约束名 | 字段 | 说明 |
|------|----|--------|------|------|
| 唯一约束 | favorites | `uq_device_question` | (device_id, question_id) | 防重复收藏 |
| 复合主键 | question_tags | — | (question_id, tag_id) | M2M 关联 |
| 级联删除 | options/solutions/attempt_logs/favorites/question_tags | — | question_id FK | 删题目时级联清理 |

### 3.2 索引（TODO — 生产环境需补）

| 表 | 字段 | 索引类型 | 说明 |
|----|------|---------|------|
| questions | `status` | B-tree | 列表查询默认 `WHERE status='published'` |
| questions | `source_id` | B-tree | 按来源筛选 |
| questions | `simhash` | B-tree | 去重汉明距离查询 |
| questions | `stem_latex_normalized` | GIN (PG FTS) | 全文搜索（生产切 pg_jieba） |

> 当前 SQLite 开发环境仅主键隐式索引，无显式索引。

---

## 四、SQLite ↔ PostgreSQL 切换

| 环境 | DATABASE_URL | 驱动 |
|------|-------------|------|
| 开发 | `sqlite+aiosqlite:///./quantquiz.db` | aiosqlite |
| 生产 | `postgresql+asyncpg://user:pass@host:5432/quantquiz` | asyncpg |

**切换方式**：仅改 `DATABASE_URL` 环境变量（或 `.env` 文件），SQLAlchemy 抽象层自动适配。

**迁移（TODO）**：当前用 `Base.metadata.create_all()` 建表（开发够用），生产环境需引入 **Alembic** 做版本化迁移（`alembic/` 目录尚未创建）。

---

## 五、ORM 加载策略

- **默认 `lazy="selectin"`**：所有 relationship 默认 selectin 预加载，避免 N+1
- **详情页显式预加载**：`selectinload(Question.source, Question.options, Question.solutions, Question.tags)`
- **列表页轻量加载**：仅预加载 `source` + `tags`（不加载 options/solutions，减少数据量）

---

## 六、种子数据

运行 `cd backend && python seed_data.py` 重建数据库并插入：

| 数据 | 数量 | 说明 |
|------|------|------|
| sources | 3 | Heard on the Street / QuantitativePrimer / 绿皮书 |
| tags | 14 | 11 知识点 + 3 岗位 |
| questions | 15 | choice(5) / fill(2) / short(6) / proof(2)，难度 P1-P5 |
| options | 20 | 选择题选项 |
| solutions | 15 | 每题 1 条解析 |
| question_tags | 39 | 题目-标签关联 |
