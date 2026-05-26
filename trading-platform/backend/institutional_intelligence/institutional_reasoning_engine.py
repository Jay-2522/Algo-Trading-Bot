from backend.institutional_intelligence.ai_reasoning_models import InstitutionalReasoningReport
from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport
from backend.institutional_intelligence.market_narrative_engine import MarketNarrativeEngine
from backend.institutional_intelligence.reasoning_explanation_builder import ReasoningExplanationBuilder
from backend.institutional_intelligence.reasoning_summary_builder import ReasoningSummaryBuilder


class InstitutionalReasoningEngine:
    """Build evidence-bounded desk commentary from the institutional orchestration report."""

    def __init__(
        self,
        narrative_engine: MarketNarrativeEngine | None = None,
        explanation_builder: ReasoningExplanationBuilder | None = None,
        summary_builder: ReasoningSummaryBuilder | None = None,
    ) -> None:
        self.narrative_engine = narrative_engine or MarketNarrativeEngine()
        self.explanation_builder = explanation_builder or ReasoningExplanationBuilder()
        self.summary_builder = summary_builder or ReasoningSummaryBuilder()

    def generate_reasoning(self, orchestration_report: InstitutionalOrchestrationReport) -> InstitutionalReasoningReport:
        narrative = self.narrative_engine.build_narrative(orchestration_report)
        bullish = self._directional_case(orchestration_report, "BULLISH")
        bearish = self._directional_case(orchestration_report, "BEARISH")
        neutral = self._neutral_case(orchestration_report)
        report = InstitutionalReasoningReport(
            symbol=orchestration_report.symbol,
            timeframe=orchestration_report.timeframe,
            narrative=narrative,
            detailed_reasoning=self.explanation_builder.build_detailed_explanation(orchestration_report),
            bullish_case=bullish,
            bearish_case=bearish,
            neutral_case=neutral,
            invalidation_notes=self._invalidation_notes(orchestration_report),
            timing_notes=self._timing_notes(orchestration_report),
            risk_notes=self._risk_notes(orchestration_report),
            confidence=narrative.confidence,
        )
        return report.model_copy(
            update={
                "executive_summary": self.summary_builder.build_executive_summary(report),
                "client_friendly_summary": self.summary_builder.build_client_friendly_summary(report),
                "dashboard_summary": self.summary_builder.build_dashboard_summary(report),
                "simulation_only": True,
                "live_execution_enabled": False,
            }
        )

    def _directional_case(self, report: InstitutionalOrchestrationReport, direction: str) -> list[str]:
        case: list[str] = []
        if report.alignment_context and report.alignment_context.overall_direction == direction:
            case.append(f"Multi-timeframe alignment supports {direction.lower()} order flow.")
        if report.sweep_context:
            sweeps = report.sweep_context.bullish_sweeps if direction == "BULLISH" else report.sweep_context.bearish_sweeps
            if sweeps:
                case.append(f"{len(sweeps)} validated {direction.lower()} liquidity sweep(s) are recorded.")
        if report.fvg_context:
            zones = report.fvg_context.bullish_fvgs if direction == "BULLISH" else report.fvg_context.bearish_fvgs
            fresh = [zone for zone in zones if zone.fresh]
            if fresh:
                case.append(f"{len(fresh)} fresh {direction.lower()} FVG(s) remain available.")
        if report.order_block_context:
            blocks = (
                report.order_block_context.bullish_order_blocks
                if direction == "BULLISH"
                else report.order_block_context.bearish_order_blocks
            )
            if any(block.fresh for block in blocks):
                case.append(f"A fresh {direction.lower()} order block is recorded.")
        if report.breaker_context:
            breakers = [block for block in report.breaker_context.breaker_blocks if block.direction == direction and block.valid]
            if breakers:
                case.append(f"A validated {direction.lower()} breaker context is recorded.")
        return case

    def _neutral_case(self, report: InstitutionalOrchestrationReport) -> list[str]:
        state = report.system_state.final_state if report.system_state else "NO_TRADE"
        notes: list[str] = []
        if state == "BLOCKED":
            notes.append("Institutional simulation is blocked by recorded timing, risk, or management conditions.")
        elif state == "NO_TRADE":
            notes.append("No setup has sufficient recorded quality for simulation approval.")
        elif state == "WAITING_FOR_CONFIRMATION":
            notes.append("The recorded setup remains conditional and awaits additional confirmation.")
        elif state == "ERROR_SAFE_MODE":
            notes.append("Incomplete pipeline evidence requires non-actionable safe mode.")
        elif state == "MANAGING_POSITION":
            notes.append("New entry reasoning is secondary while an existing paper position is managed.")
        else:
            notes.append("A setup has passed recorded controls for simulation-only review.")
        return notes

    def _invalidation_notes(self, report: InstitutionalOrchestrationReport) -> list[str]:
        notes: list[str] = []
        management = report.position_management_context
        if management:
            notes.extend(
                signal.exit_reason for signal in management.structural_exit_signals if signal.exit_required
            )
            if management.emergency_exit and management.emergency_exit.triggered:
                notes.append(management.emergency_exit.shutdown_reason)
        decision = report.simulation_decision_context.decision if report.simulation_decision_context else None
        if decision and decision.order_intent.invalidation_level is not None:
            notes.append(f"Simulation intent invalidation level is {decision.order_intent.invalidation_level:.5f}.")
        return notes or ["No explicit institutional invalidation event is recorded in the current report."]

    def _timing_notes(self, report: InstitutionalOrchestrationReport) -> list[str]:
        if not report.session_context:
            return ["Session timing context is unavailable."]
        session = report.session_context
        notes = [f"Session readiness is {session.trade_timing_readiness}."]
        if session.active_killzone.active_killzone:
            notes.append(f"Active killzone is {session.active_killzone.killzone_name}.")
        return notes

    def _risk_notes(self, report: InstitutionalOrchestrationReport) -> list[str]:
        notes = list(report.warnings)
        state = report.system_state
        if state:
            notes.append(f"Institutional risk state is {state.risk_state}.")
        notes.append("Outputs authorize simulation analysis only; broker execution is not permitted.")
        return list(dict.fromkeys(notes))
