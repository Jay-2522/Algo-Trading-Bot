from typing import Any

from backend.client_analytics.analytics_models import SessionPerformanceSummary, SymbolPerformanceSummary


class PerformanceCalculator:
    """Calculate only observable performance values; missing PnL remains zero."""

    def calculate_win_rate(self, wins: int, losses: int) -> float:
        total = wins + losses
        return round((wins / total) * 100, 2) if total else 0.0

    def calculate_net_pnl(self, trades: list[Any]) -> float:
        return round(sum(self._pnl(trade) for trade in trades), 2)

    def calculate_profit_factor(self, trades: list[Any]) -> float:
        profits = sum(pnl for pnl in [self._pnl(trade) for trade in trades] if pnl > 0)
        losses = abs(sum(pnl for pnl in [self._pnl(trade) for trade in trades] if pnl < 0))
        if profits == 0 and losses == 0:
            return 0.0
        if losses == 0:
            return round(profits, 2)
        return round(profits / losses, 2)

    def calculate_max_drawdown(self, equity_curve: list[float]) -> float:
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]
        max_drawdown = 0.0
        for value in equity_curve:
            peak = max(peak, value)
            max_drawdown = max(max_drawdown, peak - value)
        return round(max_drawdown, 2)

    def summarize_symbol(self, symbol: str, data: dict[str, list[Any]]) -> SymbolPerformanceSummary:
        normalized = symbol.upper()
        signals = [signal for signal in data.get("strategy_signals", []) if self._symbol(signal) == normalized]
        executions = [execution for execution in data.get("demo_executions", []) if self._symbol(execution) == normalized]
        pnls = [self._pnl(trade) for trade in executions]
        wins = len([pnl for pnl in pnls if pnl > 0])
        losses = len([pnl for pnl in pnls if pnl < 0])
        confidences = [float(getattr(signal, "confidence", 0) or 0) for signal in signals]
        return SymbolPerformanceSummary(
            symbol=normalized,
            total_signals=len(signals),
            buy_signals=len([signal for signal in signals if str(getattr(signal, "action", "")).upper() == "BUY"]),
            sell_signals=len([signal for signal in signals if str(getattr(signal, "action", "")).upper() == "SELL"]),
            wait_signals=len([signal for signal in signals if str(getattr(signal, "action", "")).upper() == "WAIT"]),
            demo_executions=len(executions),
            wins=wins,
            losses=losses,
            win_rate=self.calculate_win_rate(wins, losses),
            net_pnl=self.calculate_net_pnl(executions),
            avg_confidence=round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
            best_trade=max(pnls) if pnls else 0.0,
            worst_trade=min(pnls) if pnls else 0.0,
        )

    def summarize_session(self, session: str, data: dict[str, list[Any]]) -> SessionPerformanceSummary:
        normalized = session.upper()
        signals = [signal for signal in data.get("strategy_signals", []) if self._session(signal) == normalized]
        executions = [execution for execution in data.get("demo_executions", []) if self._session(execution) == normalized]
        pnls = [self._pnl(trade) for trade in executions]
        wins = len([pnl for pnl in pnls if pnl > 0])
        losses = len([pnl for pnl in pnls if pnl < 0])
        confidences = [float(getattr(signal, "confidence", 0) or 0) for signal in signals]
        return SessionPerformanceSummary(
            session=normalized,
            total_signals=len(signals),
            demo_executions=len(executions),
            wins=wins,
            losses=losses,
            win_rate=self.calculate_win_rate(wins, losses),
            net_pnl=self.calculate_net_pnl(executions),
            avg_confidence=round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
        )

    def _pnl(self, trade: Any) -> float:
        for field in ("pnl", "net_pnl", "profit", "realized_pnl"):
            value = getattr(trade, field, None)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def _symbol(self, item: Any) -> str | None:
        value = getattr(item, "symbol", None) or getattr(item, "canonical_symbol", None) or getattr(item, "source_symbol", None)
        return str(value).upper() if value else None

    def _session(self, item: Any) -> str:
        value = getattr(item, "session", None) or getattr(item, "market_session", None)
        return str(value).upper() if value else "UNKNOWN"
