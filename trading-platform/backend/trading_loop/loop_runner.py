import asyncio

from backend.orchestration.orchestrator_service import OrchestratorService
from backend.trading_loop.loop_models import LoopRunResult


class LoopRunner:
    """Execute one simulation-only orchestration evaluation per requested symbol."""

    def __init__(self, orchestrator: OrchestratorService | None = None) -> None:
        self.orchestrator = orchestrator or OrchestratorService()

    async def run_once(self, symbols: list[str]) -> list[LoopRunResult]:
        results: list[LoopRunResult] = []
        for symbol in symbols:
            results.append(await self.run_symbol(symbol))
        return results

    async def run_symbol(self, symbol: str) -> LoopRunResult:
        normalized = symbol.strip().upper() if symbol else ""
        if not normalized:
            return LoopRunResult(symbol="", success=False, errors=["Symbol cannot be empty."])
        try:
            pipeline = await asyncio.to_thread(
                self.orchestrator.run_symbol_pipeline,
                normalized,
                "M15",
            )
            return LoopRunResult(
                symbol=normalized,
                success=pipeline.success,
                decision=pipeline.decision.model_dump(mode="json"),
                errors=list(pipeline.errors),
            )
        except Exception as exc:
            return LoopRunResult(
                symbol=normalized,
                success=False,
                errors=[f"Orchestration pipeline failed safely: {exc}"],
            )
