import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_files() -> bool:
    files = [
        "backend/institutional_intelligence/paper_trade_models.py",
        "backend/institutional_intelligence/paper_trade_lifecycle.py",
        "backend/institutional_intelligence/paper_trade_tracker.py",
        "backend/institutional_intelligence/paper_trade_outcome_evaluator.py",
        "backend/institutional_intelligence/paper_trade_storage.py",
        "backend/institutional_intelligence/paper_trade_context_builder.py",
        "docs/phase-2-day-13-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    passed = not missing
    print_result("Day 13 implementation and documentation files exist", passed, str(missing))
    return passed


def decision_context(direction: str = "BUY", approved: bool = True):
    from backend.institutional_intelligence.setup_validator_models import SetupValidationContext
    from backend.institutional_intelligence.simulation_decision_models import (
        InstitutionalSimulationDecision,
        SimulationDecisionContext,
        SimulationOrderIntent,
    )

    buy = direction == "BUY"
    intent = SimulationOrderIntent(
        symbol="XAUUSD",
        timeframe="M15",
        direction=direction if approved else "NONE",
        entry_low=100.0 if approved else None,
        entry_high=101.0 if approved else None,
        invalidation_level=(99.0 if buy else 102.0) if approved else None,
        target_level=(103.5 if buy else 97.5) if approved else None,
        estimated_rr=2.0 if approved else 0.0,
        risk_quality="GOOD" if approved else "INVALID",
    )
    decision = InstitutionalSimulationDecision(
        symbol="XAUUSD",
        timeframe="M15",
        action=("SIMULATE_BUY" if buy else "SIMULATE_SELL") if approved else "NO_TRADE",
        approved_for_simulation=approved,
        readiness="APPROVED_FOR_SIMULATION" if approved else "NO_VALID_SETUP",
        confidence=88.0 if approved else 0.0,
        setup_quality="INSTITUTIONAL_A" if approved else "NO_SETUP",
        selected_model_type="ORDER_BLOCK_RETRACEMENT" if approved else None,
        order_intent=intent,
    )
    return SimulationDecisionContext(
        symbol="XAUUSD",
        timeframe="M15",
        validation_context=SetupValidationContext(symbol="XAUUSD", timeframe="M15"),
        decision=decision,
    )


def candle(time: datetime, high: float, low: float) -> dict:
    return {"time": time, "open": low, "high": high, "low": low, "close": high}


def verify_routes() -> bool:
    try:
        from backend.main import app

        required = {
            "/institutional/simulation-decision/{symbol}",
            "/institutional/paper-trades/{symbol}",
            "/institutional/paper-trades/candidates/{symbol}",
            "/institutional/paper-trades/active/{symbol}",
            "/institutional/paper-trades/closed/{symbol}",
            "/institutional/paper-trades/latest/{symbol}",
            "/institutional/paper-trades/summary/{symbol}",
        }
        missing = sorted(required - {route.path for route in app.routes})
        passed = not missing
        print_result("Paper trade routes and simulation-decision route remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI imports with paper trade routes", False, str(exc))
        return False


def verify_candidate_safety() -> bool:
    try:
        from backend.institutional_intelligence.paper_trade_lifecycle import PaperTradeLifecycleEngine

        engine = PaperTradeLifecycleEngine()
        candidate = engine.create_candidate_from_decision(decision_context())
        blocked = engine.create_candidate_from_decision(decision_context(approved=False))
        passed = (
            candidate is not None
            and candidate.status == "PENDING"
            and candidate.simulation_only is True
            and candidate.direction == "BUY"
            and blocked is None
        )
        print_result("Only approved simulation intent creates paper candidate", passed)
        return passed
    except Exception as exc:
        print_result("Only approved simulation intent creates paper candidate", False, str(exc))
        return False


def verify_tracking_and_outcome() -> bool:
    try:
        from backend.institutional_intelligence.paper_trade_lifecycle import PaperTradeLifecycleEngine
        from backend.institutional_intelligence.paper_trade_tracker import PaperTradeTracker

        engine = PaperTradeLifecycleEngine()
        tracker = PaperTradeTracker(engine)
        now = datetime.now(timezone.utc) + timedelta(minutes=1)
        buy = engine.create_candidate_from_decision(decision_context("BUY"))
        assert buy is not None
        _, winning = tracker.update_candidate(
            buy,
            [candle(now, 101.0, 100.2), candle(now + timedelta(minutes=15), 103.6, 100.0)],
        )
        ambiguous = engine.create_candidate_from_decision(decision_context("BUY"))
        assert ambiguous is not None
        _, losing = tracker.update_candidate(ambiguous, [candle(now, 104.0, 98.0)])
        sell = engine.create_candidate_from_decision(decision_context("SELL"))
        assert sell is not None
        _, selling = tracker.update_candidate(
            sell,
            [candle(now, 101.0, 100.0), candle(now + timedelta(minutes=15), 101.0, 97.0)],
        )
        passed = (
            winning is not None
            and winning.outcome == "WIN"
            and winning.rr_result > 0
            and losing is not None
            and losing.outcome == "LOSS"
            and losing.close_reason == "INVALIDATION"
            and selling is not None
            and selling.outcome == "WIN"
        )
        print_result("Tracker activates BUY/SELL positions and applies conservative stop-first outcome", passed)
        return passed
    except Exception as exc:
        print_result("Tracker activates BUY/SELL positions and applies conservative stop-first outcome", False, str(exc))
        return False


def verify_expiry_storage_and_context() -> bool:
    try:
        from backend.institutional_intelligence.paper_trade_context_builder import PaperTradeContextBuilder
        from backend.institutional_intelligence.paper_trade_lifecycle import PaperTradeLifecycleEngine
        from backend.institutional_intelligence.paper_trade_storage import PaperTradeStorage
        from backend.institutional_intelligence.paper_trade_tracker import PaperTradeTracker

        engine = PaperTradeLifecycleEngine()
        candidate = engine.create_candidate_from_decision(decision_context())
        assert candidate is not None
        expired = engine.expire_candidate(candidate, candidate.expires_at + timedelta(seconds=1))
        storage = PaperTradeStorage()
        builder = PaperTradeContextBuilder(lifecycle=engine, tracker=PaperTradeTracker(engine), storage=storage)
        now = datetime.now(timezone.utc) + timedelta(minutes=1)
        context = builder.build_paper_trade_context(
            "XAUUSD",
            "M15",
            [candle(now, 101.0, 100.2), candle(now + timedelta(minutes=15), 103.6, 100.0)],
            decision_context=decision_context(),
        )
        repeated = builder.build_paper_trade_context(
            "XAUUSD",
            "M15",
            [candle(now, 101.0, 100.2), candle(now + timedelta(minutes=15), 103.6, 100.0)],
            decision_context=decision_context(),
        )
        passed = (
            expired.status == "EXPIRED"
            and context.lifecycle_status == "POSITION_CLOSED"
            and context.closed_positions[0].outcome == "WIN"
            and len(repeated.candidates) == 1
            and len(repeated.closed_positions) == 1
            and len(storage.get_logs()) >= 3
        )
        print_result("Expiry, lifecycle logging, and repeated reads remain idempotent", passed)
        return passed
    except Exception as exc:
        print_result("Expiry, lifecycle logging, and repeated reads remain idempotent", False, str(exc))
        return False


def verify_fallback_and_api() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 required for paper trade verification.")

            def close(self):
                return None

        service = SMCService(market_data_service=UnavailableData())
        fallback = service.analyze_paper_trade_lifecycle("XAUUSD")
        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/paper-trades/XAUUSD",
                "/institutional/paper-trades/candidates/XAUUSD",
                "/institutional/paper-trades/active/XAUUSD",
                "/institutional/paper-trades/closed/XAUUSD",
                "/institutional/paper-trades/latest/XAUUSD",
                "/institutional/paper-trades/summary/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness").json()
        finally:
            institutional_routes.smc_service = original
        summary = responses[-1].json()
        passed = (
            fallback.lifecycle_status in {"BLOCKED", "NO_CANDIDATE"}
            and not fallback.active_positions
            and all(response.status_code == 200 for response in responses)
            and summary["simulation_only"] is True
            and summary["live_execution_enabled"] is False
            and any(module["module_name"] == "institutional_paper_trades" for module in readiness["modules"])
        )
        print_result("API is JSON-safe and service fails closed without market data", passed)
        return passed
    except Exception as exc:
        print_result("API is JSON-safe and service fails closed without market data", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 13 Paper Trade Lifecycle Verification")
    print("=" * 47)
    results = [
        verify_files(),
        verify_routes(),
        verify_candidate_safety(),
        verify_tracking_and_outcome(),
        verify_expiry_storage_and_context(),
        verify_fallback_and_api(),
    ]
    print("=" * 47)
    if all(results):
        print("PASS")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
