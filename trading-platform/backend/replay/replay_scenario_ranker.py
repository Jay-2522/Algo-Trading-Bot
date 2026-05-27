from backend.replay.replay_calibration_models import ReplayCalibrationReport
from backend.replay.replay_report_models import ReplayHistoricalReport


class ReplayScenarioRanker:
    """Score replay scenarios using bounded deterministic performance factors."""

    def rank_scenario(
        self,
        report: ReplayHistoricalReport,
        calibration: ReplayCalibrationReport | None = None,
    ) -> float:
        trade = report.trade_analytics
        decision = report.decision_analytics
        equity = report.equity_curve
        block_rate = calibration.block_reason_metrics.block_rate if calibration else decision.block_rate

        rr_score = self._score_net_rr(trade.net_rr)
        win_rate_score = min(max(trade.win_rate, 0.0), 100.0) * 0.20
        block_score = max(0.0, 100.0 - block_rate) * 0.20
        confidence_score = min(max(decision.average_confidence, 0.0), 100.0) * 0.15
        activity_score = self._score_trade_activity(trade.total_trades, decision.total_decisions)
        drawdown_score = self._score_drawdown(equity)

        score = rr_score + win_rate_score + block_score + confidence_score + activity_score + drawdown_score
        if trade.total_trades == 0:
            score = min(score, 35.0)
        return round(min(max(score, 0.0), 100.0), 2)

    def _score_net_rr(self, net_rr: float) -> float:
        if net_rr <= 0.0:
            return max(0.0, 12.5 + net_rr * 5.0)
        return min(25.0, 12.5 + net_rr * 6.25)

    def _score_trade_activity(self, total_trades: int, total_decisions: int) -> float:
        if total_decisions <= 0 or total_trades <= 0:
            return 0.0
        activity_ratio = min(1.0, total_trades / max(1, total_decisions))
        return round(activity_ratio * 10.0, 4)

    def _score_drawdown(self, equity) -> float:
        if not equity:
            return 10.0
        max_drawdown = max(float(point.drawdown or 0.0) for point in equity)
        if max_drawdown <= 0.0:
            return 10.0
        drawdown_pct = max_drawdown / max(float(equity[0].balance or 1.0), 1.0)
        return round(max(0.0, 10.0 - drawdown_pct * 100.0), 4)
