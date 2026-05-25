from backend.trading_loop.loop_config import get_default_loop_config
from backend.trading_loop.loop_logger import LoopLogger
from backend.trading_loop.loop_models import LoopConfig, LoopControlResponse, LoopRunResult, LoopStatus
from backend.trading_loop.loop_runner import LoopRunner
from backend.trading_loop.loop_scheduler import LoopScheduler
from backend.trading_loop.loop_state import LoopState


class TradingLoopService:
    """API facade for controlled, simulation-only orchestration cycles."""

    def __init__(
        self,
        state: LoopState | None = None,
        runner: LoopRunner | None = None,
        loop_logger: LoopLogger | None = None,
    ) -> None:
        self.state = state or LoopState(get_default_loop_config())
        self.runner = runner or LoopRunner()
        self.loop_logger = loop_logger or LoopLogger()
        self.scheduler = LoopScheduler(self.state, self.runner, self.loop_logger)

    def get_status(self) -> LoopStatus:
        return self.state.get_status()

    async def start_loop(self) -> LoopControlResponse:
        return await self.scheduler.start()

    async def stop_loop(self) -> LoopControlResponse:
        return await self.scheduler.stop()

    async def pause_loop(self) -> LoopControlResponse:
        return await self.scheduler.pause()

    async def resume_loop(self) -> LoopControlResponse:
        return await self.scheduler.resume()

    async def run_once(self) -> list[LoopRunResult]:
        symbols = self.state.config.monitored_symbols[: self.state.config.max_symbols_per_cycle]
        results = await self.runner.run_once(symbols)
        self.scheduler.record_manual_results(results)
        return results

    def add_symbol(self, symbol: str) -> list[str]:
        return self.state.add_symbol(symbol)

    def remove_symbol(self, symbol: str) -> list[str]:
        return self.state.remove_symbol(symbol)

    def get_config(self) -> LoopConfig:
        return self.state.config.model_copy(deep=True)
