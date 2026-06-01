import shutil
import sys
from pathlib import Path

from backend.deployment.deployment_models import VPSEnvironmentCheck


class VPSReadinessChecker:
    """Check local/VPS runtime prerequisites for demo deployment preparation."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]

    def check(self) -> VPSEnvironmentCheck:
        warnings: list[str] = []
        blockers: list[str] = []
        os_supported = sys.platform.startswith(("win", "linux"))
        python_available = shutil.which("python") is not None or shutil.which("python3") is not None
        node_available = shutil.which("node") is not None
        scripts_dir = self.project_root / "scripts"
        required_dirs = all((self.project_root / path).exists() for path in ["backend", "frontend", "logs", "docs"])
        script_names = [
            "start_backend.ps1",
            "start_frontend.ps1",
            "start_all_dev.ps1",
            "check_deployment_readiness.ps1",
        ]
        docker_script_names = [
            "docker_build.ps1",
            "docker_up.ps1",
            "docker_down.ps1",
            "docker_logs.ps1",
            "docker_healthcheck.ps1",
        ]
        startup_scripts_present = scripts_dir.exists() and all((scripts_dir / name).exists() for name in script_names)
        docker_scripts_present = scripts_dir.exists() and all((scripts_dir / name).exists() for name in docker_script_names)

        if not os_supported:
            blockers.append("Deployment target OS should be Windows VPS for MT5 or Linux for API-only services.")
        if not python_available:
            blockers.append("Python executable was not found.")
        if not node_available:
            warnings.append("Node executable was not found; frontend build/start may fail.")
        if not required_dirs:
            warnings.append("Recommended backend/frontend/logs/docs directories are not all present.")
        if not startup_scripts_present:
            warnings.append("Deployment startup scripts are not all present yet.")
        if not docker_scripts_present:
            warnings.append("Docker helper scripts are not all present yet.")

        return VPSEnvironmentCheck(
            os_supported=os_supported,
            python_available=python_available,
            node_available=node_available,
            ports_available=True,
            required_directories_present=required_dirs,
            startup_scripts_present=startup_scripts_present,
            docker_scripts_present=docker_scripts_present,
            recommended_region="Mumbai",
            latency_target_ms="<10ms ideal",
            warnings=warnings,
            blockers=blockers,
        )
