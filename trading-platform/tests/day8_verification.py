import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_path(path: str, label: str, is_dir: bool = False) -> bool:
    target = PROJECT_ROOT / path
    passed = target.is_dir() if is_dir else target.is_file()
    print_result(label, passed, "" if passed else path)
    return passed


def strong_context() -> dict:
    return {
        "trend_analysis": {"trend": "bullish"},
        "liquidity_analysis": {"potential_stop_hunt_zones": [{"level": 2300.0}]},
        "structure_analysis": {
            "bos": {"detected": True, "direction": "bullish"},
            "choch": {"detected": False},
        },
        "session_info": {"current_session": "London", "high_liquidity": True},
    }


def verify_routes() -> bool:
    try:
        from backend.main import app

        routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        required = {
            "/health",
            "/status",
            "/market-data/timeframes",
            "/strategy/session",
            "/risk/status",
            "/execution/status",
            "/mt5/status",
            "/database/status",
            "/ai/status",
            "/ai/regime/{symbol}",
            "/ai/signal-score/{symbol}",
            "/ai/decision/{symbol}",
            "/ai/full-analysis/{symbol}",
            "/ai/confidence/{symbol}",
        }
        missing = sorted(required - routes)
        print_result("FastAPI app imports and AI/old routes registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("FastAPI app imports and AI/old routes registered", False, str(exc))
        return False


def verify_confidence_engine() -> bool:
    try:
        from backend.ai_engine.ai_models import SignalScore
        from backend.ai_engine.confidence_engine import ConfidenceEngine

        score = SignalScore(
            trend_score=90,
            liquidity_score=85,
            structure_score=90,
            session_score=85,
            volatility_score=80,
            spread_score=90,
            risk_score=95,
            overall_score=88,
        )
        confidence = ConfidenceEngine().calculate_confidence(score)
        passed = 75 <= confidence <= 100
        print_result("ConfidenceEngine works", passed, str(confidence) if not passed else "")
        return passed
    except Exception as exc:
        print_result("ConfidenceEngine works", False, str(exc))
        return False


def verify_regime_classifier() -> bool:
    try:
        from backend.ai_engine.regime_classifier import RegimeClassifier

        regime = RegimeClassifier().classify_market_regime(85, "NORMAL", 8, 85, "London")
        passed = regime.regime == "TRENDING"
        print_result("RegimeClassifier works", passed, str(regime) if not passed else "")
        return passed
    except Exception as exc:
        print_result("RegimeClassifier works", False, str(exc))
        return False


def verify_signal_scorer() -> bool:
    try:
        from backend.ai_engine.signal_scorer import SignalScorer

        score = SignalScorer().score_trade_setup(
            strong_context()["trend_analysis"],
            strong_context()["liquidity_analysis"],
            strong_context()["structure_analysis"],
            strong_context()["session_info"],
            spread_quality=90,
            risk_status={"overall_status": "OPERATIONAL"},
            volatility_quality=85,
        )
        passed = score.overall_score >= 75 and score.risk_score == 90
        print_result("SignalScorer works", passed, str(score) if not passed else "")
        return passed
    except Exception as exc:
        print_result("SignalScorer works", False, str(exc))
        return False


def verify_decision_engine() -> bool:
    try:
        from backend.ai_engine.decision_engine import DecisionEngine
        from backend.risk_engine.risk_service import RiskService

        decision = DecisionEngine(risk_service=RiskService()).generate_trade_decision("XAUUSD", strong_context())
        passed = decision.action == "BUY" and decision.approved and decision.confidence >= 75
        print_result("DecisionEngine generates decision", passed, str(decision) if not passed else "")
        return passed
    except Exception as exc:
        print_result("DecisionEngine generates decision", False, str(exc))
        return False


def verify_orchestrator() -> bool:
    try:
        from backend.ai_engine.ai_orchestrator import AIOrchestrator
        from backend.ai_engine.decision_engine import DecisionEngine
        from backend.risk_engine.risk_service import RiskService

        orchestrator = AIOrchestrator(decision_engine=DecisionEngine(risk_service=RiskService()))
        result = orchestrator.generate_full_analysis("XAUUSD", strong_context(), persist=False)
        required = {"decision", "explanation", "signal_score", "regime", "persistence"}
        passed = required.issubset(result.keys()) and result["decision"].approved
        print_result("AIOrchestrator returns structured output", passed)
        return passed
    except Exception as exc:
        print_result("AIOrchestrator returns structured output", False, str(exc))
        return False


def main() -> int:
    print("Day 8 AI Decision Layer Verification")
    print("=" * 36)

    checks = [
        verify_path("backend/ai_engine", "ai_engine folder exists", is_dir=True),
        verify_path("backend/ai_engine/ai_models.py", "ai_models.py exists"),
        verify_path("backend/ai_engine/confidence_engine.py", "confidence_engine.py exists"),
        verify_path("backend/ai_engine/regime_classifier.py", "regime_classifier.py exists"),
        verify_path("backend/ai_engine/volatility_analyzer.py", "volatility_analyzer.py exists"),
        verify_path("backend/ai_engine/signal_scorer.py", "signal_scorer.py exists"),
        verify_path("backend/ai_engine/decision_engine.py", "decision_engine.py exists"),
        verify_path("backend/ai_engine/ai_orchestrator.py", "ai_orchestrator.py exists"),
        verify_path("backend/ai_engine/decision_logger.py", "decision_logger.py exists"),
        verify_path("backend/api/ai_routes.py", "ai_routes.py exists"),
        verify_routes(),
        verify_confidence_engine(),
        verify_regime_classifier(),
        verify_signal_scorer(),
        verify_decision_engine(),
        verify_orchestrator(),
    ]

    print("=" * 36)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

