import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

AUDIT_DOC = PROJECT_ROOT / "docs/phase20-day1-strategy-audit.md"
ENGINE_DOC = PROJECT_ROOT / "docs/phase20-day1-ai-strategy-signal-engine.md"
ENGINE_PATH = PROJECT_ROOT / "backend/strategy/client_signal_engine.py"
HISTORY_PATH = PROJECT_ROOT / "backend/strategy/signal_history_service.py"
ROUTES_PATH = PROJECT_ROOT / "backend/api/client_signal_engine_routes.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_docs_exist() -> bool:
    required_text = ["liquidity", "BOS", "CHOCH", "FVG", "order block", "session", "confidence", "risk qualification", "execution gate"]
    audit = AUDIT_DOC.read_text(encoding="utf-8") if AUDIT_DOC.exists() else ""
    missing = [item for item in required_text if item.lower() not in audit.lower()]
    passed = AUDIT_DOC.exists() and ENGINE_DOC.exists() and not missing
    return show("Strategy audit and engine docs exist", passed, ", ".join(missing))


def verify_routes_exist() -> bool:
    text = ROUTES_PATH.read_text(encoding="utf-8")
    required = [
        'prefix="/client-signals-engine"',
        '@router.get("/status")',
        '@router.get("/current")',
        '@router.get("/EURUSD")',
        '@router.get("/XAUUSD")',
        '@router.get("/NIFTY50")',
        '@router.post("/refresh")',
        '@router.get("/history")',
        '@router.get("/history/{symbol}")',
    ]
    missing = [item for item in required if item not in text]
    return show("Signal engine routes exist", not missing, ", ".join(missing))


def _valid_signal(payload: dict) -> bool:
    required = {
        "symbol",
        "signal",
        "confidence",
        "reason",
        "entry",
        "stop_loss",
        "take_profit",
        "risk_reward",
        "risk_status",
        "execution_status",
        "strategy_components",
    }
    components = payload.get("strategy_components", {})
    component_keys = {"liquidity_sweep", "bos", "choch", "fvg", "order_block", "session_valid"}
    return (
        required <= set(payload)
        and payload["signal"] in {"BUY", "SELL", "WAIT"}
        and payload["risk_status"] in {"APPROVED", "REJECTED", "NO_SIGNAL", "INSUFFICIENT_DATA", "INTEGRATION_PENDING"}
        and payload["execution_status"] in {"READY", "BLOCKED", "WAITING"}
        and component_keys <= set(components)
    )


def verify_route_responses() -> bool:
    from backend.main import app

    client = TestClient(app)
    status = client.get("/client-signals-engine/status")
    eurusd = client.get("/client-signals-engine/EURUSD")
    xauusd = client.get("/client-signals-engine/XAUUSD")
    nifty = client.get("/client-signals-engine/NIFTY50")
    current = client.get("/client-signals-engine/current")
    history = client.get("/client-signals-engine/history")
    passed = (
        status.status_code == 200
        and eurusd.status_code == 200
        and xauusd.status_code == 200
        and nifty.status_code == 200
        and current.status_code == 200
        and history.status_code == 200
        and _valid_signal(eurusd.json())
        and _valid_signal(xauusd.json())
        and _valid_signal(nifty.json())
        and nifty.json()["signal"] == "WAIT"
        and nifty.json()["execution_status"] == "BLOCKED"
        and nifty.json()["reason"] == "Indian market integration pending."
        and (eurusd.json()["signal"] != "WAIT" or eurusd.json()["confidence"] is None)
        and (xauusd.json()["signal"] != "WAIT" or xauusd.json()["confidence"] is None)
    )
    return show("EURUSD/XAUUSD/NIFTY50 signal objects are valid and honest", passed)


def verify_dashboard_uses_signal_engine() -> bool:
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    required = [
        "/client-signals-engine/current",
        "/client-signals-engine/refresh",
        "StrategyComponents",
        "Liquidity Sweep",
        "BOS",
        "CHOCH",
        "FVG",
        "Order Block",
        "Session Valid",
        "Waiting for a valid strategy setup.",
    ]
    missing = [item for item in required if item not in dashboard + api]
    forbidden = ["<select", "Manual", "fake confidence", "fake signal"]
    present = [item for item in forbidden if item in dashboard]
    return show("Execution panel and signal cards use signal engine output", not missing and not present, ", ".join(missing + present))


def verify_no_order_send_or_live_flags() -> bool:
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
    text = ENGINE_PATH.read_text(encoding="utf-8") + HISTORY_PATH.read_text(encoding="utf-8") + ROUTES_PATH.read_text(encoding="utf-8")
    forbidden = ["order_send(", '"live_execution_enabled": True', '"broker_execution_enabled": True', '"execution_allowed": True']
    present = [item for item in forbidden if item in text]
    return show("No order_send or live/broker execution enablement added", sorted(matches) == allowed and not present, ", ".join(matches + present))


def main() -> int:
    print("Phase 20 Day 1 AI Strategy Signal Engine Verification")
    print("=" * 78)
    checks = [
        verify_docs_exist(),
        verify_routes_exist(),
        verify_route_responses(),
        verify_dashboard_uses_signal_engine(),
        verify_no_order_send_or_live_flags(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
