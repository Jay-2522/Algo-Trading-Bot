from datetime import datetime, timezone

from backend.news_engine.blackout_window import BlackoutWindowService
from backend.news_engine.economic_calendar import EconomicCalendarService
from backend.news_engine.impact_classifier import ImpactClassifier
from backend.news_engine.macro_risk_scorer import MacroRiskScorer
from backend.news_engine.news_logger import NewsLogger
from backend.news_engine.news_models import BlackoutWindow, EconomicEvent, MacroRiskScore, NewsRiskStatus


class NewsFilterService:
    """Provide advisory macro-risk trading gates from economic-calendar events."""

    def __init__(
        self,
        calendar: EconomicCalendarService | None = None,
        logger: NewsLogger | None = None,
    ) -> None:
        self.calendar = calendar or EconomicCalendarService()
        self.impact_classifier = ImpactClassifier()
        self.blackout_service = BlackoutWindowService()
        self.macro_scorer = MacroRiskScorer(self.blackout_service)
        self.logger = logger or NewsLogger()

    def get_news_risk_status(self, symbol: str = "XAUUSD", persist: bool = False) -> NewsRiskStatus:
        normalized_symbol = symbol.strip().upper() if symbol else ""
        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")
        relevant_events = self._relevant_events(normalized_symbol)
        active_windows = self.blackout_service.get_active_blackouts(relevant_events)
        score = self.macro_scorer.calculate_macro_risk(relevant_events)

        if active_windows:
            allowed = False
            reason = f"Trading paused: active blackout for {active_windows[0].title}."
        elif score.risk_level == "HIGH":
            allowed = True
            reason = "High-impact macro event is upcoming; elevated caution required."
        else:
            allowed = True
            reason = "No active high-impact blackout window."

        status = NewsRiskStatus(
            trading_allowed=allowed,
            risk_level=score.risk_level,
            active_blackout=bool(active_windows),
            reason=reason,
            upcoming_events=relevant_events,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        if persist:
            self.logger.log_risk_check(normalized_symbol, status)
        return status

    def should_allow_trading(self, symbol: str = "XAUUSD", persist: bool = False) -> bool:
        return self.get_news_risk_status(symbol, persist).trading_allowed

    def get_upcoming_high_impact_events(self) -> list[EconomicEvent]:
        return self.calendar.get_high_impact_events()

    def get_blackout_windows(self) -> list[BlackoutWindow]:
        return [
            window
            for event in self.calendar.get_high_impact_events()
            if (window := self.blackout_service.create_blackout_window(event)) is not None
        ]

    def get_macro_score(self, symbol: str = "XAUUSD") -> MacroRiskScore:
        normalized_symbol = symbol.strip().upper() if symbol else ""
        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")
        return self.macro_scorer.calculate_macro_risk(self._relevant_events(normalized_symbol))

    def _relevant_events(self, symbol: str) -> list[EconomicEvent]:
        events = self.calendar.get_upcoming_events()
        if symbol == "XAUUSD":
            return [
                event
                for event in events
                if event.currency == "USD" and self.impact_classifier.is_gold_sensitive(event)
            ]
        return events
