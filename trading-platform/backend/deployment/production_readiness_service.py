from pathlib import Path

from backend.deployment.backup_readiness_service import BackupReadinessService
from backend.deployment.production_readiness_models import ProductionReadinessReport
from backend.security.security_readiness_service import SecurityReadinessService
from backend.strategy_execution_bridge.execution_operations_center import ExecutionOperationsCenter


class ProductionReadinessService:
    """Final read-only readiness certification before demo VPS deployment."""

    def __init__(
        self,
        project_root: Path | None = None,
        security_service: SecurityReadinessService | None = None,
        backup_service: BackupReadinessService | None = None,
        execution_center: ExecutionOperationsCenter | None = None,
    ) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.security_service = security_service or SecurityReadinessService(self.project_root)
        self.backup_service = backup_service or BackupReadinessService(self.project_root)
        self.execution_center = execution_center or ExecutionOperationsCenter()
        self._cached_report: ProductionReadinessReport | None = None
        self._cached_security_status = None
        self._cached_backup_status = None

    def get_report(self) -> ProductionReadinessReport:
        if self._cached_report is not None:
            return self._cached_report
        scores = self._component_scores()
        blockers = self.get_blockers(scores)
        warnings = self.get_warnings(scores)
        readiness_score = self.calculate_score(scores, blockers)
        self._cached_report = ProductionReadinessReport(
            overall_status=self._overall_status(readiness_score, blockers),
            readiness_score=readiness_score,
            deployment_score=scores["deployment_score"],
            monitoring_score=scores["monitoring_score"],
            security_score=scores["security_score"],
            backup_score=scores["backup_score"],
            execution_score=scores["execution_score"],
            strategy_score=scores["strategy_score"],
            vps_score=scores["vps_score"],
            strengths=self.get_strengths(scores),
            warnings=warnings,
            blockers=blockers,
            recommendations=self.get_recommendations(scores, blockers),
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        return self._cached_report

    def calculate_score(self, scores: dict[str, int] | None = None, blockers: list[str] | None = None) -> int:
        scores = scores or self._component_scores()
        blockers = blockers if blockers is not None else self.get_blockers(scores)
        weights = {
            "deployment_score": 0.18,
            "monitoring_score": 0.14,
            "security_score": 0.16,
            "backup_score": 0.14,
            "execution_score": 0.14,
            "strategy_score": 0.12,
            "vps_score": 0.12,
        }
        score = sum(scores[name] * weight for name, weight in weights.items())
        score -= min(20, len(blockers) * 5)
        return max(0, min(100, round(score)))

    def get_strengths(self, scores: dict[str, int] | None = None) -> list[str]:
        scores = scores or self._component_scores()
        strengths: list[str] = []
        labels = {
            "deployment_score": "Deployment readiness checks are implemented.",
            "monitoring_score": "Monitoring and health endpoints are operational.",
            "security_score": "Security hardening and secrets auditing are in place.",
            "backup_score": "Backup, recovery, rollback, and incident guides are defined.",
            "execution_score": "Execution operations are guarded and demo-only.",
            "strategy_score": "Strategy analysis routes are available.",
            "vps_score": "VPS preparation checks are available.",
        }
        for key, label in labels.items():
            if scores[key] >= 85:
                strengths.append(label)
        return strengths

    def get_warnings(self, scores: dict[str, int] | None = None) -> list[str]:
        scores = scores or self._component_scores()
        warnings: list[str] = []
        security = self._security_status()
        backup = self._backup_status()
        warnings.extend(security.warnings)
        warnings.extend(backup.warnings)
        if not (self.project_root / "frontend" / ".env.local").exists():
            warnings.append("Frontend .env.local was not detected; configure API base URL on the VPS.")
        if scores["vps_score"] < 85:
            warnings.append("Target VPS must be validated directly before demo go-live.")
        for key, label in self._score_labels().items():
            if scores[key] < 85:
                warnings.append(f"{label} is below staging threshold.")
        return list(dict.fromkeys(warnings))

    def get_blockers(self, scores: dict[str, int] | None = None) -> list[str]:
        scores = scores or self._component_scores()
        blockers: list[str] = []
        security = self._security_status()
        backup = self._backup_status()
        blockers.extend(security.blockers)
        blockers.extend(backup.blockers)
        for key, label in self._score_labels().items():
            if scores[key] < 70:
                blockers.append(f"{label} is below production minimum.")
        return list(dict.fromkeys(blockers))

    def get_recommendations(self, scores: dict[str, int] | None = None, blockers: list[str] | None = None) -> list[str]:
        scores = scores or self._component_scores()
        blockers = blockers if blockers is not None else self.get_blockers(scores)
        recommendations = [
            "Deploy first to a demo VPS with live and broker execution disabled.",
            "Run extended demo testing before client-facing acceptance.",
            "Validate dashboard, monitoring, backup, and security endpoints after VPS deployment.",
            "Run MT5 stability testing on demo only.",
            "Keep NIFTY50 and additional symbols as post-certification expansion work.",
        ]
        if blockers:
            recommendations.insert(0, "Resolve go-live blockers before demo VPS deployment.")
        if scores["vps_score"] < 85:
            recommendations.append("Complete VPS environment validation on the target Mumbai VPS.")
        if scores["security_score"] < 95:
            recommendations.append("Review security warnings and rotate any environment values outside the repository.")
        return list(dict.fromkeys(recommendations))

    def _component_scores(self) -> dict[str, int]:
        security = self._security_status()
        backup = self._backup_status()
        execution = self.execution_center.get_status()
        strategy_score = self._strategy_score()
        vps_score = self._vps_score()
        return {
            "deployment_score": self._deployment_score(),
            "monitoring_score": self._monitoring_score(),
            "security_score": security.security_score,
            "backup_score": backup.recovery_score,
            "execution_score": int(execution.get("health_score", 0)),
            "strategy_score": strategy_score,
            "vps_score": vps_score,
        }

    def _strategy_score(self) -> int:
        required = [
            "xauusd_strategy_engine.py",
            "confluence_score_engine.py",
            "signal_reason_builder.py",
        ]
        present = [
            (self.project_root / "backend" / "strategy_engine" / filename).exists()
            for filename in required
        ]
        routes_ready = (self.project_root / "backend" / "api" / "strategy_routes.py").exists()
        score = int((sum(1 for item in present if item) + (1 if routes_ready else 0)) / 4 * 100)
        return max(0, min(100, score))

    def _security_status(self):
        if self._cached_security_status is None:
            self._cached_security_status = self.security_service.run_security_check()
        return self._cached_security_status

    def _backup_status(self):
        if self._cached_backup_status is None:
            self._cached_backup_status = self.backup_service.get_status()
        return self._cached_backup_status

    def _deployment_score(self) -> int:
        required = [
            "Dockerfile.backend",
            "Dockerfile.frontend",
            "docker-compose.yml",
            "docker-compose.override.yml",
            ".env.example",
            ".env.production.example",
            "backend/api/deployment_routes.py",
            "backend/deployment/deployment_readiness_service.py",
        ]
        present = [(self.project_root / path).exists() for path in required]
        return int(sum(1 for item in present if item) / len(present) * 100)

    def _monitoring_score(self) -> int:
        required = [
            "backend/api/monitoring_routes.py",
            "backend/monitoring/logging_config.py",
            "backend/monitoring/platform_health_service.py",
            "backend/monitoring/system_metrics.py",
            "logs",
        ]
        present = [(self.project_root / path).exists() for path in required]
        return int(sum(1 for item in present if item) / len(present) * 100)

    def _vps_score(self) -> int:
        checks = [
            (self.project_root / "scripts" / "runtime_status.ps1").exists(),
            (self.project_root / "scripts" / "vps_healthcheck.ps1").exists(),
            (self.project_root / "scripts" / "restart_backend.ps1").exists(),
            (self.project_root / "scripts" / "restart_frontend.ps1").exists(),
            (self.project_root / "docs" / "vps-runtime-guide.md").exists(),
        ]
        return int(sum(1 for check in checks if check) / len(checks) * 100)

    def _overall_status(self, score: int, blockers: list[str]) -> str:
        if blockers or score < 70:
            return "BLOCKED"
        if score >= 95:
            return "READY_FOR_DEMO_VPS"
        if score >= 85:
            return "READY_FOR_STAGING"
        return "NEEDS_WORK"

    def _score_labels(self) -> dict[str, str]:
        return {
            "deployment_score": "Deployment readiness",
            "monitoring_score": "Monitoring readiness",
            "security_score": "Security readiness",
            "backup_score": "Backup readiness",
            "execution_score": "Execution operations readiness",
            "strategy_score": "Strategy readiness",
            "vps_score": "VPS readiness",
        }
