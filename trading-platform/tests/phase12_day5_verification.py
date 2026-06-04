import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "backend/nifty50/nifty_risk_models.py",
        "backend/nifty50/nifty_risk_engine.py",
        "backend/nifty50/nifty_trade_qualifier.py",
        "backend/nifty50/nifty_trade_decision_store.py",
        "docs/phase-12-day-5-progress.md",
        "docs/nifty50-risk-engine.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Risk models, risk engine, qualifier, decision store, and docs exist", not missing, ", ".join(missing))


def verify_engine_rules() -> bool:
    try:
        from backend.nifty50.nifty_risk_engine import NIFTYRiskEngine
        from backend.nifty50.nifty_strategy_models import NIFTYStrategySnapshot

        engine = NIFTYRiskEngine()
        low_confidence = engine.evaluate(NIFTYStrategySnapshot(strategy_bias="BULLISH", confidence=50, regime="TRENDING_BULLISH", placeholder=False))
        neutral = engine.evaluate(NIFTYStrategySnapshot(strategy_bias="NEUTRAL", confidence=85, regime="RANGING", placeholder=False))
        unknown = engine.evaluate(NIFTYStrategySnapshot(strategy_bias="BULLISH", confidence=85, regime="UNKNOWN", placeholder=False))
        bullish = engine.evaluate(NIFTYStrategySnapshot(strategy_bias="BULLISH", confidence=85, regime="TRENDING_BULLISH", placeholder=False))
        bearish = engine.evaluate(NIFTYStrategySnapshot(strategy_bias="BEARISH", confidence=90, regime="TRENDING_BEARISH", placeholder=False))
        passed = (
            low_confidence.approved is False
            and "Confidence below 70." in low_confidence.rejection_reasons
            and neutral.approved is False
            and "Strategy bias is neutral." in neutral.rejection_reasons
            and unknown.approved is False
            and "Market regime is unknown." in unknown.rejection_reasons
            and bullish.approved is True
            and bullish.execution_allowed is False
            and bullish.live_execution_enabled is False
            and bullish.broker_execution_enabled is False
            and bullish.trade_quality in {"A", "B", "A_PLUS"}
            and bearish.approved is True
            and bearish.execution_allowed is False
            and bearish.trade_quality == "A_PLUS"
        )
        return show("Risk engine rejects weak setups and approves valid analysis with execution disabled", passed)
    except Exception as exc:
        return show("Risk engine rejects weak setups and approves valid analysis with execution disabled", False, str(exc))


def verify_trade_qualifier_and_store() -> bool:
    try:
        from backend.nifty50.nifty_risk_engine import NIFTYRiskEngine
        from backend.nifty50.nifty_strategy_models import NIFTYStrategySnapshot
        from backend.nifty50.nifty_trade_decision_store import NIFTYTradeDecisionStore
        from backend.nifty50.nifty_trade_qualifier import NIFTYTradeQualifier

        store = NIFTYTradeDecisionStore()
        qualifier = NIFTYTradeQualifier(risk_engine=NIFTYRiskEngine(), decision_store=store)
        bullish = qualifier.qualify(NIFTYStrategySnapshot(strategy_bias="BULLISH", confidence=85, regime="TRENDING_BULLISH", placeholder=False))
        bearish = qualifier.qualify(NIFTYStrategySnapshot(strategy_bias="BEARISH", confidence=90, regime="TRENDING_BEARISH", placeholder=False))
        wait = qualifier.qualify(NIFTYStrategySnapshot(strategy_bias="NEUTRAL", confidence=85, regime="RANGING", placeholder=False))
        fetched = store.get_decision(bullish.risk_decision_id)
        passed = (
            bullish.action == "BUY"
            and bullish.qualified is True
            and bullish.execution_allowed is False
            and bearish.action == "SELL"
            and bearish.qualified is True
            and bearish.execution_allowed is False
            and wait.action == "WAIT"
            and wait.qualified is False
            and len(store.list_decisions()) == 3
            and len(store.list_candidates()) == 3
            and fetched is not None
        )
        return show("Trade qualifier creates BUY/SELL/WAIT candidates and decision store works", passed)
    except Exception as exc:
        return show("Trade qualifier creates BUY/SELL/WAIT candidates and decision store works", False, str(exc))


def verify_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        required = {
            "/nifty50/risk/status",
            "/nifty50/risk/evaluate",
            "/nifty50/risk/decisions",
            "/nifty50/risk/decisions/{decision_id}",
            "/nifty50/trade/qualify",
            "/nifty50/trade/candidates",
        }
        status = client.get("/nifty50/risk/status")
        decision = client.post("/nifty50/risk/evaluate")
        decisions = client.get("/nifty50/risk/decisions")
        fetched = client.get(f"/nifty50/risk/decisions/{decision.json()['decision_id']}")
        candidate = client.post("/nifty50/trade/qualify")
        candidates = client.get("/nifty50/trade/candidates")
        passed = (
            required <= route_paths
            and status.status_code == 200
            and status.json()["execution_allowed"] is False
            and decision.status_code == 200
            and decision.json()["execution_allowed"] is False
            and decision.json()["live_execution_enabled"] is False
            and decision.json()["broker_execution_enabled"] is False
            and decisions.status_code == 200
            and len(decisions.json()) >= 1
            and fetched.status_code == 200
            and fetched.json()["decision_id"] == decision.json()["decision_id"]
            and candidate.status_code == 200
            and candidate.json()["execution_allowed"] is False
            and candidates.status_code == 200
            and len(candidates.json()) >= 1
        )
        return show("Risk and trade qualification routes are registered and work", passed)
    except Exception as exc:
        return show("Risk and trade qualification routes are registered and work", False, str(exc))


def verify_readiness_and_executive() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        readiness = client.get("/nifty50/readiness").json()
        instruments = client.get("/client-analytics/executive/instruments").json()
        summary = client.get("/client-analytics/executive/summary").json()
        nifty = next((item for item in instruments["instruments"] if item["symbol"] == "NIFTY50"), {})
        passed = (
            readiness["status"] in {"RISK_QUALIFICATION_READY", "EXECUTION_BRIDGE_READY"}
            and readiness["market_data_ready"] is True
            and readiness["strategy_ready"] is True
            and readiness["risk_ready"] is True
            and readiness["execution_ready"] is False
            and readiness["live_execution_enabled"] is False
            and readiness["broker_execution_enabled"] is False
            and nifty["status"] in {"RISK_QUALIFICATION_READY", "EXECUTION_BRIDGE_READY"}
            and nifty["ready"] is False
            and summary["nifty50_ready"] is False
            and summary["overall_completion_percentage"] in {97, 98}
        )
        return show("Readiness and executive dashboard upgraded honestly with NIFTY50 still not ready", passed)
    except Exception as exc:
        return show("Readiness and executive dashboard upgraded honestly with NIFTY50 still not ready", False, str(exc))


def verify_no_broker_api_or_order_send() -> bool:
    try:
        forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "yfinance", "kiteconnect", "smartapi", "dhanhq", "fyers_apiv3", "upstox_client"]
        offenders = []
        for path in (PROJECT_ROOT / "backend" / "nifty50").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in forbidden:
                if token.lower() in text:
                    offenders.append(f"{path.name}:{token}")
        token = "mt5." + "order_send"
        order_matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                order_matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        return show(
            "No broker APIs, no order placement, and no new mt5.order_send added",
            not offenders and order_matches == ["backend/demo_execution/mt5_demo_executor.py"],
            ", ".join(offenders + order_matches),
        )
    except Exception as exc:
        return show("No broker APIs, no order placement, and no new mt5.order_send added", False, str(exc))


def main() -> int:
    print("Phase 12 Day 5 NIFTY50 Risk Engine & Trade Qualification Verification")
    print("=" * 78)
    checks = [
        verify_files(),
        verify_engine_rules(),
        verify_trade_qualifier_and_store(),
        verify_routes(),
        verify_readiness_and_executive(),
        verify_no_broker_api_or_order_send(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
