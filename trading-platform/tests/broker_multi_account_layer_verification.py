import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

MODEL_PATH = PROJECT_ROOT / "backend/brokers/broker_account_models.py"
SERVICE_PATH = PROJECT_ROOT / "backend/brokers/broker_account_service.py"
PLANNER_PATH = PROJECT_ROOT / "backend/brokers/multi_account_execution_planner.py"
ROUTES_PATH = PROJECT_ROOT / "backend/api/broker_account_routes.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"
DOC_PATH = PROJECT_ROOT / "docs/broker-multi-account-layer.md"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_exist() -> bool:
    paths = [MODEL_PATH, SERVICE_PATH, PLANNER_PATH, ROUTES_PATH, DOC_PATH]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in paths if not path.exists()]
    return show("Broker layer files exist", not missing, ", ".join(missing))


def verify_routes_exist() -> bool:
    text = ROUTES_PATH.read_text(encoding="utf-8")
    required = [
        '@router.get("/status")',
        '@router.get("/accounts")',
        '@router.get("/accounts/{broker_id}")',
        '@router.post("/accounts/sync")',
        '@router.get("/readiness")',
        '@router.post("/execution-plan/preview")',
        '@router.get("/execution-plan/status")',
    ]
    missing = [item for item in required if item not in text]
    return show("Broker account routes exist", not missing, ", ".join(missing))


def verify_route_responses() -> bool:
    from backend.main import app

    client = TestClient(app)
    status = client.get("/brokers/status")
    accounts = client.get("/brokers/accounts")
    readiness = client.get("/brokers/readiness")
    plan_status = client.get("/brokers/execution-plan/status")
    plan = client.post(
        "/brokers/execution-plan/preview",
        json={"symbol": "EURUSD", "side": "BUY", "lot": 0.01, "entry": 1.1, "sl": 1.09, "tp": 1.12},
    )
    status_json = status.json()
    accounts_json = accounts.json()
    broker_ids = {account["broker_id"] for account in accounts_json.get("accounts", [])}
    pending = all(account["connection_status"] == "PENDING_CONNECTION" for account in accounts_json.get("accounts", []))
    separate_terminal = "current_terminal_account" in accounts_json and "MetaQuotes" not in " ".join(
        account.get("broker_name", "") for account in accounts_json.get("accounts", [])
    )
    plan_safe = all(item["execution_status"] == "PENDING_CONNECTION" for item in plan.json().get("plans", []))
    passed = (
        status.status_code == 200
        and accounts.status_code == 200
        and readiness.status_code == 200
        and plan_status.status_code == 200
        and plan.status_code == 200
        and {"STARTRADER", "FXPRO", "VANTAGE"} <= broker_ids
        and pending
        and separate_terminal
        and plan_safe
        and status_json["live_execution_enabled"] is False
        and status_json["broker_execution_enabled"] is False
        and plan.json()["mt5_order_send_used"] is False
    )
    return show("Broker routes return pending accounts and safe plan preview", passed)


def verify_dashboard_broker_panel() -> bool:
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    required = [
        "Broker Accounts",
        "StarTrader",
        "FxPro",
        "Vantage",
        "Current Test Terminal",
        "Broker account not connected yet.",
        "current_terminal_account",
        'brokerAccounts: fetchJson<ApiRecord>("/brokers/accounts")',
    ]
    missing = [item for item in required if item not in dashboard + api]
    return show("Broker dashboard cards exist", not missing, ", ".join(missing))


def verify_no_fake_balances_or_connections() -> bool:
    text = "\n".join([SERVICE_PATH.read_text(encoding="utf-8"), DASHBOARD_PATH.read_text(encoding="utf-8")])
    forbidden = ["100003.13", "100000", 'connection_status="CONNECTED"', "execution_enabled=True", "Broker account connected"]
    present = [item for item in forbidden if item in text]
    honest = "Broker account not connected yet." in text and "PENDING_CONNECTION" in text
    return show("Unavailable accounts are shown honestly", not present and honest, ", ".join(present))


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
    broker_text = "\n".join([SERVICE_PATH.read_text(encoding="utf-8"), PLANNER_PATH.read_text(encoding="utf-8"), ROUTES_PATH.read_text(encoding="utf-8")])
    unsafe = ["live_execution_enabled\": True", "broker_execution_enabled\": True", "execution_allowed\": True", "order_send("]
    present = [item for item in unsafe if item in broker_text]
    return show("No new order_send path or live/broker execution enablement", sorted(matches) == allowed and not present, ", ".join(matches + present))


def main() -> int:
    print("Broker Multi-Account Layer Verification")
    print("=" * 78)
    checks = [
        verify_files_exist(),
        verify_routes_exist(),
        verify_route_responses(),
        verify_dashboard_broker_panel(),
        verify_no_fake_balances_or_connections(),
        verify_no_order_send_or_live_flags(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
