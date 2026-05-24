from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config.settings import get_settings
from backend.utils.logger import get_logger


settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Structured application lifecycle hooks."""

    logger.info("Starting %s in %s environment", settings.app_name, settings.environment)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Day 1 foundation for an AI-assisted algorithmic trading platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Centralized error response structure for future observability hooks."""

    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "path": request.url.path,
        },
    )


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy", "service": settings.app_name}


@app.get("/status")
async def status() -> Dict[str, Any]:
    return {
        "status": "online",
        "environment": settings.environment,
        "modules": {
            "strategy_engine": "foundation_ready",
            "execution_engine": "foundation_ready",
            "ai_engine": "foundation_ready",
            "risk_engine": "foundation_ready",
            "news_engine": "foundation_ready",
            "analytics": "foundation_ready",
            "broker_integrations": "foundation_ready",
            "database": "foundation_ready",
            "websocket": "foundation_ready",
        },
    }

