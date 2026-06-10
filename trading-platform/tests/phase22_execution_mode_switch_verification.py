import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SERVICE_PATH = PROJECT_ROOT / "backend/execution_mode/execution_mode_service.py"
ROUTES_PATH = PROJECT_ROOT / "backend/api/execution_mode_routes.py"
MAIN_PATH = PROJECT_ROOT / "backend/main.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"
GUARDED_PATH = PROJECT_ROOT / "backend/mt5_demo/guarded_demo_order_sender_service.py"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def ready_signal(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    signal = {
        "symbol": "EURUSD",
        "signal": "BUY",
        "status_level": "READY_FOR_PREVIEW",
        "execution_status": "READY_FOR_PREVIEW",
        "risk_status": "APPROVED",
        "entry": 1.1,
        "stop_loss": 1.09,
        "take_profit": 1.12,
        "risk_reward": 2.0,
        "confidence": 82,
        "signal_hash": "phase22-signal",
        "setup_reason": "Test signal passed all guards.",
        "candle_source": {
            "broker_source": "VANTAGE_DEMO",
            "source": "VANTAGE_DEMO",
            "account_login": "123",
            "server": "Vantage Demo",
            "account_type": "DEMO",
        },
        "timestamp": now,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
    signal.update(overrides)
    return signal


class FakeSignalProvider:
    def __init__(self, signal: dict[str, Any]) -> None:
        self.signal = signal

    def signal_for_symbol(self, symbol: str, record_history: bool = False) -> dict[str, Any]:
        return dict(self.signal, symbol=symbol)


class FakeGuardedSender:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send_test_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        return {
            "status": "DEMO_ORDER_SENT",
            "mt5_order_sent": True,
            "guarded_sender_used": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }


def new_service(signal: dict[str, Any]):
    from backend.execution_mode.execution_mode_service import ExecutionModeService

    tmp = TemporaryDirectory()
    sender = FakeGuardedSender()
    service = ExecutionModeService(
        signal_provider=FakeSignalProvider(signal),
        guarded_execution_service=sender,
        config_path=Path(tmp.name) / "execution-mode.json",
    )
    return service, sender, tmp


def verify_routes_and_default_mode() -> bool:
    from backend.main import app
    from backend.api.execution_mode_routes import execution_mode_service

    execution_mode_service.set_config({"execution_mode": "APPROVAL"})
    client = TestClient(app)
    status = client.get("/execution-mode/status")
    payload = status.json()
    required_routes = [
        "/execution-mode/status",
        "/execution-mode/set",
        "/execution-mode/approve-signal",
        "/execution-mode/reject-signal",
        "/execution-mode/pending-approvals",
        "/execution-mode/history",
    ]
    route_text = "\n".join(route.path for route in app.routes)
    passed = (
        status.status_code == 200
        and payload.get("execution_mode") == "APPROVAL"
        and payload.get("auto_enabled") is False
        and payload.get("approval_required") is True
        and payload.get("live_execution_enabled") is False
        and payload.get("broker_execution_enabled") is False
        and all(route in route_text for route in required_routes)
    )
    return show("Default mode is APPROVAL and execution-mode routes are registered", passed, str(payload))


def verify_config_switch() -> bool:
    service, _, tmp = new_service(ready_signal())
    try:
        auto = service.set_config({"execution_mode": "AUTO", "live_execution_enabled": True, "broker_execution_enabled": True})
        approval = service.set_config({"execution_mode": "APPROVAL"})
        passed = (
            auto["execution_mode"] == "AUTO"
            and auto["auto_enabled"] is True
            and auto["live_execution_enabled"] is False
            and auto["broker_execution_enabled"] is False
            and approval["execution_mode"] == "APPROVAL"
            and approval["approval_required"] is True
        )
        return show("AUTO is enabled only through config and never enables live/broker execution", passed)
    finally:
        tmp.cleanup()


def verify_approval_pending_and_manual_decisions() -> bool:
    signal = ready_signal()
    service, sender, tmp = new_service(signal)
    try:
        pending = service.observe_signal(signal)
        approval = pending["approval"]
        rejected = service.reject_signal({"approval_id": approval["approval_id"], "reason": "No trade."})
        service2, sender2, tmp2 = new_service(signal)
        try:
            pending2 = service2.observe_signal(signal)
            approved = service2.approve_signal({"approval_id": pending2["approval"]["approval_id"]})
            passed = (
                pending["status"] == "PENDING_APPROVAL_CREATED"
                and len(sender.calls) == 0
                and rejected["status"] == "REJECTED"
                and len(sender.calls) == 0
                and approved["status"] == "ORDER_SENT"
                and len(sender2.calls) == 1
                and sender2.calls[0]["environment"] == "DEMO"
                and sender2.calls[0]["live_execution_enabled"] is False
                and sender2.calls[0]["broker_execution_enabled"] is False
            )
            return show("APPROVAL creates pending approval, rejects safely, and manual approve uses guarded sender", passed)
        finally:
            tmp2.cleanup()
    finally:
        tmp.cleanup()


def verify_auto_and_guard_blocks() -> bool:
    valid = ready_signal(signal_hash="auto-valid")
    service, sender, tmp = new_service(valid)
    try:
        service.set_config({"execution_mode": "AUTO"})
        sent = service.observe_signal(valid)
        duplicate = service.observe_signal(valid)
        expired_signal = ready_signal(signal_hash="expired", timestamp=(datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat())
        service.signal_provider.signal = expired_signal
        expired = service.observe_signal(expired_signal)
        missing_sl = ready_signal(signal_hash="missing-sl", stop_loss=None)
        service.signal_provider.signal = missing_sl
        sl_block = service.observe_signal(missing_sl)
        low_rr = ready_signal(signal_hash="low-rr", risk_reward=1.1)
        service.signal_provider.signal = low_rr
        rr_block = service.observe_signal(low_rr)
        live = ready_signal(signal_hash="live", live_execution_enabled=True)
        service.signal_provider.signal = live
        live_block = service.observe_signal(live)
        non_demo = ready_signal(signal_hash="non-demo", candle_source={"broker_source": "VANTAGE_DEMO", "source": "VANTAGE_DEMO", "account_type": "LIVE"})
        service.signal_provider.signal = non_demo
        demo_block = service.observe_signal(non_demo)
        passed = (
            sent["status"] == "ORDER_SENT"
            and len(sender.calls) == 1
            and duplicate["status"] == "BLOCKED"
            and "DUPLICATE_SIGNAL_BLOCKED" in duplicate["blockers"]
            and "SIGNAL_EXPIRED" in expired["blockers"]
            and "SL_TP_REQUIRED" in sl_block["blockers"]
            and "RR_BELOW_MINIMUM" in rr_block["blockers"]
            and "LIVE_EXECUTION_BLOCKED" in live_block["blockers"]
            and "NON_DEMO_ACCOUNT_BLOCKED" in demo_block["blockers"]
        )
        return show("AUTO executes only after guards and blocks duplicate, expired, SL/TP, RR, live, non-demo", passed)
    finally:
        tmp.cleanup()


def verify_files_and_dashboard() -> bool:
    service = SERVICE_PATH.read_text(encoding="utf-8")
    routes = ROUTES_PATH.read_text(encoding="utf-8")
    main = MAIN_PATH.read_text(encoding="utf-8")
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    required = [
        "ExecutionModeService",
        "execution_mode_service",
        'APIRouter(prefix="/execution-mode"',
        "execution_mode_router",
        "ExecutionModePanel",
        "Pending Approvals",
        "Auto Mode Active",
        "setExecutionMode",
        "approveExecutionModeSignal",
        "rejectExecutionModeSignal",
        "/execution-mode/status",
    ]
    missing = [item for item in required if item not in service + routes + main + dashboard + api]
    return show("Dashboard execution mode data and controls are generated", not missing, ", ".join(missing))


def verify_no_unrestricted_order_send() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    execution_text = SERVICE_PATH.read_text(encoding="utf-8")
    guarded_text = GUARDED_PATH.read_text(encoding="utf-8")
    required = ["send_test_order", "guarded_execution_service", "send_order"]
    forbidden = ["order_send("]
    passed = sorted(matches) == allowed and all(item in execution_text + guarded_text for item in required) and not any(item in execution_text for item in forbidden)
    return show("No unrestricted mt5.order_send added and existing guarded sender is still used", passed, ", ".join(matches))


def main() -> int:
    print("Phase 22 Execution Mode Switch Verification")
    print("=" * 78)
    checks = [
        verify_routes_and_default_mode(),
        verify_config_switch(),
        verify_approval_pending_and_manual_decisions(),
        verify_auto_and_guard_blocks(),
        verify_files_and_dashboard(),
        verify_no_unrestricted_order_send(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
