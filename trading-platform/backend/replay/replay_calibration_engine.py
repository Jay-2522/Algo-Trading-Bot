from backend.replay.replay_block_reason_analyzer import ReplayBlockReasonAnalyzer
from backend.replay.replay_calibration_models import ReplayCalibrationReport
from backend.replay.replay_models import ReplayRunResult
from backend.replay.replay_report_models import ReplayHistoricalReport
from backend.replay.replay_threshold_analyzer import ReplayThresholdAnalyzer
from backend.replay.replay_threshold_recommendation_engine import ReplayThresholdRecommendationEngine


class ReplayCalibrationEngine:
    """Coordinate replay block analysis and threshold-tuning suggestions."""

    def __init__(
        self,
        block_analyzer: ReplayBlockReasonAnalyzer | None = None,
        threshold_analyzer: ReplayThresholdAnalyzer | None = None,
        recommendation_engine: ReplayThresholdRecommendationEngine | None = None,
    ) -> None:
        self.block_analyzer = block_analyzer or ReplayBlockReasonAnalyzer()
        self.threshold_analyzer = threshold_analyzer or ReplayThresholdAnalyzer()
        self.recommendation_engine = recommendation_engine or ReplayThresholdRecommendationEngine()

    def calibrate_replay(
        self,
        replay_result: ReplayRunResult,
        replay_report: ReplayHistoricalReport | None = None,
    ) -> ReplayCalibrationReport:
        steps = replay_result.step_results
        decision_analytics = replay_report.decision_analytics if replay_report else None
        block_metrics = self.block_analyzer.analyze_block_reasons(steps)
        threshold_analysis = self.threshold_analyzer.analyze_threshold_strictness(block_metrics, decision_analytics)
        suggestions = self.recommendation_engine.generate_suggestions(block_metrics, threshold_analysis)
        status = threshold_analysis.get("status", "INSUFFICIENT_DATA")
        warnings = self._warnings(status, block_metrics)

        return ReplayCalibrationReport(
            replay_id=replay_result.replay_id,
            symbol=replay_result.symbol,
            timeframe=replay_result.timeframe,
            block_reason_metrics=block_metrics,
            threshold_suggestions=suggestions,
            calibration_status=status,
            summary=self._summary(replay_result, status, block_metrics),
            warnings=warnings,
            simulation_only=True,
            live_execution_enabled=False,
            metadata={"threshold_analysis": threshold_analysis},
        )

    def _summary(self, replay_result: ReplayRunResult, status: str, block_metrics) -> str:
        return (
            f"Replay {replay_result.replay_id} calibration status is {status}. "
            f"{block_metrics.total_blocked} blocked step(s) were detected "
            f"({block_metrics.block_rate:.2f}% block rate); most restrictive gate: "
            f"{block_metrics.most_restrictive_gate}."
        )

    def _warnings(self, status: str, block_metrics) -> list[str]:
        warnings: list[str] = []
        if status == "INSUFFICIENT_DATA":
            warnings.append("Insufficient replay data for reliable calibration.")
        if status == "TOO_RESTRICTIVE":
            warnings.append("Replay filters may be too restrictive for research-mode simulation.")
        if status == "TOO_LOOSE":
            warnings.append("Replay filters may be allowing low-confidence decisions.")
        if block_metrics.gate_counts.get("RISK", 0):
            warnings.append("Risk gate suggestions are diagnostic only; do not relax hard risk controls.")
        if block_metrics.gate_counts.get("NEWS", 0):
            warnings.append("News blackout suggestions are diagnostic only; preserve blackout protection.")
        return warnings
