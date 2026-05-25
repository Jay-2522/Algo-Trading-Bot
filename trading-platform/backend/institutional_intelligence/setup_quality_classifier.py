class SetupQualityClassifier:
    """Convert deterministic confluence scores into non-executable quality labels."""

    def classify_setup(
        self,
        score: float,
        confidence: float,
        direction_conflict: bool = False,
    ) -> tuple[str, str]:
        if direction_conflict or score < 40.0:
            return "NO_TRADE", "NO_SETUP"
        if score >= 85.0 and confidence >= 80.0:
            return "A_PLUS", "READY_FOR_SIMULATION"
        if score >= 75.0:
            return "A", "READY_FOR_SIMULATION"
        if score >= 65.0:
            return "B", "WAIT_FOR_CONFIRMATION"
        if score >= 55.0:
            return "C", "WAIT_FOR_CONFIRMATION"
        return "LOW_QUALITY", "AVOID"
