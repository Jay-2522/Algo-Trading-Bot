from statistics import mean
from uuid import uuid4

from backend.backtesting.backtest_models import BacktestRequest, HistoricalCandle, TradeResult


class TradeSimulator:
    """Close BUY or SELL scenarios against historical bars with modeled friction."""

    def simulate_trade(
        self,
        request: BacktestRequest,
        side: str,
        entry_candle: HistoricalCandle,
        future_candles: list[HistoricalCandle],
        account_balance: float,
    ) -> TradeResult:
        normalized_side = side.upper()
        if normalized_side not in {"BUY", "SELL"}:
            raise ValueError("Simulated trade side must be BUY or SELL.")
        if not future_candles:
            raise ValueError("A simulated trade requires future candles for an exit.")

        point_size = 0.01 if request.symbol == "XAUUSD" else 0.0001
        friction = (request.spread_points / 2 + request.slippage_points) * point_size
        direction = 1 if normalized_side == "BUY" else -1
        entry_price = entry_candle.close + friction * direction
        recent_ranges = [candle.high - candle.low for candle in future_candles[:10]]
        risk_distance = max(mean(recent_ranges) * 0.8, point_size * 10)
        stop_loss = entry_price - direction * risk_distance
        take_profit = entry_price + direction * risk_distance * request.risk_reward
        exit_price, exit_reason, exit_index = self._resolve_exit(
            normalized_side,
            future_candles,
            stop_loss,
            take_profit,
            friction,
        )

        contract_multiplier = 100.0 if request.symbol == "XAUUSD" else 100000.0
        pnl = (exit_price - entry_price) * direction * request.lot_size * contract_multiplier
        risk_amount = risk_distance * request.lot_size * contract_multiplier
        realized_rr = pnl / risk_amount if risk_amount else 0.0
        pnl_percent = pnl / account_balance * 100 if account_balance else 0.0
        outcome = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"

        return TradeResult(
            trade_id=str(uuid4()),
            symbol=request.symbol,
            side=normalized_side,
            entry_time=entry_candle.timestamp,
            exit_time=future_candles[exit_index].timestamp,
            entry_price=round(entry_price, 5),
            exit_price=round(exit_price, 5),
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            lot_size=request.lot_size,
            pnl=round(pnl, 2),
            pnl_percent=round(pnl_percent, 4),
            risk_reward=round(realized_rr, 4),
            outcome=outcome,
            exit_reason=exit_reason,
            spread_points=request.spread_points,
            slippage_points=request.slippage_points,
            bars_held=exit_index + 1,
        )

    def _resolve_exit(
        self,
        side: str,
        candles: list[HistoricalCandle],
        stop_loss: float,
        take_profit: float,
        friction: float,
    ) -> tuple[float, str, int]:
        for index, candle in enumerate(candles):
            if side == "BUY":
                if candle.low <= stop_loss:
                    return stop_loss - friction, "STOP_LOSS", index
                if candle.high >= take_profit:
                    return take_profit - friction, "TAKE_PROFIT", index
            else:
                if candle.high >= stop_loss:
                    return stop_loss + friction, "STOP_LOSS", index
                if candle.low <= take_profit:
                    return take_profit + friction, "TAKE_PROFIT", index
        last = candles[-1]
        exit_price = last.close - friction if side == "BUY" else last.close + friction
        return exit_price, "END_OF_REPLAY_WINDOW", len(candles) - 1
