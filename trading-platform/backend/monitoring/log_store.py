from pathlib import Path

from backend.monitoring.logging_config import PLATFORM_LOG, configure_logging


class LogStore:
    """Read-only access to platform logs."""

    def __init__(self, log_file: Path | None = None) -> None:
        self.log_file = log_file or PLATFORM_LOG
        configure_logging()

    def get_recent_logs(self, limit: int = 100) -> list[str]:
        return self._tail(limit)

    def get_error_logs(self, limit: int = 100) -> list[str]:
        return self._filter("ERROR", limit)

    def get_warning_logs(self, limit: int = 100) -> list[str]:
        return self._filter("WARNING", limit)

    def _tail(self, limit: int) -> list[str]:
        if not self.log_file.exists():
            return []
        lines = self.log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[-max(1, min(int(limit), 1000)) :]

    def _filter(self, level: str, limit: int) -> list[str]:
        lines = [line for line in self._tail(1000) if f"| {level} |" in line]
        return lines[-max(1, min(int(limit), 1000)) :]
