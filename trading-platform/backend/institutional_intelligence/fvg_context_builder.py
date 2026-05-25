from typing import Any

from backend.institutional_intelligence.fair_value_gap_detector import FairValueGapDetector
from backend.institutional_intelligence.fair_value_gap_models import FVGContext
from backend.institutional_intelligence.fvg_mitigation_tracker import FVGMitigationTracker
from backend.institutional_intelligence.fvg_strength_scorer import FVGStrengthScorer
from backend.institutional_intelligence.structure_bias import StructureBiasAnalyzer
from backend.institutional_intelligence.swing_detector import SwingDetector


class FVGContextBuilder:
    """Build an imbalance lifecycle snapshot for later confluence analysis."""

    HIGH_QUALITY_THRESHOLD = 70.0

    def __init__(
        self,
        detector: FairValueGapDetector | None = None,
        mitigation_tracker: FVGMitigationTracker | None = None,
        scorer: FVGStrengthScorer | None = None,
    ) -> None:
        self.detector = detector or FairValueGapDetector()
        self.mitigation_tracker = mitigation_tracker or FVGMitigationTracker()
        self.scorer = scorer or FVGStrengthScorer()

    def build_fvg_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> FVGContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        source = candles or []
        structure_bias = StructureBiasAnalyzer().analyze_bias(SwingDetector().detect_swings(source))
        fvgs = []
        for detected in self.detector.detect_fvgs(source, normalized_symbol, normalized_timeframe):
            updated = self.mitigation_tracker.update_fvg_mitigation(
                detected,
                source[detected.end_index + 1 :],
            )
            score = self.scorer.score_fvg(updated, source, structure_bias)
            fvgs.append(
                updated.model_copy(
                    update={
                        "strength": score.score,
                        "metadata": {
                            **updated.metadata,
                            "bias": structure_bias.bias,
                            "bias_aligned": structure_bias.bias == updated.direction,
                            "strength_breakdown": score.model_dump(mode="json"),
                        },
                    }
                )
            )
        valid = [fvg for fvg in fvgs if fvg.valid]
        return FVGContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            fvgs=valid,
            fresh_fvgs=[fvg for fvg in valid if fvg.mitigation_status == "FRESH"],
            mitigated_fvgs=[fvg for fvg in valid if fvg.mitigation_status != "FRESH"],
            high_quality_fvgs=[fvg for fvg in valid if fvg.strength >= self.HIGH_QUALITY_THRESHOLD],
            latest_fvg=valid[-1] if valid else None,
            bullish_fvgs=[fvg for fvg in valid if fvg.direction == "BULLISH"],
            bearish_fvgs=[fvg for fvg in valid if fvg.direction == "BEARISH"],
            confidence=round(sum(fvg.strength for fvg in valid) / len(valid), 2) if valid else 0.0,
        )
