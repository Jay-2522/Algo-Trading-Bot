from math import isfinite
from typing import Any
from uuid import uuid4

from backend.institutional_intelligence.bos_detector import BOSDetector
from backend.institutional_intelligence.choch_detector import CHOCHDetector
from backend.institutional_intelligence.smc_models import SwingPoint
from backend.institutional_intelligence.structure_shift_models import StructureEvent


class StructureShiftDetector:
    """Combine swing breaks and promote confirmed character changes to MSS."""

    MSS_CONFIRMATION_WINDOW = 5
    MIN_RANGE_EXPANSION = 1.5
    MIN_BODY_TO_RANGE = 0.6

    def __init__(
        self,
        bos_detector: BOSDetector | None = None,
        choch_detector: CHOCHDetector | None = None,
    ) -> None:
        self.bos_detector = bos_detector or BOSDetector()
        self.choch_detector = choch_detector or CHOCHDetector()

    def detect_structure_events(
        self,
        candles: list[Any] | None,
        swings: list[SwingPoint] | None,
        symbol: str,
        timeframe: str,
        prior_bias: Any = None,
    ) -> list[StructureEvent]:
        if not candles or not swings:
            return []
        bos_events = self.bos_detector.detect_bos(candles, swings, symbol, timeframe)
        choch_events = self.choch_detector.detect_choch(candles, swings, symbol, timeframe, prior_bias)
        mss_events = [
            mss
            for choch in choch_events
            if (mss := self._promote_to_mss(choch, candles, bos_events)) is not None
        ]
        events = bos_events + choch_events + mss_events
        unique = {}
        for event in events:
            key = (event.event_type, event.direction, event.candle_index, event.break_level)
            unique.setdefault(key, event)
        return sorted(unique.values(), key=lambda event: (event.candle_index, self._event_rank(event.event_type)))

    def _promote_to_mss(
        self,
        choch: StructureEvent,
        candles: list[Any],
        bos_events: list[StructureEvent],
    ) -> StructureEvent | None:
        if self._is_displacement(candles, choch.candle_index, choch.direction):
            return choch.model_copy(
                update={
                    "event_id": f"MSS-{uuid4().hex}",
                    "event_type": "MSS",
                    "metadata": {
                        **choch.metadata,
                        "mss_confirmation": "CHOCH_WITH_DISPLACEMENT",
                        "derived_from_event_id": choch.event_id,
                        "displacement_confirmed": True,
                    },
                }
            )
        confirmations = [
            bos
            for bos in bos_events
            if (
                bos.direction == choch.direction
                and bos.close_confirmed
                and choch.candle_index < bos.candle_index <= choch.candle_index + self.MSS_CONFIRMATION_WINDOW
            )
        ]
        if not confirmations:
            return None
        confirmation = confirmations[0]
        return choch.model_copy(
            update={
                "event_id": f"MSS-{uuid4().hex}",
                "event_type": "MSS",
                "break_price": confirmation.break_price,
                "candle_index": confirmation.candle_index,
                "timestamp": confirmation.timestamp,
                "close_confirmed": confirmation.close_confirmed,
                "wick_break": confirmation.wick_break,
                "metadata": {
                    **choch.metadata,
                    "mss_confirmation": "CHOCH_THEN_BOS",
                    "derived_from_event_id": choch.event_id,
                    "confirmation_event_id": confirmation.event_id,
                    "displacement_confirmed": self._is_displacement(
                        candles, confirmation.candle_index, confirmation.direction
                    ),
                },
            }
        )

    def _is_displacement(self, candles: list[Any], index: int, direction: str) -> bool:
        if index < 1 or index >= len(candles):
            return False
        current = self._values(candles[index])
        previous = [
            self._values(candle)
            for candle in candles[max(0, index - 5) : index]
        ]
        recent = [value for value in previous if value is not None]
        if current is None or len(recent) < 2:
            return False
        average_range = sum(value["high"] - value["low"] for value in recent) / len(recent)
        candle_range = current["high"] - current["low"]
        body = abs(current["close"] - current["open"])
        aligned = current["close"] > current["open"] if direction == "BULLISH" else current["close"] < current["open"]
        return (
            aligned
            and average_range > 0
            and candle_range >= average_range * self.MIN_RANGE_EXPANSION
            and body >= candle_range * self.MIN_BODY_TO_RANGE
        )

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            values = {field: float(getter(field)) for field in ("open", "high", "low", "close")}
            if not all(isfinite(value) for value in values.values()) or values["high"] < values["low"]:
                return None
            return values
        except (AttributeError, KeyError, TypeError, ValueError):
            return None

    def _event_rank(self, event_type: str) -> int:
        return {"BOS": 0, "CHOCH": 1, "MSS": 2}[event_type]
