import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "backend/nifty50/nifty_analytics_service.py",
        "backend/nifty50/nifty_reporting_adapter.py",
        "docs/phase-12-day-7-progress.md",
        "docs/nifty50-analytics-integration.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("NIFTY analytics service, reporting adapter, and docs exist", not missing, ", ".join(missing))


def verify_analytics_and_reports() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/client-analytics/status")
        overview = client.get("/client-analytics/overview")
        symbols = client.get("/client-analytics/symbols")
        nifty_symbol = client.get("/client-analytics/symbols/NIFTY50")
        daily_report = client.get("/client-analytics/reports/daily")
        nifty_report = client.get("/client-analytics/reports/symbol/NIFTY50")

        symbol_payload = nifty_symbol.json()
        report_symbols = {item["symbol"] for item in daily_report.json()["symbol_performance"]}
        nifty_report_payload = nifty_report.json()
        no_fake_metrics = (
            symbol_payload["total_signals"] == 0
            and symbol_payload["demo_executions"] == 0
            and symbol_payload["wins"] == 0
            and symbol_payload["losses"] == 0
            and symbol_payload["net_pnl"] == 0
            and symbol_payload["avg_confidence"] == 0
        )
        passed = (
            status.status_code == 200
            and status.json()["nifty50_status"] == "ANALYTICS_INTEGRATED"
            and "NIFTY50" in status.json()["supported_symbols"]
            and overview.status_code == 200
            and "NIFTY50" in overview.json()["supported_symbols"]
            and symbols.status_code == 200
            and "NIFTY50" in {item["symbol"] for item in symbols.json()}
            and nifty_symbol.status_code == 200
            and no_fake_metrics
            and daily_report.status_code == 200
            and "NIFTY50" in report_symbols
            and daily_report.json()["summary"]["nifty50_status"] == "ANALYTICS_INTEGRATED"
            and nifty_report.status_code == 200
            and nifty_report_payload["summary"]["nifty50_reporting"]["status"] == "ANALYTICS_INTEGRATED"
            and nifty_report_payload["summary"]["nifty50_reporting"]["execution_ready"] is False
        )
        return show("NIFTY appears in analytics and reports with honest zero metrics", passed)
    except Exception as exc:
        return show("NIFTY appears in analytics and reports with honest zero metrics", False, str(exc))


def verify_strategy_and_executive_dashboard() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        strategy_status = client.get("/client-analytics/strategy/status")
        strategy_performance = client.get("/client-analytics/strategy/performance")
        strategy_nifty = client.get("/client-analytics/strategy/performance/NIFTY50")
        comparison = client.get("/client-analytics/strategy/comparison")
        instruments = client.get("/client-analytics/executive/instruments")
        summary = client.get("/client-analytics/executive/summary")
        completion = client.get("/client-analytics/executive/completion")
        nifty_instrument = next((item for item in instruments.json()["instruments"] if item["symbol"] == "NIFTY50"), {})

        passed = (
            strategy_status.status_code == 200
            and strategy_status.json()["nifty50_status"] == "SMC_INTELLIGENCE_READY"
            and strategy_status.json()["nifty50_analytics_status"] == "ANALYTICS_INTEGRATED"
            and strategy_performance.status_code == 200
            and "NIFTY50" in {item["symbol"] for item in strategy_performance.json()}
            and strategy_nifty.status_code == 200
            and strategy_nifty.json()["confidence_quality"] == "SMC_INTELLIGENCE_READY"
            and strategy_nifty.json()["risk_quality"] == "ANALYTICS_INTEGRATED"
            and strategy_nifty.json()["strategy_score"] == 0
            and comparison.status_code == 200
            and comparison.json()["nifty50_status"] == "ANALYTICS_INTEGRATED"
            and comparison.json()["nifty50_strategy_status"]["status"] == "SMC_INTELLIGENCE_READY"
            and instruments.status_code == 200
            and instruments.json()["xauusd_status"] == "READY"
            and instruments.json()["eurusd_status"] == "READY"
            and instruments.json()["nifty50_status"] == "ANALYTICS_INTEGRATED"
            and nifty_instrument["status"] == "ANALYTICS_INTEGRATED"
            and nifty_instrument["ready"] is False
            and summary.status_code == 200
            and summary.json()["nifty50_ready"] is False
            and summary.json()["overall_completion_percentage"] == 99
            and completion.status_code == 200
            and completion.json()["overall_completion_percentage"] == 99
            and "NIFTY50 Analytics Integration" in completion.json()["completed"]
        )
        return show("NIFTY appears in strategy intelligence and executive dashboard at 99 percent", passed)
    except Exception as exc:
        return show("NIFTY appears in strategy intelligence and executive dashboard at 99 percent", False, str(exc))


def verify_readiness() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        readiness = client.get("/nifty50/readiness")
        payload = readiness.json()
        blockers = " ".join(payload["blockers"]).lower()
        passed = (
            readiness.status_code == 200
            and payload["status"] == "ANALYTICS_INTEGRATED"
            and payload["market_data_ready"] is True
            and payload["strategy_ready"] is True
            and payload["risk_ready"] is True
            and payload["execution_bridge_ready"] is True
            and payload["analytics_ready"] is True
            and payload["execution_ready"] is False
            and payload["simulation_only"] is True
            and payload["live_execution_enabled"] is False
            and payload["broker_execution_enabled"] is False
            and "broker integration missing" in blockers
            and "demo validation missing" in blockers
            and "vps deployment missing" in blockers
        )
        return show("NIFTY readiness upgraded to analytics integrated while execution remains disabled", passed)
    except Exception as exc:
        return show("NIFTY readiness upgraded to analytics integrated while execution remains disabled", False, str(exc))


def verify_no_broker_api_or_execution() -> bool:
    try:
        forbidden = [
            "requests.",
            "httpx.",
            "aiohttp",
            "urllib.request",
            "yfinance",
            "kiteconnect",
            "smartapi",
            "dhanhq",
            "fyers_apiv3",
            "upstox_client",
            "broker_api_key",
            "access_token",
        ]
        offenders = []
        for path in (PROJECT_ROOT / "backend" / "nifty50").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in forbidden:
                if token.lower() in text:
                    offenders.append(f"{path.name}:{token}")

        token = "mt5." + "order_send"
        order_matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                order_matches.append(path.relative_to(PROJECT_ROOT).as_posix())

        return show(
            "No broker APIs, no execution enabled, and no new mt5.order_send added",
            not offenders and order_matches == ["backend/demo_execution/mt5_demo_executor.py"],
            ", ".join(offenders + order_matches),
        )
    except Exception as exc:
        return show("No broker APIs, no execution enabled, and no new mt5.order_send added", False, str(exc))


def verify_previous_routes_preserved() -> bool:
    try:
        from backend.main import app

        required = {
            "/client-analytics/status",
            "/client-analytics/overview",
            "/client-analytics/accounts",
            "/client-analytics/reports/status",
            "/client-analytics/strategy/status",
            "/client-analytics/executive/status",
            "/nifty50/status",
            "/nifty50/market-data/health",
            "/nifty50/strategy/snapshot",
            "/nifty50/risk/status",
            "/nifty50/trade/candidates",
            "/nifty50/execution/status",
        }
        registered = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        return show("Previous Phase 11 and Phase 12 routes are preserved", required <= registered)
    except Exception as exc:
        return show("Previous Phase 11 and Phase 12 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 12 Day 7 NIFTY50 Analytics Integration Verification")
    print("=" * 72)
    checks = [
        verify_files(),
        verify_analytics_and_reports(),
        verify_strategy_and_executive_dashboard(),
        verify_readiness(),
        verify_no_broker_api_or_execution(),
        verify_previous_routes_preserved(),
    ]
    print("=" * 72)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
