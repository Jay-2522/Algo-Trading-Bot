from backend.institutional_intelligence.multi_timeframe_models import (
    InstitutionalNarrative,
    MultiTimeframeAlignment,
    TimeframeDirectionalBias,
)


class InstitutionalNarrativeBuilder:
    """Translate alignment evidence into concise dashboard-ready reasoning."""

    def build_narrative(self, alignment: MultiTimeframeAlignment) -> InstitutionalNarrative:
        biases = [
            alignment.macro_bias,
            alignment.directional_bias,
            alignment.execution_bias,
            alignment.precision_bias,
        ]
        bullish = [
            f"{bias.timeframe} supports bullish institutional order flow."
            for bias in biases
            if bias.direction == "BULLISH"
        ]
        bearish = [
            f"{bias.timeframe} supports bearish institutional order flow."
            for bias in biases
            if bias.direction == "BEARISH"
        ]
        return InstitutionalNarrative(
            symbol=alignment.symbol,
            macro_story=self._story("Macro", alignment.macro_bias),
            directional_story=self._story("Directional", alignment.directional_bias),
            execution_story=self._story("Execution", alignment.execution_bias),
            precision_story=self._story("Precision", alignment.precision_bias),
            summary=self._summary(alignment),
            bullish_factors=bullish,
            bearish_factors=bearish,
            warnings=list(dict.fromkeys([*alignment.conflicts, *alignment.warnings])),
        )

    def _story(self, role: str, bias: TimeframeDirectionalBias) -> str:
        event = f" Latest structural signal: {bias.dominant_event}." if bias.dominant_event else ""
        return (
            f"{role} timeframe {bias.timeframe} is {bias.direction.lower()} "
            f"with {bias.confidence:.2f}% confidence.{event}"
        )

    def _summary(self, alignment: MultiTimeframeAlignment) -> str:
        if alignment.alignment_quality == "FULLY_ALIGNED":
            return (
                f"H4, H1, M15, and M5 are fully aligned {alignment.overall_direction.lower()}, "
                "supporting a coherent institutional narrative for simulation assessment."
            )
        if alignment.alignment_quality == "CONFLICTED":
            return "Higher and lower timeframe institutional evidence conflicts; await structural resolution."
        if alignment.overall_direction in {"BULLISH", "BEARISH"}:
            return (
                f"Top-down evidence leans {alignment.overall_direction.lower()} with "
                f"{alignment.alignment_quality.lower().replace('_', ' ')} confirmation."
            )
        return "No unified top-down institutional direction is currently established."
