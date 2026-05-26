from backend.institutional_intelligence.ai_reasoning_models import MarketNarrative
from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport


class MarketNarrativeEngine:
    """Convert recorded institutional state into a concise desk-style narrative."""

    ACTIONS = {
        "READY_FOR_SIMULATION": "READY_FOR_SIMULATION",
        "WAITING_FOR_CONFIRMATION": "WAIT",
        "BLOCKED": "AVOID",
        "ERROR_SAFE_MODE": "AVOID",
        "MANAGING_POSITION": "MANAGE_POSITION",
        "NO_TRADE": "MONITOR",
    }

    def build_narrative(self, orchestration_report: InstitutionalOrchestrationReport) -> MarketNarrative:
        state = orchestration_report.system_state
        final = state.final_state if state else "NO_TRADE"
        bias = state.institutional_bias if state else "UNCLEAR"
        market_state = state.market_state if state else "UNCLEAR"
        setup_state = state.setup_state if state else "NO_SETUP"
        simulation_state = state.simulation_state if state else "NO_VALID_SETUP"
        action = self.ACTIONS[final]
        headline = self._headline(orchestration_report.symbol, bias, market_state, final)
        drivers = self._drivers(orchestration_report)
        risks = list(dict.fromkeys(orchestration_report.warnings + self._risks(orchestration_report)))
        summary = f"{headline} Recommended desk action: {action.replace('_', ' ').lower()} in simulation-only mode."
        return MarketNarrative(
            symbol=orchestration_report.symbol,
            timeframe=orchestration_report.timeframe,
            headline=headline,
            summary=summary,
            institutional_bias=bias,
            market_state=market_state,
            setup_state=setup_state,
            simulation_state=simulation_state,
            key_drivers=drivers,
            risks=risks,
            recommended_action=action,
            confidence=state.confidence if state else 0.0,
        )

    def _headline(self, symbol: str, bias: str, market_state: str, final: str) -> str:
        if final == "MANAGING_POSITION":
            return f"{symbol} position management mode is active; focus shifts from entry to protection."
        if final == "READY_FOR_SIMULATION":
            return f"{symbol} {bias.lower()} institutional conditions qualify for simulation review."
        if final == "BLOCKED":
            return f"{symbol} {bias.lower()} conditions are present, but institutional simulation is blocked."
        if final == "ERROR_SAFE_MODE":
            return f"{symbol} institutional analysis is in safe mode after incomplete pipeline evidence."
        if final == "WAITING_FOR_CONFIRMATION":
            return f"{symbol} {market_state.lower()} market requires confirmation before simulation."
        return f"{symbol} has no approved institutional simulation setup at present."

    def _drivers(self, report: InstitutionalOrchestrationReport) -> list[str]:
        drivers: list[str] = []
        if report.alignment_context:
            drivers.append(
                f"Multi-timeframe alignment is {report.alignment_context.alignment_quality} with "
                f"{report.alignment_context.overall_direction} direction."
            )
        if report.sweep_context and report.sweep_context.sweeps:
            drivers.append(
                f"Liquidity record includes {len(report.sweep_context.bullish_sweeps)} bullish and "
                f"{len(report.sweep_context.bearish_sweeps)} bearish sweep(s)."
            )
        if report.confluence_context:
            score = report.confluence_context.confluence_score
            drivers.append(f"Confluence is classified {score.setup_quality} at {score.overall_score:.1f}.")
        if report.session_context:
            drivers.append(f"Session timing status is {report.session_context.trade_timing_readiness}.")
        if report.position_management_context and report.position_management_context.active_positions:
            drivers.append("An active paper position is under institutional management.")
        return drivers or ["No high-confidence institutional driver is available in the current report."]

    def _risks(self, report: InstitutionalOrchestrationReport) -> list[str]:
        risks: list[str] = []
        if report.alignment_context and report.alignment_context.conflicts:
            risks.append("Directional conflict is present across analyzed timeframes.")
        if report.session_context and report.session_context.trade_timing_readiness in {
            "AVOID_LOW_LIQUIDITY",
            "AVOID_NEWS_WINDOW",
        }:
            risks.append("Session conditions restrict simulation readiness.")
        if report.setup_validation_context and not report.setup_validation_context.simulation_eligible:
            risks.append("No validated setup is currently eligible for simulation.")
        return risks
