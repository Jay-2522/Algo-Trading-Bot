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


def validation(direction: str = "BULLISH", readiness: str = "APPROVED", approved: bool = True):
    from backend.institutional_intelligence.setup_validator_models import SetupValidationResult

    return SetupValidationResult(
        validation_id=f"VAL-{direction}-{readiness}",
        symbol="XAUUSD",
        timeframe="M15",
        model_type="SWEEP_FVG_CONTINUATION",
        direction=direction,
        source_model_id=f"ENT-{direction}",
        entry_zone_low=100.0,
        entry_zone_high=101.0,
        invalidation_level=99.0 if direction == "BULLISH" else 102.0,
        target_level=103.5 if direction == "BULLISH" else 97.5,
        approved_for_simulation=approved,
        overall_score=90.0 if approved else 70.0,
        confidence=88.0 if approved else 70.0,
        readiness=readiness,
        approval_reasons=["Institutional gates passed."] if approved else [],
    )


def validation_context(result, approved: bool = True):
    from backend.institutional_intelligence.setup_validator_models import SetupApprovalDecision, SetupValidationContext

    decision = SetupApprovalDecision(
        approved=approved,
        approval_grade="INSTITUTIONAL_A_PLUS" if approved else "INSTITUTIONAL_B",
        execution_readiness="APPROVED" if approved else "CONDITIONAL",
        simulation_eligible=approved,
        requires_confirmation=not approved,
        institutional_quality="INSTITUTIONAL A PLUS" if approved else "INSTITUTIONAL B",
        explanation="Assessment complete.",
    )
    return SetupValidationContext(
        symbol="XAUUSD",
        timeframe="M15",
        validations=[result],
        decisions=[decision],
        approved_setups=[result] if approved else [],
        waiting_setups=[] if approved else [result],
        best_setup=result,
        best_decision=decision,
        simulation_eligible=approved,
        execution_readiness="APPROVED" if approved else "CONDITIONAL",
        confidence=result.confidence,
    )


def verify_routes() -> bool:
    try:
        from backend.main import app

        required = {
            "/institutional/setup-validation/{symbol}",
            "/institutional/simulation-decision/{symbol}",
            "/institutional/simulation-decision/action/{symbol}",
            "/institutional/simulation-decision/intent/{symbol}",
            "/institutional/simulation-decision/explanation/{symbol}",
            "/institutional/simulation-decision/readiness/{symbol}",
        }
        missing = sorted(required - {route.path for route in app.routes})
        passed = not missing
        print_result("Simulation-decision routes and setup-validation route remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI imports with simulation-decision routes", False, str(exc))
        return False


def verify_rr_estimator_and_intent() -> bool:
    try:
        from backend.institutional_intelligence.simulation_intent_builder import SimulationIntentBuilder
        from backend.institutional_intelligence.simulation_risk_estimator import SimulationRiskEstimator

        estimator = SimulationRiskEstimator()
        rr = estimator.estimate_rr(100.0, 101.0, 99.0, 103.5, "BUY")
        invalid = estimator.estimate_rr(100.0, 101.0, 101.0, 103.5, "BUY")
        intent = SimulationIntentBuilder(estimator).build_order_intent(validation())
        passed = (
            rr == 2.0
            and estimator.classify_risk_quality(rr) == "GOOD"
            and invalid == 0.0
            and estimator.classify_risk_quality(invalid) == "INVALID"
            and intent.direction == "BUY"
            and intent.risk_quality == "GOOD"
            and intent.simulation_only is True
        )
        print_result("RR calculation and analytical BUY intent are deterministic and bounded", passed)
        return passed
    except Exception as exc:
        print_result("RR calculation and analytical BUY intent are deterministic and bounded", False, str(exc))
        return False


def verify_approved_and_conditional_decisions() -> bool:
    try:
        from backend.institutional_intelligence.simulation_decision_pipeline import InstitutionalSimulationDecisionPipeline

        pipeline = InstitutionalSimulationDecisionPipeline()
        selected, approved = pipeline.generate_decision(
            validation_context(validation()),
            risk_status={"overall_status": "OPERATIONAL"},
            news_status={"active_blackout": False, "trading_allowed": True},
            session_context={"trade_timing_readiness": "HIGH_QUALITY_WINDOW"},
        )
        conditional_result = validation(readiness="CONDITIONAL", approved=False)
        _, conditional = pipeline.generate_decision(
            validation_context(conditional_result, approved=False),
            risk_status={"overall_status": "OPERATIONAL"},
            session_context={"trade_timing_readiness": "NORMAL_MONITORING"},
        )
        passed = (
            selected is not None
            and approved.action == "SIMULATE_BUY"
            and approved.readiness == "APPROVED_FOR_SIMULATION"
            and approved.approved_for_simulation
            and approved.live_execution_enabled is False
            and conditional.action == "WAIT"
            and conditional.readiness == "WAIT_FOR_CONFIRMATION"
            and not conditional.approved_for_simulation
        )
        print_result("Approved setup simulates while conditional setup remains waiting", passed)
        return passed
    except Exception as exc:
        print_result("Approved setup simulates while conditional setup remains waiting", False, str(exc))
        return False


def verify_blocks_clear_intent() -> bool:
    try:
        from backend.institutional_intelligence.simulation_decision_pipeline import InstitutionalSimulationDecisionPipeline

        _, blocked = InstitutionalSimulationDecisionPipeline().generate_decision(
            validation_context(validation()),
            risk_status={"overall_status": "BLOCKED"},
            news_status={"active_blackout": True, "trading_allowed": False},
            session_context={"trade_timing_readiness": "AVOID_NEWS_WINDOW"},
        )
        passed = (
            blocked.action == "AVOID"
            and blocked.readiness == "BLOCKED"
            and not blocked.approved_for_simulation
            and blocked.order_intent.direction == "NONE"
            and blocked.order_intent.source_validation_id == "VAL-BULLISH-APPROVED"
            and len(blocked.rejection_reasons) >= 3
        )
        print_result("Risk/news/session restrictions block simulation and clear actionable intent", passed)
        return passed
    except Exception as exc:
        print_result("Risk/news/session restrictions block simulation and clear actionable intent", False, str(exc))
        return False


def verify_context_builder_and_fallback() -> bool:
    try:
        from backend.institutional_intelligence.simulation_decision_context_builder import SimulationDecisionContextBuilder
        from backend.institutional_intelligence.smc_service import SMCService

        built = SimulationDecisionContextBuilder().build_simulation_decision_context(
            "XAUUSD",
            "M15",
            [],
            validation_context=validation_context(validation()),
            risk_status={"overall_status": "OPERATIONAL"},
            session_context={"trade_timing_readiness": "HIGH_QUALITY_WINDOW"},
        )

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 required for simulation-decision verification.")

            def close(self):
                return None

        fallback = SMCService(market_data_service=UnavailableData()).analyze_simulation_decision("XAUUSD")
        passed = (
            built.decision.action == "SIMULATE_BUY"
            and built.selected_validation is not None
            and fallback.decision.action in {"AVOID", "NO_TRADE"}
            and fallback.decision.approved_for_simulation is False
            and fallback.decision.order_intent.direction == "NONE"
        )
        print_result("Context builder selects approved intent and service falls back safely without MT5", passed)
        return passed
    except Exception as exc:
        print_result("Context builder selects approved intent and service falls back safely without MT5", False, str(exc))
        return False


def verify_api_json_and_health() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("API simulation-decision verification does not require MT5.")

            def close(self):
                return None

        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/simulation-decision/XAUUSD",
                "/institutional/simulation-decision/action/XAUUSD",
                "/institutional/simulation-decision/intent/XAUUSD",
                "/institutional/simulation-decision/explanation/XAUUSD",
                "/institutional/simulation-decision/readiness/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness")
        finally:
            institutional_routes.smc_service = original
        action = responses[1].json()
        intent = responses[2].json()
        status = responses[-1].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and action["simulation_only"] is True
            and action["live_execution_enabled"] is False
            and intent["direction"] == "NONE"
            and status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and any(module["module_name"] == "institutional_simulation_decision" for module in readiness.json()["modules"])
        )
        print_result("Simulation-decision APIs are JSON-safe, simulation-only, and monitored", passed)
        return passed
    except Exception as exc:
        print_result("Simulation-decision APIs are JSON-safe, simulation-only, and monitored", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 12 Institutional Simulation Decision Verification")
    print("=" * 62)
    checks = [
        verify_path("backend/institutional_intelligence/simulation_decision_models.py", "simulation_decision_models.py exists"),
        verify_path("backend/institutional_intelligence/simulation_decision_pipeline.py", "simulation_decision_pipeline.py exists"),
        verify_path("backend/institutional_intelligence/simulation_intent_builder.py", "simulation_intent_builder.py exists"),
        verify_path("backend/institutional_intelligence/simulation_risk_estimator.py", "simulation_risk_estimator.py exists"),
        verify_path("backend/institutional_intelligence/simulation_decision_explainer.py", "simulation_decision_explainer.py exists"),
        verify_path("backend/institutional_intelligence/simulation_decision_context_builder.py", "simulation_decision_context_builder.py exists"),
        verify_routes(),
        verify_rr_estimator_and_intent(),
        verify_approved_and_conditional_decisions(),
        verify_blocks_clear_intent(),
        verify_context_builder_and_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 62)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
