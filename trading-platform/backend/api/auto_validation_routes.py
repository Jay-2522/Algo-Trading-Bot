import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body

from backend.api.client_signal_engine_routes import client_signal_engine
from backend.api.mt5_demo_routes import (
    guarded_demo_order_sender_service,
    historical_backfill_service,
    market_data_service,
    mt5_position_monitoring_service,
    mt5_trade_close_sync_service,
    mt5_trade_lifecycle_service,
    service as mt5_demo_service,
    vantage_xauusd_demo_validation_service,
)
from backend.api.trade_journal_persistence_routes import persistent_trade_journal_service
from backend.auto_validation.auto_validation_runner import AutoValidationRunner
from backend.auto_validation.exit_management_service import AutoValidationExitManagementService
from backend.auto_validation.auto_validation_service import AutoValidationService


router = APIRouter(prefix="/auto-validation", tags=["AUTO Demo Validation"])
exit_management_service = AutoValidationExitManagementService(
    signal_provider=client_signal_engine,
    market_data_service=market_data_service,
    guarded_sender_service=guarded_demo_order_sender_service,
    journal_service=persistent_trade_journal_service,
)
auto_validation_service = AutoValidationService(
    signal_provider=client_signal_engine,
    guarded_execution_service=vantage_xauusd_demo_validation_service,
    journal_service=persistent_trade_journal_service,
    position_service=mt5_position_monitoring_service,
    mt5_demo_service=mt5_demo_service,
    history_backfill_service=historical_backfill_service,
    lifecycle_service=mt5_trade_lifecycle_service,
    close_sync_service=mt5_trade_close_sync_service,
    exit_management_service=exit_management_service,
)
auto_validation_runner = AutoValidationRunner(auto_validation_service)


@router.get("/status")
async def get_auto_validation_status() -> dict:
    if auto_validation_service.should_auto_start_runner() and not auto_validation_runner.is_active():
        auto_validation_service.log_scan_loop_restarted("status requested while validation/exit loop should be active")
        auto_validation_runner.start()
    return await asyncio.to_thread(auto_validation_service.status)


@router.post("/start")
async def start_auto_validation(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    result = await asyncio.to_thread(auto_validation_service.start, payload)
    if result.get("status") not in {"SESSION_ALREADY_STARTED", "FRESH_START_CONFIRMATION_REQUIRED"}:
        auto_validation_runner.start()
        return await asyncio.to_thread(auto_validation_service.status)
    return result


@router.post("/pause")
async def pause_auto_validation() -> dict:
    result = await asyncio.to_thread(auto_validation_service.pause)
    auto_validation_runner.stop()
    result["runner_active"] = False
    result["scan_loop_running"] = False
    return result


@router.post("/resume")
async def resume_auto_validation(background_tasks: BackgroundTasks) -> dict:
    result = await asyncio.to_thread(auto_validation_service.resume)
    if result.get("status") == "RESUME_BLOCKED" or result.get("can_resume") is False:
        return result
    auto_validation_runner.start()
    background_tasks.add_task(auto_validation_service.run_background_resume_sync)
    result["runner_active"] = auto_validation_runner.is_active()
    result["scan_loop_running"] = auto_validation_runner.is_active()
    return result


@router.get("/pause-check")
async def get_auto_validation_pause_check() -> dict:
    return await asyncio.to_thread(auto_validation_service.pause_check)


@router.get("/resume-check")
async def get_auto_validation_resume_check() -> dict:
    return await asyncio.to_thread(auto_validation_service.resume_check, refresh_mt5=False)


@router.get("/runtime-status")
async def get_auto_validation_runtime_status() -> dict:
    return await asyncio.to_thread(auto_validation_service.runtime_status)


@router.post("/stop")
async def stop_auto_validation(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    result = await asyncio.to_thread(auto_validation_service.stop, str(payload.get("reason") or "Stopped manually."))
    auto_validation_runner.stop()
    return await asyncio.to_thread(auto_validation_service.status)


@router.post("/emergency-stop")
async def emergency_stop_auto_validation() -> dict:
    result = auto_validation_service.emergency_stop()
    auto_validation_runner.stop()
    return auto_validation_service.status()


@router.post("/reset-open-trades")
async def reset_auto_validation_open_trades() -> dict:
    return auto_validation_service.reset_active_open_trades()


@router.post("/reset-closed-trades")
async def reset_auto_validation_closed_trades() -> dict:
    return auto_validation_service.reset_active_closed_trades()


@router.get("/trades")
async def get_auto_validation_trades() -> list[dict]:
    return auto_validation_service.trades()


@router.get("/summary")
async def get_auto_validation_summary() -> dict:
    return auto_validation_service.summary()


@router.get("/read-only-scan")
async def run_auto_validation_read_only_scan() -> dict:
    return auto_validation_service.read_only_scan()


@router.get("/read-only-scan/{symbol}")
async def run_auto_validation_symbol_read_only_scan(symbol: str) -> dict:
    normalized_symbol = str(symbol or "").upper()
    timeout_seconds = 12
    try:
        return await asyncio.wait_for(asyncio.to_thread(auto_validation_service.read_only_scan_symbol, normalized_symbol), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        diagnostic = auto_validation_service.record_scan_timeout_warning(normalized_symbol, timeout_seconds * 1000)
        return {
            "status": "SCAN_TIMEOUT_WARNING",
            "symbol": normalized_symbol,
            "active_session_id": auto_validation_service.session.get("session_id"),
            "diagnostic": diagnostic,
            "read_only": True,
            "order_sent": False,
            "timestamp": diagnostic.get("timestamp"),
        }


@router.get("/scan-diagnostics")
async def get_auto_validation_scan_diagnostics() -> dict:
    if auto_validation_service.should_auto_start_runner() and not auto_validation_runner.is_active():
        auto_validation_service.log_scan_loop_restarted("scan diagnostics requested while validation running but loop was inactive")
        auto_validation_runner.start()
    return await asyncio.to_thread(auto_validation_service.scan_diagnostics_status)


@router.get("/scan-health")
async def get_auto_validation_scan_health() -> dict:
    if auto_validation_service.should_auto_start_runner() and not auto_validation_runner.is_active():
        auto_validation_service.log_scan_loop_restarted("validation running but scan loop was inactive")
        auto_validation_runner.start()
    health = await asyncio.to_thread(auto_validation_service.scan_health)
    if health.get("stale") is True and auto_validation_service.should_auto_start_runner() and not auto_validation_runner.is_active():
        auto_validation_service.log_scan_loop_restarted("stale scan while validation running")
        auto_validation_runner.start()
        health = await asyncio.to_thread(auto_validation_service.scan_health)
    return health


@router.post("/sync-lifecycle")
async def sync_auto_validation_lifecycle() -> dict:
    return auto_validation_service.sync_lifecycle()


@router.post("/run-exit-management")
async def run_auto_validation_exit_management() -> dict:
    return await asyncio.to_thread(auto_validation_service.run_exit_management)


@router.get("/open-trade-exit-diagnostics")
async def get_auto_validation_open_trade_exit_diagnostics() -> dict:
    if auto_validation_service.should_auto_start_runner() and not auto_validation_runner.is_active():
        auto_validation_service.log_scan_loop_restarted("exit diagnostics requested while exit loop should be active")
        auto_validation_runner.start()
    return await asyncio.to_thread(auto_validation_service.open_trade_exit_diagnostics)


@router.get("/post-sender-execution-summary")
async def get_auto_validation_post_sender_execution_summary() -> dict:
    return auto_validation_service.post_sender_execution_summary()


@router.get("/events")
async def get_auto_validation_events(limit: int = 100) -> list[dict]:
    return auto_validation_service.events[-max(1, min(limit, 500)) :]
