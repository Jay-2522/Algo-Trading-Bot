from backend.market_data.validators import validate_symbol_name
from backend.trading_loop.loop_config import get_default_loop_config
from backend.trading_loop.loop_models import LoopConfig, LoopRunResult, LoopStatus, utc_timestamp


class LoopState:
    """Store scheduler lifecycle, counters, and the latest advisory result in memory."""

    def __init__(self, config: LoopConfig | None = None) -> None:
        self.config = (config or get_default_loop_config()).model_copy(deep=True)
        self._running = False
        self._paused = False
        self._total_runs = 0
        self._failed_runs = 0
        self._last_run_at: str | None = None
        self._last_decision: dict | None = None

    def start(self) -> bool:
        if self._running:
            return False
        self._running = True
        self._paused = False
        self.config.enabled = True
        return True

    def stop(self) -> bool:
        if not self._running:
            return False
        self._running = False
        self._paused = False
        self.config.enabled = False
        return True

    def pause(self) -> bool:
        if not self._running or self._paused:
            return False
        self._paused = True
        return True

    def resume(self) -> bool:
        if not self._running or not self._paused:
            return False
        self._paused = False
        return True

    def is_running(self) -> bool:
        return self._running

    def is_paused(self) -> bool:
        return self._paused

    def add_symbol(self, symbol: str) -> list[str]:
        normalized = validate_symbol_name(symbol)
        if normalized not in self.config.monitored_symbols:
            self.config.monitored_symbols.append(normalized)
        return list(self.config.monitored_symbols)

    def remove_symbol(self, symbol: str) -> list[str]:
        normalized = validate_symbol_name(symbol)
        if normalized in self.config.monitored_symbols and len(self.config.monitored_symbols) > 1:
            self.config.monitored_symbols.remove(normalized)
        return list(self.config.monitored_symbols)

    def record_run(self, result: LoopRunResult) -> None:
        self._total_runs += 1
        if not result.success:
            self._failed_runs += 1
        self._last_run_at = result.timestamp
        self._last_decision = result.decision or {"symbol": result.symbol, "errors": result.errors}

    def record_failure(self, error: Exception | str) -> None:
        self._failed_runs += 1
        self._last_run_at = utc_timestamp()
        self._last_decision = {"status": "FAILED", "error": str(error)}

    def get_status(self) -> LoopStatus:
        if self._running and self._paused:
            status = "paused"
        elif self._running:
            status = "running"
        else:
            status = "stopped"
        return LoopStatus(
            status=status,
            running=self._running,
            paused=self._paused,
            simulation_only=self.config.simulation_only,
            live_execution_enabled=self.config.live_execution_enabled,
            monitored_symbols=list(self.config.monitored_symbols),
            interval_seconds=self.config.interval_seconds,
            total_runs=self._total_runs,
            failed_runs=self._failed_runs,
            last_run_at=self._last_run_at,
            last_decision=self._last_decision,
        )
