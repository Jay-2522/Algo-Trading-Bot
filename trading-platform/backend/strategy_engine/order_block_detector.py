from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.order_block_quality_scorer import OrderBlockQualityScorer
from backend.strategy_engine.strategy_models import OrderBlock


class OrderBlockDetector:
    """Detect institutional XAUUSD order blocks from displacement candles and SMC confluence."""

    def __init__(
        self,
        scorer: OrderBlockQualityScorer | None = None,
        session_service: MarketSessionService | None = None,
    ) -> None:
        self.scorer = scorer or OrderBlockQualityScorer()
        self.session_service = session_service or MarketSessionService()

    def detect(
        self,
        candles: list[Any] | None = None,
        structure_context: Any | None = None,
        liquidity_context: Any | None = None,
        symbol: str = "XAUUSD",
    ) -> dict[str, Any]:
        if not candles or len(candles) < 2:
            return {
                "order_blocks": [],
                "latest_order_block": None,
                "warnings": ["Insufficient candle data for order block detection."],
            }

        try:
            normalized = [self._normalize(candle, index) for index, candle in enumerate(candles)]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return {
                "order_blocks": [],
                "latest_order_block": None,
                "warnings": [f"Invalid candle data supplied for order block detection: {exc}"],
            }

        session_context = self.session_service.get_session_context(datetime.fromisoformat(normalized[-1]["time"]))
        order_blocks: list[OrderBlock] = []
        for index in range(1, len(normalized)):
            origin = normalized[index - 1]
            displacement = normalized[index]
            if self._is_bearish(origin) and self._is_bullish(displacement) and self._displacement(displacement) >= 60:
                if self._structure_allows("BULLISH", structure_context) or self._fvg_aligned("BULLISH", structure_context):
                    order_blocks.append(self._build_order_block(symbol, "BULLISH", origin, displacement, normalized[index + 1:], structure_context, liquidity_context))
            if self._is_bullish(origin) and self._is_bearish(displacement) and self._displacement(displacement) >= 60:
                if self._structure_allows("BEARISH", structure_context) or self._fvg_aligned("BEARISH", structure_context):
                    order_blocks.append(self._build_order_block(symbol, "BEARISH", origin, displacement, normalized[index + 1:], structure_context, liquidity_context))

        warnings = [] if order_blocks else ["No institutional order blocks detected in supplied candles."]
        latest = order_blocks[-1] if order_blocks else None
        return {"order_blocks": order_blocks, "latest_order_block": latest, "warnings": warnings}

    def _build_order_block(
        self,
        symbol: str,
        direction: str,
        origin: dict[str, Any],
        displacement: dict[str, Any],
        future: list[dict[str, Any]],
        structure_context: Any | None,
        liquidity_context: Any | None,
    ) -> OrderBlock:
        upper = round(origin["high"], 5)
        lower = round(origin["low"], 5)
        fill = self._fill_percentage(direction, upper, lower, future)
        broken = self._broken(direction, upper, lower, future)
        mitigated = fill >= 100.0
        order_block = OrderBlock(
            order_block_id=f"ob-{uuid4().hex}",
            symbol=symbol,
            direction=direction,
            creation_time=origin["time"],
            upper_bound=upper,
            lower_bound=lower,
            midpoint=round((upper + lower) / 2, 5),
            active=not broken and not mitigated,
            fresh=fill == 0.0 and not broken,
            mitigated=mitigated,
            broken=broken,
            fill_percentage=fill,
            remaining_effectiveness=0.0 if broken else round(max(0.0, 100.0 - fill), 2),
            aligned_with_structure=self._structure_allows(direction, structure_context),
            aligned_with_liquidity=self._liquidity_aligned(direction, liquidity_context),
            aligned_with_fvg=self._fvg_aligned(direction, structure_context),
            warnings=[f"displacement_strength={self._displacement(displacement)}"],
        )
        score, quality, reason = self.scorer.score(
            order_block,
            structure_context=structure_context,
            liquidity_context=liquidity_context,
            session_context=self.session_service.get_session_context(datetime.fromisoformat(displacement["time"])),
        )
        order_block.strength = score
        order_block.quality = quality
        order_block.warnings = [reason, *order_block.warnings, f"order_block_confidence={score}"]
        return order_block

    def _fill_percentage(self, direction: str, upper: float, lower: float, future: list[dict[str, Any]]) -> float:
        if not future:
            return 0.0
        size = upper - lower
        if size <= 0:
            return 100.0
        if direction == "BULLISH":
            revisits = [candle["low"] for candle in future if candle["low"] <= upper and candle["high"] >= lower]
            if not revisits:
                return 0.0
            deepest = min(revisits)
            if deepest <= lower:
                return 100.0
            return round(((upper - deepest) / size) * 100, 2)
        revisits = [candle["high"] for candle in future if candle["high"] >= lower and candle["low"] <= upper]
        if not revisits:
            return 0.0
        highest = max(revisits)
        if highest >= upper:
            return 100.0
        return round(((highest - lower) / size) * 100, 2)

    def _broken(self, direction: str, upper: float, lower: float, future: list[dict[str, Any]]) -> bool:
        if direction == "BULLISH":
            return any(candle["close"] < lower for candle in future)
        return any(candle["close"] > upper for candle in future)

    def _structure_allows(self, direction: str, structure_context: Any | None) -> bool:
        if structure_context is None:
            return False
        bos = self._get(structure_context, "bos_direction", "NONE")
        choch = self._get(structure_context, "choch_direction", "NONE")
        if direction == "BULLISH":
            return bos == "BULLISH_BOS" or choch == "BULLISH_CHOCH"
        return bos == "BEARISH_BOS" or choch == "BEARISH_CHOCH"

    def _liquidity_aligned(self, direction: str, liquidity_context: Any | None) -> bool:
        sweep = self._get(liquidity_context, "sweep_direction", "NONE")
        if direction == "BULLISH":
            return sweep == "SELL_SIDE_SWEEP"
        return sweep == "BUY_SIDE_SWEEP"

    def _fvg_aligned(self, direction: str, structure_context: Any | None) -> bool:
        if structure_context is None:
            return False
        latest = self._get(structure_context, "latest_fvg", None)
        if latest is not None and self._get(latest, "direction", "NONE") == direction:
            return True
        return any(
            self._get(fvg, "direction", "NONE") == direction
            for fvg in self._get(structure_context, "fair_value_gaps", [])
        )

    def _displacement(self, candle: dict[str, Any]) -> float:
        candle_range = candle["high"] - candle["low"]
        if candle_range <= 0:
            return 0.0
        return round((abs(candle["close"] - candle["open"]) / candle_range) * 100, 2)

    def _is_bullish(self, candle: dict[str, Any]) -> bool:
        return candle["close"] > candle["open"]

    def _is_bearish(self, candle: dict[str, Any]) -> bool:
        return candle["close"] < candle["open"]

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
            return raw.replace(tzinfo=timezone.utc) if raw.tzinfo is None else raw.astimezone(timezone.utc)
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

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
