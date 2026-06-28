# 量化面试刷题题库平台

> 面向量化岗求职者的轻量化刷题工具，Web + 微信小程序双形态，移动端优先。

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 产品设计（PRD） | [docs/product-design.md](docs/product-design.md) | 产品定位、技术选型、流水线设计、MVP 范围、路线图 |
| 系统架构 | [docs/architecture.md](docs/architecture.md) | 架构图、技术栈、前后端分层、双端适配、已知缺口 |
| API 参考 | [docs/api-reference.md](docs/api-reference.md) | 9 端点完整文档、作答判定、is_correct 安全机制 |
| 数据库设计 | [docs/database-design.md](docs/database-design.md) | 8 表字段、ER 图、约束索引、DB 切换 |
| 后端 README | [backend/README.md](backend/README.md) | 后端快速开始、结构 |
| 前端 README | [frontend/README.md](frontend/README.md) | 前端快速开始、页面/组件/Store |
| 流水线 README | [pipeline/README.md](pipeline/README.md) | CLI 命令、TODO 进度、实现路线 |

## 项目结构

```
├── backend/              # 后端 API（FastAPI + SQLAlchemy async）
│   ├── app/
│   │   ├── api/          # 路由（questions/favorites/sources/tags）
│   │   ├── models/       # SQLAlchemy 模型（8 张表）
│   │   ├── schemas/      # Pydantic 请求/响应模型
│   │   ├── config.py     # 配置（pydantic-settings）
│   │   ├── database.py   # 异步引擎与会话
│   │   └── main.py       # FastAPI 入口
│   ├── seed_data.py      # 种子数据（15 道量化样题）
│   └── requirements.txt
├── frontend/             # 前端（uni-app Vue3 + Vite + TS）
│   ├── src/
│   │   ├── api/          # HTTP 请求封装（uni.request 双端通用）
│   │   ├── components/   # 组件（FormulaText 公式渲染等）
│   │   ├── pages/        # 6 页面（首页/列表/详情/搜索/收藏/设置）
│   │   ├── stores/       # Pinia 状态管理（3 个 store）
│   │   ├── types/        # TS 类型定义
│   │   └── utils/        # 工具（markdown 渲染/难度色阶/device_id）
│   └── vite.config.ts    # /api 代理到后端 :8000
├── pipeline/             # PDF 数据流水线 CLI（脚手架阶段）
│   ├── cli.py            # CLI 入口（render/ocr/split/link/dedup/ingest）
│   └── requirements.txt
└── docs/
    ├── product-design.md     # PRD
    ├── architecture.md       # 架构文档
    ├── api-reference.md      # API 参考
    └── database-design.md    # 数据库设计
```

## 技术栈

| 层 | 技术 | 状态 |
|----|------|------|
| 前端 | uni-app (Vue3 + Vite + TS) + Pinia + KaTeX | ✅ 已集成 |
| 后端 | Python FastAPI + SQLAlchemy 2.0 (async) | ✅ 已集成 |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） | ✅ SQLite / ⏳ PG 待切换 |
| OCR | PaddleOCR（PP-OCRv4 + PP-FormulaNet-S） | ⏳ 待集成 |
| 部署 | Docker Compose + Nginx | ⏳ 待集成 |

## 快速开始

### 后端
```bash
cd backend
pip install -r requirements.txt
python seed_data.py                          # 建表 + 15 道种子题
uvicorn app.main:app --reload --port 8000    # 启动服务
# API 文档: http://localhost:8000/docs
```

### 前端
```bash
cd frontend
pnpm install
NODE_OPTIONS="" pnpm dev:h5                  # 启动 H5 开发服务器
# 浏览器: http://localhost:5173
```

### 数据流水线
```bash
cd /workspace
python -m pipeline --help                    # 查看 CLI 命令
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/questions` | 题目列表（分页+筛选） |
| GET | `/api/questions/{id}` | 题目详情 |
| GET | `/api/questions/search/all` | 关键词搜索 |
| POST | `/api/questions/{id}/attempt` | 提交作答 |
| POST | `/api/favorites` | 切换收藏 |
| GET | `/api/favorites` | 收藏列表 |
| GET | `/api/sources` | 来源书目 |
| GET | `/api/tags` | 标签列表 |

> 完整请求/响应示例详见 [API 参考文档](docs/api-reference.md)

## 项目阶段

- **一期（当前）**：PDF 数据入库 + 基础刷题前端 + 核心刷题功能
- **二期**：公开平台爬虫拓展 + 账号体系 + 错题本 + 模考模式
- **长期**：完整量化面试题库生态
