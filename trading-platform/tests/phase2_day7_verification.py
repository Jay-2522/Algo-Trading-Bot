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


def aligned_contexts() -> dict:
    return {
        "institutional_context": {
            "structure_bias": {"bias": "BULLISH", "confidence": 90.0},
            "premium_discount": {"zone": "DISCOUNT"},
            "displacement": [{"direction": "BULLISH", "valid": True}],
        },
        "sweep_context": {
            "sweeps": [{"direction": "BULLISH", "valid": True, "strength": 90.0}]
        },
        "fvg_context": {
            "fresh_fvgs": [{"direction": "BULLISH", "valid": True, "strength": 90.0}],
            "mitigated_fvgs": [],
        },
        "order_block_context": {
            "fresh_order_blocks": [{"direction": "BULLISH", "valid": True, "strength": 90.0}],
            "mitigated_order_blocks": [],
        },
        "breaker_context": {
            "fresh_breakers": [{"direction": "BULLISH", "valid": True, "strength": 90.0}],
            "mitigated_breakers": [],
        },
        "structure_shift_context": {
            "events": [{"event_type": "MSS", "direction": "BULLISH", "valid": True, "strength": 90.0}]
        },
        "session_context": {"current_session": "London", "high_liquidity": True},
        "risk_status": {"overall_status": "OPERATIONAL"},
    }


def verify_routes() -> bool:
    try:
        from backend.main import app

        paths = {route.path for route in app.routes}
        required = {
            "/system/status",
            "/institutional/status",
            "/institutional/breakers/{symbol}",
            "/institutional/structure-shift/{symbol}",
            "/institutional/confluence/{symbol}",
            "/institutional/confluence/score/{symbol}",
            "/institutional/confluence/explanation/{symbol}",
            "/institutional/confluence/components/{symbol}",
            "/institutional/confluence/readiness/{symbol}",
        }
        missing = sorted(required - paths)
        passed = not missing
        print_result("Confluence, prior institutional, and Phase 1 routes remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI app imports with confluence routes", False, str(exc))
        return False


def verify_scoring_weights_and_quality() -> bool:
    try:
        from backend.institutional_intelligence.confluence_scorer import InstitutionalConfluenceScorer

        score = InstitutionalConfluenceScorer().score_confluence("XAUUSD", "M15", **aligned_contexts())
        weights = sum(component.weight for component in score.component_scores)
        passed = (
            len(score.component_scores) == 10
            and weights == 100.0
            and score.dominant_direction == "BULLISH"
            and score.bullish_score > score.bearish_score
            and score.setup_quality == "A_PLUS"
            and score.trade_readiness == "READY_FOR_SIMULATION"
            and score.overall_score >= 85
            and score.confidence >= 80
        )
        print_result("Confluence weights total 100 and aligned institutional evidence ranks A PLUS", passed)
        return passed
    except Exception as exc:
        print_result("Confluence weights total 100 and aligned institutional evidence ranks A PLUS", False, str(exc))
        return False


def verify_mitigation_conflict_and_risk() -> bool:
    try:
        from backend.institutional_intelligence.confluence_scorer import InstitutionalConfluenceScorer

        scorer = InstitutionalConfluenceScorer()
        contexts = aligned_contexts()
        fresh = scorer.score_confluence("XAUUSD", "M15", **contexts)
        contexts["fvg_context"] = {
            "fresh_fvgs": [],
            "mitigated_fvgs": [{"direction": "BULLISH", "valid": True, "strength": 90.0}],
        }
        mitigated = scorer.score_confluence("XAUUSD", "M15", **contexts)
        contexts["risk_status"] = {"overall_status": "BLOCKED"}
        blocked = scorer.score_confluence("XAUUSD", "M15", **contexts)
        conflict = scorer.score_confluence(
            "XAUUSD",
            "M15",
            institutional_context={
                "structure_bias": {"bias": "BULLISH", "confidence": 90.0},
                "premium_discount": {"zone": "PREMIUM"},
                "displacement": [{"direction": "BEARISH", "valid": True}],
            },
            sweep_context={"sweeps": [{"direction": "BEARISH", "valid": True, "strength": 95.0}]},
            fvg_context={"fresh_fvgs": [{"direction": "BULLISH", "valid": True, "strength": 95.0}]},
            order_block_context={"fresh_order_blocks": [{"direction": "BEARISH", "valid": True, "strength": 95.0}]},
            breaker_context={"fresh_breakers": [{"direction": "BULLISH", "valid": True, "strength": 95.0}]},
            structure_shift_context={"events": [{"event_type": "MSS", "direction": "BULLISH", "valid": True, "strength": 95.0}]},
            session_context={"current_session": "London", "high_liquidity": True},
            risk_status={"overall_status": "OPERATIONAL"},
        )
        passed = (
            fresh.overall_score > mitigated.overall_score
            and blocked.trade_readiness == "BLOCKED_BY_RISK"
            and any("Risk readiness" in warning for warning in blocked.warnings)
            and conflict.dominant_direction == "CONFLICTED"
            and conflict.setup_quality == "NO_TRADE"
        )
        print_result("Mitigation reduces score, risk blocks readiness, and directional conflict prevents setup", passed)
        return passed
    except Exception as exc:
        print_result("Mitigation reduces score, risk blocks readiness, and directional conflict prevents setup", False, str(exc))
        return False


def verify_explanation_and_safe_builder() -> bool:
    try:
        from backend.institutional_intelligence.confluence_context_builder import ConfluenceContextBuilder
        from backend.institutional_intelligence.confluence_models import ConfluenceContext
        from backend.institutional_intelligence.confluence_scorer import InstitutionalConfluenceScorer

        class BrokenInstitutionalBuilder:
            def build_context(self, *args, **kwargs):
                raise RuntimeError("Component unavailable.")

        score = InstitutionalConfluenceScorer().score_confluence("XAUUSD", "M15", **aligned_contexts())
        safe_context = ConfluenceContextBuilder(
            institutional_builder=BrokenInstitutionalBuilder()
        ).build_confluence_context("XAUUSD", "M15", [])
        passed = (
            bool(score.explanation)
            and bool(score.strengths)
            and isinstance(score.warnings, list)
            and isinstance(safe_context, ConfluenceContext)
            and safe_context.institutional_context.symbol == "XAUUSD"
            and len(safe_context.confluence_score.component_scores) == 10
        )
        print_result("Explainer produces dashboard content and sub-module failure degrades safely", passed)
        return passed
    except Exception as exc:
        print_result("Explainer produces dashboard content and sub-module failure degrades safely", False, str(exc))
        return False


def verify_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 needed for confluence verification.")

            def close(self):
                return None

        context = SMCService(market_data_service=UnavailableData()).analyze_confluence("XAUUSD")
        passed = (
            context.symbol == "XAUUSD"
            and context.institutional_context.swings == []
            and len(context.confluence_score.component_scores) == 10
            and context.confluence_score.setup_quality == "NO_TRADE"
        )
        print_result("SMCService safely returns scored empty context without MT5", passed)
        return passed
    except Exception as exc:
        print_result("SMCService safely returns scored empty context without MT5", False, str(exc))
        return False


def verify_api_json_and_health() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("API JSON verification does not require MT5.")

            def close(self):
                return None

        client = TestClient(app)
        service = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/confluence/XAUUSD",
                "/institutional/confluence/score/XAUUSD",
                "/institutional/confluence/explanation/XAUUSD",
                "/institutional/confluence/components/XAUUSD",
                "/institutional/confluence/readiness/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness")
        finally:
            institutional_routes.smc_service = service
        readiness_json = responses[-1].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and "confluence_score" in responses[0].json()
            and "overall_score" in responses[1].json()
            and "explanation" in responses[2].json()
            and len(responses[3].json()) == 10
            and readiness_json["simulation_only"] is True
            and readiness_json["live_execution_enabled"] is False
            and any(module["module_name"] == "institutional_confluence" for module in readiness.json()["modules"])
        )
        print_result("Confluence APIs are JSON-safe, analysis-only, and readiness monitored", passed)
        return passed
    except Exception as exc:
        print_result("Confluence APIs are JSON-safe, analysis-only, and readiness monitored", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 7 Institutional Confluence Scoring Verification")
    print("=" * 56)
    checks = [
        verify_path("backend/institutional_intelligence/confluence_models.py", "confluence_models.py exists"),
        verify_path("backend/institutional_intelligence/confluence_scorer.py", "confluence_scorer.py exists"),
        verify_path("backend/institutional_intelligence/confluence_context_builder.py", "confluence_context_builder.py exists"),
        verify_path("backend/institutional_intelligence/confluence_explainer.py", "confluence_explainer.py exists"),
        verify_path("backend/institutional_intelligence/setup_quality_classifier.py", "setup_quality_classifier.py exists"),
        verify_routes(),
        verify_scoring_weights_and_quality(),
        verify_mitigation_conflict_and_risk(),
        verify_explanation_and_safe_builder(),
        verify_service_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 56)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
