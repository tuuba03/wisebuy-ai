from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import get_settings
from app.db.database import init_db
from app.api.v1.router import api_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 WiseBuy AI starting up...")
    await init_db()
    logger.success("✅ Database initialized")
    yield
    logger.info("🛑 WiseBuy AI shutting down...")

app = FastAPI(
    title="WiseBuy AI",
    description="Akıllı ürün analiz ve alışveriş asistanı API'si",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "app": "WiseBuy AI", "version": "1.0.0"}
