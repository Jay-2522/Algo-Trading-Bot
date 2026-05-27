from typing import Any

from backend.replay.replay_models import ReplayStepResult


class ReplayEventLogger:
    """Collect replay events in memory for the current run."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def log_step(self, step_result: ReplayStepResult) -> None:
        self.events.append(
            {
                "event_type": step_result.event_type,
                "step_index": step_result.step_index,
                "replay_time": step_result.replay_time,
                "confidence": step_result.confidence,
                "notes": step_result.notes,
            }
        )

    def log_event(self, event_type: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        self.events.append(
            {
                "event_type": event_type,
                "message": message,
                "metadata": metadata or {},
            }
        )
