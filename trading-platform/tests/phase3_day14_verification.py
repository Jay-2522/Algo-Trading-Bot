import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def sample_payload(timestamp: str = "2026-05-28T00:00:00+00:00") -> dict:
    return {
        "symbol": "EURUSD",
        "action": "BUY",
        "timeframe": "M15",
        "strategy": "TradingView Security Test",
        "price": 1.085,
        "confidence": 80,
        "timestamp": timestamp,
    }


def verify_files_and_routes() -> bool:
    files = [
        "backend/webhooks/webhook_replay_guard.py",
        "backend/webhooks/webhook_request_fingerprint.py",
        "backend/webhooks/webhook_rate_limiter.py",
        "backend/webhooks/webhook_security_models.py",
        "backend/webhooks/webhook_audit_logger.py",
        "backend/webhooks/webhook_security_monitor.py",
        "backend/webhooks/webhook_security_service.py",
        "docs/phase-3-day-14-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/webhooks/security/status",
            "/webhooks/security/events",
            "/webhooks/security/test",
            "/webhooks/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Webhook security files and routes exist", files_ok and routes_ok)


def verify_fingerprint_and_replay_guard() -> bool:
    try:
        from backend.webhooks.webhook_replay_guard import WebhookReplayGuard
        from backend.webhooks.webhook_request_fingerprint import WebhookRequestFingerprint

        builder = WebhookRequestFingerprint()
        payload = sample_payload()
        with_secret = {**payload, "secret": "do-not-store"}
        first_hash = builder.build_fingerprint(payload)
        second_hash = builder.build_fingerprint(with_secret)
        guard = WebhookReplayGuard(replay_window_seconds=300)
        first = guard.validate_request(payload)
        second = guard.validate_request(with_secret)
        passed = (
            first_hash == second_hash
            and len(first_hash) == 64
            and first.allowed is True
            and second.allowed is False
            and second.duplicate_detected is True
            and second.replay_detected is True
        )
        return show("Fingerprinting is deterministic and replay guard blocks duplicates", passed)
    except Exception as exc:
        return show("Fingerprinting is deterministic and replay guard blocks duplicates", False, str(exc))


def verify_rate_limiter_and_localhost() -> bool:
    try:
        from backend.webhooks.webhook_rate_limiter import WebhookRateLimiter

        limiter = WebhookRateLimiter(limit=2, window_seconds=60)
        first = limiter.validate_request("203.0.113.4")
        second = limiter.validate_request("203.0.113.4")
        third = limiter.validate_request("203.0.113.4")
        localhost = limiter.validate_request("127.0.0.1")
        passed = (
            first.allowed is True
            and second.allowed is True
            and third.allowed is False
            and third.blocked is True
            and localhost.allowed is True
            and localhost.request_count == 0
        )
        return show("Rate limiter blocks excessive requests and whitelists localhost", passed)
    except Exception as exc:
        return show("Rate limiter blocks excessive requests and whitelists localhost", False, str(exc))


def verify_security_monitor_and_audit() -> bool:
    try:
        from backend.webhooks.webhook_audit_logger import WebhookAuditLogger
        from backend.webhooks.webhook_security_monitor import WebhookSecurityMonitor
        from backend.webhooks.webhook_security_service import WebhookSecurityService

        service = WebhookSecurityService(
            monitor=WebhookSecurityMonitor(),
            audit_logger=WebhookAuditLogger(),
        )
        safe = service.validate_webhook_request(sample_payload("2026-05-28T00:01:00+00:00"), "203.0.113.5")
        duplicate = service.validate_webhook_request(sample_payload("2026-05-28T00:01:00+00:00"), "203.0.113.5")
        malformed = service.validate_webhook_request({"symbol": "DOGE", "action": "MOON"}, "203.0.113.6")
        events = service.get_security_events()
        passed = (
            safe.event_type == "SAFE_REQUEST"
            and safe.blocked is False
            and duplicate.event_type in {"DUPLICATE_SIGNAL", "REPLAY_ATTACK"}
            and duplicate.blocked is True
            and malformed.event_type == "INVALID_PAYLOAD"
            and len(events) == 3
            and service.get_status()["simulation_only"] is True
            and service.get_status()["live_execution_enabled"] is False
        )
        return show("Security monitor classifies malformed/replay requests and audit logger stores events", passed)
    except Exception as exc:
        return show("Security monitor classifies malformed/replay requests and audit logger stores events", False, str(exc))


def verify_webhook_service_rejects_replay() -> bool:
    try:
        from backend.webhooks.tradingview_webhook_auth import TradingViewWebhookAuthenticator
        from backend.webhooks.tradingview_webhook_service import TradingViewWebhookService
        from backend.webhooks.webhook_security_service import WebhookSecurityService

        service = TradingViewWebhookService(
            authenticator=TradingViewWebhookAuthenticator(expected_secret=None),
            security_service=WebhookSecurityService(),
        )
        payload = sample_payload("2026-05-28T00:02:00+00:00")
        signal = service.process_webhook(payload, source_ip="203.0.113.7")
        blocked = False
        try:
            service.process_webhook(payload, source_ip="203.0.113.7")
        except RuntimeError:
            blocked = True
        passed = (
            signal.canonical_symbol == "EURUSD"
            and signal.simulation_only is True
            and signal.live_execution_enabled is False
            and blocked is True
            and any(event.blocked for event in service.security_service.get_security_events())
        )
        return show("TradingView webhook service rejects replay attempts safely", passed)
    except Exception as exc:
        return show("TradingView webhook service rejects replay attempts safely", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/webhooks/security/status")
        test = client.post("/webhooks/security/test", json=sample_payload("2026-05-28T00:03:00+00:00"))
        duplicate = client.post("/webhooks/security/test", json=sample_payload("2026-05-28T00:03:00+00:00"))
        events = client.get("/webhooks/security/events")
        webhook = client.post("/webhooks/tradingview", json=sample_payload("2026-05-28T00:04:00+00:00"))
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and test.status_code == 200
            and test.json()["event_type"] == "SAFE_REQUEST"
            and duplicate.status_code == 200
            and duplicate.json()["blocked"] is True
            and events.status_code == 200
            and len(events.json()) >= 2
            and webhook.status_code == 200
            and webhook.json()["simulation_only"] is True
            and webhook.json()["live_execution_enabled"] is False
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Webhook security APIs are JSON-safe and preserve simulation-only safety", passed)
    except Exception as exc:
        return show("Webhook security APIs are JSON-safe and preserve simulation-only safety", False, str(exc))


def main() -> int:
    print("Phase 3 Day 14 Webhook Security Hardening Verification")
    print("=" * 62)
    checks = [
        verify_files_and_routes(),
        verify_fingerprint_and_replay_guard(),
        verify_rate_limiter_and_localhost(),
        verify_security_monitor_and_audit(),
        verify_webhook_service_rejects_replay(),
        verify_api_and_safety(),
    ]
    print("=" * 62)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
