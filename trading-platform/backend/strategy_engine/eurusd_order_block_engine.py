from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.strategy_models import EURUSDOrderBlock, EURUSDOrderBlockContext


class EURUSDOrderBlockEngine:
    """Detect EURUSD order blocks with forex-sized noise filtering."""

    TOLERANCE = 0.0002
    MIN_CANDLE_RANGE = 0.0001

    def __init__(
        self,
        session_service: MarketSessionService | None = None,
        tolerance: float = TOLERANCE,
        min_candle_range: float = MIN_CANDLE_RANGE,
    ) -> None:
        self.session_service = session_service or MarketSessionService()
        self.tolerance = tolerance
        self.min_candle_range = min_candle_range

    def detect(
        self,
        candles: list[Any] | None = None,
        structure_context: Any | None = None,
        liquidity_context: Any | None = None,
        fvg_context: Any | None = None,
    ) -> EURUSDOrderBlockContext:
        if not candles or len(candles) < 2:
            return EURUSDOrderBlockContext(
                symbol="EURUSD",
                warnings=["Insufficient candle data for EURUSD order block detection."],
            )

        try:
            normalized = [self._normalize(candle) for candle in candles]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return EURUSDOrderBlockContext(
                symbol="EURUSD",
                warnings=[f"Invalid candle data supplied; EURUSD order block context is a safe placeholder: {exc}"],
            )

        order_blocks: list[EURUSDOrderBlock] = []
        for index in range(1, len(normalized)):
            origin = normalized[index - 1]
            displacement = normalized[index]
            if self._range(origin) < self.min_candle_range:
                continue
            if self._is_bearish(origin) and self._is_bullish(displacement) and self._meaningful_displacement(displacement):
                if self._structure_aligned("BULLISH", structure_context) or self._fvg_aligned("BULLISH", fvg_context):
                    order_blocks.append(
                        self._build_order_block("BULLISH", origin, displacement, normalized[index + 1 :], structure_context, liquidity_context, fvg_context)
                    )
            if self._is_bullish(origin) and self._is_bearish(displacement) and self._meaningful_displacement(displacement):
                if self._structure_aligned("BEARISH", structure_context) or self._fvg_aligned("BEARISH", fvg_context):
                    order_blocks.append(
                        self._build_order_block("BEARISH", origin, displacement, normalized[index + 1 :], structure_context, liquidity_context, fvg_context)
                    )

        latest = order_blocks[-1] if order_blocks else None
        return EURUSDOrderBlockContext(
            symbol="EURUSD",
            order_blocks=order_blocks,
            latest_order_block=latest,
            bullish_order_block_detected=any(order_block.direction == "BULLISH" for order_block in order_blocks),
            bearish_order_block_detected=any(order_block.direction == "BEARISH" for order_block in order_blocks),
            active_order_block_detected=any(order_block.active for order_block in order_blocks),
            order_block_direction=latest.direction if latest else "NONE",
            order_block_quality=latest.quality if latest else "NONE",
            order_block_confidence=latest.strength if latest else 0.0,
            order_block_alignment_reason=latest.warnings[0] if latest and latest.warnings else "No active EURUSD order block alignment detected.",
            warnings=[] if order_blocks else ["No EURUSD order blocks detected in supplied candles."],
        )

    def _build_order_block(
        self,
        direction: str,
        origin: dict[str, Any],
        displacement: dict[str, Any],
        future: list[dict[str, Any]],
        structure_context: Any | None,
        liquidity_context: Any | None,
        fvg_context: Any | None,
    ) -> EURUSDOrderBlock:
        upper = round(origin["high"], 5)
        lower = round(origin["low"], 5)
        fill = self._fill_percentage(direction, upper, lower, future)
        broken = self._broken(direction, upper, lower, future)
        mitigated = fill > 0
        block = EURUSDOrderBlock(
            order_block_id=f"eurusd-ob-{uuid4().hex}",
            symbol="EURUSD",
            direction=direction,
            creation_time=origin["time"].isoformat(),
            upper_bound=upper,
            lower_bound=lower,
            midpoint=round((upper + lower) / 2, 5),
            active=not broken,
            fresh=not mitigated and not broken,
            mitigated=mitigated,
            broken=broken,
            fill_percentage=fill,
            aligned_with_structure=self._structure_aligned(direction, structure_context),
            aligned_with_liquidity=self._liquidity_aligned(direction, liquidity_context),
            aligned_with_fvg=self._fvg_aligned(direction, fvg_context),
        )
        self._score(block, displacement)
        return block

    def _score(self, order_block: EURUSDOrderBlock, displacement: dict[str, Any]) -> None:
        score = 0.0
        if order_block.aligned_with_structure:
            score += 25.0
        if order_block.aligned_with_fvg:
            score += 20.0
        if order_block.aligned_with_liquidity:
            score += 20.0
        if self.session_service.get_session_context(displacement["time"]).session_quality == "HIGH":
            score += 15.0
        if order_block.fresh:
            score += 10.0
        if self._displacement_strength(displacement) >= 50:
            score += 10.0
        if score >= 75:
            quality = "HIGH"
        elif score >= 50:
            quality = "MEDIUM"
        elif score >= 25:
            quality = "LOW"
        else:
            quality = "NONE"
        order_block.strength = round(score, 2)
        order_block.quality = quality
        order_block.warnings = [
            (
                f"EURUSD {order_block.direction} order block aligned: "
                f"structure={order_block.aligned_with_structure}, "
                f"liquidity={order_block.aligned_with_liquidity}, "
                f"fvg={order_block.aligned_with_fvg}, fresh={order_block.fresh}."
            ),
            f"order_block_confidence={round(score, 2)}",
            f"displacement_strength={self._displacement_strength(displacement)}",
        ]

    def _fill_percentage(self, direction: str, upper: float, lower: float, future: list[dict[str, Any]]) -> float:
        if not future:
            return 0.0
        size = upper - lower
        if size <= 0:
            return 100.0
        revisits = [
            candle
            for candle in future
            if candle["low"] <= upper + self.tolerance and candle["high"] >= lower - self.tolerance
        ]
        if not revisits:
            return 0.0
        if direction == "BULLISH":
            deepest = min(candle["low"] for candle in revisits)
            if deepest <= lower:
                return 100.0
            return round(max(0.0, ((upper - deepest) / size) * 100), 2)
        highest = max(candle["high"] for candle in revisits)
        if highest >= upper:
            return 100.0
        return round(max(0.0, ((highest - lower) / size) * 100), 2)

    def _broken(self, direction: str, upper: float, lower: float, future: list[dict[str, Any]]) -> bool:
        if direction == "BULLISH":
            return any(candle["close"] < lower - self.tolerance for candle in future)
        return any(candle["close"] > upper + self.tolerance for candle in future)

    def _structure_aligned(self, direction: str, structure_context: Any | None) -> bool:
        bos = self._get(structure_context, "bos_direction", "NONE")
        choch = self._get(structure_context, "choch_direction", "NONE")
        bias = self._get(structure_context, "structure_bias", "NEUTRAL")
        if direction == "BULLISH":
            return bos == "BULLISH_BOS" or choch == "BULLISH_CHOCH" or bias == "BULLISH"
        return bos == "BEARISH_BOS" or choch == "BEARISH_CHOCH" or bias == "BEARISH"

    def _liquidity_aligned(self, direction: str, liquidity_context: Any | None) -> bool:
        sweep = self._get(liquidity_context, "sweep_direction", "NONE")
        return (direction == "BULLISH" and sweep == "SELL_SIDE_SWEEP") or (
            direction == "BEARISH" and sweep == "BUY_SIDE_SWEEP"
        )

    def _fvg_aligned(self, direction: str, fvg_context: Any | None) -> bool:
        latest = self._get(fvg_context, "latest_fvg", None)
        if latest is not None and self._get(latest, "direction", "NONE") == direction:
            return True
        return any(
            self._get(fvg, "direction", "NONE") == direction
            for fvg in self._get(fvg_context, "fair_value_gaps", [])
        )

    def _meaningful_displacement(self, candle: dict[str, Any]) -> bool:
        return self._range(candle) >= self.min_candle_range and self._displacement_strength(candle) >= 50.0

    def _displacement_strength(self, candle: dict[str, Any]) -> float:
        candle_range = self._range(candle)
        if candle_range <= 0:
            return 0.0
        return round((abs(candle["close"] - candle["open"]) / candle_range) * 100, 2)

    def _range(self, candle: dict[str, Any]) -> float:
        return round(candle["high"] - candle["low"], 5)

    def _is_bullish(self, candle: dict[str, Any]) -> bool:
        return candle["close"] > candle["open"]

    def _is_bearish(self, candle: dict[str, Any]) -> bool:
        return candle["close"] < candle["open"]

    def _normalize(self, candle: Any) -> dict[str, Any]:
        return {
            "time": self._time(self._field(candle, "timestamp") if self._has_field(candle, "timestamp") else self._field(candle, "time")),
            "open": float(self._field(candle, "open")),
            "high": float(self._field(candle, "high")),
            "low": float(self._field(candle, "low")),
            "close": float(self._field(candle, "close")),
        }

    def _time(self, raw: Any) -> datetime:
        if isinstance(raw, datetime):
            return raw.replace(tzinfo=timezone.utc) if raw.tzinfo is None else raw.astimezone(timezone.utc)
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)

    def _has_field(self, candle: Any, field: str) -> bool:
        return field in candle if isinstance(candle, dict) else hasattr(candle, field)

    def _field(self, candle: Any, field: str) -> Any:
        return candle[field] if isinstance(candle, dict) else getattr(candle, field)

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
