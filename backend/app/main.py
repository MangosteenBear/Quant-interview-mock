"""
FastAPI 应用入口
量化面试刷题题库平台 - 后端 API
启动: uvicorn app.main:app --reload --port 8000
文档: http://localhost:8000/docs
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings

# 日志配置
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "面向量化岗求职者的刷题平台 API。\n\n"
        "## 功能\n"
        "- 题目浏览/搜索/作答\n"
        "- 收藏管理\n"
        "- 来源与标签查询\n\n"
        "## 说明\n"
        "- 一期匿名模式（device_id 维度）\n"
        "- 开发环境 SQLite，生产 PostgreSQL"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 全局异常处理 ----------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "detail": str(exc) if settings.DEBUG else None},
    )


# ---------- 健康检查 ----------
@app.get("/api/health", tags=["系统"], summary="健康检查")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# ---------- 挂载业务路由 ----------
from app.api.questions import router as questions_router  # noqa: E402
from app.api.favorites import router as favorites_router  # noqa: E402
from app.api.sources import router as sources_router  # noqa: E402
from app.api.tags import router as tags_router  # noqa: E402

app.include_router(questions_router)
app.include_router(favorites_router)
app.include_router(sources_router)
app.include_router(tags_router)


@app.on_event("startup")
async def startup():
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info(f"数据库: {settings.DATABASE_URL}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
