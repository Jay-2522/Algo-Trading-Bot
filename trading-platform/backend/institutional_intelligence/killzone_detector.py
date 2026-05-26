from datetime import datetime, time, timezone

from backend.institutional_intelligence.session_models import KillzoneStatus


class KillzoneDetector:
    """Identify fixed institutional high-participation UTC windows."""

    KILLZONES = (
        ("LONDON_OPEN", "LONDON", time(7, 0), time(10, 0), True, "HIGH"),
        ("NEW_YORK_OPEN", "NEW_YORK", time(12, 0), time(15, 0), True, "HIGH"),
        ("LONDON_CLOSE", "LONDON", time(15, 0), time(16, 0), False, "NORMAL"),
    )

    def get_active_killzone(self, current_time_utc: datetime | None = None) -> KillzoneStatus:
        current = self._utc(current_time_utc).time()
        for name, session, start, end, high_liquidity, quality in self.KILLZONES:
            if start <= current < end:
                return KillzoneStatus(
                    active_killzone=True,
                    killzone_name=name,
                    session_name=session,
                    start_time_utc=start.strftime("%H:%M"),
                    end_time_utc=end.strftime("%H:%M"),
                    high_liquidity_window=high_liquidity,
                    quality=quality,
                )
        return KillzoneStatus()

    def classify_killzone_quality(self, current_time_utc: datetime | None = None) -> str:
        return self.get_active_killzone(current_time_utc).quality

    def _utc(self, value: datetime | None) -> datetime:
        current = value or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current.astimezone(timezone.utc)
