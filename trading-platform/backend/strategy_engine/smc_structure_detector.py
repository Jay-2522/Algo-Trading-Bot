from datetime import datetime, timezone
from typing import Any

from backend.strategy_engine.bos_choch_detector import BosChochDetector
from backend.strategy_engine.fvg_detector import FairValueGapDetector
from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.strategy_models import SMCStructureContext
from backend.strategy_engine.structure_strength_scorer import StructureStrengthScorer


class SMCStructureDetector:
    """Detect XAUUSD BOS/CHOCH structure while preserving future SMC placeholders."""

    def __init__(
        self,
        bos_choch_detector: BosChochDetector | None = None,
        fvg_detector: FairValueGapDetector | None = None,
        scorer: StructureStrengthScorer | None = None,
        session_service: MarketSessionService | None = None,
    ) -> None:
        self.bos_choch_detector = bos_choch_detector or BosChochDetector()
        self.fvg_detector = fvg_detector or FairValueGapDetector()
        self.scorer = scorer or StructureStrengthScorer()
        self.session_service = session_service or MarketSessionService()

    def detect(
        self,
        symbol: str = "XAUUSD",
        candles: list[Any] | None = None,
        liquidity_context: Any | None = None,
        session_context: Any | None = None,
    ) -> SMCStructureContext:
        if not candles:
            return SMCStructureContext(
                symbol=symbol,
                warnings=["No candle data supplied; BOS and CHOCH structure context is a safe placeholder."],
            )

        detected = self.bos_choch_detector.detect(candles=candles, liquidity_context=liquidity_context)
        score_session = session_context or self._session_context_from_latest(candles)
        context = SMCStructureContext(
            symbol=symbol,
            swing_highs=detected["swing_highs"],
            swing_lows=detected["swing_lows"],
            latest_swing_high=detected["latest_swing_high"],
            latest_swing_low=detected["latest_swing_low"],
            bos_detected=detected["bos_direction"] != "NONE",
            choch_detected=detected["choch_direction"] != "NONE",
            fvg_detected=False,
            order_block_detected=False,
            bos_direction=detected["bos_direction"],
            choch_direction=detected["choch_direction"],
            structure_shift_detected=detected["structure_shift_detected"],
            break_level=detected["break_level"],
            break_price=detected["break_price"],
            break_candle_time=detected["break_candle_time"],
            post_sweep_confirmation=detected["post_sweep_confirmation"],
            structure_bias=detected["structure_bias"],
            confirmation_reason=detected["confirmation_reason"],
            warnings=[
                *detected["warnings"],
                "FVG and order block detection remain placeholders for future Phase 6 days.",
            ],
        )
        strength, confidence, quality = self.scorer.score(
            context,
            liquidity_context=liquidity_context,
            session_context=score_session,
        )
        context.structure_strength = strength
        context.confidence = confidence
        context.structure_quality = quality
        fvg_data = self.fvg_detector.detect(
            candles=candles,
            symbol=symbol,
            structure_context=context,
            liquidity_context=liquidity_context,
        )
        fvgs = fvg_data["fair_value_gaps"]
        latest_fvg = fvg_data["latest_fvg"]
        context.fair_value_gaps = fvgs
        context.latest_fvg = latest_fvg
        context.bullish_fvg_detected = any(fvg.direction == "BULLISH" for fvg in fvgs)
        context.bearish_fvg_detected = any(fvg.direction == "BEARISH" for fvg in fvgs)
        context.active_fvg_detected = any(fvg.active for fvg in fvgs)
        context.fvg_direction = latest_fvg.direction if latest_fvg else "NONE"
        context.fvg_quality = latest_fvg.quality if latest_fvg else "NONE"
        context.fvg_confidence = self._fvg_confidence(latest_fvg)
        context.fvg_alignment_reason = (
            latest_fvg.warnings[0] if latest_fvg and latest_fvg.warnings else "No active FVG alignment detected."
        )
        context.fvg_detected = bool(fvgs)
        context.warnings.extend(fvg_data["warnings"])
        return context

    def _session_context_from_latest(self, candles: list[Any]):
        latest = candles[-1]
        raw = latest.get("timestamp", latest.get("time")) if isinstance(latest, dict) else getattr(latest, "timestamp", getattr(latest, "time"))
        if isinstance(raw, datetime):
            latest_time = raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
        elif isinstance(raw, (int, float)):
            latest_time = datetime.fromtimestamp(raw, tz=timezone.utc)
        else:
            latest_time = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return self.session_service.get_session_context(latest_time)

    def _fvg_confidence(self, latest_fvg: Any | None) -> float:
        if latest_fvg is None:
            return 0.0
        for warning in latest_fvg.warnings:
            if warning.startswith("fvg_confidence="):
                return float(warning.split("=", 1)[1])
        return 0.0
