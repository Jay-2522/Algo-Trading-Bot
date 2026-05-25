import asyncio

from backend.trading_loop.loop_logger import LoopLogger
from backend.trading_loop.loop_models import LoopControlResponse, LoopRunResult
from backend.trading_loop.loop_runner import LoopRunner
from backend.trading_loop.loop_state import LoopState


class LoopScheduler:
    """Own one cancellable, rate-limited asyncio monitoring task."""

    def __init__(
        self,
        state: LoopState,
        runner: LoopRunner,
        loop_logger: LoopLogger,
    ) -> None:
        self.state = state
        self.runner = runner
        self.loop_logger = loop_logger
        self._task: asyncio.Task | None = None

    async def start(self) -> LoopControlResponse:
        if self._task is not None and not self._task.done():
            return self._response(False, "START", "Background loop is already running.")
        if not self.state.start():
            return self._response(False, "START", "Background loop is already running.")
        self._task = asyncio.create_task(self.run_loop())
        self.loop_logger.log_event("LOOP_STARTED", "Background monitoring loop started.")
        return self._response(True, "START", "Background monitoring loop started.")

    async def stop(self) -> LoopControlResponse:
        if not self.state.stop():
            return self._response(False, "STOP", "Background loop is not running.")
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.loop_logger.log_event("LOOP_STOPPED", "Background monitoring loop stopped.")
        return self._response(True, "STOP", "Background monitoring loop stopped.")

    async def pause(self) -> LoopControlResponse:
        if not self.state.pause():
            return self._response(False, "PAUSE", "Background loop is not running or is already paused.")
        self.loop_logger.log_event("LOOP_PAUSED", "Background monitoring loop paused.")
        return self._response(True, "PAUSE", "Background monitoring loop paused.")

    async def resume(self) -> LoopControlResponse:
        if not self.state.resume():
            return self._response(False, "RESUME", "Background loop is not paused.")
        self.loop_logger.log_event("LOOP_RESUMED", "Background monitoring loop resumed.")
        return self._response(True, "RESUME", "Background monitoring loop resumed.")

    async def run_loop(self) -> None:
        try:
            while self.state.is_running():
                await asyncio.sleep(self.state.config.interval_seconds)
                if self.state.is_running() and not self.state.is_paused():
                    symbols = self.state.config.monitored_symbols[: self.state.config.max_symbols_per_cycle]
                    results = await self.runner.run_once(symbols)
                    self._record_results(results, "BACKGROUND_CYCLE")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.state.record_failure(exc)
            self.loop_logger.log_event(
                "LOOP_FAILURE",
                "Background monitoring loop cycle failed safely.",
                {"error": str(exc)},
            )

    def record_manual_results(self, results: list[LoopRunResult]) -> None:
        self._record_results(results, "MANUAL_CYCLE")

    def _record_results(self, results: list[LoopRunResult], event_type: str) -> None:
        for result in results:
            self.state.record_run(result)
        self.loop_logger.log_event(
            event_type,
            "Simulation-only orchestration cycle completed.",
            {
                "symbols": [result.symbol for result in results],
                "successful_runs": sum(1 for result in results if result.success),
                "failed_runs": sum(1 for result in results if not result.success),
            },
        )

    def _response(self, success: bool, action: str, message: str) -> LoopControlResponse:
        return LoopControlResponse(
            success=success,
            action=action,
            message=message,
            status=self.state.get_status(),
        )
