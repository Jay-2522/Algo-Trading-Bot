import os
from pathlib import Path

from backend.deployment.deployment_models import EnvironmentAuditResult


class EnvironmentAuditor:
    """Audit deployment environment flags without mutating runtime state."""

    FORBIDDEN_TRUE_KEYS = {
        "LIVE_EXECUTION_ENABLED",
        "BROKER_EXECUTION_ENABLED",
        "ENABLE_LIVE_TRADING",
        "LIVE_TRADING_ENABLED",
        "BROKER_LIVE_EXECUTION_ENABLED",
    }

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]

    def audit(self) -> EnvironmentAuditResult:
        warnings: list[str] = []
        blockers: list[str] = []
        env_files = [
            self.project_root / ".env",
            self.project_root / ".env.local",
            self.project_root / "frontend" / ".env.local",
        ]
        env_file_present = any(path.exists() for path in env_files)
        env_values = self._load_env_files(env_files)
        api_base_url_configured = bool(env_values.get("NEXT_PUBLIC_API_BASE_URL") or os.getenv("NEXT_PUBLIC_API_BASE_URL"))
        node_environment = os.getenv("NODE_ENV") or env_values.get("NODE_ENV") or "development"
        forbidden_live_flags = self._forbidden_live_flags(env_values)

        if not env_file_present:
            warnings.append(".env or .env.local is not present; create one before VPS deployment.")
        if not api_base_url_configured:
            warnings.append("NEXT_PUBLIC_API_BASE_URL is not configured.")
        if forbidden_live_flags:
            blockers.append(f"Forbidden live execution flags enabled: {', '.join(forbidden_live_flags)}.")

        python_path_ok = self._can_import_backend()
        if not python_path_ok:
            blockers.append("Python cannot import backend.main from the project root.")

        return EnvironmentAuditResult(
            env_file_present=env_file_present,
            api_base_url_configured=api_base_url_configured,
            python_path_ok=python_path_ok,
            node_environment=node_environment,
            required_variables_present=env_file_present and api_base_url_configured,
            forbidden_live_flags_detected=bool(forbidden_live_flags),
            simulation_only=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
            warnings=warnings,
            blockers=blockers,
        )

    def _load_env_files(self, paths: list[Path]) -> dict[str, str]:
        values: dict[str, str] = {}
        for path in paths:
            if not path.exists():
                continue
            for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
        return values

    def _forbidden_live_flags(self, values: dict[str, str]) -> list[str]:
        enabled: list[str] = []
        merged = {**values, **{key: value for key, value in os.environ.items() if key in self.FORBIDDEN_TRUE_KEYS}}
        for key in self.FORBIDDEN_TRUE_KEYS:
            if str(merged.get(key, "")).strip().lower() in {"1", "true", "yes", "on", "enabled"}:
                enabled.append(key)
        return enabled

    def _can_import_backend(self) -> bool:
        try:
            import backend.main  # noqa: F401

            return True
        except Exception:
            return False
