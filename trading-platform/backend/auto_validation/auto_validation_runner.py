from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Awaitable, Callable

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
        self._support_stop_requested = False
        self._support_tasks: dict[str, asyncio.Task[None]] = {}
        self._watchdog_task: asyncio.Task[None] | None = None
        self._watchdog_restart_count = 0
        self._support_state: dict[str, dict[str, Any]] = {
            name: {
                "alive": False,
                "last_tick_at": None,
                "last_duration_ms": None,
                "last_error": "",
                "restart_count": 0,
            }
            for name in ("mt5_sync", "scan", "exit", "journal", "bot_decision")
        }
        self._publish_state()

    def status(self) -> dict[str, Any]:
        support = self.support_status()
        return {
            "runner_active": self.is_active(),
            "runner_last_tick_at": self._last_tick_at,
            "runner_next_tick_at": self._next_tick_at,
            "runner_interval_seconds": self._interval_seconds,
            "run_once_in_progress": self._run_once_in_progress,
            "last_run_once_duration_ms": self._last_duration_ms,
            "last_runner_error": self._last_error,
            **support,
        }

    def support_status(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "watchdog_restart_count": self._watchdog_restart_count,
            "last_loop_error": self._last_error,
        }
        for name, state in self._support_state.items():
            task = self._support_tasks.get(name)
            last_tick = state.get("last_tick_at")
            age = self._age_seconds(last_tick, now)
            payload[f"{name}_loop_alive"] = bool(task and not task.done() and state.get("alive"))
            payload[f"last_{name}_age_seconds"] = age
            payload[f"{name}_last_tick_at"] = last_tick
            payload[f"{name}_last_duration_ms"] = state.get("last_duration_ms")
            payload[f"{name}_last_error"] = state.get("last_error") or ""
            payload[f"{name}_restart_count"] = state.get("restart_count") or 0
            if state.get("last_error"):
                payload["last_loop_error"] = state.get("last_error")
        payload["reason_loop_alive"] = bool(payload.get("bot_decision_loop_alive"))
        payload["last_reason_loop_age_seconds"] = payload.get("last_bot_decision_age_seconds")
        return payload

    def is_active(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        self.start_support_loops()
        if not self.service.should_auto_start_runner():
            self.stop(stop_support=False)
            return
        if self.is_active():
            self._publish_state()
            return
        self._stop_requested = False
        self._task = asyncio.create_task(self._loop())
        self._publish_state()

    def start_if_running(self) -> None:
        if self.service.should_auto_start_runner():
            mark_resume = getattr(self.service, "mark_backend_startup_resume", None)
            if callable(mark_resume):
                mark_resume()
            self.start()
        else:
            self._publish_state()

    def stop(self, stop_support: bool = False) -> None:
        self._stop_requested = True
        task = self._task
        self._task = None
        self._next_tick_at = None
        if task is not None and not task.done():
            task.cancel()
        if stop_support:
            self._support_stop_requested = True
            for support_task in list(self._support_tasks.values()):
                if not support_task.done():
                    support_task.cancel()
            self._support_tasks.clear()
            if self._watchdog_task is not None and not self._watchdog_task.done():
                self._watchdog_task.cancel()
            self._watchdog_task = None
        self._publish_state()

    async def shutdown(self) -> None:
        task = self._task
        self.stop(stop_support=True)
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

    def start_support_loops(self) -> None:
        self._support_stop_requested = False
        specs: dict[str, tuple[float, float, Callable[[], Awaitable[None]]]] = {
            "mt5_sync": (3.0, 12.0, self._mt5_sync_tick),
            "scan": (3.0, 10.0, self._scan_tick),
            "exit": (5.0, 8.0, self._exit_tick),
            "journal": (4.0, 10.0, self._journal_tick),
            "bot_decision": (3.0, 4.0, self._bot_decision_tick),
        }
        for name, (interval, timeout, callback) in specs.items():
            task = self._support_tasks.get(name)
            if task is None or task.done():
                self._support_tasks[name] = asyncio.create_task(self._support_loop(name, interval, timeout, callback))
        if self._watchdog_task is None or self._watchdog_task.done():
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())
        self._publish_state()

    async def _support_loop(self, name: str, interval: float, timeout: float, callback: Callable[[], Awaitable[None]]) -> None:
        try:
            while not self._support_stop_requested:
                should_run = self.service.should_run_support_loop(name)
                if should_run:
                    started = perf_counter()
                    self._support_state[name]["alive"] = True
                    self._support_state[name]["last_tick_at"] = self._timestamp()
                    self.service.log_loop_event(f"{name.upper()}_LOOP_TICK", {"loop": name})
                    try:
                        await asyncio.wait_for(callback(), timeout=timeout)
                        self._support_state[name]["last_error"] = ""
                    except asyncio.TimeoutError:
                        message = f"{name} loop exceeded {int(timeout * 1000)} ms"
                        self._support_state[name]["last_error"] = message
                        self.service.log_loop_event("LOOP_ERROR", {"loop": name, "error": message})
                    except Exception as exc:  # pragma: no cover - defensive background loop isolation.
                        message = str(exc)
                        self._support_state[name]["last_error"] = message
                        self.service.log_loop_event("LOOP_ERROR", {"loop": name, "error": message})
                    finally:
                        self._support_state[name]["last_duration_ms"] = int((perf_counter() - started) * 1000)
                        self._publish_state()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        finally:
            self._support_state[name]["alive"] = False
            self._publish_state()

    async def _mt5_sync_tick(self) -> None:
        await asyncio.to_thread(self.service.mt5_sync_loop_tick)

    async def _exit_tick(self) -> None:
        await asyncio.to_thread(self.service.exit_loop_tick)

    async def _journal_tick(self) -> None:
        await asyncio.to_thread(self.service.journal_lifecycle_loop_tick)

    async def _bot_decision_tick(self) -> None:
        await asyncio.to_thread(self.service.bot_decision_loop_tick)

    async def _scan_tick(self) -> None:
        symbols = await asyncio.to_thread(self.service.scan_loop_symbols)
        for symbol in symbols:
            try:
                await asyncio.wait_for(asyncio.to_thread(self.service.scan_loop_tick_symbol, symbol), timeout=8.0)
            except asyncio.TimeoutError:
                self.service.record_scan_timeout_warning(symbol, 8000)
            except Exception as exc:
                self.service.log_loop_event("LOOP_ERROR", {"loop": "scan", "symbol": symbol, "error": str(exc)})

    async def _watchdog_loop(self) -> None:
        try:
            while not self._support_stop_requested:
                await asyncio.sleep(5.0)
                self._watchdog_check()
        except asyncio.CancelledError:
            raise

    def _watchdog_check(self) -> None:
        now = datetime.now(timezone.utc)
        stale_thresholds = {"mt5_sync": 20, "scan": 20, "exit": 20, "journal": 20, "bot_decision": 15}
        for name, threshold in stale_thresholds.items():
            if not self.service.should_run_support_loop(name):
                continue
            task = self._support_tasks.get(name)
            age = self._age_seconds(self._support_state[name].get("last_tick_at"), now)
            stale = task is None or task.done() or age is None or age > threshold
            if not stale:
                continue
            self._watchdog_restart_count += 1
            self._support_state[name]["restart_count"] = int(self._support_state[name].get("restart_count") or 0) + 1
            self.service.log_loop_event("LOOP_STALE", {"loop": name, "age_seconds": age, "threshold_seconds": threshold})
            if task is not None and not task.done():
                task.cancel()
            specs: dict[str, tuple[float, float, Callable[[], Awaitable[None]]]] = {
                "mt5_sync": (3.0, 12.0, self._mt5_sync_tick),
                "scan": (3.0, 10.0, self._scan_tick),
                "exit": (5.0, 8.0, self._exit_tick),
                "journal": (4.0, 10.0, self._journal_tick),
                "bot_decision": (3.0, 4.0, self._bot_decision_tick),
            }
            interval, timeout, callback = specs[name]
            self._support_tasks[name] = asyncio.create_task(self._support_loop(name, interval, timeout, callback))
            self.service.log_loop_event("LOOP_RESTARTED", {"loop": name, "restart_count": self._support_state[name]["restart_count"]})
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

    def _age_seconds(self, value: Any, now: datetime) -> int | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0, int((now - parsed).total_seconds()))
        except Exception:
            return None
