from typing import Any

from backend.institutional_intelligence.paper_trade_lifecycle import PaperTradeLifecycleEngine
from backend.institutional_intelligence.paper_trade_models import PaperTradeLifecycleContext
from backend.institutional_intelligence.paper_trade_storage import PaperTradeStorage
from backend.institutional_intelligence.paper_trade_tracker import PaperTradeTracker
from backend.institutional_intelligence.simulation_decision_context_builder import SimulationDecisionContextBuilder


class PaperTradeContextBuilder:
    """Advance paper lifecycle records using approved simulation decisions and observed candles."""

    def __init__(
        self,
        decision_builder: SimulationDecisionContextBuilder | None = None,
        lifecycle: PaperTradeLifecycleEngine | None = None,
        tracker: PaperTradeTracker | None = None,
        storage: PaperTradeStorage | None = None,
    ) -> None:
        self.decision_builder = decision_builder or SimulationDecisionContextBuilder()
        self.lifecycle = lifecycle or PaperTradeLifecycleEngine()
        self.tracker = tracker or PaperTradeTracker(self.lifecycle)
        self.storage = storage or PaperTradeStorage()

    def build_paper_trade_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        decision_context: Any = None,
    ) -> PaperTradeLifecycleContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        source = candles or []
        decision = decision_context or self.decision_builder.build_simulation_decision_context(
            normalized_symbol, normalized_timeframe, source
        )
        candidate = self.storage.get_open_candidate(normalized_symbol, normalized_timeframe)
        if candidate is None:
            proposed = self.lifecycle.create_candidate_from_decision(decision)
            if proposed is not None:
                signature = proposed.metadata.get("intent_signature")
                prior = [
                    stored for stored in self.storage.get_candidates(normalized_symbol, normalized_timeframe)
                    if stored.metadata.get("intent_signature") == signature
                ]
                candidate = prior[-1] if prior else proposed
                if not prior:
                    self.storage.save_candidate(candidate)
                    self.storage.log_event("CANDIDATE_CREATED", candidate.candidate_id)

        if candidate is not None and candidate.status == "PENDING":
            updated_candidate, position = self.tracker.update_candidate(candidate, source)
            candidate = self.storage.save_candidate(updated_candidate)
            if position is not None:
                self.storage.log_event("POSITION_ACTIVATED", position.position_id, {"candidate_id": candidate.candidate_id})
                position = self.storage.save_position(position)
                if position.status == "CLOSED":
                    candidate = self.storage.save_candidate(candidate.model_copy(update={"status": "CLOSED"}))
                    self.storage.log_event("POSITION_CLOSED", position.position_id, {"outcome": position.outcome})
        elif candidate is not None and candidate.status == "ACTIVE":
            position = self.storage.get_position_for_candidate(candidate.candidate_id)
            if position is not None:
                updated = self.tracker.update_position(position, source)
                self.storage.save_position(updated)
                if updated.status == "CLOSED":
                    candidate = self.storage.save_candidate(candidate.model_copy(update={"status": "CLOSED"}))
                    self.storage.log_event("POSITION_CLOSED", updated.position_id, {"outcome": updated.outcome})

        candidates = self.storage.get_candidates(normalized_symbol, normalized_timeframe)
        positions = self.storage.get_positions(normalized_symbol)
        active = [position for position in positions if position.status == "ACTIVE"]
        closed = [position for position in positions if position.status == "CLOSED"]
        lifecycle_status = self._status(candidates, active, closed, decision)
        return PaperTradeLifecycleContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            candidates=candidates,
            active_positions=active,
            closed_positions=closed,
            latest_candidate=candidates[-1] if candidates else None,
            latest_position=positions[-1] if positions else None,
            lifecycle_status=lifecycle_status,
            summary=self._summary(lifecycle_status, closed, decision),
        )

    def _status(self, candidates: list, active: list, closed: list, decision: Any) -> str:
        if active:
            return "POSITION_ACTIVE"
        if closed:
            return "POSITION_CLOSED"
        if any(candidate.status == "PENDING" for candidate in candidates):
            return "WAITING_FOR_ENTRY"
        if not self._get(self._get(decision, "decision"), "approved_for_simulation"):
            return "BLOCKED"
        return "NO_CANDIDATE"

    def _summary(self, status: str, closed: list, decision: Any) -> str:
        if status == "POSITION_CLOSED":
            latest = closed[-1]
            return f"Paper position closed as {latest.outcome} with {latest.rr_result:.2f}R simulated result."
        if status == "POSITION_ACTIVE":
            return "Paper position is active and monitoring analytical invalidation and target levels."
        if status == "WAITING_FOR_ENTRY":
            return "Approved paper candidate is waiting for price interaction with its entry zone."
        if status == "BLOCKED":
            action = self._get(self._get(decision, "decision"), "action") or "NO_TRADE"
            return f"No paper trade candidate created because simulation decision is {action}."
        return "No paper lifecycle record is available."

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
