from fastapi import APIRouter, Body, HTTPException, Query

from backend.trade_journal.journal_models import (
    ExposureStatus,
    JournalEntry,
    RiskAlert,
    RiskAnalytics,
    SessionPerformance,
    SymbolPerformance,
)
from backend.trade_journal.journal_service import JournalService


router = APIRouter(prefix="/trade-journal", tags=["Trade Journal & Risk Analytics"])
journal_service = JournalService()


@router.get("/status")
async def get_trade_journal_status() -> dict:
    return {
        "status": "operational",
        "mode": "SIMULATION_ANALYTICS_ONLY",
        "live_execution_enabled": False,
        "journal_entries_supported": True,
        "risk_alerts_enabled": True,
    }


@router.post("/add-test-entry", response_model=JournalEntry)
async def add_test_entry(entry: JournalEntry | None = Body(default=None)) -> JournalEntry:
    if entry is None:
        raise HTTPException(status_code=400, detail="Explicit journal entry payload required. No default demo trade is generated.")
    try:
        return journal_service.add_entry(entry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recent", response_model=list[JournalEntry])
async def get_recent_entries(limit: int = Query(default=50, ge=1, le=500)) -> list[JournalEntry]:
    return journal_service.get_recent_entries(limit)


@router.get("/symbol-performance/{symbol}", response_model=SymbolPerformance)
async def get_symbol_performance(symbol: str) -> SymbolPerformance:
    return journal_service.get_symbol_performance(symbol)


@router.get("/session-performance/{session}", response_model=SessionPerformance)
async def get_session_performance(session: str) -> SessionPerformance:
    return journal_service.get_session_performance(session)


@router.get("/risk-analytics", response_model=RiskAnalytics)
async def get_risk_analytics() -> RiskAnalytics:
    return journal_service.get_risk_analytics()


@router.get("/exposure", response_model=ExposureStatus)
async def get_exposure() -> ExposureStatus:
    return journal_service.get_exposure()


@router.get("/risk-alerts", response_model=list[RiskAlert])
async def get_risk_alerts() -> list[RiskAlert]:
    return journal_service.get_risk_alerts()


@router.get("/overall-performance")
async def get_overall_performance() -> dict:
    return journal_service.get_overall_performance()
