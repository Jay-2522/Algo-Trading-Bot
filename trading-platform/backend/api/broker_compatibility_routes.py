from fastapi import APIRouter, HTTPException

from backend.broker_compatibility.broker_compatibility_service import BrokerCompatibilityService
from backend.broker_compatibility.broker_models import (
    BrokerCompatibilityResult,
    BrokerDemoReadinessReport,
    SupportedBroker,
)
from backend.broker_compatibility.broker_observation_models import (
    BrokerObservationReport,
    BrokerObservationStatus,
    BrokerSymbolSnapshot,
)
from backend.broker_compatibility.mt5_demo_models import (
    BrokerDemoVerificationReport,
    BrokerSymbolVerification,
    MT5TerminalReadiness,
)


router = APIRouter(prefix="/brokers", tags=["Broker Compatibility"])
broker_compatibility_service = BrokerCompatibilityService()


@router.get("/status")
async def get_broker_compatibility_status() -> dict:
    return broker_compatibility_service.get_status()


@router.get("/mt5/readiness", response_model=MT5TerminalReadiness)
async def get_mt5_demo_readiness() -> MT5TerminalReadiness:
    return broker_compatibility_service.get_mt5_demo_readiness()


@router.get("/verification/all", response_model=list[BrokerDemoVerificationReport])
async def verify_all_broker_symbols() -> list[BrokerDemoVerificationReport]:
    return broker_compatibility_service.verify_all_broker_symbols()


@router.get("/observation/status", response_model=BrokerObservationStatus)
async def get_broker_observation_status() -> BrokerObservationStatus:
    return broker_compatibility_service.get_observation_status()


@router.get("/observation/all", response_model=list[BrokerObservationReport])
async def observe_all_brokers() -> list[BrokerObservationReport]:
    return broker_compatibility_service.observe_all_brokers()


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


@router.get("/{broker_id}/verification", response_model=BrokerDemoVerificationReport)
async def verify_broker_symbols(broker_id: str) -> BrokerDemoVerificationReport:
    if broker_compatibility_service.get_broker(broker_id) is None:
        raise HTTPException(status_code=404, detail="Broker is not supported.")
    return broker_compatibility_service.verify_broker_symbols(broker_id)


@router.get("/{broker_id}/verification/{symbol}", response_model=BrokerSymbolVerification)
async def verify_broker_symbol(broker_id: str, symbol: str) -> BrokerSymbolVerification:
    if broker_compatibility_service.get_broker(broker_id) is None:
        raise HTTPException(status_code=404, detail="Broker is not supported.")
    return broker_compatibility_service.verify_broker_symbol(broker_id, symbol)


@router.get("/{broker_id}/observation", response_model=BrokerObservationReport)
async def observe_broker(broker_id: str) -> BrokerObservationReport:
    if broker_compatibility_service.get_broker(broker_id) is None:
        raise HTTPException(status_code=404, detail="Broker is not supported.")
    return broker_compatibility_service.observe_broker(broker_id)


@router.get("/{broker_id}/observation/{symbol}", response_model=BrokerSymbolSnapshot)
async def observe_broker_symbol(broker_id: str, symbol: str) -> BrokerSymbolSnapshot:
    if broker_compatibility_service.get_broker(broker_id) is None:
        raise HTTPException(status_code=404, detail="Broker is not supported.")
    return broker_compatibility_service.snapshot_broker_symbol(broker_id, symbol)
