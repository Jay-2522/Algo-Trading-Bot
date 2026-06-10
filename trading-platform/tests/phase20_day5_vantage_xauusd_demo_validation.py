import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

BROKER_SERVICE_PATH = PROJECT_ROOT / "backend/brokers/broker_account_service.py"
VANTAGE_SERVICE_PATH = PROJECT_ROOT / "backend/mt5_demo/vantage_xauusd_demo_validation_service.py"
ROUTES_PATH = PROJECT_ROOT / "backend/api/mt5_demo_routes.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


class FakeMT5DemoService:
    def __init__(self, server="VantageMarkets-Demo", account_type="DEMO"):
        self.server = server
        self.account_type = account_type

    def get_status(self):
        return {
            "status": "CONNECTED",
            "account_connected": self.account_type == "DEMO",
            "account_type": self.account_type,
            "login": "vantage-demo-1",
            "server": self.server,
            "balance": "1000",
            "equity": "1000",
            "free_margin": "1000",
            "used_margin": "0",
        }

    def get_account(self):
        return self.get_status()


class FakeMarketDataService:
    def __init__(self, tick=None):
        self.tick = tick or {
            "symbol": "XAUUSD",
            "status": "OK",
            "bid": 2350.0,
            "ask": 2350.25,
            "spread": 0.25,
            "source": "VANTAGE_DEMO",
            "tick_recovery_status": "TICK_AVAILABLE_DIRECT",
            "symbol_availability": "SYMBOL_AVAILABLE",
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_symbol_tick(self, symbol):
        return self.tick

    def get_xauusd_diagnostics(self):
        return {
            "broker_detected": "VANTAGE_DEMO",
            "server": "VantageMarkets-Demo",
            "account_login": "vantage-demo-1",
            "account_type": "DEMO",
            "tick_available": self.tick.get("status") == "OK",
            "bid": self.tick.get("bid"),
            "ask": self.tick.get("ask"),
            "spread": self.tick.get("spread"),
            "source": self.tick.get("source"),
            "readiness_result": "READY" if self.tick.get("status") == "OK" else "BLOCKED",
        }


class FakeApprovalWorkflow:
    def run_workflow(self, payload):
        return {"approved_for_future_demo_order": True, "blockers": [], "mt5_order_sent": False}


class FakeGuardedSender:
    def __init__(self):
        self.called = False

    def send_order(self, payload):
        self.called = True
        return {"status": "DEMO_ORDER_SENT", "mt5_order_sent": True, "symbol": payload["symbol"]}


def _service(server="VantageMarkets-Demo", account_type="DEMO", tick=None):
    from backend.mt5_demo.vantage_xauusd_demo_validation_service import VantageXAUUSDDemoValidationService

    guarded = FakeGuardedSender()
    service = VantageXAUUSDDemoValidationService(
        mt5_demo_service=FakeMT5DemoService(server=server, account_type=account_type),
        market_data_service=FakeMarketDataService(tick=tick),
        approval_workflow_service=FakeApprovalWorkflow(),
        guarded_sender_service=guarded,
        position_sync_service=object(),
        lifecycle_service=object(),
    )
    return service, guarded


def valid_payload(**overrides):
    payload = {
        "symbol": "XAUUSD",
        "side": "BUY",
        "lot": 0.01,
        "stop_loss": 2345.0,
        "take_profit": 2360.0,
        "confirm": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
    payload.update(overrides)
    return payload


def verify_routes_and_dashboard() -> bool:
    route_text = ROUTES_PATH.read_text(encoding="utf-8")
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    required = [
        '@router.get("/vantage/xauusd/status")',
        '@router.post("/vantage/xauusd/test-order/preview")',
        '@router.post("/vantage/xauusd/test-order")',
        "Vantage XAUUSD Demo Validation",
        "vantageXauusdStatus",
        "vantageXauusdPreview",
        "/mt5-demo/vantage/xauusd/status",
        "/mt5-demo/vantage/xauusd/test-order/preview",
    ]
    missing = [item for item in required if item not in route_text + dashboard + api]
    return show("Vantage XAUUSD routes and dashboard panel exist", not missing, ", ".join(missing))


def verify_broker_detection() -> bool:
    from backend.brokers.broker_account_service import BrokerAccountService

    service = BrokerAccountService(mt5_demo_service=FakeMT5DemoService())
    current = service.current_terminal_account()
    vantage = service.get_account_status("VANTAGE")
    passed = current.broker_detected == "VANTAGE_DEMO" and vantage.connection_status == "CONNECTED" and vantage.execution_enabled is False
    return show("Vantage demo current terminal maps to VANTAGE_DEMO without enabling execution", passed)


def verify_preview_ready_and_no_send() -> bool:
    service, guarded = _service()
    preview = service.preview(valid_payload())
    passed = (
        preview["readiness_decision"] == "READY_FOR_GUARDED_DEMO_TEST"
        and preview["would_send"] is False
        and preview["broker_detected"] == "VANTAGE_DEMO"
        and preview["entry_estimate"] == 2350.25
        and guarded.called is False
    )
    return show("Vantage preview can be ready but never sends", passed, str(preview))


def verify_blockers() -> bool:
    cases = [
        ("non-Vantage blocked", _service(server="MetaQuotes-Demo")[0].preview(valid_payload()), "VANTAGE_DEMO_ACCOUNT_REQUIRED"),
        ("live account blocked", _service(account_type="LIVE")[0].preview(valid_payload()), "VANTAGE_DEMO_ACCOUNT_REQUIRED"),
        ("confirm false blocked", _service()[0].send_test_order(valid_payload(confirm=False)), "EXPLICIT_CONFIRM_TRUE_REQUIRED"),
        ("lot too large blocked", _service()[0].preview(valid_payload(lot=0.02)), "LOT_MUST_BE_0_01_OR_LESS"),
        ("missing SL blocked", _service()[0].preview(valid_payload(stop_loss=None)), "STOP_LOSS_REQUIRED"),
        ("missing TP blocked", _service()[0].preview(valid_payload(take_profit=None)), "TAKE_PROFIT_REQUIRED"),
        ("invalid placement blocked", _service()[0].preview(valid_payload(stop_loss=2355.0, take_profit=2360.0)), "INVALID_BUY_SL_TP_PLACEMENT"),
    ]
    failed = []
    for name, result, blocker in cases:
        if blocker not in result.get("blocked_reasons", []):
            failed.append(f"{name}:{blocker}")
    return show("Vantage safety blockers work", not failed, ", ".join(failed))


def verify_duplicate_and_unavailable_tick() -> bool:
    service, guarded = _service()
    service._test_order_attempted = True
    duplicate = service.preview(valid_payload())
    unavailable_service, _ = _service(tick={"symbol": "XAUUSD", "status": "SYMBOL_TICK_UNAVAILABLE", "bid": 0.0, "ask": 0.0, "spread": None, "source": "VANTAGE_DEMO"})
    unavailable = unavailable_service.preview(valid_payload())
    passed = (
        "DUPLICATE_VANTAGE_XAUUSD_TEST_ORDER_BLOCKED" in duplicate.get("blocked_reasons", [])
        and "XAUUSD_TICK_NOT_READY" in unavailable.get("blocked_reasons", [])
        and "SPREAD_UNAVAILABLE" in unavailable.get("blocked_reasons", [])
        and guarded.called is False
    )
    return show("Duplicate and unavailable tick remain blocked", passed)


def verify_live_routes_are_safe() -> bool:
    from backend.main import app

    client = TestClient(app)
    status = client.get("/mt5-demo/vantage/xauusd/status")
    preview = client.post("/mt5-demo/vantage/xauusd/test-order/preview", json={"symbol": "XAUUSD", "side": "BUY", "lot": 0.01, "live_execution_enabled": False, "broker_execution_enabled": False})
    blocked_send = client.post("/mt5-demo/vantage/xauusd/test-order", json=valid_payload(confirm=False))
    passed = (
        status.status_code == 200
        and preview.status_code == 200
        and blocked_send.status_code == 200
        and preview.json().get("would_send") is False
        and blocked_send.json().get("mt5_order_sent") is False
        and blocked_send.json().get("guarded_sender_used") is False
        and status.json().get("live_execution_enabled") is False
        and status.json().get("broker_execution_enabled") is False
    )
    print("Live Vantage status:", status.json())
    print("Live Vantage preview:", preview.json())
    return show("Live Vantage endpoints are read-only unless all guarded gates pass", passed)


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
    text = VANTAGE_SERVICE_PATH.read_text(encoding="utf-8") + BROKER_SERVICE_PATH.read_text(encoding="utf-8")
    forbidden = ['"live_execution_enabled": True', '"broker_execution_enabled": True', "order_send("]
    present = [item for item in forbidden if item in text]
    return show("No unrestricted order_send or live/broker enablement added", sorted(matches) == allowed and not present, ", ".join(matches + present))


def main() -> int:
    print("Phase 20 Day 5 Vantage XAUUSD Demo Validation")
    print("=" * 78)
    checks = [
        verify_routes_and_dashboard(),
        verify_broker_detection(),
        verify_preview_ready_and_no_send(),
        verify_blockers(),
        verify_duplicate_and_unavailable_tick(),
        verify_live_routes_are_safe(),
        verify_no_unrestricted_order_send(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
