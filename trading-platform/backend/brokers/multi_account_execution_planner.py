from datetime import datetime, timezone
import hashlib
from typing import Any

from backend.brokers.broker_account_service import BrokerAccountService


class DuplicateTradeProtection:
    def __init__(self) -> None:
        self._recent_hashes: set[str] = set()

    def check(self, broker_id: str, account_login: str | None, symbol: str, direction: str, signal_hash: str) -> dict[str, Any]:
        key = self._key(broker_id, account_login, symbol, direction, signal_hash)
        duplicate = key in self._recent_hashes
        if not duplicate:
            self._recent_hashes.add(key)
        return {
            "duplicate": duplicate,
            "signal_hash": signal_hash,
            "reason": "Duplicate recent signal for broker/account/symbol/direction." if duplicate else "No duplicate recent signal detected.",
        }

    def _key(self, broker_id: str, account_login: str | None, symbol: str, direction: str, signal_hash: str) -> str:
        return "|".join([broker_id, account_login or "NO_ACCOUNT", symbol, direction, signal_hash])


class MultiAccountExecutionPlanner:
    """Preview future broker-account execution without placing orders."""

    supported_symbols_by_broker = {
        "STARTRADER": {"EURUSD", "XAUUSD"},
        "FXPRO": {"EURUSD", "XAUUSD"},
        "VANTAGE": {"EURUSD", "XAUUSD"},
    }

    def __init__(self, account_service: BrokerAccountService | None = None, duplicate_protection: DuplicateTradeProtection | None = None) -> None:
        self.account_service = account_service or BrokerAccountService()
        self.duplicate_protection = duplicate_protection or DuplicateTradeProtection()

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

    def copy_readiness(self) -> dict[str, Any]:
        return self.preview(
            {
                "symbol": "EURUSD",
                "side": "BUY",
                "lot": 0.01,
                "entry": 1.0,
                "sl": 0.99,
                "tp": 1.02,
                "signal_hash": "COPY_READINESS_STATUS",
                "record_duplicate": False,
            }
        ) | {"status": "COPY_READINESS_PREVIEW_ONLY"}

    def preview(self, signal: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "symbol": str(signal.get("symbol") or "").strip().upper(),
            "side": str(signal.get("side") or signal.get("action") or "").strip().upper(),
            "lot": self._number(signal.get("lot")),
            "entry": self._number(signal.get("entry") or signal.get("entry_price")),
            "sl": self._number(signal.get("sl") or signal.get("stop_loss")),
            "tp": self._number(signal.get("tp") or signal.get("take_profit")),
            "signal_hash": str(signal.get("signal_hash") or "").strip(),
        }
        if not normalized["signal_hash"]:
            normalized["signal_hash"] = self._signal_hash(normalized)
        plans = []
        for account in self.account_service.list_accounts():
            plans.append(self._plan_for_account(account, normalized, bool(signal.get("record_duplicate", True))))
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

    def _plan_for_account(self, account: Any, signal: dict[str, Any], record_duplicate: bool) -> dict[str, Any]:
        config = self.account_service.get_account_config(account.broker_id)
        blocked_reasons: list[str] = []
        connected = account.connection_status == "CONNECTED"
        if not connected:
            blocked_reasons.append("Broker account not connected yet.")
        if not account.enabled:
            blocked_reasons.append("Broker account is disabled.")
        if account.broker_id not in self.supported_symbols_by_broker:
            blocked_reasons.append("Broker is not supported.")
        if signal["symbol"] not in self.supported_symbols_by_broker.get(account.broker_id, set()):
            blocked_reasons.append("Symbol is not supported by broker.")
        if signal["side"] not in {"BUY", "SELL"}:
            blocked_reasons.append("Direction must be BUY or SELL.")
        if not isinstance(signal["lot"], (int, float)) or signal["lot"] <= 0:
            blocked_reasons.append("Lot size is invalid.")
        if not isinstance(signal["sl"], (int, float)) or signal["sl"] <= 0:
            blocked_reasons.append("Stop loss is required.")
        if not isinstance(signal["tp"], (int, float)) or signal["tp"] <= 0:
            blocked_reasons.append("Take profit is required.")
        if len(config.open_positions) >= config.max_open_trades:
            blocked_reasons.append("Max open trades exceeded.")
        open_position_duplicate = any(
            str(position.get("symbol", "")).upper() == signal["symbol"] and str(position.get("side", position.get("direction", ""))).upper() == signal["side"]
            for position in config.open_positions
        )
        if open_position_duplicate:
            blocked_reasons.append("Already open position for same symbol and direction.")

        duplicate = (
            self.duplicate_protection.check(account.broker_id, account.account_login, signal["symbol"], signal["side"], signal["signal_hash"])
            if record_duplicate
            else {"duplicate": False, "signal_hash": signal["signal_hash"], "reason": "Duplicate check preview only."}
        )
        if duplicate["duplicate"]:
            blocked_reasons.append(duplicate["reason"])

        live_disabled = True
        if live_disabled:
            blocked_reasons.append("Live execution disabled guard is active.")

        adjusted_lot = self._adjust_lot(signal["lot"])
        demo_ready_blockers = [
            reason
            for reason in blocked_reasons
            if reason
            not in {
                "Live execution disabled guard is active.",
            }
        ]
        if demo_ready_blockers:
            final_decision = "BLOCKED"
            readiness_status = "BLOCKED"
        elif account.account_type == "LIVE":
            final_decision = "READY_FOR_LIVE_DISABLED"
            readiness_status = "LIVE_DISABLED"
        else:
            final_decision = "READY_FOR_DEMO"
            readiness_status = "READY_FOR_DEMO_PREVIEW"
        return {
            "broker_id": account.broker_id,
            "broker_name": account.broker_name,
            "connection_status": account.connection_status,
            "execution_enabled": False,
            "account_type": account.account_type,
            "balance": account.balance,
            "equity": account.equity,
            "requested_symbol": signal["symbol"],
            "direction": signal["side"],
            "requested_lot": signal["lot"],
            "adjusted_lot": adjusted_lot,
            "readiness_status": readiness_status,
            "blocked_reasons": blocked_reasons,
            "duplicate_protection": duplicate | {"already_open_position": open_position_duplicate},
            "final_execution_decision": final_decision,
            "eligible": final_decision != "BLOCKED",
            "reason": "; ".join(blocked_reasons) if blocked_reasons else "Preview ready; execution remains disabled.",
            "execution_status": "PENDING_CONNECTION" if account.connection_status != "CONNECTED" else final_decision,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _adjust_lot(self, lot: float | None) -> float | None:
        if not isinstance(lot, (int, float)) or lot <= 0:
            return None
        return round(max(0.01, lot), 2)

    def _signal_hash(self, signal: dict[str, Any]) -> str:
        raw = "|".join(str(signal.get(key)) for key in ["symbol", "side", "lot", "entry", "sl", "tp"])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

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
