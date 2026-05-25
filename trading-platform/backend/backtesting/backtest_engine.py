from typing import Any
from uuid import uuid4

from backend.ai_engine.decision_engine import DecisionEngine
from backend.backtesting.backtest_models import BacktestRequest, BacktestResult, HistoricalCandle, TradeResult
from backend.backtesting.backtest_storage import BacktestStorage
from backend.backtesting.equity_curve import EquityCurveBuilder
from backend.backtesting.historical_data_loader import HistoricalDataLoader
from backend.backtesting.performance_analyzer import PerformanceAnalyzer
from backend.backtesting.trade_simulator import TradeSimulator
from backend.risk_engine.risk_service import RiskService
from backend.strategy_engine.liquidity_detector import LiquidityDetector
from backend.strategy_engine.session_manager import SessionManager
from backend.strategy_engine.structure_analyzer import StructureAnalyzer
from backend.strategy_engine.trend_analyzer import TrendAnalyzer


class BacktestEngine:
    """Replay historical bars through advisory analysis and internal trade simulation."""

    WINDOW_SIZE = 200
    MAX_HOLDING_BARS = 16
    EVALUATION_STRIDE = 4

    def __init__(
        self,
        loader: HistoricalDataLoader | None = None,
        trade_simulator: TradeSimulator | None = None,
        performance_analyzer: PerformanceAnalyzer | None = None,
        equity_builder: EquityCurveBuilder | None = None,
        storage: BacktestStorage | None = None,
        decision_engine: DecisionEngine | None = None,
    ) -> None:
        self.loader = loader or HistoricalDataLoader()
        self.trade_simulator = trade_simulator or TradeSimulator()
        self.performance_analyzer = performance_analyzer or PerformanceAnalyzer()
        self.equity_builder = equity_builder or EquityCurveBuilder()
        self.storage = storage or BacktestStorage()
        self.decision_engine = decision_engine or DecisionEngine(risk_service=RiskService())
        self.trend_analyzer = TrendAnalyzer()
        self.liquidity_detector = LiquidityDetector()
        self.structure_analyzer = StructureAnalyzer()
        self.session_manager = SessionManager()

    def run(
        self,
        request: BacktestRequest,
        candles: list[HistoricalCandle | dict[str, Any]] | None = None,
        persist: bool = True,
    ) -> BacktestResult:
        errors: list[str] = []
        source_candles = candles if candles is not None else self.loader.load_candles(request)
        replay_candles = self._validated_candles(source_candles, errors)
        trades = self._replay(request, replay_candles, errors) if replay_candles else []
        start_timestamp = replay_candles[0].timestamp if replay_candles else request.start_date
        curve = self.equity_builder.build(request.initial_balance, trades, start_timestamp)
        metrics = self.performance_analyzer.analyze(request.initial_balance, trades, curve)
        status = "COMPLETED" if replay_candles else "NO_VALID_DATA"
        result = BacktestResult(
            backtest_id=str(uuid4()),
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_balance=metrics.initial_balance,
            ending_balance=metrics.ending_balance,
            net_profit=metrics.net_profit,
            profit_percent=metrics.profit_percent,
            max_drawdown=metrics.max_drawdown,
            win_rate=metrics.win_rate,
            total_trades=metrics.total_trades,
            winning_trades=metrics.winning_trades,
            losing_trades=metrics.losing_trades,
            average_rr=metrics.average_rr,
            profit_factor=metrics.profit_factor,
            sharpe_ratio=metrics.sharpe_ratio,
            equity_curve=curve,
            trade_history=trades,
            metrics=metrics,
            approved=bool(replay_candles),
            status=status,
            errors=errors,
        )
        if persist and not self.storage.save_result(result):
            result.errors.append("storage: backtest report could not be persisted.")
            result.status = "COMPLETED_WITH_STORAGE_WARNING"
        return result

    def _validated_candles(
        self,
        candles: list[HistoricalCandle | dict[str, Any]],
        errors: list[str],
    ) -> list[HistoricalCandle]:
        validated: list[HistoricalCandle] = []
        for index, candidate in enumerate(candles):
            try:
                candle = HistoricalCandle.model_validate(candidate)
                if (
                    candle.high < max(candle.open, candle.close)
                    or candle.low > min(candle.open, candle.close)
                    or candle.high < candle.low
                ):
                    raise ValueError("invalid OHLC range")
                validated.append(candle)
            except Exception as exc:
                errors.append(f"candle[{index}] skipped: {exc}")
        return validated

    def _replay(
        self,
        request: BacktestRequest,
        candles: list[HistoricalCandle],
        errors: list[str],
    ) -> list[TradeResult]:
        if len(candles) <= self.WINDOW_SIZE + 1:
            return []
        trades: list[TradeResult] = []
        account_balance = request.initial_balance
        index = self.WINDOW_SIZE - 1
        while index < len(candles) - 2:
            window = candles[index - self.WINDOW_SIZE + 1 : index + 1]
            try:
                decision = self._historical_ai_decision(request.symbol, request.timeframe, window)
                if decision.approved and decision.action in {"BUY", "SELL"}:
                    future = candles[index + 1 : index + 1 + self.MAX_HOLDING_BARS]
                    trade = self.trade_simulator.simulate_trade(
                        request,
                        decision.action,
                        future[0],
                        future,
                        account_balance,
                    )
                    trades.append(trade)
                    account_balance += trade.pnl
                    index += max(trade.bars_held, self.EVALUATION_STRIDE)
                else:
                    index += self.EVALUATION_STRIDE
            except Exception as exc:
                errors.append(f"replay[{index}] skipped: {exc}")
                index += self.EVALUATION_STRIDE
        return trades

    def _historical_ai_decision(
        self,
        symbol: str,
        timeframe: str,
        candles: list[HistoricalCandle],
    ):
        context = {
            "symbol": symbol,
            "timeframe": timeframe,
            "trend_analysis": self.trend_analyzer.determine_trend(candles),
            "liquidity_analysis": self.liquidity_detector.detect_liquidity_zones(candles[-40:]),
            "structure_analysis": self.structure_analyzer.analyze_market_structure(candles[-20:]),
            "session_info": self.session_manager.get_session_info(candles[-1].timestamp),
            "status": "historical_replay",
        }
        return self.decision_engine.evaluate_setup(
            symbol,
            strategy_context=context,
            spread_quality=90.0,
        )["decision"]
