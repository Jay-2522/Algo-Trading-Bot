from fastapi import APIRouter, HTTPException, Query

from backend.database.db_health import DatabaseHealthService
from backend.database.persistence_service import PersistenceService


router = APIRouter(prefix="/database", tags=["Database Persistence"])


def _service() -> PersistenceService:
    service = PersistenceService()
    if not service.initialize_database():
        service.close()
        raise HTTPException(status_code=503, detail="Database initialization is unavailable.")
    return service


@router.get("/status")
async def get_database_status() -> dict:
    return DatabaseHealthService().get_database_status()


@router.post("/init")
async def initialize_database() -> dict:
    service = PersistenceService()
    try:
        initialized = service.initialize_database()
        if not initialized:
            raise HTTPException(status_code=503, detail="Database initialization failed.")
        return {"initialized": True, "message": "Database tables initialized."}
    finally:
        service.close()


@router.get("/trades/recent")
async def get_recent_trades(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = _service()
    try:
        return service.get_recent_trades(limit)
    finally:
        service.close()


@router.get("/execution-logs/recent")
async def get_recent_execution_logs(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = _service()
    try:
        return service.get_recent_execution_logs(limit)
    finally:
        service.close()


@router.get("/risk-events/recent")
async def get_recent_risk_events(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = _service()
    try:
        return service.get_recent_risk_events(limit)
    finally:
        service.close()


@router.get("/strategy-snapshots/recent")
async def get_recent_strategy_snapshots(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = _service()
    try:
        return service.get_recent_strategy_snapshots(limit)
    finally:
        service.close()


@router.get("/market-snapshots/recent")
async def get_recent_market_snapshots(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = _service()
    try:
        return service.get_recent_market_snapshots(limit)
    finally:
        service.close()


@router.get("/audit-logs/recent")
async def get_recent_audit_logs(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = _service()
    try:
        return service.get_recent_audit_logs(limit)
    finally:
        service.close()


@router.post("/audit-logs/test")
async def create_test_audit_log() -> dict:
    service = _service()
    try:
        return service.save_audit_log(
            {
                "component": "database.api",
                "event_type": "TEST_AUDIT",
                "message": "Persistence API test audit log.",
                "severity": "INFO",
                "metadata_json": {"development_test": True},
            }
        )
    finally:
        service.close()


@router.post("/market-snapshots/test")
async def create_test_market_snapshot() -> dict:
    service = _service()
    try:
        return service.save_market_snapshot(
            {
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "bid": 0.0,
                "ask": 0.0,
                "spread": 0.0,
                "last_price": 0.0,
                "metadata_json": {"development_test": True},
            }
        )
    finally:
        service.close()

