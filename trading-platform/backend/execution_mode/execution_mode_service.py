from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class ExecutionModeService:
    """Configurable AUTO/APPROVAL layer that only delegates to the guarded demo sender."""

    default_ttl_seconds = 30

    def __init__(
        self,
        signal_provider: Any | None = None,
        guarded_execution_service: Any | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.signal_provider = signal_provider
        self.guarded_execution_service = guarded_execution_service
        self.config_path = config_path or Path(__file__).with_name("execution_mode_config.json")
        self._pending: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._processed_auto_hashes: set[str] = set()
        self._config = self._load_config()

    def status(self) -> dict[str, Any]:
        config = self.get_config()
        return {
            "status": "READY",
            "config": config,
            "execution_mode": config["execution_mode"],
            "auto_enabled": config["auto_enabled"],
            "approval_required": config["approval_required"],
            "pending_approvals": self.pending_approvals(),
            "history": self.history(20),
            "last_auto_executed_signal": self._last_event("ORDER_SENT", mode="AUTO"),
            "blocked_auto_attempts": [item for item in reversed(self._history) if item.get("mode") == "AUTO" and str(item.get("event", "")).startswith("BLOCKED")][:10],
            "safety_flags": self._safety_flags(config),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def get_config(self) -> dict[str, Any]:
        return dict(self._config)

    def set_config(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        mode = str(payload.get("execution_mode") or self._config.get("execution_mode") or "APPROVAL").strip().upper()
        if mode not in {"AUTO", "APPROVAL"}:
            mode = "APPROVAL"
        config = self._default_config()
        config.update(
            {
                "execution_mode": mode,
                "auto_enabled": mode == "AUTO",
                "approval_required": mode == "APPROVAL",
                "allowed_symbols": self._clean_list(payload.get("allowed_symbols"), {"EURUSD", "XAUUSD"}),
                "allowed_brokers": self._clean_list(payload.get("allowed_brokers"), {"VANTAGE_DEMO"}),
                "max_lot_per_trade": min(self._number(payload.get("max_lot_per_trade"), 0.01), 0.01),
                "require_sl_tp": bool(payload.get("require_sl_tp", True)),
                "require_rr_minimum": self._number(payload.get("require_rr_minimum"), 1.5),
                "require_duplicate_check": bool(payload.get("require_duplicate_check", True)),
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "updated_at": self._timestamp(),
            }
        )
        self._config = config
        self._save_config(config)
        self._log("MODE_UPDATED", mode=mode, details={"requested": payload, "applied": config})
        return self.status()

    def observe_signal(self, signal: dict[str, Any] | None) -> dict[str, Any]:
        signal = signal or {}
        symbol = self._symbol(signal)
        if not symbol:
            return {"status": "IGNORED", "reason": "SYMBOL_REQUIRED"}
        self._log("SIGNAL_RECEIVED", signal=signal, mode=self._config["execution_mode"])
        if not self._ready(signal):
            return {"status": "IGNORED", "reason": "SIGNAL_NOT_READY"}

        if self._config["execution_mode"] == "AUTO":
            return self._handle_auto(signal)
        return self._create_pending(signal)

    def pending_approvals(self) -> list[dict[str, Any]]:
        self._expire_pending()
        return [record for record in self._pending.values() if record.get("status") == "PENDING"]

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-max(1, min(limit, 500)) :]

    def approve_signal(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        record = self._find_pending(payload)
        if record is None:
            result = self._blocked("MANUAL_APPROVE", "PENDING_APPROVAL_NOT_FOUND", payload=payload)
            self._log("BLOCKED_STALE_SIGNAL", mode="APPROVAL", details=result)
            return result
        if self._expired(record):
            record["status"] = "EXPIRED"
            result = self._blocked("MANUAL_APPROVE", "SIGNAL_EXPIRED", signal=record["signal"])
            self._log("BLOCKED_STALE_SIGNAL", signal=record["signal"], mode="APPROVAL", details=result)
            return result
        execution = self._execute_signal(record["signal"], mode="APPROVAL", manual=True)
        record["status"] = "APPROVED" if execution.get("status") == "ORDER_SENT" else "BLOCKED"
        record["decision"] = execution
        return execution

    def reject_signal(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        record = self._find_pending(payload)
        reason = str(payload.get("reason") or "Rejected manually.").strip()
        if record is None:
            result = self._blocked("MANUAL_REJECT", "PENDING_APPROVAL_NOT_FOUND", payload=payload)
            self._log("BLOCKED_STALE_SIGNAL", mode="APPROVAL", details=result)
            return result
        record["status"] = "REJECTED"
        record["rejection_reason"] = reason
        record["rejected_at"] = self._timestamp()
        result = {
            "status": "REJECTED",
            "approval_id": record["approval_id"],
            "signal_hash": record["signal"].get("signal_hash"),
            "reason": reason,
            "mt5_order_sent": False,
            "guarded_sender_used": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }
        self._log("REJECTED_MANUALLY", signal=record["signal"], mode="APPROVAL", details=result)
        return result

    def _handle_auto(self, signal: dict[str, Any]) -> dict[str, Any]:
        signal_hash = str(signal.get("signal_hash") or self._fallback_hash(signal))
        if signal_hash in self._processed_auto_hashes:
            result = self._blocked("AUTO", "DUPLICATE_SIGNAL_BLOCKED", signal=signal)
            self._log("BLOCKED_DUPLICATE", signal=signal, mode="AUTO", details=result)
            return result
        result = self._execute_signal(signal, mode="AUTO", manual=False)
        if result.get("status") in {"ORDER_SENT", "ORDER_FAILED", "BLOCKED"}:
            self._processed_auto_hashes.add(signal_hash)
        return result

    def _create_pending(self, signal: dict[str, Any]) -> dict[str, Any]:
        existing = self._find_pending({"signal_hash": signal.get("signal_hash"), "symbol": signal.get("symbol")})
        if existing:
            return {"status": "PENDING_APPROVAL_EXISTS", "approval": existing}
        created_at = datetime.now(timezone.utc)
        record = {
            "approval_id": f"approval-{uuid4()}",
            "status": "PENDING",
            "mode": "APPROVAL",
            "signal": signal,
            "symbol": self._symbol(signal),
            "signal_hash": signal.get("signal_hash"),
            "action": str(signal.get("signal") or "").upper(),
            "entry": signal.get("entry"),
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("take_profit"),
            "risk_reward": signal.get("risk_reward"),
            "confidence": signal.get("confidence"),
            "broker": "VANTAGE_DEMO",
            "account": self._signal_account(signal),
            "created_at": created_at.isoformat(),
            "expires_at": (created_at + timedelta(seconds=self.default_ttl_seconds)).isoformat(),
            "ttl_seconds": self.default_ttl_seconds,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }
        self._pending[record["approval_id"]] = record
        self._log("PENDING_APPROVAL_CREATED", signal=signal, mode="APPROVAL", details=record)
        return {"status": "PENDING_APPROVAL_CREATED", "approval": record}

    def _execute_signal(self, signal: dict[str, Any], mode: str, manual: bool) -> dict[str, Any]:
        validation = self._validate_signal(signal)
        if validation["blockers"]:
            event = self._blocked_event(validation["blockers"])
            result = self._blocked("EXECUTE", validation["blockers"], signal=signal)
            self._log(event, signal=signal, mode=mode, details=result)
            return result
        payload = self._guarded_payload(validation["signal"])
        service = self.guarded_execution_service
        if service is None:
            result = self._blocked("EXECUTE", "GUARDED_SENDER_UNAVAILABLE", signal=signal)
            self._log("ORDER_FAILED", signal=signal, mode=mode, details=result)
            return result
        result = service.send_test_order(payload)
        sent = result.get("status") == "DEMO_ORDER_SENT" and result.get("mt5_order_sent") is True
        response = {
            "status": "ORDER_SENT" if sent else "ORDER_FAILED",
            "mode": mode,
            "manual_approval": manual,
            "guarded_sender_used": result.get("guarded_sender_used") is True,
            "mt5_order_sent": bool(result.get("mt5_order_sent")),
            "signal_hash": validation["signal"].get("signal_hash"),
            "symbol": validation["signal"].get("symbol"),
            "sender_result": result,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }
        self._log("ORDER_SENT" if sent else "ORDER_FAILED", signal=validation["signal"], mode=mode, details=response)
        return response

    def _validate_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        current = self._current_signal(signal)
        blockers: list[str] = []
        config = self._config
        symbol = self._symbol(signal)
        action = str(signal.get("signal") or "").upper()
        rr = self._number(signal.get("risk_reward"), 0)
        lot = 0.01

        if self._expired_signal(signal):
            blockers.append("SIGNAL_EXPIRED")
        if symbol not in set(config["allowed_symbols"]):
            blockers.append("SYMBOL_NOT_ALLOWED")
        if "VANTAGE_DEMO" not in set(config["allowed_brokers"]):
            blockers.append("VANTAGE_DEMO_BROKER_REQUIRED")
        if action not in {"BUY", "SELL"}:
            blockers.append("SIGNAL_DIRECTION_REQUIRED")
        if lot > float(config["max_lot_per_trade"]):
            blockers.append("LOT_EXCEEDS_MAX")
        if config["require_sl_tp"] and not all(self._number(signal.get(key), 0) > 0 for key in ["entry", "stop_loss", "take_profit"]):
            blockers.append("SL_TP_REQUIRED")
        if rr < float(config["require_rr_minimum"]):
            blockers.append("RR_BELOW_MINIMUM")
        if signal.get("live_execution_enabled") is True or config["live_execution_enabled"] is True:
            blockers.append("LIVE_EXECUTION_BLOCKED")
        if signal.get("broker_execution_enabled") is True or config["broker_execution_enabled"] is True:
            blockers.append("BROKER_EXECUTION_BLOCKED")
        if current is not None:
            if current.get("execution_status") != "READY_FOR_PREVIEW":
                blockers.append("SIGNAL_NO_LONGER_READY_FOR_PREVIEW")
            if current.get("risk_status") != "APPROVED":
                blockers.append("SIGNAL_NO_LONGER_APPROVED")
            if str(current.get("signal") or "").upper() != action:
                blockers.append("SIGNAL_DIRECTION_CHANGED")
            if signal.get("signal_hash") and current.get("signal_hash") != signal.get("signal_hash"):
                blockers.append("SIGNAL_HASH_CHANGED")
            signal = current

        account_type = str((self._signal_account(signal) or {}).get("account_type") or "").upper()
        broker = str((self._signal_account(signal) or {}).get("broker_source") or (self._signal_account(signal) or {}).get("source") or "").upper()
        if account_type and account_type != "DEMO":
            blockers.append("NON_DEMO_ACCOUNT_BLOCKED")
        if broker and broker != "VANTAGE_DEMO":
            blockers.append("VANTAGE_DEMO_ONLY")
        return {"signal": signal, "blockers": sorted(set(blockers))}

    def _current_signal(self, signal: dict[str, Any]) -> dict[str, Any] | None:
        if self.signal_provider is None:
            return None
        symbol = self._symbol(signal)
        if not symbol:
            return None
        try:
            return self.signal_provider.signal_for_symbol(symbol, record_history=False)
        except TypeError:
            return self.signal_provider.signal_for_symbol(symbol)
        except Exception:
            return None

    def _guarded_payload(self, signal: dict[str, Any]) -> dict[str, Any]:
        action = str(signal.get("signal") or "").upper()
        symbol = self._symbol(signal)
        source = self._signal_account(signal) or {}
        return {
            "symbol": symbol,
            "side": action,
            "action": action,
            "lot": 0.01,
            "entry_price": self._number(signal.get("entry"), 0),
            "stop_loss": self._number(signal.get("stop_loss"), 0),
            "take_profit": self._number(signal.get("take_profit"), 0),
            "risk_reward_ratio": self._number(signal.get("risk_reward"), 0),
            "signal_confidence": self._number(signal.get("confidence"), 0),
            "signal_hash": signal.get("signal_hash"),
            "signal_timestamp": signal.get("timestamp"),
            "setup_reason": signal.get("setup_reason") or signal.get("reason"),
            "strategy_metadata": {
                "market_structure_state": signal.get("market_structure_state") or {},
                "strategy_components": signal.get("strategy_components") or {},
                "quality_score": signal.get("quality_score") or {},
                "approval_audit": signal.get("approval_audit") or {},
                "candle_source": signal.get("candle_source") or {},
            },
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
            "broker_id": "VANTAGE_DEMO",
            "broker_source": source.get("broker_source") or source.get("source") or "VANTAGE_DEMO",
        }

    def _ready(self, signal: dict[str, Any]) -> bool:
        return signal.get("execution_status") == "READY_FOR_PREVIEW" and signal.get("risk_status") == "APPROVED" and str(signal.get("signal") or "").upper() in {"BUY", "SELL"}

    def _expired_pending(self) -> None:
        self._expire_pending()

    def _expire_pending(self) -> None:
        for record in self._pending.values():
            if record.get("status") == "PENDING" and self._expired(record):
                record["status"] = "EXPIRED"
                self._log("BLOCKED_STALE_SIGNAL", signal=record["signal"], mode="APPROVAL", details={"reason": "SIGNAL_EXPIRED", "approval_id": record["approval_id"]})

    def _expired(self, record: dict[str, Any]) -> bool:
        try:
            expires_at = datetime.fromisoformat(str(record.get("expires_at")).replace("Z", "+00:00"))
        except ValueError:
            return True
        return datetime.now(timezone.utc) > expires_at

    def _expired_signal(self, signal: dict[str, Any]) -> bool:
        timestamp = signal.get("timestamp")
        if not timestamp:
            return True
        try:
            created = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return True
        return (datetime.now(timezone.utc) - created).total_seconds() > self.default_ttl_seconds

    def _find_pending(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        approval_id = str(payload.get("approval_id") or "").strip()
        if approval_id and approval_id in self._pending:
            return self._pending[approval_id]
        signal_hash = str(payload.get("signal_hash") or "").strip()
        symbol = str(payload.get("symbol") or "").strip().upper()
        for record in self._pending.values():
            if record.get("status") != "PENDING":
                continue
            if signal_hash and record.get("signal_hash") == signal_hash:
                return record
            if symbol and record.get("symbol") == symbol:
                return record
        return None

    def _blocked(self, action: str, blockers: Any, signal: dict[str, Any] | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        reasons = blockers if isinstance(blockers, list) else [str(blockers)]
        return {
            "status": "BLOCKED",
            "action": action,
            "blockers": reasons,
            "signal_hash": (signal or {}).get("signal_hash"),
            "symbol": (signal or payload or {}).get("symbol"),
            "mt5_order_sent": False,
            "guarded_sender_used": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def _blocked_event(self, blockers: list[str]) -> str:
        if any("DUPLICATE" in item for item in blockers):
            return "BLOCKED_DUPLICATE"
        if any("EXPIRED" in item or "HASH_CHANGED" in item or "NO_LONGER" in item for item in blockers):
            return "BLOCKED_STALE_SIGNAL"
        return "BLOCKED_BY_RISK"

    def _signal_account(self, signal: dict[str, Any]) -> dict[str, Any]:
        source = signal.get("candle_source")
        return source if isinstance(source, dict) else {}

    def _symbol(self, signal: dict[str, Any]) -> str:
        return str(signal.get("symbol") or "").strip().upper()

    def _log(self, event: str, signal: dict[str, Any] | None = None, mode: str | None = None, details: dict[str, Any] | None = None) -> None:
        self._history.append(
            {
                "event": event,
                "mode": mode or self._config.get("execution_mode", "APPROVAL"),
                "symbol": self._symbol(signal or {}),
                "signal_hash": (signal or {}).get("signal_hash"),
                "details": details or {},
                "timestamp": self._timestamp(),
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            }
        )

    def _last_event(self, event: str, mode: str | None = None) -> dict[str, Any] | None:
        for item in reversed(self._history):
            if item.get("event") == event and (mode is None or item.get("mode") == mode):
                return item
        return None

    def _safety_flags(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "demo_only": True,
            "vantage_demo_only": config["allowed_brokers"] == ["VANTAGE_DEMO"],
            "live_disabled": config["live_execution_enabled"] is False,
            "broker_execution_disabled": config["broker_execution_enabled"] is False,
            "max_lot": config["max_lot_per_trade"],
            "allowed_symbols": config["allowed_symbols"],
            "duplicate_check_required": config["require_duplicate_check"],
        }

    def _default_config(self) -> dict[str, Any]:
        return {
            "execution_mode": "APPROVAL",
            "auto_enabled": False,
            "approval_required": True,
            "allowed_symbols": ["EURUSD", "XAUUSD"],
            "allowed_brokers": ["VANTAGE_DEMO"],
            "max_lot_per_trade": 0.01,
            "require_sl_tp": True,
            "require_rr_minimum": 1.5,
            "require_duplicate_check": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "updated_at": self._timestamp(),
        }

    def _load_config(self) -> dict[str, Any]:
        default = self._default_config()
        try:
            if self.config_path.exists():
                loaded = json.loads(self.config_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    default.update(loaded)
        except Exception:
            pass
        default["live_execution_enabled"] = False
        default["broker_execution_enabled"] = False
        if default.get("execution_mode") not in {"AUTO", "APPROVAL"}:
            default["execution_mode"] = "APPROVAL"
        default["auto_enabled"] = default["execution_mode"] == "AUTO"
        default["approval_required"] = default["execution_mode"] == "APPROVAL"
        return default

    def _save_config(self, config: dict[str, Any]) -> None:
        try:
            self.config_path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
        except Exception:
            pass

    def _clean_list(self, value: Any, allowed: set[str]) -> list[str]:
        items = value if isinstance(value, list) else sorted(allowed)
        cleaned = sorted({str(item).strip().upper() for item in items if str(item).strip().upper() in allowed})
        return cleaned or sorted(allowed)

    def _fallback_hash(self, signal: dict[str, Any]) -> str:
        return "|".join(str(signal.get(key)) for key in ["symbol", "signal", "entry", "stop_loss", "take_profit"])

    def _number(self, value: Any, fallback: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return fallback
        return number

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
