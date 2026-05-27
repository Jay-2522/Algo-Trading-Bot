import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_routes() -> bool:
    files = [
        "backend/account_routing/__init__.py",
        "backend/account_routing/account_models.py",
        "backend/account_routing/account_registry.py",
        "backend/account_routing/account_group_manager.py",
        "backend/account_routing/signal_account_matcher.py",
        "backend/account_routing/routing_policy_engine.py",
        "backend/account_routing/routing_decision_builder.py",
        "backend/account_routing/account_routing_service.py",
        "backend/api/account_routing_routes.py",
        "docs/phase-3-day-15-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/accounts/status",
            "/accounts",
            "/accounts/{account_id}",
            "/accounts/groups",
            "/accounts/policy/default",
            "/accounts/route-preview",
            "/webhooks/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Account routing files and routes exist", files_ok and routes_ok)


def verify_registry_and_groups() -> bool:
    try:
        from backend.account_routing.account_group_manager import AccountGroupManager
        from backend.account_routing.account_registry import AccountRegistry

        registry = AccountRegistry()
        accounts = registry.list_accounts()
        forex_accounts = registry.list_accounts_by_symbol("EURUSD")
        nifty_accounts = registry.list_accounts_by_symbol("NIFTY50")
        groups = AccountGroupManager(registry).list_groups()
        account_ids = {account.account_id for account in accounts}
        indian = [registry.get_account(account_id) for account_id in ["ZERODHA_PLACEHOLDER", "ANGELONE_PLACEHOLDER", "UPSTOX_PLACEHOLDER"]]
        passed = (
            {"STARTRADER_DEMO_1", "FXPRO_DEMO_1", "VANTAGE_DEMO_1"} <= account_ids
            and {"ZERODHA_PLACEHOLDER", "ANGELONE_PLACEHOLDER", "UPSTOX_PLACEHOLDER"} <= account_ids
            and all(account is not None and account.enabled is False and account.demo_ready is False for account in indian)
            and all(account.live_execution_enabled is False for account in accounts)
            and len(forex_accounts) == 3
            and len(nifty_accounts) == 3
            and len(groups["FOREX_CFD_GROUP"]) == 3
            and len(groups["INDIAN_BROKER_GROUP"]) == 3
        )
        return show("Default accounts and groups are registered safely", passed)
    except Exception as exc:
        return show("Default accounts and groups are registered safely", False, str(exc))


def verify_routing_decisions() -> bool:
    try:
        from backend.account_routing.account_routing_service import AccountRoutingService

        service = AccountRoutingService()
        eur = service.preview_route({"signal_id": "manual-test-001", "canonical_symbol": "EURUSD", "action": "BUY"})
        xau = service.preview_route({"signal_id": "manual-test-002", "canonical_symbol": "XAUUSD", "action": "SELL"})
        nifty = service.preview_route({"signal_id": "manual-test-003", "canonical_symbol": "NIFTY50", "action": "BUY"})
        policy = service.get_default_policy()
        passed = (
            eur.routing_ready is True
            and eur.routing_mode == "COPY_TO_ALL"
            and len(eur.eligible_accounts) == 3
            and {account.broker_id for account in eur.eligible_accounts} == {"STARTRADER", "FXPRO", "VANTAGE"}
            and xau.routing_ready is True
            and len(xau.eligible_accounts) == 3
            and nifty.routing_ready is False
            and len(nifty.eligible_accounts) == 0
            and any("No eligible accounts" in reason for reason in nifty.rejection_reasons)
            and policy.routing_mode == "COPY_TO_ALL"
            and policy.live_execution_enabled is False
            and eur.simulation_only is True
            and eur.live_execution_enabled is False
        )
        return show("Routing preview handles EURUSD/XAUUSD and keeps NIFTY50 conservative", passed)
    except Exception as exc:
        return show("Routing preview handles EURUSD/XAUUSD and keeps NIFTY50 conservative", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/accounts/status")
        accounts = client.get("/accounts")
        groups = client.get("/accounts/groups")
        policy = client.get("/accounts/policy/default")
        eur = client.post("/accounts/route-preview", json={"signal_id": "api-eur", "canonical_symbol": "EURUSD", "action": "BUY"})
        nifty = client.post("/accounts/route-preview", json={"signal_id": "api-nifty", "canonical_symbol": "NIFTY50", "action": "BUY"})
        webhooks = client.get("/webhooks/status")
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and accounts.status_code == 200
            and len(accounts.json()) == 6
            and groups.status_code == 200
            and "FOREX_CFD_GROUP" in groups.json()
            and policy.status_code == 200
            and policy.json()["routing_mode"] == "COPY_TO_ALL"
            and policy.json()["live_execution_enabled"] is False
            and eur.status_code == 200
            and eur.json()["routing_ready"] is True
            and len(eur.json()["eligible_accounts"]) == 3
            and nifty.status_code == 200
            and nifty.json()["routing_ready"] is False
            and webhooks.status_code == 200
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Account routing APIs are JSON-safe and preserve webhook routes", passed)
    except Exception as exc:
        return show("Account routing APIs are JSON-safe and preserve webhook routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 15 Multi-Account Routing Verification")
    print("=" * 58)
    checks = [
        verify_files_and_routes(),
        verify_registry_and_groups(),
        verify_routing_decisions(),
        verify_api_and_safety(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
