from typing import Any

from backend.institutional_intelligence.displacement_detector import DisplacementDetector
from backend.institutional_intelligence.liquidity_mapper import LiquidityMapper
from backend.institutional_intelligence.premium_discount import PremiumDiscountAnalyzer
from backend.institutional_intelligence.smc_models import InstitutionalContext
from backend.institutional_intelligence.structure_bias import StructureBiasAnalyzer
from backend.institutional_intelligence.swing_detector import SwingDetector


class InstitutionalContextBuilder:
    """Combine SMC observations into one analysis-only institutional snapshot."""

    def __init__(self) -> None:
        self.swings = SwingDetector()
        self.liquidity = LiquidityMapper()
        self.bias = StructureBiasAnalyzer()
        self.premium_discount = PremiumDiscountAnalyzer()
        self.displacement = DisplacementDetector()

    def build_context(self, symbol: str, timeframe: str, candles: list[Any] | None) -> InstitutionalContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        source = candles or []
        swings = self.swings.detect_swings(source)
        zone = self.premium_discount.calculate_zone(source)
        pools = self.liquidity.map_liquidity_pools(source, swings)
        pools = self.liquidity.mark_swept_liquidity(pools, zone.current_price)
        structure = self.bias.analyze_bias(swings)
        moves = self.displacement.detect_displacement(source)
        confidence_inputs = [
            structure.confidence,
            min(len(swings) * 10.0, 100.0),
            100.0 if pools else 0.0,
            100.0 if moves else 0.0,
        ]
        confidence = round(sum(confidence_inputs) / len(confidence_inputs), 2) if source else 0.0
        return InstitutionalContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            swings=swings,
            liquidity_pools=pools,
            structure_bias=structure,
            premium_discount=zone,
            displacement=moves,
            confidence=confidence,
        )
