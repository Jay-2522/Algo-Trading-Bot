from datetime import datetime, timezone
from typing import Any


class VantageXAUUSDDemoValidationService:
    """Vantage XAUUSD demo validation wrapper around the existing guarded sender."""

    symbol = "XAUUSD"
    supported_symbols = {"EURUSD", "XAUUSD"}
    broker = "VANTAGE_DEMO"
    max_lot = 0.01
    max_spread = 1.0
    demo_collection_max_open_trades_total = 5
    demo_collection_max_open_trades_per_symbol = 3

    def __init__(
        self,
        mt5_demo_service: Any,
        market_data_service: Any,
        approval_workflow_service: Any,
        guarded_sender_service: Any,
        position_sync_service: Any,
        lifecycle_service: Any,
        signal_engine_service: Any | None = None,
    ) -> None:
        self.mt5_demo_service = mt5_demo_service
        self.market_data_service = market_data_service
        self.approval_workflow_service = approval_workflow_service
        self.guarded_sender_service = guarded_sender_service
        self.position_sync_service = position_sync_service
        self.lifecycle_service = lifecycle_service
        self.signal_engine_service = signal_engine_service
        self._latest_preview: dict[str, Any] | None = None
        self._latest_order: dict[str, Any] | None = None
        self._test_order_attempted = False
        self._sent_signal_keys: set[str] = set()
        self._last_duplicate_check: dict[str, Any] | None = None

    def preview(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        readiness = self._readiness(payload, require_confirm=False)
        side = str(payload.get("side") or payload.get("action") or "BUY").strip().upper()
        symbol = readiness["symbol"]
        tick = readiness["tick"]
        entry = self._entry_estimate(side, tick)
        result = {
            "would_send": False,
            "broker": self.broker,
            "broker_detected": readiness["broker_detected"],
            "account_login": readiness["account"].get("login"),
            "server": readiness["account"].get("server"),
            "account_type": readiness["account"].get("account_type"),
            "symbol": symbol,
            "side": side,
            "lot": self._float_or_none(payload.get("lot")) or self.max_lot,
            "entry_estimate": entry,
            "stop_loss": self._float_or_none(payload.get("stop_loss") or payload.get("sl")),
            "take_profit": self._float_or_none(payload.get("take_profit") or payload.get("tp")),
            "spread": tick.get("spread"),
            "blocked_reasons": readiness["blockers"],
            "blockers": readiness["blockers"],
            "readiness_decision": "READY_FOR_GUARDED_DEMO_TEST" if not readiness["blockers"] else "BLOCKED",
            "approval_status": "APPROVED" if not readiness["blockers"] else "BLOCKED",
            "duplicate_protection_status": "BLOCKED" if readiness["duplicate_blocked"] else "PASSED",
            "duplicate_check": readiness["duplicate_check"],
            "tick_status": tick.get("status"),
            "tick_recovery_status": tick.get("tick_recovery_status"),
            "source": tick.get("source"),
            "broker_source": tick.get("source"),
            "signal_confidence": self._float_or_none(payload.get("signal_confidence")),
            "signal_hash": payload.get("signal_hash"),
            "setup_reason": payload.get("setup_reason"),
            "signal_revalidation": readiness["signal_revalidation"],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }
        self._latest_preview = result
        return result

    def send_test_order(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        readiness = self._readiness(payload, require_confirm=True)
        preview = self.preview(payload)
        if readiness["blockers"]:
            final_blocker = readiness["blockers"][0] if readiness["blockers"] else "VANTAGE_READINESS_BLOCKED"
            diagnostics = self._rejection_diagnostics(payload, readiness["blockers"], readiness, "Vantage demo validation blocked the order.")
            result = {
                **preview,
                "status": "BLOCKED",
                "would_send": False,
                "mt5_order_sent": False,
                "guarded_sender_used": False,
                "approval_workflow_status": "NOT_RUN",
                "approval_workflow_passed": False,
                "guarded_sender_attempted": False,
                "order_send_attempted": False,
                "order_opened": False,
                "final_blocker": final_blocker,
                "blocked_reasons": readiness["blockers"],
                **diagnostics,
            }
            self._latest_order = result
            return result

        side = str(payload.get("side") or payload.get("action")).strip().upper()
        symbol = readiness["symbol"]
        tick = readiness["tick"]
        guarded_payload = {
            "environment": "DEMO",
            "symbol": symbol,
            "action": side,
            "lot": self.max_lot,
            "entry_price": self._entry_estimate(side, tick),
            "stop_loss": self._float_or_none(payload.get("stop_loss") or payload.get("sl")),
            "take_profit": self._float_or_none(payload.get("take_profit") or payload.get("tp")),
            "manual_confirmation": True,
            "acknowledge_demo_only": True,
            "acknowledge_no_live_trading": True,
            "acknowledge_single_trade_only": True,
            "acknowledge_no_order_placement_today": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "broker_id": self.broker,
            "broker_source": self.broker,
            "signal_confidence": self._float_or_none(payload.get("signal_confidence")),
            "risk_reward_ratio": self._float_or_none(payload.get("risk_reward_ratio") or payload.get("risk_reward")),
            "signal_hash": payload.get("signal_hash"),
            "validation_session_id": payload.get("validation_session_id"),
            "setup_reason": payload.get("setup_reason"),
            "strategy_metadata": payload.get("strategy_metadata"),
            "strategy_profile": payload.get("strategy_profile"),
            "allow_xauusd_vantage_demo_test": symbol == "XAUUSD",
            "allow_eurusd_vantage_demo_test": symbol == "EURUSD",
            "execute_single_demo_order_now": True,
        }
        approval_payload = {
            **guarded_payload,
            "acknowledge_no_order_placement_today": True,
        }
        approval = self.approval_workflow_service.run_workflow(approval_payload)
        if approval.get("approved_for_future_demo_order") is not True:
            blockers = sorted(set([*readiness["blockers"], *approval.get("blockers", ["APPROVAL_WORKFLOW_NOT_APPROVED"])]))
            final_blocker = blockers[0] if blockers else "APPROVAL_WORKFLOW_NOT_APPROVED"
            diagnostics = self._rejection_diagnostics(payload, blockers, readiness, "Approval workflow blocked the guarded demo order.")
            result = {
                **preview,
                "status": "BLOCKED",
                "would_send": False,
                "mt5_order_sent": False,
                "guarded_sender_used": False,
                "approval_result": approval,
                "approval_workflow_status": approval.get("status") or "BLOCKED",
                "approval_workflow_passed": False,
                "guarded_sender_attempted": False,
                "order_send_attempted": False,
                "order_opened": False,
                "final_blocker": final_blocker,
                "blocked_reasons": blockers,
                **diagnostics,
            }
            self._latest_order = result
            return result

        self._test_order_attempted = True
        result = self.guarded_sender_service.send_order(guarded_payload)
        if result.get("status") == "DEMO_ORDER_SENT" and result.get("mt5_order_sent") is True:
            self._sent_signal_keys.add(self._duplicate_key(payload, symbol, side))
        result["broker"] = self.broker
        result["guarded_sender_used"] = True
        result["approval_result"] = approval
        result["approval_workflow_status"] = approval.get("status") or "APPROVED"
        result["approval_workflow_passed"] = True
        result["guarded_sender_attempted"] = True
        result["order_opened"] = result.get("status") == "DEMO_ORDER_SENT" and result.get("mt5_order_sent") is True
        result["order_send_attempted"] = result.get("demo_order_attempted") is True or result["order_opened"]
        result["final_blocker"] = "" if result["order_opened"] else result.get("rejection_code") or result.get("failed_guard") or result.get("final_comment") or result.get("comment") or result.get("status")
        result["duplicate_check"] = readiness["duplicate_check"]
        result["duplicate_protection_status"] = "BLOCKED" if readiness["duplicate_blocked"] else "PASSED"
        result["signal_revalidation"] = readiness["signal_revalidation"]
        result["readiness_decision"] = "READY_FOR_GUARDED_DEMO_TEST"
        result["approval_status"] = "APPROVED"
        result["tick_status"] = tick.get("status")
        result["tick_recovery_status"] = tick.get("tick_recovery_status")
        result["spread"] = tick.get("spread")
        result["entry_estimate"] = guarded_payload["entry_price"]
        self._latest_order = result
        return result

    def status(self) -> dict[str, Any]:
        diagnostics = self.market_data_service.get_xauusd_diagnostics()
        account = self.mt5_demo_service.get_status()
        return {
            "status": "READY",
            "broker_detected": self._broker_detected(account),
            "server": account.get("server"),
            "account_login": account.get("login"),
            "account_type": account.get("account_type"),
            "tick_available": diagnostics.get("tick_available"),
            "bid": diagnostics.get("bid"),
            "ask": diagnostics.get("ask"),
            "spread": diagnostics.get("spread"),
            "source": diagnostics.get("source"),
            "readiness_result": diagnostics.get("readiness_result"),
            "latest_preview": self._latest_preview,
            "latest_test_order": self._latest_order,
            "last_duplicate_check": self._last_duplicate_check,
            "position_sync_compatible": True,
            "lifecycle_sync_compatible": True,
            "journal_compatible": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _readiness(self, payload: dict[str, Any], require_confirm: bool) -> dict[str, Any]:
        account = self.mt5_demo_service.get_status()
        symbol = str(payload.get("symbol") or self.symbol).strip().upper()
        tick = self.market_data_service.get_symbol_tick(symbol if symbol in self.supported_symbols else self.symbol)
        side = str(payload.get("side") or payload.get("action") or "").strip().upper()
        lot = self._float_or_none(payload.get("lot"))
        stop_loss = self._float_or_none(payload.get("stop_loss") or payload.get("sl"))
        take_profit = self._float_or_none(payload.get("take_profit") or payload.get("tp"))
        entry = self._entry_estimate(side, tick)
        blockers: list[str] = []

        if self._broker_detected(account) != self.broker:
            blockers.append("VANTAGE_DEMO_ACCOUNT_REQUIRED")
        if account.get("account_type") != "DEMO":
            blockers.append("DEMO_ACCOUNT_REQUIRED")
        if symbol not in self.supported_symbols:
            blockers.append("SUPPORTED_SYMBOL_REQUIRED")
        if require_confirm and payload.get("confirm") is not True:
            blockers.append("EXPLICIT_CONFIRM_TRUE_REQUIRED")
        if side not in {"BUY", "SELL"}:
            blockers.append("SIDE_MUST_BE_BUY_OR_SELL")
        if lot is None or lot <= 0 or lot > self.max_lot:
            blockers.append("LOT_MUST_BE_0_01_OR_LESS")
        if stop_loss is None or stop_loss <= 0:
            blockers.append("STOP_LOSS_REQUIRED")
        if take_profit is None or take_profit <= 0:
            blockers.append("TAKE_PROFIT_REQUIRED")
        if entry is None:
            blockers.append("ENTRY_PRICE_UNAVAILABLE")
        elif side == "BUY" and stop_loss is not None and take_profit is not None and not (stop_loss < entry < take_profit):
            blockers.append("INVALID_BUY_SL_TP_PLACEMENT")
        elif side == "SELL" and stop_loss is not None and take_profit is not None and not (take_profit < entry < stop_loss):
            blockers.append("INVALID_SELL_SL_TP_PLACEMENT")
        strategy_profile = str(payload.get("strategy_profile") or "").upper()
        tick_ready = tick.get("status") == "OK" or (strategy_profile == "DEMO_COLLECTION" and self._tick_stale_within_grace(tick))
        if not tick_ready:
            blockers.append(f"{symbol}_TICK_NOT_READY")
        if tick.get("spread") is None:
            blockers.append("SPREAD_UNAVAILABLE")
        elif float(tick["spread"]) > self.max_spread:
            blockers.append("SPREAD_TOO_WIDE")
        duplicate_check = self._duplicate_check(payload, symbol, side)
        self._last_duplicate_check = duplicate_check
        if duplicate_check["final_duplicate_decision"] is True:
            blockers.append("DUPLICATE_VANTAGE_XAUUSD_TEST_ORDER_BLOCKED")
        if payload.get("live_execution_enabled") is not False:
            blockers.append("LIVE_EXECUTION_FLAG_MUST_BE_FALSE")
        if payload.get("broker_execution_enabled") is True:
            blockers.append("BROKER_EXECUTION_MUST_REMAIN_DISABLED")
        signal_revalidation = self._revalidate_signal(payload, symbol, side)
        blockers.extend(signal_revalidation["blockers"])
        return {
            "account": account,
            "tick": tick,
            "symbol": symbol if symbol in self.supported_symbols else self.symbol,
            "broker_detected": self._broker_detected(account),
            "blockers": sorted(set(blockers)),
            "duplicate_blocked": "DUPLICATE_VANTAGE_XAUUSD_TEST_ORDER_BLOCKED" in blockers,
            "duplicate_check": duplicate_check,
            "signal_revalidation": signal_revalidation,
        }

    def _duplicate_key(self, payload: dict[str, Any], symbol: str, side: str) -> str:
        profile = str(payload.get("strategy_profile") or "").upper()
        session_id = str(payload.get("validation_session_id") or "")
        signal_hash = str(payload.get("signal_hash") or "")
        return "|".join([profile, str(symbol or "").upper(), str(side or "").upper(), session_id, signal_hash])

    def _duplicate_check(self, payload: dict[str, Any], symbol: str, side: str) -> dict[str, Any]:
        key = self._duplicate_key(payload, symbol, side)
        raw_symbol_positions = self._open_positions(symbol)
        raw_all_open_positions = self._all_open_positions()
        if not raw_all_open_positions:
            raw_all_open_positions = raw_symbol_positions
        profile = str(payload.get("strategy_profile") or "").upper()
        if profile == "DEMO_COLLECTION":
            open_positions = self._demo_collection_limit_positions(payload, raw_symbol_positions)
            all_open_positions = self._demo_collection_limit_positions(payload, raw_all_open_positions)
        else:
            open_positions = raw_symbol_positions
            all_open_positions = raw_all_open_positions
        raw_allowed_positions = [position for position in raw_all_open_positions if str(position.get("symbol") or "").upper() in self.supported_symbols]
        active_journal_positions = self._active_journal_open_positions(payload, profile)
        active_journal_symbol_positions = [trade for trade in active_journal_positions if str(trade.get("symbol") or "").upper() == str(symbol or "").upper()]
        if profile == "DEMO_COLLECTION":
            symbol_limit_count = max(len(raw_symbol_positions), len(open_positions), len(active_journal_symbol_positions))
            total_limit_count = max(len(raw_allowed_positions), len(all_open_positions), len(active_journal_positions))
            limit_count_source = "max_raw_mt5_current_session_active_journal"
        else:
            symbol_limit_count = len(open_positions)
            total_limit_count = len(all_open_positions)
            limit_count_source = "all_open_positions"
        same_side_open_positions = [position for position in open_positions if self._position_side(position) == str(side or "").upper()]
        active_signal_sent = key in self._sent_signal_keys
        if profile == "DEMO_COLLECTION":
            total_limit_reached = total_limit_count >= self.demo_collection_max_open_trades_total
            symbol_limit_reached = symbol_limit_count >= self.demo_collection_max_open_trades_per_symbol
            duplicate = bool(active_signal_sent or total_limit_reached or symbol_limit_reached)
            if active_signal_sent:
                source = "same_active_signal_already_sent"
            elif total_limit_reached:
                source = "max_open_trades_total_reached"
            elif symbol_limit_reached:
                source = "max_open_trades_per_symbol_reached"
            else:
                source = "none"
        else:
            total_limit_reached = bool(open_positions)
            symbol_limit_reached = bool(open_positions)
            duplicate = bool(open_positions or active_signal_sent)
            source = "open_mt5_position" if open_positions else "same_active_signal_already_sent" if active_signal_sent else "none"
        return {
            "duplicate_key": key,
            "duplicate_source": source,
            "open_positions_count": len(open_positions),
            "total_open_positions_count": len(all_open_positions),
            "raw_open_positions_count": len(raw_symbol_positions),
            "raw_total_open_positions_count": len(raw_all_open_positions),
            "raw_allowed_open_positions_count": len(raw_allowed_positions),
            "active_journal_symbol_positions_count": len(active_journal_symbol_positions),
            "active_journal_total_positions_count": len(active_journal_positions),
            "symbol_limit_count": symbol_limit_count,
            "total_limit_count": total_limit_count,
            "historical_unowned_positions_count": max(len(raw_all_open_positions) - len(all_open_positions), 0),
            "limit_count_source": limit_count_source,
            "same_side_open_positions_count": len(same_side_open_positions),
            "max_open_trades_total": self.demo_collection_max_open_trades_total if profile == "DEMO_COLLECTION" else 1,
            "max_open_trades_per_symbol": self.demo_collection_max_open_trades_per_symbol if profile == "DEMO_COLLECTION" else 1,
            "pending_orders_count": 0,
            "matching_journal_records": 0,
            "cooldown_active": False,
            "total_limit_reached": total_limit_reached,
            "symbol_limit_reached": symbol_limit_reached,
            "final_duplicate_decision": duplicate,
            "symbol": str(symbol or "").upper(),
            "side": str(side or "").upper(),
            "strategy_profile": profile,
            "signal_hash": str(payload.get("signal_hash") or ""),
            "timestamp": self._timestamp(),
        }

    def _active_journal_open_positions(self, payload: dict[str, Any], profile: str) -> list[dict[str, Any]]:
        session_id = str(payload.get("validation_session_id") or "")
        if not session_id:
            return []
        journal = getattr(self.guarded_sender_service, "persistent_trade_journal_service", None)
        reader = getattr(journal, "list_trades", None)
        if not callable(reader):
            return []
        try:
            trades = reader(limit=100000)
        except Exception:
            return []
        active_statuses = {"OPEN", "SENT", "PENDING"}
        active_profile = str(profile or "").upper()
        return [
            trade
            for trade in trades
            if str(trade.get("validation_session_id") or "") == session_id
            and str(trade.get("symbol") or "").upper() in self.supported_symbols
            and str(trade.get("status") or "").upper() in active_statuses
            and (
                active_profile != "DEMO_COLLECTION"
                or str((trade.get("strategy_metadata") if isinstance(trade.get("strategy_metadata"), dict) else {}).get("strategy_profile") or trade.get("strategy_profile") or "").upper() == "DEMO_COLLECTION"
            )
        ]

    def _demo_collection_limit_positions(self, payload: dict[str, Any], positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [position for position in positions if self._position_belongs_to_payload_session(payload, position)]

    def _position_belongs_to_payload_session(self, payload: dict[str, Any], position: dict[str, Any]) -> bool:
        session_id = str(payload.get("validation_session_id") or "")
        if session_id and str(position.get("validation_session_id") or "") == session_id:
            return True
        return self._position_has_auto_validation_marker(position) and self._position_opened_after_session_start(payload, position)

    def _position_has_auto_validation_marker(self, position: dict[str, Any]) -> bool:
        profile = str(position.get("strategy_profile") or position.get("execution_mode") or "").upper()
        if profile in {"DEMO_COLLECTION", "AUTO_VALIDATION"}:
            return True
        comment = str(position.get("comment") or position.get("external_id") or position.get("magic_comment") or "").upper()
        return "AUTO" in comment or "GUARDED" in comment or "VALIDATION" in comment

    def _position_opened_after_session_start(self, payload: dict[str, Any], position: dict[str, Any]) -> bool:
        session_start = str(payload.get("validation_session_start_time") or payload.get("session_start_time") or "")
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

    def _open_positions(self, symbol: str) -> list[dict[str, Any]]:
        try:
            result = self.position_sync_service.get_open_positions_by_symbol(symbol)
        except Exception:
            return []
        positions = result.get("positions", []) if isinstance(result, dict) else []
        return positions if isinstance(positions, list) else []

    def _tick_stale_within_grace(self, tick: dict[str, Any]) -> bool:
        status = str(tick.get("status") or "").upper()
        stale_age = self._float_or_none(tick.get("stale_age_seconds"))
        spread = self._float_or_none(tick.get("spread"))
        return status == "STALE_TICK" and stale_age is not None and stale_age <= 10 and spread is not None and spread <= self.max_spread

    def _all_open_positions(self) -> list[dict[str, Any]]:
        try:
            reader = getattr(self.position_sync_service, "get_open_positions", None)
            result = reader() if callable(reader) else None
        except Exception:
            return []
        positions = result.get("positions", []) if isinstance(result, dict) else []
        return positions if isinstance(positions, list) else []

    def _position_side(self, position: dict[str, Any]) -> str:
        return str(position.get("side") or position.get("type") or position.get("action") or "").upper()

    def _revalidate_signal(self, payload: dict[str, Any], symbol: str, side: str) -> dict[str, Any]:
        signal_timestamp = payload.get("signal_timestamp")
        signal_hash = str(payload.get("signal_hash") or "")
        ai_payload = bool(signal_timestamp or signal_hash or payload.get("signal_confidence") is not None)
        if not ai_payload:
            return {"status": "SKIPPED_NON_AI_PREVIEW", "blockers": [], "age_seconds": None}

        blockers: list[str] = []
        age_seconds = self._signal_age_seconds(signal_timestamp)
        if age_seconds is None:
            blockers.append("SIGNAL_TIMESTAMP_REQUIRED")
        elif age_seconds < 0:
            blockers.append("SIGNAL_TIMESTAMP_IN_FUTURE")
        elif age_seconds > 30:
            blockers.append("SIGNAL_EXPIRED")

        strategy_profile = str(payload.get("strategy_profile") or "").upper()
        current_signal = None
        if self.signal_engine_service is not None and symbol in self.supported_symbols:
            try:
                if strategy_profile in {"AUTO_VALIDATION", "DEMO_COLLECTION"}:
                    current_signal = self.signal_engine_service.generate_signal(symbol, strategy_profile=strategy_profile)
                else:
                    current_signal = self.signal_engine_service.generate_signal(symbol)
            except TypeError:
                current_signal = self.signal_engine_service.generate_signal(symbol)
        if current_signal is not None:
            current_direction = str(current_signal.get("signal") or "").upper()
            if current_direction in {"BUY", "SELL"} and side in {"BUY", "SELL"} and current_direction != side:
                blockers.append("SIGNAL_DIRECTION_CHANGED")
            elif current_direction not in {"BUY", "SELL"}:
                blockers.append("SIGNAL_NO_LONGER_HAS_DIRECTION")
            if strategy_profile == "DEMO_COLLECTION":
                if not self._demo_collection_payload_still_executable(payload, side):
                    blockers.append("DEMO_COLLECTION_PAYLOAD_NO_LONGER_EXECUTABLE")
            else:
                if current_signal.get("execution_status") != "READY_FOR_PREVIEW":
                    blockers.append("SIGNAL_NO_LONGER_READY_FOR_PREVIEW")
                if current_signal.get("risk_status") != "APPROVED":
                    blockers.append("SIGNAL_NO_LONGER_APPROVED")
            if signal_hash and current_signal.get("signal_hash") != signal_hash and strategy_profile not in {"AUTO_VALIDATION", "DEMO_COLLECTION"}:
                blockers.append("SIGNAL_HASH_CHANGED")
            if strategy_profile == "AUTO_VALIDATION":
                if self._float_or_none(current_signal.get("risk_reward")) is not None and self._float_or_none(current_signal.get("risk_reward")) < 1.5:
                    blockers.append("RR_BELOW_AUTO_VALIDATION_MINIMUM")
                if self._float_or_none(current_signal.get("confidence")) is not None and self._float_or_none(current_signal.get("confidence")) < 65:
                    blockers.append("CONFIDENCE_BELOW_AUTO_VALIDATION_MINIMUM")
            if strategy_profile == "DEMO_COLLECTION":
                if self._float_or_none(current_signal.get("risk_reward")) is not None and self._float_or_none(current_signal.get("risk_reward")) < 1.2:
                    blockers.append("RR_BELOW_DEMO_COLLECTION_MINIMUM")
                if self._float_or_none(current_signal.get("confidence")) is not None and self._float_or_none(current_signal.get("confidence")) < 55:
                    blockers.append("CONFIDENCE_BELOW_DEMO_COLLECTION_MINIMUM")

        return {
            "status": "PASSED" if not blockers else "BLOCKED",
            "blockers": sorted(set(blockers)),
            "age_seconds": round(age_seconds, 2) if age_seconds is not None else None,
            "max_age_seconds": 30,
            "current_signal": {
                "signal": current_signal.get("signal"),
                "requested_side": side,
                "execution_status": current_signal.get("execution_status"),
                "risk_status": current_signal.get("risk_status"),
                "signal_hash": current_signal.get("signal_hash"),
                "timestamp": current_signal.get("timestamp"),
                "strategy_profile": current_signal.get("strategy_profile"),
            }
            if current_signal is not None
            else None,
        }

    def _demo_collection_payload_still_executable(self, payload: dict[str, Any], side: str) -> bool:
        entry = self._float_or_none(payload.get("entry_price") or payload.get("entry"))
        if entry is None:
            symbol = str(payload.get("symbol") or self.symbol).strip().upper()
            tick = self.market_data_service.get_symbol_tick(symbol if symbol in self.supported_symbols else self.symbol)
            entry = self._entry_estimate(side, tick)
        stop_loss = self._float_or_none(payload.get("stop_loss") or payload.get("sl"))
        take_profit = self._float_or_none(payload.get("take_profit") or payload.get("tp"))
        rr = self._float_or_none(payload.get("risk_reward_ratio") or payload.get("risk_reward") or payload.get("rr"))
        confidence = self._float_or_none(payload.get("signal_confidence") or payload.get("confidence"))
        if side == "BUY" and not (entry and stop_loss and take_profit and stop_loss < entry < take_profit):
            return False
        if side == "SELL" and not (entry and stop_loss and take_profit and take_profit < entry < stop_loss):
            return False
        return bool(rr is not None and rr >= 1.2 and confidence is not None and confidence >= 55)

    def _rejection_diagnostics(self, payload: dict[str, Any], blockers: list[str], readiness: dict[str, Any], reason: str) -> dict[str, Any]:
        account = readiness.get("account") if isinstance(readiness.get("account"), dict) else {}
        tick = readiness.get("tick") if isinstance(readiness.get("tick"), dict) else {}
        failed_guard = blockers[0] if blockers else "UNKNOWN"
        return {
            "rejection_code": failed_guard,
            "rejection_reason": reason,
            "failed_guard": failed_guard,
            "symbol": readiness.get("symbol") or payload.get("symbol"),
            "side": str(payload.get("side") or payload.get("action") or "").upper(),
            "lot": self._float_or_none(payload.get("lot")),
            "entry": self._entry_estimate(str(payload.get("side") or payload.get("action") or "").upper(), tick),
            "sl": self._float_or_none(payload.get("stop_loss") or payload.get("sl")),
            "tp": self._float_or_none(payload.get("take_profit") or payload.get("tp")),
            "rr": self._float_or_none(payload.get("risk_reward_ratio") or payload.get("rr")),
            "confidence": self._float_or_none(payload.get("signal_confidence")),
            "broker": self.broker,
            "account": account.get("login") or account.get("account_login"),
            "server": account.get("server"),
            "account_type": account.get("account_type"),
            "strategy_profile": payload.get("strategy_profile"),
        }

    def _signal_age_seconds(self, value: Any) -> float | None:
        if not value:
            return None
        parsed = self._parse_time(value)
        if parsed is None:
            return None
        return (datetime.now(timezone.utc) - parsed).total_seconds()

    def _parse_time(self, value: Any) -> datetime | None:
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (OSError, OverflowError, ValueError):
                return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _broker_detected(self, account: dict[str, Any]) -> str | None:
        server = str(account.get("server") or "").lower()
        if "vantage" in server and account.get("account_type") == "DEMO":
            return self.broker
        return None

    def _entry_estimate(self, side: str, tick: dict[str, Any]) -> float | None:
        key = "ask" if side == "BUY" else "bid"
        value = self._float_or_none(tick.get(key))
        return value if value and value > 0 else None

    def _float_or_none(self, value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
