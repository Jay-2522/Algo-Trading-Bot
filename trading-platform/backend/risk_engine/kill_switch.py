from datetime import datetime, timezone
from typing import Any, Dict


class KillSwitch:
    """In-memory emergency halt state for future trading permission checks."""

    def __init__(self) -> None:
        self._active = False
        self._reason: str | None = None
        self._updated_at: datetime = datetime.now(timezone.utc)

    def activate(self, reason: str) -> Dict[str, Any]:
        if not reason or not reason.strip():
            raise ValueError("Kill switch activation reason cannot be empty.")
        self._active = True
        self._reason = reason.strip()
        self._updated_at = datetime.now(timezone.utc)
        return self.get_status()

    def deactivate(self) -> Dict[str, Any]:
        self._active = False
        self._reason = None
        self._updated_at = datetime.now(timezone.utc)
        return self.get_status()

    def is_active(self) -> bool:
        return self._active

    def get_status(self) -> Dict[str, Any]:
        return {
            "active": self._active,
            "reason": self._reason,
            "updated_at": self._updated_at.isoformat(),
        }

