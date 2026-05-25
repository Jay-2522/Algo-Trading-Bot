import math
from statistics import mean, pstdev

from backend.backtesting.backtest_models import EquityPoint, PerformanceMetrics, TradeResult


class PerformanceAnalyzer:
    """Calculate stable risk/return statistics from closed simulated trades."""

    def analyze(
        self,
        initial_balance: float,
        trades: list[TradeResult],
        equity_curve: list[EquityPoint],
    ) -> PerformanceMetrics:
        profits = [trade.pnl for trade in trades if trade.pnl > 0]
        losses = [trade.pnl for trade in trades if trade.pnl < 0]
        total_trades = len(trades)
        net_profit = sum(trade.pnl for trade in trades)
        ending_balance = initial_balance + net_profit
        winning_trades = len(profits)
        losing_trades = len(losses)
        gross_profit = sum(profits)
        gross_loss = abs(sum(losses))
        returns = [trade.pnl / initial_balance for trade in trades] if initial_balance else []

        return PerformanceMetrics(
            initial_balance=round(initial_balance, 2),
            ending_balance=round(ending_balance, 2),
            net_profit=round(net_profit, 2),
            profit_percent=round(net_profit / initial_balance * 100, 4) if initial_balance else 0.0,
            max_drawdown=round(max((point.drawdown_percent for point in equity_curve), default=0.0), 4),
            win_rate=round(winning_trades / total_trades * 100, 4) if total_trades else 0.0,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            average_rr=round(mean([trade.risk_reward for trade in trades]), 4) if trades else 0.0,
            profit_factor=round(gross_profit / gross_loss, 4) if gross_loss else (gross_profit if gross_profit else 0.0),
            expectancy=round(net_profit / total_trades, 4) if total_trades else 0.0,
            sharpe_ratio=self._sharpe_ratio(returns),
            equity_growth=round(ending_balance - initial_balance, 2),
            max_consecutive_wins=self._max_streak(trades, "WIN"),
            max_consecutive_losses=self._max_streak(trades, "LOSS"),
            best_trade=round(max((trade.pnl for trade in trades), default=0.0), 2),
            worst_trade=round(min((trade.pnl for trade in trades), default=0.0), 2),
        )

    def _sharpe_ratio(self, returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        deviation = pstdev(returns)
        if deviation == 0:
            return 0.0
        return round(mean(returns) / deviation * math.sqrt(len(returns)), 4)

    def _max_streak(self, trades: list[TradeResult], outcome: str) -> int:
        best = current = 0
        for trade in trades:
            if trade.outcome == outcome:
                current += 1
                best = max(best, current)
            else:
                current = 0
        return best
