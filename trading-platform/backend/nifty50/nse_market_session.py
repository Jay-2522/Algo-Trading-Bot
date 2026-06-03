from datetime import datetime, timezone, timedelta


class NSEMarketSession:
    timezone = timezone(timedelta(hours=5, minutes=30), name="IST")

    def get_current_session(self, now: datetime | None = None) -> str:
        local_now = (now or datetime.now(self.timezone)).astimezone(self.timezone)
        minutes = local_now.hour * 60 + local_now.minute
        if 9 * 60 <= minutes < 9 * 60 + 15:
            return "PRE_OPEN_PLACEHOLDER"
        if 9 * 60 + 15 <= minutes <= 15 * 60 + 30:
            return "REGULAR_SESSION_PLACEHOLDER"
        if 15 * 60 + 30 < minutes <= 16 * 60:
            return "POST_MARKET_PLACEHOLDER"
        return "CLOSED_PLACEHOLDER"

    def is_market_open(self, now: datetime | None = None) -> bool:
        return self.get_current_session(now) == "REGULAR_SESSION_PLACEHOLDER"

    def get_session_context(self, now: datetime | None = None) -> dict:
        session_name = self.get_current_session(now)
        return {
            "exchange": "NSE",
            "timezone": "Asia/Kolkata",
            "session_name": session_name,
            "market_open": session_name == "REGULAR_SESSION_PLACEHOLDER",
            "pre_open_placeholder": "09:00-09:15 IST",
            "regular_session_placeholder": "09:15-15:30 IST",
            "post_market_placeholder": "15:30-16:00 IST",
            "holiday_calendar_connected": False,
            "warnings": ["Exact NSE holiday calendar is pending.", "Session context is architecture-only in Phase 12 Day 1."],
        }
