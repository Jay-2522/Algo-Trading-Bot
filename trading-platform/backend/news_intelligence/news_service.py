from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.news_intelligence.economic_calendar_store import EconomicCalendarStore
from backend.news_intelligence.event_classifier import EventClassifier
from backend.news_intelligence.financial_juice_adapter import FinancialJuiceAdapter
from backend.news_intelligence.forex_factory_adapter import ForexFactoryAdapter
from backend.news_intelligence.headline_classifier import HeadlineClassifier
from backend.news_intelligence.headline_models import HeadlineEvent, HeadlineRiskContext
from backend.news_intelligence.headline_risk_engine import HeadlineRiskEngine
from backend.news_intelligence.headline_store import HeadlineStore
from backend.news_intelligence.headline_strategy_filter import HeadlineStrategyFilter
from backend.news_intelligence.macro_bias_engine import MacroBiasEngine
from backend.news_intelligence.macro_context_store import MacroContextStore
from backend.news_intelligence.macro_models import MacroInstrumentContext, XAUUSDMacroBiasContext
from backend.news_intelligence.macro_strategy_filter import MacroStrategyFilter
from backend.news_intelligence.models import EconomicCalendarEvent, NewsEvent, NewsIntelligenceStatus, NewsRiskContext
from backend.news_intelligence.news_risk_engine import NewsRiskEngine
from backend.news_intelligence.news_strategy_filter import NewsStrategyFilter
from backend.news_intelligence.news_window_engine import NewsWindowEngine


class NewsService:
    """Architecture-only news intelligence service with placeholder calendar data."""

    SUPPORTED_SOURCES = [
        "FOREX_FACTORY_PENDING",
        "FINANCIAL_JUICE_PENDING",
        "FINANCIAL_JUICE",
        "FIRSTSQUAWK_PENDING",
        "DXY_PENDING",
        "US10Y_PENDING",
    ]

    def __init__(
        self,
        classifier: EventClassifier | None = None,
        risk_engine: NewsRiskEngine | None = None,
        forex_factory_adapter: ForexFactoryAdapter | None = None,
        calendar_store: EconomicCalendarStore | None = None,
        window_engine: NewsWindowEngine | None = None,
        strategy_filter: NewsStrategyFilter | None = None,
        macro_bias_engine: MacroBiasEngine | None = None,
        macro_context_store: MacroContextStore | None = None,
        macro_strategy_filter: MacroStrategyFilter | None = None,
        headline_classifier: HeadlineClassifier | None = None,
        headline_risk_engine: HeadlineRiskEngine | None = None,
        financial_juice_adapter: FinancialJuiceAdapter | None = None,
        headline_store: HeadlineStore | None = None,
        headline_strategy_filter: HeadlineStrategyFilter | None = None,
    ) -> None:
        self.classifier = classifier or EventClassifier()
        self.risk_engine = risk_engine or NewsRiskEngine()
        self.forex_factory_adapter = forex_factory_adapter or ForexFactoryAdapter(
            classifier=self.classifier,
            risk_engine=self.risk_engine,
        )
        self.calendar_store = calendar_store or EconomicCalendarStore()
        self.window_engine = window_engine or NewsWindowEngine()
        self.strategy_filter = strategy_filter or NewsStrategyFilter()
        self.macro_bias_engine = macro_bias_engine or MacroBiasEngine()
        self.macro_context_store = macro_context_store or MacroContextStore()
        self.macro_strategy_filter = macro_strategy_filter or MacroStrategyFilter()
        self.headline_classifier = headline_classifier or HeadlineClassifier()
        self.headline_risk_engine = headline_risk_engine or HeadlineRiskEngine()
        self.financial_juice_adapter = financial_juice_adapter or FinancialJuiceAdapter(
            classifier=self.headline_classifier,
            risk_engine=self.headline_risk_engine,
        )
        self.headline_store = headline_store or HeadlineStore()
        self.headline_strategy_filter = headline_strategy_filter or HeadlineStrategyFilter()

    def get_status(self) -> NewsIntelligenceStatus:
        return NewsIntelligenceStatus(
            status="ARCHITECTURE_READY",
            architecture_ready=True,
            sources_supported=self.get_supported_sources(),
            event_types_supported=self.get_supported_events(),
            risk_engine_ready=True,
            strategy_integration_ready=True,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def get_supported_sources(self) -> list[str]:
        return ["FOREX_FACTORY", *self.SUPPORTED_SOURCES]

    def get_supported_events(self) -> list[str]:
        return list(self.classifier.SUPPORTED_CATEGORIES)

    def build_placeholder_calendar(self) -> list[NewsEvent]:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        titles = [
            ("US CPI Placeholder", "USD", "FOREX_FACTORY_PENDING", 6),
            ("US Non-Farm Payrolls Placeholder", "USD", "FOREX_FACTORY_PENDING", 30),
            ("FOMC Rate Decision Placeholder", "USD", "FINANCIAL_JUICE_PENDING", 45),
            ("US PMI Placeholder", "USD", "FOREX_FACTORY_PENDING", 12),
        ]
        events: list[NewsEvent] = []
        for title, currency, source, hours_ahead in titles:
            category, impact = self.classifier.classify(title)
            event = NewsEvent(
                event_id=f"news-{uuid4().hex}",
                title=title,
                category=category,
                currency=currency,
                impact=impact,
                scheduled_time=now + timedelta(hours=hours_ahead),
                source=source,
                risk_level="LOW",
                active=False,
                warnings=["Placeholder only; no external API, API key, or scraping is active."],
            )
            events.append(self.risk_engine.evaluate(event))
        return events

    def ingest_forex_factory_events(self, raw_events: list[dict]) -> list[EconomicCalendarEvent]:
        normalized = self.forex_factory_adapter.normalize_events(raw_events)
        windowed = [self.window_engine.apply_windows(event) for event in normalized]
        return self.calendar_store.upsert_events(windowed)

    def list_calendar_events(self) -> list[EconomicCalendarEvent]:
        events = self.calendar_store.list_events()
        return [self.window_engine.apply_windows(event) for event in events]

    def get_upcoming_events(self) -> list[EconomicCalendarEvent]:
        events = self.calendar_store.upcoming_events()
        return [self.window_engine.apply_windows(event) for event in events]

    def get_news_risk_context(self) -> NewsRiskContext:
        return self.window_engine.build_context(self.calendar_store.list_events())

    def evaluate_filter(self, symbol: str = "XAUUSD", news_context: NewsRiskContext | dict | None = None):
        return self.strategy_filter.evaluate(
            symbol=symbol,
            news_context=news_context or self.get_news_risk_context(),
        )

    def update_macro_context(self, symbol: str, current_value: float | None, previous_value: float | None) -> MacroInstrumentContext:
        context = self.macro_bias_engine.build_instrument_context(symbol, current_value, previous_value)
        return self.macro_context_store.update_instrument_context(context)

    def list_macro_contexts(self) -> list[MacroInstrumentContext]:
        return self.macro_context_store.get_all_contexts()

    def get_xauusd_macro_bias(self) -> XAUUSDMacroBiasContext:
        return self.macro_bias_engine.build_xauusd_macro_bias(
            dxy_context=self.macro_context_store.get_instrument_context("DXY"),
            us10y_context=self.macro_context_store.get_instrument_context("US10Y"),
        )

    def evaluate_xauusd_macro_bias(self, action: str = "WAIT") -> XAUUSDMacroBiasContext:
        return self.macro_strategy_filter.evaluate_xauusd(action, self.get_xauusd_macro_bias())

    def ingest_headlines(self, raw_headlines: list[dict]) -> list[HeadlineEvent]:
        normalized = self.financial_juice_adapter.normalize_headlines(raw_headlines)
        return self.headline_store.upsert_headlines(normalized)

    def list_headlines(self) -> list[HeadlineEvent]:
        return self.headline_store.list_headlines()

    def recent_headlines(self, minutes: int = 60) -> list[HeadlineEvent]:
        return self.headline_store.recent_headlines(minutes=minutes)

    def get_headline_risk_context(self) -> HeadlineRiskContext:
        headlines = self.headline_store.active_headlines() or self.headline_store.recent_headlines(minutes=60)
        return self.headline_risk_engine.build_context(headlines)

    def evaluate_headlines_for_xauusd(self, action: str = "WAIT", headline_context: HeadlineRiskContext | dict | None = None):
        return self.headline_strategy_filter.evaluate_xauusd(
            action=action,
            headline_context=headline_context or self.get_headline_risk_context(),
        )
