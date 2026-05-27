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
        "backend/webhooks/__init__.py",
        "backend/webhooks/webhook_models.py",
        "backend/webhooks/tradingview_webhook_auth.py",
        "backend/webhooks/tradingview_payload_validator.py",
        "backend/webhooks/tradingview_signal_normalizer.py",
        "backend/webhooks/tradingview_signal_classifier.py",
        "backend/webhooks/webhook_event_store.py",
        "backend/webhooks/webhook_monitoring_service.py",
        "backend/webhooks/tradingview_webhook_service.py",
        "backend/api/tradingview_webhook_routes.py",
        "docs/phase-3-day-12-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/webhooks/tradingview",
            "/webhooks/status",
            "/webhooks/events",
            "/webhooks/events/{event_id}",
            "/brokers/status",
            "/replay/status",
            "/institutional/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Webhook files and routes exist", files_ok and routes_ok)


def verify_auth_and_validator() -> bool:
    try:
        from backend.webhooks.tradingview_payload_validator import TradingViewPayloadValidator
        from backend.webhooks.tradingview_webhook_auth import TradingViewWebhookAuthenticator

        auth = TradingViewWebhookAuthenticator(expected_secret="expected")
        validator = TradingViewPayloadValidator()
        malformed = validator.validate_payload({"symbol": "DOGE", "action": "MOON"})
        valid = validator.validate_payload(
            {
                "symbol": "XAU/USD",
                "action": "BUY",
                "timeframe": "M15",
                "strategy": "Liquidity Sweep",
                "price": 4450.25,
                "confidence": 82,
            }
        )
        passed = (
            auth.validate_secret("wrong") is False
            and auth.authenticate_request({"secret": "expected"}) is True
            and malformed["valid"] is False
            and len(malformed["issues"]) >= 2
            and valid["valid"] is True
        )
        return show("Authentication rejects invalid secrets and validator catches malformed payloads", passed)
    except Exception as exc:
        return show("Authentication rejects invalid secrets and validator catches malformed payloads", False, str(exc))


def verify_normalization() -> bool:
    try:
        from backend.webhooks.tradingview_signal_normalizer import TradingViewSignalNormalizer

        normalizer = TradingViewSignalNormalizer()
        eur = normalizer.normalize({"symbol": "EUR/USD", "action": "long", "timeframe": "m15", "price": 1.1})
        xau = normalizer.normalize({"symbol": "GOLD", "action": "SELL", "timeframe": "H1", "price": 2400})
        nifty = normalizer.normalize({"symbol": "NIFTY 50", "action": "ALERT", "timeframe": "H4"})
        passed = (
            eur.canonical_symbol == "EURUSD"
            and eur.market_type == "FOREX"
            and eur.action == "BUY"
            and eur.orchestration_ready is True
            and "STARTRADER" in eur.broker_targets
            and xau.canonical_symbol == "XAUUSD"
            and xau.market_type == "COMMODITY_CFD"
            and xau.action == "SELL"
            and nifty.canonical_symbol == "NIFTY50"
            and nifty.market_type == "INDIAN_INDEX"
            and nifty.action == "ALERT_ONLY"
            and nifty.simulation_only is True
            and nifty.live_execution_enabled is False
        )
        return show("Signal normalization works for EURUSD, XAUUSD, and NIFTY50 aliases", passed)
    except Exception as exc:
        return show("Signal normalization works for EURUSD, XAUUSD, and NIFTY50 aliases", False, str(exc))


def verify_service_and_store() -> bool:
    try:
        from backend.webhooks.tradingview_webhook_auth import TradingViewWebhookAuthenticator
        from backend.webhooks.tradingview_webhook_service import TradingViewWebhookService
        from backend.webhooks.webhook_event_store import WebhookEventStore
        from backend.webhooks.webhook_monitoring_service import WebhookMonitoringService

        store = WebhookEventStore()
        service = TradingViewWebhookService(
            authenticator=TradingViewWebhookAuthenticator(expected_secret="ok"),
            store=store,
        )
        signal = service.process_webhook(
            {
                "secret": "ok",
                "symbol": "XAUUSD",
                "action": "BUY",
                "timeframe": "M15",
                "strategy": "Liquidity Sweep",
                "price": 4450.25,
                "confidence": 82,
            }
        )
        try:
            service.process_webhook({"secret": "bad", "symbol": "EURUSD", "action": "BUY", "timeframe": "M15"})
        except PermissionError:
            pass
        monitoring = WebhookMonitoringService(store)
        events = monitoring.get_recent_events()
        first_event = monitoring.get_event(events[0].event_id)
        passed = (
            signal.canonical_symbol == "XAUUSD"
            and signal.orchestration_ready is True
            and signal.routing_ready is True
            and signal.simulation_only is True
            and signal.live_execution_enabled is False
            and len(events) == 2
            and first_event is not None
            and any(event.processing_status == "REJECTED" for event in events)
            and monitoring.get_status()["simulation_only"] is True
        )
        return show("Webhook service returns orchestration-ready signals and stores events safely", passed)
    except Exception as exc:
        return show("Webhook service returns orchestration-ready signals and stores events safely", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/webhooks/status")
        post = client.post(
            "/webhooks/tradingview",
            json={
                "symbol": "XAUUSD",
                "action": "BUY",
                "timeframe": "M15",
                "strategy": "Liquidity Sweep",
                "price": 4450.25,
                "confidence": 82,
            },
        )
        events = client.get("/webhooks/events")
        rejected = client.post("/webhooks/tradingview", json={"symbol": "DOGE", "action": "BUY"})
        broker = client.get("/brokers/status")
        replay = client.get("/replay/status")
        institutional = client.get("/institutional/status")
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and post.status_code == 200
            and post.json()["canonical_symbol"] == "XAUUSD"
            and post.json()["orchestration_ready"] is True
            and post.json()["simulation_only"] is True
            and post.json()["live_execution_enabled"] is False
            and events.status_code == 200
            and len(events.json()) >= 1
            and rejected.status_code == 400
            and broker.status_code == 200
            and replay.status_code == 200
            and institutional.status_code == 200
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Webhook APIs are JSON-safe and preserve previous routes", passed)
    except Exception as exc:
        return show("Webhook APIs are JSON-safe and preserve previous routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 12 TradingView Webhook Verification")
    print("=" * 56)
    checks = [
        verify_files_and_routes(),
        verify_auth_and_validator(),
        verify_normalization(),
        verify_service_and_store(),
        verify_api_and_safety(),
    ]
    print("=" * 56)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
