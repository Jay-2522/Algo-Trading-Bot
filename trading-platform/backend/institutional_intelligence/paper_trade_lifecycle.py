from datetime import datetime, timedelta, timezone
from typing import Any

from backend.institutional_intelligence.paper_trade_models import PaperTradeCandidate, PaperTradePosition
from backend.institutional_intelligence.paper_trade_outcome_evaluator import PaperTradeOutcomeEvaluator


class PaperTradeLifecycleEngine:
    """Create and transition simulated positions from approved analytical decisions only."""

    def __init__(
        self,
        outcome_evaluator: PaperTradeOutcomeEvaluator | None = None,
        candidate_lifetime_hours: int = 24,
    ) -> None:
        self.outcome_evaluator = outcome_evaluator or PaperTradeOutcomeEvaluator()
        self.candidate_lifetime_hours = candidate_lifetime_hours

    def create_candidate_from_decision(self, decision_context: Any) -> PaperTradeCandidate | None:
        decision = self._get(decision_context, "decision")
        intent = self._get(decision, "order_intent")
        if (
            not self._get(decision, "approved_for_simulation")
            or self._get(intent, "direction") not in {"BUY", "SELL"}
            or not self._valid_intent(intent)
        ):
            return None
        created_at = self._timestamp(self._get(decision, "timestamp"))
        direction = self._get(intent, "direction")
        entry_low = float(self._get(intent, "entry_low"))
        entry_high = float(self._get(intent, "entry_high"))
        invalidation = float(self._get(intent, "invalidation_level"))
        target = float(self._get(intent, "target_level"))
        return PaperTradeCandidate(
            symbol=self._get(decision, "symbol"),
            timeframe=self._get(decision, "timeframe"),
            direction=direction,
            source_decision_id=self._get(decision, "decision_id"),
            source_intent_id=self._get(intent, "intent_id"),
            entry_low=entry_low,
            entry_high=entry_high,
            invalidation_level=invalidation,
            target_level=target,
            estimated_rr=float(self._get(intent, "estimated_rr") or 0.0),
            quality_score=float(self._get(decision, "confidence") or 0.0),
            created_at=created_at,
            expires_at=created_at + timedelta(hours=self.candidate_lifetime_hours),
            metadata={
                "selected_model_type": self._get(decision, "selected_model_type"),
                "risk_quality": self._get(intent, "risk_quality"),
                "intent_signature": (
                    f"{direction}:{entry_low:.8f}:{entry_high:.8f}:{invalidation:.8f}:{target:.8f}"
                ),
            },
        )

    def activate_candidate(self, candidate: PaperTradeCandidate, latest_price: float, opened_at: datetime | None = None) -> PaperTradePosition | None:
        if candidate.status != "PENDING" or not candidate.entry_low <= float(latest_price) <= candidate.entry_high:
            return None
        return PaperTradePosition(
            candidate_id=candidate.candidate_id,
            symbol=candidate.symbol,
            direction=candidate.direction,
            entry_price=round((candidate.entry_low + candidate.entry_high) / 2.0, 8),
            invalidation_level=candidate.invalidation_level,
            target_level=candidate.target_level,
            opened_at=self._timestamp(opened_at),
            metadata={"source_intent_id": candidate.source_intent_id},
        )

    def cancel_candidate(self, candidate: PaperTradeCandidate, reason: str) -> PaperTradeCandidate:
        if candidate.status not in {"PENDING", "ACTIVE"}:
            return candidate
        return candidate.model_copy(
            update={"status": "CANCELLED", "metadata": {**candidate.metadata, "cancel_reason": reason}}
        )

    def expire_candidate(self, candidate: PaperTradeCandidate, current_time: datetime) -> PaperTradeCandidate:
        if candidate.status == "PENDING" and self._timestamp(current_time) >= candidate.expires_at:
            return candidate.model_copy(
                update={"status": "EXPIRED", "metadata": {**candidate.metadata, "expire_reason": "Entry window expired."}}
            )
        return candidate

    def close_position(
        self,
        position: PaperTradePosition,
        close_price: float,
        reason: str,
        closed_at: datetime | None = None,
    ) -> PaperTradePosition:
        if position.status == "CLOSED":
            return position
        assessed = position.model_copy(
            update={
                "status": "CLOSED",
                "closed_at": self._timestamp(closed_at),
                "pnl_points": self.outcome_evaluator.calculate_pnl_points(position, close_price),
                "rr_result": self.outcome_evaluator.calculate_rr_result(position, close_price),
                "close_reason": reason,
            }
        )
        return assessed.model_copy(update={"outcome": self.outcome_evaluator.classify_outcome(assessed)})

    def _valid_intent(self, intent: Any) -> bool:
        values = [self._get(intent, key) for key in ("entry_low", "entry_high", "invalidation_level", "target_level")]
        if any(value is None for value in values):
            return False
        entry_low, entry_high, invalidation, target = [float(value) for value in values]
        direction = self._get(intent, "direction")
        has_zone = entry_high > entry_low
        valid_buy = direction == "BUY" and invalidation < entry_low < target
        valid_sell = direction == "SELL" and target < entry_high < invalidation
        return has_zone and (valid_buy or valid_sell) and bool(self._get(intent, "simulation_only"))

    def _timestamp(self, value: Any) -> datetime:
        if not isinstance(value, datetime):
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
