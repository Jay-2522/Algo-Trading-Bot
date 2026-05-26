from backend.institutional_intelligence.multi_timeframe_models import (
    TimeframeConflictResult,
    TimeframeDirectionalBias,
)


class TimeframeConflictDetector:
    """Detect disagreement that weakens a top-down institutional thesis."""

    ORDER = ("H4", "H1", "M15", "M5")
    SEVERITY_RANK = {"NONE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3, "SEVERE": 4}

    def detect_conflicts(
        self,
        timeframe_biases: dict[str, TimeframeDirectionalBias] | list[TimeframeDirectionalBias],
    ) -> TimeframeConflictResult:
        biases = self._normalize(timeframe_biases)
        conflicts: list[str] = []
        affected: list[str] = []
        severity = "NONE"
        h4 = biases.get("H4")

        directional = {
            bias.direction
            for bias in biases.values()
            if bias.direction in {"BULLISH", "BEARISH"}
        }
        if directional == {"BULLISH", "BEARISH"}:
            conflicts.append("Bullish and bearish institutional signals disagree across timeframes.")
            affected.extend(
                timeframe for timeframe, bias in biases.items() if bias.direction in directional
            )
            severity = self._stronger(severity, "HIGH")

        if h4 and h4.direction in {"BULLISH", "BEARISH"}:
            opposite = "BEARISH" if h4.direction == "BULLISH" else "BULLISH"
            for timeframe in ("M15", "M5"):
                lower = biases.get(timeframe)
                if lower and lower.direction == opposite:
                    conflicts.append(
                        f"{timeframe} {opposite.lower()} signal conflicts with "
                        f"H4 {h4.direction.lower()} macro bias."
                    )
                    affected.extend(["H4", timeframe])
                    severity = self._stronger(severity, "SEVERE")
                    if lower.dominant_event and "MSS" in lower.dominant_event:
                        conflicts.append(
                            f"{timeframe} MSS reversal is forming against the prevailing H4 direction."
                        )

        if h4 and h4.direction in {"NEUTRAL", "CONFLICTED"}:
            aggressive = [
                timeframe
                for timeframe in ("H1", "M15", "M5")
                if timeframe in biases
                and biases[timeframe].direction in {"BULLISH", "BEARISH"}
                and biases[timeframe].confluence_score >= 65.0
            ]
            if aggressive:
                conflicts.append("Directional lower-timeframe setup is unsupported by a neutral H4 macro bias.")
                affected.extend(["H4", *aggressive])
                severity = self._stronger(severity, "MODERATE")

        h1 = biases.get("H1")
        m15 = biases.get("M15")
        if (
            h1
            and m15
            and h1.direction in {"BULLISH", "BEARISH"}
            and m15.direction in {"BULLISH", "BEARISH"}
            and h1.direction != m15.direction
            and h1.confluence_score >= 65.0
            and m15.confluence_score >= 65.0
        ):
            conflicts.append("H1 directional structure and M15 execution structure carry opposing conviction.")
            affected.extend(["H1", "M15"])
            severity = self._stronger(severity, "HIGH")

        return TimeframeConflictResult(
            conflicts=list(dict.fromkeys(conflicts)),
            severity=severity,
            affected_timeframes=list(dict.fromkeys(affected)),
        )

    def _normalize(
        self,
        biases: dict[str, TimeframeDirectionalBias] | list[TimeframeDirectionalBias],
    ) -> dict[str, TimeframeDirectionalBias]:
        if isinstance(biases, dict):
            return {timeframe: biases[timeframe] for timeframe in self.ORDER if timeframe in biases}
        return {bias.timeframe: bias for bias in biases}

    def _stronger(self, current: str, candidate: str) -> str:
        return candidate if self.SEVERITY_RANK[candidate] > self.SEVERITY_RANK[current] else current
