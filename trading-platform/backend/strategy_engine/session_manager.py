from datetime import datetime, time, timezone
from typing import Dict, List


class SessionManager:
    """Provide institutional market-session context using UTC ranges."""

    SESSIONS = {
        "Asian": {"start": time(0, 0), "end": time(9, 0), "high_liquidity": False},
        "London": {"start": time(7, 0), "end": time(16, 0), "high_liquidity": True},
        "New York": {"start": time(12, 0), "end": time(21, 0), "high_liquidity": True},
    }

    def get_current_session(self, now: datetime | None = None) -> str:
        """Return the current primary trading session."""

        current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).time()
        for session_name, config in self.SESSIONS.items():
            if config["start"] <= current_time < config["end"]:
                return session_name
        return "Closed"

    def get_session_info(self, now: datetime | None = None) -> Dict[str, object]:
        """Return current session name, UTC ranges, and liquidity context."""

        current_session = self.get_current_session(now)
        return {
            "current_session": current_session,
            "utc_ranges": self._session_ranges(),
            "high_liquidity": self.is_high_liquidity_session(now),
        }

    def is_high_liquidity_session(self, now: datetime | None = None) -> bool:
        """Return true when current UTC time is inside a high-liquidity session."""

        current_session = self.get_current_session(now)
        if current_session == "Closed":
            return False
        return bool(self.SESSIONS[current_session]["high_liquidity"])

    def _session_ranges(self) -> List[Dict[str, object]]:
        return [
            {
                "name": name,
                "start_utc": config["start"].strftime("%H:%M"),
                "end_utc": config["end"].strftime("%H:%M"),
                "high_liquidity": config["high_liquidity"],
            }
            for name, config in self.SESSIONS.items()
        ]

