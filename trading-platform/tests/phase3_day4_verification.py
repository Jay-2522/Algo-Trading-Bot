import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def sample_report(replay_id: str, timeframe: str, win_rate: float, net_rr: float, block_rate: float, trades: int):
    from backend.replay.replay_report_models import (
        ReplayDecisionAnalytics,
        ReplayEquityPoint,
        ReplayHistoricalReport,
        ReplayTradeAnalytics,
    )

    return ReplayHistoricalReport(
        replay_id=replay_id,
        symbol="XAUUSD",
        timeframe=timeframe,
        trade_analytics=ReplayTradeAnalytics(
            total_trades=trades,
            wins=trades if win_rate >= 50 else 0,
            losses=0 if win_rate >= 50 else trades,
            win_rate=win_rate,
            net_rr=net_rr,
            average_rr=round(net_rr / trades, 4) if trades else 0.0,
        ),
        decision_analytics=ReplayDecisionAnalytics(
            total_decisions=10,
            simulate_buy=trades,
            simulate_sell=0,
            wait=2,
            avoid=int(block_rate / 20),
            no_trade=int(block_rate / 20),
            block_rate=block_rate,
            average_confidence=70.0 if net_rr > 0 else 35.0,
            most_common_action="SIMULATE_BUY" if trades else "NO_TRADE",
        ),
        equity_curve=[
            ReplayEquityPoint(step_index=0, balance=10000.0, equity=10000.0, drawdown=0.0, cumulative_rr=0.0),
            ReplayEquityPoint(step_index=1, balance=10000.0 + net_rr * 100.0, equity=10000.0 + net_rr * 100.0, drawdown=0.0, cumulative_rr=net_rr),
        ],
        summary="Synthetic report.",
        metadata={"total_steps": 10},
    )


def sample_calibration(replay_id: str, gate: str, total_blocked: int, block_rate: float):
    from backend.replay.replay_calibration_models import ReplayBlockReasonMetrics, ReplayCalibrationReport

    return ReplayCalibrationReport(
        replay_id=replay_id,
        symbol="XAUUSD",
        timeframe="M15",
        block_reason_metrics=ReplayBlockReasonMetrics(
            total_blocked=total_blocked,
            block_rate=block_rate,
            common_reasons=[f"{gate} blocked replay."],
            gate_counts={gate: total_blocked},
            most_restrictive_gate=gate,
        ),
        threshold_suggestions=[],
        calibration_status="TOO_RESTRICTIVE" if block_rate >= 70 else "HEALTHY",
        summary="Synthetic calibration.",
    )


def verify_files_and_routes() -> bool:
    files = [
        "backend/replay/replay_comparison_models.py",
        "backend/replay/replay_scenario_comparator.py",
        "backend/replay/replay_timeframe_comparator.py",
        "backend/replay/replay_filter_comparator.py",
        "backend/replay/replay_scenario_ranker.py",
        "backend/replay/replay_comparison_report_builder.py",
        "docs/phase-3-day-4-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/replay/compare/recent",
            "/replay/compare",
            "/replay/compare/timeframes/{symbol}",
            "/replay/compare/filters",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Comparison files and routes exist", files_ok and routes_ok)


def verify_ranker_and_comparators() -> bool:
    try:
        from backend.replay.replay_comparison_report_builder import ReplayComparisonReportBuilder
        from backend.replay.replay_filter_comparator import ReplayFilterComparator
        from backend.replay.replay_scenario_comparator import ReplayScenarioComparator
        from backend.replay.replay_scenario_ranker import ReplayScenarioRanker
        from backend.replay.replay_timeframe_comparator import ReplayTimeframeComparator

        strong = sample_report("RPL-STRONG", "M15", 66.0, 3.0, 20.0, 3)
        weak = sample_report("RPL-WEAK", "H1", 25.0, -1.5, 80.0, 2)
        empty_score = ReplayScenarioRanker().rank_scenario(sample_report("RPL-EMPTY", "M5", 0.0, 0.0, 100.0, 0))
        strong_score = ReplayScenarioRanker().rank_scenario(strong, sample_calibration("RPL-STRONG", "SESSION", 2, 20.0))
        weak_score = ReplayScenarioRanker().rank_scenario(weak, sample_calibration("RPL-WEAK", "CONFLUENCE", 8, 80.0))
        empty_comparison = ReplayScenarioComparator().compare_scenarios([])
        single_comparison = ReplayScenarioComparator().compare_scenarios([strong])
        multi_comparison = ReplayScenarioComparator().compare_scenarios(
            [weak, strong],
            [sample_calibration("RPL-WEAK", "CONFLUENCE", 8, 80.0), sample_calibration("RPL-STRONG", "SESSION", 2, 20.0)],
        )
        timeframe = ReplayTimeframeComparator().compare_timeframes([weak, strong])
        filters = ReplayFilterComparator().compare_filters(
            [sample_calibration("RPL-WEAK", "CONFLUENCE", 8, 80.0), sample_calibration("RPL-STRONG", "SESSION", 2, 20.0)]
        )
        report = ReplayComparisonReportBuilder().build_comparison_report(
            [weak, strong],
            [sample_calibration("RPL-WEAK", "CONFLUENCE", 8, 80.0), sample_calibration("RPL-STRONG", "SESSION", 2, 20.0)],
        )
        passed = (
            0.0 <= empty_score <= 100.0
            and 0.0 <= weak_score <= 100.0
            and 0.0 <= strong_score <= 100.0
            and strong_score > weak_score
            and empty_comparison.scenario_count == 0
            and single_comparison.scenario_count == 1
            and multi_comparison.scenario_count == 2
            and multi_comparison.best_scenario.replay_id == "RPL-STRONG"
            and timeframe.best_timeframe == "M15"
            and filters.most_restrictive_filter == "CONFLUENCE"
            and report.simulation_only is True
            and report.live_execution_enabled is False
        )
        return show("Ranker and scenario/timeframe/filter comparators are deterministic", passed)
    except Exception as exc:
        return show("Ranker and scenario/timeframe/filter comparators are deterministic", False, str(exc))


def verify_service_methods() -> bool:
    try:
        from backend.replay.replay_models import ReplayRunResult
        from backend.replay.replay_service import ReplayService

        service = ReplayService()
        empty = service.compare_recent_replays()
        run_a = ReplayRunResult(replay_id="RPL-A", symbol="XAUUSD", timeframe="M15", total_steps=0, step_results=[])
        run_b = ReplayRunResult(replay_id="RPL-B", symbol="XAUUSD", timeframe="H1", total_steps=0, step_results=[])
        service.storage.save_result(run_a)
        service.storage.save_result(run_b)
        by_ids = service.compare_replay_ids(["RPL-A", "RPL-B", "MISSING"])
        recent = service.compare_recent_replays(limit=5)
        timeframe = service.compare_timeframes("XAUUSD")
        filters = service.compare_filters()
        passed = (
            empty.scenario_count == 0
            and by_ids.scenario_count == 2
            and recent.scenario_count == 2
            and timeframe.symbol == "XAUUSD"
            and "M15" in timeframe.timeframes_compared
            and filters is not None
        )
        return show("Replay service exposes comparison methods with safe fallbacks", passed)
    except Exception as exc:
        return show("Replay service exposes comparison methods with safe fallbacks", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        empty_recent = client.get("/replay/compare/recent")
        empty_timeframes = client.get("/replay/compare/timeframes/XAUUSD")
        empty_filters = client.get("/replay/compare/filters")
        run_a = client.post(
            "/replay/run/XAUUSD?timeframe=M15",
            json={"window_size": 30, "step_size": 10, "max_steps": 1, "simulation_only": True},
        )
        run_b = client.post(
            "/replay/run/XAUUSD?timeframe=H1",
            json={"window_size": 30, "step_size": 10, "max_steps": 1, "simulation_only": True},
        )
        compare = client.post("/replay/compare", json=[run_a.json()["replay_id"], run_b.json()["replay_id"]])
        recent = client.get("/replay/compare/recent")
        timeframes = client.get("/replay/compare/timeframes/XAUUSD")
        filters = client.get("/replay/compare/filters")
        safety = client.get("/system/safety-scan").json()
        passed = (
            empty_recent.status_code == 200
            and empty_timeframes.status_code == 200
            and empty_filters.status_code == 200
            and run_a.status_code == 200
            and run_b.status_code == 200
            and compare.status_code == 200
            and recent.status_code == 200
            and timeframes.status_code == 200
            and filters.status_code == 200
            and compare.json()["simulation_only"] is True
            and compare.json()["live_execution_enabled"] is False
            and compare.json()["scenario_count"] == 2
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
        )
        return show("Comparison API is JSON-safe and preserves simulation-only safety", passed)
    except Exception as exc:
        return show("Comparison API is JSON-safe and preserves simulation-only safety", False, str(exc))


def main() -> int:
    print("Phase 3 Day 4 Replay Scenario Comparison Verification")
    print("=" * 58)
    checks = [
        verify_files_and_routes(),
        verify_ranker_and_comparators(),
        verify_service_methods(),
        verify_api_and_safety(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
