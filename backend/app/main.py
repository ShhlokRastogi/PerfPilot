import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.runs import router as runs_router
from backend.app.api.config import router as config_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("perfpilot")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing PerfPilot database...")
    await init_db()
    os.makedirs(settings.ARTIFACTS_DIR, exist_ok=True)
    logger.info("PerfPilot backend initialized successfully.")
    yield
    logger.info("Shutting down PerfPilot backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="PerfPilot: AI-Powered Application Performance Engineering Platform for AgentOps 2026",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "sqlite_ready",
        "mock_llm": settings.MOCK_LLM
    }

app.include_router(runs_router)
app.include_router(config_router)
