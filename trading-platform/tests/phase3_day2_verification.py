import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def sample_steps():
    from backend.replay.replay_models import ReplayStepResult

    now = datetime.now(timezone.utc)
    return [
        ReplayStepResult(
            step_index=0,
            replay_time=now,
            candles_visible=30,
            simulation_decision={"action": "NO_TRADE"},
            paper_trade_state={"active_positions": 0, "latest_outcome": None, "latest_rr": None},
            confidence=30.0,
        ),
        ReplayStepResult(
            step_index=1,
            replay_time=now,
            candles_visible=30,
            simulation_decision={"action": "SIMULATE_BUY"},
            paper_trade_state={"active_positions": 1, "latest_outcome": "OPEN", "latest_rr": None},
            confidence=82.0,
        ),
        ReplayStepResult(
            step_index=2,
            replay_time=now,
            candles_visible=30,
            simulation_decision={"action": "WAIT"},
            paper_trade_state={"active_positions": 0, "latest_outcome": "WIN", "latest_rr": 2.0},
            confidence=65.0,
        ),
        ReplayStepResult(
            step_index=3,
            replay_time=now,
            candles_visible=30,
            simulation_decision={"action": "AVOID"},
            paper_trade_state={"active_positions": 0, "latest_outcome": None, "latest_rr": None},
            confidence=20.0,
            notes=["Session block observed."],
        ),
    ]


def verify_files_and_routes() -> bool:
    files = [
        "backend/replay/replay_trade_analyzer.py",
        "backend/replay/replay_decision_analyzer.py",
        "backend/replay/replay_report_models.py",
        "backend/replay/replay_report_builder.py",
        "backend/replay/replay_weakness_detector.py",
        "backend/replay/replay_equity_curve.py",
        "docs/phase-3-day-2-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/replay/status",
            "/replay/run/{symbol}",
            "/replay/recent",
            "/replay/result/{replay_id}",
            "/replay/metrics/{replay_id}",
            "/replay/report/{replay_id}",
            "/replay/report/latest",
            "/replay/analytics/trades/{replay_id}",
            "/replay/analytics/decisions/{replay_id}",
            "/replay/equity/{replay_id}",
            "/replay/weaknesses/{replay_id}",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Replay analytics files and report routes exist", files_ok and routes_ok)


def verify_analyzers() -> bool:
    try:
        from backend.replay.replay_decision_analyzer import ReplayDecisionAnalyzer
        from backend.replay.replay_equity_curve import ReplayEquityCurveBuilder
        from backend.replay.replay_trade_analyzer import ReplayTradeAnalyzer
        from backend.replay.replay_weakness_detector import ReplayWeaknessDetector

        steps = sample_steps()
        empty_trade = ReplayTradeAnalyzer().analyze_trades([])
        trade = ReplayTradeAnalyzer().analyze_trades(steps)
        decision = ReplayDecisionAnalyzer().analyze_decisions(steps)
        equity = ReplayEquityCurveBuilder().build_equity_curve(steps, initial_balance=10000.0)
        weaknesses = ReplayWeaknessDetector().detect_weaknesses(empty_trade, ReplayDecisionAnalyzer().analyze_decisions([]), [])
        passed = (
            empty_trade.total_trades == 0
            and trade.total_trades == 1
            and trade.wins == 1
            and trade.net_rr == 2.0
            and decision.simulate_buy == 1
            and decision.wait == 1
            and decision.avoid == 1
            and decision.no_trade == 1
            and decision.block_rate == 50.0
            and len(equity) == len(steps)
            and equity[-1].cumulative_rr == 2.0
            and all(point.drawdown >= 0.0 for point in equity)
            and weaknesses
            and weaknesses[0].category == "DATA"
        )
        return show("Trade, decision, equity, and weakness analyzers are deterministic", passed)
    except Exception as exc:
        return show("Trade, decision, equity, and weakness analyzers are deterministic", False, str(exc))


def verify_report_builder_and_service() -> bool:
    try:
        from backend.replay.replay_models import ReplayRunResult
        from backend.replay.replay_report_builder import ReplayReportBuilder
        from backend.replay.replay_report_models import ReplayHistoricalReport
        from backend.replay.replay_service import ReplayService

        run = ReplayRunResult(
            replay_id="RPL-TEST",
            symbol="XAUUSD",
            timeframe="M15",
            total_steps=4,
            step_results=sample_steps(),
        )
        report = ReplayReportBuilder().build_report(run)
        service = ReplayService()
        stored = service.storage.save_result(run)
        service_report = service.get_replay_report(stored.replay_id)
        latest = service.get_latest_replay_report()
        missing = service.get_replay_report("MISSING")
        passed = (
            isinstance(report, ReplayHistoricalReport)
            and report.simulation_only is True
            and report.live_execution_enabled is False
            and report.trade_analytics.total_trades == 1
            and service_report is not None
            and latest.replay_id == "RPL-TEST"
            and missing is None
        )
        return show("Report builder and replay service expose JSON-safe analytics", passed)
    except Exception as exc:
        return show("Report builder and replay service expose JSON-safe analytics", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        latest_empty = client.get("/replay/report/latest")
        run = client.post(
            "/replay/run/XAUUSD",
            json={"window_size": 30, "step_size": 10, "max_steps": 2, "simulation_only": True},
        )
        replay_id = run.json()["replay_id"]
        report = client.get(f"/replay/report/{replay_id}")
        trades = client.get(f"/replay/analytics/trades/{replay_id}")
        decisions = client.get(f"/replay/analytics/decisions/{replay_id}")
        equity = client.get(f"/replay/equity/{replay_id}")
        weaknesses = client.get(f"/replay/weaknesses/{replay_id}")
        latest = client.get("/replay/report/latest")
        missing = client.get("/replay/report/MISSING")
        safety = client.get("/system/safety-scan").json()
        passed = (
            latest_empty.status_code == 200
            and run.status_code == 200
            and report.status_code == 200
            and trades.status_code == 200
            and decisions.status_code == 200
            and equity.status_code == 200
            and weaknesses.status_code == 200
            and latest.status_code == 200
            and missing.status_code == 404
            and report.json()["simulation_only"] is True
            and report.json()["live_execution_enabled"] is False
            and isinstance(equity.json(), list)
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
        )
        return show("Replay report API is JSON-safe and safety remains simulation-only", passed)
    except Exception as exc:
        return show("Replay report API is JSON-safe and safety remains simulation-only", False, str(exc))


def main() -> int:
    print("Phase 3 Day 2 Replay Analytics Verification")
    print("=" * 48)
    checks = [
        verify_files_and_routes(),
        verify_analyzers(),
        verify_report_builder_and_service(),
        verify_api_and_safety(),
    ]
    print("=" * 48)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
