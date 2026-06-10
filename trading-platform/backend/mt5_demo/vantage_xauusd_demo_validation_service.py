from datetime import datetime, timezone
from typing import Any


class VantageXAUUSDDemoValidationService:
    """Vantage XAUUSD demo validation wrapper around the existing guarded sender."""

    symbol = "XAUUSD"
    broker = "VANTAGE_DEMO"
    max_lot = 0.01
    max_spread = 1.0

    def __init__(
        self,
        mt5_demo_service: Any,
        market_data_service: Any,
        approval_workflow_service: Any,
        guarded_sender_service: Any,
        position_sync_service: Any,
        lifecycle_service: Any,
    ) -> None:
        self.mt5_demo_service = mt5_demo_service
        self.market_data_service = market_data_service
        self.approval_workflow_service = approval_workflow_service
        self.guarded_sender_service = guarded_sender_service
        self.position_sync_service = position_sync_service
        self.lifecycle_service = lifecycle_service
        self._latest_preview: dict[str, Any] | None = None
        self._latest_order: dict[str, Any] | None = None
        self._test_order_attempted = False

    def preview(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        readiness = self._readiness(payload, require_confirm=False)
        side = str(payload.get("side") or payload.get("action") or "BUY").strip().upper()
        tick = readiness["tick"]
        entry = self._entry_estimate(side, tick)
        result = {
            "would_send": False,
            "broker": self.broker,
            "broker_detected": readiness["broker_detected"],
            "symbol": self.symbol,
            "side": side,
            "lot": self._float_or_none(payload.get("lot")) or self.max_lot,
            "entry_estimate": entry,
            "stop_loss": self._float_or_none(payload.get("stop_loss") or payload.get("sl")),
            "take_profit": self._float_or_none(payload.get("take_profit") or payload.get("tp")),
            "spread": tick.get("spread"),
            "blocked_reasons": readiness["blockers"],
            "readiness_decision": "READY_FOR_GUARDED_DEMO_TEST" if not readiness["blockers"] else "BLOCKED",
            "tick_status": tick.get("status"),
            "tick_recovery_status": tick.get("tick_recovery_status"),
            "source": tick.get("source"),
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
            result = {
                **preview,
                "status": "BLOCKED",
                "would_send": False,
                "mt5_order_sent": False,
                "guarded_sender_used": False,
                "blocked_reasons": readiness["blockers"],
            }
            self._latest_order = result
            return result

        side = str(payload.get("side") or payload.get("action")).strip().upper()
        tick = readiness["tick"]
        guarded_payload = {
            "environment": "DEMO",
            "symbol": self.symbol,
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
            "allow_xauusd_vantage_demo_test": True,
            "execute_single_demo_order_now": True,
        }
        approval_payload = {
            **guarded_payload,
            "acknowledge_no_order_placement_today": True,
        }
        approval = self.approval_workflow_service.run_workflow(approval_payload)
        if approval.get("approved_for_future_demo_order") is not True:
            result = {
                **preview,
                "status": "BLOCKED",
                "would_send": False,
                "mt5_order_sent": False,
                "guarded_sender_used": False,
                "approval_result": approval,
                "blocked_reasons": sorted(set([*readiness["blockers"], *approval.get("blockers", ["APPROVAL_WORKFLOW_NOT_APPROVED"])])),
            }
            self._latest_order = result
            return result

        self._test_order_attempted = True
        result = self.guarded_sender_service.send_order(guarded_payload)
        result["broker"] = self.broker
        result["guarded_sender_used"] = True
        result["approval_result"] = approval
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
        tick = self.market_data_service.get_symbol_tick(self.symbol)
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
        if str(payload.get("symbol") or self.symbol).strip().upper() != self.symbol:
            blockers.append("XAUUSD_SYMBOL_REQUIRED")
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
        if tick.get("status") != "OK":
            blockers.append("XAUUSD_TICK_NOT_READY")
        if tick.get("spread") is None:
            blockers.append("SPREAD_UNAVAILABLE")
        elif float(tick["spread"]) > self.max_spread:
            blockers.append("SPREAD_TOO_WIDE")
        if self._test_order_attempted:
            blockers.append("DUPLICATE_VANTAGE_XAUUSD_TEST_ORDER_BLOCKED")
        if payload.get("live_execution_enabled") is not False:
            blockers.append("LIVE_EXECUTION_FLAG_MUST_BE_FALSE")
        if payload.get("broker_execution_enabled") is True:
            blockers.append("BROKER_EXECUTION_MUST_REMAIN_DISABLED")
        return {
            "account": account,
            "tick": tick,
            "broker_detected": self._broker_detected(account),
            "blockers": sorted(set(blockers)),
        }

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
