from datetime import datetime, timedelta, timezone

from backend.news_intelligence.models import EconomicCalendarEvent, NewsRiskContext


class NewsWindowEngine:
    """Apply pre/post-event risk windows and build strategy news context."""

    def apply_windows(
        self,
        event: EconomicCalendarEvent,
        now_utc: datetime | None = None,
    ) -> EconomicCalendarEvent:
        now = now_utc or datetime.now(timezone.utc)
        if event.risk_level == "EXTREME":
            event.pre_event_window_minutes = 60
            event.post_event_window_minutes = 45
            event.trade_action = "BLOCK"
        elif event.risk_level == "HIGH":
            event.pre_event_window_minutes = 30
            event.post_event_window_minutes = 30
            event.trade_action = "BLOCK"
        elif event.risk_level == "MEDIUM":
            event.pre_event_window_minutes = 15
            event.post_event_window_minutes = 15
            event.trade_action = "REDUCE_RISK"
        else:
            event.pre_event_window_minutes = 0
            event.post_event_window_minutes = 0
            event.trade_action = "ALLOW"

        event.active_risk_window = False
        if event.scheduled_time is not None:
            window_start = event.scheduled_time - timedelta(minutes=event.pre_event_window_minutes)
            window_end = event.scheduled_time + timedelta(minutes=event.post_event_window_minutes)
            event.active_risk_window = window_start <= now <= window_end and event.trade_action != "ALLOW"
        return event

    def build_context(
        self,
        events: list[EconomicCalendarEvent],
        now_utc: datetime | None = None,
    ) -> NewsRiskContext:
        now = now_utc or datetime.now(timezone.utc)
        windowed = [self.apply_windows(event, now_utc=now) for event in events]
        active = [event for event in windowed if event.active_risk_window]
        upcoming = [
            event
            for event in windowed
            if event.scheduled_time is not None and now <= event.scheduled_time <= now + timedelta(hours=24)
        ]
        risk_level = self._max_risk(active)
        trade_action = self._trade_action(active)
        reason = "No active news risk window."
        if active:
            titles = ", ".join(event.title for event in active[:3])
            reason = f"Active news risk window from {titles}."
        return NewsRiskContext(
            high_impact_event_active=any(event.risk_level in {"HIGH", "EXTREME"} for event in active),
            active_events=active,
            upcoming_events=upcoming,
            risk_level=risk_level,
            trade_action=trade_action,
            reason=reason,
            sources_checked=sorted({event.source for event in windowed}),
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _max_risk(self, events: list[EconomicCalendarEvent]) -> str:
        rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "EXTREME": 3}
        if not events:
            return "LOW"
        return max((event.risk_level for event in events), key=lambda item: rank[item])

    def _trade_action(self, events: list[EconomicCalendarEvent]) -> str:
        actions = {event.trade_action for event in events}
        if "BLOCK" in actions:
            return "BLOCK"
        if "WAIT_FOR_STABILIZATION" in actions:
            return "WAIT_FOR_STABILIZATION"
        if "REDUCE_RISK" in actions:
            return "REDUCE_RISK"
        return "ALLOW"
