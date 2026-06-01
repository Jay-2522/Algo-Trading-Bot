from pathlib import Path
from typing import Any

from backend.deployment.backup_models import BackupReadinessStatus


class BackupReadinessService:
    """Read-only backup, rollback, and recovery readiness checks."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]

    def get_status(self) -> BackupReadinessStatus:
        docs = self._doc_status()
        warnings = [f"{name} is missing." for name, exists in docs.items() if not exists]
        score = int(sum(1 for exists in docs.values() if exists) / len(docs) * 100)
        status = "READY" if score == 100 else "WARNING" if score >= 50 else "BLOCKED"
        return BackupReadinessStatus(
            status=status,
            backups_defined=docs["backup_strategy"],
            rollback_defined=docs["rollback_guide"],
            recovery_defined=docs["recovery_runbook"],
            incident_response_defined=docs["incident_response"],
            recovery_score=score,
            warnings=warnings,
            blockers=[] if score >= 50 else ["Recovery documentation is incomplete."],
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def get_backup_plan(self) -> dict[str, Any]:
        return self._safe_payload(
            {
                "source_code_backup": "Commit and push source code to the approved private repository before deployment changes.",
                "environment_backup": "Keep .env.production outside source control in a secure operator vault.",
                "logs_backup": "Archive logs/platform.log and rotated backups before major releases.",
                "mt5_config_backup": "Export or document MT5 demo terminal profile, broker server, and demo login details securely.",
                "deployment_backup": "Snapshot VPS or preserve Docker images and previous release artifacts before upgrade.",
            }
        )

    def get_recovery_plan(self) -> dict[str, Any]:
        return self._safe_payload(
            {
                "backend": "Restart backend, verify /health, /deployment/readiness, and /monitoring/health.",
                "frontend": "Restart frontend, verify /dashboard and browser access.",
                "mt5": "Restart MT5 terminal, confirm demo account login, and check /monitoring/mt5.",
                "vps": "Reboot only after collecting logs and confirming no deployment script is mid-run.",
            }
        )

    def get_rollback_plan(self) -> dict[str, Any]:
        return self._safe_payload(
            {
                "checkpoint": "Record current commit hash, env file checksum, and health status before deployment.",
                "restore_code": "Checkout previous known-good commit or image.",
                "restore_env": "Restore secure env file from operator vault.",
                "validate": "Run backend checks, frontend build, /health, /deployment/readiness, and /monitoring/health.",
            }
        )

    def _doc_status(self) -> dict[str, bool]:
        return {
            "backup_strategy": (self.project_root / "docs" / "backup-strategy.md").exists(),
            "recovery_runbook": (self.project_root / "docs" / "recovery-runbook.md").exists(),
            "rollback_guide": (self.project_root / "docs" / "deployment-rollback-guide.md").exists(),
            "incident_response": (self.project_root / "docs" / "incident-response-guide.md").exists(),
        }

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
