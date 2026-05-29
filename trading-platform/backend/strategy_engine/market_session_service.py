from datetime import datetime, timezone

from backend.strategy_engine.strategy_models import MarketSessionContext


class MarketSessionService:
    """UTC session classifier for XAUUSD strategy analysis."""

    def get_current_session(self, now_utc: datetime | None = None) -> str:
        now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
        hour = now.hour

        if 0 <= hour < 7:
            return "ASIAN"
        if 7 <= hour < 12:
            return "LONDON"
        if 12 <= hour < 16:
            return "OVERLAP"
        if 16 <= hour < 21:
            return "NEW_YORK"
        return "OFF_SESSION"

    def get_session_context(self, now_utc: datetime | None = None) -> MarketSessionContext:
        session = self.get_current_session(now_utc)
        quality = "HIGH" if session in {"LONDON", "NEW_YORK", "OVERLAP"} else "MEDIUM"
        if session == "OFF_SESSION":
            quality = "LOW"

        warnings: list[str] = []
        if session == "OFF_SESSION":
            warnings.append("Outside London/New York strategy focus window.")
        elif session == "ASIAN":
            warnings.append("Asian session is monitored primarily for high/low formation.")

        return MarketSessionContext(
            current_session=session,
            is_london_session=session in {"LONDON", "OVERLAP"},
            is_new_york_session=session in {"NEW_YORK", "OVERLAP"},
            is_asian_session=session == "ASIAN",
            session_quality=quality,
            warnings=warnings,
        )
