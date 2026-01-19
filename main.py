import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from __init__ import SERVICE_NAME, VERSION
from api.routers import health_router, query_router, chat_router
from api.services import session_manager

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename=None,
    encoding="utf-8",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時
    logger.info("Starting session cleanup task...")
    await session_manager.start_cleanup_task(interval_minutes=5)
    yield
    # 關閉時
    logger.info("Shutting down session manager...")
    await session_manager.shutdown()


app = FastAPI(title=SERVICE_NAME, version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(query_router)
app.include_router(chat_router)
