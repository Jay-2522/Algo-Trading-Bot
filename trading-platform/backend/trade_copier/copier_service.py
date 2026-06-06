from __future__ import annotations

from typing import Any

from backend.trade_copier.copier_models import CopierAccount, CopierBatch, CopierQueueItem, MasterSignal


class CopierFoundationService:
    """Simulation-only trade copier architecture foundation."""

    def __init__(self) -> None:
        self.master_signals: list[MasterSignal] = []
        self.queue_items: list[CopierQueueItem] = []
        self.batches: list[CopierBatch] = []
        self.accounts = [
            CopierAccount(account_id="STARTRADER_DEMO_1", label="StarTrader Demo 1"),
            CopierAccount(account_id="FXPRO_DEMO_1", label="FxPro Demo 1"),
            CopierAccount(account_id="VANTAGE_DEMO_1", label="Vantage Demo 1"),
        ]

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "ARCHITECTURE_READY_EXECUTION_DISABLED",
            "mode": "SIMULATION_ONLY",
            "master_signals": len(self.master_signals),
            "queue_items": len(self.queue_items),
            "batches": len(self.batches),
            "message": "Trade copier is architecture-ready but execution-disabled.",
            "simulation_only": True,
            "demo_execution": True,
            "execution_allowed": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def create_master_signal(self, payload: dict[str, Any]) -> MasterSignal:
        signal = MasterSignal(
            symbol=str(payload.get("symbol") or "EURUSD").upper(),
            side=str(payload.get("side") or payload.get("action") or "BUY").upper(),
            lot=float(payload.get("lot") or 0.01),
            source=str(payload.get("source") or "SIMULATION").upper(),
        )
        self.master_signals.append(signal)
        return signal

    def simulate_queue(self, payload: dict[str, Any]) -> CopierBatch:
        signal = self._resolve_signal(payload)
        if signal not in self.master_signals:
            self.master_signals.append(signal)
        items = [
            CopierQueueItem(
                master_signal_id=signal.master_signal_id,
                account_id=account.account_id,
                symbol=signal.symbol,
                side=signal.side,
                lot=signal.lot,
            )
            for account in self.accounts
        ]
        batch = CopierBatch(master_signal_id=signal.master_signal_id, queue_items=items)
        self.queue_items.extend(items)
        self.batches.append(batch)
        return batch

    def list_queue(self) -> list[CopierQueueItem]:
        return list(reversed(self.queue_items))

    def list_accounts(self) -> list[CopierAccount]:
        return self.accounts

    def list_batches(self) -> list[CopierBatch]:
        return list(reversed(self.batches))

    def get_readiness(self) -> dict[str, Any]:
        return {
            "status": "FUTURE_EXECUTION_REQUIRED",
            "architecture_ready": True,
            "execution_disabled": True,
            "broker_integration_required": True,
            "mt5_order_send_used": False,
            "message": "No copier execution will occur until a future explicit execution phase approves it.",
            "simulation_only": True,
            "demo_execution": True,
            "execution_allowed": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _resolve_signal(self, payload: dict[str, Any]) -> MasterSignal:
        signal_id = str(payload.get("master_signal_id") or "")
        existing = next((signal for signal in self.master_signals if signal.master_signal_id == signal_id), None)
        if existing:
            return existing
        return self.create_master_signal(payload)
