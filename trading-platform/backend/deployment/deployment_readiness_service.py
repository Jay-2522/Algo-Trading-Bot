from pathlib import Path
from typing import Any

from backend.deployment.deployment_health_store import DeploymentHealthStore
from backend.deployment.deployment_models import DeploymentReadinessStatus
from backend.deployment.environment_auditor import EnvironmentAuditor
from backend.deployment.mt5_environment_checker import MT5EnvironmentChecker
from backend.deployment.vps_readiness_checker import VPSReadinessChecker


class DeploymentReadinessService:
    """Aggregate deployment-readiness checks while preserving demo-only policy."""

    def __init__(
        self,
        project_root: Path | None = None,
        environment_auditor: EnvironmentAuditor | None = None,
        vps_checker: VPSReadinessChecker | None = None,
        mt5_checker: MT5EnvironmentChecker | None = None,
        store: DeploymentHealthStore | None = None,
    ) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.environment_auditor = environment_auditor or EnvironmentAuditor(self.project_root)
        self.vps_checker = vps_checker or VPSReadinessChecker(self.project_root)
        self.mt5_checker = mt5_checker or MT5EnvironmentChecker()
        self.store = store or DeploymentHealthStore()

    def get_status(self) -> DeploymentReadinessStatus:
        return self.run_full_check()

    def run_full_check(self) -> DeploymentReadinessStatus:
        environment = self.environment_auditor.audit()
        vps = self.vps_checker.check()
        mt5 = self.mt5_checker.check()

        logging_ready = (self.project_root / "logs").exists()
        health_checks_ready = True
        docker_ready = (self.project_root / "Dockerfile.backend").exists() and (self.project_root / "Dockerfile.frontend").exists()
        compose_ready = (
            (self.project_root / "docker-compose.yml").exists()
            and (self.project_root / "docker-compose.override.yml").exists()
            and (self.project_root / ".dockerignore").exists()
        )
        env_templates_ready = environment.env_templates_ready
        blockers = [*environment.blockers, *vps.blockers, *mt5.blockers]
        warnings = [*environment.warnings, *vps.warnings, *mt5.warnings]
        if not docker_ready:
            warnings.append("Backend and frontend Dockerfiles are not both present.")
        if not compose_ready:
            warnings.append("Docker Compose files or .dockerignore are not ready.")
        if not env_templates_ready:
            warnings.append("Environment templates are not ready.")

        environment_ready = environment.python_path_ok and not environment.forbidden_live_flags_detected
        vps_ready = vps.os_supported and vps.python_available and vps.required_directories_present
        mt5_environment_ready = mt5.mt5_ready_for_demo
        score = self._score(
            environment_ready,
            vps_ready,
            mt5_environment_ready,
            logging_ready,
            health_checks_ready,
            docker_ready,
            compose_ready,
            env_templates_ready,
            blockers,
            warnings,
        )
        if blockers or score < 70:
            status = "BLOCKED"
        elif score == 100:
            status = "READY_FOR_DEMO_VPS"
        elif score >= 70:
            status = "WARNING"
        else:
            status = "READY_FOR_VPS_PREP"

        return self.store.store_status(
            DeploymentReadinessStatus(
                status=status,
                environment_ready=environment_ready,
                vps_ready=vps_ready,
                mt5_environment_ready=mt5_environment_ready,
                logging_ready=logging_ready,
                health_checks_ready=health_checks_ready,
                docker_ready=docker_ready,
                compose_ready=compose_ready,
                env_templates_ready=env_templates_ready,
                deployment_score=score,
                blockers=blockers,
                warnings=warnings,
                simulation_only=True,
                demo_execution=True,
                live_execution_enabled=False,
                broker_execution_enabled=False,
            )
        )

    def get_checklist(self) -> dict[str, Any]:
        return {
            "recommended_region": "Mumbai",
            "preferred_providers": ["Vultr Mumbai", "AWS Mumbai", "Contabo"],
            "backend": ["Install Python", "Install requirements", "Run uvicorn on 127.0.0.1:8000"],
            "frontend": ["Install Node", "Run npm install", "Run npm run build", "Serve frontend on port 3000"],
            "mt5": ["Install MT5 terminal", "Login to demo account", "Enable AutoTrading for demo tests only"],
            "safety": [
                "simulation_only=true",
                "demo_execution=true",
                "live_execution_enabled=false",
                "broker_execution_enabled=false",
            ],
            "health_checks": ["/health", "/status", "/deployment/status", "/deployment/readiness"],
            "docker": ["Dockerfile.backend", "Dockerfile.frontend", "docker-compose.yml", "docker-compose.override.yml"],
        }

    def get_blockers(self) -> dict[str, Any]:
        status = self.run_full_check()
        return {
            "blockers": status.blockers,
            "deployment_score": status.deployment_score,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_warnings(self) -> dict[str, Any]:
        status = self.run_full_check()
        return {
            "warnings": status.warnings,
            "deployment_score": status.deployment_score,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _score(
        self,
        environment_ready: bool,
        vps_ready: bool,
        mt5_ready: bool,
        logging_ready: bool,
        health_ready: bool,
        docker_ready: bool,
        compose_ready: bool,
        env_templates_ready: bool,
        blockers: list[str],
        warnings: list[str],
    ) -> int:
        score = 0
        score += 20 if environment_ready else 0
        score += 20 if vps_ready else 0
        score += 15 if mt5_ready else 8
        score += 10 if logging_ready else 0
        score += 10 if health_ready else 0
        score += 10 if docker_ready else 0
        score += 10 if compose_ready else 0
        score += 5 if env_templates_ready else 0
        score -= min(30, len(blockers) * 15)
        score -= min(15, len(warnings) * 3)
        return max(0, min(100, score))
