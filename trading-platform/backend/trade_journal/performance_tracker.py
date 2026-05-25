from collections import defaultdict

from backend.trade_journal.journal_models import JournalEntry, SessionPerformance, SymbolPerformance


class PerformanceTracker:
    """Deterministic calculations for closed simulated journal entries."""

    def calculate(self, entries: list[JournalEntry]) -> dict:
        closed = [entry for entry in entries if entry.outcome != "OPEN"]
        wins = [entry for entry in closed if entry.outcome == "WIN"]
        profits = [entry.pnl for entry in closed if entry.pnl > 0]
        losses = [entry.pnl for entry in closed if entry.pnl < 0]
        gross_profit = sum(profits)
        gross_loss = abs(sum(losses))
        total = len(closed)
        return {
            "total_trades": total,
            "wins": len(wins),
            "losses": len([entry for entry in closed if entry.outcome == "LOSS"]),
            "win_rate": round(len(wins) / total * 100, 4) if total else 0.0,
            "net_profit": round(sum(entry.pnl for entry in closed), 2),
            "average_rr": round(sum(entry.rr for entry in closed) / total, 4) if total else 0.0,
            "best_trade": round(max((entry.pnl for entry in closed), default=0.0), 2),
            "worst_trade": round(min((entry.pnl for entry in closed), default=0.0), 2),
            "profit_factor": round(gross_profit / gross_loss, 4)
            if gross_loss
            else round(gross_profit, 4),
            "expectancy": round(sum(entry.pnl for entry in closed) / total, 4) if total else 0.0,
            "average_execution_quality": round(
                sum(entry.execution_quality for entry in closed) / total, 4
            ) if total else 0.0,
        }

    def symbol_performance(self, symbol: str, entries: list[JournalEntry]) -> SymbolPerformance:
        metrics = self.calculate(entries)
        return SymbolPerformance(
            symbol=symbol.strip().upper(),
            total_trades=metrics["total_trades"],
            win_rate=metrics["win_rate"],
            profit_factor=metrics["profit_factor"],
            average_rr=metrics["average_rr"],
            net_profit=metrics["net_profit"],
        )

    def session_performance(self, session: str, entries: list[JournalEntry]) -> SessionPerformance:
        metrics = self.calculate(entries)
        return SessionPerformance(
            session_name=session.strip().upper(),
            total_trades=metrics["total_trades"],
            win_rate=metrics["win_rate"],
            net_profit=metrics["net_profit"],
            average_rr=metrics["average_rr"],
            best_trade=metrics["best_trade"],
            worst_trade=metrics["worst_trade"],
        )

    def strategy_effectiveness(self, entries: list[JournalEntry]) -> list[dict]:
        strategies: dict[str, list[JournalEntry]] = defaultdict(list)
        for entry in entries:
            strategies[entry.strategy_name].append(entry)
        return [
            {"strategy_name": name, **self.calculate(group)}
            for name, group in sorted(strategies.items())
        ]
