from datetime import datetime

from backend.backtesting.backtest_models import EquityPoint, TradeResult


class EquityCurveBuilder:
    """Maintain balance and drawdown observations during a historical replay."""

    def build(
        self,
        initial_balance: float,
        trades: list[TradeResult],
        start_timestamp: datetime,
    ) -> list[EquityPoint]:
        balance = initial_balance
        peak = initial_balance
        curve = [
            EquityPoint(
                timestamp=start_timestamp,
                balance=round(initial_balance, 2),
                drawdown_percent=0.0,
            )
        ]
        for trade in trades:
            balance += trade.pnl
            peak = max(peak, balance)
            drawdown = ((peak - balance) / peak * 100) if peak else 0.0
            curve.append(
                EquityPoint(
                    timestamp=trade.exit_time,
                    balance=round(balance, 2),
                    drawdown_percent=round(drawdown, 4),
                    trade_id=trade.trade_id,
                )
            )
        return curve
