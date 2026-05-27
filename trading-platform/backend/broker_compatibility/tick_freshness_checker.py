from datetime import datetime, timezone


class TickFreshnessChecker:
    """Determine whether an observed broker tick timestamp is recent."""

    def is_fresh(self, timestamp, max_age_seconds: int = 30) -> bool:
        if timestamp is None:
            return False
        try:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds()
            return 0 <= age <= max_age_seconds
        except Exception:
            return False
