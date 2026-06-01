from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.ai_routes import router as ai_router
from backend.api.account_routing_routes import router as account_routing_router
from backend.api.backtesting_routes import router as backtesting_router
from backend.api.broker_compatibility_routes import router as broker_compatibility_router
from backend.api.client_acceptance_routes import router as client_acceptance_router
from backend.api.control_center_routes import router as control_center_router
from backend.api.dashboard_routes import router as dashboard_router
from backend.api.database_routes import router as database_router
from backend.api.demo_execution_routes import router as demo_execution_router
from backend.api.demo_mode_routes import router as demo_mode_router
from backend.api.deployment_routes import router as deployment_router
from backend.api.execution_confirmation_routes import router as execution_confirmation_router
from backend.api.execution_dashboard_routes import router as execution_dashboard_router
from backend.api.execution_risk_routes import router as execution_risk_router
from backend.api.execution_routes import router as execution_router
from backend.api.execution_queue_routes import router as execution_queue_router
from backend.api.institutional_routes import router as institutional_router
from backend.api.market_data_routes import router as market_data_router
from backend.api.monitoring_routes import router as monitoring_router
from backend.api.mt5_routes import router as mt5_router
from backend.api.multi_account_execution_routes import router as multi_account_execution_router
from backend.api.news_routes import router as news_router
from backend.api.operational_intelligence_routes import router as operational_intelligence_router
from backend.api.orchestration_routes import router as orchestration_router
from backend.api.phase3_readiness_routes import router as phase3_readiness_router
from backend.api.portfolio_routes import router as portfolio_router
from backend.api.risk_routes import router as risk_router
from backend.api.replay_routes import router as replay_router
from backend.api.strategy_routes import router as strategy_router
from backend.api.strategy_execution_bridge_routes import router as strategy_execution_bridge_router
from backend.api.streaming_routes import router as streaming_router
from backend.api.streaming_routes import websocket_router as streaming_websocket_router
from backend.api.system_health_routes import router as system_health_router
from backend.api.trade_copier_routes import router as trade_copier_router
from backend.api.tradingview_webhook_routes import router as tradingview_webhook_router
from backend.api.trading_loop_routes import router as trading_loop_router
from backend.api.trading_loop_routes import trading_loop_service
from backend.api.trade_journal_routes import router as trade_journal_router
from backend.config.settings import get_settings
from backend.utils.logger import get_logger


settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Structured application lifecycle hooks."""

    logger.info("Starting %s in %s environment", settings.app_name, settings.environment)
    yield
    if trading_loop_service.get_status().running:
        await trading_loop_service.stop_loop()
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
app.include_router(account_routing_router)
app.include_router(client_acceptance_router)
app.include_router(control_center_router)
app.include_router(dashboard_router)
app.include_router(demo_execution_router)
app.include_router(demo_mode_router)
app.include_router(deployment_router)
app.include_router(execution_confirmation_router)
app.include_router(execution_dashboard_router)
app.include_router(execution_risk_router)
app.include_router(strategy_router)
app.include_router(strategy_execution_bridge_router)
app.include_router(risk_router)
app.include_router(execution_router)
app.include_router(execution_queue_router)
app.include_router(mt5_router)
app.include_router(multi_account_execution_router)
app.include_router(trade_copier_router)
app.include_router(monitoring_router)
app.include_router(database_router)
app.include_router(ai_router)
app.include_router(news_router)
app.include_router(operational_intelligence_router)
app.include_router(orchestration_router)
app.include_router(phase3_readiness_router)
app.include_router(portfolio_router)
app.include_router(backtesting_router)
app.include_router(replay_router)
app.include_router(broker_compatibility_router)
app.include_router(tradingview_webhook_router)
app.include_router(streaming_router)
app.include_router(streaming_websocket_router)
app.include_router(trading_loop_router)
app.include_router(trade_journal_router)
app.include_router(system_health_router)
app.include_router(institutional_router)


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
