from backend.institutional_intelligence.ai_reasoning_models import InstitutionalReasoningReport, ReasoningQualityCheck


class ReasoningQualityChecker:
    """Ensure desk commentary remains clear, state-consistent, and simulation-only."""

    CONSISTENT_ACTIONS = {
        "READY_FOR_SIMULATION": "READY_FOR_SIMULATION",
        "WAITING_FOR_CONFIRMATION": "WAIT",
        "NO_TRADE": "MONITOR",
        "BLOCKED": "AVOID",
        "ERROR_SAFE_MODE": "AVOID",
        "MANAGING_POSITION": "MANAGE_POSITION",
    }
    PROHIBITED_CLAIMS = [
        "live trading " + "is active",
        "live trade " + "is active",
        "order has " + "been placed",
        "broker order " + "submitted",
        "live execution " + "is enabled",
    ]

    def check_reasoning_quality(
        self, reasoning_report: InstitutionalReasoningReport, final_state: str | None = None
    ) -> ReasoningQualityCheck:
        missing: list[str] = []
        for field in [
            "executive_summary",
            "detailed_reasoning",
            "client_friendly_summary",
            "dashboard_summary",
        ]:
            if not getattr(reasoning_report, field):
                missing.append(field)
        if not reasoning_report.narrative.headline:
            missing.append("narrative.headline")
        state = final_state or self._infer_state(reasoning_report.narrative.recommended_action)
        expected = self.CONSISTENT_ACTIONS.get(state)
        contradiction = bool(expected and expected != reasoning_report.narrative.recommended_action)
        warnings: list[str] = []
        combined = reasoning_report.model_dump_json().lower()
        if any(claim in combined for claim in self.PROHIBITED_CLAIMS):
            contradiction = True
            warnings.append("Reasoning contains a prohibited live-trading claim.")
        if not reasoning_report.simulation_only or reasoning_report.live_execution_enabled:
            contradiction = True
            warnings.append("Reasoning safety flags are inconsistent with simulation-only policy.")
        if contradiction and not warnings:
            warnings.append("Recommended action conflicts with final institutional state.")
        clarity = max(0.0, 100.0 - len(missing) * 18.0 - (30.0 if contradiction else 0.0))
        return ReasoningQualityCheck(
            passed=not missing and not contradiction,
            clarity_score=clarity,
            contradiction_detected=contradiction,
            missing_sections=missing,
            warnings=warnings,
        )

    def _infer_state(self, action: str) -> str:
        reverse = {value: key for key, value in self.CONSISTENT_ACTIONS.items()}
        return reverse.get(action, "NO_TRADE")
