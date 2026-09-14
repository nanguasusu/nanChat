"""FastAPI 应用入口：注册生命周期、跨域设置和业务路由。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.clients import close_clients
from app.core.config import get_cors_origins
from app.core.database import init_database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时初始化数据库，关闭时释放外部客户端。"""
    await init_database()
    yield
    await close_clients()


# 创建 FastAPI 应用，并绑定生命周期钩子
app = FastAPI(title="AI Chat API", version="0.1.0", lifespan=lifespan)

# 配置 CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载业务路由
app.include_router(router)
