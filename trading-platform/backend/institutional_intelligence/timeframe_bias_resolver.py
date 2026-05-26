from backend.institutional_intelligence.multi_timeframe_models import (
    BiasResolutionResult,
    TimeframeConflictResult,
    TimeframeDirectionalBias,
)


class TimeframeBiasResolver:
    """Resolve top-down direction with explicit higher-timeframe authority."""

    WEIGHTS = {"H4": 40.0, "H1": 30.0, "M15": 20.0, "M5": 10.0}
    CONFLICT_PENALTY = {"NONE": 0.0, "LOW": 5.0, "MODERATE": 15.0, "HIGH": 25.0, "SEVERE": 40.0}

    def resolve_bias(
        self,
        timeframe_biases: dict[str, TimeframeDirectionalBias] | list[TimeframeDirectionalBias],
        conflicts: TimeframeConflictResult | None = None,
    ) -> BiasResolutionResult:
        biases = self._normalize(timeframe_biases)
        conflict_result = conflicts or TimeframeConflictResult()
        support = {"BULLISH": 0.0, "BEARISH": 0.0}
        for timeframe, bias in biases.items():
            if bias.direction in support:
                support[bias.direction] += self.WEIGHTS[timeframe] * bias.confidence / 100.0

        h4 = biases.get("H4")
        warnings: list[str] = []
        override = self._strong_mss_override(biases, h4)
        if override:
            direction = override.direction
            warnings.append(
                f"{override.timeframe} strong MSS temporarily overrides weak H4 evidence; confirmation is required."
            )
        elif conflict_result.severity in {"HIGH", "SEVERE"} and len([score for score in support.values() if score]) > 1:
            direction = "CONFLICTED"
        elif h4 and h4.direction in support and h4.confidence >= 40.0:
            direction = h4.direction
        elif support["BULLISH"] > support["BEARISH"]:
            direction = "BULLISH"
        elif support["BEARISH"] > support["BULLISH"]:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        leading_support = max(support.values())
        selected_support = support.get(direction, leading_support)
        confidence = max(
            selected_support - self.CONFLICT_PENALTY[conflict_result.severity],
            0.0,
        )
        confirmations = [
            f"{timeframe} confirms {direction.lower()} institutional direction."
            for timeframe in self.WEIGHTS
            if timeframe in biases and direction in support and biases[timeframe].direction == direction
        ]
        return BiasResolutionResult(
            direction=direction,
            confidence=round(min(confidence, 100.0), 2),
            confirmations=confirmations,
            warnings=warnings,
        )

    def _strong_mss_override(
        self,
        biases: dict[str, TimeframeDirectionalBias],
        h4: TimeframeDirectionalBias | None,
    ) -> TimeframeDirectionalBias | None:
        if not h4 or h4.direction not in {"BULLISH", "BEARISH"} or h4.confidence >= 50.0:
            return None
        opposite = "BEARISH" if h4.direction == "BULLISH" else "BULLISH"
        candidates = [
            bias
            for timeframe, bias in biases.items()
            if timeframe != "H4"
            and bias.direction == opposite
            and bias.confidence >= 80.0
            and bias.dominant_event
            and "MSS" in bias.dominant_event
        ]
        return max(candidates, key=lambda bias: bias.confidence, default=None)

    def _normalize(
        self,
        biases: dict[str, TimeframeDirectionalBias] | list[TimeframeDirectionalBias],
    ) -> dict[str, TimeframeDirectionalBias]:
        if isinstance(biases, dict):
            return biases
        return {bias.timeframe: bias for bias in biases}
