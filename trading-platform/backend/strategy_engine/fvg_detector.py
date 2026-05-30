from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.strategy_engine.fvg_quality_scorer import FVGQualityScorer
from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.strategy_models import FairValueGap


class FairValueGapDetector:
    """Detect bullish and bearish three-candle fair value gaps."""

    def __init__(
        self,
        scorer: FVGQualityScorer | None = None,
        session_service: MarketSessionService | None = None,
    ) -> None:
        self.scorer = scorer or FVGQualityScorer()
        self.session_service = session_service or MarketSessionService()

    def detect(
        self,
        candles: list[Any] | None = None,
        symbol: str = "XAUUSD",
        structure_context: Any | None = None,
        liquidity_context: Any | None = None,
    ) -> dict[str, Any]:
        if not candles or len(candles) < 3:
            return {
                "fair_value_gaps": [],
                "latest_fvg": None,
                "warnings": ["Insufficient candle data for FVG detection."],
            }

        try:
            normalized = [self._normalize(candle, index) for index, candle in enumerate(candles)]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return {
                "fair_value_gaps": [],
                "latest_fvg": None,
                "warnings": [f"Invalid candle data supplied for FVG detection: {exc}"],
            }

        session_context = self.session_service.get_session_context(
            datetime.fromisoformat(normalized[-1]["time"])
        )
        fvgs: list[FairValueGap] = []
        for index in range(2, len(normalized)):
            first = normalized[index - 2]
            middle = normalized[index - 1]
            third = normalized[index]
            bullish = first["high"] < third["low"] and self._displacement(middle) > 0
            bearish = first["low"] > third["high"] and self._displacement(middle) > 0
            if bullish:
                fvgs.append(
                    self._build_fvg(symbol, "BULLISH", first, middle, third, first["high"], third["low"], normalized[index + 1:])
                )
            if bearish:
                fvgs.append(
                    self._build_fvg(symbol, "BEARISH", first, middle, third, first["low"], third["high"], normalized[index + 1:])
                )

        scored: list[FairValueGap] = []
        for fvg in fvgs:
            score, quality, reason = self.scorer.score(
                fvg,
                structure_context=structure_context,
                liquidity_context=liquidity_context,
                session_context=session_context,
            )
            fvg.quality = quality
            fvg.aligned_with_structure = self.scorer._structure_aligned(fvg, structure_context)
            fvg.aligned_with_liquidity = self.scorer._liquidity_aligned(fvg, liquidity_context)
            fvg.warnings = [reason, f"fvg_confidence={score}"]
            scored.append(fvg)

        latest = scored[-1] if scored else None
        warnings = [] if scored else ["No fair value gaps detected in supplied candles."]
        return {
            "fair_value_gaps": scored,
            "latest_fvg": latest,
            "warnings": warnings,
        }

    def _build_fvg(
        self,
        symbol: str,
        direction: str,
        first: dict[str, Any],
        middle: dict[str, Any],
        third: dict[str, Any],
        bound_a: float,
        bound_b: float,
        future: list[dict[str, Any]],
    ) -> FairValueGap:
        upper = round(max(bound_a, bound_b), 5)
        lower = round(min(bound_a, bound_b), 5)
        size = round(upper - lower, 5)
        fill = self._fill_percentage(direction, upper, lower, future)
        mitigated = fill >= 100.0
        return FairValueGap(
            fvg_id=f"fvg-{uuid4().hex}",
            symbol=symbol,
            direction=direction,
            start_time=first["time"],
            end_time=third["time"],
            upper_bound=upper,
            lower_bound=lower,
            midpoint=round((upper + lower) / 2, 5),
            size=size,
            fill_percentage=fill,
            mitigated=mitigated,
            active=not mitigated,
            displacement_strength=self._displacement(middle),
        )

    def _fill_percentage(self, direction: str, upper: float, lower: float, future: list[dict[str, Any]]) -> float:
        if not future:
            return 0.0
        size = upper - lower
        if size <= 0:
            return 100.0
        if direction == "BULLISH":
            deepest = min(candle["low"] for candle in future)
            if deepest <= lower:
                return 100.0
            if deepest < upper:
                return round(((upper - deepest) / size) * 100, 2)
            return 0.0
        highest = max(candle["high"] for candle in future)
        if highest >= upper:
            return 100.0
        if highest > lower:
            return round(((highest - lower) / size) * 100, 2)
        return 0.0

    def _displacement(self, candle: dict[str, Any]) -> float:
        body = abs(candle["close"] - candle["open"])
        full_range = candle["high"] - candle["low"]
        if full_range <= 0:
            return 0.0
        return round((body / full_range) * 100, 2)

    def _normalize(self, candle: Any, index: int) -> dict[str, Any]:
        return {
            "index": index,
            "time": self._time(candle).isoformat(),
            "open": float(self._value(candle, "open")),
            "high": float(self._value(candle, "high")),
            "low": float(self._value(candle, "low")),
            "close": float(self._value(candle, "close")),
        }

    def _time(self, candle: Any) -> datetime:
        raw = self._value(candle, "timestamp") if self._has_field(candle, "timestamp") else self._value(candle, "time")
        if isinstance(raw, datetime):
            if raw.tzinfo is None:
                return raw.replace(tzinfo=timezone.utc)
            return raw.astimezone(timezone.utc)
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)

    def _has_field(self, candle: Any, field: str) -> bool:
        if isinstance(candle, dict):
            return field in candle
        return hasattr(candle, field)

    def _value(self, candle: Any, field: str) -> Any:
        if isinstance(candle, dict):
            return candle[field]
        return getattr(candle, field)
