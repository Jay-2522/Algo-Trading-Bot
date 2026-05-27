from typing import Any

from fastapi import APIRouter, Body, HTTPException

from backend.account_routing.account_models import AccountRoutingDecision, AccountRoutingPolicy, BrokerAccountProfile
from backend.account_routing.account_routing_service import AccountRoutingService


router = APIRouter(prefix="/accounts", tags=["Account Routing"])
account_routing_service = AccountRoutingService()


@router.get("/status")
async def get_account_routing_status() -> dict:
    return account_routing_service.get_status()


@router.get("", response_model=list[BrokerAccountProfile])
async def list_accounts() -> list[BrokerAccountProfile]:
    return account_routing_service.list_accounts()


@router.get("/groups", response_model=dict[str, list[BrokerAccountProfile]])
async def list_account_groups() -> dict[str, list[BrokerAccountProfile]]:
    return account_routing_service.list_groups()


@router.get("/policy/default", response_model=AccountRoutingPolicy)
async def get_default_account_routing_policy() -> AccountRoutingPolicy:
    return account_routing_service.get_default_policy()


@router.post("/route-preview", response_model=AccountRoutingDecision)
async def preview_account_route(signal_payload: dict[str, Any] = Body(default_factory=dict)) -> AccountRoutingDecision:
    return account_routing_service.preview_route(signal_payload)


@router.get("/{account_id}", response_model=BrokerAccountProfile)
async def get_account(account_id: str) -> BrokerAccountProfile:
    account = account_routing_service.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account profile not found.")
    return account
