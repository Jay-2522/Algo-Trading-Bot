import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SignalHistoryService:
    """Lightweight persistence for generated client strategy signals."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("data/client_signals/signal_history.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, signal: dict[str, Any]) -> dict[str, Any]:
        entry = {
            "symbol": signal.get("symbol"),
            "signal": signal.get("signal"),
            "timestamp": signal.get("timestamp") or self._timestamp(),
            "confidence": signal.get("confidence"),
            "execution_status": signal.get("execution_status"),
        }
        history = self.history()
        history.append(entry)
        self.storage_path.write_text(json.dumps(history[-500:], indent=2), encoding="utf-8")
        return entry

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)][-limit:]

    def history_for_symbol(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        normalized = str(symbol or "").strip().upper()
        return [item for item in self.history(500) if item.get("symbol") == normalized][-limit:]

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
