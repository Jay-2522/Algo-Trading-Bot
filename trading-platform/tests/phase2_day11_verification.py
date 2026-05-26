import sys
from pathlib import Path

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


def entry_model(direction: str = "BULLISH", model_type: str = "SWEEP_FVG_CONTINUATION"):
    from backend.institutional_intelligence.entry_model_models import InstitutionalEntryModel

    return InstitutionalEntryModel(
        symbol="XAUUSD",
        timeframe="M15",
        model_type=model_type,
        direction=direction if model_type != "NO_TRADE" else "NEUTRAL",
        entry_zone_low=100.0 if model_type != "NO_TRADE" else None,
        entry_zone_high=101.0 if model_type != "NO_TRADE" else None,
        invalidation_level=99.0 if model_type != "NO_TRADE" else None,
        target_level=103.0 if model_type != "NO_TRADE" else None,
        confidence=90.0,
        quality_score=90.0,
        readiness="READY_FOR_SIMULATION" if model_type != "NO_TRADE" else "AVOID",
        supporting_factors=["Validated bullish sweep.", "Fresh bullish FVG."],
        blocking_factors=["No qualified evidence."] if model_type == "NO_TRADE" else [],
    )


def confluence(direction: str = "BULLISH", readiness: str = "READY_FOR_SIMULATION") -> dict:
    return {
        "confluence_score": {
            "dominant_direction": direction,
            "overall_score": 90.0,
            "confidence": 88.0,
            "trade_readiness": readiness,
        }
    }


def alignment(direction: str = "BULLISH", quality: str = "FULLY_ALIGNED") -> dict:
    return {"overall_direction": direction, "alignment_quality": quality, "alignment_score": 92.0}


def session(readiness: str = "HIGH_QUALITY_WINDOW") -> dict:
    return {
        "trade_timing_readiness": readiness,
        "session_quality_score": 90.0,
        "active_killzone": {"active_killzone": True},
        "liquidity_profile": {"liquidity_quality": "HIGH"},
    }


def verify_routes() -> bool:
    try:
        from backend.main import app

        required = {
            "/institutional/entry-models/{symbol}",
            "/institutional/setup-validation/{symbol}",
            "/institutional/setup-validation/approved/{symbol}",
            "/institutional/setup-validation/waiting/{symbol}",
            "/institutional/setup-validation/rejected/{symbol}",
            "/institutional/setup-validation/best/{symbol}",
            "/institutional/setup-validation/readiness/{symbol}",
        }
        missing = sorted(required - {route.path for route in app.routes})
        passed = not missing
        print_result("Setup-validation routes and prior entry-model route remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI imports with setup-validation routes", False, str(exc))
        return False


def verify_gatekeepers_and_approval() -> bool:
    try:
        from backend.institutional_intelligence.setup_approval_engine import SetupApprovalEngine
        from backend.institutional_intelligence.setup_validator_engine import SetupValidatorEngine

        result = SetupValidatorEngine().validate_setup(
            entry_model(),
            confluence_context=confluence(),
            alignment_context=alignment(),
            session_context=session(),
            risk_context={"overall_status": "OPERATIONAL"},
        )
        decision = SetupApprovalEngine().generate_decision(result)
        passed = (
            result.approved_for_simulation
            and result.readiness == "APPROVED"
            and result.overall_score >= 85.0
            and all(rule.passed for rule in result.rules)
            and decision.approved
            and decision.approval_grade == "INSTITUTIONAL_A_PLUS"
            and decision.simulation_eligible
        )
        print_result("Aligned high-quality setup earns institutional A Plus simulation approval", passed)
        return passed
    except Exception as exc:
        print_result("Aligned high-quality setup earns institutional A Plus simulation approval", False, str(exc))
        return False


def verify_critical_rejection_rules() -> bool:
    try:
        from backend.institutional_intelligence.setup_approval_engine import SetupApprovalEngine
        from backend.institutional_intelligence.setup_validator_engine import SetupValidatorEngine

        result = SetupValidatorEngine().validate_setup(
            entry_model(),
            confluence_context=confluence("CONFLICTED", "BLOCKED_BY_RISK"),
            alignment_context=alignment("BEARISH", "CONFLICTED"),
            session_context=session("AVOID_NEWS_WINDOW"),
            risk_context={"overall_status": "BLOCKED"},
        )
        decision = SetupApprovalEngine().generate_decision(result)
        categories = {rule.category for rule in result.rules if not rule.passed and rule.severity == "CRITICAL"}
        passed = (
            result.readiness == "REJECTED"
            and not result.approved_for_simulation
            and {"ALIGNMENT", "NEWS", "CONFLUENCE", "RISK"}.issubset(categories)
            and decision.approval_grade == "REJECTED"
            and not decision.simulation_eligible
        )
        print_result("Contradictory, news-blocked, and risk-blocked setup is rejected", passed)
        return passed
    except Exception as exc:
        print_result("Contradictory, news-blocked, and risk-blocked setup is rejected", False, str(exc))
        return False


def verify_risk_and_structure_integrity() -> bool:
    try:
        from backend.institutional_intelligence.risk_gatekeeper import RiskGatekeeper
        from backend.institutional_intelligence.setup_validator_engine import SetupValidatorEngine

        weak_rr = entry_model()
        weak_rr = weak_rr.model_copy(update={"target_level": 101.2})
        risk_rules = RiskGatekeeper().validate_risk(weak_rr, {"overall_status": "OPERATIONAL"})
        no_trade = SetupValidatorEngine().validate_setup(
            entry_model(model_type="NO_TRADE"),
            confluence_context=confluence(),
            alignment_context=alignment(),
            session_context=session(),
            risk_context={"overall_status": "OPERATIONAL"},
        )
        passed = (
            not risk_rules[0].passed
            and risk_rules[0].severity == "CRITICAL"
            and no_trade.readiness == "REJECTED"
            and any(rule.category == "STRUCTURE" and not rule.passed for rule in no_trade.rules)
        )
        print_result("Weak reward-to-risk and no-trade structure cannot pass final approval", passed)
        return passed
    except Exception as exc:
        print_result("Weak reward-to-risk and no-trade structure cannot pass final approval", False, str(exc))
        return False


def verify_context_classification() -> bool:
    try:
        from backend.institutional_intelligence.entry_model_models import EntryModelContext
        from backend.institutional_intelligence.setup_validation_context_builder import SetupValidationContextBuilder

        entries = EntryModelContext(
            symbol="XAUUSD",
            timeframe="M15",
            models=[entry_model()],
            best_model=entry_model(),
            ready_models=[entry_model()],
            overall_readiness="READY_FOR_SIMULATION",
            confidence=90.0,
        )
        context = SetupValidationContextBuilder().build_validation_context(
            "XAUUSD",
            "M15",
            [],
            entry_model_context=entries,
            confluence_context=confluence(),
            alignment_context=alignment(),
            session_context=session(),
            risk_context={"overall_status": "OPERATIONAL"},
        )
        passed = (
            context.simulation_eligible
            and context.execution_readiness == "APPROVED"
            and len(context.approved_setups) == 1
            and context.best_decision is not None
            and context.best_decision.approval_grade == "INSTITUTIONAL_A_PLUS"
        )
        print_result("Validation context separates and selects approved institutional setups", passed)
        return passed
    except Exception as exc:
        print_result("Validation context separates and selects approved institutional setups", False, str(exc))
        return False


def verify_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.setup_validator_models import SetupValidationContext
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 required for setup validation.")

            def close(self):
                return None

        context = SMCService(market_data_service=UnavailableData()).analyze_setup_validation("XAUUSD")
        passed = (
            isinstance(context, SetupValidationContext)
            and not context.simulation_eligible
            and context.execution_readiness == "REJECTED"
            and context.rejected_setups
        )
        print_result("SMCService rejects simulation eligibility safely without MT5", passed)
        return passed
    except Exception as exc:
        print_result("SMCService rejects simulation eligibility safely without MT5", False, str(exc))
        return False


def verify_api_json_and_health() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("API setup-validation test does not require MT5.")

            def close(self):
                return None

        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/setup-validation/XAUUSD",
                "/institutional/setup-validation/approved/XAUUSD",
                "/institutional/setup-validation/waiting/XAUUSD",
                "/institutional/setup-validation/rejected/XAUUSD",
                "/institutional/setup-validation/best/XAUUSD",
                "/institutional/setup-validation/readiness/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness")
        finally:
            institutional_routes.smc_service = original
        decision = responses[-1].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and responses[0].json()["simulation_eligible"] is False
            and responses[3].json()
            and decision["simulation_only"] is True
            and decision["live_execution_enabled"] is False
            and any(module["module_name"] == "institutional_setup_validation" for module in readiness.json()["modules"])
        )
        print_result("Setup-validation APIs are JSON-safe, simulation-only, and monitored", passed)
        return passed
    except Exception as exc:
        print_result("Setup-validation APIs are JSON-safe, simulation-only, and monitored", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 11 Trade Setup Validator and Execution Readiness Verification")
    print("=" * 70)
    checks = [
        verify_path("backend/institutional_intelligence/setup_validator_models.py", "setup_validator_models.py exists"),
        verify_path("backend/institutional_intelligence/setup_validator_engine.py", "setup_validator_engine.py exists"),
        verify_path("backend/institutional_intelligence/risk_gatekeeper.py", "risk_gatekeeper.py exists"),
        verify_path("backend/institutional_intelligence/alignment_gatekeeper.py", "alignment_gatekeeper.py exists"),
        verify_path("backend/institutional_intelligence/session_gatekeeper.py", "session_gatekeeper.py exists"),
        verify_path("backend/institutional_intelligence/confluence_gatekeeper.py", "confluence_gatekeeper.py exists"),
        verify_path("backend/institutional_intelligence/setup_approval_engine.py", "setup_approval_engine.py exists"),
        verify_path("backend/institutional_intelligence/setup_validation_context_builder.py", "setup_validation_context_builder.py exists"),
        verify_routes(),
        verify_gatekeepers_and_approval(),
        verify_critical_rejection_rules(),
        verify_risk_and_structure_integrity(),
        verify_context_classification(),
        verify_service_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 70)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
