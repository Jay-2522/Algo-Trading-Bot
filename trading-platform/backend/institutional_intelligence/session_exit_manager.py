from datetime import datetime, timezone
from typing import Any

from backend.institutional_intelligence.position_management_models import ManagedPosition, ManagementDecision


class SessionExitManager:
    """Identify timing-based exits for paper positions approaching adverse holding windows."""

    def __init__(self, new_york_close_hour_utc: int = 20) -> None:
        self.new_york_close_hour_utc = new_york_close_hour_utc

    def evaluate_exit(
        self,
        position: ManagedPosition,
        session_context: Any = None,
        current_time: datetime | None = None,
    ) -> ManagementDecision | None:
        now = self._utc(current_time)
        readiness = self._get(session_context, "trade_timing_readiness")
        liquidity = self._get(self._get(session_context, "liquidity_profile"), "liquidity_quality")
        reasons: list[str] = []
        entry_killzone = position.metadata.get("entry_killzone")
        current_killzone = self._get(session_context, "active_killzone")
        if entry_killzone and entry_killzone != "NONE" and not self._get(current_killzone, "active_killzone"):
            reasons.append(f"Entry killzone {entry_killzone} has ended.")
        if readiness in {"AVOID_LOW_LIQUIDITY", "AVOID_NEWS_WINDOW"}:
            reasons.append(f"Session readiness is {readiness}.")
        if liquidity == "POOR":
            reasons.append("Session liquidity quality deteriorated to POOR.")
        if now.hour >= self.new_york_close_hour_utc:
            reasons.append("New York close risk window is approaching.")
        if not reasons:
            return None
        return ManagementDecision(
            position_id=position.position_id,
            action="EXIT_SIMULATION",
            state="CLOSING",
            reason=" ".join(reasons),
            confidence=80.0,
        )

    def _utc(self, value: datetime | None) -> datetime:
        value = value or datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
