from time import perf_counter
from typing import Any, Callable

from backend.institutional_intelligence.institutional_orchestration_models import (
    InstitutionalOrchestrationReport,
    InstitutionalPipelineStep,
)
from backend.institutional_intelligence.paper_trade_models import PaperTradeLifecycleContext
from backend.institutional_intelligence.position_management_models import InstitutionalPositionManagement


class InstitutionalPipelineRunner:
    """Run Phase 2 analysis in dependency order while isolating individual failures."""

    def __init__(self, service: Any) -> None:
        self.service = service

    def run_pipeline(
        self, symbol: str, timeframe: str, candles: list[Any] | None = None
    ) -> InstitutionalOrchestrationReport:
        source = candles or []
        values: dict[str, Any] = {}
        steps: list[InstitutionalPipelineStep] = []

        self._run(steps, values, "institutional_context", lambda: self.service.analyze_from_candles(symbol, timeframe, source))
        self._run(steps, values, "sweep_context", lambda: self.service.analyze_sweeps_from_candles(symbol, timeframe, source))
        self._run(steps, values, "fvg_context", lambda: self.service.analyze_fvgs_from_candles(symbol, timeframe, source))
        self._run(steps, values, "order_block_context", lambda: self.service.analyze_order_blocks_from_candles(symbol, timeframe, source))
        self._run(steps, values, "breaker_context", lambda: self.service.analyze_breaker_blocks_from_candles(symbol, timeframe, source))
        self._run(steps, values, "structure_shift_context", lambda: self.service.analyze_structure_shift_from_candles(symbol, timeframe, source))
        self._run(steps, values, "confluence_context", lambda: self.service.analyze_confluence_from_candles(symbol, timeframe, source))
        self._run(steps, values, "alignment_context", lambda: self.service.analyze_multi_timeframe_alignment(symbol))
        self._run(
            steps,
            values,
            "session_context",
            lambda: self.service.analyze_session_intelligence_from_candles(
                symbol, timeframe, source, alignment_context=values.get("alignment_context")
            ),
        )
        self._run(
            steps,
            values,
            "entry_model_context",
            lambda: self.service.analyze_entry_models_from_candles(
                symbol,
                timeframe,
                source,
                alignment_context=values.get("alignment_context"),
                session_context=values.get("session_context"),
            ),
        )
        self._run(
            steps,
            values,
            "setup_validation_context",
            lambda: self.service.setup_validation_context_builder.build_validation_context(
                symbol,
                timeframe,
                source,
                entry_model_context=values.get("entry_model_context"),
                confluence_context=values.get("confluence_context"),
                alignment_context=values.get("alignment_context"),
                session_context=values.get("session_context"),
                risk_context=self.service._safe_risk_status(),
            ),
        )
        self._run(
            steps,
            values,
            "simulation_decision_context",
            lambda: self.service.simulation_decision_context_builder.build_simulation_decision_context(
                symbol,
                timeframe,
                source,
                validation_context=values.get("setup_validation_context"),
                risk_status=self.service._safe_risk_status(),
                session_context=values.get("session_context"),
            ),
        )
        self._run(
            steps,
            values,
            "paper_trade_context",
            lambda: self.service.paper_trade_context_builder.build_paper_trade_context(
                symbol,
                timeframe,
                source,
                decision_context=values.get("simulation_decision_context"),
            ),
            fallback=PaperTradeLifecycleContext(
                symbol=symbol,
                timeframe=timeframe,
                lifecycle_status="BLOCKED",
                summary="Paper lifecycle step unavailable; no position was created.",
            ),
        )
        self._run(
            steps,
            values,
            "position_management_context",
            lambda: self.service.position_management_context_builder.build_position_management_context(
                symbol,
                timeframe,
                source,
                paper_context=values.get("paper_trade_context"),
                structure_context=values.get("structure_shift_context"),
                breaker_context=values.get("breaker_context"),
                session_context=values.get("session_context"),
                risk_context=self.service._safe_risk_status(),
            ),
            fallback=InstitutionalPositionManagement(
                symbol=symbol,
                timeframe=timeframe,
                management_status="NO_POSITION",
                summary="Position management step unavailable; simulation remains inactive.",
            ),
        )
        return InstitutionalOrchestrationReport(symbol=symbol, timeframe=timeframe, pipeline_steps=steps, **values)

    def _run(
        self,
        steps: list[InstitutionalPipelineStep],
        values: dict[str, Any],
        name: str,
        operation: Callable[[], Any],
        fallback: Any = None,
    ) -> None:
        started = perf_counter()
        try:
            value = operation()
            values[name] = value
            steps.append(
                InstitutionalPipelineStep(
                    step_name=name,
                    status="PASSED",
                    success=True,
                    duration_ms=round((perf_counter() - started) * 1000.0, 3),
                    summary=f"{name.replace('_', ' ').title()} completed.",
                )
            )
        except Exception as exc:
            values[name] = fallback
            steps.append(
                InstitutionalPipelineStep(
                    step_name=name,
                    status="FAILED",
                    success=False,
                    duration_ms=round((perf_counter() - started) * 1000.0, 3),
                    error=str(exc),
                    summary=f"{name.replace('_', ' ').title()} failed safely.",
                )
            )
