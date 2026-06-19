from __future__ import annotations

from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.mt5_demo.mt5_historical_backfill_service import MT5HistoricalBackfillService
from backend.reason_panel.execution_reason_service import ExecutionReasonPanelService
from backend.validation_rounds.validation_round_archive_service import ValidationRoundArchiveService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = PROJECT_ROOT / "data" / "auto_validation" / "session_state.json"


class AutoValidationService:
    """Controlled 30-trade demo validation runner using the existing guarded sender only."""

    def __init__(
        self,
        signal_provider: Any | None = None,
        guarded_execution_service: Any | None = None,
        journal_service: Any | None = None,
        position_service: Any | None = None,
        mt5_demo_service: Any | None = None,
        history_backfill_service: Any | None = None,
        lifecycle_service: Any | None = None,
        close_sync_service: Any | None = None,
        exit_management_service: Any | None = None,
        state_path: Path | None = None,
    ) -> None:
        self.signal_provider = signal_provider
        self.guarded_execution_service = guarded_execution_service
        self.journal_service = journal_service
        self.position_service = position_service
        self.mt5_demo_service = mt5_demo_service
        self.history_backfill_service = history_backfill_service or self._provider_history_backfill_service(signal_provider) or MT5HistoricalBackfillService()
        self.lifecycle_service = lifecycle_service
        self.close_sync_service = close_sync_service
        self.exit_management_service = exit_management_service
        self.reason_panel_service = ExecutionReasonPanelService()
        self.round_archive_service = ValidationRoundArchiveService()
        self.state_path = state_path or DEFAULT_STATE_PATH
        self.config = self._default_config()
        self.session = self._empty_session()
        self.events: list[dict[str, Any]] = []
        self.runner_state = self._empty_runner_state()
        self.mt5_health_state = self._empty_mt5_health_state()
        self._tick_cache: dict[str, dict[str, Any]] = {}
        self._confidence_timeline: dict[str, list[dict[str, Any]]] = {}
        self._last_hash_change_audit: dict[str, Any] | None = None
        self._last_sender_rejection: dict[str, Any] | None = None
        self._last_duplicate_check: dict[str, Any] | None = None
        self._open_position_sync_diagnostics: dict[str, Any] = self._empty_open_position_sync_diagnostics()
        self._lifecycle_sync_diagnostics: dict[str, Any] = self._empty_lifecycle_sync_diagnostics()
        self._exit_management_diagnostics: dict[str, Any] = self._empty_exit_management_diagnostics()
        self._history_warmup_diagnostics: dict[str, Any] = self._empty_history_warmup_diagnostics()
        self._execution_timelines: list[dict[str, Any]] = []
        self._validation_close_reports: list[dict[str, Any]] = []
        self._reported_close_keys: set[str] = set()
        self._startup_session_diagnostics: dict[str, Any] = {
            "active_session_id": "",
            "recovered_session_id": "",
            "dashboard_session_id": "",
            "startup_recovery_action": "NOT_LOADED",
            "startup_recovery_reason": "",
            "timestamp": None,
        }
        self._seen_signal_hashes: set[str] = set()
        self._sent_signal_keys: set[str] = set()
        self._last_trade_time: datetime | None = None
        self._last_execution_decision: dict[str, Any] | None = None
        self._current_signal_watched: dict[str, Any] | None = None
        self._decision_traces: list[dict[str, Any]] = []
        self._load_state()
        self._apply_balanced_round3_config()
        self._sync_round_archive()

    def status(self) -> dict[str, Any]:
        self._apply_balanced_round3_config()
        self._sync_lifecycle_services(manual=False)
        self._maybe_advance_all_adaptive_strategy_levels()
        self._refresh_session_metrics()
        self._maybe_clear_stale_risk_halt()
        self._clear_disallowed_watched_signal()
        recovery = self._recovery_status()
        return {
            "status": "READY",
            "mode": self.session["status"],
            **recovery,
            "config": dict(self.config),
            "session": dict(self.session),
            "current_signal_watched": copy.deepcopy(self._current_signal_watched),
            "last_execution_decision": copy.deepcopy(self._last_execution_decision),
            "latest_decision_trace": copy.deepcopy(self._decision_traces[-1]) if self._decision_traces else copy.deepcopy(self.session.get("latest_decision_trace")),
            "decision_traces": copy.deepcopy(self._decision_traces[-50:] or self.session.get("decision_traces", [])[-50:]),
            "blocked_reasons": self._last_execution_decision.get("blockers", []) if isinstance(self._last_execution_decision, dict) else [],
            "next_eligible_time": self._next_eligible_time(),
            "events": self.events[-50:],
            "mt5_health": copy.deepcopy(self.mt5_health_state),
            "history_warmup": copy.deepcopy(self._history_warmup_diagnostics),
            "history_ready": bool(self._history_warmup_diagnostics.get("history_ready")),
            "risk_halt": copy.deepcopy(self.session.get("risk_halt_diagnostics", self._risk_halt_diagnostics())),
            "active_session_id": self.session.get("session_id", ""),
            "dashboard_session_id": self.session.get("session_id", ""),
            "active_round_diagnostics": copy.deepcopy(self.session.get("active_round_diagnostics", {})),
            "recovered_session_id": "",
            "startup_session_diagnostics": copy.deepcopy(self._startup_session_diagnostics),
            "last_hash_change_audit": copy.deepcopy(self._last_hash_change_audit),
            "last_sender_rejection": copy.deepcopy(self._last_sender_rejection),
            "last_duplicate_check": copy.deepcopy(self._last_duplicate_check),
            "open_position_sync": copy.deepcopy(self._open_position_sync_diagnostics),
            "lifecycle_sync": copy.deepcopy(self._lifecycle_sync_diagnostics),
            "exit_management": copy.deepcopy(self._exit_management_diagnostics),
            "latest_validation_close_report": copy.deepcopy(self._validation_close_reports[-1]) if self._validation_close_reports else None,
            "validation_close_reports": copy.deepcopy(self._validation_close_reports[-30:]),
            "post_sender_execution_summary": self.post_sender_execution_summary(),
            "execution_timelines": copy.deepcopy(self._execution_timelines[-100:]),
            "confidence_timeline": copy.deepcopy(self._confidence_timeline),
            **self.runner_state,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def read_only_scan(self) -> dict[str, Any]:
        """Evaluate the current allowed symbols without sending orders or resuming validation."""
        self._apply_balanced_round3_config()
        mt5_health = self._mt5_health_check()
        self._history_warmup_diagnostics = self._warmup_history_before_validation()
        self.session["history_ready"] = bool(self._history_warmup_diagnostics.get("history_ready"))
        self.session["history_status"] = str(self._history_warmup_diagnostics.get("status") or "NOT_STARTED")
        signals = [self._normalize_demo_collection_signal(signal) for signal in self._allowed_signals(self._load_signals())]
        checked = [self._checked_symbol_result(signal) for signal in signals]
        best = self._best_candidate(checked)
        qualifies = bool(best and best.get("ready_for_execution"))
        reason = "Current market qualifies for Balanced Round 3, but no order was sent because this was a read-only scan." if qualifies else self._no_qualified_signal_reason(checked)
        decision = self._decision(
            "READ_ONLY_SCAN",
            [] if qualifies else ["NO_READY_APPROVED_SIGNAL"],
            extra={
                **self._scan_context(checked, best),
                "decision_reason": reason,
                "final_decision_reason": reason,
                "read_only": True,
            },
        )
        self._record_decision_traces(checked, decision)
        self._log("READ_ONLY_SCAN", {"market_qualifies": qualifies, "reason": reason, "best_candidate": best})
        self._save_state()
        return {
            "status": "READ_ONLY_SCAN_COMPLETE",
            "market_qualifies": qualifies,
            "active_session_id": self.session.get("session_id"),
            "adaptive_level": self._current_adaptive_strategy_level(),
            "symbol_adaptive_state": copy.deepcopy(self.session.get("symbol_adaptive_state", {})),
            "strategy_model": self.config.get("round3_strategy_model"),
            "mt5_health": copy.deepcopy(mt5_health),
            "history_warmup": copy.deepcopy(self._history_warmup_diagnostics),
            "best_candidate": copy.deepcopy(best),
            "checked_symbols": copy.deepcopy(checked),
            "reason": reason,
            "timestamp": self._timestamp(),
        }

    def start(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        explicit_reset = payload.get("confirm_fresh_start") is True or payload.get("force_new_round") is True
        self._refresh_session_metrics()
        active_statuses = {"RUNNING", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC", "PAUSED", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"}
        existing_closed = int(self.session.get("current_closed_trades") or self.session.get("current_session_closed") or 0)
        existing_open = int(self.session.get("current_open_trades") or self.session.get("current_session_open") or 0)
        existing_session_id = str(self.session.get("session_id") or "")
        if not explicit_reset and existing_session_id and self.session.get("status") in active_statuses:
            if existing_closed > 0 or existing_open > 0 or self._has_current_user_session():
                status = self.status()
                status["status"] = "SESSION_ALREADY_STARTED"
                status["message"] = "Round 3 validation is already started. Use Resume Validation to continue the existing session."
                status["start_disabled"] = True
                self._log(
                    "START_BLOCKED_EXISTING_SESSION",
                    {
                        "session_id": existing_session_id,
                        "status": self.session.get("status"),
                        "closed_trades": existing_closed,
                        "open_trades": existing_open,
                    },
                )
                self._save_state()
                return status
        if self._has_recoverable_progress() and not explicit_reset:
            self._log(
                "FRESH_START_CONFIRMATION_REQUIRED",
                {
                    "recovered_session_id": self.session.get("session_id"),
                    "recovered_closed_trades": self.session.get("current_closed_trades", 0),
                    "recovered_open_trades": self.session.get("current_open_trades", 0),
                },
            )
            status = self.status()
            status["status"] = "FRESH_START_CONFIRMATION_REQUIRED"
            status["message"] = "Recoverable validation progress exists. Confirm fresh start to reset it."
            return status
        self.config = {**self.config, **self._safe_config(payload)}
        self.config["auto_validation_enabled"] = True
        started_at = self._timestamp()
        self.session = {
            **self._empty_session(),
            "session_id": f"auto-validation-{uuid4()}",
            "started_at": started_at,
            "session_start_time": started_at,
            "last_trade_activity_time": started_at,
            "adaptive_level_activation_time": started_at,
            "status": "RUNNING",
            "target_closed_trades": int(self.config["target_closed_trades"]),
            "target_validation_trades": int(self.config["target_validation_trades"]),
            "session_started_by": str(payload.get("session_started_by") or "user_click"),
            "round_label": str(payload.get("round_label") or ""),
            "session_note": str(payload.get("session_note") or ""),
            "client_dashboard_scope": str(payload.get("client_dashboard_scope") or "CURRENT_SESSION_ONLY"),
        }
        self._ensure_adaptive_strategy_state()
        round_snapshot = self.round_archive_service.start_round(self.session, self.config)
        if round_snapshot:
            self.session["round_number"] = int(round_snapshot.get("round_number") or 0)
            self.session["round_label"] = str(round_snapshot.get("round_label") or self.session.get("round_label") or "")
        self._startup_session_diagnostics = {
            "active_session_id": self.session["session_id"],
            "recovered_session_id": "",
            "dashboard_session_id": self.session["session_id"],
            "startup_recovery_action": "FRESH_SESSION_STARTED",
            "startup_recovery_reason": "explicit_fresh_start" if explicit_reset else "start_validation",
            "timestamp": started_at,
        }
        self._seen_signal_hashes = set()
        self._sent_signal_keys = set()
        self._execution_timelines = []
        self._validation_close_reports = []
        self._reported_close_keys = set()
        self.events = []
        self._confidence_timeline = {}
        self._open_position_sync_diagnostics = self._empty_open_position_sync_diagnostics()
        self._last_trade_time = None
        self._last_execution_decision = None
        self._current_signal_watched = None
        self._last_duplicate_check = None
        self._last_hash_change_audit = None
        self._last_sender_rejection = None
        self._decision_traces = []
        self._history_warmup_diagnostics = self._warmup_history_before_validation()
        self._apply_history_warmup_state()
        self._log(
            "SESSION_STARTED",
            {
                "session_id": self.session["session_id"],
                "resumed_session_id": "",
                "closed_trade_count": 0,
                "open_position_count": 0,
                "new_session_created": True,
                "history_ready": self._history_warmup_diagnostics.get("history_ready"),
            },
        )
        self._save_state()
        return self.status()

    def pause(self) -> dict[str, Any]:
        if self.session["status"] in {"RUNNING", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC"}:
            self.session["status"] = "PAUSED"
            self._log("SESSION_PAUSED")
            self._save_state()
        return self.status()

    def resume(self) -> dict[str, Any]:
        if self.session["status"] == "HALTED_RISK":
            self.session["risk_halt_diagnostics"] = self._risk_halt_diagnostics()
            self._persist_risk_halt_event()
            self._save_state()
            return self.status()
        if self.session["status"] in {"PAUSED", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"}:
            self.session["status"] = "RUNNING"
            self.config["auto_validation_enabled"] = True
            self._ensure_adaptive_strategy_state()
            self._history_warmup_diagnostics = self._warmup_history_before_validation()
            self._apply_history_warmup_state()
            self._log("SESSION_RESUMED")
            self._save_state()
        return self.status()

    def stop(self, reason: str = "Stopped manually.") -> dict[str, Any]:
        if self.session["status"] in {"RUNNING", "PAUSED", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"}:
            self.session["status"] = "STOPPED"
            self.session["stopped_at"] = self._timestamp()
            self.session["reason_stopped"] = reason
            self.config["auto_validation_enabled"] = False
            self._log("SESSION_STOPPED", {"reason": reason})
            self._save_state()
        return self.status()

    def emergency_stop(self) -> dict[str, Any]:
        return self._halt("EMERGENCY_STOP")

    def trades(self) -> list[dict[str, Any]]:
        session_id = self.session.get("session_id")
        if not session_id or self.journal_service is None:
            return []
        return [trade for trade in self.journal_service.list_trades(limit=100000) if trade.get("validation_session_id") == session_id]

    def _resume_incomplete_validation_session(self, payload: dict[str, Any] | None = None, trigger: str = "backend_startup", activate: bool = False) -> dict[str, Any] | None:
        candidate = self._latest_incomplete_validation_session()
        if candidate is None:
            self._log_recovery_decision("", 0, 0, True, trigger, "no_incomplete_session")
            return None
        target = int((payload or {}).get("target_validation_trades") or (payload or {}).get("target_closed_trades") or self.config.get("target_validation_trades") or self.config.get("target_closed_trades") or 30)
        session_id = str(candidate.get("session_id") or "")
        if not session_id:
            self._log_recovery_decision("", 0, 0, True, trigger, "missing_session_id")
            return None
        current_session_id = str(self.session.get("session_id") or "")
        if trigger == "backend_startup" and current_session_id and current_session_id != session_id:
            current_started = self._parse_time(self.session.get("started_at") or self.session.get("session_start_time"))
            candidate_latest = self._parse_time(candidate.get("latest_trade_time") or candidate.get("started_at"))
            current_closed = int(self.session.get("current_closed_trades") or self.session.get("current_session_closed") or 0)
            current_open = int(self.session.get("current_open_trades") or self.session.get("current_session_open_trades") or 0)
            if current_started and candidate_latest and current_started >= candidate_latest and current_closed == 0 and current_open == 0:
                self._log_recovery_decision(session_id, int(candidate.get("closed_count") or 0), int(candidate.get("open_count") or 0), True, trigger, "skipped_older_archived_session")
                return None
        if str(self.session.get("session_id") or "") == session_id and self._has_current_user_session():
            if activate:
                self.session["status"] = "RUNNING"
                self.session["paused_reason"] = ""
                self.session["reason_stopped"] = ""
                self.config["auto_validation_enabled"] = True
                self._history_warmup_diagnostics = self._warmup_history_before_validation()
                self._apply_history_warmup_state()
            self._refresh_session_metrics()
            self._log_recovery_decision(session_id, int(candidate.get("closed_count") or 0), int(candidate.get("open_count") or 0), False, trigger, "current_session_already_active")
            self._save_state()
            return dict(candidate)

        self.config = {**self.config, **self._safe_config(payload or {})}
        self.config["auto_validation_enabled"] = activate
        started_at = str(candidate.get("started_at") or self.session.get("started_at") or self._timestamp())
        self.session = {
            **self._empty_session(),
            **self.session,
            "session_id": session_id,
            "started_at": started_at,
            "session_start_time": str(candidate.get("session_start_time") or started_at),
            "status": "RUNNING" if activate else "PAUSED_REQUIRES_USER_RESUME",
            "target_closed_trades": target,
            "target_validation_trades": target,
            "session_started_by": "user_click",
            "round_label": str((payload or {}).get("round_label") or self.session.get("round_label") or "RESUMED_VALIDATION"),
            "session_note": str((payload or {}).get("session_note") or self.session.get("session_note") or "Resumed incomplete validation session from trade journal."),
            "client_dashboard_scope": str((payload or {}).get("client_dashboard_scope") or self.session.get("client_dashboard_scope") or "CURRENT_SESSION_ONLY"),
            "paused_reason": "" if activate else "RECOVERED_FROM_TRADE_JOURNAL_REQUIRES_START",
            "reason_stopped": "" if activate else "RECOVERED_FROM_TRADE_JOURNAL_REQUIRES_START",
        }
        self._refresh_session_metrics()
        if activate:
            self._history_warmup_diagnostics = self._warmup_history_before_validation()
            self._apply_history_warmup_state()
        self._log_recovery_decision(session_id, int(self.session.get("current_closed_trades") or 0), int(self.session.get("current_open_trades") or 0), False, trigger, "resumed_incomplete_session")
        self._save_state()
        return dict(candidate)

    def summary(self) -> dict[str, Any]:
        self._sync_lifecycle_services(manual=False)
        self._refresh_session_metrics()
        return dict(self.session)

    def sync_lifecycle(self) -> dict[str, Any]:
        result = self._sync_lifecycle_services(manual=True)
        self._refresh_session_metrics()
        self._save_state()
        return {
            "status": "SYNCED",
            "message": "AUTO validation lifecycle synchronized.",
            "lifecycle_sync": copy.deepcopy(result),
            "session": dict(self.session),
            "open_position_sync": copy.deepcopy(self._open_position_sync_diagnostics),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def run_exit_management(self) -> dict[str, Any]:
        result = self._run_exit_management(manual=True)
        self._refresh_session_metrics()
        self._save_state()
        return {
            "status": result.get("status", "READY"),
            "message": result.get("message", "Exit management evaluated."),
            "exit_management": copy.deepcopy(result),
            "session": dict(self.session),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def post_sender_execution_summary(self) -> dict[str, Any]:
        return {
            "WRAPPER_SUBMITTED": int(self.session.get("wrapper_submitted") or 0),
            "APPROVAL_WORKFLOW_PASSED": int(self.session.get("approval_workflow_passed") or 0),
            "SENT": int(self.session.get("signals_sent_to_sender") or 0),
            "GUARDED_SENDER_ATTEMPTED": int(self.session.get("guarded_sender_attempted") or self.session.get("signals_sent_to_sender") or 0),
            "ORDER_SEND_ATTEMPTED": int(self.session.get("order_send_attempted") or 0),
            "ORDER_SEND_FAILED": int(self.session.get("order_send_failed") or 0),
            "OPENED": int(self.session.get("opened") or self.session.get("orders_created") or 0),
            "BLOCKED": int(self.session.get("signals_blocked_by_sender") or 0),
            "dominant_blocker": self._dominant_post_sender_blocker(),
            "latest_timeline": copy.deepcopy(self._execution_timelines[-1]) if self._execution_timelines else None,
            "timelines": copy.deepcopy(self._execution_timelines[-100:]),
            "timestamp": self._timestamp(),
        }

    def run_once(self, signals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if self.session["status"] not in {"RUNNING", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC"} or self.config["auto_validation_enabled"] is not True:
            return self._decision("IDLE", ["AUTO_VALIDATION_NOT_RUNNING"])
        self._sync_lifecycle_services(manual=False)
        self._refresh_session_metrics()
        mt5_health = self._mt5_health_check()
        if self.session["status"] == "WAITING_FOR_MT5_RECONNECT":
            if mt5_health.get("status") == "MT5_CONNECTED":
                self.session["status"] = "RUNNING"
                self.session["paused_reason"] = ""
                self.session["mt5_disconnect_recovered_at"] = self._timestamp()
                self._log("MT5_RECONNECTED", {"mt5_health": mt5_health, "reconnect_attempts": self.session.get("mt5_reconnect_attempts", 0)})
                self._save_state()
            elif self._mt5_disconnect_timed_out():
                return self._halt("MT5_DISCONNECT_TIMEOUT")
            else:
                return self._decision("WAITING_FOR_MT5_RECONNECT", ["MT5_DISCONNECTED"], extra={"mt5_health": copy.deepcopy(mt5_health)})
        elif mt5_health.get("status") == "MT5_DISCONNECTED":
            return self._pause_for_mt5_disconnect(mt5_health)
        self._history_warmup_diagnostics = self._warmup_history_before_validation()
        self._apply_history_warmup_state()
        if self._history_warmup_diagnostics.get("history_ready") is not True:
            decision = self._decision(
                "WAITING_FOR_MT5_HISTORY_SYNC",
                ["MT5_HISTORY_SYNC_PENDING"],
                extra={
                    "history_warmup": copy.deepcopy(self._history_warmup_diagnostics),
                    "reason": self._history_warmup_diagnostics.get("message"),
                    "final_decision_reason": self._history_warmup_diagnostics.get("message"),
                },
            )
            self._log("WAITING_FOR_MT5_HISTORY_SYNC", self._history_warmup_diagnostics)
            return decision
        halt = self._risk_halt_reason()
        if halt:
            return self._halt(halt)
        self._run_exit_management(manual=False)
        signals = [self._normalize_demo_collection_signal(signal) for signal in self._allowed_signals(signals if signals is not None else self._load_signals())]
        self._record_execution_funnel_scan(signals)
        self._record_confidence_timeline(signals)
        checked = [self._checked_symbol_result(signal) for signal in signals]
        best_candidate = self._best_candidate(checked)
        blocked_decision: dict[str, Any] | None = None
        for signal in signals:
            self._current_signal_watched = signal
            self._log("SIGNAL_EVALUATED", {"symbol": signal.get("symbol"), "signal_hash": signal.get("signal_hash")})
            if not self._ready(signal):
                continue
            decision = self._execute_signal(signal)
            decision.update(self._scan_context(checked, signal))
            self._last_execution_decision = decision
            self._record_decision_traces(checked, decision)
            self._save_state()
            if decision["status"] in {"ORDER_SENT", "HALTED_RISK"}:
                return decision
            if decision["status"] == "BLOCKED":
                blocked_decision = decision
                continue
        if blocked_decision is not None:
            self._record_decision_traces(checked, blocked_decision)
            self._log("NO_QUALIFIED_SIGNAL", blocked_decision)
            return blocked_decision
        no_qualified_reason = self._no_qualified_signal_reason(checked)
        decision = self._decision(
            "NO_QUALIFIED_SIGNAL",
            ["NO_READY_APPROVED_SIGNAL"],
            extra={
                **self._scan_context(checked, best_candidate),
                "decision_reason": no_qualified_reason,
                "final_decision_reason": no_qualified_reason,
                "rejection_reason": no_qualified_reason,
            },
        )
        self._record_decision_traces(checked, decision)
        self._log("NO_QUALIFIED_SIGNAL", decision)
        return decision

    def _execute_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        blockers = self._validate_signal(signal)
        if blockers:
            event = "RISK_HALT_TRIGGERED" if self._halt_blocker(blockers) else "SIGNAL_BLOCKED"
            self._log(event, {"blockers": blockers, "signal_hash": signal.get("signal_hash")})
            if self._halt_blocker(blockers):
                return self._halt(blockers[0])
            return self._decision("BLOCKED", blockers, signal)

        service = self.guarded_execution_service
        if service is None:
            return self._halt("GUARDED_SENDER_UNAVAILABLE")
        payload = self._guarded_payload(signal)
        self._increment_funnel("wrapper_submitted")
        result = service.send_test_order(payload)
        execution_timeline = self._record_post_sender_timeline(signal, payload, result)
        self._apply_execution_stage_counters(result)
        sent = result.get("status") == "DEMO_ORDER_SENT" and result.get("mt5_order_sent") is True
        if not sent:
            self._increment_funnel("signals_blocked_by_sender")
            rejection = self._sender_rejection(result, payload)
            self._last_sender_rejection = rejection
            self._log("GUARDED_SENDER_REJECTED", rejection)
            return self._decision("BLOCKED", ["GUARDED_SENDER_REJECTED"], signal, {"sender_result": result, "last_sender_rejection": rejection, "guarded_sender_used": bool(result.get("guarded_sender_used")), "execution_timeline": execution_timeline})
        self._increment_funnel("orders_created")
        self._increment_funnel("opened")
        decision = self._decision("ORDER_SENT", [], signal, {"sender_result": result, "guarded_sender_used": True, "mt5_order_sent": True, "execution_timeline": execution_timeline})
        self._record_opened_trade_from_sender(signal, payload, result, decision)
        self._seen_signal_hashes.add(str(signal.get("signal_hash") or ""))
        self._sent_signal_keys.add(self._duplicate_key(signal))
        self._last_trade_time = datetime.now(timezone.utc)
        self._log("ORDER_SENT", decision)
        self._refresh_session_metrics()
        self._save_state()
        return decision

    def _validate_signal(self, signal: dict[str, Any]) -> list[str]:
        blockers: list[str] = []
        config = self.config
        symbol = str(signal.get("symbol") or "").upper()
        signal_hash = str(signal.get("signal_hash") or "")
        account = self._account_status(signal)
        tick = self._tick(symbol)
        current = self._current_signal(symbol)
        active_profile = str(self.config.get("strategy_profile") or "DEMO_COLLECTION").upper()
        raw_open_positions = self._open_positions()
        open_positions = self._limit_count_positions(raw_open_positions, active_profile)
        exposure_counts = self._demo_collection_exposure_counts(symbol, raw_open_positions, open_positions, active_profile)
        duplicate_check = self._duplicate_check(signal, open_positions, exposure_counts)
        self._last_duplicate_check = duplicate_check
        hash_audit = self._hash_change_audit(signal, current)

        if account.get("account_type") != config["account_type_required"]:
            blockers.append("LIVE_ACCOUNT_DETECTED" if account.get("account_type") == "LIVE" else "DEMO_ACCOUNT_REQUIRED")
        if self._broker_detected(account, signal) != config["broker_required"]:
            blockers.append("NON_VANTAGE_BROKER_DETECTED")
        if symbol not in set(config["allowed_symbols"]):
            blockers.append("SYMBOL_NOT_ALLOWED")
        if float(config["lot_size"]) > 0.01:
            blockers.append("LOT_SIZE_EXCEEDS_0_01")
        if active_profile == "DEMO_COLLECTION":
            if signal.get("risk_status") != "APPROVED":
                blockers.append("RISK_REJECTED")
        elif signal.get("execution_status") != "READY_FOR_PREVIEW" or signal.get("risk_status") != "APPROVED":
            blockers.append("SIGNAL_NOT_READY_APPROVED")
        if active_profile in {"AUTO_VALIDATION", "DEMO_COLLECTION"}:
            if str(signal.get("strategy_profile") or "").upper() != active_profile:
                blockers.append("STRATEGY_PROFILE_MISMATCH")
            blockers.extend(self._profile_blockers(signal, active_profile))
        if self._news_blackout_active(signal):
            blockers.append("HIGH_IMPACT_NEWS_BLACKOUT")
        if active_profile != "DEMO_COLLECTION" and self._number(signal.get("confidence"), 0) < float(config["min_confidence"]):
            blockers.append("CONFIDENCE_BELOW_MINIMUM")
        if self._number(signal.get("risk_reward"), 0) < float(config["min_rr"]):
            blockers.append("RR_BELOW_MINIMUM")
        if config["require_sl_tp"] and not all(self._number(signal.get(key), 0) > 0 for key in ["entry", "stop_loss", "take_profit"]):
            blockers.append("SL_TP_REQUIRED")
        same_symbol_positions = [item for item in open_positions if str(item.get("symbol") or "").upper() == symbol]
        if duplicate_check["final_duplicate_decision"] is True:
            blockers.append("DUPLICATE_SIGNAL_BLOCKED")
        total_open_count = int(exposure_counts.get("total_limit_count", len(open_positions)))
        same_symbol_open_count = int(exposure_counts.get("symbol_limit_count", len(same_symbol_positions)))
        if total_open_count >= int(config["max_open_trades_total"]):
            blockers.append("MAX_OPEN_TRADES_TOTAL_REACHED")
        if same_symbol_open_count >= int(config["max_open_trades_per_symbol"]):
            blockers.append("MAX_OPEN_TRADES_PER_SYMBOL_REACHED")
        if self._daily_trade_count() >= int(config["max_daily_demo_trades"]):
            blockers.append("MAX_DAILY_TRADE_LIMIT_REACHED")
        if active_profile != "DEMO_COLLECTION" and self._cooldown_active():
            blockers.append("COOLDOWN_ACTIVE")
        if self.mt5_health_state.get("status") == "MT5_DISCONNECTED":
            blockers.append("MT5_DISCONNECTED")
        if tick.get("status") not in {"OK", "TICK_AVAILABLE_DIRECT"} and not self._tick_stale_within_grace(symbol, tick):
            blockers.append("SYMBOL_TICK_UNAVAILABLE")
            self._log("TEMPORARY_MARKET_DATA_FAILURE", {"symbol": symbol, "reason": "SYMBOL_TICK_UNAVAILABLE", "tick_status": tick.get("status"), "mt5_health": self.mt5_health_state})
        if tick.get("spread") is None:
            blockers.append("SPREAD_UNAVAILABLE")
            self._log("TEMPORARY_MARKET_DATA_FAILURE", {"symbol": symbol, "reason": "SPREAD_UNAVAILABLE", "tick_status": tick.get("status"), "mt5_health": self.mt5_health_state})
        if hash_audit.get("changed"):
            if hash_audit.get("minor_change"):
                self._last_hash_change_audit = hash_audit
                self._log("HASH_CHANGE_MINOR", hash_audit)
            elif not hash_audit.get("informational_only"):
                self._last_hash_change_audit = hash_audit
                if active_profile != "DEMO_COLLECTION":
                    blockers.append("SIGNAL_HASH_CHANGED")
                self._log("SIGNAL_HASH_CHANGED", hash_audit)
        return sorted(set(blockers))

    def _guarded_payload(self, signal: dict[str, Any]) -> dict[str, Any]:
        source = signal.get("candle_source") if isinstance(signal.get("candle_source"), dict) else {}
        strategy_profile = str(signal.get("strategy_profile") or self.config.get("strategy_profile") or "DEMO_COLLECTION").upper()
        symbol = str(signal.get("symbol") or "").upper()
        adaptive_level = self._current_adaptive_strategy_level(symbol) if strategy_profile == "DEMO_COLLECTION" else None
        return {
            "symbol": symbol,
            "side": str(signal.get("signal") or "").upper(),
            "action": str(signal.get("signal") or "").upper(),
            "lot": 0.01,
            "entry_price": self._number(signal.get("entry"), 0),
            "stop_loss": self._number(signal.get("stop_loss"), 0),
            "take_profit": self._number(signal.get("take_profit"), 0),
            "risk_reward_ratio": self._number(signal.get("risk_reward"), 0),
            "signal_confidence": self._number(signal.get("confidence"), 0),
            "adaptive_strategy_level": adaptive_level,
            "signal_hash": signal.get("signal_hash"),
            "signal_timestamp": signal.get("timestamp"),
            "setup_reason": signal.get("setup_reason") or signal.get("reason"),
            "strategy_profile": strategy_profile,
            "strategy_metadata": {
                "strategy_profile": strategy_profile,
                "market_structure_state": signal.get("market_structure_state") or {},
                "strategy_components": signal.get("strategy_components") or {},
                "quality_score": signal.get("quality_score") or {},
                "approval_audit": signal.get("approval_audit") or {},
                "round3_diagnostics": signal.get("round3_diagnostics") or self._round3_signal_diagnostics(signal) if strategy_profile == "DEMO_COLLECTION" else {},
                "adaptive_strategy_level": adaptive_level,
                "candle_source": signal.get("candle_source") or {},
                "sl_tp_source": signal.get("sl_tp_source"),
                "demo_risk_model": signal.get("demo_risk_model"),
            },
            "validation_session_id": self.session["session_id"],
            "validation_session_start_time": self.session.get("session_start_time") or self.session.get("started_at"),
            "session_started_by": self.session.get("session_started_by"),
            "execution_mode": "AUTO_VALIDATION",
            "broker_source": source.get("broker_source") or source.get("source") or "VANTAGE_DEMO",
            "account_login": source.get("account_login"),
            "confirm": True,
            "environment": "DEMO",
            "manual_confirmation": True,
            "acknowledge_demo_only": True,
            "acknowledge_no_live_trading": True,
            "acknowledge_no_order_placement_today": True,
            "acknowledge_single_trade_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _load_signals(self) -> list[dict[str, Any]]:
        if self.signal_provider is None:
            return []
        signals = [signal for symbol in sorted(self._allowed_symbols()) if (signal := self._signal_for_symbol(symbol)) is not None]
        return self._allowed_signals(signals)

    def _current_signal(self, symbol: str) -> dict[str, Any] | None:
        if symbol not in self._allowed_symbols():
            return None
        return self._signal_for_symbol(symbol)

    def _signal_for_symbol(self, symbol: str) -> dict[str, Any] | None:
        if self.signal_provider is None:
            return None
        profile = str(self.config.get("strategy_profile") or "DEMO_COLLECTION").upper()
        try:
            signal = self.signal_provider.signal_for_symbol(symbol, record_history=False, strategy_profile=profile)
        except TypeError:
            try:
                signal = self.signal_provider.signal_for_symbol(symbol, record_history=False)
            except TypeError:
                signal = self.signal_provider.signal_for_symbol(symbol)
        except Exception:
            return None
        if isinstance(signal, dict):
            signal.setdefault("strategy_profile", profile)
            return signal
        return None

    def _account_status(self, signal: dict[str, Any]) -> dict[str, Any]:
        if self.mt5_demo_service is not None:
            try:
                return self.mt5_demo_service.get_status()
            except Exception:
                pass
        source = signal.get("candle_source") if isinstance(signal.get("candle_source"), dict) else {}
        return {
            "account_type": source.get("account_type") or "DEMO",
            "server": source.get("server") or "VantageMarkets-Demo",
            "login": source.get("account_login") or "",
        }

    def _broker_detected(self, account: dict[str, Any], signal: dict[str, Any]) -> str | None:
        source = signal.get("candle_source") if isinstance(signal.get("candle_source"), dict) else {}
        broker = str(source.get("broker_source") or source.get("source") or "").upper()
        server = str(account.get("server") or source.get("server") or "").lower()
        if "vantage" in server and account.get("account_type") == "DEMO":
            return "VANTAGE_DEMO"
        if account.get("server") and "vantage" not in server:
            return None
        if broker == "VANTAGE_DEMO":
            return "VANTAGE_DEMO"
        return broker or None

    def _tick(self, symbol: str) -> dict[str, Any]:
        cached = self._tick_cache.get(symbol)
        if cached is not None:
            return cached
        service = getattr(self.guarded_execution_service, "market_data_service", None)
        if service is None:
            tick = {"status": "OK", "spread": 0.0, "symbol": symbol, "timestamp": self._timestamp()}
            self._tick_cache[symbol] = tick
            return tick
        try:
            tick = service.get_symbol_tick(symbol)
            if isinstance(tick, dict):
                tick.setdefault("symbol", symbol)
                tick.setdefault("timestamp", self._timestamp())
                self._tick_cache[symbol] = tick
                return tick
            return {"status": "SYMBOL_TICK_UNAVAILABLE", "spread": None, "symbol": symbol, "timestamp": self._timestamp()}
        except Exception:
            tick = {"status": "SYMBOL_TICK_UNAVAILABLE", "spread": None, "symbol": symbol, "timestamp": self._timestamp()}
            self._tick_cache[symbol] = tick
            return tick

    def _open_positions(self) -> list[dict[str, Any]]:
        if self.position_service is None:
            return []
        try:
            result = self.position_service.get_open_positions()
        except Exception:
            return []
        positions = result.get("positions", []) if isinstance(result, dict) else []
        return positions if isinstance(positions, list) else []

    def _limit_count_positions(self, positions: list[dict[str, Any]], profile: str) -> list[dict[str, Any]]:
        if str(profile or "").upper() != "DEMO_COLLECTION":
            return positions
        return [position for position in positions if self._position_belongs_to_current_session(position)]

    def _demo_collection_exposure_counts(
        self,
        symbol: str,
        raw_positions: list[dict[str, Any]],
        session_positions: list[dict[str, Any]],
        profile: str,
    ) -> dict[str, Any]:
        allowed_symbols = self._allowed_symbols()
        raw_allowed_positions = [position for position in raw_positions if str(position.get("symbol") or "").upper() in allowed_symbols]
        raw_symbol_positions = [position for position in raw_allowed_positions if str(position.get("symbol") or "").upper() == symbol]
        session_symbol_positions = [position for position in session_positions if str(position.get("symbol") or "").upper() == symbol]
        active_journal_positions = self._active_journal_open_positions(profile)
        journal_symbol_positions = [trade for trade in active_journal_positions if str(trade.get("symbol") or "").upper() == symbol]
        if str(profile or "").upper() == "DEMO_COLLECTION":
            symbol_limit_count = max(len(raw_symbol_positions), len(session_symbol_positions), len(journal_symbol_positions))
            total_limit_count = max(len(raw_allowed_positions), len(session_positions), len(active_journal_positions))
            limit_count_source = "max_raw_mt5_current_session_active_journal"
        else:
            symbol_limit_count = len(session_symbol_positions)
            total_limit_count = len(session_positions)
            limit_count_source = "profile_positions"
        return {
            "symbol_limit_count": symbol_limit_count,
            "total_limit_count": total_limit_count,
            "raw_symbol_open_positions_count": len(raw_symbol_positions),
            "raw_allowed_open_positions_count": len(raw_allowed_positions),
            "current_session_symbol_positions_count": len(session_symbol_positions),
            "current_session_total_positions_count": len(session_positions),
            "active_journal_symbol_positions_count": len(journal_symbol_positions),
            "active_journal_total_positions_count": len(active_journal_positions),
            "limit_count_source": limit_count_source,
        }

    def _active_journal_open_positions(self, profile: str) -> list[dict[str, Any]]:
        session_id = str(self.session.get("session_id") or "")
        allowed_symbols = self._allowed_symbols()
        active_statuses = {"OPEN", "SENT", "PENDING"}
        active_profile = str(profile or "").upper()
        return [
            trade
            for trade in self.trades()
            if str(trade.get("validation_session_id") or "") == session_id
            and str(trade.get("symbol") or "").upper() in allowed_symbols
            and str(trade.get("status") or "").upper() in active_statuses
            and (
                active_profile != "DEMO_COLLECTION"
                or str((trade.get("strategy_metadata") if isinstance(trade.get("strategy_metadata"), dict) else {}).get("strategy_profile") or trade.get("strategy_profile") or "").upper() == "DEMO_COLLECTION"
            )
        ]

    def _position_belongs_to_current_session(self, position: dict[str, Any]) -> bool:
        session_id = str(self.session.get("session_id") or "")
        if session_id and str(position.get("validation_session_id") or "") == session_id:
            return True
        return self._position_has_auto_validation_marker(position) and self._position_opened_after_session_start(position)

    def _reconcile_open_mt5_positions(self) -> list[dict[str, Any]]:
        session_id = str(self.session.get("session_id") or "")
        if not self._has_current_user_session():
            positions = self._open_positions()
            self._open_position_sync_diagnostics = {
                **self._empty_open_position_sync_diagnostics(),
                "mt5_open_positions_detected": len(positions),
                "mt5_open_positions": len(positions),
                "unmatched_open_positions": len(positions),
                "historical_unowned_open_positions": len(positions),
                "historical_positions": len(positions),
                "validation_positions": 0,
                "current_session_positions": 0,
                "current_session_open_positions_by_symbol": {},
                "limit_count_source": "current_session_positions_only",
                "unmatched_open_position_tickets": [self._position_ticket(position) for position in positions if self._position_ticket(position)],
                "historical_unowned_open_position_tickets": [self._position_ticket(position) for position in positions if self._position_ticket(position)],
                "timestamp": self._timestamp(),
            }
            return []
        positions = self._open_positions()
        trades = self.trades()
        trades_by_ticket = {
            str(trade.get("mt5_ticket") or ""): trade
            for trade in trades
            if str(trade.get("mt5_ticket") or "")
        }
        allowed_symbols = self._allowed_symbols()
        session_positions: list[dict[str, Any]] = []
        unmatched_positions: list[dict[str, Any]] = []
        for position in positions:
            ticket = self._position_ticket(position)
            matched_trade = trades_by_ticket.get(ticket)
            position_session = str(position.get("validation_session_id") or "")
            symbol = str(position.get("symbol") or "").upper()
            allowed_position = symbol in allowed_symbols
            auto_owned = matched_trade is not None or position_session == session_id or self._position_belongs_to_current_session(position)
            if not auto_owned:
                unmatched_positions.append(position)
                continue
            session_positions.append(position)
            self._persist_open_confirmed_reason(position)
            if matched_trade is not None:
                self._record_open_position(position, matched_trade)
            elif allowed_position and self._position_opened_after_session_start(position):
                self._record_open_position(position, self._synthetic_open_position_trade(position))
        self._open_position_sync_diagnostics = {
            "mt5_open_positions_detected": len(positions),
            "mt5_open_positions": len(positions),
            "auto_owned_open_positions": len(session_positions),
            "unmatched_open_positions": len(unmatched_positions),
            "historical_unowned_open_positions": len(unmatched_positions),
            "historical_positions": len(unmatched_positions),
            "validation_positions": len(session_positions),
            "current_session_positions": len(session_positions),
            "current_session_open_positions_by_symbol": self._positions_by_symbol(session_positions),
            "limit_count_source": "current_session_positions_only",
            "open_position_tickets": [self._position_ticket(position) for position in session_positions if self._position_ticket(position)],
            "unmatched_open_position_tickets": [self._position_ticket(position) for position in unmatched_positions if self._position_ticket(position)],
            "historical_unowned_open_position_tickets": [self._position_ticket(position) for position in unmatched_positions if self._position_ticket(position)],
            "timestamp": self._timestamp(),
        }
        return session_positions

    def _positions_by_symbol(self, positions: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for position in positions:
            symbol = str(position.get("symbol") or "").upper()
            if symbol:
                counts[symbol] = counts.get(symbol, 0) + 1
        return counts

    def _record_opened_trade_from_sender(self, signal: dict[str, Any], payload: dict[str, Any], result: dict[str, Any], decision: dict[str, Any] | None = None) -> None:
        ticket = str(result.get("ticket") or result.get("mt5_ticket") or "")
        if not ticket or ticket == "0":
            return
        symbol = str(payload.get("symbol") or signal.get("symbol") or "").upper()
        level = self._current_adaptive_strategy_level(symbol)
        entry = result.get("entry") or result.get("entry_estimate") or payload.get("entry_price") or signal.get("entry")
        sl = result.get("sl") or payload.get("stop_loss") or signal.get("stop_loss")
        tp = result.get("tp") or payload.get("take_profit") or signal.get("take_profit")
        try:
            self.reason_panel_service.persist_order_sent(signal=signal, payload=payload, result=result, decision=decision or {}, timestamp=(decision or {}).get("timestamp"))
        except Exception:
            pass
        self._log(
            "ORDER_OPEN_CONFIRMED",
            {
                "ticket": ticket,
                "symbol": symbol,
                "side": payload.get("action") or payload.get("side") or signal.get("signal"),
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "confirmation_score": (decision or {}).get("confirmation_score"),
                "confirmation_required": (decision or {}).get("confirmation_required"),
                "adaptive_level": level,
                "validation_session_id": self.session.get("session_id"),
            },
        )
        self._record_adaptive_trade_activity("OPENED", {"ticket": ticket, "symbol": symbol, "opened_at": self._timestamp()})
        if self.journal_service is None or not hasattr(self.journal_service, "record_open_position"):
            return
        journal_payload = {
            "trade_id": f"mt5_demo_{ticket}",
            "source": "MT5_DEMO",
            "environment": "DEMO",
            "symbol": symbol,
            "side": payload.get("action") or payload.get("side") or signal.get("signal"),
            "lot": payload.get("lot"),
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "risk_reward_ratio": result.get("rr") or payload.get("risk_reward_ratio") or signal.get("risk_reward"),
            "profit_loss": 0.0,
            "mt5_ticket": ticket,
            "mt5_retcode": result.get("retcode") or result.get("final_retcode"),
            "mt5_comment": result.get("comment") or result.get("final_comment"),
            "account_login": result.get("account_login") or payload.get("account_login"),
            "server": result.get("server"),
            "broker_source": result.get("broker_source") or payload.get("broker_source") or payload.get("broker_id"),
            "validation_session_id": self.session.get("session_id"),
            "execution_mode": payload.get("execution_mode"),
            "signal_confidence": payload.get("signal_confidence") or signal.get("confidence"),
            "signal_hash": payload.get("signal_hash") or signal.get("signal_hash"),
            "setup_reason": payload.get("setup_reason") or signal.get("setup_reason"),
            "decision_reason": (decision or {}).get("decision_reason") or (decision or {}).get("final_decision_reason"),
            "final_decision_reason": (decision or {}).get("final_decision_reason"),
            "passed_rules": (decision or {}).get("passed_rules"),
            "failed_rules": (decision or {}).get("failed_rules"),
            "advisory_warnings": (decision or {}).get("advisory_warnings"),
            "confirmation_score": (decision or {}).get("confirmation_score"),
            "confirmation_required": (decision or {}).get("confirmation_required"),
            "confirmation_total": (decision or {}).get("confirmation_total"),
            "confirmation_passed": (decision or {}).get("confirmation_passed"),
            "confirmation_missing": (decision or {}).get("confirmation_missing"),
            "adaptive_strategy_level": level,
            "strategy_profile": payload.get("strategy_profile") or signal.get("strategy_profile") or self.config.get("strategy_profile"),
            "strategy_metadata": payload.get("strategy_metadata"),
            "notes": "AUTO validation MT5 demo position opened through guarded sender.",
        }
        try:
            self.journal_service.record_open_position(journal_payload)
        except Exception:
            pass

    def _record_open_position(self, position: dict[str, Any], matched_trade: dict[str, Any]) -> None:
        if self.journal_service is None or not hasattr(self.journal_service, "record_open_position"):
            return
        ticket = self._position_ticket(position)
        payload = {
            **matched_trade,
            "trade_id": matched_trade.get("trade_id") or f"mt5_demo_{ticket}",
            "source": "MT5_DEMO",
            "environment": "DEMO",
            "symbol": position.get("symbol") or matched_trade.get("symbol"),
            "side": position.get("side") or position.get("type") or matched_trade.get("side"),
            "lot": position.get("lot") or position.get("volume") or matched_trade.get("lot"),
            "entry_price": position.get("entry_price") or position.get("price_open") or matched_trade.get("entry_price"),
            "stop_loss": position.get("stop_loss") or position.get("sl") or matched_trade.get("stop_loss"),
            "take_profit": position.get("take_profit") or position.get("tp") or matched_trade.get("take_profit"),
            "profit_loss": position.get("floating_pnl") or position.get("profit") or 0.0,
            "mt5_ticket": ticket,
            "account_login": position.get("account_login") or matched_trade.get("account_login"),
            "server": position.get("server") or matched_trade.get("server"),
            "validation_session_id": self.session.get("session_id"),
            "notes": "Reconciled AUTO validation open MT5 position.",
        }
        try:
            self.journal_service.record_open_position(payload)
        except Exception:
            pass

    def _persist_open_confirmed_reason(self, position: dict[str, Any]) -> None:
        try:
            symbol = str(position.get("symbol") or "").upper()
            self.reason_panel_service.persist_open_confirmed(
                self._normalized_open_position(position),
                adaptive_level=self._current_adaptive_strategy_level(symbol),
                session_id=str(self.session.get("session_id") or ""),
                timestamp=self._timestamp(),
            )
        except Exception:
            pass

    def _normalized_open_position(self, position: dict[str, Any]) -> dict[str, Any]:
        side = self._position_side(position) or str(position.get("side") or position.get("type") or position.get("action") or "").upper()
        return {
            **position,
            "ticket": self._position_ticket(position),
            "symbol": str(position.get("symbol") or "").upper(),
            "side": side,
            "entry_price": position.get("entry_price") or position.get("price_open"),
            "current_price": position.get("current_price") or position.get("price_current"),
            "stop_loss": position.get("stop_loss") or position.get("sl"),
            "take_profit": position.get("take_profit") or position.get("tp"),
            "floating_pnl": position.get("floating_pnl") if position.get("floating_pnl") is not None else position.get("profit"),
            "validation_session_id": str(self.session.get("session_id") or ""),
        }

    def _synthetic_open_position_trade(self, position: dict[str, Any]) -> dict[str, Any]:
        ticket = self._position_ticket(position)
        symbol = str(position.get("symbol") or "").upper()
        side = str(position.get("side") or position.get("type") or position.get("action") or "").upper()
        return {
            "trade_id": f"mt5_demo_{ticket}" if ticket else f"mt5_demo_open_{symbol.lower()}",
            "status": "OPEN",
            "result": "OPEN",
            "source": "MT5_DEMO",
            "environment": "DEMO",
            "symbol": symbol,
            "side": side,
            "lot": position.get("lot") or position.get("volume") or 0.01,
            "mt5_ticket": ticket,
            "validation_session_id": self.session.get("session_id"),
            "strategy_profile": self.config.get("strategy_profile"),
            "notes": "Reconciled AUTO validation open MT5 position detected by open-position guard.",
        }

    def _position_ticket(self, position: dict[str, Any]) -> str:
        return str(position.get("ticket") or position.get("mt5_ticket") or "")

    def _position_side(self, position: dict[str, Any]) -> str:
        raw = position.get("side") or position.get("action") or position.get("type")
        if isinstance(raw, str):
            text = raw.upper()
            if "BUY" in text or text == "0":
                return "BUY"
            if "SELL" in text or text == "1":
                return "SELL"
        if raw == 0:
            return "BUY"
        if raw == 1:
            return "SELL"
        return ""

    def _position_opened_after_session_start(self, position: dict[str, Any]) -> bool:
        session_start = str(self.session.get("session_start_time") or self.session.get("started_at") or "")
        opened_at = (
            position.get("validation_session_started_at")
            or position.get("auto_validation_opened_at")
            or position.get("opened_at")
            or position.get("time_update")
            or position.get("time")
            or position.get("time_msc")
        )
        if not session_start or opened_at in {None, ""}:
            return False
        session_dt = self._parse_time(session_start)
        position_dt = self._parse_time(opened_at)
        return bool(session_dt and position_dt and position_dt >= session_dt)

    def _position_has_auto_validation_marker(self, position: dict[str, Any]) -> bool:
        session_id = str(self.session.get("session_id") or "")
        if str(position.get("validation_session_id") or "") == session_id:
            return True
        profile = str(position.get("strategy_profile") or position.get("execution_mode") or "").upper()
        if profile in {"DEMO_COLLECTION", "AUTO_VALIDATION"}:
            return True
        comment = str(position.get("comment") or position.get("external_id") or position.get("magic_comment") or "").upper()
        return "AUTO" in comment or "GUARDED" in comment or "VALIDATION" in comment

    def _has_current_user_session(self) -> bool:
        return bool(
            self.session.get("session_id")
            and self.session.get("session_start_time")
            and str(self.session.get("session_started_by") or "") == "user_click"
        )

    def _allowed_symbols(self) -> set[str]:
        symbols = self.config.get("allowed_symbols", ["XAUUSD", "EURUSD"])
        return {str(symbol).upper() for symbol in symbols if str(symbol).upper()}

    def _history_symbols(self) -> list[str]:
        return [symbol for symbol in sorted(self._allowed_symbols()) if symbol in {"EURUSD", "XAUUSD"}] or ["EURUSD"]

    def _history_timeframes(self) -> list[str]:
        raw = self.config.get("history_warmup_timeframes", ["M15", "H1", "H4"])
        return [str(timeframe).upper() for timeframe in raw if str(timeframe).upper() in {"M15", "H1", "H4"}] or ["M15", "H1", "H4"]

    def _history_required_candles(self) -> int:
        return max(300, int(self.config.get("history_required_candles") or 300))

    def _provider_history_backfill_service(self, provider: Any | None) -> Any | None:
        if provider is None:
            return None
        service = getattr(provider, "backfill_service", None)
        if service is None:
            real_signal_service = getattr(provider, "real_signal_service", None)
            service = getattr(real_signal_service, "backfill_service", None)
        return service if service is not None and hasattr(service, "fetch_history") else None

    def _empty_history_warmup_diagnostics(self) -> dict[str, Any]:
        return {
            "status": "NOT_STARTED",
            "message": "MT5 history sync has not run.",
            "history_ready": False,
            "symbols": [],
            "timeframes": ["M15", "H1", "H4"],
            "required_candles": 300,
            "diagnostics": [],
            "timestamp": self._timestamp(),
        }

    def _warmup_history_before_validation(self) -> dict[str, Any]:
        required = self._history_required_candles()
        diagnostics: list[dict[str, Any]] = []
        for symbol in self._history_symbols():
            for timeframe in self._history_timeframes():
                try:
                    history = self.history_backfill_service.fetch_history(symbol, timeframe, count=required)
                except Exception as exc:
                    history = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "returned_count": 0,
                        "source": "MT5_DEMO",
                        "status": "HISTORY_SYNC_ERROR",
                        "message": str(exc),
                    }
                candles_loaded = int(history.get("returned_count") or len(history.get("candles", []) or []))
                ready = str(history.get("status") or "").upper() == "OK" and candles_loaded >= required
                diagnostics.append(
                    {
                        "symbol": str(history.get("symbol") or symbol).upper(),
                        "requested_symbol": str(history.get("requested_symbol") or symbol).upper(),
                        "resolved_symbol": str(history.get("resolved_symbol") or history.get("symbol") or symbol),
                        "timeframe": str(history.get("timeframe") or timeframe).upper(),
                        "candles_loaded": candles_loaded,
                        "candles_required": required,
                        "data_source": str(history.get("broker_source") or history.get("source") or "MT5_DEMO"),
                        "source": str(history.get("broker_source") or history.get("source") or "MT5_DEMO"),
                        "mt5_last_error": history.get("mt5_last_error"),
                        "process_id": history.get("process_id"),
                        "connection_id": history.get("connection_id"),
                        "terminal_path": history.get("terminal_path"),
                        "cache_hit": history.get("cache_hit") is True,
                        "cache_reason": history.get("cache_reason"),
                        "symbol_select_result": history.get("symbol_select_result"),
                        "symbol_select_error": history.get("symbol_select_error"),
                        "symbol_resolution": history.get("symbol_resolution") if isinstance(history.get("symbol_resolution"), dict) else {},
                        "history_ready": ready,
                        "status": "READY" if ready else "WAITING_FOR_MT5_HISTORY_SYNC",
                        "mt5_status": str(history.get("status") or "HISTORY_UNAVAILABLE"),
                        "message": str(history.get("message") or ""),
                    }
                )
        pending = self._first_pending_history_diagnostic(diagnostics)
        history_ready = pending is None and bool(diagnostics)
        message = "MT5 history sync ready."
        if pending:
            message = (
                f"Waiting for MT5 {pending.get('timeframe')} history sync: {pending.get('requested_symbol')} resolved as {pending.get('resolved_symbol')}, "
                f"loaded {pending.get('candles_loaded')} / required {pending.get('candles_required')} candles."
            )
        return {
            "status": "HISTORY_READY" if history_ready else "WAITING_FOR_MT5_HISTORY_SYNC",
            "message": message,
            "history_ready": history_ready,
            "symbols": self._history_symbols(),
            "timeframes": self._history_timeframes(),
            "required_candles": required,
            "diagnostics": diagnostics,
            "timestamp": self._timestamp(),
        }

    def _first_pending_history_diagnostic(self, diagnostics: list[dict[str, Any]]) -> dict[str, Any] | None:
        pending = [item for item in diagnostics if item.get("history_ready") is not True]
        if not pending:
            return None
        timeframe_rank = {"H4": 0, "M15": 1, "H1": 2}
        return sorted(pending, key=lambda item: (timeframe_rank.get(str(item.get("timeframe") or "").upper(), 9), str(item.get("symbol") or "")))[0]

    def _apply_history_warmup_state(self) -> None:
        self.session["history_ready"] = bool(self._history_warmup_diagnostics.get("history_ready"))
        self.session["history_status"] = str(self._history_warmup_diagnostics.get("status") or "NOT_STARTED")
        if self.session.get("status") in {"RUNNING", "WAITING_FOR_MT5_HISTORY_SYNC"}:
            self.session["status"] = "RUNNING" if self.session["history_ready"] else "WAITING_FOR_MT5_HISTORY_SYNC"
            self.session["paused_reason"] = "" if self.session["history_ready"] else "MT5_HISTORY_SYNC_PENDING"

    def _mt5_health_check(self) -> dict[str, Any]:
        self._tick_cache = {}
        status = self._account_status({})
        terminal_running = bool(status.get("terminal_running", status.get("status") == "CONNECTED"))
        account_login = str(status.get("login") or status.get("account_login") or "")
        server = str(status.get("server") or "")
        account_ok = bool(account_login and server)
        valid_tick_symbol = ""
        last_tick_time = None
        symbol_statuses: dict[str, Any] = {}
        for symbol in sorted(self._allowed_symbols()):
            tick = self._tick(symbol)
            valid_tick = tick.get("status") in {"OK", "TICK_AVAILABLE_DIRECT"} and self._number(tick.get("bid"), 0) > 0 and self._number(tick.get("ask"), 0) > 0
            symbol_statuses[symbol] = {"status": "MT5_CONNECTED" if valid_tick else "SYMBOL_TICK_UNAVAILABLE", "tick": tick}
            if valid_tick and not valid_tick_symbol:
                valid_tick_symbol = symbol
                last_tick_time = tick.get("timestamp") or self._timestamp()
        connected = terminal_running and account_ok and bool(valid_tick_symbol)
        previous_failures = int(self.mt5_health_state.get("consecutive_failed_health_checks") or 0)
        failures = 0 if connected else previous_failures + 1
        health_status = "MT5_CONNECTED" if connected else "MT5_DISCONNECTED" if failures >= 3 else "SYMBOL_TICK_UNAVAILABLE"
        self.mt5_health_state = {
            "status": health_status,
            "terminal_running": terminal_running,
            "account_login_present": bool(account_login),
            "server_present": bool(server),
            "account_login": account_login,
            "server": server,
            "consecutive_failed_health_checks": failures,
            "last_successful_tick_symbol": valid_tick_symbol or self.mt5_health_state.get("last_successful_tick_symbol", ""),
            "last_tick_time": last_tick_time or self.mt5_health_state.get("last_tick_time"),
            "symbol_statuses": symbol_statuses,
            "timestamp": self._timestamp(),
        }
        if not connected:
            if self.session.get("status") == "WAITING_FOR_MT5_RECONNECT":
                self.session["mt5_reconnect_attempts"] = int(self.session.get("mt5_reconnect_attempts") or 0) + 1
            self._log("TEMPORARY_MARKET_DATA_FAILURE", {"mt5_health": self.mt5_health_state})
        self._save_state()
        return self.mt5_health_state

    def _allowed_signals(self, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        allowed = self._allowed_symbols()
        return [signal for signal in signals if str(signal.get("symbol") or "").upper() in allowed]

    def _clear_disallowed_watched_signal(self) -> None:
        if not isinstance(self._current_signal_watched, dict):
            return
        if str(self._current_signal_watched.get("symbol") or "").upper() not in self._allowed_symbols():
            self._current_signal_watched = None
            self._save_state()

    def _checked_symbol_result(self, signal: dict[str, Any]) -> dict[str, Any]:
        symbol = str(signal.get("symbol") or "").upper()
        ready = self._ready(signal)
        blockers = self._validate_signal(signal) if ready else self._readiness_blockers(signal)
        round3 = self._round3_signal_diagnostics(signal) if str(self.config.get("strategy_profile") or "").upper() == "DEMO_COLLECTION" else {}
        confirmation_score = self._number(round3.get("confirmation_score"), self._number(signal.get("confirmation_score"), 0))
        tick_status = self.mt5_health_state.get("symbol_statuses", {}).get(symbol, {}) if isinstance(self.mt5_health_state.get("symbol_statuses"), dict) else {}
        failed_hard_gates = self._decision_trace_failed_gates(blockers, round3)
        execution_decision = "READY_FOR_ORDER" if ready and not blockers else ("BLOCKED" if failed_hard_gates else "WAITING")
        return {
            "symbol": symbol,
            "status": signal.get("status_level") or signal.get("execution_status") or signal.get("signal") or "UNKNOWN",
            "confidence": signal.get("confidence"),
            "execution_status": signal.get("execution_status"),
            "risk_status": signal.get("risk_status"),
            "signal": signal.get("signal"),
            "direction_candidate": round3.get("direction_candidate") or signal.get("signal"),
            "signal_hash": signal.get("signal_hash"),
            "blocking_reason": ", ".join(blockers) if blockers else "QUALIFIED",
            "blockers": blockers,
            "hard_gates_passed": not failed_hard_gates,
            "failed_hard_gates": failed_hard_gates,
            "execution_decision": execution_decision,
            "why_order_not_sent": "" if execution_decision == "READY_FOR_ORDER" else self._why_order_not_sent(blockers, round3),
            "adaptive_level": round3.get("adaptive_level", self._current_adaptive_strategy_level(symbol)),
            "strategy_profile": signal.get("strategy_profile") or self.config.get("strategy_profile"),
            "market_data_status": tick_status.get("status", self.mt5_health_state.get("status")),
            "ready_for_execution": ready and not blockers,
            "score": confirmation_score,
            "required_score": round3.get("confirmation_required", 2),
            "confirmation_score": confirmation_score,
            "confirmation_required": round3.get("confirmation_required", 2),
            "confirmation_total": round3.get("confirmation_total", 4),
            "confirmation_passed": round3.get("confirmation_passed", []),
            "confirmation_missing": round3.get("confirmation_missing", []),
            "conditions": {
                "htf_bias": round3.get("trend_alignment_status"),
                "momentum": bool((round3.get("confirmation_states") or {}).get("MOMENTUM_DISPLACEMENT")) if isinstance(round3.get("confirmation_states"), dict) else False,
                "pullback_retest": bool((round3.get("confirmation_states") or {}).get("PULLBACK_RETEST")) if isinstance(round3.get("confirmation_states"), dict) else False,
                "bos": str(round3.get("bos_status") or "").upper() == "PRESENT",
                "liquidity_sweep": str(round3.get("liquidity_sweep_status") or "").upper() == "PRESENT",
                "fvg": str(round3.get("fvg_status") or "").upper() == "PRESENT",
                "fvg_retest": str(round3.get("fvg_retest_status") or "").upper() == "PRESENT",
                "session_bonus": bool(round3.get("advisory_session_bonus")),
            },
            "what_needs_to_happen_next": signal.get("what_needs_to_happen_next"),
            "missing_requirements": signal.get("missing_requirements") if isinstance(signal.get("missing_requirements"), list) else [],
        }

    def _readiness_blockers(self, signal: dict[str, Any]) -> list[str]:
        if str(self.config.get("strategy_profile") or "").upper() == "DEMO_COLLECTION":
            round3 = self._round3_signal_diagnostics(signal)
            failed = [str(item) for item in round3.get("failed_rules", []) if str(item or "").strip()]
            if failed:
                return sorted(set(failed))
        blockers: list[str] = []
        if signal.get("execution_status") != "READY_FOR_PREVIEW":
            blockers.append("SIGNAL_NOT_READY_FOR_PREVIEW")
        if signal.get("risk_status") != "APPROVED":
            blockers.append("RISK_STATUS_NOT_APPROVED")
        if str(signal.get("signal") or "").upper() not in {"BUY", "SELL"}:
            blockers.append("NO_BUY_SELL_SIGNAL")
        missing = signal.get("missing_requirements")
        if isinstance(missing, list):
            blockers.extend(str(item.get("code") or item.get("label") or item) for item in missing if item)
        return sorted(set(blockers)) or ["NO_READY_APPROVED_SIGNAL"]

    def _decision_trace_failed_gates(self, blockers: list[str], round3: dict[str, Any]) -> list[str]:
        failed = [str(item) for item in round3.get("failed_rules", []) if str(item or "").strip()]
        failed.extend(str(item) for item in blockers if str(item or "").strip())
        ignored_legacy = {
            "CONFIDENCE_BELOW_MINIMUM",
            "CONFIDENCE_GAP",
            "SESSION_VALID_REQUIRED",
            "FVG_REQUIRED",
            "ORDER_BLOCK_REQUIRED",
            "BOS_REQUIRED",
            "LIQUIDITY_SWEEP_REQUIRED",
            "SIGNAL_NOT_READY_FOR_PREVIEW",
            "RISK_STATUS_NOT_APPROVED",
            "NO_BUY_SELL_SIGNAL",
        }
        return sorted({item for item in failed if item not in ignored_legacy})

    def _why_order_not_sent(self, blockers: list[str], round3: dict[str, Any]) -> str:
        failed = self._decision_trace_failed_gates(blockers, round3)
        if failed:
            return f"Blocked because {self._friendly_gate_reason(failed[0])}."
        reason = str(round3.get("final_decision_reason") or "").strip()
        if reason:
            return reason
        return "No order was sent because the signal was not ready for execution."

    def _friendly_gate_reason(self, gate: str) -> str:
        labels = {
            "BALANCED_ENTRY_REQUIREMENT_MISSING": "balanced entry gates are incomplete",
            "MOMENTUM_OR_PULLBACK_MISSING": "momentum or pullback/retest is missing",
            "STRUCTURE_CONFIRMATION_MISSING": "BOS, liquidity sweep, or FVG retest is missing",
            "ROUND_3_SCORE_BELOW_THRESHOLD": "score is below the balanced threshold",
            "SCORE_5_NEEDS_CLEAN_MOMENTUM": "score 5 needs clean momentum",
            "LEVEL_3_NEEDS_MOMENTUM_AND_BOS_OR_SWEEP": "Level 3 needs momentum plus BOS or liquidity sweep",
            "RR_BELOW_2_0": "RR is below required 2.0",
            "SPREAD_TOO_HIGH": "spread is too high",
            "SL_TP_REQUIRED": "valid SL/TP is missing",
            "SL_TP_INVALID": "SL/TP is invalid",
            "RISK_REJECTED": "risk validation failed",
            "DIRECTION_BIAS_MISMATCH": "direction does not match higher-timeframe bias",
            "H4_HISTORY_INSUFFICIENT": "H4 history is not ready",
            "H1_HISTORY_INSUFFICIENT": "H1 history is not ready",
            "M15_HISTORY_INSUFFICIENT": "M15 history is not ready",
            "HIGH_IMPACT_NEWS_BLACKOUT": "high-impact news blackout is active",
        }
        return labels.get(str(gate), str(gate).replace("_", " ").lower())

    def _no_qualified_signal_reason(self, checked: list[dict[str, Any]]) -> str:
        if not checked:
            return "No order was sent because no allowed symbols produced a signal."
        best = self._best_candidate(checked) or checked[0]
        reason = str(best.get("why_order_not_sent") or "").strip()
        if reason:
            return reason
        failed = best.get("failed_hard_gates") if isinstance(best.get("failed_hard_gates"), list) else []
        if failed:
            return f"Blocked because {self._friendly_gate_reason(str(failed[0]))}."
        return "No order was sent because no balanced Round 3 setup passed the hard gates."

    def _record_decision_traces(self, checked: list[dict[str, Any]], decision: dict[str, Any] | None = None) -> None:
        timestamp = self._timestamp()
        decision_status = str((decision or {}).get("status") or "")
        decision_reason = str((decision or {}).get("decision_reason") or (decision or {}).get("final_decision_reason") or "")
        sender_result = (decision or {}).get("sender_result") if isinstance((decision or {}).get("sender_result"), dict) else {}
        sender_blockers = sender_result.get("blocked_reasons") or sender_result.get("blockers") or []
        if not isinstance(sender_blockers, list):
            sender_blockers = [str(sender_blockers)]
        sender_reason = (
            sender_result.get("final_blocker")
            or sender_result.get("rejection_code")
            or sender_result.get("failed_guard")
            or (sender_blockers[0] if sender_blockers else "")
            or sender_result.get("final_comment")
            or sender_result.get("comment")
            or sender_result.get("status")
            or ""
        )
        traces: list[dict[str, Any]] = []
        for item in checked:
            ready_item = bool(item.get("ready_for_execution"))
            execution_decision = decision_status if decision_status and ready_item else item.get("execution_decision")
            why_not_sent = "" if decision_status == "ORDER_SENT" else (item.get("why_order_not_sent") or decision_reason)
            if ready_item and decision_status == "BLOCKED" and sender_reason:
                execution_decision = "BLOCKED"
                why_not_sent = f"Blocked because {self._friendly_gate_reason(str(sender_reason))}."
            trace = {
                "timestamp": timestamp,
                "adaptive_level": int(item.get("adaptive_level") or self._current_adaptive_strategy_level(str(item.get("symbol") or ""))),
                "symbol": item.get("symbol"),
                "direction_candidate": item.get("direction_candidate"),
                "score": item.get("confirmation_score") or item.get("score"),
                "required_score": item.get("required_score") or item.get("confirmation_required"),
                "conditions": item.get("conditions") if isinstance(item.get("conditions"), dict) else {},
                "hard_gates_passed": bool(item.get("hard_gates_passed")),
                "failed_hard_gates": sender_blockers if ready_item and decision_status == "BLOCKED" and sender_blockers else item.get("failed_hard_gates") if isinstance(item.get("failed_hard_gates"), list) else [],
                "execution_decision": execution_decision,
                "why_order_not_sent": why_not_sent,
            }
            conditions = trace["conditions"] if isinstance(trace.get("conditions"), dict) else {}
            trace.update(
                {
                    "htf_bias": conditions.get("htf_bias"),
                    "momentum": conditions.get("momentum"),
                    "pullback_retest": conditions.get("pullback_retest"),
                    "bos": conditions.get("bos"),
                    "liquidity_sweep": conditions.get("liquidity_sweep"),
                    "fvg": conditions.get("fvg"),
                    "fvg_retest": conditions.get("fvg_retest"),
                    "session_bonus": conditions.get("session_bonus"),
                    "decision": execution_decision,
                    "reason": why_not_sent,
                }
            )
            traces.append(trace)
            self._persist_scan_trace(trace)
        if not traces and decision:
            traces.append(
                {
                    "timestamp": timestamp,
                    "adaptive_level": self._current_adaptive_strategy_level(str(decision.get("symbol") or "")),
                    "symbol": decision.get("symbol"),
                    "direction_candidate": decision.get("signal"),
                    "score": decision.get("confirmation_score"),
                    "hard_gates_passed": False,
                    "failed_hard_gates": decision.get("blockers") if isinstance(decision.get("blockers"), list) else [],
                    "execution_decision": decision_status or "UNKNOWN",
                    "why_order_not_sent": decision_reason or "No order was sent.",
                }
            )
        self._decision_traces = (self._decision_traces + traces)[-200:]
        if self._decision_traces:
            self.session["latest_decision_trace"] = self._decision_traces[-1]
            self.session["decision_traces"] = self._decision_traces[-200:]

    def _persist_scan_trace(self, trace: dict[str, Any]) -> None:
        try:
            timestamp = str(trace.get("timestamp") or self._timestamp())
            symbol = str(trace.get("symbol") or "").upper()
            trace = {
                **trace,
                "event_id": f"scan-result-{symbol.lower()}-{timestamp}",
                "active_session_id": self.session.get("session_id"),
                "decision": trace.get("execution_decision"),
            }
            self.reason_panel_service.persist_scan_result(trace, session_id=str(self.session.get("session_id") or ""))
        except Exception:
            pass

    def _profile_blockers(self, signal: dict[str, Any], profile: str) -> list[str]:
        blockers: list[str] = []
        components = signal.get("strategy_components") if isinstance(signal.get("strategy_components"), dict) else {}
        if profile == "AUTO_VALIDATION":
            if not components.get("fvg"):
                blockers.append("FVG_REQUIRED")
            if not components.get("order_block"):
                blockers.append("ORDER_BLOCK_REQUIRED")
            if not components.get("session_valid"):
                blockers.append("SESSION_VALID_REQUIRED")
        if profile == "DEMO_COLLECTION":
            round3 = self._round3_signal_diagnostics(signal)
            blockers.extend(round3.get("failed_rules", []))
        if str(signal.get("signal") or "").upper() not in {"BUY", "SELL"}:
            blockers.append("BUY_OR_SELL_REQUIRED")
        if self._number(signal.get("risk_reward"), 0) < float(self.config.get("min_rr", 1.5)):
            blockers.append("RR_BELOW_MINIMUM")
        if not self._signal_sl_tp_valid(signal):
            blockers.append("SL_TP_REQUIRED")
        symbol = str(signal.get("symbol") or "").upper()
        tick = self._tick(symbol)
        max_spread = 1.0 if symbol == "XAUUSD" else 0.0003
        spread = self._number(tick.get("spread"), None)
        spread_ok = spread is not None and spread <= max_spread
        live_tick_ok = tick.get("status") in {"OK", "TICK_AVAILABLE_DIRECT"} and spread_ok
        tick_ok_or_grace = live_tick_ok or self._tick_stale_within_grace(symbol, tick)
        if profile == "DEMO_COLLECTION":
            if not tick_ok_or_grace:
                blockers.append("SPREAD_TOO_HIGH")
        elif not live_tick_ok and not self._tick_stale_within_grace(symbol, tick):
            blockers.append("SPREAD_NOT_ACCEPTABLE_OR_STALE_WITHIN_GRACE")
        return blockers

    def _round3_signal_diagnostics(self, signal: dict[str, Any]) -> dict[str, Any]:
        symbol = str(signal.get("symbol") or "").upper()
        self._maybe_advance_adaptive_strategy_level(symbol)
        components = signal.get("strategy_components") if isinstance(signal.get("strategy_components"), dict) else {}
        candle_source = signal.get("candle_source") if isinstance(signal.get("candle_source"), dict) else {}
        timeframes = candle_source.get("timeframes", {}) if isinstance(candle_source.get("timeframes"), dict) else {}
        warmup = self._history_warmup_diagnostics if isinstance(self._history_warmup_diagnostics, dict) else {}
        warmup_diagnostics = warmup.get("diagnostics") if isinstance(warmup.get("diagnostics"), list) else []

        def history_ok(timeframe: str) -> bool:
            report = timeframes.get(timeframe, {}) if isinstance(timeframes, dict) else {}
            returned = int(report.get("returned_count") or 0)
            return str(report.get("status") or "").upper() == "OK" and returned >= self._history_required_candles()

        def warmup_count(timeframe: str) -> int:
            for item in warmup_diagnostics:
                if isinstance(item, dict) and str(item.get("timeframe") or "").upper() == timeframe:
                    return int(item.get("candles_loaded") or 0)
            return 0

        h4_ok = history_ok("H4")
        m15_ok = history_ok("M15")
        h1_ok = history_ok("H1")
        warmup_ready = warmup.get("history_ready") is True
        warmup_h4_count = warmup_count("H4")
        signal_h4_count = int((timeframes.get("H4", {}) if isinstance(timeframes, dict) else {}).get("returned_count") or 0)
        signal_history_ready = bool(candle_source.get("signal_history_ready")) or (h4_ok and h1_ok and m15_ok)
        confirmations = self._round3_confirmation_summary(signal, components)
        level = self._current_adaptive_strategy_level(symbol)
        level_config = self._adaptive_level_config(level, symbol)
        rr = self._number(signal.get("risk_reward"), None)
        passed_rules: list[str] = []
        failed_rules: list[str] = []
        level_specific_passed = self._adaptive_level_specific_passed(confirmations, level_config)
        states = confirmations.get("states") if isinstance(confirmations.get("states"), dict) else {}
        momentum_or_pullback = bool(states.get("MOMENTUM_DISPLACEMENT") or states.get("PULLBACK_RETEST"))
        structure_confirmed = bool(states.get("BOS") or states.get("LIQUIDITY_SWEEP") or states.get("FVG_RETEST"))
        score_threshold_passed = confirmations["score"] >= confirmations["required_score"]
        clean_score_five = confirmations["score"] > 5 or bool(states.get("MOMENTUM_DISPLACEMENT"))
        level3_structure = bool(states.get("BOS") or states.get("LIQUIDITY_SWEEP"))
        checks = [
            ("H4_HISTORY_AVAILABLE", "H4_HISTORY_INSUFFICIENT", h4_ok),
            ("H1_HISTORY_AVAILABLE", "H1_HISTORY_INSUFFICIENT", h1_ok),
            ("M15_HISTORY_AVAILABLE", "M15_HISTORY_INSUFFICIENT", m15_ok),
            ("RR_2_0_OR_HIGHER", "RR_BELOW_2_0", rr is not None and rr >= 2.0),
            ("SPREAD_ACCEPTABLE", "SPREAD_TOO_HIGH", bool(states.get("SPREAD_CLEAN"))),
            ("DIRECTION_MATCHES_HIGHER_TIMEFRAME_BIAS", "DIRECTION_BIAS_MISMATCH", confirmations["direction_valid"]),
            ("MOMENTUM_OR_PULLBACK_PRESENT", "MOMENTUM_OR_PULLBACK_MISSING", momentum_or_pullback),
            ("STRUCTURE_CONFIRMATION_PRESENT", "STRUCTURE_CONFIRMATION_MISSING", structure_confirmed),
            ("ROUND_3_SCORE_THRESHOLD", "ROUND_3_SCORE_BELOW_THRESHOLD", score_threshold_passed),
            ("SCORE_5_HAS_CLEAN_MOMENTUM", "SCORE_5_NEEDS_CLEAN_MOMENTUM", clean_score_five),
            (level_config.get("passed_rule", "ADAPTIVE_LEVEL_REQUIREMENT_MET"), "LEVEL_3_NEEDS_MOMENTUM_AND_BOS_OR_SWEEP" if level == 3 and not level_specific_passed else level_config.get("failed_rule", "ADAPTIVE_LEVEL_REQUIREMENT_MISSING"), level_specific_passed),
        ]
        for passed_code, failed_code, passed in checks:
            (passed_rules if passed else failed_rules).append(passed_code if passed else failed_code)
        advisory_warnings: list[str] = []
        advisory_warnings.extend(f"{code}_MISSING" for code in confirmations["missing_codes"])
        decision = "ACCEPTED" if not failed_rules else "REJECTED"
        reason = self._round3_decision_reason(symbol, decision, failed_rules, rr, confirmations)
        symbol_state = self._symbol_adaptive_state(symbol)
        return {
            "rule_name": "ROUND_3_EDGE_SCORE_FILTERS",
            "adaptive_level": level,
            "adaptive_level_name": level_config["name"],
            "current_strategy_level": level,
            "adaptive_activation_time": symbol_state.get("activation_time"),
            "last_trade_activity_time": symbol_state.get("last_activity_time"),
            "symbol_adaptive_level": level,
            "symbol_adaptive_state": copy.deepcopy(symbol_state),
            "passed_rules": passed_rules,
            "failed_rules": failed_rules,
            "advisory_warnings": advisory_warnings,
            "session": components.get("session") or "UNAVAILABLE",
            "RR": rr,
            "risk_reward": rr,
            "required_rr": 2.0,
            "history_required_candles": self._history_required_candles(),
            "warmup_history_ready": warmup_ready,
            "signal_history_ready": signal_history_ready,
            "warmup_m15_count": warmup_count("M15"),
            "warmup_h1_count": warmup_count("H1"),
            "warmup_h4_count": warmup_h4_count,
            "signal_m15_count": int(candle_source.get("signal_m15_count") or (timeframes.get("M15", {}) if isinstance(timeframes, dict) else {}).get("returned_count") or 0),
            "signal_h1_count": int(candle_source.get("signal_h1_count") or (timeframes.get("H1", {}) if isinstance(timeframes, dict) else {}).get("returned_count") or 0),
            "signal_h4_count": signal_h4_count,
            "confirmation_score": confirmations["score"],
            "confirmation_required": confirmations["required_score"],
            "confirmation_total": confirmations["total"],
            "confirmation_weights": confirmations["weights"],
            "score_breakdown": confirmations["score_breakdown"],
            "strong_confirmation_count": confirmations["strong_count"],
            "strong_confirmation_required": confirmations["strong_required"],
            "confirmation_passed": confirmations["passed_labels"],
            "confirmation_missing": confirmations["missing_labels"],
            "level3_structure_passed": level3_structure,
            "advisory_session_bonus": bool(components.get("session_valid")),
            "confirmation_states": confirmations["states"],
            "direction_candidate": confirmations.get("direction_candidate") or confirmations.get("direction"),
            "bos_status": "PRESENT" if components.get("bos") else "MISSING",
            "fvg_status": "PRESENT" if components.get("fvg") else "MISSING",
            "fvg_retest_status": "PRESENT" if confirmations["states"].get("FVG_RETEST") else "MISSING",
            "momentum_status": "PRESENT" if confirmations["states"].get("MOMENTUM_DISPLACEMENT") else "MISSING",
            "pullback_retest_status": "PRESENT" if confirmations["states"].get("PULLBACK_RETEST") else "MISSING",
            "liquidity_sweep_status": "PRESENT" if components.get("liquidity_sweep") else "MISSING",
            "trend_alignment_status": "ALIGNED" if confirmations["states"].get("HTF_ALIGNMENT") else "NOT_ALIGNED",
            "direction_bias_status": "MATCHED" if confirmations["direction_valid"] else "MISMATCHED",
            "h4_history_status": "AVAILABLE" if h4_ok else "INSUFFICIENT",
            "h1_history_status": "AVAILABLE" if h1_ok else "INSUFFICIENT",
            "m15_history_status": "AVAILABLE" if m15_ok else "INSUFFICIENT",
            "final_decision": decision,
            "final_decision_reason": reason,
            "rejection_reason": "" if decision == "ACCEPTED" else reason,
        }

    def _round3_confirmation_summary(self, signal: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
        symbol = str(signal.get("symbol") or "").upper()
        level_config = self._adaptive_level_config(symbol=symbol)
        trend = signal.get("market_structure_state") if isinstance(signal.get("market_structure_state"), dict) else {}
        direction = self._round3_direction_candidate(signal, components)
        raw_trend_bias = str(trend.get("trend_bias") or trend.get("higher_timeframe_bias") or components.get("higher_timeframe_bias") or components.get("trend_bias") or "").upper()
        trend_bias = self._normalize_bias_direction(raw_trend_bias)
        h4_bias = self._normalize_bias_direction(str(components.get("h4_bias") or components.get("h4_trend_bias") or trend.get("h4_bias") or trend.get("h4_trend_bias") or trend.get("higher_timeframe_bias") or "").upper())
        h1_bias = self._normalize_bias_direction(str(components.get("h1_bias") or components.get("h1_trend_bias") or trend.get("h1_bias") or trend.get("h1_trend_bias") or trend.get("intermediate_timeframe_bias") or "").upper())
        htf_bias = h4_bias if h4_bias and h4_bias == h1_bias else ""
        htf_agrees = bool(h4_bias and h1_bias and h4_bias == h1_bias)
        trend_aligned = direction in {"BUY", "SELL"} and htf_agrees and htf_bias == direction
        fvg = bool(components.get("fvg") or components.get("imbalance") or components.get("imbalance_zone"))
        pullback = bool(components.get("pullback") or components.get("retest") or components.get("entry_zone_valid") or components.get("near_fvg") or components.get("near_retest_zone"))
        fvg_retest = bool(components.get("fvg_retest") or components.get("fvg_retested") or components.get("fvg_entry_retest") or (fvg and pullback))
        momentum = bool(components.get("momentum") or components.get("displacement") or components.get("displacement_candle") or components.get("impulse_candle"))
        spread_clean = "SPREAD_TOO_HIGH" not in self._profile_spread_blockers(signal)
        rr_ok = self._number(signal.get("risk_reward"), 0) >= float(self.config.get("min_rr", 2.0))
        states = {
            "HTF_ALIGNMENT": trend_aligned,
            "BOS": bool(components.get("bos") or components.get("structure_confirmation")),
            "LIQUIDITY_SWEEP": bool(components.get("liquidity_sweep")),
            "FVG_RETEST": fvg_retest,
            "MOMENTUM_DISPLACEMENT": momentum,
            "PULLBACK_RETEST": pullback,
            "SPREAD_CLEAN": spread_clean,
            "RR_2_0": rr_ok,
        }
        labels = {
            "HTF_ALIGNMENT": "H1/H4 HTF alignment",
            "BOS": "BOS",
            "LIQUIDITY_SWEEP": "liquidity sweep",
            "FVG_RETEST": "FVG retest",
            "MOMENTUM_DISPLACEMENT": "momentum/displacement",
            "PULLBACK_RETEST": "pullback/retest",
            "SPREAD_CLEAN": "clean spread",
            "RR_2_0": "RR >= 2.0",
        }
        weights = {
            "HTF_ALIGNMENT": 2,
            "MOMENTUM_DISPLACEMENT": 2,
            "PULLBACK_RETEST": 1,
            "BOS": 2,
            "LIQUIDITY_SWEEP": 1,
            "FVG_RETEST": 1,
            "SPREAD_CLEAN": 1,
            "RR_2_0": 1,
        }
        strong_codes = {"HTF_ALIGNMENT", "BOS", "MOMENTUM_DISPLACEMENT", "PULLBACK_RETEST", "LIQUIDITY_SWEEP", "FVG_RETEST"}
        passed_codes = [code for code, passed in states.items() if passed]
        missing_codes = [code for code, passed in states.items() if not passed]
        score_breakdown = {code: weights.get(code, 0) for code in passed_codes}
        score = sum(score_breakdown.values())
        return {
            "score": score,
            "required_score": int(level_config["required_score"]),
            "preferred_score": int(level_config.get("preferred_score", 6)),
            "total": sum(weights.values()),
            "weights": weights,
            "score_breakdown": score_breakdown,
            "strong_count": len([code for code in passed_codes if code in strong_codes]),
            "strong_required": int(level_config["strong_required"]),
            "direction_valid": direction in {"BUY", "SELL"} and trend_aligned,
            "direction": direction,
            "direction_candidate": direction,
            "trend_bias": htf_bias or trend_bias or raw_trend_bias or direction,
            "h1_bias": h1_bias,
            "h4_bias": h4_bias,
            "states": states,
            "passed_codes": passed_codes,
            "missing_codes": missing_codes,
            "passed_labels": [labels[code] for code in passed_codes],
            "missing_labels": [labels[code] for code in missing_codes],
        }

    def _join_labels(self, labels: list[str]) -> str:
        if not labels:
            return ""
        if len(labels) == 1:
            return labels[0]
        if len(labels) == 2:
            return f"{labels[0]} and {labels[1]}"
        return f"{', '.join(labels[:-1])}, and {labels[-1]}"

    def _round3_decision_reason(self, symbol: str, decision: str, failed_rules: list[str], rr: float | None, confirmations: dict[str, Any] | None = None) -> str:
        confirmations = confirmations or {"score": 0, "required_score": 5, "strong_count": 0, "passed_labels": [], "missing_labels": ["HTF alignment", "momentum/pullback", "structure confirmation"]}
        first_failure = failed_rules[0] if failed_rules else ""
        level = self._current_adaptive_strategy_level(symbol)
        prefix = f"{symbol} Adaptive Level {level} active. "
        if decision == "ACCEPTED":
            rr_text = f"{rr:.1f}" if rr is not None else "2.0"
            passed = self._join_labels(list(confirmations.get("passed_labels") or [])) or "score"
            return f"{prefix}Accepted: Balanced Round 3 score {int(confirmations.get('score') or 0)}/{int(confirmations.get('required_score') or 5)} with {passed}. Direction {confirmations.get('direction')}. HTF bias {confirmations.get('trend_bias')}. RR {rr_text}. Risk approved."
        if first_failure == "H4_HISTORY_INSUFFICIENT":
            return f"{symbol} rejected because H4 history was insufficient."
        if first_failure == "H1_HISTORY_INSUFFICIENT":
            return f"{symbol} rejected because H1 history was insufficient."
        if first_failure == "M15_HISTORY_INSUFFICIENT":
            return f"{symbol} rejected because M15 history was insufficient."
        if first_failure == "RR_BELOW_2_0":
            rr_text = f"{rr:.1f}" if rr is not None else "missing"
            return f"Rejected: RR {rr_text} below required 2.0."
        if first_failure == "DIRECTION_BIAS_MISMATCH":
            return f"Rejected: direction {confirmations.get('direction') or 'unclear'} does not match higher-timeframe bias {confirmations.get('trend_bias') or 'unclear'}."
        if first_failure == "ROUND_3_SCORE_BELOW_THRESHOLD":
            missing = list(confirmations.get("missing_labels") or [])
            missing_text = self._join_labels(missing) or "more confluence"
            return f"{prefix}Waiting: Score {int(confirmations.get('score') or 0)}/{int(confirmations.get('required_score') or 5)}. Missing {missing_text}."
        if first_failure == "MOMENTUM_OR_PULLBACK_MISSING":
            return f"{prefix}Waiting: momentum or pullback/retest is needed next."
        if first_failure == "STRUCTURE_CONFIRMATION_MISSING":
            return f"{prefix}Waiting: need one structure confirmation from BOS, liquidity sweep, or FVG retest."
        if first_failure == "SCORE_5_NEEDS_CLEAN_MOMENTUM":
            return f"{prefix}Waiting: score 5 setups need clean momentum."
        if first_failure == "BALANCED_ENTRY_REQUIREMENT_MISSING":
            missing = list(confirmations.get("missing_labels") or [])
            missing_text = self._join_labels(missing) or "balanced entry confluence"
            return f"{prefix}Waiting: balanced entry is incomplete. Missing {missing_text}."
        if first_failure == "LEVEL_3_NEEDS_MOMENTUM_AND_BOS_OR_SWEEP":
            states = confirmations.get("states") if isinstance(confirmations.get("states"), dict) else {}
            missing = []
            if not states.get("MOMENTUM_DISPLACEMENT"):
                missing.append("momentum")
            if not (states.get("BOS") or states.get("LIQUIDITY_SWEEP")):
                missing.append("BOS or liquidity sweep")
            return f"{prefix}Waiting: Level 3 needs {self._join_labels(missing) or 'momentum plus BOS or liquidity sweep'}."
        return f"{prefix}Waiting: Score {int(confirmations.get('score') or 0)}/{int(confirmations.get('required_score') or 5)}."

    def _execution_decision_reason(self, status: str, blockers: list[str], signal: dict[str, Any] | None = None) -> str:
        blockers = [str(blocker) for blocker in blockers if str(blocker or "").strip()]
        blocker = blockers[0] if blockers else ""
        rr = self._number((signal or {}).get("risk_reward"), None)
        confirmations = self._round3_confirmation_summary(signal or {}, (signal or {}).get("strategy_components") if isinstance((signal or {}).get("strategy_components"), dict) else {}) if isinstance(signal, dict) else {"score": 0, "missing_labels": []}
        if status == "ORDER_SENT":
            rr_text = f"{rr:.1f}" if rr is not None else "2.0"
            level = self._current_adaptive_strategy_level(str((signal or {}).get("symbol") or ""))
            side = str((signal or {}).get("signal") or confirmations.get("direction") or "").upper()
            bias = str(confirmations.get("trend_bias") or "HTF bias").lower()
            return f"{side or 'Trade'} executed using Balanced Round 3. Adaptive Level {level} accepted score {int(confirmations.get('score') or 0)}/{int(confirmations.get('required_score') or 5)} with {bias}, RR {rr_text}, spread clean, and risk approved."
        if blocker in {"RR_BELOW_2_0", "RISK_REWARD_BELOW_MINIMUM", "RR_BELOW_MINIMUM"}:
            rr_text = f"{rr:.1f}" if rr is not None else "missing"
            return f"Rejected: RR {rr_text} below required 2.0."
        if blocker in {"SPREAD_TOO_HIGH", "SPREAD_TOO_WIDE", "SPREAD_UNAVAILABLE", "VALID_TICK_SPREAD_REQUIRED"}:
            return "Rejected: spread too high."
        if blocker == "HIGH_IMPACT_NEWS_BLACKOUT":
            return "Rejected: high-impact news blackout is active."
        if "RISK" in blocker or blocker in {"SL_TP_REQUIRED", "SL_TP_INVALID"}:
            return "Rejected: risk validation failed."
        if blocker in {"H4_HISTORY_INSUFFICIENT", "H1_HISTORY_INSUFFICIENT", "M15_HISTORY_INSUFFICIENT", "HISTORY_UNAVAILABLE"}:
            return f"Rejected: {blocker.replace('_', ' ').title()}."
        if status == "HALTED_RISK":
            diagnostics = self.session.get("risk_halt_diagnostics") if isinstance(self.session.get("risk_halt_diagnostics"), dict) else self._risk_halt_diagnostics()
            return str(diagnostics.get("message") or self._risk_halt_message(diagnostics))
        if blocker in {"CONFIRMATION_SCORE_BELOW_2", "CONFIRMATION_SCORE_LOW", "NO_READY_APPROVED_SIGNAL", "ROUND_3_SCORE_BELOW_THRESHOLD", "ADAPTIVE_LEVEL_1_REQUIREMENT_MISSING", "ADAPTIVE_LEVEL_0_REQUIREMENT_MISSING", "BALANCED_ENTRY_REQUIREMENT_MISSING", "MOMENTUM_OR_PULLBACK_MISSING", "STRUCTURE_CONFIRMATION_MISSING", "SCORE_5_NEEDS_CLEAN_MOMENTUM", "LEVEL_3_NEEDS_MOMENTUM_AND_BOS_OR_SWEEP"}:
            missing = list(confirmations.get("missing_labels") or [])
            missing_text = self._join_labels(missing) or "one more confirmation"
            level = self._current_adaptive_strategy_level(str((signal or {}).get("symbol") or ""))
            return f"Adaptive Level {level} active. Waiting: Score {int(confirmations.get('score') or 0)}/{int(confirmations.get('required_score') or 5)}. Missing {missing_text}."
        if blocker:
            return f"Rejected: {blocker.replace('_', ' ').lower()}."
        return "Waiting: no qualified Round 3 signal yet."

    def _round3_direction_candidate(self, signal: dict[str, Any], components: dict[str, Any]) -> str:
        raw = str(signal.get("signal") or signal.get("side") or signal.get("action") or "").upper()
        if raw in {"BUY", "SELL"}:
            return raw
        symbol = str(signal.get("symbol") or "").upper()
        if self._current_adaptive_strategy_level(symbol) < 3:
            return raw
        trend = signal.get("market_structure_state") if isinstance(signal.get("market_structure_state"), dict) else {}
        bias = str(trend.get("trend_bias") or trend.get("higher_timeframe_bias") or components.get("higher_timeframe_bias") or components.get("trend_bias") or "").upper()
        return self._normalize_bias_direction(bias) or raw

    def _normalize_bias_direction(self, value: str) -> str:
        text = str(value or "").upper()
        if text in {"BUY", "BULLISH", "LONG"}:
            return "BUY"
        if text in {"SELL", "BEARISH", "SHORT"}:
            return "SELL"
        return ""

    def _normalize_demo_collection_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        if str(self.config.get("strategy_profile") or "").upper() != "DEMO_COLLECTION":
            return signal
        normalized = dict(signal)
        components = normalized.get("strategy_components") if isinstance(normalized.get("strategy_components"), dict) else {}
        direction = self._round3_direction_candidate(normalized, components)
        if direction not in {"BUY", "SELL"}:
            return signal
        normalized["signal"] = direction
        normalized.setdefault("side", direction)
        normalized.setdefault("action", direction)
        symbol = str(normalized.get("symbol") or "").upper()
        tick = self._tick(symbol)
        if not self._demo_collection_tick_ok(symbol, tick):
            return normalized
        entry = self._number(normalized.get("entry"), None)
        if entry is None or entry <= 0:
            entry = self._entry_from_tick(direction, tick)
        if entry is not None and entry > 0:
            normalized["entry"] = entry
        if self._demo_collection_trade_plan_can_use_fallback(normalized):
            normalized.update(self._demo_collection_fallback_trade_plan(symbol, direction, entry))
        rr = self._number(normalized.get("risk_reward"), 0)
        if (
            self._signal_sl_tp_valid(normalized)
            and rr >= float(self.config.get("min_rr", 2.0))
            and not self._round3_signal_diagnostics(normalized).get("failed_rules")
        ):
            normalized["execution_status"] = "READY_FOR_PREVIEW"
            normalized["risk_status"] = "APPROVED"
            normalized["status_level"] = "READY_FOR_PREVIEW"
            audit = normalized.get("approval_audit") if isinstance(normalized.get("approval_audit"), dict) else {}
            advisory = self._demo_collection_advisory_from_signal(normalized)
            normalized["approval_audit"] = {
                **audit,
                "strategy_profile": "DEMO_COLLECTION",
                "sl_tp_source": normalized.get("sl_tp_source") or audit.get("sl_tp_source") or "STRATEGY",
                "relaxed_blockers": advisory,
                "advisory_requirements": advisory,
                "approval_note": "Round 3 normalized by AUTO runner: valid H4/M15 history, RR >= 2.0, SL/TP risk, spread, direction bias, and edge score passed. London/NY session is advisory bonus only.",
            }
            normalized.update(self._round3_signal_diagnostics(normalized))
            normalized["missing_requirements"] = [item for item in normalized.get("missing_requirements", []) if not self._demo_collection_advisory_code(item)]
        return normalized

    def _demo_collection_tick_ok(self, symbol: str, tick: dict[str, Any]) -> bool:
        spread = self._number(tick.get("spread"), None)
        max_spread = 1.0 if symbol == "XAUUSD" else 0.0003
        live_ok = tick.get("status") in {"OK", "TICK_AVAILABLE_DIRECT"} and spread is not None and spread <= max_spread
        return live_ok or self._tick_stale_within_grace(symbol, tick)

    def _profile_spread_blockers(self, signal: dict[str, Any]) -> list[str]:
        symbol = str(signal.get("symbol") or "").upper()
        tick = self._tick(symbol)
        if self._demo_collection_tick_ok(symbol, tick):
            return []
        return ["SPREAD_TOO_HIGH"]

    def _entry_from_tick(self, direction: str, tick: dict[str, Any]) -> float | None:
        return self._number(tick.get("ask" if direction == "BUY" else "bid"), None)

    def _demo_collection_trade_plan_can_use_fallback(self, signal: dict[str, Any]) -> bool:
        values = {key: self._number(signal.get(key), None) for key in ["entry", "stop_loss", "take_profit"]}
        if any(value is None or value <= 0 for value in values.values()):
            return True
        if self._signal_sl_tp_valid(signal) and self._number(signal.get("risk_reward"), 0) < float(self.config.get("min_rr", 2.0)):
            return True
        return False

    def _demo_collection_fallback_trade_plan(self, symbol: str, direction: str, entry: float | None) -> dict[str, Any]:
        if entry is None or entry <= 0:
            return {}
        min_rr = float(self.config.get("min_rr", 2.0))
        risk = max(entry * (0.001 if symbol == "XAUUSD" else 0.0008), 0.01 if symbol == "XAUUSD" else 0.0001)
        digits = 2 if symbol == "XAUUSD" else 5
        if direction == "BUY":
            stop_loss = entry - risk
            take_profit = entry + risk * min_rr
        else:
            stop_loss = entry + risk
            take_profit = entry - risk * min_rr
        return {
            "entry": round(entry, digits),
            "stop_loss": round(stop_loss, digits),
            "take_profit": round(take_profit, digits),
            "risk_reward": round(min_rr, 2),
            "sl_tp_source": "DEMO_RISK_FALLBACK",
            "demo_risk_model": {
                "model": "AUTO_RUNNER_FIXED_RISK",
                "risk_distance": round(risk, digits),
                "min_rr": min_rr,
            },
        }

    def _demo_collection_advisory_from_signal(self, signal: dict[str, Any]) -> list[dict[str, Any]]:
        advisory_codes = {"ORDER_BLOCK_MISSING", "LIQUIDITY_SWEEP_MISSING", "TREND_ALIGNMENT_MISSING"}
        items = signal.get("missing_requirements") if isinstance(signal.get("missing_requirements"), list) else []
        advisory = []
        for item in items:
            code = str((item.get("code") if isinstance(item, dict) else item) or "")
            if code in advisory_codes:
                advisory.append({**item, "advisory": True} if isinstance(item, dict) else {"code": code, "advisory": True})
        return advisory

    def _demo_collection_advisory_code(self, item: Any) -> bool:
        code = str((item.get("code") if isinstance(item, dict) else item) or "")
        return code in {"ORDER_BLOCK_MISSING", "LIQUIDITY_SWEEP_MISSING", "TREND_ALIGNMENT_MISSING", "SESSION_INVALID", "SESSION_OUTSIDE_LONDON_NY"}

    def _news_blackout_active(self, signal: dict[str, Any]) -> bool:
        sources = [
            signal.get("news_context"),
            signal.get("news_filter_decision"),
            signal.get("unified_news_decision"),
            signal.get("news_risk"),
        ]
        for source in sources:
            if not isinstance(source, dict):
                continue
            text = " ".join(str(source.get(key) or "") for key in ["status", "decision", "risk_level", "reason", "message"]).upper()
            if source.get("blackout_active") is True or source.get("in_blackout") is True:
                return True
            if "BLACKOUT" in text and any(word in text for word in ["ACTIVE", "BLOCK", "HIGH"]):
                return True
            if "HIGH" in text and "IMPACT" in text and any(word in text for word in ["BLOCK", "AVOID", "PAUSE"]):
                return True
        return False

    def _signal_sl_tp_valid(self, signal: dict[str, Any]) -> bool:
        direction = str(signal.get("signal") or "").upper()
        entry = self._number(signal.get("entry"), None)
        stop_loss = self._number(signal.get("stop_loss"), None)
        take_profit = self._number(signal.get("take_profit"), None)
        if direction == "BUY":
            return bool(entry and stop_loss and take_profit and stop_loss < entry < take_profit)
        if direction == "SELL":
            return bool(entry and stop_loss and take_profit and take_profit < entry < stop_loss)
        return False

    def _tick_stale_within_grace(self, symbol: str, tick: dict[str, Any]) -> bool:
        if str(tick.get("status") or "").upper() != "STALE_TICK":
            return False
        spread = self._number(tick.get("spread"), None)
        max_spread = 1.0 if symbol == "XAUUSD" else 0.0003
        stale_age = self._number(tick.get("stale_age_seconds"), 999999)
        return spread is not None and spread <= max_spread and stale_age <= 10

    def _best_candidate(self, checked: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not checked:
            return None
        return sorted(checked, key=lambda item: (bool(item.get("ready_for_execution")), self._number(item.get("score"), 0)), reverse=True)[0]

    def _scan_context(self, checked: list[dict[str, Any]], selected: dict[str, Any] | None) -> dict[str, Any]:
        allowed = sorted(self._allowed_symbols())
        per_symbol = {item["symbol"]: item for item in checked}
        no_qualified = "; ".join(f"{item['symbol']}: {item['blocking_reason']}" for item in checked if item.get("blocking_reason")) or "NO_ALLOWED_SYMBOL_SIGNALS"
        return {
            "watched_symbols": allowed,
            "last_checked_symbol": checked[-1]["symbol"] if checked else None,
            "best_candidate_symbol": (selected or {}).get("symbol"),
            "no_qualified_reason": no_qualified,
            "per_symbol_results": per_symbol,
            "EURUSD": per_symbol.get("EURUSD"),
            "XAUUSD": per_symbol.get("XAUUSD"),
            "mt5_health": copy.deepcopy(self.mt5_health_state),
            "strategy_profile": self.config.get("strategy_profile"),
            "last_hash_change_audit": copy.deepcopy(self._last_hash_change_audit),
            "xauusd_confidence_timeline": self._confidence_timeline.get("XAUUSD", [])[-20:],
        }

    def _refresh_session_metrics(self) -> None:
        reconciliation = self._reconcile_active_close_reports_into_journal()
        mt5_open_positions = self._reconcile_open_mt5_positions()
        target_trades = int(self.config.get("target_validation_trades") or self.config.get("target_closed_trades") or 30)
        if not self._has_current_user_session():
            self.session.update(
                {
                    "total_trades": 0,
                    "current_session_total_trades": 0,
                    "target_validation_trades": target_trades,
                    "current_closed_trades": 0,
                    "current_session_closed": 0,
                    "current_open_trades": 0,
                    "current_session_open_trades": 0,
                    "open_trades": 0,
                    "current_session_opened": 0,
                    "daily_demo_trade_count": 0,
                    "remaining_trades_to_target": target_trades,
                    "remaining_closed_trades": target_trades,
                    "progress_percentage": 0.0,
                    "signals_scanned": 0,
                    "signals_wait": 0,
                    "signals_watchlist": 0,
                    "signals_ready_for_preview": 0,
                    "signals_sent_to_sender": 0,
                    "signals_blocked_by_sender": 0,
                    "orders_created": 0,
                    "wrapper_submitted": 0,
                    "approval_workflow_passed": 0,
                    "guarded_sender_attempted": 0,
                    "opened": 0,
                    "order_build_attempted": 0,
                    "order_build_failed": 0,
                    "order_send_attempted": 0,
                    "order_send_failed": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "net_pnl": 0.0,
                    "avg_rr": 0.0,
                    "average_rr": 0.0,
                    "profit_factor": 0.0,
                    "max_drawdown": 0.0,
                    "best_setup_type": "Unavailable",
                    "worst_setup_type": "Unavailable",
                    "equity_curve": [],
                }
            )
            return
        trades = self.trades()
        closed = [trade for trade in trades if trade.get("status") == "CLOSED"]
        open_trades = [trade for trade in trades if trade.get("status") in {"OPEN", "SENT"}]
        open_ticket_keys = {str(trade.get("mt5_ticket") or "") for trade in open_trades if str(trade.get("mt5_ticket") or "")}
        mt5_open_ticket_keys = {self._position_ticket(position) for position in mt5_open_positions if self._position_ticket(position)}
        open_trade_count = len(open_trades) + len(mt5_open_ticket_keys - open_ticket_keys)
        opened_count = max(int(self.session.get("opened") or 0), int(self.session.get("orders_created") or 0), open_trade_count)
        daily_demo_trade_count = self._daily_trade_count()
        wins = [trade for trade in closed if trade.get("result") == "WIN"]
        losses = [trade for trade in closed if trade.get("result") == "LOSS"]
        pnl_values = [self._trade_pnl(trade) for trade in closed]
        rr_values = [rr for rr in (self._trade_rr(trade) for trade in closed) if rr is not None]
        gross_profit = sum(value for value in pnl_values if value > 0)
        gross_loss = abs(sum(value for value in pnl_values if value < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        setup_performance = self._setup_performance(closed)
        self._refresh_adaptive_strategy_level_stats(open_trades, closed)
        self.session.update(
            {
                "total_trades": len(closed) + open_trade_count,
                "current_session_total_trades": len(closed) + open_trade_count,
                "target_validation_trades": target_trades,
                "current_closed_trades": len(closed),
                "current_session_closed": len(closed),
                "current_open_trades": open_trade_count,
                "current_session_open_trades": open_trade_count,
                "open_trades": open_trade_count,
                "daily_demo_trade_count": daily_demo_trade_count,
                "remaining_trades_to_target": max(0, target_trades - len(closed)),
                "remaining_closed_trades": max(0, target_trades - len(closed)),
                "progress_percentage": round((len(closed) / target_trades) * 100, 2) if target_trades else 0.0,
                "opened": opened_count,
                "current_session_opened": opened_count,
                "orders_created": opened_count,
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": round((len(wins) / len(closed)) * 100, 2) if closed else 0.0,
                "net_pnl": round(sum(pnl_values), 2),
                "avg_rr": round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0,
                "average_rr": round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0,
                "profit_factor": round(profit_factor, 2),
                "max_drawdown": self._max_drawdown(pnl_values),
                "best_setup_type": setup_performance["best_setup_type"],
                "worst_setup_type": setup_performance["worst_setup_type"],
                "equity_curve": self._equity_curve(closed),
                "active_round_diagnostics": {
                    "active_session_id": self.session.get("session_id", ""),
                    "open_trade_count": open_trade_count,
                    "closed_trade_count": len(closed),
                    "latest_closed_tickets": [str(trade.get("mt5_ticket") or trade.get("ticket") or "") for trade in closed[-5:]],
                    "latest_open_tickets": sorted(mt5_open_ticket_keys or open_ticket_keys),
                    "event_count": len(self.events),
                    "counter_source": "active_session_trade_journal_plus_mt5_open_positions",
                    "reconciliation_action": reconciliation.get("action", "none"),
                    "reconciled_closed_tickets": reconciliation.get("tickets", []),
                },
            }
        )
        if self.session["status"] == "RUNNING" and self.session["current_closed_trades"] >= target_trades:
            self.session["status"] = "COMPLETED"
            self.session["stopped_at"] = self._timestamp()
            self.session["reason_stopped"] = "TARGET_COMPLETED"
            self.config["auto_validation_enabled"] = False
            self._log("TARGET_COMPLETED")
            self.round_archive_service.complete_round(self.session, self.config, closed, self.events)
            self._save_state()

    def _reconcile_active_close_reports_into_journal(self) -> dict[str, Any]:
        session_id = str(self.session.get("session_id") or "")
        if not session_id or self.journal_service is None or not hasattr(self.journal_service, "record_trade_closed"):
            return {"action": "skipped", "tickets": []}
        reports = [
            report
            for report in self._validation_close_reports
            if str(report.get("validation_session_id") or "") == session_id and str(report.get("ticket") or report.get("mt5_ticket") or "")
        ]
        if not reports:
            return {"action": "none", "tickets": []}
        existing = {str(trade.get("mt5_ticket") or trade.get("ticket") or ""): trade for trade in self.trades() if str(trade.get("mt5_ticket") or trade.get("ticket") or "")}
        reconciled: list[str] = []
        for report in reports:
            ticket = str(report.get("ticket") or report.get("mt5_ticket") or "")
            current = existing.get(ticket)
            if current is not None and str(current.get("status") or "").upper() == "CLOSED":
                self._persist_closed_confirmed_reason(current)
                continue
            payload = {
                **(current or {}),
                "trade_id": str((current or {}).get("trade_id") or report.get("trade_id") or f"mt5_demo_{ticket}"),
                "source": "MT5_DEMO",
                "environment": "DEMO",
                "symbol": report.get("symbol"),
                "side": report.get("side"),
                "entry_price": report.get("entry"),
                "close_price": report.get("exit"),
                "profit_loss": report.get("pnl"),
                "realized_pnl": report.get("pnl"),
                "total_pnl": report.get("pnl"),
                "net_pnl": report.get("pnl"),
                "result": report.get("result"),
                "exit_reason": report.get("exit_reason"),
                "opened_at": report.get("opened_at"),
                "closed_at": report.get("closed_at"),
                "close_time": report.get("closed_at"),
                "risk_reward_ratio": report.get("rr"),
                "signal_confidence": report.get("confidence"),
                "mt5_ticket": ticket,
                "validation_session_id": session_id,
                "strategy_profile": report.get("strategy_profile") or self.config.get("strategy_profile"),
                "notes": "Reconciled from MT5-confirmed validation close report.",
            }
            try:
                updated = self.journal_service.record_trade_closed(payload)
                self._persist_closed_confirmed_reason(updated)
                existing[ticket] = updated
                reconciled.append(ticket)
            except Exception:
                continue
        return {"action": "reconciled_close_reports_to_journal" if reconciled else "already_reconciled", "tickets": reconciled}

    def _persist_closed_confirmed_reason(self, trade: dict[str, Any]) -> None:
        try:
            self.reason_panel_service.persist_closed_confirmed(
                trade,
                session_id=str(self.session.get("session_id") or ""),
                timestamp=str(trade.get("closed_at") or trade.get("close_time") or self._timestamp()),
            )
        except Exception:
            pass

    def _sync_lifecycle_services(self, manual: bool = False) -> dict[str, Any]:
        result = self._empty_lifecycle_sync_diagnostics()
        result["manual"] = manual
        if not self._has_current_user_session():
            self._lifecycle_sync_diagnostics = {
                **result,
                "status": "SKIPPED",
                "message": "No current user-started AUTO validation session.",
                "timestamp": self._timestamp(),
            }
            return self._lifecycle_sync_diagnostics

        lifecycle_result: dict[str, Any] = {}
        close_result: dict[str, Any] = {}
        errors: list[str] = []
        try:
            if self.lifecycle_service is not None and hasattr(self.lifecycle_service, "sync"):
                lifecycle_result = self.lifecycle_service.sync()
        except Exception as exc:
            errors.append(f"lifecycle_sync_failed: {exc}")
        try:
            if self.close_sync_service is not None and hasattr(self.close_sync_service, "run"):
                close_result = self.close_sync_service.run()
        except Exception as exc:
            errors.append(f"close_sync_failed: {exc}")

        updated = []
        if isinstance(lifecycle_result.get("updated_trades"), list):
            updated.extend(item for item in lifecycle_result["updated_trades"] if isinstance(item, dict))
        if isinstance(close_result.get("closed_trades"), list):
            updated.extend(item for item in close_result["closed_trades"] if isinstance(item, dict))
        session_id = str(self.session.get("session_id") or "")
        session_closed = [trade for trade in updated if str(trade.get("validation_session_id") or "") == session_id]
        self._lifecycle_sync_diagnostics = {
            **result,
            "status": "ERROR" if errors else "SYNCED",
            "message": "; ".join(errors) if errors else "Lifecycle sync completed.",
            "lifecycle_status": lifecycle_result.get("status", "NOT_CONFIGURED" if not lifecycle_result else ""),
            "close_sync_status": close_result.get("status", "NOT_CONFIGURED" if not close_result else ""),
            "open_trades_checked": int(lifecycle_result.get("open_trades_checked") or close_result.get("open_trades_checked") or 0),
            "closed_trades_updated": len(session_closed),
            "all_closed_trades_updated": int(lifecycle_result.get("closed_trades_updated") or 0) + int(close_result.get("closed_trades_updated") or 0),
            "session_closed_trade_ids": [str(trade.get("trade_id") or "") for trade in session_closed if trade.get("trade_id")],
            "warnings": close_result.get("warnings") if isinstance(close_result.get("warnings"), list) else [],
            "errors": errors,
            "timestamp": self._timestamp(),
        }
        if session_closed:
            reports = self._emit_validation_close_reports(session_closed)
            self._lifecycle_sync_diagnostics["validation_close_reports"] = reports
            self._lifecycle_sync_diagnostics["latest_validation_close_report"] = reports[-1] if reports else None
            self._log("LIFECYCLE_SYNC_CLOSED_TRADES", {"closed_trades_updated": len(session_closed), "trade_ids": self._lifecycle_sync_diagnostics["session_closed_trade_ids"]})
        elif manual:
            self._log("LIFECYCLE_SYNC_COMPLETED", {"closed_trades_updated": 0, "status": self._lifecycle_sync_diagnostics["status"]})
        return self._lifecycle_sync_diagnostics

    def _run_exit_management(self, manual: bool = False) -> dict[str, Any]:
        if self.exit_management_service is None:
            self._exit_management_diagnostics = {
                **self._empty_exit_management_diagnostics(),
                "status": "NOT_CONFIGURED",
                "message": "Exit management service is not configured.",
                "manual": manual,
                "timestamp": self._timestamp(),
            }
            return self._exit_management_diagnostics
        positions = self._reconcile_open_mt5_positions()
        trades = self.trades()
        try:
            result = self.exit_management_service.run(session=dict(self.session), config=dict(self.config), positions=positions, trades=trades)
        except Exception as exc:
            result = {
                **self._empty_exit_management_diagnostics(),
                "status": "ERROR",
                "message": f"Exit management failed safely: {exc}",
                "manual": manual,
                "timestamp": self._timestamp(),
            }
        result["manual"] = manual
        self._exit_management_diagnostics = result
        managed_positions = result.get("managed_positions", []) if isinstance(result.get("managed_positions"), list) else []
        for item in managed_positions:
            if not isinstance(item, dict) or item.get("action") == "HOLD":
                continue
            event = "EXIT_SL_MOVED" if item.get("action") == "MODIFY_SL" else "EXIT_CLOSE_ATTEMPTED"
            execution = item.get("execution_result") if isinstance(item.get("execution_result"), dict) else {}
            if execution.get("status") in {"POSITION_CLOSED", "POSITION_PARTIALLY_CLOSED"}:
                event = "EXIT_CLOSE_SUCCEEDED"
            elif execution.get("status") == "EXIT_FAILED":
                event = "EXIT_CLOSE_FAILED"
            elif item.get("exit_reason") == "TRAILING_STOP":
                event = "EXIT_TRAILING_UPDATED"
            self._log(event, {"ticket": item.get("ticket"), "symbol": item.get("symbol"), "exit_reason": item.get("exit_reason"), "execution_result": execution})
        if int(result.get("actions_taken") or 0) > 0:
            self._log("EXIT_MANAGEMENT_ACTION", {"actions_taken": result.get("actions_taken"), "last_action": result.get("last_action")})
        elif manual:
            self._log("EXIT_MANAGEMENT_EVALUATED", {"positions_checked": result.get("positions_checked"), "status": result.get("status")})
        return self._exit_management_diagnostics

    def _risk_halt_reason(self) -> str | None:
        if self.session["current_closed_trades"] >= int(self.config.get("target_validation_trades") or self.config["target_closed_trades"]):
            return "TARGET_COMPLETED"
        if self.session["net_pnl"] <= -abs(float(self.config["max_daily_loss_amount"])):
            return "MAX_DAILY_LOSS_REACHED"
        if self.session["max_drawdown"] >= abs(float(self.config["max_total_drawdown_amount"])):
            return "MAX_DRAWDOWN_REACHED"
        return None

    def _apply_balanced_round3_config(self) -> None:
        if str(self.config.get("strategy_profile") or "").upper() != "DEMO_COLLECTION":
            return
        self.config["round3_strategy_model"] = "BALANCED_EDGE_SCORE"
        self.config["allowed_symbols"] = ["EURUSD", "XAUUSD"]
        self.config["balanced_round3_min_score"] = 5
        self.config["balanced_round3_preferred_score"] = 6
        self.config["adaptive_inactivity_minutes"] = 45
        self.config["min_rr"] = max(2.0, float(self.config.get("min_rr") or 2.0))
        self.config["break_even_trigger_r"] = 0.8
        self.config["trailing_stop_trigger_r"] = 1.2
        self.config["trailing_stop_distance_r"] = float(self.config.get("trailing_stop_distance_r") or 0.75)
        self.config["exit_stale_minutes"] = max(180, int(self.config.get("exit_stale_minutes") or 180))
        self.config["exit_soft_adverse_minutes"] = max(180, int(self.config.get("exit_soft_adverse_minutes") or 180))
        self.config["exit_no_progress_minutes"] = max(180, int(self.config.get("exit_no_progress_minutes") or 180))
        settings = self.config.get("per_symbol_exit_settings") if isinstance(self.config.get("per_symbol_exit_settings"), dict) else {}
        for symbol, symbol_settings in settings.items():
            if not isinstance(symbol_settings, dict):
                continue
            symbol_settings["break_even_trigger_r"] = 0.8
            symbol_settings["trailing_stop_trigger_r"] = 1.2
            symbol_settings["stale_exit_minutes"] = max(180, int(symbol_settings.get("stale_exit_minutes") or 180))
            symbol_settings["soft_adverse_minutes"] = max(180, int(symbol_settings.get("soft_adverse_minutes") or 180))
            symbol_settings["no_progress_minutes"] = max(180, int(symbol_settings.get("no_progress_minutes") or 180))
            settings[symbol] = symbol_settings
        self.config["per_symbol_exit_settings"] = settings

    def _risk_halt_message(self, diagnostics: dict[str, Any]) -> str:
        reason = str(diagnostics.get("reason") or "")
        if reason == "MAX_DAILY_LOSS_REACHED":
            return f"Risk halted: net P&L {diagnostics.get('net_pnl')} reached the daily loss limit {diagnostics.get('max_daily_loss_amount')}."
        if reason == "MAX_DRAWDOWN_REACHED":
            return f"Risk halted: max drawdown {diagnostics.get('max_drawdown')} reached the drawdown limit {diagnostics.get('max_total_drawdown_amount')}."
        if reason == "MT5_DISCONNECT_TIMEOUT":
            if diagnostics.get("stale"):
                return "Risk halt cleared: MT5 disconnect timeout was stale because MT5 is connected again. Resume manually when ready."
            return f"Risk halted: MT5 was disconnected longer than {diagnostics.get('mt5_disconnect_timeout_seconds')} seconds."
        if reason == "EMERGENCY_STOP":
            return "Risk halted: emergency stop was triggered."
        return f"Risk halted: {reason.replace('_', ' ').lower() or 'risk protection active'}."

    def _risk_halt_diagnostics(self, *, status_override: str | None = None, stale_override: bool | None = None) -> dict[str, Any]:
        reason = str(self.session.get("reason_stopped") or "")
        mt5_status = str(self.mt5_health_state.get("status") or "")
        net_pnl = round(float(self.session.get("net_pnl") or 0.0), 2)
        max_drawdown = round(float(self.session.get("max_drawdown") or 0.0), 2)
        daily_limit = abs(float(self.config.get("max_daily_loss_amount") or 0.0))
        drawdown_limit = abs(float(self.config.get("max_total_drawdown_amount") or 0.0))
        stale = reason == "MT5_DISCONNECT_TIMEOUT" and mt5_status == "MT5_CONNECTED"
        if stale_override is not None:
            stale = stale_override
        active = self.session.get("status") == "HALTED_RISK"
        diagnostics = {
            "active": active,
            "status": status_override or ("RISK_HALTED" if active else "RISK_CLEARED" if stale else "INACTIVE"),
            "reason": reason,
            "stale": stale,
            "clearable": stale and reason == "MT5_DISCONNECT_TIMEOUT",
            "net_pnl": net_pnl,
            "max_daily_loss_amount": daily_limit,
            "daily_loss_limit_reached": net_pnl <= -daily_limit if daily_limit else False,
            "max_drawdown": max_drawdown,
            "max_total_drawdown_amount": drawdown_limit,
            "drawdown_limit_reached": max_drawdown >= drawdown_limit if drawdown_limit else False,
            "mt5_health_status": mt5_status,
            "mt5_disconnect_timeout_seconds": int(float(self.config.get("mt5_disconnect_timeout_seconds") or 0)),
            "last_mt5_disconnect_at": self.session.get("last_mt5_disconnect_at") or "",
            "mt5_disconnect_recovered_at": self.session.get("mt5_disconnect_recovered_at") or "",
            "closed_trades": int(self.session.get("current_closed_trades") or 0),
            "wins": int(self.session.get("wins") or 0),
            "losses": int(self.session.get("losses") or 0),
            "timestamp": self._timestamp(),
        }
        diagnostics["message"] = self._risk_halt_message(diagnostics)
        return diagnostics

    def _persist_risk_halt_event(self, diagnostics: dict[str, Any] | None = None) -> None:
        try:
            self.reason_panel_service.persist_risk_halt(
                diagnostics or self._risk_halt_diagnostics(),
                session_id=str(self.session.get("session_id") or ""),
            )
        except Exception:
            pass

    def _maybe_clear_stale_risk_halt(self) -> None:
        if self.session.get("status") != "HALTED_RISK":
            return
        diagnostics = self._risk_halt_diagnostics()
        if diagnostics.get("clearable") is not True:
            self.session["risk_halt_diagnostics"] = diagnostics
            self._persist_risk_halt_event(diagnostics)
            return
        cleared = {**diagnostics, "active": False, "status": "RISK_CLEARED", "stale": True, "timestamp": self._timestamp()}
        cleared["message"] = self._risk_halt_message(cleared)
        self.session["status"] = "PAUSED_REQUIRES_USER_RESUME"
        self.session["paused_reason"] = "STALE_RISK_HALT_CLEARED"
        self.session["risk_halt_cleared_at"] = cleared["timestamp"]
        self.session["risk_halt_original_reason"] = diagnostics.get("reason")
        self.session["risk_halt_diagnostics"] = cleared
        self.config["auto_validation_enabled"] = False
        self._log("STALE_RISK_HALT_CLEARED", cleared)
        self._persist_risk_halt_event(cleared)
        self._save_state()

    def _pause_for_mt5_disconnect(self, mt5_health: dict[str, Any]) -> dict[str, Any]:
        if not self.session.get("last_mt5_disconnect_at"):
            self.session["last_mt5_disconnect_at"] = self._timestamp()
        self.session["status"] = "WAITING_FOR_MT5_RECONNECT"
        self.session["paused_reason"] = "MT5_DISCONNECTED"
        self.session["mt5_reconnect_attempts"] = int(self.session.get("mt5_reconnect_attempts") or 0) + 1
        self._log("MT5_DISCONNECT_DETECTED", {"mt5_health": mt5_health, "timeout_seconds": self.config.get("mt5_disconnect_timeout_seconds")})
        self._save_state()
        return self._decision("WAITING_FOR_MT5_RECONNECT", ["MT5_DISCONNECTED"], extra={"mt5_health": copy.deepcopy(mt5_health)})

    def _mt5_disconnect_timed_out(self) -> bool:
        started = self.session.get("last_mt5_disconnect_at")
        if not started:
            return False
        try:
            started_at = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        except ValueError:
            return False
        timeout = float(self.config.get("mt5_disconnect_timeout_seconds", 600))
        return datetime.now(timezone.utc) >= started_at + timedelta(seconds=timeout)

    def _halt(self, reason: str) -> dict[str, Any]:
        self.session["status"] = "COMPLETED" if reason == "TARGET_COMPLETED" else "HALTED_RISK"
        self.session["stopped_at"] = self._timestamp()
        self.session["reason_stopped"] = reason
        self.session["risk_halt_diagnostics"] = self._risk_halt_diagnostics()
        self.config["auto_validation_enabled"] = False
        self._log("RISK_HALT_TRIGGERED" if reason != "TARGET_COMPLETED" else "TARGET_COMPLETED", {"reason": reason})
        if reason != "TARGET_COMPLETED":
            self._persist_risk_halt_event(self.session["risk_halt_diagnostics"])
        self._save_state()
        return self._decision("HALTED_RISK" if reason != "TARGET_COMPLETED" else "COMPLETED", [reason])

    def _decision(self, status: str, blockers: list[str], signal: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        round3 = self._round3_signal_diagnostics(signal) if isinstance(signal, dict) and str(self.config.get("strategy_profile") or "").upper() == "DEMO_COLLECTION" else {}
        exact_reason = self._execution_decision_reason(status, blockers, signal)
        if status != "ORDER_SENT" and (not round3.get("final_decision_reason") or str(round3.get("final_decision_reason") or "").lower().startswith("accepted")):
            round3["final_decision_reason"] = exact_reason
            round3["rejection_reason"] = exact_reason if status in {"BLOCKED", "HALTED_RISK"} else ""
        decision = {
            "status": status,
            "blockers": blockers,
            "symbol": (signal or {}).get("symbol"),
            "signal_hash": (signal or {}).get("signal_hash"),
            "validation_session_id": self.session.get("session_id"),
            "guarded_sender_used": False,
            "mt5_order_sent": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "strategy_profile": self.config.get("strategy_profile"),
            "decision_reason": exact_reason,
            **round3,
            "timestamp": self._timestamp(),
            **(extra or {}),
        }
        self._last_execution_decision = decision
        self._save_state()
        return decision

    def _daily_trade_count(self) -> int:
        today = datetime.now(timezone.utc).date()
        count = 0
        for event in self.events:
            if event.get("event") != "ORDER_SENT":
                continue
            try:
                event_date = datetime.fromisoformat(str(event.get("timestamp")).replace("Z", "+00:00")).date()
            except ValueError:
                continue
            if event_date == today:
                count += 1
        return count

    def _latest_incomplete_validation_session(self) -> dict[str, Any] | None:
        if self.journal_service is None:
            return None
        try:
            trades = self.journal_service.list_trades(limit=100000)
        except Exception:
            return None
        target = int(self.config.get("target_validation_trades") or self.config.get("target_closed_trades") or 30)
        grouped: dict[str, dict[str, Any]] = {}
        for trade in trades:
            session_id = str(trade.get("validation_session_id") or "").strip()
            if not session_id:
                continue
            status = str(trade.get("status") or "").upper()
            group = grouped.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "trades": [],
                    "closed_count": 0,
                    "open_count": 0,
                    "latest_trade_time": "",
                    "started_at": "",
                    "session_start_time": "",
                },
            )
            group["trades"].append(trade)
            if status == "CLOSED":
                group["closed_count"] += 1
            if status in {"OPEN", "SENT", "PENDING"}:
                group["open_count"] += 1
            trade_time = self._trade_sort_time(trade)
            if trade_time and trade_time > str(group.get("latest_trade_time") or ""):
                group["latest_trade_time"] = trade_time
            opened_at = str(trade.get("opened_at") or trade.get("created_at") or "")
            if opened_at and (not group.get("started_at") or opened_at < str(group.get("started_at") or "")):
                group["started_at"] = opened_at
                group["session_start_time"] = opened_at
        mt5_positions = self._open_positions()
        mt5_tickets = {self._position_ticket(position) for position in mt5_positions if self._position_ticket(position)}
        for group in grouped.values():
            open_tickets = {
                str(trade.get("mt5_ticket") or "")
                for trade in group.get("trades", [])
                if str(trade.get("mt5_ticket") or "") and str(trade.get("status") or "").upper() in {"OPEN", "SENT", "PENDING"}
            }
            group["open_count"] = max(int(group.get("open_count") or 0), len(open_tickets & mt5_tickets))
            group["mt5_open_position_count"] = len(open_tickets & mt5_tickets)
        candidates = [
            group
            for group in grouped.values()
            if int(group.get("closed_count") or 0) < target or int(group.get("open_count") or 0) > 0
        ]
        if not candidates:
            return None
        current_id = str(self.session.get("session_id") or "")
        current = next((group for group in candidates if str(group.get("session_id") or "") == current_id), None)
        if current and (int(current.get("closed_count") or 0) > 0 or int(current.get("open_count") or 0) > 0):
            return current
        return sorted(candidates, key=lambda group: str(group.get("latest_trade_time") or group.get("started_at") or ""), reverse=True)[0]

    def _trade_sort_time(self, trade: dict[str, Any]) -> str:
        return str(
            trade.get("closed_at")
            or trade.get("opened_at")
            or trade.get("updated_at")
            or trade.get("created_at")
            or ""
        )

    def _log_recovery_decision(self, session_id: str, closed_count: int, open_count: int, new_session_created: bool, trigger: str, reason: str) -> None:
        self._log(
            "VALIDATION_SESSION_RECOVERY",
            {
                "resumed_session_id": session_id,
                "closed_trade_count": closed_count,
                "open_position_count": open_count,
                "new_session_created": new_session_created,
                "trigger": trigger,
                "reason": reason,
            },
        )

    def _cooldown_active(self) -> bool:
        if self._last_trade_time is None:
            return False
        return datetime.now(timezone.utc) < self._last_trade_time + timedelta(minutes=float(self.config["cooldown_after_trade_minutes"]))

    def _next_eligible_time(self) -> str | None:
        if self._last_trade_time is None:
            return None
        return (self._last_trade_time + timedelta(minutes=float(self.config["cooldown_after_trade_minutes"]))).isoformat()

    def _ready(self, signal: dict[str, Any]) -> bool:
        if str(self.config.get("strategy_profile") or "").upper() == "DEMO_COLLECTION":
            return signal.get("risk_status") == "APPROVED" and str(signal.get("signal") or "").upper() in {"BUY", "SELL"}
        return signal.get("execution_status") == "READY_FOR_PREVIEW" and signal.get("risk_status") == "APPROVED" and str(signal.get("signal") or "").upper() in {"BUY", "SELL"}

    def _halt_blocker(self, blockers: list[str]) -> bool:
        halts = {
            "LIVE_ACCOUNT_DETECTED",
            "DEMO_ACCOUNT_REQUIRED",
            "NON_VANTAGE_BROKER_DETECTED",
            "LOT_SIZE_EXCEEDS_0_01",
            "SL_TP_REQUIRED",
            "MAX_DRAWDOWN_REACHED",
            "MAX_DAILY_LOSS_REACHED",
            "MT5_DISCONNECT_TIMEOUT",
        }
        return any(item in halts for item in blockers)

    def _log(self, event: str, details: dict[str, Any] | None = None) -> None:
        self.events.append({"event": event, "details": details or {}, "timestamp": self._timestamp()})
        self._save_state()

    def log_runner_error(self, message: str) -> None:
        self._log("RUNNER_ERROR", {"error": message})

    def update_runner_state(self, **updates: Any) -> None:
        self.runner_state.update(updates)

    def should_auto_start_runner(self) -> bool:
        return self.session.get("status") in {"RUNNING", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC"} and self.config.get("auto_validation_enabled") is True

    def _has_recoverable_progress(self) -> bool:
        if self.session.get("status") not in {"PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"}:
            return False
        if not self._has_current_user_session():
            return False
        progress_keys = (
            "current_closed_trades",
            "current_session_closed",
            "current_open_trades",
            "current_session_open_trades",
            "opened",
            "orders_created",
            "current_session_opened",
            "total_trades",
            "current_session_total_trades",
        )
        return any(int(self.session.get(key) or 0) > 0 for key in progress_keys)

    def _recovery_status(self) -> dict[str, Any]:
        recoverable = self._has_recoverable_progress()
        return {
            "recoverable_session": recoverable,
            "recovered_session_id": self.session.get("session_id") if recoverable else "",
            "recovered_closed_trades": int(self.session.get("current_closed_trades") or self.session.get("current_session_closed") or 0) if recoverable else 0,
            "recovered_open_trades": int(self.session.get("current_open_trades") or self.session.get("current_session_open_trades") or 0) if recoverable else 0,
            "recovered_remaining_closed_trades": int(self.session.get("remaining_closed_trades") or self.session.get("remaining_trades_to_target") or 0) if recoverable else int(self.session.get("remaining_closed_trades") or 0),
            "requires_user_resume": self.session.get("status") in {"PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"},
        }

    def mark_backend_startup_resume(self) -> None:
        if self.should_auto_start_runner() and self.session.get("session_started_by") == "persisted_resume":
            self.session["session_started_by"] = "backend_startup_resume"
            self._save_state()

    def waiting_for_mt5_reconnect(self) -> bool:
        return self.session.get("status") == "WAITING_FOR_MT5_RECONNECT"

    def waiting_for_mt5_history_sync(self) -> bool:
        return self.session.get("status") == "WAITING_FOR_MT5_HISTORY_SYNC"

    def watched_signal_is_watchlist(self) -> bool:
        watched = self._current_signal_watched if isinstance(self._current_signal_watched, dict) else {}
        quality = watched.get("quality_score") if isinstance(watched.get("quality_score"), dict) else {}
        return str(watched.get("status_level") or quality.get("rating") or "").upper() == "WATCHLIST"

    def _empty_runner_state(self) -> dict[str, Any]:
        return {
            "runner_active": False,
            "runner_last_tick_at": None,
            "runner_next_tick_at": None,
            "runner_interval_seconds": 3,
            "run_once_in_progress": False,
            "last_run_once_duration_ms": None,
            "last_runner_error": "",
        }

    def _empty_lifecycle_sync_diagnostics(self) -> dict[str, Any]:
        return {
            "status": "NOT_SYNCED",
            "message": "AUTO validation lifecycle sync has not run.",
            "manual": False,
            "lifecycle_status": "NOT_CONFIGURED",
            "close_sync_status": "NOT_CONFIGURED",
            "open_trades_checked": 0,
            "closed_trades_updated": 0,
            "all_closed_trades_updated": 0,
            "session_closed_trade_ids": [],
            "validation_close_reports": [],
            "latest_validation_close_report": None,
            "warnings": [],
            "errors": [],
            "timestamp": None,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _empty_exit_management_diagnostics(self) -> dict[str, Any]:
        return {
            "status": "NOT_RUN",
            "message": "Exit management has not run yet.",
            "enabled": False,
            "manual": False,
            "positions_checked": 0,
            "actions_taken": 0,
            "blocked_actions": 0,
            "failed_actions": 0,
            "break_even_moves": 0,
            "trailing_stop_moves": 0,
            "time_stale_exits": 0,
            "signal_reversal_exits": 0,
            "confidence_drop_exits": 0,
            "managed_positions": [],
            "last_action": None,
            "last_failed_action": None,
            "timestamp": None,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _empty_mt5_health_state(self) -> dict[str, Any]:
        return {
            "status": "MT5_CONNECTED",
            "terminal_running": False,
            "account_login_present": False,
            "server_present": False,
            "account_login": "",
            "server": "",
            "consecutive_failed_health_checks": 0,
            "last_successful_tick_symbol": "",
            "last_tick_time": None,
            "symbol_statuses": {},
            "timestamp": None,
        }

    def _persisted_session_stale(self, updated_at: str) -> bool:
        if not updated_at:
            return True
        try:
            parsed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        return datetime.now(timezone.utc) - parsed > timedelta(minutes=30)

    def _seconds_since(self, timestamp: str, now: datetime | None = None) -> float:
        if not timestamp:
            return float("inf")
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return float("inf")
        return max(0.0, ((now or datetime.now(timezone.utc)) - parsed).total_seconds())

    def _parse_time(self, value: Any) -> datetime | None:
        if value in {None, ""}:
            return None
        if isinstance(value, (int, float)):
            number = float(value)
            if number > 10_000_000_000:
                number = number / 1000
            return datetime.fromtimestamp(number, tz=timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def _empty_open_position_sync_diagnostics(self) -> dict[str, Any]:
        return {
            "mt5_open_positions_detected": 0,
            "mt5_open_positions": 0,
            "auto_owned_open_positions": 0,
            "unmatched_open_positions": 0,
            "historical_unowned_open_positions": 0,
            "historical_positions": 0,
            "validation_positions": 0,
            "current_session_positions": 0,
            "current_session_open_positions_by_symbol": {},
            "limit_count_source": "current_session_positions_only",
            "open_position_tickets": [],
            "unmatched_open_position_tickets": [],
            "historical_unowned_open_position_tickets": [],
            "timestamp": None,
        }

    def _record_confidence_timeline(self, signals: list[dict[str, Any]]) -> None:
        for signal in signals:
            symbol = str(signal.get("symbol") or "").upper()
            if symbol != "XAUUSD":
                continue
            components = signal.get("strategy_components") if isinstance(signal.get("strategy_components"), dict) else {}
            audit = signal.get("approval_audit") if isinstance(signal.get("approval_audit"), dict) else {}
            quality = signal.get("quality_score") if isinstance(signal.get("quality_score"), dict) else {}
            factors = quality.get("factors") if isinstance(quality.get("factors"), dict) else {}
            previous = self._confidence_timeline.get(symbol, [])[-1] if self._confidence_timeline.get(symbol) else {}
            confidence = self._number(signal.get("confidence"), self._number(audit.get("confidence"), 0))
            previous_confidence = self._number(previous.get("confidence"), confidence)
            delta = round(confidence - previous_confidence, 2)
            if delta > 0:
                reason = f"Confidence increased by {delta} from prior scan."
            elif delta < 0:
                reason = f"Confidence decreased by {abs(delta)} from prior scan."
            else:
                reason = "Confidence unchanged from prior scan."
            item = {
                "timestamp": self._timestamp(),
                "confidence": confidence,
                "bos": components.get("bos"),
                "liquidity_sweep": components.get("liquidity_sweep"),
                "choch": components.get("choch"),
                "fvg": components.get("fvg"),
                "order_block": components.get("order_block"),
                "spread": components.get("spread_quality"),
                "session": components.get("session"),
                "session_valid": components.get("session_valid"),
                "factors": factors,
                "reason_for_confidence_change": reason,
            }
            self._confidence_timeline[symbol] = (self._confidence_timeline.get(symbol, []) + [item])[-20:]

    def _record_execution_funnel_scan(self, signals: list[dict[str, Any]]) -> None:
        for signal in signals:
            status = str(signal.get("status_level") or signal.get("execution_status") or signal.get("signal") or "").upper()
            action = str(signal.get("signal") or "").upper()
            self._increment_funnel("signals_scanned")
            if action == "WAIT" or status == "WAIT":
                self._increment_funnel("signals_wait")
            if status == "WATCHLIST":
                self._increment_funnel("signals_watchlist")
            if status == "READY_FOR_PREVIEW" or self._ready(signal):
                self._increment_funnel("signals_ready_for_preview")

    def _increment_funnel(self, key: str, amount: int = 1) -> None:
        self.session[key] = int(self.session.get(key) or 0) + amount

    def _record_post_sender_timeline(self, signal: dict[str, Any], payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        signal_id = str(payload.get("signal_hash") or signal.get("signal_hash") or "")
        blockers = result.get("blockers") or result.get("blocked_reasons") or []
        if not isinstance(blockers, list):
            blockers = [str(blockers)]
        duplicate_check = result.get("duplicate_check") if isinstance(result.get("duplicate_check"), dict) else {}
        revalidation = result.get("signal_revalidation") if isinstance(result.get("signal_revalidation"), dict) else {}
        approval = result.get("approval_result") if isinstance(result.get("approval_result"), dict) else {}
        tick_status = str(result.get("tick_status") or result.get("tick_recovery_status") or "")
        spread = self._number(result.get("spread"), None)
        spread_status = "SPREAD_OK" if spread is not None else "SPREAD_UNKNOWN"
        if "SPREAD_UNAVAILABLE" in blockers:
            spread_status = "SPREAD_UNAVAILABLE"
        elif "SPREAD_TOO_WIDE" in blockers:
            spread_status = "SPREAD_TOO_WIDE"
        hash_status = "HASH_NOT_REVALIDATED"
        current_signal = revalidation.get("current_signal") if isinstance(revalidation.get("current_signal"), dict) else {}
        if revalidation:
            current_hash = str(current_signal.get("signal_hash") or "")
            hash_status = "HASH_UNCHANGED" if current_hash and current_hash == signal_id else "HASH_CHANGED" if current_hash else "HASH_UNKNOWN"
        sent = result.get("status") == "DEMO_ORDER_SENT" and result.get("mt5_order_sent") is True
        guarded_sender_used = result.get("guarded_sender_used") is True
        order_build_attempted = result.get("guarded_sender_attempted") is True or guarded_sender_used or bool(result.get("request_id")) or sent
        order_send_attempted = result.get("order_send_attempted") is True or result.get("demo_order_attempted") is True or sent
        final_reason = (
            result.get("final_blocker")
            or result.get("rejection_code")
            or result.get("failed_guard")
            or (blockers[0] if blockers else "")
            or result.get("final_comment")
            or result.get("comment")
            or result.get("reason")
            or ("OPENED" if sent else "UNKNOWN")
        )
        timeline = {
            "signal_id": signal_id,
            "symbol": payload.get("symbol") or signal.get("symbol"),
            "strategy_profile": payload.get("strategy_profile") or signal.get("strategy_profile") or self.config.get("strategy_profile"),
            "sender_decision": result.get("status"),
            "revalidation_result": revalidation.get("status") or "NOT_REPORTED",
            "tick_status": tick_status or "NOT_REPORTED",
            "spread_status": spread_status,
            "entry_price": result.get("entry") or result.get("entry_estimate") or payload.get("entry_price"),
            "hash_status": hash_status,
            "approval_status": result.get("approval_status") or ("APPROVED" if approval.get("approved_for_future_demo_order") is True else "BLOCKED" if approval else "NOT_REPORTED"),
            "duplicate_status": result.get("duplicate_protection_status") or ("BLOCKED" if duplicate_check.get("final_duplicate_decision") is True else "PASSED" if duplicate_check else "NOT_REPORTED"),
            "cooldown_status": "COOLDOWN_ACTIVE" if duplicate_check.get("cooldown_active") is True else "READY",
            "order_build_status": result.get("order_build_status") or ("ORDER_BUILD_ATTEMPTED" if order_build_attempted else "NOT_ATTEMPTED"),
            "order_send_status": result.get("order_send_status") or ("ORDER_SEND_SUCCEEDED" if sent else "ORDER_SEND_FAILED" if order_send_attempted else "NOT_ATTEMPTED"),
            "final_rejection_reason": "" if sent else str(final_reason),
            "blockers": blockers,
            "retcode": result.get("retcode") or result.get("final_retcode"),
            "comment": result.get("final_comment") or result.get("comment") or result.get("reason"),
            "timestamp": self._timestamp(),
        }
        self._execution_timelines = (self._execution_timelines + [timeline])[-100:]
        self._log("POST_SENDER_EXECUTION_TRACE", timeline)
        return timeline

    def _apply_execution_stage_counters(self, result: dict[str, Any]) -> None:
        sent = result.get("status") == "DEMO_ORDER_SENT" and result.get("mt5_order_sent") is True
        approval_passed = result.get("approval_workflow_passed") is True
        guarded_attempted = result.get("guarded_sender_attempted") is True or (result.get("guarded_sender_used") is True and result.get("approval_workflow_passed") is True)
        order_send_attempted = result.get("order_send_attempted") is True or result.get("demo_order_attempted") is True or sent
        if approval_passed:
            self._increment_funnel("approval_workflow_passed")
        if guarded_attempted:
            self._increment_funnel("guarded_sender_attempted")
            self._increment_funnel("signals_sent_to_sender")
        if order_send_attempted:
            self._increment_funnel("order_send_attempted")
        if order_send_attempted and not sent:
            self._increment_funnel("order_send_failed")

    def _dominant_post_sender_blocker(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for item in self._execution_timelines:
            reason = str(item.get("final_rejection_reason") or "").strip()
            if not reason:
                continue
            counts[reason] = counts.get(reason, 0) + 1
        if not counts:
            return {"reason": "", "count": 0}
        reason, count = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[0]
        return {"reason": reason, "count": count}

    def _hash_change_audit(self, original: dict[str, Any], current: dict[str, Any] | None) -> dict[str, Any]:
        original_hash = str(original.get("signal_hash") or "")
        current_hash = str((current or {}).get("signal_hash") or "")
        if not current or current_hash == original_hash:
            return {"changed": False, "original_hash": original_hash, "current_hash": current_hash}
        fields = [
            ("entry", ["entry"]),
            ("stop_loss", ["stop_loss"]),
            ("take_profit", ["take_profit"]),
            ("confidence", ["confidence"]),
            ("trend_alignment", ["market_structure_state", "trend_bias"]),
            ("BOS", ["strategy_components", "bos"]),
            ("liquidity_sweep", ["strategy_components", "liquidity_sweep"]),
            ("order_block", ["strategy_components", "order_block"]),
            ("FVG", ["strategy_components", "fvg"]),
            ("session", ["strategy_components", "session"]),
            ("session_valid", ["strategy_components", "session_valid"]),
            ("signal_direction", ["signal"]),
            ("rr", ["risk_reward"]),
            ("status_level", ["status_level"]),
            ("execution_status", ["execution_status"]),
            ("risk_status", ["risk_status"]),
        ]
        changed_fields: list[dict[str, Any]] = []
        for label, path in fields:
            original_value = self._nested(original, path)
            current_value = self._nested(current, path)
            if original_value != current_value:
                changed_fields.append({"field": label, "original": original_value, "current": current_value})
        spread_original = original.get("spread")
        spread_current = current.get("spread")
        if spread_original != spread_current:
            changed_fields.append({"field": "spread", "original": spread_original, "current": spread_current})
        auto_profile = str(original.get("strategy_profile") or current.get("strategy_profile") or self.config.get("strategy_profile") or "").upper() in {"AUTO_VALIDATION", "DEMO_COLLECTION"}
        if auto_profile:
            classification = self._auto_validation_hash_classification(original, current, changed_fields)
            informational = bool(classification["minor_change"])
            minor_change = bool(classification["minor_change"])
            material_reasons = classification["material_reasons"]
        else:
            informational = self._informational_hash_change_only(changed_fields)
            minor_change = False
            material_reasons = [] if informational else ["PRODUCTION_HASH_CHANGED"]
        return {
            "changed": True,
            "informational_only": informational,
            "minor_change": minor_change,
            "event": "HASH_CHANGE_MINOR" if minor_change else "SIGNAL_HASH_CHANGED",
            "material_reasons": material_reasons,
            "original_hash": original_hash,
            "current_hash": current_hash,
            "changed_fields": changed_fields,
            "original_signal_timestamp": original.get("timestamp"),
            "revalidation_timestamp": current.get("timestamp") or self._timestamp(),
            "root_cause": self._hash_root_cause(changed_fields, informational, material_reasons),
        }

    def _auto_validation_hash_classification(self, original: dict[str, Any], current: dict[str, Any], changed_fields: list[dict[str, Any]]) -> dict[str, Any]:
        material: list[str] = []
        original_direction = str(original.get("signal") or "").upper()
        current_direction = str(current.get("signal") or "").upper()
        if original_direction in {"BUY", "SELL"} and current_direction in {"BUY", "SELL"} and original_direction != current_direction:
            material.append("SIGNAL_DIRECTION_CHANGED")
        if self._number(original.get("stop_loss"), 0) != self._number(current.get("stop_loss"), 0):
            material.append("STOP_LOSS_CHANGED")
        if current_direction not in {"BUY", "SELL"}:
            material.append("SETUP_BECAME_WAIT_OR_REJECTED")
        if str(current.get("execution_status") or "").upper() != "READY_FOR_PREVIEW" or str(current.get("risk_status") or "").upper() != "APPROVED":
            material.append("SETUP_BECAME_WAIT_OR_REJECTED")
        if str(current.get("status_level") or "").upper() in {"WAIT", "REJECTED"}:
            material.append("SETUP_BECAME_WAIT_OR_REJECTED")
        components = current.get("strategy_components") if isinstance(current.get("strategy_components"), dict) else {}
        profile = str(original.get("strategy_profile") or current.get("strategy_profile") or self.config.get("strategy_profile") or "").upper()
        if components.get("session_valid") is False and profile != "DEMO_COLLECTION":
            material.append("SESSION_INVALID")
        if self._number(current.get("risk_reward"), 0) < float(self.config.get("min_rr", 1.5)):
            material.append("RR_BELOW_THRESHOLD")
        if self._number(current.get("confidence"), 0) < float(self.config.get("min_confidence", 65)):
            material.append("CONFIDENCE_BELOW_PROFILE_THRESHOLD")

        allowed_minor_fields = {"entry", "take_profit", "confidence", "spread"}
        changed_names = {str(item.get("field")) for item in changed_fields}
        unknown_material = sorted(changed_names - allowed_minor_fields - {"signal_direction", "stop_loss", "session_valid", "rr", "status_level", "execution_status", "risk_status"})
        if unknown_material:
            material.append("TRACKED_SETUP_FIELD_CHANGED")

        return {
            "minor_change": bool(changed_fields) and not material and changed_names.issubset(allowed_minor_fields),
            "material_reasons": sorted(set(material)),
        }

    def _informational_hash_change_only(self, changed_fields: list[dict[str, Any]]) -> bool:
        if not changed_fields:
            return True
        allowed = {"confidence", "spread"}
        for item in changed_fields:
            field = item.get("field")
            if field not in allowed:
                return False
            original = self._number(item.get("original"), 0)
            current = self._number(item.get("current"), 0)
            if field == "confidence" and abs(current - original) > 2:
                return False
            if field == "spread" and abs(current - original) > max(abs(original) * 0.25, 0.0001):
                return False
        return True

    def _hash_root_cause(self, changed_fields: list[dict[str, Any]], informational: bool, material_reasons: list[str] | None = None) -> str:
        if not changed_fields:
            return "Signal hash changed but tracked execution fields are unchanged."
        names = ", ".join(str(item.get("field")) for item in changed_fields)
        if informational:
            prefix = "HASH_CHANGE_MINOR"
        else:
            reasons = ", ".join(material_reasons or ["material setup field changed"])
            prefix = f"Material signal revalidation change ({reasons})"
        return f"{prefix}: {names} changed."

    def _nested(self, payload: dict[str, Any], path: list[str]) -> Any:
        value: Any = payload
        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    def _adaptive_level_definitions(self) -> dict[int, dict[str, Any]]:
        return {
            0: {
                "name": "Balanced Preferred",
                "required_score": 6,
                "preferred_score": 6,
                "strong_required": 2,
                "requires_balanced_entry": True,
                "passed_rule": "BALANCED_ENTRY_REQUIREMENT_MET",
                "failed_rule": "BALANCED_ENTRY_REQUIREMENT_MISSING",
            },
            1: {
                "name": "Balanced Active",
                "required_score": 5,
                "preferred_score": 6,
                "strong_required": 2,
                "requires_balanced_entry": True,
                "passed_rule": "BALANCED_ENTRY_REQUIREMENT_MET",
                "failed_rule": "BALANCED_ENTRY_REQUIREMENT_MISSING",
            },
            2: {
                "name": "Balanced Active",
                "required_score": 5,
                "preferred_score": 6,
                "strong_required": 2,
                "requires_balanced_entry": True,
                "passed_rule": "BALANCED_ENTRY_REQUIREMENT_MET",
                "failed_rule": "BALANCED_ENTRY_REQUIREMENT_MISSING",
            },
            3: {
                "name": "Balanced Active",
                "required_score": 5,
                "preferred_score": 6,
                "strong_required": 2,
                "requires_balanced_entry": True,
                "passed_rule": "BALANCED_ENTRY_REQUIREMENT_MET",
                "failed_rule": "BALANCED_ENTRY_REQUIREMENT_MISSING",
            },
        }

    def _adaptive_level_config(self, level: int | None = None, symbol: str | None = None) -> dict[str, Any]:
        definitions = self._adaptive_level_definitions()
        safe_level = max(0, min(3, int(level if level is not None else self._current_adaptive_strategy_level(symbol))))
        return {**definitions[safe_level], "level": safe_level}

    def _empty_adaptive_strategy_levels(self, activation_time: str | None = None) -> dict[str, dict[str, Any]]:
        levels: dict[str, dict[str, Any]] = {}
        for level, definition in self._adaptive_level_definitions().items():
            levels[str(level)] = {
                "level": level,
                "name": definition["name"],
                "status": "Not Reached" if level > 0 else "Active",
                "open": 0,
                "closed": 0,
                "wins": 0,
                "losses": 0,
                "net_pnl": 0.0,
                "reached": level == 0,
                "activation_time": activation_time if level == 0 else None,
                "last_trade_activity_time": None,
            }
        return levels

    def _empty_symbol_adaptive_state(self, symbol: str, level: int = 0, activation_time: str | None = None, last_activity_time: str | None = None) -> dict[str, Any]:
        safe_level = max(0, min(3, int(level or 0)))
        timestamp = activation_time or last_activity_time or self._timestamp()
        levels = self._empty_adaptive_strategy_levels(timestamp)
        for key, item in levels.items():
            numeric = int(key)
            item["reached"] = numeric <= safe_level
            item["status"] = "Active" if numeric == safe_level else ("Not Worked" if numeric <= safe_level else "Not Reached")
            item["activation_time"] = timestamp if numeric == safe_level or numeric == 0 else None
            item["last_trade_activity_time"] = last_activity_time if numeric == safe_level else None
        return {
            "symbol": symbol,
            "current_level": safe_level,
            "activation_time": timestamp,
            "last_activity_time": last_activity_time or timestamp,
            "open": 0,
            "closed": 0,
            "wins": 0,
            "losses": 0,
            "net_pnl": 0.0,
            "levels": levels,
            "history": [],
        }

    def _ensure_adaptive_strategy_state(self) -> None:
        now = self._timestamp()
        started = str(self.session.get("session_start_time") or self.session.get("started_at") or now)
        level = max(0, min(3, int(self.session.get("current_strategy_level") or 0)))
        self.session["current_strategy_level"] = level
        if not self.session.get("adaptive_level_activation_time"):
            self.session["adaptive_level_activation_time"] = started
        if not self.session.get("last_trade_activity_time"):
            self.session["last_trade_activity_time"] = started
        if not isinstance(self.session.get("adaptive_strategy_levels"), dict):
            self.session["adaptive_strategy_levels"] = self._empty_adaptive_strategy_levels(str(self.session.get("adaptive_level_activation_time") or started))
        if not isinstance(self.session.get("adaptive_strategy_history"), list):
            self.session["adaptive_strategy_history"] = []
        levels = self.session["adaptive_strategy_levels"]
        for key, definition in self._adaptive_level_definitions().items():
            item = levels.get(str(key)) if isinstance(levels.get(str(key)), dict) else {}
            reached = bool(item.get("reached")) or key <= level
            item.update(
                {
                    "level": key,
                    "name": definition["name"],
                    "open": int(item.get("open") or 0),
                    "closed": int(item.get("closed") or 0),
                    "reached": reached,
                    "status": "Active" if key == level else ("Worked" if int(item.get("open") or 0) + int(item.get("closed") or 0) > 0 else ("Not Worked" if reached else "Not Reached")),
                    "activation_time": item.get("activation_time") or (self.session.get("adaptive_level_activation_time") if key == level else (started if key == 0 else None)),
                    "last_trade_activity_time": item.get("last_trade_activity_time") or (self.session.get("last_trade_activity_time") if key == level else None),
                }
            )
            levels[str(key)] = item

        symbol_state = self.session.get("symbol_adaptive_state") if isinstance(self.session.get("symbol_adaptive_state"), dict) else {}
        migrated_state: dict[str, Any] = {}
        allowed_symbols = sorted(self._allowed_symbols() or {"EURUSD", "XAUUSD"})
        global_levels = self.session.get("adaptive_strategy_levels") if isinstance(self.session.get("adaptive_strategy_levels"), dict) else {}
        global_history = self.session.get("adaptive_strategy_history") if isinstance(self.session.get("adaptive_strategy_history"), list) else []
        for symbol in allowed_symbols:
            raw_item = symbol_state.get(symbol) if isinstance(symbol_state.get(symbol), dict) else {}
            if raw_item:
                symbol_level = max(0, min(3, int(raw_item.get("current_level") if raw_item.get("current_level") is not None else raw_item.get("level") or 0)))
                activation_time = str(raw_item.get("activation_time") or started)
                last_activity = str(raw_item.get("last_activity_time") or raw_item.get("last_trade_activity_time") or activation_time)
                item_levels = raw_item.get("levels") if isinstance(raw_item.get("levels"), dict) else self._empty_adaptive_strategy_levels(activation_time)
                history = raw_item.get("history") if isinstance(raw_item.get("history"), list) else []
            else:
                inherit_global = symbol == "EURUSD" and not symbol_state
                symbol_level = level if inherit_global else 0
                activation_time = str(self.session.get("adaptive_level_activation_time") or started) if inherit_global else started
                last_activity = str(self.session.get("last_trade_activity_time") or activation_time) if inherit_global else started
                item_levels = copy.deepcopy(global_levels) if inherit_global and global_levels else self._empty_adaptive_strategy_levels(activation_time)
                history = [entry for entry in global_history if isinstance(entry, dict) and str(entry.get("symbol") or symbol).upper() == symbol] if inherit_global else []
            normalized_levels: dict[str, dict[str, Any]] = {}
            for key, definition in self._adaptive_level_definitions().items():
                existing = item_levels.get(str(key)) if isinstance(item_levels.get(str(key)), dict) else {}
                reached = bool(existing.get("reached")) or key <= symbol_level
                open_count = int(existing.get("open") or 0)
                closed_count = int(existing.get("closed") or 0)
                worked = open_count + closed_count > 0
                normalized_levels[str(key)] = {
                    "level": key,
                    "name": definition["name"],
                    "status": "Active" if key == symbol_level else ("Worked" if worked else ("Not Worked" if reached else "Not Reached")),
                    "open": open_count,
                    "closed": closed_count,
                    "wins": int(existing.get("wins") or 0),
                    "losses": int(existing.get("losses") or 0),
                    "net_pnl": round(float(existing.get("net_pnl") or 0.0), 2),
                    "reached": reached,
                    "activation_time": existing.get("activation_time") or (activation_time if key == symbol_level or key == 0 else None),
                    "last_trade_activity_time": existing.get("last_trade_activity_time") or (last_activity if key == symbol_level else None),
                }
            migrated_state[symbol] = {
                "symbol": symbol,
                "current_level": symbol_level,
                "activation_time": activation_time,
                "last_activity_time": last_activity,
                "open": int(raw_item.get("open") or 0) if raw_item else 0,
                "closed": int(raw_item.get("closed") or 0) if raw_item else 0,
                "wins": int(raw_item.get("wins") or 0) if raw_item else 0,
                "losses": int(raw_item.get("losses") or 0) if raw_item else 0,
                "net_pnl": round(float(raw_item.get("net_pnl") or 0.0), 2) if raw_item else 0.0,
                "levels": normalized_levels,
                "history": history[-100:],
            }
        self.session["symbol_adaptive_state"] = migrated_state
        self._sync_global_adaptive_mirror()

    def _sync_global_adaptive_mirror(self) -> None:
        state = self.session.get("symbol_adaptive_state") if isinstance(self.session.get("symbol_adaptive_state"), dict) else {}
        if not state:
            return
        levels = [int(item.get("current_level") or 0) for item in state.values() if isinstance(item, dict)]
        mirror_level = max(levels) if levels else 0
        self.session["current_strategy_level"] = mirror_level
        active_symbols = [item for item in state.values() if isinstance(item, dict) and int(item.get("current_level") or 0) == mirror_level]
        mirror = active_symbols[0] if active_symbols else next(iter(state.values()))
        if isinstance(mirror, dict):
            self.session["last_trade_activity_time"] = mirror.get("last_activity_time") or self.session.get("last_trade_activity_time")
            self.session["adaptive_level_activation_time"] = mirror.get("activation_time") or self.session.get("adaptive_level_activation_time")

    def _symbol_adaptive_state(self, symbol: str | None) -> dict[str, Any]:
        self._ensure_adaptive_strategy_state()
        normalized = str(symbol or "").upper()
        state = self.session.get("symbol_adaptive_state") if isinstance(self.session.get("symbol_adaptive_state"), dict) else {}
        if normalized and normalized in state and isinstance(state[normalized], dict):
            return state[normalized]
        fallback_symbol = sorted(state.keys())[0] if state else ""
        return state.get(fallback_symbol, {}) if fallback_symbol else {}

    def _current_adaptive_strategy_level(self, symbol: str | None = None) -> int:
        self._ensure_adaptive_strategy_state()
        if symbol:
            state = self.session.get("symbol_adaptive_state") if isinstance(self.session.get("symbol_adaptive_state"), dict) else {}
            item = state.get(str(symbol).upper()) if isinstance(state.get(str(symbol).upper()), dict) else {}
            return int(item.get("current_level") or 0)
        return int(self.session.get("current_strategy_level") or 0)

    def _adaptive_last_activity_at(self, symbol: str | None = None) -> datetime | None:
        if symbol:
            state = self._symbol_adaptive_state(symbol)
            value = state.get("last_activity_time") or state.get("last_trade_activity_time") or self.session.get("session_start_time") or self.session.get("started_at")
        else:
            value = self.session.get("last_trade_activity_time") or self.session.get("session_start_time") or self.session.get("started_at")
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _adaptive_level_specific_passed(self, confirmations: dict[str, Any], level_config: dict[str, Any]) -> bool:
        states = confirmations.get("states") if isinstance(confirmations.get("states"), dict) else {}
        if int(level_config.get("level") or 0) == 3:
            structure = bool(states.get("BOS") or states.get("LIQUIDITY_SWEEP"))
            return bool(states.get("HTF_ALIGNMENT")) and bool(states.get("MOMENTUM_DISPLACEMENT")) and structure and bool(states.get("RR_2_0")) and bool(states.get("SPREAD_CLEAN"))
        if level_config.get("requires_balanced_entry"):
            momentum_or_pullback = bool(states.get("MOMENTUM_DISPLACEMENT") or states.get("PULLBACK_RETEST"))
            structure = bool(states.get("BOS") or states.get("LIQUIDITY_SWEEP") or states.get("FVG_RETEST"))
            return bool(states.get("HTF_ALIGNMENT")) and bool(states.get("RR_2_0")) and bool(states.get("SPREAD_CLEAN")) and momentum_or_pullback and structure
        return True

    def _maybe_advance_all_adaptive_strategy_levels(self) -> None:
        self._ensure_adaptive_strategy_state()
        for symbol in sorted(self._allowed_symbols() or set()):
            self._maybe_advance_adaptive_strategy_level(symbol)
        self._sync_global_adaptive_mirror()

    def _maybe_advance_adaptive_strategy_level(self, symbol: str | None = None) -> None:
        if self.session.get("status") not in {"RUNNING", "WAITING_FOR_MT5_HISTORY_SYNC", "WAITING_FOR_MT5_RECONNECT"}:
            self._ensure_adaptive_strategy_state()
            return
        self._ensure_adaptive_strategy_state()
        normalized_symbol = str(symbol or "EURUSD").upper()
        state = self.session.get("symbol_adaptive_state") if isinstance(self.session.get("symbol_adaptive_state"), dict) else {}
        item = state.get(normalized_symbol) if isinstance(state.get(normalized_symbol), dict) else self._empty_symbol_adaptive_state(normalized_symbol)
        level = int(item.get("current_level") or 0)
        if level >= 3:
            return
        last_activity = self._adaptive_last_activity_at(normalized_symbol)
        if last_activity is None:
            item["last_activity_time"] = self._timestamp()
            state[normalized_symbol] = item
            self.session["symbol_adaptive_state"] = state
            return
        now = datetime.now(timezone.utc)
        inactivity_minutes = float(self.config.get("adaptive_inactivity_minutes") or 45)
        if now < last_activity + timedelta(minutes=inactivity_minutes):
            return
        new_level = min(3, level + 1)
        timestamp = self._timestamp()
        item["current_level"] = new_level
        item["activation_time"] = timestamp
        item["last_activity_time"] = timestamp
        levels = item.get("levels") if isinstance(item.get("levels"), dict) else self._empty_adaptive_strategy_levels(timestamp)
        level_item = levels.get(str(new_level)) if isinstance(levels.get(str(new_level)), dict) else {}
        level_item.update({"reached": True, "status": "Active", "activation_time": timestamp, "last_trade_activity_time": timestamp})
        levels[str(new_level)] = level_item
        for key, existing in levels.items():
            if key != str(new_level) and isinstance(existing, dict) and existing.get("status") == "Active":
                existing["status"] = "Worked" if int(existing.get("open") or 0) + int(existing.get("closed") or 0) > 0 else "Not Worked"
        item["levels"] = levels
        state[normalized_symbol] = item
        self.session["symbol_adaptive_state"] = state
        self._ensure_adaptive_strategy_state()
        history = self.session.get("adaptive_strategy_history") if isinstance(self.session.get("adaptive_strategy_history"), list) else []
        entry = {
            "event": "ADAPTIVE_LEVEL_ADVANCED",
            "symbol": normalized_symbol,
            "from_level": level,
            "to_level": new_level,
            "reason": "45 minutes without an opened or closed trade for this symbol.",
            "timestamp": timestamp,
        }
        history.append(entry)
        self.session["adaptive_strategy_history"] = history[-100:]
        symbol_history = item.get("history") if isinstance(item.get("history"), list) else []
        symbol_history.append(entry)
        item["history"] = symbol_history[-100:]
        state[normalized_symbol] = item
        self.session["symbol_adaptive_state"] = state
        self._log(
            "ADAPTIVE_LEVEL_ADVANCED",
            {
                "symbol": normalized_symbol,
                "from_level": level,
                "to_level": new_level,
                "reason": "45_MINUTES_SYMBOL_INACTIVITY",
                "message": f"{normalized_symbol} Adaptive Level {new_level} active after 45 minutes without opened or closed activity.",
            },
        )

    def _record_adaptive_trade_activity(self, activity: str, details: dict[str, Any] | None = None) -> None:
        self._ensure_adaptive_strategy_state()
        symbol = str((details or {}).get("symbol") or "EURUSD").upper()
        state = self.session.get("symbol_adaptive_state") if isinstance(self.session.get("symbol_adaptive_state"), dict) else {}
        symbol_state = state.get(symbol) if isinstance(state.get(symbol), dict) else self._empty_symbol_adaptive_state(symbol)
        level = int(symbol_state.get("current_level") or 0)
        timestamp = str((details or {}).get("closed_at") or (details or {}).get("opened_at") or self._timestamp())
        symbol_state["last_activity_time"] = timestamp
        levels = symbol_state.get("levels") if isinstance(symbol_state.get("levels"), dict) else {}
        item = levels.get(str(level)) if isinstance(levels.get(str(level)), dict) else {}
        if activity == "OPENED":
            item["open"] = int(item.get("open") or 0) + 1
        elif activity == "CLOSED":
            item["closed"] = int(item.get("closed") or 0) + 1
            pnl = self._number((details or {}).get("pnl") or (details or {}).get("profit_loss"), 0)
            item["net_pnl"] = round(float(item.get("net_pnl") or 0.0) + float(pnl or 0.0), 2)
            result = str((details or {}).get("result") or "").upper()
            if result == "WIN" or float(pnl or 0.0) > 0:
                item["wins"] = int(item.get("wins") or 0) + 1
            elif result == "LOSS" or float(pnl or 0.0) < 0:
                item["losses"] = int(item.get("losses") or 0) + 1
        item["last_trade_activity_time"] = timestamp
        item["status"] = "Active"
        item["reached"] = True
        levels[str(level)] = item
        symbol_state["levels"] = levels
        symbol_state["open"] = sum(int(entry.get("open") or 0) for entry in levels.values() if isinstance(entry, dict))
        symbol_state["closed"] = sum(int(entry.get("closed") or 0) for entry in levels.values() if isinstance(entry, dict))
        symbol_state["wins"] = sum(int(entry.get("wins") or 0) for entry in levels.values() if isinstance(entry, dict))
        symbol_state["losses"] = sum(int(entry.get("losses") or 0) for entry in levels.values() if isinstance(entry, dict))
        symbol_state["net_pnl"] = round(sum(float(entry.get("net_pnl") or 0.0) for entry in levels.values() if isinstance(entry, dict)), 2)
        state[symbol] = symbol_state
        self.session["symbol_adaptive_state"] = state
        self._sync_global_adaptive_mirror()
        history = self.session.get("adaptive_strategy_history") if isinstance(self.session.get("adaptive_strategy_history"), list) else []
        history_entry = {
            "event": f"ADAPTIVE_TRADE_{activity}",
            "level": level,
            "ticket": (details or {}).get("ticket") or (details or {}).get("mt5_ticket"),
            "symbol": symbol,
            "timestamp": timestamp,
        }
        history.append(history_entry)
        self.session["adaptive_strategy_history"] = history[-100:]
        symbol_history = symbol_state.get("history") if isinstance(symbol_state.get("history"), list) else []
        symbol_history.append(history_entry)
        symbol_state["history"] = symbol_history[-100:]
        state[symbol] = symbol_state
        self.session["symbol_adaptive_state"] = state

    def _adaptive_level_for_trade(self, trade: dict[str, Any]) -> int | None:
        candidates = [
            trade.get("adaptive_strategy_level"),
            trade.get("adaptive_level"),
        ]
        metadata = trade.get("strategy_metadata") if isinstance(trade.get("strategy_metadata"), dict) else {}
        approval = metadata.get("approval_audit") if isinstance(metadata.get("approval_audit"), dict) else {}
        diagnostics = metadata.get("round3_diagnostics") if isinstance(metadata.get("round3_diagnostics"), dict) else {}
        candidates.extend([approval.get("adaptive_level"), diagnostics.get("adaptive_level"), diagnostics.get("current_strategy_level")])
        for value in candidates:
            try:
                level = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= level <= 3:
                return level
        return None

    def _refresh_adaptive_strategy_level_stats(self, open_trades: list[dict[str, Any]], closed_trades: list[dict[str, Any]]) -> None:
        self._ensure_adaptive_strategy_state()
        state = self.session.get("symbol_adaptive_state") if isinstance(self.session.get("symbol_adaptive_state"), dict) else {}
        refreshed_state: dict[str, Any] = {}
        started = str(self.session.get("started_at") or self.session.get("session_start_time") or self._timestamp())
        for symbol in sorted(self._allowed_symbols() or set()):
            previous_symbol = state.get(symbol) if isinstance(state.get(symbol), dict) else self._empty_symbol_adaptive_state(symbol, 0, started, started)
            current_level = int(previous_symbol.get("current_level") or 0)
            refreshed = self._empty_adaptive_strategy_levels(str(previous_symbol.get("activation_time") or started))
            previous_levels = previous_symbol.get("levels") if isinstance(previous_symbol.get("levels"), dict) else {}
            for key, item in refreshed.items():
                previous = previous_levels.get(key) if isinstance(previous_levels.get(key), dict) else {}
                item["reached"] = bool(previous.get("reached")) or int(key) <= current_level
                item["activation_time"] = previous.get("activation_time") or item.get("activation_time")
                item["last_trade_activity_time"] = previous.get("last_trade_activity_time") or (previous_symbol.get("last_activity_time") if int(key) == current_level else None)
                item["wins"] = 0
                item["losses"] = 0
                item["net_pnl"] = 0.0
            refreshed_state[symbol] = {
                **previous_symbol,
                "symbol": symbol,
                "current_level": current_level,
                "levels": refreshed,
                "open": 0,
                "closed": 0,
                "wins": 0,
                "losses": 0,
                "net_pnl": 0.0,
            }
        for trade in open_trades:
            symbol = str(trade.get("symbol") or "").upper()
            if symbol not in refreshed_state:
                continue
            level = self._adaptive_level_for_trade(trade)
            if level is None:
                level = int(refreshed_state[symbol].get("current_level") or 0)
            level_item = refreshed_state[symbol]["levels"][str(level)]
            level_item["open"] = int(level_item.get("open") or 0) + 1
            level_item["reached"] = True
            refreshed_state[symbol]["open"] = int(refreshed_state[symbol].get("open") or 0) + 1
        for trade in closed_trades:
            symbol = str(trade.get("symbol") or "").upper()
            if symbol not in refreshed_state:
                continue
            level = self._adaptive_level_for_trade(trade)
            if level is None:
                level = int(refreshed_state[symbol].get("current_level") or 0)
            level_item = refreshed_state[symbol]["levels"][str(level)]
            pnl = self._trade_pnl(trade)
            result = str(trade.get("result") or "").upper()
            level_item["closed"] = int(level_item.get("closed") or 0) + 1
            level_item["net_pnl"] = round(float(level_item.get("net_pnl") or 0.0) + pnl, 2)
            if result == "WIN" or pnl > 0:
                level_item["wins"] = int(level_item.get("wins") or 0) + 1
                refreshed_state[symbol]["wins"] = int(refreshed_state[symbol].get("wins") or 0) + 1
            elif result == "LOSS" or pnl < 0:
                level_item["losses"] = int(level_item.get("losses") or 0) + 1
                refreshed_state[symbol]["losses"] = int(refreshed_state[symbol].get("losses") or 0) + 1
            level_item["reached"] = True
            refreshed_state[symbol]["closed"] = int(refreshed_state[symbol].get("closed") or 0) + 1
            refreshed_state[symbol]["net_pnl"] = round(float(refreshed_state[symbol].get("net_pnl") or 0.0) + pnl, 2)
        for symbol, symbol_state in refreshed_state.items():
            current_level = int(symbol_state.get("current_level") or 0)
            levels = symbol_state.get("levels") if isinstance(symbol_state.get("levels"), dict) else {}
            for key, item in levels.items():
                level = int(key)
                worked = int(item.get("open") or 0) + int(item.get("closed") or 0) > 0
                item["status"] = "Active" if level == current_level else ("Worked" if worked else ("Not Worked" if item.get("reached") else "Not Reached"))
        self.session["symbol_adaptive_state"] = refreshed_state
        mirror_symbol = "EURUSD" if "EURUSD" in refreshed_state else (next(iter(refreshed_state.keys())) if refreshed_state else "")
        if mirror_symbol:
            self.session["adaptive_strategy_levels"] = copy.deepcopy(refreshed_state[mirror_symbol].get("levels") or {})
        self._sync_global_adaptive_mirror()

    def _empty_session(self) -> dict[str, Any]:
        return {
            "session_id": "",
            "started_at": None,
            "stopped_at": None,
            "status": "IDLE",
            "target_closed_trades": 30,
            "target_validation_trades": 30,
            "session_started_by": "",
            "session_start_time": None,
            "round_label": "",
            "session_note": "",
            "client_dashboard_scope": "CURRENT_SESSION_ONLY",
            "current_session_total_trades": 0,
            "current_closed_trades": 0,
            "current_session_closed": 0,
            "current_open_trades": 0,
            "current_session_open_trades": 0,
            "open_trades": 0,
            "current_session_opened": 0,
            "daily_demo_trade_count": 0,
            "remaining_trades_to_target": 30,
            "remaining_closed_trades": 30,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "net_pnl": 0.0,
            "avg_rr": 0.0,
            "average_rr": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "best_setup_type": "Unavailable",
            "worst_setup_type": "Unavailable",
            "equity_curve": [],
            "reason_stopped": "",
            "paused_reason": "",
            "last_mt5_disconnect_at": None,
            "mt5_disconnect_recovered_at": None,
            "mt5_reconnect_attempts": 0,
            "signals_scanned": 0,
            "signals_wait": 0,
            "signals_watchlist": 0,
            "signals_ready_for_preview": 0,
            "signals_sent_to_sender": 0,
            "signals_blocked_by_sender": 0,
            "orders_created": 0,
            "wrapper_submitted": 0,
            "approval_workflow_passed": 0,
            "guarded_sender_attempted": 0,
            "opened": 0,
            "order_build_attempted": 0,
            "order_build_failed": 0,
            "order_send_attempted": 0,
            "order_send_failed": 0,
            "history_ready": False,
            "history_status": "NOT_STARTED",
            "latest_decision_trace": None,
            "decision_traces": [],
            "current_strategy_level": 0,
            "last_trade_activity_time": None,
            "adaptive_level_activation_time": None,
            "adaptive_strategy_levels": self._empty_adaptive_strategy_levels(None),
            "adaptive_strategy_history": [],
            "symbol_adaptive_state": {},
        }

    def _fresh_empty_active_session(self, reason: str) -> None:
        started_at = self._timestamp()
        target = int(self.config.get("target_validation_trades") or self.config.get("target_closed_trades") or 30)
        self.session = {
            **self._empty_session(),
            "session_id": f"auto-validation-{uuid4()}",
            "started_at": started_at,
            "session_start_time": started_at,
            "last_trade_activity_time": started_at,
            "adaptive_level_activation_time": started_at,
            "status": "READY_ROUND_3",
            "target_closed_trades": target,
            "target_validation_trades": target,
            "session_started_by": "system_fresh_empty",
            "round_label": "ROUND_3",
            "session_note": "Fresh empty Round 3 session created because no active session was persisted.",
            "client_dashboard_scope": "CURRENT_SESSION_ONLY",
            "remaining_trades_to_target": target,
            "remaining_closed_trades": target,
            "progress_percentage": 0.0,
        }
        self._ensure_adaptive_strategy_state()
        self._startup_session_diagnostics = {
            "active_session_id": self.session["session_id"],
            "recovered_session_id": "",
            "dashboard_session_id": self.session["session_id"],
            "startup_recovery_action": "CREATED_FRESH_EMPTY_SESSION",
            "startup_recovery_reason": reason,
            "timestamp": started_at,
        }
        self._log(
            "ACTIVE_SESSION_INITIALIZED",
            {
                "active_session_id": self.session["session_id"],
                "recovered_session_id": "",
                "dashboard_session_id": self.session["session_id"],
                "reason": reason,
                "closed_trades": 0,
                "wins": 0,
                "losses": 0,
                "net_pnl": 0.0,
            },
        )

    def _finalize_loaded_active_session(self, reason: str) -> None:
        session_id = str(self.session.get("session_id") or "")
        if not session_id:
            self._fresh_empty_active_session(reason)
            self._save_state()
            return
        self._startup_session_diagnostics = {
            "active_session_id": session_id,
            "recovered_session_id": "",
            "dashboard_session_id": session_id,
            "startup_recovery_action": "PRESERVED_ACTIVE_SESSION",
            "startup_recovery_reason": reason,
            "timestamp": self._timestamp(),
        }
        self._save_state()

    def _load_state(self) -> None:
        try:
            if not self.state_path.exists():
                self._fresh_empty_active_session("state_file_missing")
                return
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._fresh_empty_active_session("state_file_unreadable")
            return
        if isinstance(data.get("config"), dict):
            self.config = {**self._default_config(), **data["config"]}
            self.config["strategy_profile"] = self._normalize_profile(self.config.get("strategy_profile"))
            if self.config["strategy_profile"] == "DEMO_COLLECTION":
                self.config["min_confidence"] = 55
                self.config["min_rr"] = 2.0
                self.config["target_validation_trades"] = 30
                self.config["target_closed_trades"] = 30
                self.config["max_open_trades_total"] = 5
                self.config["max_open_trades_per_symbol"] = 3
                self.config["max_daily_demo_trades"] = 30
                self.config["max_daily_trades"] = 30
                self.config["break_even_trigger_r"] = 0.8
                self.config["trailing_stop_trigger_r"] = 1.2
                self.config["exit_stale_minutes"] = max(180, int(self.config.get("exit_stale_minutes") or 180))
                self.config["exit_soft_adverse_minutes"] = max(180, int(self.config.get("exit_soft_adverse_minutes") or 180))
                self.config["exit_no_progress_minutes"] = max(180, int(self.config.get("exit_no_progress_minutes") or 180))
                self.config["exit_no_progress_min_r"] = float(self.config.get("exit_no_progress_min_r") or 0.3)
                for settings in (self.config.get("per_symbol_exit_settings") or {}).values():
                    if isinstance(settings, dict):
                        settings["break_even_trigger_r"] = 0.8
                        settings["trailing_stop_trigger_r"] = 1.2
                        settings["stale_exit_minutes"] = max(180, int(settings.get("stale_exit_minutes") or 180))
                        settings["soft_adverse_minutes"] = max(180, int(settings.get("soft_adverse_minutes") or 180))
                        settings["no_progress_minutes"] = max(180, int(settings.get("no_progress_minutes") or 180))
                        settings["no_progress_min_r"] = float(settings.get("no_progress_min_r") or 0.3)
            elif self.config["strategy_profile"] == "AUTO_VALIDATION":
                self.config["min_confidence"] = 65
                self.config["min_rr"] = 1.5
                self.config["max_open_trades_total"] = 1
                self.config["max_open_trades_per_symbol"] = 1
            self.config["live_execution_enabled"] = False
            self.config["broker_execution_enabled"] = False
            self.config["history_required_candles"] = max(300, int(self.config.get("history_required_candles") or 300))
            self.config["history_warmup_timeframes"] = [
                str(timeframe).upper()
                for timeframe in self.config.get("history_warmup_timeframes", ["M15", "H1", "H4"])
                if str(timeframe).upper() in {"M15", "H1", "H4"}
            ] or ["M15", "H1", "H4"]
        if isinstance(data.get("session"), dict):
            self.session = {**self._empty_session(), **data["session"]}
            self._ensure_adaptive_strategy_state()
        active_round = self.round_archive_service.load_active()
        if isinstance(active_round, dict):
            active_session = active_round.get("session") if isinstance(active_round.get("session"), dict) else {}
            active_session_id = str(active_round.get("session_id") or active_session.get("session_id") or "")
            if active_session_id:
                self.session = {**self._empty_session(), **active_session, "session_id": active_session_id}
                self._ensure_adaptive_strategy_state()
                self.session["round_number"] = int(active_round.get("round_number") or self.session.get("round_number") or 0)
                self.session["round_label"] = str(active_round.get("round_label") or self.session.get("round_label") or "")
                if active_round.get("status") == "COMPLETED":
                    self.session["status"] = "COMPLETED"
                    self.config["auto_validation_enabled"] = False
                    self.runner_state = self._empty_runner_state()
        if isinstance(data.get("events"), list):
            self.events = [event for event in data["events"] if isinstance(event, dict)][-500:]
        if isinstance(data.get("last_execution_decision"), dict):
            self._last_execution_decision = data["last_execution_decision"]
        if isinstance(data.get("current_signal_watched"), dict):
            self._current_signal_watched = data["current_signal_watched"]
        if isinstance(data.get("last_hash_change_audit"), dict):
            self._last_hash_change_audit = data["last_hash_change_audit"]
        if isinstance(data.get("last_sender_rejection"), dict):
            self._last_sender_rejection = data["last_sender_rejection"]
        if isinstance(data.get("last_duplicate_check"), dict):
            self._last_duplicate_check = data["last_duplicate_check"]
        if isinstance(data.get("open_position_sync"), dict):
            self._open_position_sync_diagnostics = data["open_position_sync"]
        if isinstance(data.get("lifecycle_sync"), dict):
            self._lifecycle_sync_diagnostics = data["lifecycle_sync"]
        if isinstance(data.get("exit_management"), dict):
            self._exit_management_diagnostics = data["exit_management"]
        if isinstance(data.get("history_warmup"), dict):
            self._history_warmup_diagnostics = data["history_warmup"]
        if isinstance(data.get("startup_session_diagnostics"), dict):
            self._startup_session_diagnostics = data["startup_session_diagnostics"]
        if isinstance(data.get("execution_timelines"), list):
            self._execution_timelines = [item for item in data["execution_timelines"] if isinstance(item, dict)][-100:]
        if isinstance(data.get("validation_close_reports"), list):
            self._validation_close_reports = [item for item in data["validation_close_reports"] if isinstance(item, dict)][-30:]
            self._reported_close_keys = {self._close_report_key(item) for item in self._validation_close_reports if self._close_report_key(item)}
        if isinstance(data.get("sent_signal_keys"), list):
            self._sent_signal_keys = {str(item) for item in data["sent_signal_keys"] if item}
        if isinstance(data.get("confidence_timeline"), dict):
            self._confidence_timeline = data["confidence_timeline"]
        if isinstance(data.get("decision_traces"), list):
            self._decision_traces = [item for item in data["decision_traces"] if isinstance(item, dict)][-200:]
        elif isinstance(self.session.get("decision_traces"), list):
            self._decision_traces = [item for item in self.session["decision_traces"] if isinstance(item, dict)][-200:]
        if self.session.get("status") in {"RUNNING", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC"}:
            updated_at = str(data.get("updated_at") or self.session.get("started_at") or "")
            if not self.config.get("allow_persisted_auto_resume", False):
                self.session["status"] = "PAUSED_REQUIRES_USER_RESUME"
                self.session["paused_reason"] = "PERSISTED_AUTO_RESUME_DISABLED"
                self.session["reason_stopped"] = "PERSISTED_AUTO_RESUME_DISABLED"
                self.config["auto_validation_enabled"] = False
                self.runner_state = self._empty_runner_state()
            elif self._persisted_session_stale(updated_at):
                self.session["status"] = "RECOVERED_STOPPED"
                self.session["paused_reason"] = "STALE_PERSISTED_SESSION_REQUIRES_USER_RESUME"
                self.session["reason_stopped"] = "STALE_PERSISTED_SESSION_REQUIRES_USER_RESUME"
                self.config["auto_validation_enabled"] = False
                self.runner_state = self._empty_runner_state()
            else:
                self.session["session_started_by"] = "persisted_resume"
                self.config["auto_validation_enabled"] = True
        self._finalize_loaded_active_session("state_loaded_without_journal_recovery")

    def _save_state(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "config": self.config,
                "session": self.session,
                "events": self.events[-500:],
                "last_execution_decision": self._last_execution_decision,
                "current_signal_watched": self._current_signal_watched,
                "last_hash_change_audit": self._last_hash_change_audit,
                "last_sender_rejection": self._last_sender_rejection,
                "last_duplicate_check": self._last_duplicate_check,
                "open_position_sync": self._open_position_sync_diagnostics,
                "lifecycle_sync": self._lifecycle_sync_diagnostics,
                "exit_management": self._exit_management_diagnostics,
                "history_warmup": self._history_warmup_diagnostics,
                "startup_session_diagnostics": self._startup_session_diagnostics,
                "validation_close_reports": self._validation_close_reports[-30:],
                "execution_timelines": self._execution_timelines[-100:],
                "confidence_timeline": self._confidence_timeline,
                "decision_traces": self._decision_traces[-200:],
                "sent_signal_keys": sorted(self._sent_signal_keys),
                "updated_at": self._timestamp(),
            }
            self.state_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            self._sync_round_archive()
        except OSError:
            pass

    def _sync_round_archive(self) -> None:
        session_id = str(self.session.get("session_id") or "")
        if not session_id:
            return
        try:
            trades = self.trades()
            if self.journal_service is not None:
                all_trades = self.journal_service.list_trades(limit=100000)
                self.round_archive_service.bootstrap_archived_rounds(all_trades, session_id, self.config)
        except Exception:
            trades = []
        try:
            if self.session.get("status") == "COMPLETED":
                snapshot = self.round_archive_service.complete_round(self.session, self.config, trades, self.events)
            else:
                snapshot = self.round_archive_service.update_round(self.session, self.config, trades, self.events)
            if snapshot:
                self.session["round_number"] = int(snapshot.get("round_number") or self.session.get("round_number") or 0)
                self.session["round_label"] = str(snapshot.get("round_label") or self.session.get("round_label") or "")
        except Exception:
            return

    def _default_config(self) -> dict[str, Any]:
        return {
            "auto_validation_enabled": False,
            "target_closed_trades": 30,
            "target_validation_trades": 30,
            "allowed_symbols": ["XAUUSD", "EURUSD"],
            "broker_required": "VANTAGE_DEMO",
            "account_type_required": "DEMO",
            "lot_size": 0.01,
            "max_open_trades_total": 5,
            "max_open_trades_per_symbol": 3,
            "max_daily_trades": 30,
            "max_daily_demo_trades": 30,
            "duplicate_recent_seconds": 60,
            "max_daily_loss_amount": 100.0,
            "max_total_drawdown_amount": 150.0,
            "exit_management_enabled": True,
            "break_even_trigger_r": 0.8,
            "trailing_stop_trigger_r": 1.2,
            "trailing_stop_distance_r": 0.75,
            "exit_stale_minutes": 180,
            "exit_stale_min_r": 0.0,
            "exit_soft_adverse_minutes": 180,
            "exit_no_progress_minutes": 180,
            "exit_no_progress_min_r": 0.3,
            "exit_confidence_floor": 40,
            "exit_confidence_drop_points": 25,
            "exit_max_close_retries": 3,
            "per_symbol_exit_settings": {
                "XAUUSD": {
                    "break_even_trigger_r": 0.8,
                    "trailing_stop_trigger_r": 1.2,
                    "trailing_stop_distance_r": 0.75,
                    "stale_exit_minutes": 180,
                    "soft_adverse_minutes": 180,
                    "no_progress_minutes": 180,
                    "no_progress_min_r": 0.3,
                    "confidence_floor": 40,
                    "confidence_drop_points": 25,
                    "max_spread": 1.0,
                    "max_tick_age_seconds": 10,
                },
                "EURUSD": {
                    "break_even_trigger_r": 0.8,
                    "trailing_stop_trigger_r": 1.2,
                    "trailing_stop_distance_r": 0.75,
                    "stale_exit_minutes": 180,
                    "soft_adverse_minutes": 180,
                    "no_progress_minutes": 180,
                    "no_progress_min_r": 0.3,
                    "confidence_floor": 40,
                    "confidence_drop_points": 25,
                    "max_spread": 0.0003,
                    "max_tick_age_seconds": 10,
                },
                "NIFTY50": {
                    "break_even_trigger_r": 0.8,
                    "trailing_stop_trigger_r": 1.2,
                    "trailing_stop_distance_r": 0.75,
                    "stale_exit_minutes": 180,
                    "soft_adverse_minutes": 180,
                    "no_progress_minutes": 180,
                    "no_progress_min_r": 0.3,
                    "confidence_floor": 40,
                    "confidence_drop_points": 25,
                    "max_spread": 5.0,
                    "max_tick_age_seconds": 10,
                },
            },
            "min_confidence": 55,
            "strategy_profile": "DEMO_COLLECTION",
            "min_rr": 2.0,
            "require_sl_tp": True,
            "cooldown_after_trade_minutes": 15,
            "stop_after_target_reached": True,
            "mt5_disconnect_timeout_seconds": 600,
            "history_required_candles": 300,
            "history_warmup_timeframes": ["M15", "H1", "H4"],
            "allow_persisted_auto_resume": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _sender_rejection(self, result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        blockers = result.get("blockers") or result.get("blocked_reasons") or []
        failed_guard = result.get("failed_guard") or (blockers[0] if isinstance(blockers, list) and blockers else result.get("status") or "UNKNOWN")
        return {
            "rejection_code": result.get("rejection_code") or failed_guard,
            "rejection_reason": result.get("rejection_reason") or result.get("reason") or result.get("comment") or result.get("final_comment") or "Guarded sender rejected the demo order.",
            "failed_guard": failed_guard,
            "symbol": result.get("symbol") or payload.get("symbol"),
            "side": result.get("side") or result.get("action") or payload.get("action") or payload.get("side"),
            "lot": result.get("lot") or payload.get("lot"),
            "entry": result.get("entry") or result.get("entry_price") or payload.get("entry_price"),
            "sl": result.get("sl") or payload.get("stop_loss"),
            "tp": result.get("tp") or payload.get("take_profit"),
            "rr": result.get("rr") or payload.get("risk_reward_ratio"),
            "confidence": result.get("confidence") or result.get("signal_confidence") or payload.get("signal_confidence"),
            "broker": result.get("broker") or result.get("broker_source") or payload.get("broker_source") or payload.get("broker_id"),
            "account": result.get("account_login") or payload.get("account_login"),
            "server": result.get("server"),
            "strategy_profile": result.get("strategy_profile") or payload.get("strategy_profile"),
            "sender_status": result.get("status"),
            "timestamp": self._timestamp(),
        }

    def _duplicate_key(self, signal: dict[str, Any]) -> str:
        profile = str(signal.get("strategy_profile") or self.config.get("strategy_profile") or "DEMO_COLLECTION").upper()
        symbol = str(signal.get("symbol") or "").upper()
        side = str(signal.get("signal") or "").upper()
        session_id = str(self.session.get("session_id") or "")
        signal_hash = str(signal.get("signal_hash") or "")
        return "|".join([profile, symbol, side, session_id, signal_hash])

    def _duplicate_check(self, signal: dict[str, Any], open_positions: list[dict[str, Any]], exposure_counts: dict[str, Any] | None = None) -> dict[str, Any]:
        key = self._duplicate_key(signal)
        symbol = str(signal.get("symbol") or "").upper()
        side = str(signal.get("signal") or "").upper()
        profile = str(signal.get("strategy_profile") or self.config.get("strategy_profile") or "DEMO_COLLECTION").upper()
        signal_hash = str(signal.get("signal_hash") or "")
        active_positions = [
            item for item in open_positions
            if str(item.get("symbol") or "").upper() == symbol
        ]
        same_side_positions = [
            item for item in active_positions
            if self._position_side(item) == side
        ]
        pending_records = []
        matching_records = []
        recent_same_side_records = []
        duplicate_window_seconds = float(self.config.get("duplicate_recent_seconds", 60))
        now = datetime.now(timezone.utc)
        for trade in self.trades():
            metadata = trade.get("strategy_metadata") if isinstance(trade.get("strategy_metadata"), dict) else {}
            trade_symbol = str(trade.get("symbol") or "").upper()
            trade_side = str(trade.get("side") or trade.get("action") or "").upper()
            trade_profile = str(trade.get("strategy_profile") or metadata.get("strategy_profile") or "").upper()
            trade_hash = str(trade.get("signal_hash") or "")
            status = str(trade.get("status") or "").upper()
            trade_session_id = str(trade.get("validation_session_id") or "")
            if trade_symbol == symbol and trade_side == side and trade_profile == profile and trade_hash == signal_hash and trade_session_id == str(self.session.get("session_id") or ""):
                matching_records.append(trade)
                if status in {"OPEN", "SENT", "PENDING"}:
                    pending_records.append(trade)
            if trade_symbol == symbol and trade_side == side and trade_profile == profile and trade_session_id == str(self.session.get("session_id") or "") and status in {"OPEN", "SENT", "PENDING"}:
                timestamp = str(trade.get("opened_at") or trade.get("created_at") or trade.get("updated_at") or "")
                if self._seconds_since(timestamp, now) <= duplicate_window_seconds:
                    recent_same_side_records.append(trade)
        active_signal_sent = key in self._sent_signal_keys
        demo_collection = profile == "DEMO_COLLECTION"
        exposure_counts = exposure_counts or {}
        same_side_position_limit_reached = max(len(same_side_positions), int(exposure_counts.get("symbol_limit_count", 0))) >= int(self.config.get("max_open_trades_per_symbol") or 1)
        if demo_collection:
            duplicate = bool(pending_records or active_signal_sent or recent_same_side_records or same_side_position_limit_reached)
        else:
            duplicate = bool(active_positions or pending_records or active_signal_sent)
        if not demo_collection and active_positions:
            source = "open_mt5_position"
        elif pending_records:
            source = "active_journal_record"
        elif active_signal_sent:
            source = "same_active_signal_already_sent"
        elif demo_collection and recent_same_side_records:
            source = "recent_same_symbol_side_duplicate"
        elif demo_collection and same_side_position_limit_reached:
            source = "open_mt5_position"
        else:
            source = "none"
        return {
            "duplicate_key": key,
            "duplicate_source": source,
            "open_positions_count": len(active_positions),
            "same_side_open_positions_count": len(same_side_positions),
            "limit_count_source": exposure_counts.get("limit_count_source") or ("current_session_positions_only" if demo_collection else "all_open_positions"),
            "symbol_limit_count": exposure_counts.get("symbol_limit_count", len(active_positions)),
            "total_limit_count": exposure_counts.get("total_limit_count", len(open_positions)),
            "raw_symbol_open_positions_count": exposure_counts.get("raw_symbol_open_positions_count"),
            "raw_allowed_open_positions_count": exposure_counts.get("raw_allowed_open_positions_count"),
            "current_session_symbol_positions_count": exposure_counts.get("current_session_symbol_positions_count", len(active_positions)),
            "current_session_total_positions_count": exposure_counts.get("current_session_total_positions_count", len(open_positions)),
            "active_journal_symbol_positions_count": exposure_counts.get("active_journal_symbol_positions_count", 0),
            "active_journal_total_positions_count": exposure_counts.get("active_journal_total_positions_count", 0),
            "pending_orders_count": len(pending_records),
            "matching_journal_records": len(matching_records),
            "recent_same_side_records": len(recent_same_side_records),
            "cooldown_active": self._cooldown_active(),
            "same_side_position_limit_reached": same_side_position_limit_reached,
            "final_duplicate_decision": duplicate,
            "symbol": symbol,
            "side": side,
            "strategy_profile": profile,
            "signal_hash": signal_hash,
            "timestamp": self._timestamp(),
        }

    def _safe_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        safe = dict(self.config)
        for key in [
            "target_closed_trades",
            "target_validation_trades",
            "max_daily_loss_amount",
            "max_total_drawdown_amount",
            "cooldown_after_trade_minutes",
            "max_daily_trades",
            "max_daily_demo_trades",
            "max_open_trades_total",
            "max_open_trades_per_symbol",
            "duplicate_recent_seconds",
            "mt5_disconnect_timeout_seconds",
            "history_required_candles",
            "allow_persisted_auto_resume",
            "break_even_trigger_r",
            "trailing_stop_trigger_r",
            "trailing_stop_distance_r",
            "exit_stale_minutes",
            "exit_stale_min_r",
            "exit_soft_adverse_minutes",
            "exit_no_progress_minutes",
            "exit_no_progress_min_r",
            "exit_confidence_floor",
            "exit_confidence_drop_points",
        ]:
            if key in payload:
                safe[key] = payload[key]
        if "per_symbol_exit_settings" in payload and isinstance(payload.get("per_symbol_exit_settings"), dict):
            safe["per_symbol_exit_settings"] = payload["per_symbol_exit_settings"]
        if "history_warmup_timeframes" in payload:
            safe["history_warmup_timeframes"] = payload["history_warmup_timeframes"]
        safe["auto_validation_enabled"] = bool(payload.get("auto_validation_enabled", safe["auto_validation_enabled"]))
        safe["allowed_symbols"] = [symbol for symbol in payload.get("allowed_symbols", safe["allowed_symbols"]) if symbol in {"XAUUSD", "EURUSD", "NIFTY50"}] or ["XAUUSD", "EURUSD"]
        safe["lot_size"] = min(float(payload.get("lot_size", 0.01)), 0.01)
        safe["broker_required"] = "VANTAGE_DEMO"
        safe["account_type_required"] = "DEMO"
        safe["strategy_profile"] = self._normalize_profile(payload.get("strategy_profile", safe.get("strategy_profile")))
        safe["target_validation_trades"] = int(safe.get("target_validation_trades") or safe.get("target_closed_trades") or 30)
        safe["target_closed_trades"] = int(safe["target_validation_trades"])
        safe["max_daily_demo_trades"] = int(safe.get("max_daily_demo_trades") or safe.get("max_daily_trades") or 30)
        safe["max_daily_trades"] = int(safe["max_daily_demo_trades"])
        safe["history_required_candles"] = max(300, int(safe.get("history_required_candles") or 300))
        safe["history_warmup_timeframes"] = [str(timeframe).upper() for timeframe in safe.get("history_warmup_timeframes", ["M15", "H1", "H4"]) if str(timeframe).upper() in {"M15", "H1", "H4"}] or ["M15", "H1", "H4"]
        if safe["strategy_profile"] == "DEMO_COLLECTION":
            safe["min_confidence"] = 55
            safe["min_rr"] = 2.0
            safe["max_open_trades_total"] = int(payload.get("max_open_trades_total", 5))
            safe["max_open_trades_per_symbol"] = int(payload.get("max_open_trades_per_symbol", 3))
            safe["max_daily_demo_trades"] = int(payload.get("max_daily_demo_trades", 30))
            safe["max_daily_trades"] = int(safe["max_daily_demo_trades"])
            safe["target_validation_trades"] = int(payload.get("target_validation_trades", 30))
            safe["target_closed_trades"] = int(safe["target_validation_trades"])
        else:
            safe["min_confidence"] = 65
            safe["min_rr"] = 1.5
            safe["max_open_trades_total"] = 1
            safe["max_open_trades_per_symbol"] = 1
        safe["live_execution_enabled"] = False
        safe["broker_execution_enabled"] = False
        return safe

    def _normalize_profile(self, value: Any) -> str:
        profile = str(value or "").upper()
        return profile if profile in {"AUTO_VALIDATION", "DEMO_COLLECTION"} else "DEMO_COLLECTION"

    def _max_drawdown(self, pnl_values: list[float]) -> float:
        peak = 0.0
        equity = 0.0
        max_drawdown = 0.0
        for value in pnl_values:
            equity += value
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return round(max_drawdown, 2)

    def _emit_validation_close_reports(self, closed_trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for trade in closed_trades:
            report = self._validation_close_report(trade)
            key = self._close_report_key(report)
            if key and key in self._reported_close_keys:
                continue
            if key:
                self._reported_close_keys.add(key)
            self._validation_close_reports.append(report)
            self._validation_close_reports = self._validation_close_reports[-30:]
            reports.append(report)
            self._record_adaptive_trade_activity("CLOSED", report)
            self._persist_closed_confirmed_reason({**trade, **report, "mt5_ticket": report.get("ticket")})
            self._log("VALIDATION_TRADE_CLOSED_REPORT", report)
            self._log("ORDER_CLOSED_CONFIRMED", report)
        return reports

    def _validation_close_report(self, trade: dict[str, Any]) -> dict[str, Any]:
        metadata = trade.get("strategy_metadata") if isinstance(trade.get("strategy_metadata"), dict) else {}
        setup_type = self._setup_type(trade)
        confidence = self._number(trade.get("signal_confidence") or metadata.get("confidence"), 0)
        rr = self._trade_rr(trade)
        market_session = self._market_session_label(trade, metadata)
        ticket = str(trade.get("mt5_ticket") or trade.get("ticket") or "")
        return {
            "report_type": "VALIDATION_TRADE_CLOSED",
            "ticket": ticket,
            "trade_id": str(trade.get("trade_id") or ""),
            "symbol": str(trade.get("symbol") or "").upper(),
            "side": str(trade.get("side") or trade.get("action") or "").upper(),
            "entry": self._number_or_none(trade.get("entry_price") or trade.get("entry")),
            "exit": self._number_or_none(trade.get("close_price") or trade.get("exit_price")),
            "pnl": round(self._trade_pnl(trade), 2),
            "exit_reason": str(trade.get("exit_reason") or "UNKNOWN"),
            "setup_type": setup_type,
            "confidence": confidence,
            "rr": rr,
            "session": market_session,
            "validation_session_id": str(trade.get("validation_session_id") or self.session.get("session_id") or ""),
            "opened_at": str(trade.get("opened_at") or trade.get("created_at") or ""),
            "closed_at": str(trade.get("closed_at") or trade.get("close_time") or trade.get("updated_at") or ""),
            "result": str(trade.get("result") or ""),
            "strategy_profile": str(trade.get("strategy_profile") or metadata.get("strategy_profile") or self.config.get("strategy_profile") or ""),
            "generated_at": self._timestamp(),
        }

    def _market_session_label(self, trade: dict[str, Any], metadata: dict[str, Any]) -> str:
        for source in (trade, metadata):
            for key in ("session", "market_session", "trading_session", "session_label"):
                value = str(source.get(key) or "").strip()
                if value:
                    return value
        components = metadata.get("strategy_components") if isinstance(metadata.get("strategy_components"), dict) else {}
        value = str(components.get("session") or components.get("market_session") or "").strip()
        if value:
            return value
        if "session_valid" in components:
            return "SESSION_VALID" if components.get("session_valid") else "SESSION_INVALID"
        return str(trade.get("validation_session_id") or self.session.get("session_id") or "UNKNOWN_SESSION")

    def _close_report_key(self, report: dict[str, Any]) -> str:
        ticket = str(report.get("ticket") or "")
        closed_at = str(report.get("closed_at") or "")
        trade_id = str(report.get("trade_id") or "")
        return "|".join([ticket, closed_at, trade_id]).strip("|")

    def _number_or_none(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number == number else None

    def _trade_pnl(self, trade: dict[str, Any]) -> float:
        for key in ["net_pnl", "profit_loss", "realized_pnl", "total_pnl"]:
            if key in trade:
                return self._number(trade.get(key), 0)
        return 0.0

    def _trade_rr(self, trade: dict[str, Any]) -> float | None:
        for key in ["risk_reward_ratio", "risk_reward", "rr"]:
            if key in trade:
                value = self._number(trade.get(key), 0)
                return value if value > 0 else None
        return None

    def _setup_type(self, trade: dict[str, Any]) -> str:
        direct = str(trade.get("setup_type") or "").strip()
        if direct:
            return direct
        metadata = trade.get("strategy_metadata") if isinstance(trade.get("strategy_metadata"), dict) else {}
        metadata_setup = str(metadata.get("setup_type") or "").strip()
        if metadata_setup:
            return metadata_setup
        components = metadata.get("strategy_components") if isinstance(metadata.get("strategy_components"), dict) else {}
        ordered = [
            ("liquidity_sweep", "Sweep"),
            ("bos", "BOS"),
            ("choch", "CHOCH"),
            ("fvg", "FVG"),
            ("order_block", "OB"),
        ]
        active = [label for key, label in ordered if bool(components.get(key))]
        return " + ".join(active) if active else "Unknown Setup"

    def _setup_performance(self, closed: list[dict[str, Any]]) -> dict[str, str]:
        grouped: dict[str, list[float]] = {}
        for trade in closed:
            grouped.setdefault(self._setup_type(trade), []).append(self._trade_pnl(trade))
        if not grouped:
            return {"best_setup_type": "Unavailable", "worst_setup_type": "Unavailable"}
        ranked = sorted(
            grouped.items(),
            key=lambda item: (sum(item[1]) / len(item[1]), sum(item[1]), len(item[1])),
        )
        return {"best_setup_type": ranked[-1][0], "worst_setup_type": ranked[0][0]}

    def _equity_curve(self, closed: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def sort_key(trade: dict[str, Any]) -> str:
            return str(trade.get("closed_at") or trade.get("updated_at") or trade.get("created_at") or trade.get("timestamp") or "")

        equity = 0.0
        peak = 0.0
        points: list[dict[str, Any]] = []
        for index, trade in enumerate(sorted(closed, key=sort_key), start=1):
            pnl = self._trade_pnl(trade)
            equity += pnl
            peak = max(peak, equity)
            points.append(
                {
                    "trade_index": index,
                    "trade_id": trade.get("trade_id") or trade.get("id") or f"trade-{index}",
                    "timestamp": trade.get("closed_at") or trade.get("updated_at") or trade.get("created_at") or trade.get("timestamp"),
                    "pnl": round(pnl, 2),
                    "equity": round(equity, 2),
                    "drawdown": round(peak - equity, 2),
                }
            )
        return points

    def _number(self, value: Any, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
