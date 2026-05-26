from datetime import datetime, time, timezone
from typing import Any

from backend.institutional_intelligence.killzone_detector import KillzoneDetector
from backend.institutional_intelligence.session_liquidity_analyzer import SessionLiquidityAnalyzer
from backend.institutional_intelligence.session_manipulation_detector import SessionManipulationDetector
from backend.institutional_intelligence.session_models import SessionIntelligenceContext
from backend.institutional_intelligence.session_quality_scorer import SessionQualityScorer
from backend.institutional_intelligence.session_range_detector import SessionRangeDetector


class SessionContextBuilder:
    """Build session timing intelligence and temper it with broader institutional conflict."""

    def __init__(
        self,
        range_detector: SessionRangeDetector | None = None,
        killzone_detector: KillzoneDetector | None = None,
        liquidity_analyzer: SessionLiquidityAnalyzer | None = None,
        manipulation_detector: SessionManipulationDetector | None = None,
        quality_scorer: SessionQualityScorer | None = None,
    ) -> None:
        self.range_detector = range_detector or SessionRangeDetector()
        self.killzone_detector = killzone_detector or KillzoneDetector()
        self.liquidity_analyzer = liquidity_analyzer or SessionLiquidityAnalyzer()
        self.manipulation_detector = manipulation_detector or SessionManipulationDetector()
        self.quality_scorer = quality_scorer or SessionQualityScorer()

    def build_session_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        sweep_context: Any = None,
        news_status: Any = None,
        confluence_context: Any = None,
        alignment_context: Any = None,
        current_time_utc: datetime | None = None,
    ) -> SessionIntelligenceContext:
        ranges = self.range_detector.detect_all_session_ranges(candles)
        killzone = self.killzone_detector.get_active_killzone(current_time_utc)
        current_session = self._current_session(current_time_utc, killzone.session_name)
        active_range = ranges.get(current_session, ranges["ASIAN"])
        liquidity = self.liquidity_analyzer.analyze_liquidity(candles, active_range, sweep_context)
        manipulation = self.manipulation_detector.detect_manipulation(candles, ranges["ASIAN"], sweep_context)
        score = self.quality_scorer.score_session_quality(killzone, liquidity, manipulation, news_status)
        warnings = self._warnings(killzone, liquidity, news_status, confluence_context, alignment_context)
        readiness = self._readiness(killzone, liquidity, score, news_status, warnings)
        return SessionIntelligenceContext(
            symbol=symbol.strip().upper(),
            timeframe=timeframe.strip().upper(),
            current_session=current_session,
            active_killzone=killzone,
            asian_range=ranges["ASIAN"],
            london_range=ranges["LONDON"],
            new_york_range=ranges["NEW_YORK"],
            liquidity_profile=liquidity,
            manipulation_signals=manipulation,
            session_quality_score=score,
            trade_timing_readiness=readiness,
            warnings=warnings,
        )

    def _current_session(self, now: datetime | None, killzone_session: str) -> str:
        if killzone_session in {"LONDON", "NEW_YORK"}:
            return killzone_session
        value = now or datetime.now(timezone.utc)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        current = value.astimezone(timezone.utc).time()
        if time(12, 0) <= current < time(21, 0):
            return "NEW_YORK"
        if time(7, 0) <= current < time(16, 0):
            return "LONDON"
        if time(0, 0) <= current < time(9, 0):
            return "ASIAN"
        return "CLOSED"

    def _warnings(
        self,
        killzone: Any,
        liquidity: Any,
        news_status: Any,
        confluence: Any,
        alignment: Any,
    ) -> list[str]:
        warnings = []
        if not killzone.active_killzone:
            warnings.append("No institutional killzone is currently active.")
        if liquidity.liquidity_quality in {"LOW", "POOR"}:
            warnings.append("Observed session liquidity is insufficient for high-quality timing.")
        if self._get(news_status, "active_blackout") or self._get(news_status, "trading_allowed") is False:
            warnings.append("Active news blackout prevents session-based simulation readiness.")
        if self._get(self._get(confluence, "confluence_score"), "dominant_direction") == "CONFLICTED":
            warnings.append("Institutional confluence is directionally conflicted.")
        if self._get(alignment, "overall_direction") == "CONFLICTED":
            warnings.append("Multi-timeframe alignment is conflicted.")
        return warnings

    def _readiness(
        self,
        killzone: Any,
        liquidity: Any,
        score: float,
        news_status: Any,
        warnings: list[str],
    ) -> str:
        if self._get(news_status, "active_blackout") or self._get(news_status, "trading_allowed") is False:
            return "AVOID_NEWS_WINDOW"
        if liquidity.liquidity_quality in {"LOW", "POOR"}:
            return "AVOID_LOW_LIQUIDITY"
        if not killzone.active_killzone:
            return "WAIT_FOR_KILLZONE"
        if score >= 70.0 and not any("conflicted" in warning.lower() for warning in warnings):
            return "HIGH_QUALITY_WINDOW"
        return "NORMAL_MONITORING"

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
