from fastapi import APIRouter, Query

from backend.execution_engine.execution_models import (
    ExecutionLog,
    ExecutionResult,
    OrderRequest,
    OrderValidationResult,
)
from backend.execution_engine.execution_service import ExecutionService


router = APIRouter(prefix="/execution", tags=["Execution Engine"])
execution_service = ExecutionService()


@router.get("/status")
async def get_execution_engine_status() -> dict:
    return {
        "status": "operational",
        "mode": "SIMULATION_ONLY",
        "real_trading_enabled": False,
    }


@router.post("/validate-order", response_model=OrderValidationResult)
async def validate_order(order: OrderRequest) -> OrderValidationResult:
    return execution_service.validate_order(order)


@router.post("/simulate-order", response_model=ExecutionResult)
async def simulate_order(order: OrderRequest) -> ExecutionResult:
    return execution_service.simulate_order(order)


@router.post("/prepare-mt5-order")
async def prepare_mt5_order(order: OrderRequest) -> dict:
    return execution_service.prepare_mt5_order(order)


@router.get("/logs", response_model=list[ExecutionLog])
async def get_recent_logs(limit: int = Query(default=50, ge=1, le=500)) -> list[ExecutionLog]:
    return execution_service.get_recent_logs(limit)


@router.get("/logs/{execution_id}", response_model=list[ExecutionLog])
async def get_execution_logs(execution_id: str) -> list[ExecutionLog]:
    return execution_service.get_execution_logs(execution_id)

