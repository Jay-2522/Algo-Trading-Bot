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
        "backend/nifty50/nifty_execution_models.py",
        "backend/nifty50/nifty_execution_validator.py",
        "backend/nifty50/nifty_order_mapper.py",
        "backend/nifty50/nifty_execution_bridge.py",
        "backend/nifty50/nifty_execution_store.py",
        "backend/nifty50/nifty_broker_order_preview.py",
        "docs/phase-12-day-6-progress.md",
        "docs/nifty50-execution-bridge.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Execution models, validator, mapper, bridge, store, preview, and docs exist", not missing, ", ".join(missing))


def verify_validator_mapper_preview_and_store() -> bool:
    try:
        from backend.nifty50.nifty_broker_order_preview import NIFTYBrokerOrderPreview
        from backend.nifty50.nifty_execution_bridge import NIFTYExecutionBridge
        from backend.nifty50.nifty_execution_models import NIFTYExecutionIntent
        from backend.nifty50.nifty_execution_validator import NIFTYExecutionValidator
        from backend.nifty50.nifty_order_mapper import NIFTYOrderMapper
        from backend.nifty50.nifty_risk_models import NIFTYTradeCandidate

        validator = NIFTYExecutionValidator()
        wait_candidate = NIFTYTradeCandidate(action="WAIT", confidence=0, strategy_bias="NEUTRAL", trade_quality="NO_TRADE", risk_decision_id="risk-wait", qualified=False, rejection_reasons=["No setup"])
        unqualified = NIFTYTradeCandidate(action="BUY", confidence=75, strategy_bias="BULLISH", trade_quality="B", risk_decision_id="risk-low", qualified=False, rejection_reasons=["Blocked"])
        qualified = NIFTYTradeCandidate(action="BUY", confidence=82, strategy_bias="BULLISH", trade_quality="A", risk_decision_id="risk-ok", qualified=True, rejection_reasons=[])
        wait_reasons = validator.validate_candidate(wait_candidate)
        unqualified_reasons = validator.validate_candidate(unqualified)
        intent = NIFTYExecutionIntent(candidate_id=qualified.candidate_id, action="BUY", quantity=1, broker_id=None, strategy_confidence=82, risk_decision_id=qualified.risk_decision_id)
        intent_reasons = validator.validate_intent(intent)
        mapper = NIFTYOrderMapper()
        dhan = mapper.map_to_broker_order(intent.model_copy(update={"broker_id": "dhan"}), "dhan")
        angel = mapper.map_to_broker_order(intent.model_copy(update={"broker_id": "angel_one"}), "angel_one")
        preview = NIFTYBrokerOrderPreview(validator).create_preview(intent)
        bridge = NIFTYExecutionBridge()
        stored_intent = bridge.create_intent_from_candidate(qualified)
        stored_preview = bridge.preview_order(stored_intent)
        passed = (
            "WAIT candidate cannot be converted to execution intent." in wait_reasons
            and "Candidate is not qualified." in unqualified_reasons
            and "Broker not selected." in intent_reasons
            and "Execution disabled; preview only." in intent_reasons
            and dhan["broker"] == "Dhan"
            and dhan["placeholder"] is True
            and dhan["api_call_enabled"] is False
            and angel["broker"] == "Angel One"
            and angel["placeholder"] is True
            and preview.preview_status == "BROKER_NOT_SELECTED"
            and preview.broker_execution_enabled is False
            and stored_preview.preview_status in {"BROKER_NOT_SELECTED", "BLOCKED_EXECUTION_DISABLED"}
            and len(bridge.store.list_intents()) == 1
            and len(bridge.store.list_previews()) == 1
            and len(bridge.store.list_audit_events()) >= 2
        )
        return show("Validator, mapper, preview, bridge, and audit store work safely", passed)
    except Exception as exc:
        return show("Validator, mapper, preview, bridge, and audit store work safely", False, str(exc))


def verify_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        required = {
            "/nifty50/execution/status",
            "/nifty50/execution/create-intent",
            "/nifty50/execution/preview-order",
            "/nifty50/execution/intents",
            "/nifty50/execution/intents/{intent_id}",
            "/nifty50/execution/previews",
            "/nifty50/execution/previews/{preview_id}",
            "/nifty50/execution/audit-events",
        }
        status = client.get("/nifty50/execution/status")
        intent = client.post("/nifty50/execution/create-intent")
        preview = client.post("/nifty50/execution/preview-order")
        intents = client.get("/nifty50/execution/intents")
        fetched_intent = client.get(f"/nifty50/execution/intents/{intent.json()['intent_id']}")
        previews = client.get("/nifty50/execution/previews")
        fetched_preview = client.get(f"/nifty50/execution/previews/{preview.json()['preview_id']}")
        audit = client.get("/nifty50/execution/audit-events")
        passed = (
            required <= route_paths
            and status.status_code == 200
            and status.json()["preview_only"] is True
            and status.json()["execution_allowed"] is False
            and intent.status_code == 200
            and intent.json()["execution_allowed"] is False
            and intent.json()["live_execution_enabled"] is False
            and intent.json()["broker_execution_enabled"] is False
            and preview.status_code == 200
            and preview.json()["broker_execution_enabled"] is False
            and preview.json()["preview_status"] in {"BROKER_NOT_SELECTED", "BLOCKED_EXECUTION_DISABLED", "REJECTED"}
            and intents.status_code == 200
            and len(intents.json()) >= 1
            and fetched_intent.status_code == 200
            and fetched_intent.json()["intent_id"] == intent.json()["intent_id"]
            and previews.status_code == 200
            and len(previews.json()) >= 1
            and fetched_preview.status_code == 200
            and fetched_preview.json()["preview_id"] == preview.json()["preview_id"]
            and audit.status_code == 200
            and len(audit.json()) >= 2
        )
        return show("Execution bridge routes are registered and preview-only behavior works", passed)
    except Exception as exc:
        return show("Execution bridge routes are registered and preview-only behavior works", False, str(exc))


def verify_readiness_and_executive() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        readiness = client.get("/nifty50/readiness").json()
        instruments = client.get("/client-analytics/executive/instruments").json()
        summary = client.get("/client-analytics/executive/summary").json()
        nifty = next((item for item in instruments["instruments"] if item["symbol"] == "NIFTY50"), {})
        passed = (
            readiness["status"] in {"EXECUTION_BRIDGE_READY", "ANALYTICS_INTEGRATED"}
            and readiness["market_data_ready"] is True
            and readiness["strategy_ready"] is True
            and readiness["risk_ready"] is True
            and readiness["execution_bridge_ready"] is True
            and readiness["execution_ready"] is False
            and readiness["live_execution_enabled"] is False
            and readiness["broker_execution_enabled"] is False
            and nifty["status"] in {"EXECUTION_BRIDGE_READY", "ANALYTICS_INTEGRATED"}
            and nifty["ready"] is False
            and summary["nifty50_ready"] is False
            and summary["overall_completion_percentage"] in {98, 99}
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


def verify_phase12_preserved() -> bool:
    try:
        from backend.main import app

        required = {
            "/nifty50/status",
            "/nifty50/market-data/health",
            "/nifty50/strategy/snapshot",
            "/nifty50/risk/status",
            "/nifty50/trade/candidates",
            "/nifty50/execution/status",
        }
        registered = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        return show("Phase 12 Day 1-5 routes are preserved", required <= registered)
    except Exception as exc:
        return show("Phase 12 Day 1-5 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 12 Day 6 NIFTY50 Execution Bridge & Broker Adapter Preparation Verification")
    print("=" * 88)
    checks = [
        verify_files(),
        verify_validator_mapper_preview_and_store(),
        verify_routes(),
        verify_readiness_and_executive(),
        verify_no_broker_api_or_order_send(),
        verify_phase12_preserved(),
    ]
    print("=" * 88)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
