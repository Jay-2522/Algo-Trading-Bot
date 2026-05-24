from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.market_data_routes import router as market_data_router
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


def register_middleware(fastapi_app: FastAPI) -> None:
    """Register application middleware in one place."""

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_routes(fastapi_app: FastAPI) -> None:
    """Register all API routers and core routes on the same app instance."""

    fastapi_app.include_router(market_data_router)
    fastapi_app.include_router(strategy_router)

    @fastapi_app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "healthy", "service": settings.app_name}

    @fastapi_app.get("/status")
    async def status() -> Dict[str, str]:
        return {
            "status": "running",
            "environment": settings.environment,
            "service": settings.app_name,
            "version": fastapi_app.version,
        }


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    fastapi_app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Foundation for an AI-assisted algorithmic trading platform.",
        lifespan=lifespan,
    )
    register_middleware(fastapi_app)
    register_routes(fastapi_app)
    return fastapi_app


app = create_app()


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

