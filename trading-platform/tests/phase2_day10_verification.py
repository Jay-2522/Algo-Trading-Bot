import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_path(path: str, label: str) -> bool:
    passed = (PROJECT_ROOT / path).is_file()
    print_result(label, passed, "" if passed else path)
    return passed


def bullish_context(direction: str = "BULLISH", readiness: str = "READY_FOR_SIMULATION"):
    return SimpleNamespace(
        sweep_context={"sweeps": [{"sweep_id": "SWP-1", "direction": "BULLISH", "valid": True, "strength": 88.0}]},
        fvg_context={
            "fresh_fvgs": [
                {"fvg_id": "FVG-1", "direction": "BULLISH", "valid": True, "fresh": True, "strength": 90.0,
                 "gap_low": 100.0, "gap_high": 101.0}
            ]
        },
        order_block_context={
            "fresh_order_blocks": [
                {"ob_id": "OB-1", "direction": "BULLISH", "valid": True, "fresh": True, "strength": 85.0,
                 "zone_low": 99.5, "zone_high": 100.5}
            ]
        },
        breaker_context={
            "fresh_breakers": [
                {"breaker_id": "BRK-1", "direction": "BULLISH", "valid": True, "fresh": True, "strength": 82.0,
                 "zone_low": 100.0, "zone_high": 100.75}
            ]
        },
        structure_shift_context={
            "current_structure_state": "BULLISH",
            "events": [{"event_id": "STR-1", "event_type": "MSS", "direction": "BULLISH", "valid": True, "strength": 90.0}],
        },
        confluence_score={
            "dominant_direction": direction,
            "overall_score": 90.0,
            "trade_readiness": readiness,
        },
    )


def alignment(direction: str = "BULLISH") -> dict:
    return {"overall_direction": direction, "alignment_score": 90.0}


def session(readiness: str = "HIGH_QUALITY_WINDOW") -> dict:
    return {"trade_timing_readiness": readiness, "session_quality_score": 90.0}


def verify_routes() -> bool:
    try:
        from backend.main import app

        required = {
            "/institutional/session/{symbol}",
            "/institutional/entry-models/{symbol}",
            "/institutional/entry-models/best/{symbol}",
            "/institutional/entry-models/ready/{symbol}",
            "/institutional/entry-models/waiting/{symbol}",
            "/institutional/entry-models/avoided/{symbol}",
            "/institutional/entry-models/explanation/{symbol}",
        }
        missing = sorted(required - {route.path for route in app.routes})
        passed = not missing
        print_result("Entry-model routes and prior session route remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI imports with entry-model routes", False, str(exc))
        return False


def verify_detector_and_context_ranking() -> bool:
    try:
        from backend.institutional_intelligence.entry_model_context_builder import EntryModelContextBuilder

        context = EntryModelContextBuilder().build_entry_model_context(
            "XAUUSD",
            "M15",
            [],
            confluence_context=bullish_context(),
            alignment_context=alignment(),
            session_context=session(),
        )
        types = {model.model_type for model in context.models}
        passed = (
            "SWEEP_FVG_CONTINUATION" in types
            and "ORDER_BLOCK_RETRACEMENT" in types
            and "BREAKER_RETEST" in types
            and "MSS_REVERSAL" in types
            and context.best_model is not None
            and context.best_model.direction == "BULLISH"
            and context.best_model.entry_zone_low is not None
            and context.best_model.invalidation_level is not None
            and context.best_model.target_level is not None
            and context.ready_models
            and context.overall_readiness == "READY_FOR_SIMULATION"
        )
        print_result("Aligned evidence creates ranked bullish institutional entry candidates", bool(passed))
        return bool(passed)
    except Exception as exc:
        print_result("Aligned evidence creates ranked bullish institutional entry candidates", False, str(exc))
        return False


def verify_validation_and_score_bounds() -> bool:
    try:
        from backend.institutional_intelligence.entry_model_models import InstitutionalEntryModel
        from backend.institutional_intelligence.entry_model_scorer import EntryModelScorer
        from backend.institutional_intelligence.entry_model_validator import EntryModelValidator

        invalid = InstitutionalEntryModel(
            symbol="XAUUSD",
            timeframe="M15",
            model_type="ORDER_BLOCK_RETRACEMENT",
            direction="BULLISH",
            supporting_factors=["Fresh order block only."],
        )
        validation = EntryModelValidator().validate_model(invalid, bullish_context(), alignment(), session())
        score = EntryModelScorer().score_model(invalid, bullish_context(), alignment(), session())
        passed = (
            not validation.valid
            and len(validation.missing_requirements) >= 3
            and 0.0 <= score.score <= 100.0
            and score.alignment_score <= 20.0
            and score.confluence_score <= 25.0
            and score.session_score <= 15.0
        )
        print_result("Validation rejects incomplete geometry and scoring remains bounded", passed)
        return passed
    except Exception as exc:
        print_result("Validation rejects incomplete geometry and scoring remains bounded", False, str(exc))
        return False


def verify_no_trade_and_explanation() -> bool:
    try:
        from backend.institutional_intelligence.entry_model_context_builder import EntryModelContextBuilder

        context = EntryModelContextBuilder().build_entry_model_context(
            "XAUUSD",
            "M15",
            [],
            confluence_context=bullish_context("CONFLICTED", "BLOCKED_BY_RISK"),
            alignment_context=alignment("CONFLICTED"),
            session_context=session("AVOID_NEWS_WINDOW"),
        )
        best = context.best_model
        passed = (
            best is not None
            and best.model_type == "NO_TRADE"
            and best.readiness == "AVOID"
            and context.overall_readiness == "AVOID"
            and bool(best.blocking_factors)
            and "No trade" in best.metadata["explanation"]["summary"]
        )
        print_result("Conflict, risk, and session blocks produce an explained no-trade model", passed)
        return passed
    except Exception as exc:
        print_result("Conflict, risk, and session blocks produce an explained no-trade model", False, str(exc))
        return False


def verify_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.entry_model_models import EntryModelContext
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 required for entry-model verification.")

            def close(self):
                return None

        context = SMCService(market_data_service=UnavailableData()).analyze_entry_models("XAUUSD")
        passed = (
            isinstance(context, EntryModelContext)
            and context.best_model is not None
            and context.best_model.model_type == "NO_TRADE"
            and context.overall_readiness == "AVOID"
            and any("timing" in factor.lower() for factor in context.best_model.blocking_factors)
        )
        print_result("SMCService safely avoids entry qualification without MT5 liquidity evidence", passed)
        return passed
    except Exception as exc:
        print_result("SMCService safely avoids entry qualification without MT5 liquidity evidence", False, str(exc))
        return False


def verify_api_json_and_health() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("API verification does not require MT5.")

            def close(self):
                return None

        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/entry-models/XAUUSD",
                "/institutional/entry-models/best/XAUUSD",
                "/institutional/entry-models/ready/XAUUSD",
                "/institutional/entry-models/waiting/XAUUSD",
                "/institutional/entry-models/avoided/XAUUSD",
                "/institutional/entry-models/explanation/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness")
        finally:
            institutional_routes.smc_service = original
        explanation = responses[-1].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and "best_model" in responses[0].json()
            and responses[1].json()["model_type"] == "NO_TRADE"
            and explanation["simulation_only"] is True
            and explanation["live_execution_enabled"] is False
            and any(module["module_name"] == "institutional_entry_models" for module in readiness.json()["modules"])
        )
        print_result("Entry-model APIs are JSON-safe, analysis-only, and monitored", passed)
        return passed
    except Exception as exc:
        print_result("Entry-model APIs are JSON-safe, analysis-only, and monitored", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 10 Institutional Entry Model Verification")
    print("=" * 56)
    checks = [
        verify_path("backend/institutional_intelligence/entry_model_models.py", "entry_model_models.py exists"),
        verify_path("backend/institutional_intelligence/entry_model_detector.py", "entry_model_detector.py exists"),
        verify_path("backend/institutional_intelligence/entry_model_validator.py", "entry_model_validator.py exists"),
        verify_path("backend/institutional_intelligence/entry_model_scorer.py", "entry_model_scorer.py exists"),
        verify_path("backend/institutional_intelligence/entry_model_context_builder.py", "entry_model_context_builder.py exists"),
        verify_path("backend/institutional_intelligence/entry_model_explainer.py", "entry_model_explainer.py exists"),
        verify_routes(),
        verify_detector_and_context_ranking(),
        verify_validation_and_score_bounds(),
        verify_no_trade_and_explanation(),
        verify_service_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 56)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
