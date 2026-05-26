from backend.institutional_intelligence.performance_analytics_models import DecisionQualityMetrics, SetupPerformanceMetrics


class RejectionPatternAnalyzer:
    """Classify repeatable institutional gating themes from recorded reasons."""

    THEMES = {
        "SESSION_TIMING": ("session", "killzone", "timing", "liquidity"),
        "CONFLUENCE": ("confluence", "conflict"),
        "RISK": ("risk", "rr", "reward", "invalidation", "target"),
        "SETUP_QUALITY": ("entry zone", "setup", "missing"),
        "STRUCTURE": ("alignment", "htf", "structure", "bias"),
        "NEWS": ("news", "blackout"),
    }

    def analyze_rejections(
        self, setup_metrics: SetupPerformanceMetrics, decision_metrics: DecisionQualityMetrics
    ) -> list[str]:
        reasons = setup_metrics.recurring_rejection_reasons + decision_metrics.recurring_block_reasons
        normalized = " ".join(reasons).lower()
        patterns = [
            theme
            for theme, keywords in self.THEMES.items()
            if any(keyword in normalized for keyword in keywords)
        ]
        if setup_metrics.rejection_rate >= 60.0:
            patterns.append("HIGH_REJECTION_RATE")
        if decision_metrics.decision_block_rate >= 60.0:
            patterns.append("HIGH_DECISION_BLOCK_RATE")
        return list(dict.fromkeys(patterns))
