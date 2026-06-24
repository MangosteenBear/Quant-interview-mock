# 量化面试刷题题库平台

> 面向量化岗求职者的轻量化刷题工具，Web + 微信小程序双形态，移动端优先。

## 项目结构

```
├── backend/          # 后端 API（FastAPI + SQLAlchemy + SQLite/PostgreSQL）
│   ├── app/
│   │   ├── api/      # 路由模块（题目/收藏/来源/标签）
│   │   ├── models/   # SQLAlchemy 数据模型（8张表）
│   │   ├── schemas/  # Pydantic 请求/响应模型
│   │   ├── config.py # 配置
│   │   ├── database.py # 异步引擎与会话
│   │   └── main.py   # FastAPI 入口
│   ├── seed_data.py  # 种子数据（15道量化样题）
│   └── requirements.txt
├── frontend/         # 前端（uni-app Vue3 + Vite + TS）
│   ├── src/
│   │   ├── api/      # HTTP 请求封装
│   │   ├── components/ # 组件（FormulaText公式渲染等）
│   │   ├── pages/    # 6个页面（首页/列表/详情/搜索/收藏/设置）
│   │   ├── stores/   # Pinia 状态管理
│   │   ├── types/    # TS 类型定义
│   │   └── utils/    # 工具（markdown渲染/难度色阶/device_id）
│   └── vite.config.ts # 含 /api 代理到后端8000
├── pipeline/         # PDF数据处理流水线脚手架（Python CLI）
│   ├── cli.py        # CLI入口（render/ocr/split/link/dedup/ingest）
│   └── requirements.txt
└── docs/
    └── product-design.md  # 产品设计文档（PRD）
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | uni-app (Vue3 + Vite + TS) + Pinia + KaTeX |
| 后端 | Python FastAPI + SQLAlchemy 2.0 (async) |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| OCR | PaddleOCR（PP-OCRv4 + PP-FormulaNet-S，待集成） |

## 快速开始

### 后端
```bash
cd backend
pip install -r requirements.txt
python seed_data.py                          # 建表 + 15道种子题
uvicorn app.main:app --reload --port 8000    # 启动服务
# API文档: http://localhost:8000/docs
```

### 前端
```bash
cd frontend
pnpm install
NODE_OPTIONS="" pnpm dev:h5                  # 启动H5开发服务器
# 浏览器: http://localhost:5173
```

### 数据流水线
```bash
cd /workspace
python -m pipeline --help                    # 查看CLI命令
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

## 项目阶段

- **一期（当前）**：PDF数据入库 + 基础刷题前端 + 核心刷题功能
- **二期**：公开平台爬虫拓展 + 账号体系 + 错题本 + 模考模式
- **长期**：完整量化面试题库生态
