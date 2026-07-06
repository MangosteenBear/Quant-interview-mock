import sys
import os

# 让 Vercel serverless 能找到 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app  # noqa: F401 — Vercel ASGI entry point
