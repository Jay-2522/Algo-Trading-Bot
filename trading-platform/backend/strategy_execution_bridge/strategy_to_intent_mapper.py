from typing import Any

from backend.strategy_execution_bridge.bridge_models import StrategyExecutionIntent


class StrategyToIntentMapper:
    """Map approved strategy signals into non-executing intent objects."""

    DEFAULT_LOT = 0.01
    MAX_LOT = 0.01

    def map_signal_to_intent(self, signal: Any) -> StrategyExecutionIntent:
        symbol = str(self._get(signal, "symbol", "")).upper()
        action = str(self._get(signal, "action", "")).upper()
        metadata = self._get(signal, "metadata", {}) or {}
        strategy_name = metadata.get("phase") if isinstance(metadata, dict) else None
        requested_lot = float(
            self._get(signal, "total_lot", None)
            or self._get(signal, "suggested_lot", None)
            or self._get(signal, "lot", None)
            or self.DEFAULT_LOT
        )
        return StrategyExecutionIntent(
            source_signal_id=str(self._get(signal, "signal_id", "manual-signal")),
            symbol=symbol,
            action=action,
            confidence=float(self._get(signal, "confidence", 0.0) or 0.0),
            suggested_lot=requested_lot,
            allocation_mode="EQUAL",
            total_lot=requested_lot,
            strategy_name=str(strategy_name or f"{symbol}_STRATEGY"),
            reason=str(self._get(signal, "reason", "Strategy signal mapped to execution intent preview.")),
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
        )

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
