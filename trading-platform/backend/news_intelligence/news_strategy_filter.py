from datetime import datetime, timedelta, timezone
from typing import Any

from backend.news_intelligence.models import EconomicCalendarEvent, NewsRiskContext
from backend.news_intelligence.news_block_reason_builder import NewsBlockReasonBuilder
from backend.news_intelligence.news_filter_models import NewsFilterDecision


class NewsStrategyFilter:
    """Gate strategy confidence and output using normalized news risk context."""

    CRITICAL_CATEGORIES = {"FOMC", "CPI", "NFP"}

    def __init__(self, reason_builder: NewsBlockReasonBuilder | None = None) -> None:
        self.reason_builder = reason_builder or NewsBlockReasonBuilder()

    def evaluate(
        self,
        symbol: str = "XAUUSD",
        news_context: NewsRiskContext | dict[str, Any] | None = None,
        now_utc: datetime | None = None,
    ) -> NewsFilterDecision:
        now = now_utc or datetime.now(timezone.utc)
        context = self._context(news_context, now)
        active = [event for event in context.active_events if self._relevant(symbol, event)]
        upcoming = [event for event in context.upcoming_events if self._relevant(symbol, event)]
        decision = NewsFilterDecision(
            symbol=symbol,
            risk_level=context.risk_level,
            active_events=active,
            upcoming_events=upcoming,
            simulation_only=True,
            live_execution_enabled=False,
        )

        post_event = self._post_event_stabilization(active, now)
        if post_event is not None:
            decision.blocked = True
            decision.confidence_cap = 30.0
            decision.risk_level = post_event.risk_level
            decision.trade_action = "WAIT_FOR_STABILIZATION"
            decision.reason = "Post-news stabilization window active."
            return self._with_messages(decision)

        active_extreme = self._first_with_risk(active, "EXTREME")
        if active_extreme is not None:
            decision.blocked = True
            decision.confidence_cap = 0.0
            decision.risk_level = "EXTREME"
            decision.trade_action = "BLOCK"
            decision.reason = "Extreme news event active."
            return self._with_messages(decision)

        active_high = self._first_with_risk(active, "HIGH")
        if active_high is not None:
            decision.blocked = True
            decision.confidence_cap = 20.0
            decision.risk_level = "HIGH"
            decision.trade_action = "BLOCK"
            decision.reason = "High-impact news window active."
            return self._with_messages(decision)

        upcoming_extreme = self._first_upcoming_within(upcoming, now, "EXTREME", 60)
        if upcoming_extreme is not None:
            decision.blocked = True
            decision.confidence_cap = 0.0
            decision.risk_level = "EXTREME"
            decision.trade_action = "BLOCK"
            decision.reason = "Extreme USD news upcoming."
            return self._with_messages(decision)

        upcoming_high = self._first_upcoming_within(upcoming, now, "HIGH", 30)
        if upcoming_high is not None:
            decision.blocked = True
            decision.confidence_cap = 20.0
            decision.risk_level = "HIGH"
            decision.trade_action = "BLOCK"
            decision.reason = "High-impact USD news upcoming."
            return self._with_messages(decision)

        medium = self._first_upcoming_within(upcoming, now, "MEDIUM", 15)
        if medium is not None:
            decision.blocked = False
            decision.confidence_penalty = 20.0
            decision.risk_level = "MEDIUM"
            decision.trade_action = "REDUCE_RISK"
            decision.reason = "Medium-impact news approaching."
            return self._with_messages(decision)

        decision.reason = "No relevant news risk."
        return self._with_messages(decision)

    def _context(self, news_context: NewsRiskContext | dict[str, Any] | None, now: datetime) -> NewsRiskContext:
        if news_context is None:
            return NewsRiskContext()
        if isinstance(news_context, NewsRiskContext):
            return news_context
        data = dict(news_context)
        data["active_events"] = [self._event(event, now) for event in data.get("active_events", [])]
        data["upcoming_events"] = [self._event(event, now) for event in data.get("upcoming_events", [])]
        return NewsRiskContext.model_validate(data)

    def _event(self, raw_event: Any, now: datetime) -> EconomicCalendarEvent:
        if isinstance(raw_event, EconomicCalendarEvent):
            return raw_event
        event = dict(raw_event)
        scheduled_time = event.get("scheduled_time") or event.get("time")
        if scheduled_time is None and event.get("minutes_until") is not None:
            scheduled_time = now + timedelta(minutes=float(event["minutes_until"]))
        return EconomicCalendarEvent(
            event_id=str(event.get("event_id") or "manual-news-event"),
            source=str(event.get("source") or "MANUAL"),
            title=str(event.get("title") or "Manual news event"),
            currency=str(event.get("currency") or "USD").upper(),
            impact=str(event.get("impact") or "LOW").upper(),
            category=str(event.get("category") or event.get("title") or "OTHER").upper().replace(" ", "_"),
            scheduled_time=scheduled_time,
            risk_level=str(event.get("risk_level") or "LOW").upper(),
            active_risk_window=bool(event.get("active_risk_window", False)),
            trade_action=str(event.get("trade_action") or "ALLOW").upper(),
            warnings=list(event.get("warnings", [])),
        )

    def _relevant(self, symbol: str, event: EconomicCalendarEvent) -> bool:
        if symbol.upper() == "XAUUSD":
            return (
                event.currency.upper() == "USD"
                or event.category in self.CRITICAL_CATEGORIES
                or event.risk_level == "MEDIUM"
            )
        return True

    def _post_event_stabilization(
        self,
        events: list[EconomicCalendarEvent],
        now: datetime,
    ) -> EconomicCalendarEvent | None:
        for event in events:
            if event.scheduled_time is None or event.risk_level not in {"HIGH", "EXTREME"}:
                continue
            if event.scheduled_time <= now and event.trade_action == "BLOCK":
                return event
        return None

    def _first_with_risk(self, events: list[EconomicCalendarEvent], risk: str) -> EconomicCalendarEvent | None:
        return next((event for event in events if event.risk_level == risk), None)

    def _first_upcoming_within(
        self,
        events: list[EconomicCalendarEvent],
        now: datetime,
        risk: str,
        minutes: int,
    ) -> EconomicCalendarEvent | None:
        for event in events:
            if event.risk_level != risk:
                continue
            minutes_until = self._minutes_until(event, now)
            if minutes_until is not None and 0 <= minutes_until <= minutes:
                return event
        return None

    def _minutes_until(self, event: EconomicCalendarEvent, now: datetime) -> float | None:
        if event.scheduled_time is not None:
            return (event.scheduled_time - now).total_seconds() / 60
        minutes = getattr(event, "minutes_until", None)
        return float(minutes) if minutes is not None else None

    def _with_messages(self, decision: NewsFilterDecision) -> NewsFilterDecision:
        decision.client_message = self.reason_builder.build_client_message(decision)
        decision.technical_message = self.reason_builder.build_technical_message(decision)
        return decision
