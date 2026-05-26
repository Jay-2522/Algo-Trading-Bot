from backend.institutional_intelligence.ai_reasoning_models import InstitutionalReasoningReport


class ReasoningSummaryBuilder:
    """Compress institutional reasoning for executive and dashboard consumption."""

    def build_executive_summary(self, reasoning_report: InstitutionalReasoningReport) -> str:
        action = reasoning_report.narrative.recommended_action.replace("_", " ").title()
        return f"{reasoning_report.symbol}: {action}. Confidence {reasoning_report.confidence:.1f}%."

    def build_client_friendly_summary(self, reasoning_report: InstitutionalReasoningReport) -> str:
        action = reasoning_report.narrative.recommended_action
        copy = {
            "READY_FOR_SIMULATION": "A qualified setup is ready for simulation review.",
            "WAIT": "The setup needs confirmation before simulation.",
            "AVOID": "Current conditions do not support simulation.",
            "MANAGE_POSITION": "An existing paper position is being managed.",
            "MONITOR": "No qualified simulated setup is present.",
        }
        return f"{reasoning_report.symbol}: {copy.get(action, 'Monitor institutional conditions.')} Broker execution remains disabled."

    def build_dashboard_summary(self, reasoning_report: InstitutionalReasoningReport) -> str:
        action = reasoning_report.narrative.recommended_action.replace("_", " ")
        return f"{reasoning_report.symbol} | {action} | {reasoning_report.confidence:.1f}%"
