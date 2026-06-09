from fastapi import APIRouter, Body, HTTPException

from backend.brokers.broker_account_service import BrokerAccountService
from backend.brokers.multi_account_execution_planner import MultiAccountExecutionPlanner


router = APIRouter(prefix="/brokers", tags=["Broker Account Layer"])
broker_account_service = BrokerAccountService()
execution_planner = MultiAccountExecutionPlanner(account_service=broker_account_service)


@router.get("/status")
async def get_broker_account_layer_status() -> dict:
    return broker_account_service.get_status()


@router.get("/accounts")
async def list_broker_accounts() -> dict:
    return {
        "status": "READY",
        "accounts": [account.model_dump(mode="json") for account in broker_account_service.list_accounts()],
        "current_terminal_account": broker_account_service.current_terminal_account().model_dump(mode="json"),
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }


@router.post("/accounts/sync")
async def sync_broker_accounts() -> dict:
    return broker_account_service.sync_accounts()


@router.get("/accounts/{broker_id}")
async def get_broker_account(broker_id: str) -> dict:
    try:
        account = broker_account_service.get_account_status(broker_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Broker account is not registered.") from exc
    return account.model_dump(mode="json")


@router.get("/readiness")
async def get_broker_account_readiness() -> dict:
    return broker_account_service.readiness()


@router.get("/copy-readiness")
async def get_broker_copy_readiness() -> dict:
    return execution_planner.copy_readiness()


@router.post("/execution-plan/preview")
async def preview_multi_account_execution_plan(payload: dict = Body(default_factory=dict)) -> dict:
    return execution_planner.preview(payload)


@router.get("/execution-plan/status")
async def get_multi_account_execution_plan_status() -> dict:
    return execution_planner.status()
