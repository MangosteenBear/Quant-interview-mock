# 量化面试刷题题库平台 - 后端

## 技术栈
- **FastAPI** + **SQLAlchemy 2.0 (async)** + **Pydantic v2**
- 开发数据库：SQLite (aiosqlite)，零配置
- 生产数据库：PostgreSQL (asyncpg)，切换 `DATABASE_URL` 即可

## 快速开始

```bash
# 1. 安装依赖
cd backend
sudo pip3 install -r requirements.txt

# 2. 初始化数据库 + 种子数据
python seed_data.py

# 3. 启动服务
uvicorn app.main:app --reload --port 8000

# 4. 访问 API 文档
# 浏览器打开 http://localhost:8000/docs
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/questions` | 题目列表（分页、筛选） |
| GET | `/api/questions/{id}` | 题目详情 |
| GET | `/api/questions/search/all` | 关键词���索 |
| POST | `/api/questions/{id}/attempt` | 提交作答 |
| POST | `/api/favorites` | 切换收藏 |
| GET | `/api/favorites` | 收藏列表 |
| GET | `/api/sources` | 来源书目 |
| GET | `/api/tags` | 标签列表 |

## 项目结构

```
backend/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 配置（环境变量）
│   ├── database.py      # 异步引擎 + 会话
│   ├── models/          # SQLAlchemy 模型（8张表）
│   ├── schemas/         # Pydantic 请求/响应模型
│   └── api/             # 路由模块
├── seed_data.py         # 种子数据脚本
├── requirements.txt
└── README.md
```

## 数据库切换

开发用 SQLite，生产切 PostgreSQL，修改环境变量即可：

```bash
# 开发
DATABASE_URL=sqlite+aiosqlite:///./quantquiz.db

# 生产
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/quantquiz
```

## 数据模型

详见 `/workspace/docs/product-design.md` §3.3

共 8 张表：sources / questions / options / solutions / tags / question_tags / attempt_logs / favorites
