from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any

from backend.auto_validation.auto_validation_service import AutoValidationService


class AutoValidationRunner:
    """Async polling loop for the AUTO validation service."""

    def __init__(self, service: AutoValidationService, default_interval_seconds: float = 3.0, watchlist_interval_seconds: float = 2.0, reconnect_interval_seconds: float = 10.0) -> None:
        self.service = service
        self.default_interval_seconds = default_interval_seconds
        self.watchlist_interval_seconds = watchlist_interval_seconds
        self.reconnect_interval_seconds = reconnect_interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._run_once_in_progress = False
        self._stop_requested = False
        self._last_tick_at: str | None = None
        self._next_tick_at: str | None = None
        self._last_duration_ms: int | None = None
        self._last_error = ""
        self._interval_seconds = default_interval_seconds
        self._publish_state()

    def status(self) -> dict[str, Any]:
        return {
            "runner_active": self.is_active(),
            "runner_last_tick_at": self._last_tick_at,
            "runner_next_tick_at": self._next_tick_at,
            "runner_interval_seconds": self._interval_seconds,
            "run_once_in_progress": self._run_once_in_progress,
            "last_run_once_duration_ms": self._last_duration_ms,
            "last_runner_error": self._last_error,
        }

    def is_active(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if not self.service.should_auto_start_runner():
            self.stop()
            return
        if self.is_active():
            self._publish_state()
            return
        self._stop_requested = False
        self._task = asyncio.create_task(self._loop())
        self._publish_state()

    def start_if_running(self) -> None:
        if self.service.should_auto_start_runner():
            self.start()
        else:
            self._publish_state()

    def stop(self) -> None:
        self._stop_requested = True
        task = self._task
        self._task = None
        self._next_tick_at = None
        if task is not None and not task.done():
            task.cancel()
        self._publish_state()

    async def shutdown(self) -> None:
        task = self._task
        self.stop()
        if task is not None and not task.done():
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def run_tick(self) -> dict[str, Any]:
        if self._run_once_in_progress:
            self._publish_state()
            return {"status": "SKIPPED", "reason": "RUN_ONCE_IN_PROGRESS"}
        if not self.service.should_auto_start_runner():
            self.stop()
            return {"status": "STOPPED", "reason": "AUTO_VALIDATION_NOT_RUNNING"}

        self._run_once_in_progress = True
        self._last_tick_at = self._timestamp()
        self._last_error = ""
        self._publish_state()
        started = perf_counter()
        try:
            result = await asyncio.to_thread(self.service.run_once)
            return result if isinstance(result, dict) else {"status": "UNKNOWN_RESULT"}
        except Exception as exc:  # pragma: no cover - exercised by integration tests with fakes.
            self._last_error = str(exc)
            self.service.log_runner_error(self._last_error)
            return {"status": "RUNNER_ERROR", "error": self._last_error}
        finally:
            self._last_duration_ms = int((perf_counter() - started) * 1000)
            self._run_once_in_progress = False
            self._interval_seconds = self._next_interval()
            self._next_tick_at = self._future_timestamp(self._interval_seconds) if self.service.should_auto_start_runner() else None
            self._publish_state()

    async def _loop(self) -> None:
        try:
            while not self._stop_requested and self.service.should_auto_start_runner():
                await self.run_tick()
                if not self.service.should_auto_start_runner():
                    break
                await asyncio.sleep(self._interval_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._last_error = str(exc)
            self.service.log_runner_error(self._last_error)
        finally:
            self._task = None
            self._next_tick_at = None
            self._publish_state()

    def _next_interval(self) -> float:
        waiting_for_reconnect = getattr(self.service, "waiting_for_mt5_reconnect", lambda: False)
        if waiting_for_reconnect():
            return self.reconnect_interval_seconds
        return self.watchlist_interval_seconds if self.service.watched_signal_is_watchlist() else self.default_interval_seconds

    def _publish_state(self) -> None:
        self.service.update_runner_state(**self.status())

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _future_timestamp(self, seconds: float) -> str:
        return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
