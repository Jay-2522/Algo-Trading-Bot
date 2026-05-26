import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def result(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def managed(direction: str = "BUY"):
    from backend.institutional_intelligence.position_management_models import ManagedPosition

    return ManagedPosition(
        position_id=f"PPP-{direction}",
        candidate_id=f"PPC-{direction}",
        symbol="XAUUSD",
        timeframe="M15",
        direction=direction,
        entry_price=100.0,
        initial_stop=99.0 if direction == "BUY" else 101.0,
        current_stop=99.0 if direction == "BUY" else 101.0,
        target_level=104.0 if direction == "BUY" else 96.0,
        initial_risk=1.0,
        opened_at=datetime.now(timezone.utc),
    )


def active_paper_context():
    from backend.institutional_intelligence.paper_trade_models import PaperTradeLifecycleContext, PaperTradePosition

    position = PaperTradePosition(
        position_id="PPP-CONTEXT",
        candidate_id="PPC-CONTEXT",
        symbol="XAUUSD",
        direction="BUY",
        entry_price=100.0,
        invalidation_level=99.0,
        target_level=104.0,
    )
    return PaperTradeLifecycleContext(
        symbol="XAUUSD",
        timeframe="M15",
        active_positions=[position],
        latest_position=position,
        lifecycle_status="POSITION_ACTIVE",
    )


def verify_files_and_routes() -> bool:
    paths = [
        "backend/institutional_intelligence/position_management_models.py",
        "backend/institutional_intelligence/partial_take_profit_manager.py",
        "backend/institutional_intelligence/break_even_manager.py",
        "backend/institutional_intelligence/trailing_stop_manager.py",
        "backend/institutional_intelligence/structural_exit_detector.py",
        "backend/institutional_intelligence/session_exit_manager.py",
        "backend/institutional_intelligence/emergency_risk_exit.py",
        "backend/institutional_intelligence/position_state_machine.py",
        "backend/institutional_intelligence/position_management_context_builder.py",
        "docs/phase-2-day-14-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in paths)
    try:
        from backend.main import app

        expected = {
            "/institutional/paper-trades/{symbol}",
            "/institutional/position-management/{symbol}",
            "/institutional/position-management/active/{symbol}",
            "/institutional/position-management/exits/{symbol}",
            "/institutional/position-management/emergency/{symbol}",
            "/institutional/position-management/state/{symbol}",
            "/institutional/position-management/context/{symbol}",
        }
        routes_ok = expected <= {route.path for route in app.routes}
    except Exception:
        routes_ok = False
    return result("Day 14 files and routes are registered with prior paper routes preserved", files_ok and routes_ok)


def verify_state_machine() -> bool:
    try:
        from backend.institutional_intelligence.position_state_machine import PositionStateMachine

        machine = PositionStateMachine()
        position, _ = machine.transition(managed(), "PARTIAL_TP_1", "TP1")
        position, _ = machine.transition(position, "BREAK_EVEN", "Protected")
        position, _ = machine.transition(position, "TRAILING", "Trail")
        position, _ = machine.transition(position, "PARTIAL_TP_2", "TP2")
        invalid_blocked = False
        try:
            machine.transition(managed(), "PARTIAL_TP_2", "Invalid jump")
        except ValueError:
            invalid_blocked = True
        emergency, _ = machine.transition(managed(), "EMERGENCY_EXIT", "Risk failure")
        return result(
            "State machine permits institutional path and blocks invalid transitions",
            position.state == "PARTIAL_TP_2" and invalid_blocked and emergency.state == "EMERGENCY_EXIT",
        )
    except Exception as exc:
        return result("State machine permits institutional path and blocks invalid transitions", False, str(exc))


def verify_profit_protection() -> bool:
    try:
        from backend.institutional_intelligence.break_even_manager import BreakEvenManager
        from backend.institutional_intelligence.partial_take_profit_manager import PartialTakeProfitManager
        from backend.institutional_intelligence.trailing_stop_manager import TrailingStopManager

        position, partials = PartialTakeProfitManager().evaluate(
            managed(),
            [{"high": 102.3, "low": 100.6, "close": 102.1}, {"high": 103.0, "low": 100.8, "close": 102.8}],
        )
        position, break_even = BreakEvenManager().apply_break_even(position)
        position, trailing = TrailingStopManager().adjust_stop(position, [
            {"high": 102.3, "low": 100.6, "close": 102.1},
            {"high": 103.0, "low": 100.8, "close": 102.8},
        ])
        sell, sell_partials = PartialTakeProfitManager().evaluate(managed("SELL"), [{"low": 97.8, "high": 99.4}])
        passed = (
            [partial.level for partial in partials] == ["TP1", "TP2"]
            and position.remaining_size == 0.25
            and position.realized_rr == 1.0
            and break_even.applied
            and position.current_stop > position.entry_price
            and trailing.applied
            and [partial.level for partial in sell_partials] == ["TP1", "TP2"]
            and sell.remaining_size == 0.25
        )
        return result("Partial TP, break-even, and trailing protection are deterministic for both directions", passed)
    except Exception as exc:
        return result("Partial TP, break-even, and trailing protection are deterministic for both directions", False, str(exc))


def verify_exit_detectors() -> bool:
    try:
        from backend.institutional_intelligence.emergency_risk_exit import EmergencyRiskExit
        from backend.institutional_intelligence.session_exit_manager import SessionExitManager
        from backend.institutional_intelligence.structural_exit_detector import StructuralExitDetector

        structural = StructuralExitDetector().detect_exit(
            managed(),
            {"events": [{"event_type": "MSS", "direction": "BEARISH", "valid": True, "strength": 86.0}]},
            {"breaker_blocks": []},
        )
        timed = SessionExitManager().evaluate_exit(
            managed().model_copy(update={"metadata": {"entry_killzone": "LONDON_OPEN"}}),
            {
                "trade_timing_readiness": "AVOID_LOW_LIQUIDITY",
                "liquidity_profile": {"liquidity_quality": "POOR"},
                "active_killzone": {"active_killzone": False},
            },
            datetime(2026, 5, 26, 14, 0, tzinfo=timezone.utc),
        )
        emergency = EmergencyRiskExit().evaluate_emergency(managed(), {"overall_status": "BLOCKED"})
        passed = (
            structural.exit_required
            and structural.severity == "CRITICAL"
            and timed is not None
            and timed.action == "EXIT_SIMULATION"
            and "has ended" in timed.reason
            and emergency.triggered
            and emergency.emergency_action == "CLOSE_SIMULATION_POSITION"
        )
        return result("Structural, session, and emergency exits fail simulated positions closed", passed)
    except Exception as exc:
        return result("Structural, session, and emergency exits fail simulated positions closed", False, str(exc))


def verify_context_and_degradation() -> bool:
    try:
        from backend.institutional_intelligence.position_management_context_builder import PositionManagementContextBuilder
        from backend.institutional_intelligence.smc_service import SMCService

        context = PositionManagementContextBuilder().build_position_management_context(
            "XAUUSD",
            "M15",
            [{"high": 102.3, "low": 100.6, "close": 102.1}, {"high": 103.0, "low": 100.8, "close": 102.8}],
            paper_context=active_paper_context(),
            structure_context={"events": [], "current_structure_state": "BULLISH"},
            session_context={"trade_timing_readiness": "NORMAL_MONITORING", "liquidity_profile": {"liquidity_quality": "NORMAL"}},
            risk_context={"overall_status": "OPERATIONAL"},
        )

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 required for Day 14 verification.")

            def close(self):
                return None

        fallback = SMCService(market_data_service=UnavailableData()).get_position_management("XAUUSD")
        passed = (
            context.management_status == "MANAGING"
            and context.simulation_only is True
            and context.live_execution_enabled is False
            and fallback.management_status == "NO_POSITION"
            and not fallback.active_positions
        )
        return result("Context manages active paper positions and degrades safely without MT5", passed)
    except Exception as exc:
        return result("Context manages active paper positions and degrades safely without MT5", False, str(exc))


def verify_api_safety() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("API does not require MT5.")

            def close(self):
                return None

        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/position-management/XAUUSD",
                "/institutional/position-management/active/XAUUSD",
                "/institutional/position-management/exits/XAUUSD",
                "/institutional/position-management/emergency/XAUUSD",
                "/institutional/position-management/state/XAUUSD",
                "/institutional/position-management/context/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            health = client.get("/system/readiness").json()
            safety = client.get("/system/safety-scan").json()
        finally:
            institutional_routes.smc_service = original
        payload = responses[0].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and payload["simulation_only"] is True
            and payload["live_execution_enabled"] is False
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and any(module["module_name"] == "institutional_position_management" for module in health["modules"])
        )
        return result("Position management APIs remain JSON-safe and simulation-only", passed)
    except Exception as exc:
        return result("Position management APIs remain JSON-safe and simulation-only", False, str(exc))


def main() -> int:
    print("Phase 2 Day 14 Institutional Position Management Verification")
    print("=" * 60)
    tests = [
        verify_files_and_routes(),
        verify_state_machine(),
        verify_profit_protection(),
        verify_exit_detectors(),
        verify_context_and_degradation(),
        verify_api_safety(),
    ]
    print("=" * 60)
    print("PASS" if all(tests) else "FAIL")
    return 0 if all(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
