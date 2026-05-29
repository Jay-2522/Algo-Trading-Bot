from typing import Any

from backend.strategy_engine.strategy_models import SMCStructureContext


class SMCStructureDetector:
    """Phase 6 Day 1 SMC/ICT structure placeholder with honest confidence."""

    def detect(self, symbol: str = "XAUUSD", candles: list[Any] | None = None) -> SMCStructureContext:
        if not candles:
            return SMCStructureContext(
                symbol=symbol,
                warnings=["No candle data supplied; BOS, CHOCH, FVG, and order block checks are placeholders."],
            )

        warnings = [
            "BOS/CHOCH/FVG/order block detection is a Phase 6 placeholder and does not assert a trade setup yet."
        ]
        return SMCStructureContext(
            symbol=symbol,
            bos_detected=False,
            choch_detected=False,
            fvg_detected=False,
            order_block_detected=False,
            structure_bias="NEUTRAL",
            confidence=0.0,
            warnings=warnings,
        )
