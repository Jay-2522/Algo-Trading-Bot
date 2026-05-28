import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


DASHBOARD_ROUTES = [
    "/dashboard/status",
    "/dashboard/overview",
    "/dashboard/cards",
    "/dashboard/summary",
]

MONITORING_ROUTES = [
    "/monitoring/status",
    "/monitoring/system-health",
    "/monitoring/modules",
    "/monitoring/execution",
    "/monitoring/webhooks",
    "/monitoring/brokers",
    "/monitoring/alerts",
]


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_routes_return_json() -> bool:
    try:
        from backend.main import app

        client = TestClient(app, raise_server_exceptions=False)
        failures: list[str] = []
        for path in DASHBOARD_ROUTES + MONITORING_ROUTES:
            response = client.get(path)
            if response.status_code != 200:
                failures.append(f"{path} returned {response.status_code}: {response.text[:300]}")
                continue
            try:
                payload = response.json()
                json.dumps(payload, default=str)
            except Exception as exc:
                failures.append(f"{path} is not JSON-safe: {exc}")
        return show("Dashboard and monitoring routes return HTTP 200 JSON", not failures, "; ".join(failures))
    except Exception as exc:
        return show("Dashboard and monitoring routes return HTTP 200 JSON", False, str(exc))


def verify_empty_state_shapes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app, raise_server_exceptions=False)
        status = client.get("/dashboard/status").json()
        overview = client.get("/dashboard/overview").json()
        cards = client.get("/dashboard/cards").json()
        summary = client.get("/dashboard/summary").json()
        alerts = client.get("/monitoring/alerts").json()
        passed = (
            status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and overview["simulation_only"] is True
            and overview["live_execution_enabled"] is False
            and isinstance(cards, list)
            and len(cards) >= 8
            and all(card.get("simulation_only") is True for card in cards)
            and all(card.get("live_execution_enabled") is False for card in cards)
            and summary["simulation_only"] is True
            and summary["live_execution_enabled"] is False
            and isinstance(alerts, list)
        )
        return show("Dashboard payloads expose safe defaults and safety flags", passed)
    except Exception as exc:
        return show("Dashboard payloads expose safe defaults and safety flags", False, str(exc))


def verify_no_live_execution_patterns() -> bool:
    try:
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            "mt5.order_send" not in text
            and "order_send(" not in text
            and "live_execution_enabled=True" not in text
            and "real_trading_enabled=True" not in text
            and "enable_live_trading" not in text
        )
        return show("No live execution patterns were added", passed)
    except Exception as exc:
        return show("No live execution patterns were added", False, str(exc))


def main() -> int:
    print("Dashboard JSON Safety Verification")
    print("=" * 42)
    checks = [
        verify_routes_return_json(),
        verify_empty_state_shapes(),
        verify_no_live_execution_patterns(),
    ]
    print("=" * 42)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
