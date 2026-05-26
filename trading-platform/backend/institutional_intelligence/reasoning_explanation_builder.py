from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport


class ReasoningExplanationBuilder:
    """Build a factual explanation only from fields present in an orchestration report."""

    def build_detailed_explanation(self, orchestration_report: InstitutionalOrchestrationReport) -> str:
        state = orchestration_report.system_state
        lines: list[str] = []
        if state:
            lines.append(
                f"Market state is {state.market_state}; institutional bias is {state.institutional_bias}; "
                f"final state is {state.final_state}."
            )
        if orchestration_report.confluence_context:
            score = orchestration_report.confluence_context.confluence_score
            lines.append(
                f"Confluence quality is {score.setup_quality} with overall score {score.overall_score:.1f} "
                f"and dominant direction {score.dominant_direction}."
            )
        if orchestration_report.alignment_context:
            alignment = orchestration_report.alignment_context
            lines.append(
                f"Multi-timeframe alignment is {alignment.alignment_quality}, resolving to "
                f"{alignment.overall_direction} with confidence {alignment.confidence:.1f}."
            )
        if orchestration_report.sweep_context:
            sweep = orchestration_report.sweep_context
            lines.append(
                f"Liquidity evidence records {len(sweep.bullish_sweeps)} bullish and "
                f"{len(sweep.bearish_sweeps)} bearish sweep(s)."
            )
        zones: list[str] = []
        if orchestration_report.fvg_context:
            zones.append(f"{len(orchestration_report.fvg_context.fresh_fvgs)} fresh FVG(s)")
        if orchestration_report.order_block_context:
            zones.append(f"{len(orchestration_report.order_block_context.fresh_order_blocks)} fresh order block(s)")
        if orchestration_report.breaker_context:
            zones.append(f"{len(orchestration_report.breaker_context.fresh_breakers)} fresh breaker(s)")
        if zones:
            lines.append("Institutional zones include " + ", ".join(zones) + ".")
        if orchestration_report.structure_shift_context:
            structure = orchestration_report.structure_shift_context
            lines.append(
                f"Structure detection records {len(structure.bos_events)} BOS, {len(structure.choch_events)} CHOCH, "
                f"and {len(structure.mss_events)} MSS event(s)."
            )
        if orchestration_report.session_context:
            session = orchestration_report.session_context
            lines.append(
                f"Session timing is {session.trade_timing_readiness} with quality score "
                f"{session.session_quality_score:.1f}."
            )
        if state:
            lines.append(
                f"Setup state is {state.setup_state}; simulation state is {state.simulation_state}; "
                f"risk state is {state.risk_state}."
            )
        return " ".join(lines) or "No institutional evidence is available for detailed reasoning."
