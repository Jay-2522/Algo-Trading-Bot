from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.strategy_execution_bridge.bridge_models import StrategyExecutionIntent


class QueuePreviewAdapter:
    """Create bridge-owned queue preview records without execution."""

    _previews: dict[str, dict[str, Any]] = {}

    def create_preview_from_intent(self, intent: StrategyExecutionIntent, risk_decision: Any | None = None) -> dict[str, Any]:
        preview_id = f"strategy_queue_preview_{uuid4().hex[:12]}"
        preview = {
            "queue_preview_id": preview_id,
            "source": "STRATEGY_EXECUTION_BRIDGE",
            "intent_id": intent.intent_id,
            "source_signal_id": intent.source_signal_id,
            "symbol": intent.symbol,
            "action": intent.action,
            "total_lot": intent.total_lot,
            "risk_decision_id": self._get(risk_decision, "decision_id", None),
            "status": "CREATED",
            "execution_triggered": False,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._previews[preview_id] = preview
        return preview

    def get_preview(self, queue_preview_id: str) -> dict[str, Any] | None:
        return self._previews.get(queue_preview_id)

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
