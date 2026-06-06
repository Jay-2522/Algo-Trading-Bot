import os
import re
from pathlib import Path

from backend.security.security_models import SecretsAuditResult


class SecretsAuditor:
    """Audit env templates and obvious repository secret leaks without printing values."""

    REQUIRED_PLACEHOLDERS = {
        "API_KEY_PLACEHOLDER",
        "BROKER_LOGIN_PLACEHOLDER",
        "BROKER_PASSWORD_PLACEHOLDER",
        "NEWS_API_KEY_PLACEHOLDER",
    }
    LIVE_FLAG_KEYS = {"LIVE_EXECUTION_ENABLED", "BROKER_EXECUTION_ENABLED", "ENABLE_LIVE_TRADING", "LIVE_TRADING_ENABLED"}
    SECRET_KEY_PARTS = ("password", "secret", "token", "api_key", "apikey", "private")
    EXCLUDED_DIRS = {".git", ".next", "node_modules", "__pycache__", ".venv", "logs", "frontend_old"}
    SCANNED_NAMES = {".env.example", ".env.production.example", "docker-compose.yml", "docker-compose.override.yml"}

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]

    def audit(self) -> SecretsAuditResult:
        env_templates = [self.project_root / ".env.example", self.project_root / ".env.production.example"]
        checked = [path.name for path in env_templates if path.exists()]
        warnings: list[str] = []
        blockers: list[str] = []
        missing_placeholders = self._missing_placeholders(env_templates)
        unsafe_live_flags = self._unsafe_live_flags(env_templates)
        suspicious_locations = self._scan_for_real_secrets()

        if missing_placeholders:
            blockers.append("Required secret placeholders are missing from env templates.")
        if unsafe_live_flags:
            blockers.append("Unsafe live execution flags are enabled in environment templates.")
        if suspicious_locations:
            blockers.append("Potential real secrets detected in repository files; values are redacted.")
            warnings.extend([f"Potential secret-like value detected at {location}." for location in suspicious_locations[:20]])
        for path in env_templates:
            if not path.exists():
                blockers.append(f"{path.name} is missing.")

        return SecretsAuditResult(
            env_files_checked=checked,
            required_secret_placeholders_present=not missing_placeholders,
            real_secrets_detected_in_repo=bool(suspicious_locations),
            missing_secret_placeholders=missing_placeholders,
            unsafe_live_flags=unsafe_live_flags,
            warnings=warnings,
            blockers=blockers,
        )

    def _missing_placeholders(self, paths: list[Path]) -> list[str]:
        combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in paths if path.exists())
        return sorted([placeholder for placeholder in self.REQUIRED_PLACEHOLDERS if placeholder not in combined])

    def _unsafe_live_flags(self, paths: list[Path]) -> list[str]:
        unsafe: list[str] = []
        for path in paths:
            if not path.exists():
                continue
            for key, value in self._env_pairs(path).items():
                if key.upper() in self.LIVE_FLAG_KEYS and value.strip().lower() in {"1", "true", "yes", "on", "enabled"}:
                    unsafe.append(f"{path.name}:{key}")
        return unsafe

    def _scan_for_real_secrets(self) -> list[str]:
        locations: list[str] = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [directory for directory in dirs if directory not in self.EXCLUDED_DIRS]
            for filename in files:
                path = Path(root) / filename
                if path.name not in self.SCANNED_NAMES:
                    continue
                if path.name in {".env", ".env.local", ".env.production"}:
                    continue
                try:
                    pairs = self._env_pairs(path)
                except OSError:
                    continue
                for key, value in pairs.items():
                    if not self._looks_sensitive(key, value):
                        continue
                    locations.append(f"{path.relative_to(self.project_root).as_posix()}:{key}=********")
        return locations

    def _env_pairs(self, path: Path) -> dict[str, str]:
        pairs: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            clean_key = key.strip()
            if not re.fullmatch(r"[A-Z0-9_]+", clean_key):
                continue
            pairs[clean_key] = value.strip().strip('"').strip("'")
        return pairs

    def _looks_sensitive(self, key: str, value: str) -> bool:
        lowered = key.lower()
        stripped = value.strip()
        if not stripped or "placeholder" in stripped.lower():
            return False
        if key.upper() in self.LIVE_FLAG_KEYS:
            return False
        if any(part in lowered for part in self.SECRET_KEY_PARTS):
            return len(stripped) >= 8 or bool(re.search(r"[A-Za-z].*\d|\d.*[A-Za-z]", stripped))
        if re.fullmatch(r"[A-Za-z0-9_\-]{32,}", stripped):
            return True
        return False

    def _excluded(self, path: Path) -> bool:
        return any(part in self.EXCLUDED_DIRS for part in path.parts)
