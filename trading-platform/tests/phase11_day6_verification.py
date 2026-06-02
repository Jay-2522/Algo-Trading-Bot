import re
import subprocess
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
        "backend/client_analytics/strategy_models.py",
        "backend/client_analytics/strategy_analytics_service.py",
        "backend/client_analytics/comparative_analytics.py",
        "frontend/components/strategy-intelligence/StrategyIntelligenceSection.tsx",
        "frontend/components/strategy-intelligence/StrategyOverviewCards.tsx",
        "frontend/components/strategy-intelligence/StrategyComparisonGrid.tsx",
        "frontend/components/strategy-intelligence/SessionEfficiencyPanel.tsx",
        "frontend/components/strategy-intelligence/StrategyRankingPanel.tsx",
        "frontend/components/strategy-intelligence/StrategyIntelligenceEmptyState.tsx",
        "frontend/lib/strategyAnalyticsApi.ts",
        "docs/phase-11-day-6-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Strategy analytics backend, frontend, API client, and docs exist", not missing, ", ".join(missing))


def verify_strategy_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        overview = client.get("/client-analytics/strategy/overview")
        rankings = client.get("/client-analytics/strategy/rankings")
        comparison = client.get("/client-analytics/strategy/comparison")
        performance = client.get("/client-analytics/strategy/performance")
        nifty = client.get("/client-analytics/strategy/performance/NIFTY50")
        overview_payload = overview.json()
        comparison_payload = comparison.json()
        nifty_payload = nifty.json()
        passed = (
            overview.status_code == 200
            and rankings.status_code == 200
            and comparison.status_code == 200
            and performance.status_code == 200
            and nifty.status_code == 200
            and overview_payload["simulation_only"] is True
            and overview_payload["demo_execution"] is True
            and overview_payload["live_execution_enabled"] is False
            and overview_payload["broker_execution_enabled"] is False
            and comparison_payload["nifty50_status"] == "PENDING IMPLEMENTATION"
            and nifty_payload["confidence_quality"] == "PLACEHOLDER"
        )
        return show("Strategy overview, rankings, comparison, performance, and safety flags work", passed)
    except Exception as exc:
        return show("Strategy overview, rankings, comparison, performance, and safety flags work", False, str(exc))


def verify_dashboard_ui() -> bool:
    try:
        page = (PROJECT_ROOT / "frontend" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        section = (PROJECT_ROOT / "frontend" / "components" / "strategy-intelligence" / "StrategyIntelligenceSection.tsx").read_text(encoding="utf-8")
        grid = (PROJECT_ROOT / "frontend" / "components" / "strategy-intelligence" / "StrategyComparisonGrid.tsx").read_text(encoding="utf-8")
        rankings = (PROJECT_ROOT / "frontend" / "components" / "strategy-intelligence" / "StrategyRankingPanel.tsx").read_text(encoding="utf-8")
        sessions = (PROJECT_ROOT / "frontend" / "components" / "strategy-intelligence" / "SessionEfficiencyPanel.tsx").read_text(encoding="utf-8")
        passed = (
            "StrategyIntelligenceSection" in page
            and "Strategy Performance Intelligence" in section
            and "SIMULATION ONLY" in section
            and "LIVE DISABLED" in section
            and "PENDING IMPLEMENTATION" in grid
            and "Comparative Ranking" in rankings
            and "Session Effectiveness" in sessions
        )
        return show("Strategy dashboard section, comparison grid, rankings, session panel, and labels exist", passed)
    except Exception as exc:
        return show("Strategy dashboard section, comparison grid, rankings, session panel, and labels exist", False, str(exc))


def verify_no_fake_profit_and_order_send() -> bool:
    try:
        paths = [
            *list((PROJECT_ROOT / "frontend" / "components" / "strategy-intelligence").glob("*.tsx")),
            PROJECT_ROOT / "frontend" / "lib" / "strategyAnalyticsApi.ts",
            *list((PROJECT_ROOT / "backend" / "client_analytics").glob("strategy*.py")),
            PROJECT_ROOT / "backend" / "client_analytics" / "comparative_analytics.py",
        ]
        suspicious: list[str] = []
        fake_profit_pattern = re.compile(r"[\+\$]\s?(?:[1-9]\d{2,}|900|1000|5000)")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for match in fake_profit_pattern.finditer(text):
                suspicious.append(f"{path.name}: {match.group(0)}")
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not suspicious and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("No fake profits and no new mt5.order_send exist", passed, ", ".join(suspicious + matches))
    except Exception as exc:
        return show("No fake profits and no new mt5.order_send exist", False, str(exc))


def verify_phase11_preserved() -> bool:
    try:
        from backend.main import app

        required = {
            "/client-analytics/status",
            "/client-analytics/accounts",
            "/client-analytics/reports/status",
            "/client-analytics/strategy/status",
            "/client-analytics/strategy/overview",
            "/client-analytics/strategy/performance",
            "/client-analytics/strategy/rankings",
            "/client-analytics/strategy/session-efficiency",
            "/client-analytics/strategy/comparison",
        }
        registered = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        return show("Phase 11 Day 1-5 and strategy routes are preserved", required <= registered)
    except Exception as exc:
        return show("Phase 11 Day 1-5 and strategy routes are preserved", False, str(exc))


def verify_frontend_build() -> bool:
    try:
        result = subprocess.run(
            ["npm.cmd", "run", "build"],
            cwd=PROJECT_ROOT / "frontend",
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        detail = (result.stderr or result.stdout).splitlines()[-1] if result.returncode else ""
        return show("Frontend build expected to pass", result.returncode == 0, detail)
    except Exception as exc:
        return show("Frontend build expected to pass", False, str(exc))


def main() -> int:
    print("Phase 11 Day 6 Strategy Performance Intelligence Verification")
    print("=" * 68)
    checks = [
        verify_files(),
        verify_strategy_routes(),
        verify_dashboard_ui(),
        verify_no_fake_profit_and_order_send(),
        verify_phase11_preserved(),
        verify_frontend_build(),
    ]
    print("=" * 68)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
