from backend.institutional_intelligence.simulation_decision_models import InstitutionalSimulationDecision


class SimulationDecisionExplainer:
    def explain_decision(self, decision: InstitutionalSimulationDecision) -> dict[str, object]:
        if decision.action == "SIMULATE_BUY":
            summary = "Simulation buy approved because institutional validation passed and risk geometry is acceptable."
        elif decision.action == "SIMULATE_SELL":
            summary = "Simulation sell approved because institutional validation passed and risk geometry is acceptable."
        elif decision.action == "WAIT":
            summary = "Wait for confirmation because the strongest institutional setup remains conditional."
        elif decision.action == "AVOID":
            summary = "No simulation allowed because a safety, session, news, or risk restriction is active."
        else:
            summary = "No simulation intent is available because no validated institutional setup qualified."
        return {
            "summary": summary,
            "approval_reasons": decision.approval_reasons,
            "rejection_reasons": decision.rejection_reasons,
            "warnings": decision.warnings,
        }
