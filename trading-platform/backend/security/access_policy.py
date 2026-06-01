import os

from backend.security.security_models import AccessPolicyStatus


class AccessPolicy:
    """Classify routes for future auth enforcement without enforcing auth yet."""

    ADMIN_PREFIXES = (
        "/deployment/",
        "/monitoring/",
        "/strategy-execution-bridge/",
        "/trade-copier/",
        "/execution-risk/",
        "/demo-execution/",
        "/control-center/",
    )
    CLIENT_PREFIXES = ("/dashboard", "/strategy/analyze/", "/news/status", "/deployment/status")

    def get_status(self) -> AccessPolicyStatus:
        mode = os.getenv("ACCESS_MODE", "LOCAL_DEV").upper()
        if mode not in {"LOCAL_DEV", "DEMO_VPS", "PRODUCTION_LOCKED"}:
            mode = "LOCAL_DEV"
        admin_protected = mode == "PRODUCTION_LOCKED"
        warnings = []
        if not admin_protected:
            warnings.append("Admin-route authentication is classified but not enforced in this phase.")
        return AccessPolicyStatus(
            mode=mode,
            admin_routes_protected=admin_protected,
            client_routes_public_safe=True,
            operations_routes_restricted_placeholder=True,
            api_key_guard_ready=True,
            warnings=warnings,
        )

    def is_admin_route(self, path: str) -> bool:
        normalized = self._normalize(path)
        return any(normalized.startswith(prefix) for prefix in self.ADMIN_PREFIXES)

    def is_client_route(self, path: str) -> bool:
        normalized = self._normalize(path)
        return any(normalized == prefix or normalized.startswith(prefix) for prefix in self.CLIENT_PREFIXES)

    def require_admin_placeholder(self, path: str) -> bool:
        return self.is_admin_route(path)

    def _normalize(self, path: str) -> str:
        normalized = "/" + str(path).lstrip("/")
        if normalized == "/deployment/status":
            return normalized
        return normalized
