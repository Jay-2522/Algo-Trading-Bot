from pathlib import Path
from typing import Any

from backend.security.access_policy import AccessPolicy
from backend.security.config_redactor import ConfigRedactor
from backend.security.secrets_auditor import SecretsAuditor
from backend.security.security_audit_store import SecurityAuditStore
from backend.security.security_models import SecurityReadinessStatus


class SecurityReadinessService:
    """Aggregate security readiness while keeping auth enforcement as a future phase."""

    def __init__(
        self,
        project_root: Path | None = None,
        secrets_auditor: SecretsAuditor | None = None,
        access_policy: AccessPolicy | None = None,
        redactor: ConfigRedactor | None = None,
        audit_store: SecurityAuditStore | None = None,
    ) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.secrets_auditor = secrets_auditor or SecretsAuditor(self.project_root)
        self.access_policy = access_policy or AccessPolicy()
        self.redactor = redactor or ConfigRedactor()
        self.audit_store = audit_store or SecurityAuditStore()

    def get_status(self) -> SecurityReadinessStatus:
        return self.run_security_check()

    def run_security_check(self) -> SecurityReadinessStatus:
        secrets = self.secrets_auditor.audit()
        access = self.access_policy.get_status()
        redaction_ready = self.redactor.redact_value("api_key", "abc123") == "********"
        cors_policy_ready = True
        blockers = list(secrets.blockers)
        warnings = [*secrets.warnings, *access.warnings]
        unsafe_flags = bool(secrets.unsafe_live_flags)
        secrets_ready = not secrets.blockers and secrets.required_secret_placeholders_present
        access_policy_ready = access.api_key_guard_ready and access.operations_routes_restricted_placeholder
        score = self._score(secrets_ready, access_policy_ready, cors_policy_ready, redaction_ready, unsafe_flags, blockers, warnings)
        status = "BLOCKED" if blockers or score < 70 else "READY" if score == 100 else "WARNING"
        readiness = SecurityReadinessStatus(
            status=status,
            security_score=score,
            secrets_ready=secrets_ready,
            access_policy_ready=access_policy_ready,
            cors_policy_ready=cors_policy_ready,
            unsafe_flags_detected=unsafe_flags,
            redaction_ready=redaction_ready,
            blockers=blockers,
            warnings=warnings,
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        self.audit_store.store_event(
            {
                "event_type": "SECURITY_READINESS_CHECK",
                "message": "Security readiness checked.",
                "metadata": self.redactor.redact_dict({"status": readiness.status, "security_score": readiness.security_score}),
            }
        )
        return readiness

    def get_blockers(self) -> dict[str, Any]:
        status = self.run_security_check()
        return self._safe_payload({"blockers": status.blockers, "security_score": status.security_score})

    def get_warnings(self) -> dict[str, Any]:
        status = self.run_security_check()
        return self._safe_payload({"warnings": status.warnings, "security_score": status.security_score})

    def get_access_policy(self):
        return self.access_policy.get_status()

    def list_audit_events(self, limit: int = 100) -> list[dict]:
        return self.audit_store.list_events(limit)

    def _score(
        self,
        secrets_ready: bool,
        access_policy_ready: bool,
        cors_policy_ready: bool,
        redaction_ready: bool,
        unsafe_flags: bool,
        blockers: list[str],
        warnings: list[str],
    ) -> int:
        score = 0
        score += 35 if secrets_ready else 0
        score += 25 if access_policy_ready else 0
        score += 20 if cors_policy_ready else 0
        score += 20 if redaction_ready else 0
        if unsafe_flags:
            score -= 40
        score -= min(30, len(blockers) * 15)
        score -= min(20, len(warnings) * 2)
        return max(0, min(100, score))

    def _safe_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload.update(
            {
                "simulation_only": True,
                "demo_execution": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            }
        )
        return payload
