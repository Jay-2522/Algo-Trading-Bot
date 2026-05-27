from fastapi import APIRouter, HTTPException

from backend.broker_compatibility.broker_compatibility_service import BrokerCompatibilityService
from backend.broker_compatibility.broker_models import (
    BrokerCompatibilityResult,
    BrokerDemoReadinessReport,
    SupportedBroker,
)


router = APIRouter(prefix="/brokers", tags=["Broker Compatibility"])
broker_compatibility_service = BrokerCompatibilityService()


@router.get("/status")
async def get_broker_compatibility_status() -> dict:
    return broker_compatibility_service.get_status()


@router.get("", response_model=list[SupportedBroker])
async def list_supported_brokers() -> list[SupportedBroker]:
    return broker_compatibility_service.list_brokers()


@router.get("/{broker_id}", response_model=SupportedBroker)
async def get_supported_broker(broker_id: str) -> SupportedBroker:
    broker = broker_compatibility_service.get_broker(broker_id)
    if broker is None:
        raise HTTPException(status_code=404, detail="Broker is not supported.")
    return broker


@router.get("/{broker_id}/symbols", response_model=list[BrokerCompatibilityResult])
async def get_broker_symbol_support(broker_id: str) -> list[BrokerCompatibilityResult]:
    if broker_compatibility_service.get_broker(broker_id) is None:
        raise HTTPException(status_code=404, detail="Broker is not supported.")
    return broker_compatibility_service.check_broker_all_symbols(broker_id)


@router.get("/{broker_id}/symbols/{symbol}", response_model=BrokerCompatibilityResult)
async def get_broker_symbol_mapping(broker_id: str, symbol: str) -> BrokerCompatibilityResult:
    if broker_compatibility_service.get_broker(broker_id) is None:
        raise HTTPException(status_code=404, detail="Broker is not supported.")
    return broker_compatibility_service.check_broker_symbol(broker_id, symbol)


@router.get("/{broker_id}/demo-readiness", response_model=BrokerDemoReadinessReport)
async def get_broker_demo_readiness(broker_id: str) -> BrokerDemoReadinessReport:
    if broker_compatibility_service.get_broker(broker_id) is None:
        raise HTTPException(status_code=404, detail="Broker is not supported.")
    return broker_compatibility_service.check_demo_readiness(broker_id)
