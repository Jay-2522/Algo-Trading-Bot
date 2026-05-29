from datetime import datetime, timezone
from typing import Any

from backend.strategy_engine.liquidity_level_builder import LiquidityLevelBuilder
from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.strategy_models import LiquiditySweepContext
from backend.strategy_engine.sweep_strength_scorer import SweepStrengthScorer


class LiquiditySweepDetector:
    """Detect professional XAUUSD liquidity sweep context from supplied candles."""

    def __init__(
        self,
        level_builder: LiquidityLevelBuilder | None = None,
        scorer: SweepStrengthScorer | None = None,
        session_service: MarketSessionService | None = None,
    ) -> None:
        self.level_builder = level_builder or LiquidityLevelBuilder()
        self.scorer = scorer or SweepStrengthScorer()
        self.session_service = session_service or MarketSessionService()

    def detect(self, symbol: str = "XAUUSD", candles: list[Any] | None = None) -> LiquiditySweepContext:
        levels = self.level_builder.build_levels(symbol=symbol, candles=candles)
        if not candles:
            return LiquiditySweepContext(
                symbol=symbol,
                equal_highs=levels["equal_highs"],
                equal_lows=levels["equal_lows"],
                liquidity_pools=levels["liquidity_pools"],
                warnings=levels["warnings"],
            )

        try:
            latest = candles[-1]
            latest_open = float(self._value(latest, "open"))
            latest_high = float(self._value(latest, "high"))
            latest_low = float(self._value(latest, "low"))
            latest_close = float(self._value(latest, "close"))
            latest_time = self._time(latest)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return LiquiditySweepContext(
                symbol=symbol,
                warnings=[f"Invalid candle data supplied; liquidity context is a safe placeholder: {exc}"],
            )

        session_context = self.session_service.get_session_context(latest_time)
        volume_spike = self._volume_spike(candles)
        candidates = self._sweep_candidates(levels, latest_high, latest_low, latest_close)
        active = max(candidates, key=lambda item: item["importance"], default=None)

        direction = "NONE"
        active_level = None
        sweep_price = None
        rejection_detected = False
        rejection_type = "NONE"
        if active is not None:
            direction = active["direction"]
            active_level = active["type"]
            sweep_price = latest_high if direction == "BUY_SIDE_SWEEP" else latest_low
            rejection_detected = True
            rejection_type = self._rejection_type(
                latest_open,
                latest_high,
                latest_low,
                latest_close,
                active["level"],
                direction,
                candles,
            )

        context = LiquiditySweepContext(
            symbol=symbol,
            asian_high=levels["asian_high"],
            asian_low=levels["asian_low"],
            previous_day_high=levels["previous_day_high"],
            previous_day_low=levels["previous_day_low"],
            equal_highs=levels["equal_highs"],
            equal_lows=levels["equal_lows"],
            liquidity_pools=levels["liquidity_pools"],
            swept_asian_high=any(item["type"] == "ASIAN_HIGH" for item in candidates),
            swept_asian_low=any(item["type"] == "ASIAN_LOW" for item in candidates),
            swept_previous_high=any(item["type"] == "PREVIOUS_DAY_HIGH" for item in candidates),
            swept_previous_low=any(item["type"] == "PREVIOUS_DAY_LOW" for item in candidates),
            active_sweep_level=active_level,
            sweep_price=round(sweep_price, 5) if sweep_price is not None else None,
            rejection_detected=rejection_detected,
            rejection_candle_type=rejection_type,
            session_alignment=session_context.session_quality == "HIGH",
            volume_spike_detected=volume_spike,
            structure_confirmation_pending=direction != "NONE",
            sweep_direction=direction,
            warnings=levels["warnings"],
        )
        strength, confidence, quality = self.scorer.score(context, session_context=session_context)
        context.sweep_strength = strength
        context.confidence = confidence
        context.sweep_quality = quality
        return context

    def _sweep_candidates(
        self,
        levels: dict[str, Any],
        latest_high: float,
        latest_low: float,
        latest_close: float,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        high_levels = [
            ("ASIAN_HIGH", levels["asian_high"], 25),
            ("PREVIOUS_DAY_HIGH", levels["previous_day_high"], 30),
        ]
        low_levels = [
            ("ASIAN_LOW", levels["asian_low"], 25),
            ("PREVIOUS_DAY_LOW", levels["previous_day_low"], 30),
        ]

        for level_type, level, importance in high_levels:
            if level is not None and latest_high > level and latest_close < level:
                candidates.append(
                    {"type": level_type, "level": level, "importance": importance, "direction": "BUY_SIDE_SWEEP"}
                )
        for level_type, level, importance in low_levels:
            if level is not None and latest_low < level and latest_close > level:
                candidates.append(
                    {"type": level_type, "level": level, "importance": importance, "direction": "SELL_SIDE_SWEEP"}
                )

        for pool in levels["equal_highs"]:
            level = float(pool["level"])
            if latest_high > level and latest_close < level:
                candidates.append(
                    {
                        "type": "EQUAL_HIGHS",
                        "level": level,
                        "importance": int(pool.get("importance", 20)),
                        "direction": "BUY_SIDE_SWEEP",
                    }
                )
        for pool in levels["equal_lows"]:
            level = float(pool["level"])
            if latest_low < level and latest_close > level:
                candidates.append(
                    {
                        "type": "EQUAL_LOWS",
                        "level": level,
                        "importance": int(pool.get("importance", 20)),
                        "direction": "SELL_SIDE_SWEEP",
                    }
                )
        return candidates

    def _rejection_type(
        self,
        candle_open: float,
        candle_high: float,
        candle_low: float,
        candle_close: float,
        level: float,
        direction: str,
        candles: list[Any],
    ) -> str:
        body = abs(candle_close - candle_open)
        body = body if body > 0 else 0.00001
        upper_wick = candle_high - max(candle_open, candle_close)
        lower_wick = min(candle_open, candle_close) - candle_low

        if direction == "BUY_SIDE_SWEEP" and upper_wick >= body * 1.5:
            return "PIN_BAR"
        if direction == "SELL_SIDE_SWEEP" and lower_wick >= body * 1.5:
            return "PIN_BAR"
        if self._engulfing_rejection(candles, direction):
            return "ENGULFING"
        if direction == "BUY_SIDE_SWEEP" and candle_close < level:
            return "STRONG_CLOSE_BACK_INSIDE"
        if direction == "SELL_SIDE_SWEEP" and candle_close > level:
            return "STRONG_CLOSE_BACK_INSIDE"
        return "NONE"

    def _engulfing_rejection(self, candles: list[Any], direction: str) -> bool:
        if len(candles) < 2:
            return False
        previous = candles[-2]
        latest = candles[-1]
        previous_open = float(self._value(previous, "open"))
        previous_close = float(self._value(previous, "close"))
        latest_open = float(self._value(latest, "open"))
        latest_close = float(self._value(latest, "close"))
        if direction == "BUY_SIDE_SWEEP":
            return latest_close < latest_open and latest_open >= previous_close and latest_close <= previous_open
        return latest_close > latest_open and latest_open <= previous_close and latest_close >= previous_open

    def _volume_spike(self, candles: list[Any]) -> bool:
        if len(candles) < 6:
            return False
        volumes = [float(self._optional_value(candle, "volume", self._optional_value(candle, "tick_volume", 0.0))) for candle in candles]
        if not volumes[-1]:
            return False
        baseline = sum(volumes[-6:-1]) / 5
        return baseline > 0 and volumes[-1] >= baseline * 1.5

    def _time(self, candle: Any) -> datetime:
        raw = self._value(candle, "timestamp") if self._has_field(candle, "timestamp") else self._value(candle, "time")
        if isinstance(raw, datetime):
            if raw.tzinfo is None:
                return raw.replace(tzinfo=timezone.utc)
            return raw.astimezone(timezone.utc)
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)

    def _optional_value(self, candle: Any, field: str, default: Any) -> Any:
        if self._has_field(candle, field):
            return self._value(candle, field)
        return default

    def _has_field(self, candle: Any, field: str) -> bool:
        if isinstance(candle, dict):
            return field in candle
        return hasattr(candle, field)

    def _value(self, candle: Any, field: str) -> Any:
        if isinstance(candle, dict):
            return candle[field]
        return getattr(candle, field)
