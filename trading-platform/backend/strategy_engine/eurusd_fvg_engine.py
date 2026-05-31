from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.strategy_models import EURUSDFVGContext, EURUSDFairValueGap


class EURUSDFVGEngine:
    """Detect EURUSD fair value gaps with forex precision and noise filtering."""

    TOLERANCE = 0.0002
    MIN_GAP_SIZE = 0.0001

    def __init__(
        self,
        session_service: MarketSessionService | None = None,
        tolerance: float = TOLERANCE,
        min_gap_size: float = MIN_GAP_SIZE,
    ) -> None:
        self.session_service = session_service or MarketSessionService()
        self.tolerance = tolerance
        self.min_gap_size = min_gap_size

    def detect(
        self,
        candles: list[Any] | None = None,
        structure_context: Any | None = None,
        liquidity_context: Any | None = None,
    ) -> EURUSDFVGContext:
        if not candles or len(candles) < 3:
            return EURUSDFVGContext(
                symbol="EURUSD",
                warnings=["Insufficient candle data for EURUSD FVG detection."],
            )

        try:
            normalized = [self._normalize(candle) for candle in candles]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return EURUSDFVGContext(
                symbol="EURUSD",
                warnings=[f"Invalid candle data supplied; EURUSD FVG context is a safe placeholder: {exc}"],
            )

        session_context = self.session_service.get_session_context(normalized[-1]["time"])
        fvgs: list[EURUSDFairValueGap] = []
        for index in range(2, len(normalized)):
            first = normalized[index - 2]
            middle = normalized[index - 1]
            third = normalized[index]
            bullish_gap = round(third["low"] - first["high"], 5)
            bearish_gap = round(first["low"] - third["high"], 5)
            displacement = self._displacement(middle)
            future = normalized[index + 1 :]

            if bullish_gap >= self.min_gap_size and displacement > 0:
                fvg = self._build_fvg("BULLISH", first, third, first["high"], third["low"], displacement, future)
                self._score(fvg, structure_context, liquidity_context, session_context)
                fvgs.append(fvg)
            if bearish_gap >= self.min_gap_size and displacement > 0:
                fvg = self._build_fvg("BEARISH", first, third, first["low"], third["high"], displacement, future)
                self._score(fvg, structure_context, liquidity_context, session_context)
                fvgs.append(fvg)

        latest = fvgs[-1] if fvgs else None
        return EURUSDFVGContext(
            symbol="EURUSD",
            fair_value_gaps=fvgs,
            latest_fvg=latest,
            bullish_fvg_detected=any(fvg.direction == "BULLISH" for fvg in fvgs),
            bearish_fvg_detected=any(fvg.direction == "BEARISH" for fvg in fvgs),
            active_fvg_detected=any(fvg.active for fvg in fvgs),
            fvg_direction=latest.direction if latest else "NONE",
            fvg_quality=latest.quality if latest else "NONE",
            fvg_confidence=self._confidence_from_warnings(latest),
            fvg_alignment_reason=latest.warnings[0] if latest and latest.warnings else "No active EURUSD FVG alignment detected.",
            warnings=[] if fvgs else ["No EURUSD fair value gaps detected in supplied candles."],
        )

    def _build_fvg(
        self,
        direction: str,
        first: dict[str, Any],
        third: dict[str, Any],
        bound_a: float,
        bound_b: float,
        displacement: float,
        future: list[dict[str, Any]],
    ) -> EURUSDFairValueGap:
        upper = round(max(bound_a, bound_b), 5)
        lower = round(min(bound_a, bound_b), 5)
        size = round(upper - lower, 5)
        fill = self._fill_percentage(direction, upper, lower, future)
        mitigated = fill >= 100.0
        return EURUSDFairValueGap(
            fvg_id=f"eurusd-fvg-{uuid4().hex}",
            symbol="EURUSD",
            direction=direction,
            start_time=first["time"].isoformat(),
            end_time=third["time"].isoformat(),
            upper_bound=upper,
            lower_bound=lower,
            midpoint=round((upper + lower) / 2, 5),
            size=size,
            fill_percentage=fill,
            mitigated=mitigated,
            active=not mitigated,
            displacement_strength=displacement,
        )

    def _score(
        self,
        fvg: EURUSDFairValueGap,
        structure_context: Any | None,
        liquidity_context: Any | None,
        session_context: Any,
    ) -> None:
        score = 0.0
        if fvg.displacement_strength > 0:
            score += 25.0
        fvg.aligned_with_structure = self._structure_aligned(fvg, structure_context)
        fvg.aligned_with_liquidity = self._liquidity_aligned(fvg, liquidity_context)
        if fvg.aligned_with_structure:
            score += 25.0
        if fvg.aligned_with_liquidity:
            score += 20.0
        if self._get(session_context, "session_quality", "LOW") == "HIGH":
            score += 15.0
        if fvg.size >= self.min_gap_size:
            score += 10.0
        if fvg.active and not fvg.mitigated:
            score += 5.0
        if score >= 75:
            quality = "HIGH"
        elif score >= 50:
            quality = "MEDIUM"
        elif score >= 25:
            quality = "LOW"
        else:
            quality = "NONE"
        fvg.quality = quality
        alignment_reason = (
            f"EURUSD {fvg.direction} FVG aligned: structure={fvg.aligned_with_structure}, "
            f"liquidity={fvg.aligned_with_liquidity}, active={fvg.active}."
        )
        fvg.warnings = [alignment_reason, f"fvg_confidence={round(score, 2)}"]

    def _structure_aligned(self, fvg: EURUSDFairValueGap, structure_context: Any | None) -> bool:
        bias = self._get(structure_context, "structure_bias", "NEUTRAL")
        bos = self._get(structure_context, "bos_direction", "NONE")
        choch = self._get(structure_context, "choch_direction", "NONE")
        if fvg.direction == "BULLISH":
            return bias == "BULLISH" or bos == "BULLISH_BOS" or choch == "BULLISH_CHOCH"
        return bias == "BEARISH" or bos == "BEARISH_BOS" or choch == "BEARISH_CHOCH"

    def _liquidity_aligned(self, fvg: EURUSDFairValueGap, liquidity_context: Any | None) -> bool:
        sweep = self._get(liquidity_context, "sweep_direction", "NONE")
        return (fvg.direction == "BULLISH" and sweep == "SELL_SIDE_SWEEP") or (
            fvg.direction == "BEARISH" and sweep == "BUY_SIDE_SWEEP"
        )

    def _fill_percentage(self, direction: str, upper: float, lower: float, future: list[dict[str, Any]]) -> float:
        if not future:
            return 0.0
        size = upper - lower
        if size <= 0:
            return 100.0
        if direction == "BULLISH":
            deepest = min(candle["low"] for candle in future)
            if deepest <= lower + self.tolerance:
                return 100.0
            if deepest < upper:
                return round(((upper - deepest) / size) * 100, 2)
            return 0.0
        highest = max(candle["high"] for candle in future)
        if highest >= upper - self.tolerance:
            return 100.0
        if highest > lower:
            return round(((highest - lower) / size) * 100, 2)
        return 0.0

    def _displacement(self, candle: dict[str, Any]) -> float:
        full_range = candle["high"] - candle["low"]
        if full_range <= 0:
            return 0.0
        return round((abs(candle["close"] - candle["open"]) / full_range) * 100, 2)

    def _confidence_from_warnings(self, fvg: EURUSDFairValueGap | None) -> float:
        if not fvg:
            return 0.0
        for warning in fvg.warnings:
            if warning.startswith("fvg_confidence="):
                return float(warning.split("=", 1)[1])
        return 0.0

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
