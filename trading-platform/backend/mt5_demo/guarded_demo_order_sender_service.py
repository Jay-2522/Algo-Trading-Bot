from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

try:
    import MetaTrader5 as mt5
except Exception as exc:  # pragma: no cover - depends on local MT5 installation
    mt5 = None
    MT5_IMPORT_ERROR = exc
else:
    MT5_IMPORT_ERROR = None


class GuardedDemoOrderSenderService:
    """Guarded Phase 17 sender boundary. Verification paths never send orders."""

    allowed_symbols = {"EURUSD", "XAUUSD"}
    runtime_symbols = {"EURUSD"}
    allowed_actions = {"BUY", "SELL"}
    max_demo_lot = 0.01

    def __init__(
        self,
        mt5_demo_service: Any,
        approval_workflow_service: Any,
        final_approval_service: Any,
        dry_run_service: Any,
        preflight_service: Any,
        simulator_service: Any,
        readiness_service: Any,
        persistent_trade_journal_service: Any | None = None,
    ) -> None:
        self.mt5_demo_service = mt5_demo_service
        self.approval_workflow_service = approval_workflow_service
        self.final_approval_service = final_approval_service
        self.dry_run_service = dry_run_service
        self.preflight_service = preflight_service
        self.simulator_service = simulator_service
        self.readiness_service = readiness_service
        self.persistent_trade_journal_service = persistent_trade_journal_service or PersistentTradeJournalService()
        self._history: list[dict[str, Any]] = []
        self._demo_send_attempted = False

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "GUARDED_DEMO_ORDER_SENDER_LOCKED",
            "single_trade_limit": 1,
            "demo_send_attempted": self._demo_send_attempted,
            "allowed_symbols": sorted(self.allowed_symbols),
            "max_demo_lot": self.max_demo_lot,
            "execution_allowed": False,
            "mt5_order_sent": False,
            "demo_order_attempted": False,
            "live_order_attempted": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def prepare_order(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        return self._handle(payload, require_final_flag=False)

    def send_order(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        if not payload or payload.get("execute_single_demo_order_now") is not True:
            result = self._handle(payload, require_final_flag=False)
            result["status"] = "PREPARED_BUT_NOT_SENT" if result["status"] == "PREPARED_BUT_NOT_SENT" else result["status"]
            result["reason"] = "Explicit final execution flag not provided."
            return result
        return self._handle(payload, require_final_flag=True)

    def get_latest(self) -> dict[str, Any]:
        if self._history:
            return self._history[-1]
        return {
            "status": "NOT_PREPARED",
            "execution_allowed": False,
            "mt5_order_sent": False,
            "demo_order_attempted": False,
            "live_order_attempted": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def list_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def _handle(self, payload: dict[str, Any] | None, require_final_flag: bool) -> dict[str, Any]:
        payload = payload or {}
        blockers = self._validate(payload)
        if blockers:
            result = self._result("REJECTED", payload, blockers, "Safety validation failed.")
            self._history.append(result)
            return result

        if not require_final_flag:
            result = self._result("PREPARED_BUT_NOT_SENT", payload, [], "Explicit final execution flag not provided.")
            self._history.append(result)
            return result

        self._demo_send_attempted = True
        result = self._send_to_mt5(payload)
        self._history.append(result)
        return result

    def _validate(self, payload: dict[str, Any]) -> list[str]:
        blockers: list[str] = []
        symbol = str(payload.get("symbol") or "").strip().upper()
        action = str(payload.get("action") or "").strip().upper()
        lot = self._float_or_none(payload.get("lot"))
        account_status = self.mt5_demo_service.get_status()
        workflow = self.approval_workflow_service.get_latest()
        final_approval = self.final_approval_service.get_latest_approval()
        dry_run = self.dry_run_service.get_latest()
        preflight = self.preflight_service.get_latest()
        simulator = self.simulator_service.get_latest()
        readiness = self.readiness_service.get_latest_audit()

        if payload.get("environment") != "DEMO":
            blockers.append("ENVIRONMENT_MUST_BE_DEMO")
        if symbol not in self.allowed_symbols:
            blockers.append("INVALID_SYMBOL")
        elif symbol not in self.runtime_symbols:
            blockers.append("RUNTIME_SYMBOL_NOT_ENABLED")
        if action not in self.allowed_actions:
            blockers.append("INVALID_ACTION")
        if lot != self.max_demo_lot:
            blockers.append("LOT_MUST_BE_EXACTLY_0_01")
        for key in ["entry_price", "stop_loss", "take_profit"]:
            value = self._float_or_none(payload.get(key))
            if value is None or value <= 0:
                blockers.append(f"{key.upper()}_REQUIRED")
        for key in [
            "manual_confirmation",
            "acknowledge_demo_only",
            "acknowledge_no_live_trading",
            "acknowledge_single_trade_only",
        ]:
            if payload.get(key) is not True:
                blockers.append(f"{key.upper()}_REQUIRED")
        if payload.get("live_execution_enabled") is True:
            blockers.append("LIVE_TRADING_ENABLED")
        if payload.get("broker_execution_enabled") is True:
            blockers.append("PRODUCTION_BROKER_EXECUTION_ENABLED")
        if self._demo_send_attempted and not self._safe_rejected_send_retry_available():
            blockers.append("SINGLE_DEMO_TRADE_LIMIT_REACHED")
        if account_status.get("status") != "CONNECTED" or account_status.get("environment") != "DEMO":
            blockers.append("MT5_DEMO_ACCOUNT_NOT_VALIDATED")
        if account_status.get("account_type", "DEMO") != "DEMO":
            blockers.append("MT5_ACCOUNT_IS_NOT_DEMO")
        if workflow.get("approved_for_future_demo_order") is not True:
            blockers.append("APPROVAL_WORKFLOW_NOT_APPROVED")
        if final_approval.get("approved_for_future_demo_order") is not True:
            blockers.append("FINAL_APPROVAL_NOT_APPROVED")
        if dry_run.get("validation_passed") is not True:
            blockers.append("DRY_RUN_NOT_COMPLETE")
        if preflight.get("validation_passed") is not True:
            blockers.append("PREFLIGHT_NOT_COMPLETE")
        if simulator.get("simulation_passed") is not True:
            blockers.append("SIMULATOR_NOT_COMPLETE")
        if readiness.get("overall_status") != "READY":
            blockers.append("READINESS_NOT_READY")
        return blockers

    def _send_to_mt5(self, payload: dict[str, Any]) -> dict[str, Any]:
        symbol = str(payload["symbol"]).strip().upper()
        action = str(payload["action"]).strip().upper()
        lot = float(payload["lot"])
        stop_loss = float(payload["stop_loss"])
        take_profit = float(payload["take_profit"])

        initialized = False
        try:
            if mt5 is None:
                return self._sent_result(
                    "DEMO_ORDER_REJECTED",
                    payload,
                    False,
                    None,
                    None,
                    f"MetaTrader5 package unavailable: {MT5_IMPORT_ERROR}",
                )
            initialized = bool(mt5.initialize())
            if not initialized:
                return self._sent_result("DEMO_ORDER_REJECTED", payload, False, None, None, f"MT5 initialize failed: {mt5.last_error()}")

            account = mt5.account_info()
            demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
            account_trade_mode = getattr(account, "trade_mode", None) if account else None
            server = str(getattr(account, "server", "") if account else "")
            is_demo = account is not None and ("demo" in server.lower() or (demo_mode is not None and account_trade_mode == demo_mode))
            if not is_demo:
                return self._sent_result(
                    "DEMO_ORDER_REJECTED",
                    payload,
                    False,
                    None,
                    None,
                    "MT5 account is not confirmed as DEMO.",
                    account=account,
                )

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return self._sent_result("DEMO_ORDER_REJECTED", payload, False, None, None, f"No MT5 tick available for {symbol}.", account=account)
            price = float(getattr(tick, "ask", 0.0) if action == "BUY" else getattr(tick, "bid", 0.0))
            if price <= 0:
                return self._sent_result("DEMO_ORDER_REJECTED", payload, False, None, None, f"No valid {action} price available.", account=account)

            symbol_info = mt5.symbol_info("EURUSD")
            filling_mode_candidates = self._build_filling_mode_candidates(symbol_info)
            if not filling_mode_candidates:
                return self._sent_result(
                    "DEMO_ORDER_REJECTED",
                    payload,
                    False,
                    0,
                    None,
                    "No supported filling mode available for EURUSD.",
                    account=account,
                    selected_filling_mode=None,
                    filling_mode_attempts=[],
                    final_retcode=None,
                    final_comment="No supported filling mode available for EURUSD.",
                )

            base_order_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 20,
                "magic": 17001,
                "comment": "PHASE17_SINGLE_DEMO_TEST",
                "type_time": mt5.ORDER_TIME_GTC,
            }
            filling_mode_attempts: list[dict[str, Any]] = []
            success_codes = {getattr(mt5, "TRADE_RETCODE_DONE", None), getattr(mt5, "TRADE_RETCODE_PLACED", None)}
            unsupported_filling_retcode = 10030
            selected_filling_mode = None
            final_result = None
            final_retcode = None
            final_comment = ""
            sent = False

            for filling_mode in filling_mode_candidates:
                order_request = dict(base_order_request)
                order_request["type_filling"] = filling_mode
                mt5_result = mt5.order_send(order_request)
                retcode = getattr(mt5_result, "retcode", None)
                comment = str(getattr(mt5_result, "comment", ""))
                attempt = {
                    "mode": filling_mode,
                    "retcode": retcode,
                    "comment": comment,
                    "order": getattr(mt5_result, "order", 0) or 0,
                    "deal": getattr(mt5_result, "deal", 0) or 0,
                }
                filling_mode_attempts.append(attempt)
                selected_filling_mode = filling_mode
                final_result = mt5_result
                final_retcode = retcode
                final_comment = comment
                sent = retcode in {code for code in success_codes if code is not None}
                if sent:
                    break
                if retcode != unsupported_filling_retcode or "unsupported filling mode" not in comment.lower():
                    break

            ticket = getattr(final_result, "order", 0) if final_result is not None else 0
            result = self._sent_result(
                "DEMO_ORDER_SENT" if sent else "DEMO_ORDER_REJECTED",
                payload,
                sent,
                ticket or 0,
                final_retcode,
                final_comment,
                account=account,
                mt5_result={
                    "retcode": final_retcode,
                    "order": getattr(final_result, "order", 0) if final_result is not None else 0,
                    "deal": getattr(final_result, "deal", 0) if final_result is not None else 0,
                    "comment": final_comment,
                },
                selected_filling_mode=selected_filling_mode,
                filling_mode_attempts=filling_mode_attempts,
                final_retcode=final_retcode,
                final_comment=final_comment,
            )
            self._persist_trade_journal_result(result, payload, price)
            return result
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return self._sent_result("DEMO_ORDER_REJECTED", payload, False, None, None, f"Guarded MT5 send failed safely: {exc}")
        finally:
            if initialized:
                mt5.shutdown()

    def _build_filling_mode_candidates(self, symbol_info: Any) -> list[Any]:
        supported = getattr(symbol_info, "filling_mode", None) if symbol_info is not None else None
        preferred_modes = [
            getattr(mt5, "ORDER_FILLING_IOC", None),
            getattr(mt5, "ORDER_FILLING_FOK", None),
            getattr(mt5, "ORDER_FILLING_RETURN", None),
        ]
        preferred_modes = [mode for mode in preferred_modes if mode is not None]
        candidates: list[Any] = []
        if supported is not None:
            candidates.append(supported)
        for mode in preferred_modes:
            if mode not in candidates:
                candidates.append(mode)
        return candidates

    def _safe_rejected_send_retry_available(self) -> bool:
        demo_attempts = sum(1 for item in self._history if item.get("demo_order_attempted") is True)
        if demo_attempts != 1:
            return False
        latest = self.get_latest()
        attempts = latest.get("filling_mode_attempts") or []
        created_order_or_deal = any((attempt.get("order") or 0) != 0 or (attempt.get("deal") or 0) != 0 for attempt in attempts)
        return latest.get("status") == "DEMO_ORDER_REJECTED" and latest.get("mt5_order_sent") is False and str(latest.get("ticket")) == "0" and not created_order_or_deal

    def _persist_trade_journal_result(self, result: dict[str, Any], payload: dict[str, Any], executed_price: float | None = None) -> None:
        ticket = self._positive_int(result.get("ticket"))
        retcode = self._positive_int(result.get("retcode"))
        attempted = result.get("demo_order_attempted") is True
        sent = result.get("status") == "DEMO_ORDER_SENT" and result.get("mt5_order_sent") is True and retcode == 10009 and ticket > 0
        rejected = result.get("status") == "DEMO_ORDER_REJECTED" and attempted and result.get("mt5_order_sent") is False and retcode is not None

        if not sent and not rejected:
            return

        journal_payload = self._journal_payload(result, payload, executed_price)
        if sent:
            self.persistent_trade_journal_service.record_order_sent(journal_payload)
        elif rejected:
            self.persistent_trade_journal_service.record_order_rejected(journal_payload)

    def _journal_payload(self, result: dict[str, Any], payload: dict[str, Any], executed_price: float | None = None) -> dict[str, Any]:
        ticket = str(result.get("ticket") or "0")
        retcode = str(result.get("retcode") or "")
        return {
            "trade_id": f"mt5_demo_{ticket}" if ticket != "0" else f"mt5_demo_rejected_{result.get('request_id')}",
            "source": "MT5_DEMO",
            "environment": "DEMO",
            "symbol": "EURUSD",
            "side": str(payload.get("action") or result.get("action") or "").strip().upper(),
            "lot": 0.01,
            "entry_price": executed_price or self._float_or_none(payload.get("entry_price")),
            "stop_loss": self._float_or_none(payload.get("stop_loss")),
            "take_profit": self._float_or_none(payload.get("take_profit")),
            "risk_reward_ratio": self._risk_reward_ratio(payload),
            "mt5_ticket": ticket,
            "mt5_retcode": retcode,
            "mt5_comment": result.get("final_comment") or result.get("comment"),
            "profit_loss": 0,
            "notes": "First controlled MT5 demo order executed through guarded sender.",
        }

    def _risk_reward_ratio(self, payload: dict[str, Any]) -> float | None:
        explicit = self._float_or_none(payload.get("risk_reward_ratio") or payload.get("rr"))
        if explicit is not None:
            return explicit
        entry = self._float_or_none(payload.get("entry_price"))
        stop_loss = self._float_or_none(payload.get("stop_loss"))
        take_profit = self._float_or_none(payload.get("take_profit"))
        action = str(payload.get("action") or "").strip().upper()
        if entry is None or stop_loss is None or take_profit is None:
            return 2.0
        risk = entry - stop_loss if action == "BUY" else stop_loss - entry
        reward = take_profit - entry if action == "BUY" else entry - take_profit
        if risk <= 0 or reward <= 0:
            return 2.0
        return round(reward / risk, 2)

    def _sent_result(
        self,
        status: str,
        payload: dict[str, Any],
        mt5_order_sent: bool,
        ticket: Any,
        retcode: Any,
        comment: str,
        account: Any = None,
        mt5_result: dict[str, Any] | None = None,
        selected_filling_mode: Any = None,
        filling_mode_attempts: list[dict[str, Any]] | None = None,
        final_retcode: Any = None,
        final_comment: str | None = None,
    ) -> dict[str, Any]:
        return {
            "request_id": f"guarded-demo-order-{uuid4()}",
            "status": status,
            "mt5_order_sent": mt5_order_sent,
            "demo_order_attempted": True,
            "live_order_attempted": False,
            "ticket": str(ticket) if ticket is not None else "",
            "retcode": str(retcode) if retcode is not None else "",
            "comment": comment,
            "selected_filling_mode": selected_filling_mode,
            "filling_mode_attempts": filling_mode_attempts or [],
            "final_retcode": final_retcode,
            "final_comment": final_comment if final_comment is not None else comment,
            "symbol": str(payload.get("symbol") or "").strip().upper(),
            "action": str(payload.get("action") or "").strip().upper(),
            "lot": float(payload.get("lot") or 0.0),
            "sl": self._float_or_none(payload.get("stop_loss")),
            "tp": self._float_or_none(payload.get("take_profit")),
            "account_login": str(getattr(account, "login", "")) if account else "",
            "server": str(getattr(account, "server", "")) if account else "",
            "environment": "DEMO",
            "mt5_result": mt5_result or {},
            "single_trade_limit": 1,
            "execution_allowed": False,
            "simulation_only": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def _result(
        self,
        status: str,
        payload: dict[str, Any],
        blockers: list[str],
        reason: str,
        demo_order_attempted: bool = False,
    ) -> dict[str, Any]:
        symbol = str(payload.get("symbol") or "").strip().upper()
        lot = self._float_or_none(payload.get("lot")) or 0.0
        return {
            "request_id": f"guarded-demo-order-{uuid4()}",
            "status": status,
            "environment": "DEMO",
            "symbol": symbol,
            "action": str(payload.get("action") or "").strip().upper(),
            "lot": lot,
            "order_request_preview": self._preview(payload) if not blockers else {},
            "mt5_order_sent": False,
            "demo_order_attempted": demo_order_attempted,
            "live_order_attempted": False,
            "reason": reason,
            "blockers": blockers,
            "single_trade_limit": 1,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def _preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": str(payload.get("symbol") or "").strip().upper(),
            "type": str(payload.get("action") or "").strip().upper(),
            "volume": self._float_or_none(payload.get("lot")),
            "price": self._float_or_none(payload.get("entry_price")),
            "sl": self._float_or_none(payload.get("stop_loss")),
            "tp": self._float_or_none(payload.get("take_profit")),
            "comment": "GUARDED_DEMO_PREPARE_ONLY",
        }

    def _float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _positive_int(self, value: Any) -> int | None:
        try:
            number = int(str(value))
        except (TypeError, ValueError):
            return None
        return number if number > 0 else 0

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
