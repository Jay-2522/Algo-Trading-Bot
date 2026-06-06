from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService


router = APIRouter(prefix="/trade-journal/persistence", tags=["Persistent Trade Journal"])
persistent_trade_journal_service = PersistentTradeJournalService()


@router.get("/status")
async def get_persistent_trade_journal_status() -> dict[str, Any]:
    return persistent_trade_journal_service.get_status()


@router.post("/planned")
async def create_planned_trade(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    return persistent_trade_journal_service.create_planned_trade(payload)


@router.post("/order-sent")
async def record_order_sent(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    return persistent_trade_journal_service.record_order_sent(payload)


@router.post("/order-rejected")
async def record_order_rejected(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    return persistent_trade_journal_service.record_order_rejected(payload)


@router.post("/trade-opened")
async def record_trade_opened(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    return persistent_trade_journal_service.record_trade_opened(payload)


@router.post("/trade-closed")
async def record_trade_closed(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    return persistent_trade_journal_service.record_trade_closed(payload)


@router.get("/recent")
async def get_recent_persistent_trades(limit: int = Query(default=20, ge=1, le=500)) -> list[dict[str, Any]]:
    return persistent_trade_journal_service.get_recent_trades(limit)


@router.get("/summary")
async def get_persistent_trade_journal_summary() -> dict[str, Any]:
    return persistent_trade_journal_service.get_summary()


@router.get("/{trade_id}")
async def get_persistent_trade(trade_id: str) -> dict[str, Any]:
    trade = persistent_trade_journal_service.get_trade(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Persistent trade journal record not found.")
    return trade
