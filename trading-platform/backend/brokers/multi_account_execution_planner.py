from datetime import datetime, timezone
from typing import Any

from backend.brokers.broker_account_service import BrokerAccountService


class MultiAccountExecutionPlanner:
    """Preview future broker-account execution without placing orders."""

    def __init__(self, account_service: BrokerAccountService | None = None) -> None:
        self.account_service = account_service or BrokerAccountService()

    def status(self) -> dict[str, Any]:
        return {
            "status": "PLANNER_READY_FOUNDATION_ONLY",
            "mode": "PREVIEW_ONLY",
            "supported_brokers": ["STARTRADER", "FXPRO", "VANTAGE"],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "mt5_order_send_used": False,
            "timestamp": self._timestamp(),
        }

    def preview(self, signal: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "symbol": str(signal.get("symbol") or "").strip().upper(),
            "side": str(signal.get("side") or signal.get("action") or "").strip().upper(),
            "lot": self._number(signal.get("lot")),
            "entry": self._number(signal.get("entry") or signal.get("entry_price")),
            "sl": self._number(signal.get("sl") or signal.get("stop_loss")),
            "tp": self._number(signal.get("tp") or signal.get("take_profit")),
        }
        plans = []
        for account in self.account_service.list_accounts():
            connected = account.connection_status == "CONNECTED"
            future_ready = bool(account.enabled) and connected and not account.execution_enabled
            if not connected:
                status = "PENDING_CONNECTION"
                eligible = False
                reason = "Broker account not connected yet."
            elif not self._valid_signal(normalized):
                status = "BLOCKED"
                eligible = False
                reason = "Signal is incomplete."
            elif account.execution_enabled:
                status = "BLOCKED"
                eligible = False
                reason = "Broker execution remains disabled by safety policy."
            else:
                status = "READY_FOR_FUTURE"
                eligible = future_ready
                reason = "Account can be considered after future broker connection and explicit execution enablement."
            plans.append(
                {
                    "broker_id": account.broker_id,
                    "broker_name": account.broker_name,
                    "eligible": eligible,
                    "reason": reason,
                    "execution_status": status,
                    "live_execution_enabled": False,
                    "broker_execution_enabled": False,
                    "execution_allowed": False,
                }
            )
        return {
            "status": "PREVIEW_ONLY",
            "signal": normalized,
            "plans": plans,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "mt5_order_send_used": False,
            "timestamp": self._timestamp(),
        }

    def _valid_signal(self, signal: dict[str, Any]) -> bool:
        return (
            signal["symbol"] in {"EURUSD", "XAUUSD"}
            and signal["side"] in {"BUY", "SELL"}
            and all(isinstance(signal[key], (int, float)) and signal[key] > 0 for key in ["lot", "entry", "sl", "tp"])
        )

    def _number(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip():
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
