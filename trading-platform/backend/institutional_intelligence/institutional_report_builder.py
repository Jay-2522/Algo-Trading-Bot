from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport


class InstitutionalReportBuilder:
    """Produce compact dashboard explanations from the coordinated institutional report."""

    def build_executive_summary(self, report: InstitutionalOrchestrationReport) -> str:
        state = report.system_state.final_state if report.system_state else "NO_TRADE"
        direction = report.system_state.institutional_bias if report.system_state else "UNCLEAR"
        if state == "MANAGING_POSITION":
            return f"{direction} institutional position is being managed in paper-trading mode."
        if state == "READY_FOR_SIMULATION":
            return f"{direction} institutional conditions qualify for simulation-only evaluation."
        if state == "WAITING_FOR_CONFIRMATION":
            return f"{direction} setup exists but requires confirmation before simulation."
        if state == "BLOCKED":
            return "Institutional simulation is blocked by risk, timing, or management exit constraints."
        if state == "ERROR_SAFE_MODE":
            return "Institutional pipeline degraded safely; no simulation action is authorized."
        return "No qualified institutional paper setup is currently available."

    def extract_strengths(self, report: InstitutionalOrchestrationReport) -> list[str]:
        strengths: list[str] = []
        confluence = report.confluence_context.confluence_score if report.confluence_context else None
        if confluence and confluence.overall_score >= 65:
            strengths.append(f"Confluence quality is {confluence.setup_quality} at {confluence.overall_score:.1f}.")
        if report.alignment_context and report.alignment_context.alignment_quality in {"FULLY_ALIGNED", "STRONGLY_ALIGNED"}:
            strengths.append(f"Timeframes are {report.alignment_context.alignment_quality.lower().replace('_', ' ')}.")
        if report.session_context and report.session_context.trade_timing_readiness == "HIGH_QUALITY_WINDOW":
            strengths.append("Active session timing supports institutional evaluation.")
        if report.setup_validation_context and report.setup_validation_context.simulation_eligible:
            strengths.append("Setup passed simulation eligibility validation.")
        if report.position_management_context and report.position_management_context.active_positions:
            strengths.append("Active paper position has institutional management coverage.")
        return strengths

    def extract_weaknesses(self, report: InstitutionalOrchestrationReport) -> list[str]:
        weaknesses: list[str] = []
        if report.alignment_context and report.alignment_context.conflicts:
            weaknesses.append("Timeframe alignment contains directional conflict.")
        if report.session_context and report.session_context.trade_timing_readiness != "HIGH_QUALITY_WINDOW":
            weaknesses.append(f"Session readiness is {report.session_context.trade_timing_readiness}.")
        if report.confluence_context and report.confluence_context.confluence_score.setup_quality in {"LOW_QUALITY", "NO_TRADE"}:
            weaknesses.append("Institutional confluence is not high quality.")
        if report.setup_validation_context and not report.setup_validation_context.simulation_eligible:
            weaknesses.append("No setup is currently approved for simulation.")
        return weaknesses

    def extract_warnings(self, report: InstitutionalOrchestrationReport) -> list[str]:
        warnings = list(report.system_state.warnings if report.system_state else [])
        warnings.extend(
            f"{step.step_name} failed safely: {step.error}" for step in report.pipeline_steps if step.status == "FAILED"
        )
        if report.live_execution_enabled:
            warnings.append("Safety violation: live execution flag must remain false.")
        if not report.simulation_only:
            warnings.append("Safety violation: orchestration must remain simulation-only.")
        return list(dict.fromkeys(warnings))
