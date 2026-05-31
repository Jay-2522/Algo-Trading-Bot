from datetime import datetime, timezone
from typing import Any

from backend.news_intelligence.headline_classifier import HeadlineClassifier
from backend.news_intelligence.headline_models import HeadlineEvent
from backend.news_intelligence.headline_risk_engine import HeadlineRiskEngine


class FinancialJuiceAdapter:
    """Normalize Financial Juice-style manual headline payloads without live fetching."""

    def __init__(
        self,
        classifier: HeadlineClassifier | None = None,
        risk_engine: HeadlineRiskEngine | None = None,
    ) -> None:
        self.classifier = classifier or HeadlineClassifier()
        self.risk_engine = risk_engine or HeadlineRiskEngine()

    def normalize_headline(self, raw_headline: dict[str, Any] | None) -> HeadlineEvent:
        raw = raw_headline or {}
        warnings: list[str] = []
        title = str(raw.get("title") or "").strip()
        body = str(raw.get("body") or "").strip()
        if not title:
            title = "Untitled headline"
            warnings.append("Headline title missing; placeholder title assigned.")

        timestamp = self._parse_timestamp(raw.get("timestamp"), warnings)
        classification = self.classifier.classify(f"{title} {body}")
        event = HeadlineEvent(
            source=self._normalize_source(raw.get("source")),
            title=title,
            body=body,
            timestamp=timestamp,
            symbols=classification["symbols"],
            currencies=classification["currencies"],
            categories=classification["categories"],
            impact=classification["impact"],
            sentiment=classification["sentiment"],
            risk_level=classification["risk_level"],
            gold_relevance=classification["gold_relevance"],
            usd_relevance=classification["usd_relevance"],
            active=True,
            warnings=warnings,
        )
        return self.risk_engine.evaluate(event)

    def normalize_headlines(self, raw_headlines: list[dict[str, Any]] | None) -> list[HeadlineEvent]:
        return [self.normalize_headline(raw) for raw in raw_headlines or []]

    def _normalize_source(self, source: Any) -> str:
        value = str(source or "Financial Juice").strip().upper().replace(" ", "_")
        if value in {"FINANCIALJUICE", "FINANCIAL_JUICE"}:
            return "FINANCIAL_JUICE"
        return value or "FINANCIAL_JUICE"

    def _parse_timestamp(self, value: Any, warnings: list[str]) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if not value:
            warnings.append("Headline timestamp missing; current UTC timestamp assigned.")
            return datetime.now(timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            warnings.append("Headline timestamp could not be parsed; current UTC timestamp assigned.")
            return datetime.now(timezone.utc)
