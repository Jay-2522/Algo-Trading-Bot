from backend.institutional_intelligence.ai_reasoning_models import InstitutionalReasoningReport


class ReasoningSummaryBuilder:
    """Compress institutional reasoning for executive and dashboard consumption."""

    def build_executive_summary(self, reasoning_report: InstitutionalReasoningReport) -> str:
        return (
            f"{reasoning_report.narrative.headline} "
            f"Confidence {reasoning_report.confidence:.1f}; action {reasoning_report.narrative.recommended_action}."
        )

    def build_client_friendly_summary(self, reasoning_report: InstitutionalReasoningReport) -> str:
        action = reasoning_report.narrative.recommended_action.replace("_", " ").lower()
        return (
            f"{reasoning_report.symbol} is assessed as {reasoning_report.narrative.institutional_bias.lower()} "
            f"with {reasoning_report.narrative.market_state.lower()} structure. "
            f"Current guidance is to {action} in simulation-only analysis."
        )

    def build_dashboard_summary(self, reasoning_report: InstitutionalReasoningReport) -> str:
        return (
            f"{reasoning_report.symbol} | {reasoning_report.narrative.institutional_bias} | "
            f"{reasoning_report.narrative.recommended_action} | {reasoning_report.confidence:.1f}% confidence"
        )
