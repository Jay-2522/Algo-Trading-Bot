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
        "backend/security/__init__.py",
        "backend/security/security_models.py",
        "backend/security/secrets_auditor.py",
        "backend/security/access_policy.py",
        "backend/security/config_redactor.py",
        "backend/security/security_readiness_service.py",
        "backend/security/security_audit_store.py",
        "backend/api/security_routes.py",
        "scripts/security_check.ps1",
        "docs/phase-10-day-5-progress.md",
        "docs/security-hardening-guide.md",
        "docs/secrets-management-guide.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Security package, routes, script, and docs exist", not missing, ", ".join(missing))


def verify_imports_env_and_redaction() -> bool:
    try:
        from backend.security.access_policy import AccessPolicy
        from backend.security.config_redactor import ConfigRedactor
        from backend.security.secrets_auditor import SecretsAuditor
        from backend.security.security_audit_store import SecurityAuditStore
        from backend.security.security_models import AccessPolicyStatus, SecretsAuditResult, SecurityReadinessStatus
        from backend.security.security_readiness_service import SecurityReadinessService

        env_text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        prod_text = (PROJECT_ROOT / ".env.production.example").read_text(encoding="utf-8")
        placeholders = ["API_KEY_PLACEHOLDER", "BROKER_LOGIN_PLACEHOLDER", "BROKER_PASSWORD_PLACEHOLDER", "NEWS_API_KEY_PLACEHOLDER"]
        redacted = ConfigRedactor().redact_dict(
            {
                "admin_api_key": "REAL_VALUE_SHOULD_HIDE",
                "broker_password": "REAL_VALUE_SHOULD_HIDE",
                "nested": {"account_id": "123456", "safe": "visible"},
            }
        )
        imports_ok = all(
            item is not None
            for item in [
                AccessPolicy,
                ConfigRedactor,
                SecretsAuditor,
                SecurityAuditStore,
                SecurityReadinessService,
                AccessPolicyStatus,
                SecretsAuditResult,
                SecurityReadinessStatus,
            ]
        )
        passed = (
            imports_ok
            and all(item in env_text for item in placeholders)
            and all(item in prod_text for item in placeholders)
            and "LIVE_EXECUTION_ENABLED=false" in env_text
            and "BROKER_EXECUTION_ENABLED=false" in env_text
            and "LIVE_EXECUTION_ENABLED=false" in prod_text
            and "BROKER_EXECUTION_ENABLED=false" in prod_text
            and redacted["admin_api_key"] == "********"
            and redacted["broker_password"] == "********"
            and redacted["nested"]["account_id"] == "********"
            and redacted["nested"]["safe"] == "visible"
        )
        return show("Security imports, env placeholders, and redaction work", passed)
    except Exception as exc:
        return show("Security imports, env placeholders, and redaction work", False, str(exc))


def verify_secrets_and_access_policy() -> bool:
    try:
        from backend.security.access_policy import AccessPolicy
        from backend.security.secrets_auditor import SecretsAuditor

        audit = SecretsAuditor(PROJECT_ROOT).audit()
        combined_output = " ".join([*audit.warnings, *audit.blockers])
        policy = AccessPolicy()
        passed = (
            audit.required_secret_placeholders_present is True
            and not audit.unsafe_live_flags
            and "REAL_VALUE_SHOULD_HIDE" not in combined_output
            and policy.is_admin_route("/deployment/runtime/status") is True
            and policy.is_admin_route("/strategy-execution-bridge/operations/status") is True
            and policy.is_client_route("/strategy/analyze/eurusd") is True
            and policy.require_admin_placeholder("/trade-copier/status") is True
        )
        return show("Secrets auditor redacts findings and access policy classifies routes", passed)
    except Exception as exc:
        return show("Secrets auditor redacts findings and access policy classifies routes", False, str(exc))


def verify_routes_and_deployment_integration() -> bool:
    try:
        from backend.main import app

        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        required = [
            "/security/status",
            "/security/secrets-audit",
            "/security/access-policy",
            "/security/blockers",
            "/security/warnings",
            "/security/audit-events",
        ]
        routes_ok = all("GET" in route_methods.get(route, set()) for route in required)
        client = TestClient(app)
        status = client.get("/security/status")
        secrets = client.get("/security/secrets-audit")
        access = client.get("/security/access-policy")
        blockers = client.get("/security/blockers")
        warnings = client.get("/security/warnings")
        audit_events = client.get("/security/audit-events")
        readiness = client.get("/deployment/readiness")
        status_payload = status.json()
        readiness_payload = readiness.json()
        passed = (
            routes_ok
            and status.status_code == 200
            and secrets.status_code == 200
            and access.status_code == 200
            and blockers.status_code == 200
            and warnings.status_code == 200
            and audit_events.status_code == 200
            and readiness.status_code == 200
            and readiness_payload["security_ready"] is True
            and status_payload["simulation_only"] is True
            and status_payload["demo_execution"] is True
            and status_payload["live_execution_enabled"] is False
            and status_payload["broker_execution_enabled"] is False
            and readiness_payload["simulation_only"] is True
            and readiness_payload["demo_execution"] is True
            and readiness_payload["live_execution_enabled"] is False
            and readiness_payload["broker_execution_enabled"] is False
        )
        return show("Security routes work and deployment readiness includes security_ready", passed)
    except Exception as exc:
        return show("Security routes work and deployment readiness includes security_ready", False, str(exc))


def verify_preserved_routes_and_order_send_safety() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registered_get_routes = {
            route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path for route in app.routes if route.__class__.__name__ == "APIWebSocketRoute"
        }
        required = {
            "/security/status",
            "/deployment/status",
            "/deployment/runtime/status",
            "/monitoring/health",
            "/strategy-execution-bridge/operations/status",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not missing and not missing_ws and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("Phase 10 Day 1-4 and Phase 9 routes plus order_send isolation are preserved", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Phase 10 Day 1-4 and Phase 9 routes plus order_send isolation are preserved", False, str(exc))


def main() -> int:
    print("Phase 10 Day 5 Security Hardening Verification")
    print("=" * 56)
    checks = [
        verify_files(),
        verify_imports_env_and_redaction(),
        verify_secrets_and_access_policy(),
        verify_routes_and_deployment_integration(),
        verify_preserved_routes_and_order_send_safety(),
    ]
    print("=" * 56)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
