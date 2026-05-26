from typing import Any

from backend.institutional_intelligence.performance_analytics_models import PaperTradePerformanceMetrics


class PaperTradePerformanceAnalyzer:
    """Analyze paper results while deduplicating repeated lifecycle snapshots."""

    def analyze_paper_trades(self, paper_trade_contexts: list[Any] | None) -> PaperTradePerformanceMetrics:
        candidates: dict[str, Any] = {}
        positions: dict[str, Any] = {}
        for context in paper_trade_contexts or []:
            for candidate in self._items(context, "candidates"):
                candidates[str(self._get(candidate, "candidate_id"))] = candidate
            for position in self._items(context, "active_positions") + self._items(context, "closed_positions"):
                positions[str(self._get(position, "position_id"))] = position
        closed = [position for position in positions.values() if self._get(position, "status") == "CLOSED"]
        wins = [position for position in closed if self._get(position, "outcome") == "WIN"]
        losses = [position for position in closed if self._get(position, "outcome") == "LOSS"]
        breakevens = [position for position in closed if self._get(position, "outcome") == "BREAKEVEN"]
        rr = [float(self._get(position, "rr_result", 0.0) or 0.0) for position in closed]
        pnl = [float(self._get(position, "pnl_points", 0.0) or 0.0) for position in closed]
        return PaperTradePerformanceMetrics(
            total_candidates=len(candidates),
            activated_positions=len(positions),
            closed_positions=len(closed),
            win_count=len(wins),
            loss_count=len(losses),
            breakeven_count=len(breakevens),
            win_rate=round(len(wins) / len(closed) * 100.0, 2) if closed else 0.0,
            average_rr=round(sum(rr) / len(rr), 2) if rr else 0.0,
            average_pnl_points=round(sum(pnl) / len(pnl), 8) if pnl else 0.0,
            best_trade_rr=max(rr) if rr else 0.0,
            worst_trade_rr=min(rr) if rr else 0.0,
        )

    def _items(self, value: Any, key: str) -> list[Any]:
        return value.get(key, []) if isinstance(value, dict) else getattr(value, key, [])

    def _get(self, value: Any, key: str, default: Any = None) -> Any:
        return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)
