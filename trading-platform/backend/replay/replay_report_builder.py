from backend.replay.replay_decision_analyzer import ReplayDecisionAnalyzer
from backend.replay.replay_equity_curve import ReplayEquityCurveBuilder
from backend.replay.replay_models import ReplayRunResult, ReplayStepResult
from backend.replay.replay_report_models import ReplayHistoricalReport
from backend.replay.replay_trade_analyzer import ReplayTradeAnalyzer
from backend.replay.replay_weakness_detector import ReplayWeaknessDetector


class ReplayReportBuilder:
    """Build historical replay analytics reports from replay run output."""

    def __init__(
        self,
        trade_analyzer: ReplayTradeAnalyzer | None = None,
        decision_analyzer: ReplayDecisionAnalyzer | None = None,
        equity_builder: ReplayEquityCurveBuilder | None = None,
        weakness_detector: ReplayWeaknessDetector | None = None,
    ) -> None:
        self.trade_analyzer = trade_analyzer or ReplayTradeAnalyzer()
        self.decision_analyzer = decision_analyzer or ReplayDecisionAnalyzer()
        self.equity_builder = equity_builder or ReplayEquityCurveBuilder()
        self.weakness_detector = weakness_detector or ReplayWeaknessDetector()

    def build_report(
        self,
        replay_result: ReplayRunResult,
        step_results: list[ReplayStepResult] | None = None,
        initial_balance: float = 10000.0,
    ) -> ReplayHistoricalReport:
        steps = step_results if step_results is not None else replay_result.step_results
        trade_analytics = self.trade_analyzer.analyze_trades(steps)
        decision_analytics = self.decision_analyzer.analyze_decisions(steps)
        equity_curve = self.equity_builder.build_equity_curve(steps, initial_balance)
        weaknesses = self.weakness_detector.detect_weaknesses(trade_analytics, decision_analytics, steps)
        best_conditions, worst_conditions = self._conditions(steps)

        return ReplayHistoricalReport(
            replay_id=replay_result.replay_id,
            symbol=replay_result.symbol,
            timeframe=replay_result.timeframe,
            trade_analytics=trade_analytics,
            decision_analytics=decision_analytics,
            equity_curve=equity_curve,
            weakness_insights=weaknesses,
            best_conditions=best_conditions,
            worst_conditions=worst_conditions,
            summary=self._summary(replay_result, trade_analytics, decision_analytics),
            simulation_only=True,
            live_execution_enabled=False,
            metadata={"total_steps": replay_result.total_steps},
        )

    def _conditions(self, steps: list[ReplayStepResult]) -> tuple[list[str], list[str]]:
        if not steps:
            return ["No historical conditions available."], ["No replay sample was available for evaluation."]

        actions = [str(step.simulation_decision.get("action", "NO_TRADE") or "NO_TRADE") for step in steps]
        outcomes = [step.paper_trade_state.get("latest_outcome") for step in steps]
        best: list[str] = []
        worst: list[str] = []
        if any(action in {"SIMULATE_BUY", "SIMULATE_SELL"} for action in actions):
            best.append("Simulation decisions appeared when institutional validation aligned.")
        if any(outcome == "WIN" for outcome in outcomes):
            best.append("At least one replayed paper position reached target.")
        if any(action in {"AVOID", "NO_TRADE"} for action in actions):
            worst.append("Blocked/no-trade conditions appeared in the replay sample.")
        if any(outcome == "LOSS" for outcome in outcomes):
            worst.append("At least one replayed paper position hit invalidation.")
        return best or ["No standout favorable condition detected."], worst or ["No major unfavorable condition detected."]

    def _summary(
        self,
        replay_result: ReplayRunResult,
        trade_analytics,
        decision_analytics,
    ) -> str:
        return (
            f"Replay {replay_result.replay_id} analyzed {replay_result.total_steps} step(s) "
            f"with {decision_analytics.total_decisions} decision observation(s), "
            f"{trade_analytics.total_trades} closed simulated trade(s), "
            f"{trade_analytics.win_rate:.2f}% win rate, and {trade_analytics.net_rr:.2f} net R."
        )
