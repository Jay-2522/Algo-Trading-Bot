from collections.abc import Callable
from typing import Any

from backend.institutional_intelligence.institutional_narrative_builder import InstitutionalNarrativeBuilder
from backend.institutional_intelligence.multi_timeframe_models import MultiTimeframeAlignment, TimeframeDirectionalBias
from backend.institutional_intelligence.timeframe_bias_resolver import TimeframeBiasResolver
from backend.institutional_intelligence.timeframe_conflict_detector import TimeframeConflictDetector


class MultiTimeframeAlignmentEngine:
    """Aggregate H4-to-M5 confluence into deterministic top-down intelligence."""

    TIMEFRAMES = ("H4", "H1", "M15", "M5")
    WEIGHTS = {"H4": 40.0, "H1": 30.0, "M15": 20.0, "M5": 10.0}

    def __init__(
        self,
        confluence_provider: Callable[[str, str], Any] | None = None,
        conflict_detector: TimeframeConflictDetector | None = None,
        bias_resolver: TimeframeBiasResolver | None = None,
        narrative_builder: InstitutionalNarrativeBuilder | None = None,
    ) -> None:
        self.confluence_provider = confluence_provider
        self.conflict_detector = conflict_detector or TimeframeConflictDetector()
        self.bias_resolver = bias_resolver or TimeframeBiasResolver()
        self.narrative_builder = narrative_builder or InstitutionalNarrativeBuilder()

    def analyze_alignment(
        self,
        symbol: str,
        confluence_contexts: dict[str, Any] | None = None,
    ) -> MultiTimeframeAlignment:
        normalized_symbol = symbol.strip().upper()
        contexts, unavailable = self._get_contexts(normalized_symbol, confluence_contexts)
        biases = {
            timeframe: self._build_bias(timeframe, contexts.get(timeframe))
            for timeframe in self.TIMEFRAMES
        }
        conflict_result = self.conflict_detector.detect_conflicts(biases)
        resolution = self.bias_resolver.resolve_bias(biases, conflict_result)
        quality = self._quality(biases, conflict_result.severity)
        score = self._alignment_score(biases, resolution.direction, conflict_result.severity)
        warnings = [*resolution.warnings]
        if unavailable:
            warnings.append(f"Confluence data unavailable for: {', '.join(unavailable)}.")
        if resolution.direction == "NEUTRAL":
            warnings.append("No directional multi-timeframe confirmation is available.")
        alignment = MultiTimeframeAlignment(
            symbol=normalized_symbol,
            macro_bias=biases["H4"],
            directional_bias=biases["H1"],
            execution_bias=biases["M15"],
            precision_bias=biases["M5"],
            overall_direction=resolution.direction,
            alignment_score=score,
            confidence=resolution.confidence,
            alignment_quality=quality,
            conflicts=conflict_result.conflicts,
            confirmations=resolution.confirmations,
            warnings=list(dict.fromkeys(warnings)),
        )
        return alignment.model_copy(
            update={"institutional_narrative": self.narrative_builder.build_narrative(alignment)}
        )

    def _get_contexts(
        self,
        symbol: str,
        supplied: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], list[str]]:
        contexts: dict[str, Any] = {}
        unavailable: list[str] = []
        for timeframe in self.TIMEFRAMES:
            if supplied is not None and timeframe in supplied:
                contexts[timeframe] = supplied[timeframe]
                continue
            if self.confluence_provider is None:
                unavailable.append(timeframe)
                continue
            try:
                contexts[timeframe] = self.confluence_provider(symbol, timeframe)
            except Exception:
                unavailable.append(timeframe)
        return contexts, unavailable

    def _build_bias(self, timeframe: str, context: Any) -> TimeframeDirectionalBias:
        score = self._get(context, "confluence_score")
        direction = self._get(score, "dominant_direction") or "NEUTRAL"
        confidence = float(self._get(score, "confidence") or 0.0)
        confluence_score = float(self._get(score, "overall_score") or 0.0)
        structure = self._get(self._get(context, "institutional_context"), "structure_bias")
        structure_bias = self._get(structure, "bias") or "UNCLEAR"
        latest = self._get(self._get(context, "structure_shift_context"), "latest_event")
        event_type = self._get(latest, "event_type")
        event_direction = self._get(latest, "direction")
        dominant_event = f"{event_type}_{event_direction}" if event_type and event_direction else None
        return TimeframeDirectionalBias(
            timeframe=timeframe,
            direction=direction if direction in {"BULLISH", "BEARISH", "NEUTRAL", "CONFLICTED"} else "NEUTRAL",
            confidence=confidence,
            structure_bias=structure_bias,
            confluence_score=confluence_score,
            dominant_event=dominant_event,
            narrative=(
                f"{timeframe} confluence is {direction.lower()} at {confluence_score:.2f}, "
                f"with {structure_bias.lower()} underlying structure."
            ),
        )

    def _quality(self, biases: dict[str, TimeframeDirectionalBias], severity: str) -> str:
        directions = [biases[timeframe].direction for timeframe in self.TIMEFRAMES]
        directional = [direction for direction in directions if direction in {"BULLISH", "BEARISH"}]
        if severity in {"HIGH", "SEVERE"}:
            return "CONFLICTED"
        if len(directional) == 4 and len(set(directional)) == 1:
            return "FULLY_ALIGNED"
        if (
            biases["H4"].direction in {"BULLISH", "BEARISH"}
            and biases["H4"].direction == biases["H1"].direction
            and not any(
                bias.direction in {"BULLISH", "BEARISH"} and bias.direction != biases["H4"].direction
                for bias in (biases["M15"], biases["M5"])
            )
        ):
            return "STRONGLY_ALIGNED"
        if directional and max(directional.count("BULLISH"), directional.count("BEARISH")) >= 2:
            return "PARTIALLY_ALIGNED"
        return "MIXED"

    def _alignment_score(
        self,
        biases: dict[str, TimeframeDirectionalBias],
        direction: str,
        severity: str,
    ) -> float:
        candidate = direction if direction in {"BULLISH", "BEARISH"} else None
        if candidate is None:
            totals = {
                direction_name: sum(
                    self.WEIGHTS[timeframe] * bias.confidence / 100.0
                    for timeframe, bias in biases.items()
                    if bias.direction == direction_name
                )
                for direction_name in ("BULLISH", "BEARISH")
            }
            candidate = max(totals, key=totals.get)
        score = sum(
            self.WEIGHTS[timeframe] * bias.confidence / 100.0
            for timeframe, bias in biases.items()
            if bias.direction == candidate
        )
        penalty = {"NONE": 0.0, "LOW": 5.0, "MODERATE": 12.5, "HIGH": 25.0, "SEVERE": 35.0}[severity]
        return round(min(max(score - penalty, 0.0), 100.0), 2)

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
