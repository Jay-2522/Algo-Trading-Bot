from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.broker_symbol_mapper import BrokerSymbolMapper
from backend.broker_compatibility.candle_normalizer import CandleNormalizer
from backend.broker_compatibility.candle_stream_quality_checker import CandleStreamQualityChecker
from backend.broker_compatibility.canonical_candle_models import CanonicalCandle, MultiTimeframeFeedReport
from backend.broker_compatibility.mt5_candle_fetcher import MT5CandleFetcher
from backend.replay.client_symbol_registry import ClientSymbolRegistry


class MultiTimeframeFeedEngine:
    """Build canonical multi-timeframe candle feeds from read-only or fallback data."""

    SUPPORTED_TIMEFRAMES = ("M5", "M15", "H1", "H4")

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        symbol_registry: ClientSymbolRegistry | None = None,
        mapper: BrokerSymbolMapper | None = None,
        fetcher: MT5CandleFetcher | None = None,
        normalizer: CandleNormalizer | None = None,
        quality_checker: CandleStreamQualityChecker | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.symbol_registry = symbol_registry or ClientSymbolRegistry()
        self.mapper = mapper or BrokerSymbolMapper(self.registry, self.symbol_registry)
        self.fetcher = fetcher or MT5CandleFetcher()
        self.normalizer = normalizer or CandleNormalizer()
        self.quality_checker = quality_checker or CandleStreamQualityChecker()

    def build_symbol_feed(self, broker_id: str, symbol: str) -> MultiTimeframeFeedReport:
        return self._build_report(broker_id, symbol, list(self.SUPPORTED_TIMEFRAMES))

    def build_timeframe_feed(self, broker_id: str, symbol: str, timeframe: str) -> MultiTimeframeFeedReport:
        tf = str(timeframe or "").strip().upper()
        if tf not in self.SUPPORTED_TIMEFRAMES:
            tf = "M15"
        return self._build_report(broker_id, symbol, [tf])

    def build_all_feeds(self) -> list[MultiTimeframeFeedReport]:
        reports: list[MultiTimeframeFeedReport] = []
        for broker in self.registry.list_brokers():
            for instrument in self.symbol_registry.list_supported_symbols():
                reports.append(self.build_symbol_feed(broker.broker_id, instrument.canonical_symbol))
        return reports

    def _build_report(self, broker_id: str, symbol: str, timeframes: list[str]) -> MultiTimeframeFeedReport:
        broker_key = str(broker_id or "").strip().upper()
        mapping = self.mapper.map_symbol(broker_key, symbol)
        canonical = mapping.canonical_symbol
        broker_symbol = mapping.broker_symbol or canonical
        candles_by_timeframe: dict[str, list[CanonicalCandle]] = {}
        usable_timeframes: list[str] = []
        unusable_timeframes: list[str] = []

        for timeframe in timeframes:
            try:
                raw_candles = self.fetcher.fetch_candles(broker_symbol, timeframe, count=100)
                normalized = [
                    self.normalizer.normalize_candle(raw, canonical, broker_key, timeframe)
                    for raw in raw_candles
                ]
                quality = self.quality_checker.classify_feed_quality(normalized)
                for candle in normalized:
                    candle.quality = self.quality_checker.classify_candle_quality(candle)
                candles_by_timeframe[timeframe] = normalized
                if normalized and quality in {"GOOD", "WARNING"} and any(candle.usable for candle in normalized):
                    usable_timeframes.append(timeframe)
                else:
                    unusable_timeframes.append(timeframe)
            except Exception:
                candles_by_timeframe[timeframe] = []
                unusable_timeframes.append(timeframe)

        overall_quality = self._overall_quality(candles_by_timeframe, usable_timeframes, unusable_timeframes)
        return MultiTimeframeFeedReport(
            broker_id=broker_key,
            canonical_symbol=canonical,
            timeframes=timeframes,
            candles=candles_by_timeframe,
            usable_timeframes=usable_timeframes,
            unusable_timeframes=unusable_timeframes,
            overall_quality=overall_quality,
            ai_ready=bool(usable_timeframes) and not unusable_timeframes,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _overall_quality(
        self,
        candles_by_timeframe: dict[str, list[CanonicalCandle]],
        usable_timeframes: list[str],
        unusable_timeframes: list[str],
    ) -> str:
        if not candles_by_timeframe:
            return "UNAVAILABLE"
        if not usable_timeframes:
            return "UNAVAILABLE" if all(not candles for candles in candles_by_timeframe.values()) else "INVALID"
        qualities = [
            self.quality_checker.classify_feed_quality(candles)
            for candles in candles_by_timeframe.values()
        ]
        if unusable_timeframes or any(quality in {"INVALID", "UNAVAILABLE"} for quality in qualities):
            return "WARNING"
        if any(quality == "WARNING" for quality in qualities):
            return "WARNING"
        return "GOOD"
