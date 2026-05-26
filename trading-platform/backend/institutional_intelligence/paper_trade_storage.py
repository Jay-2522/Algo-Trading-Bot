from datetime import datetime, timezone
from typing import Any

from backend.institutional_intelligence.paper_trade_models import PaperTradeCandidate, PaperTradePosition


class PaperTradeStorage:
    """Resilient in-memory paper lifecycle store; never stores broker instructions."""

    def __init__(self) -> None:
        self._candidates: dict[str, PaperTradeCandidate] = {}
        self._positions: dict[str, PaperTradePosition] = {}
        self._logs: list[dict[str, Any]] = []

    def save_candidate(self, candidate: PaperTradeCandidate) -> PaperTradeCandidate:
        self._candidates[candidate.candidate_id] = candidate
        return candidate

    def save_position(self, position: PaperTradePosition) -> PaperTradePosition:
        self._positions[position.position_id] = position
        return position

    def get_candidates(self, symbol: str, timeframe: str | None = None) -> list[PaperTradeCandidate]:
        normalized = symbol.strip().upper()
        items = [
            candidate
            for candidate in self._candidates.values()
            if candidate.symbol == normalized and (timeframe is None or candidate.timeframe == timeframe)
        ]
        return sorted(items, key=lambda item: item.created_at)

    def get_positions(self, symbol: str) -> list[PaperTradePosition]:
        normalized = symbol.strip().upper()
        items = [position for position in self._positions.values() if position.symbol == normalized]
        return sorted(items, key=lambda item: item.opened_at)

    def get_open_candidate(self, symbol: str, timeframe: str) -> PaperTradeCandidate | None:
        candidates = [
            candidate
            for candidate in self.get_candidates(symbol, timeframe)
            if candidate.status in {"PENDING", "ACTIVE"}
        ]
        return candidates[-1] if candidates else None

    def get_position_for_candidate(self, candidate_id: str) -> PaperTradePosition | None:
        matches = [position for position in self._positions.values() if position.candidate_id == candidate_id]
        return matches[-1] if matches else None

    def log_event(self, event_type: str, reference_id: str, metadata: dict[str, Any] | None = None) -> None:
        self._logs.append(
            {
                "event_type": event_type,
                "reference_id": reference_id,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "simulation_only": True,
            }
        )

    def get_logs(self, reference_id: str | None = None) -> list[dict[str, Any]]:
        if reference_id is None:
            return list(self._logs)
        return [log for log in self._logs if log["reference_id"] == reference_id]
