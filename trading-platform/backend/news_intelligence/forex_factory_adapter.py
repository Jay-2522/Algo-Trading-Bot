from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.news_intelligence.event_classifier import EventClassifier
from backend.news_intelligence.models import EconomicCalendarEvent
from backend.news_intelligence.news_risk_engine import NewsRiskEngine


class ForexFactoryAdapter:
    """Normalize Forex Factory-style calendar dictionaries without live fetching."""

    def __init__(
        self,
        classifier: EventClassifier | None = None,
        risk_engine: NewsRiskEngine | None = None,
    ) -> None:
        self.classifier = classifier or EventClassifier()
        self.risk_engine = risk_engine or NewsRiskEngine()

    def normalize_event(self, raw_event: dict[str, Any]) -> EconomicCalendarEvent:
        warnings: list[str] = []
        title = str(raw_event.get("title") or "Untitled Forex Factory event")
        category, classified_impact = self.classifier.classify(title)
        impact = self._impact(raw_event.get("impact"), classified_impact)
        scheduled_time = self._time(raw_event.get("time"), warnings)
        event = EconomicCalendarEvent(
            event_id=str(raw_event.get("event_id") or f"ff-{uuid4().hex}"),
            source="FOREX_FACTORY",
            title=title,
            currency=str(raw_event.get("currency") or "USD").upper(),
            impact=impact,
            category=category,
            scheduled_time=scheduled_time,
            actual=self._optional_text(raw_event.get("actual")),
            forecast=self._optional_text(raw_event.get("forecast")),
            previous=self._optional_text(raw_event.get("previous")),
            risk_level="LOW",
            warnings=warnings,
        )
        return self.risk_engine.evaluate(event)

    def normalize_events(self, raw_events: list[dict[str, Any]]) -> list[EconomicCalendarEvent]:
        return [self.normalize_event(raw_event) for raw_event in raw_events]

    def _impact(self, raw_impact: Any, classified_impact: str) -> str:
        normalized = str(raw_impact or classified_impact).strip().upper()
        if normalized in {"HIGH", "MEDIUM", "LOW"}:
            return normalized
        return classified_impact

    def _time(self, raw_time: Any, warnings: list[str]) -> datetime | None:
        if not raw_time:
            warnings.append("Forex Factory event time missing; event retained without scheduled_time.")
            return None
        try:
            if isinstance(raw_time, datetime):
                return raw_time.replace(tzinfo=timezone.utc) if raw_time.tzinfo is None else raw_time.astimezone(timezone.utc)
            return datetime.fromisoformat(str(raw_time).replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            warnings.append("Forex Factory event time could not be parsed; event retained without scheduled_time.")
            return None

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None
