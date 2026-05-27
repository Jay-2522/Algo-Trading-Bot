import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_routes() -> bool:
    files = [
        "backend/webhooks/webhook_orchestration_models.py",
        "backend/webhooks/webhook_institutional_context_checker.py",
        "backend/webhooks/webhook_risk_gate.py",
        "backend/webhooks/webhook_broker_routing_preview.py",
        "backend/webhooks/webhook_orchestration_engine.py",
        "backend/webhooks/webhook_orchestration_store.py",
        "backend/webhooks/webhook_orchestration_service.py",
        "docs/phase-3-day-13-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/webhooks/orchestration/status",
            "/webhooks/orchestration/decisions",
            "/webhooks/orchestration/decisions/{decision_id}",
            "/webhooks/orchestration/test",
            "/webhooks/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Webhook orchestration files and routes exist", files_ok and routes_ok)


def make_signal(symbol="EURUSD", action="BUY", confidence=80):
    from backend.webhooks.tradingview_signal_normalizer import TradingViewSignalNormalizer

    return TradingViewSignalNormalizer().normalize(
        {
            "symbol": symbol,
            "action": action,
            "timeframe": "M15",
            "strategy": "TradingView Test",
            "price": 1.085,
            "confidence": confidence,
        }
    )


def verify_risk_gate() -> bool:
    try:
        from backend.webhooks.webhook_risk_gate import WebhookRiskGate

        gate = WebhookRiskGate()
        valid = gate.evaluate_signal_risk(make_signal("EURUSD", "BUY", 80))
        low_confidence = gate.evaluate_signal_risk(make_signal("XAUUSD", "SELL", 20))
        invalid = make_signal("EURUSD", "BUY", 80)
        invalid.action = "INVALID"
        invalid.orchestration_ready = False
        invalid_result = gate.evaluate_signal_risk(invalid)
        passed = (
            valid.passed is True
            and valid.risk_level in {"LOW", "MEDIUM"}
            and low_confidence.passed is False
            and any("confidence" in reason.lower() for reason in low_confidence.reasons)
            and invalid_result.passed is False
            and any("action" in reason.lower() for reason in invalid_result.reasons)
        )
        return show("Risk gate blocks invalid actions and low-confidence signals", passed)
    except Exception as exc:
        return show("Risk gate blocks invalid actions and low-confidence signals", False, str(exc))


def verify_routing_preview() -> bool:
    try:
        from backend.webhooks.webhook_broker_routing_preview import WebhookBrokerRoutingPreviewBuilder

        builder = WebhookBrokerRoutingPreviewBuilder()
        eur = builder.build_preview(make_signal("EUR/USD", "BUY", 80))
        xau = builder.build_preview(make_signal("GOLD", "SELL", 80))
        nifty = builder.build_preview(make_signal("NIFTY 50", "ALERT", 80))
        expected_brokers = {"STARTRADER", "FXPRO", "VANTAGE"}
        passed = (
            set(eur.supported_brokers) == expected_brokers
            and eur.routing_ready is True
            and eur.broker_symbol_map["STARTRADER"] == "EURUSD"
            and set(xau.supported_brokers) == expected_brokers
            and xau.broker_symbol_map["FXPRO"] == "XAUUSD"
            and nifty.routing_ready is False
            and "ZERODHA_FUTURE" in nifty.unsupported_brokers
            and "preview-only" in nifty.message
        )
        return show("Broker routing preview maps FX/CFD and keeps NIFTY50 conservative", passed)
    except Exception as exc:
        return show("Broker routing preview maps FX/CFD and keeps NIFTY50 conservative", False, str(exc))


def verify_engine_and_store() -> bool:
    try:
        from backend.webhooks.webhook_institutional_context_checker import WebhookInstitutionalContextChecker
        from backend.webhooks.webhook_orchestration_engine import WebhookOrchestrationEngine
        from backend.webhooks.webhook_orchestration_models import WebhookInstitutionalContextCheck
        from backend.webhooks.webhook_orchestration_service import WebhookOrchestrationService

        class NeutralContextChecker(WebhookInstitutionalContextChecker):
            def __init__(self):
                pass

            def check_signal_context(self, signal):
                return WebhookInstitutionalContextCheck(
                    canonical_symbol=signal.canonical_symbol,
                    institutional_bias="NEUTRAL",
                    dashboard_status="HEALTHY",
                    recommendation="MONITOR",
                    confidence=70,
                    aligned_with_signal=None,
                    issues=[],
                )

        engine = WebhookOrchestrationEngine(institutional_checker=NeutralContextChecker())
        service = WebhookOrchestrationService(engine=engine)
        accepted = service.process_signal(make_signal("EURUSD", "BUY", 80))
        blocked = service.process_signal(make_signal("XAUUSD", "SELL", 10))
        rejected = service.process_signal(make_signal("NIFTY50", "ALERT", 80))
        decisions = service.get_recent_decisions()
        fetched = service.get_decision(accepted.decision_id)
        passed = (
            accepted.final_decision == "SIMULATION_ACCEPTED"
            and accepted.simulation_only is True
            and accepted.live_execution_enabled is False
            and blocked.final_decision == "BLOCKED"
            and rejected.final_decision == "REJECTED"
            and len(decisions) == 3
            and fetched is not None
            and service.get_status()["live_execution_enabled"] is False
        )
        return show("Orchestration engine and store produce simulation-only decisions", passed)
    except Exception as exc:
        return show("Orchestration engine and store produce simulation-only decisions", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/webhooks/orchestration/status")
        decision = client.post(
            "/webhooks/orchestration/test",
            json={
                "symbol": "EURUSD",
                "action": "BUY",
                "timeframe": "M15",
                "strategy": "TradingView Test",
                "price": 1.085,
                "confidence": 80,
            },
        )
        decisions = client.get("/webhooks/orchestration/decisions")
        webhook = client.post(
            "/webhooks/tradingview",
            json={
                "symbol": "XAUUSD",
                "action": "SELL",
                "timeframe": "M15",
                "strategy": "TradingView Test",
                "price": 2400,
                "confidence": 80,
                "orchestrate": True,
            },
        )
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and decision.status_code == 200
            and decision.json()["simulation_only"] is True
            and decision.json()["live_execution_enabled"] is False
            and decision.json()["final_decision"] in {
                "SIMULATION_ACCEPTED",
                "WAIT_FOR_CONFIRMATION",
                "BLOCKED",
                "REJECTED",
            }
            and decisions.status_code == 200
            and len(decisions.json()) >= 1
            and webhook.status_code == 200
            and webhook.json()["canonical_symbol"] == "XAUUSD"
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Webhook orchestration APIs are JSON-safe and execution-free", passed)
    except Exception as exc:
        return show("Webhook orchestration APIs are JSON-safe and execution-free", False, str(exc))


def main() -> int:
    print("Phase 3 Day 13 Webhook Orchestration Verification")
    print("=" * 58)
    checks = [
        verify_files_and_routes(),
        verify_risk_gate(),
        verify_routing_preview(),
        verify_engine_and_store(),
        verify_api_and_safety(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
