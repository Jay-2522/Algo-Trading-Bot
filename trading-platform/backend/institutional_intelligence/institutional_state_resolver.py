from backend.institutional_intelligence.institutional_orchestration_models import (
    InstitutionalOrchestrationReport,
    InstitutionalSystemState,
)


class InstitutionalStateResolver:
    """Resolve one conservative final system state from the complete Phase 2 report."""

    def resolve_state(self, report: InstitutionalOrchestrationReport) -> InstitutionalSystemState:
        warnings = list(report.warnings)
        position = report.position_management_context
        decision = report.simulation_decision_context.decision if report.simulation_decision_context else None
        validation = report.setup_validation_context
        session = report.session_context
        failed = [step.step_name for step in report.pipeline_steps if step.status == "FAILED"]
        risk_state = "SAFE"

        if position and position.emergency_exit and position.emergency_exit.triggered:
            risk_state = "EMERGENCY_EXIT"
            warnings.append(position.emergency_exit.shutdown_reason)
        elif session and session.trade_timing_readiness in {"AVOID_LOW_LIQUIDITY", "AVOID_NEWS_WINDOW"}:
            risk_state = "SESSION_BLOCK"
            warnings.extend(session.warnings)

        if failed:
            final = "ERROR_SAFE_MODE"
            warnings.append(f"Pipeline steps failed safely: {', '.join(failed)}.")
        elif position and (position.active_positions or position.management_status in {"ACTIVE", "MANAGING"}):
            final = "MANAGING_POSITION"
        elif position and position.management_status in {"EMERGENCY", "EXIT_REQUIRED"}:
            final = "BLOCKED"
        elif decision and decision.approved_for_simulation:
            final = "READY_FOR_SIMULATION"
        elif risk_state != "SAFE" or (decision and decision.readiness == "BLOCKED"):
            final = "BLOCKED"
        elif validation and (
            validation.execution_readiness in {"CONDITIONAL", "WAIT"} or validation.waiting_setups
        ):
            final = "WAITING_FOR_CONFIRMATION"
        else:
            final = "NO_TRADE"

        market_state = (
            report.structure_shift_context.current_structure_state
            if report.structure_shift_context is not None
            else "UNCLEAR"
        )
        bias = (
            report.alignment_context.overall_direction
            if report.alignment_context is not None
            else (
                report.institutional_context.structure_bias.bias
                if report.institutional_context is not None
                else "UNCLEAR"
            )
        )
        setup_state = (
            report.entry_model_context.overall_readiness if report.entry_model_context is not None else "NO_SETUP"
        )
        simulation_state = decision.readiness if decision is not None else "NO_VALID_SETUP"
        position_state = position.management_status if position is not None else "NO_POSITION"
        confidence_values = [
            value
            for value in [
                report.institutional_context.confidence if report.institutional_context else None,
                report.confluence_context.confluence_score.confidence if report.confluence_context else None,
                report.alignment_context.confidence if report.alignment_context else None,
                validation.confidence if validation else None,
                decision.confidence if decision else None,
            ]
            if value is not None
        ]
        confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 0.0
        return InstitutionalSystemState(
            symbol=report.symbol,
            timeframe=report.timeframe,
            market_state=market_state,
            institutional_bias=bias,
            setup_state=setup_state,
            simulation_state=simulation_state,
            position_state=position_state,
            risk_state=risk_state,
            final_state=final,
            confidence=confidence,
            warnings=list(dict.fromkeys(warnings)),
        )
