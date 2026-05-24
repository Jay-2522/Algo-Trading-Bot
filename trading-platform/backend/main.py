from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.ai_routes import router as ai_router
from backend.api.database_routes import router as database_router
from backend.api.execution_routes import router as execution_router
from backend.api.market_data_routes import router as market_data_router
from backend.api.mt5_routes import router as mt5_router
from backend.api.news_routes import router as news_router
from backend.api.risk_routes import router as risk_router
from backend.api.strategy_routes import router as strategy_router
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
    version="1.0.0",
    description="Foundation for an AI-assisted algorithmic trading platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": settings.app_name}


@app.get("/status")
async def system_status() -> Dict[str, str]:
    return {
        "status": "running",
        "environment": settings.environment,
        "service": settings.app_name,
        "version": app.version,
    }


app.include_router(market_data_router)
app.include_router(strategy_router)
app.include_router(risk_router)
app.include_router(execution_router)
app.include_router(mt5_router)
app.include_router(database_router)
app.include_router(ai_router)
app.include_router(news_router)


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
