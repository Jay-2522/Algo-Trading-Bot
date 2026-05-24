from datetime import datetime, timezone
from typing import Any

from backend.execution_engine.execution_models import ExecutionLog


class ExecutionLogger:
    """In-memory structured event log for simulated execution activity."""

    def __init__(self) -> None:
        self._logs: list[ExecutionLog] = []

    def log_event(
        self,
        execution_id: str,
        event_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionLog:
        log = ExecutionLog(
            execution_id=execution_id,
            event_type=event_type,
            message=message,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._logs.append(log)
        return log

    def get_logs(self, execution_id: str) -> list[ExecutionLog]:
        return [log for log in self._logs if log.execution_id == execution_id]

    def get_recent_logs(self, limit: int = 50) -> list[ExecutionLog]:
        if limit < 1:
            raise ValueError("Log limit must be greater than zero.")
        return list(reversed(self._logs[-limit:]))

