from typing import Any
from uuid import uuid4

from backend.institutional_intelligence.smc_service import SMCService
from backend.replay.historical_replay_loader import HistoricalReplayLoader
from backend.replay.replay_clock import ReplayClock
from backend.replay.replay_event_logger import ReplayEventLogger
from backend.replay.replay_metrics import ReplayMetricsCalculator
from backend.replay.replay_models import ReplayRequest, ReplayRunResult, ReplayStepResult
from backend.replay.replay_window_builder import ReplayWindowBuilder


class _ReplayOfflineMarketData:
    def get_candles(self, *args, **kwargs):
        raise RuntimeError("Replay uses deterministic historical candles only.")

    def close(self):
        return None


class AdvancedHistoricalReplayEngine:
    """Replay historical windows through Phase 2 institutional analysis safely."""

    def __init__(
        self,
        loader: HistoricalReplayLoader | None = None,
        clock: ReplayClock | None = None,
        window_builder: ReplayWindowBuilder | None = None,
        metrics: ReplayMetricsCalculator | None = None,
        event_logger: ReplayEventLogger | None = None,
        smc_service: SMCService | None = None,
    ) -> None:
        self.loader = loader or HistoricalReplayLoader()
        self.clock = clock or ReplayClock()
        self.window_builder = window_builder or ReplayWindowBuilder()
        self.metrics = metrics or ReplayMetricsCalculator()
        self.event_logger = event_logger or ReplayEventLogger()
        self.smc_service = smc_service or SMCService(market_data_service=_ReplayOfflineMarketData())

    def run_replay(self, request: ReplayRequest) -> ReplayRunResult:
        replay_id = f"RPL-{uuid4().hex}"
        candles = self.loader.load_candles(
            request.symbol,
            request.timeframe,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=max(request.window_size + request.step_size * (request.max_steps or 50), request.window_size),
        )
        step_indexes = self.clock.build_steps(candles, request.window_size, request.step_size, request.max_steps)
        results: list[ReplayStepResult] = []
        for ordinal, end_index in enumerate(step_indexes):
            window = self.window_builder.build_window(candles, end_index, request.window_size)
            result = self._run_step(ordinal, window, request.symbol, request.timeframe)
            results.append(result)
            self.event_logger.log_step(result)
        return self.metrics.calculate_metrics(results, replay_id, request.symbol, request.timeframe)

    def _run_step(self, step_index: int, candles: list[Any], symbol: str, timeframe: str) -> ReplayStepResult:
        replay_time = self._timestamp(candles[-1]) if candles else None
        notes: list[str] = []
        try:
            institutional = self.smc_service.analyze_institutional_orchestration_from_candles(symbol, timeframe, candles)
            decision = self.smc_service.analyze_simulation_decision_from_candles(symbol, timeframe, candles)
            paper = self.smc_service.analyze_paper_trade_lifecycle_from_candles(
                symbol, timeframe, candles, decision_context=decision
            )
            position = self.smc_service.get_position_management_from_candles(
                symbol, timeframe, candles, paper_context=paper
            )
            action = decision.decision.action
            event_type = "SIMULATION_DECISION" if action in {"SIMULATE_BUY", "SIMULATE_SELL"} else (
                "BLOCKED" if action in {"AVOID", "NO_TRADE"} else "ANALYSIS_STEP"
            )
            latest = paper.latest_position
            return ReplayStepResult(
                step_index=step_index,
                replay_time=replay_time,
                candles_visible=len(candles),
                institutional_state={
                    "final_state": institutional.system_state.final_state if institutional.system_state else "NO_TRADE",
                    "market_state": institutional.system_state.market_state if institutional.system_state else "UNCLEAR",
                    "bias": institutional.system_state.institutional_bias if institutional.system_state else "UNCLEAR",
                },
                simulation_decision=decision.decision.model_dump(mode="json"),
                paper_trade_state={
                    "lifecycle_status": paper.lifecycle_status,
                    "candidates": len(paper.candidates),
                    "active_positions": len(paper.active_positions),
                    "closed_positions": len(paper.closed_positions),
                    "latest_outcome": latest.outcome if latest else None,
                    "latest_rr": latest.rr_result if latest else None,
                },
                position_state={
                    "management_status": position.management_status,
                    "active_positions": len(position.active_positions),
                    "latest_state": position.latest_state.state if position.latest_state else None,
                },
                event_type=event_type,
                confidence=decision.decision.confidence,
                notes=notes,
            )
        except Exception as exc:
            notes.append(f"Replay step failed safely: {exc}")
            return ReplayStepResult(
                step_index=step_index,
                replay_time=replay_time,
                candles_visible=len(candles),
                event_type="ERROR_SAFE",
                notes=notes,
            )

    def _timestamp(self, candle: Any):
        return candle.get("timestamp") if isinstance(candle, dict) else getattr(candle, "timestamp")
