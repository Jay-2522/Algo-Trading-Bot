import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def sample_contexts():
    from backend.institutional_intelligence.paper_trade_models import (
        PaperTradeCandidate,
        PaperTradeLifecycleContext,
        PaperTradePosition,
    )
    from backend.institutional_intelligence.position_management_models import (
        BreakEvenAdjustment,
        EmergencyExitSignal,
        InstitutionalPositionManagement,
        ManagementDecision,
        PartialTakeProfit,
        StructuralExitSignal,
        TrailingStopAdjustment,
    )
    from backend.institutional_intelligence.setup_validator_models import SetupValidationContext, SetupValidationResult
    from backend.institutional_intelligence.simulation_decision_models import (
        InstitutionalSimulationDecision,
        SimulationDecisionContext,
        SimulationOrderIntent,
    )

    now = datetime.now(timezone.utc)
    validations = [
        SetupValidationResult(
            symbol="XAUUSD", timeframe="M15", model_type="SWEEP_FVG_CONTINUATION", direction="BULLISH",
            approved_for_simulation=True, overall_score=90, confidence=88, readiness="APPROVED",
        ),
        SetupValidationResult(
            symbol="XAUUSD", timeframe="M15", model_type="ORDER_BLOCK_RETRACEMENT", direction="BULLISH",
            overall_score=30, confidence=32, readiness="REJECTED",
            rejection_reasons=["Session timing quality is poor."],
        ),
        SetupValidationResult(
            symbol="XAUUSD", timeframe="M15", model_type="ORDER_BLOCK_RETRACEMENT", direction="BEARISH",
            overall_score=34, confidence=35, readiness="REJECTED",
            rejection_reasons=["Session timing quality is poor.", "Confluence conflict detected."],
        ),
        SetupValidationResult(
            symbol="XAUUSD", timeframe="M15", model_type="MSS_REVERSAL", direction="BULLISH",
            overall_score=58, confidence=59, readiness="WAIT",
        ),
    ]
    setup_contexts = [SetupValidationContext(symbol="XAUUSD", timeframe="M15", validations=validations)]
    decisions = []
    for index, (action, confidence, reasons) in enumerate([
        ("SIMULATE_BUY", 88.0, []),
        ("AVOID", 35.0, ["Session timing quality is poor."]),
        ("NO_TRADE", 30.0, ["Confluence conflict detected."]),
        ("WAIT", 58.0, []),
    ]):
        intent = SimulationOrderIntent(symbol="XAUUSD", timeframe="M15", direction="NONE")
        decision = InstitutionalSimulationDecision(
            symbol="XAUUSD", timeframe="M15", action=action,
            approved_for_simulation=action == "SIMULATE_BUY",
            readiness="APPROVED_FOR_SIMULATION" if action == "SIMULATE_BUY" else (
                "BLOCKED" if action in {"AVOID", "NO_TRADE"} else "WAIT_FOR_CONFIRMATION"
            ),
            confidence=confidence, order_intent=intent, rejection_reasons=reasons,
        )
        decisions.append(
            SimulationDecisionContext(
                symbol="XAUUSD", timeframe="M15",
                validation_context=setup_contexts[0], decision=decision,
            )
        )
    candidates = [
        PaperTradeCandidate(
            candidate_id="C1", symbol="XAUUSD", timeframe="M15", direction="BUY",
            source_decision_id="D1", source_intent_id="I1", entry_low=100, entry_high=101,
            invalidation_level=99, target_level=104, estimated_rr=2.0, quality_score=90,
            expires_at=now + timedelta(days=1), status="CLOSED",
        ),
        PaperTradeCandidate(
            candidate_id="C2", symbol="XAUUSD", timeframe="M15", direction="SELL",
            source_decision_id="D2", source_intent_id="I2", entry_low=100, entry_high=101,
            invalidation_level=102, target_level=97, estimated_rr=2.0, quality_score=70,
            expires_at=now + timedelta(days=1), status="CLOSED",
        ),
    ]
    closed = [
        PaperTradePosition(
            position_id="P1", candidate_id="C1", symbol="XAUUSD", direction="BUY",
            entry_price=100.5, invalidation_level=99, target_level=104, status="CLOSED",
            outcome="WIN", pnl_points=3.0, rr_result=2.0, close_reason="TARGET",
        ),
        PaperTradePosition(
            position_id="P2", candidate_id="C2", symbol="XAUUSD", direction="SELL",
            entry_price=100.5, invalidation_level=102, target_level=97, status="CLOSED",
            outcome="LOSS", pnl_points=-1.5, rr_result=-1.0, close_reason="INVALIDATION",
        ),
    ]
    paper_context = PaperTradeLifecycleContext(
        symbol="XAUUSD", timeframe="M15", candidates=candidates, closed_positions=closed,
        lifecycle_status="POSITION_CLOSED",
    )
    management_context = InstitutionalPositionManagement(
        symbol="XAUUSD", timeframe="M15",
        decisions=[ManagementDecision(position_id="P1", action="TRAIL_STOP", reason="Protect.", confidence=82)],
        partial_take_profits=[
            PartialTakeProfit(
                position_id="P1", level="TP1", trigger_price=101.5, rr_level=1.0,
                reduction_percent=50, remaining_size=0.5, realized_rr=0.5, reason="TP1.",
            )
        ],
        break_even_adjustments=[
            BreakEvenAdjustment(position_id="P1", applied=True, previous_stop=99, adjusted_stop=100.5, reason="BE.")
        ],
        trailing_stop_adjustments=[
            TrailingStopAdjustment(position_id="P1", applied=True, previous_stop=100.5, adjusted_stop=101, reason="Trail.")
        ],
        structural_exit_signals=[
            StructuralExitSignal(position_id="P2", exit_required=True, exit_reason="Opposing MSS.", confidence=86)
        ],
        emergency_exit=EmergencyExitSignal(
            position_id="P2", triggered=True, trigger_source="RISK_ENGINE", severity="CRITICAL",
            shutdown_reason="Risk engine status is BLOCKED.", emergency_action="CLOSE_SIMULATION_POSITION",
        ),
    )
    return setup_contexts, decisions, [paper_context, paper_context], [management_context]


class UnavailableData:
    def get_candles(self, *args, **kwargs):
        raise RuntimeError("No MT5 required for performance verification.")

    def close(self):
        return None


def verify_files_routes() -> bool:
    files = [
        "backend/institutional_intelligence/performance_analytics_models.py",
        "backend/institutional_intelligence/setup_performance_analyzer.py",
        "backend/institutional_intelligence/decision_quality_analyzer.py",
        "backend/institutional_intelligence/paper_trade_performance_analyzer.py",
        "backend/institutional_intelligence/position_management_analyzer.py",
        "backend/institutional_intelligence/rejection_pattern_analyzer.py",
        "backend/institutional_intelligence/optimization_recommendation_engine.py",
        "backend/institutional_intelligence/performance_analytics_context_builder.py",
        "docs/phase-2-day-17-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app
        routes = {route.path for route in app.routes}
        expected = {
            "/institutional/reasoning/{symbol}",
            "/institutional/performance/{symbol}",
            "/institutional/performance/setups/{symbol}",
            "/institutional/performance/decisions/{symbol}",
            "/institutional/performance/paper-trades/{symbol}",
            "/institutional/performance/position-management/{symbol}",
            "/institutional/performance/recommendations/{symbol}",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Day 17 files and performance routes exist with reasoning preserved", files_ok and routes_ok)


def verify_analyzers() -> bool:
    try:
        from backend.institutional_intelligence.decision_quality_analyzer import DecisionQualityAnalyzer
        from backend.institutional_intelligence.paper_trade_performance_analyzer import PaperTradePerformanceAnalyzer
        from backend.institutional_intelligence.position_management_analyzer import PositionManagementAnalyzer
        from backend.institutional_intelligence.setup_performance_analyzer import SetupPerformanceAnalyzer

        setup, decision, paper, management = sample_contexts()
        setup_metrics = SetupPerformanceAnalyzer().analyze_setups(setup)
        decision_metrics = DecisionQualityAnalyzer().analyze_decisions(decision)
        paper_metrics = PaperTradePerformanceAnalyzer().analyze_paper_trades(paper)
        management_metrics = PositionManagementAnalyzer().analyze_position_management(management)
        passed = (
            setup_metrics.total_setups == 4
            and setup_metrics.approval_rate == 25.0
            and setup_metrics.best_setup_type == "SWEEP_FVG_CONTINUATION"
            and decision_metrics.total_decisions == 4
            and decision_metrics.decision_block_rate == 50.0
            and paper_metrics.total_candidates == 2
            and paper_metrics.closed_positions == 2
            and paper_metrics.win_rate == 50.0
            and paper_metrics.average_rr == 0.5
            and management_metrics.partial_tp_count == 1
            and management_metrics.break_even_moves == 1
            and management_metrics.emergency_exits == 1
        )
        return show("Metric analyzers calculate setup, decision, paper, and management results deterministically", passed)
    except Exception as exc:
        return show("Metric analyzers calculate setup, decision, paper, and management results deterministically", False, str(exc))


def verify_context_recommendations_and_empty() -> bool:
    try:
        from backend.institutional_intelligence.performance_analytics_context_builder import PerformanceAnalyticsContextBuilder

        setup, decisions, paper, management = sample_contexts()
        builder = PerformanceAnalyticsContextBuilder()
        populated = builder.build_performance_context(
            "XAUUSD", "M15",
            {
                "setup_validation_contexts": setup,
                "simulation_decision_contexts": decisions,
                "paper_trade_contexts": paper,
                "position_management_contexts": management,
                "sample_count": 3,
            },
        )
        empty = builder.build_performance_context("XAUUSD", "M15")
        categories = {item.category for item in populated.recommendations}
        passed = (
            populated.optimization_status in {"NEEDS_ATTENTION", "DEGRADED", "HEALTHY"}
            and populated.overall_health_score > 0
            and "SESSION_TIMING" in categories
            and "CONFLUENCE" in categories
            and "RISK" in categories
            and empty.optimization_status == "INSUFFICIENT_DATA"
            and len(empty.recommendations) == 1
        )
        return show("Context produces optimization guidance and safe insufficient-data output", passed)
    except Exception as exc:
        return show("Context produces optimization guidance and safe insufficient-data output", False, str(exc))


def verify_service_and_api_safety() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        fallback = SMCService(market_data_service=UnavailableData()).analyze_performance_analytics("XAUUSD")
        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/performance/XAUUSD",
                "/institutional/performance/setups/XAUUSD",
                "/institutional/performance/decisions/XAUUSD",
                "/institutional/performance/paper-trades/XAUUSD",
                "/institutional/performance/position-management/XAUUSD",
                "/institutional/performance/recommendations/XAUUSD",
            ]
            responses = [client.get(path) for path in endpoints]
            readiness = client.get("/system/readiness").json()
            safety = client.get("/system/safety-scan").json()
        finally:
            institutional_routes.smc_service = original
        data = responses[0].json()
        serialized = str(data).lower()
        passed = (
            fallback.optimization_status == "INSUFFICIENT_DATA"
            and fallback.simulation_only is True
            and fallback.live_execution_enabled is False
            and all(response.status_code == 200 for response in responses)
            and data["simulation_only"] is True
            and data["live_execution_enabled"] is False
            and ("live trading " + "is active") not in serialized
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and any(module["module_name"] == "institutional_performance" for module in readiness["modules"])
        )
        return show("Performance API fails safely without data and remains analytics-only", passed)
    except Exception as exc:
        return show("Performance API fails safely without data and remains analytics-only", False, str(exc))


def main() -> int:
    print("Phase 2 Day 17 Institutional Performance Analytics Verification")
    print("=" * 62)
    tests = [
        verify_files_routes(),
        verify_analyzers(),
        verify_context_recommendations_and_empty(),
        verify_service_and_api_safety(),
    ]
    print("=" * 62)
    print("PASS" if all(tests) else "FAIL")
    return 0 if all(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
