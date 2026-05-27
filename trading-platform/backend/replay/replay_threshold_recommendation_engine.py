from typing import Any

from backend.replay.replay_calibration_models import ReplayBlockReasonMetrics, ThresholdAdjustmentSuggestion


class ReplayThresholdRecommendationEngine:
    """Generate safe research-mode calibration suggestions."""

    SAFETY_NOTE = (
        "Research-mode suggestion only. Do not apply to live trading; keep simulation_only=true "
        "and live_execution_enabled=false."
    )

    def generate_suggestions(
        self,
        block_metrics: ReplayBlockReasonMetrics,
        threshold_analysis: dict[str, Any],
    ) -> list[ThresholdAdjustmentSuggestion]:
        flags = threshold_analysis.get("flags", {})
        suggestions: list[ThresholdAdjustmentSuggestion] = []

        if flags.get("repeated_confluence_rejection") or block_metrics.most_restrictive_gate == "CONFLUENCE":
            suggestions.append(
                ThresholdAdjustmentSuggestion(
                    threshold_name="confluence_approval_threshold",
                    current_value=75.0,
                    suggested_value=70.0,
                    adjustment_direction="RELAX",
                    confidence=72.0,
                    reason="Replay blocks are repeatedly linked to confluence conflict or strict approval scoring.",
                    safety_note=self.SAFETY_NOTE,
                )
            )

        if flags.get("repeated_session_rejection") or block_metrics.most_restrictive_gate == "SESSION":
            suggestions.append(
                ThresholdAdjustmentSuggestion(
                    threshold_name="session_killzone_requirement",
                    current_value="STRICT_FOR_ALL_SETUPS",
                    suggested_value="STRICT_FOR_A_PLUS_ONLY",
                    adjustment_direction="RELAX",
                    confidence=68.0,
                    reason="Session timing blocks are frequent; consider allowing high-confluence observations outside killzones for research comparison.",
                    safety_note=self.SAFETY_NOTE,
                )
            )

        if flags.get("no_simulated_trades"):
            suggestions.append(
                ThresholdAdjustmentSuggestion(
                    threshold_name="entry_model_quality_floor",
                    current_value=75.0,
                    suggested_value=70.0,
                    adjustment_direction="RELAX",
                    confidence=64.0,
                    reason="No simulated trades were generated, suggesting the entry model quality floor may be too restrictive for replay research.",
                    safety_note=self.SAFETY_NOTE,
                )
            )

        if flags.get("low_confidence_decisions") and block_metrics.block_rate < 35.0:
            suggestions.append(
                ThresholdAdjustmentSuggestion(
                    threshold_name="minimum_decision_confidence",
                    current_value=55.0,
                    suggested_value=60.0,
                    adjustment_direction="TIGHTEN",
                    confidence=60.0,
                    reason="Low-confidence decisions are passing too often; tightening confidence may improve replay quality.",
                    safety_note=self.SAFETY_NOTE,
                )
            )

        if flags.get("entry_geometry_gap"):
            suggestions.append(
                ThresholdAdjustmentSuggestion(
                    threshold_name="entry_geometry_validation",
                    current_value="REQUIRED",
                    suggested_value="REQUIRED_WITH_VERBOSE_DIAGNOSTICS",
                    adjustment_direction="KEEP",
                    confidence=85.0,
                    reason="Missing entry, invalidation, or target geometry should remain a hard simulation gate.",
                    safety_note="Keep this gate strict. Undefined trade geometry must never be relaxed.",
                )
            )

        if flags.get("risk_gate_pressure"):
            suggestions.append(
                ThresholdAdjustmentSuggestion(
                    threshold_name="risk_gate",
                    current_value="STRICT",
                    suggested_value="STRICT",
                    adjustment_direction="KEEP",
                    confidence=95.0,
                    reason="Risk gates are protective and should not be relaxed based on replay block frequency alone.",
                    safety_note="Hard risk controls must remain strict in simulation and any future production workflow.",
                )
            )

        if flags.get("news_gate_pressure"):
            suggestions.append(
                ThresholdAdjustmentSuggestion(
                    threshold_name="news_blackout_gate",
                    current_value="STRICT",
                    suggested_value="STRICT",
                    adjustment_direction="KEEP",
                    confidence=95.0,
                    reason="News blackout protection is a hard safety-style filter and should not be relaxed automatically.",
                    safety_note="Never relax news blackout behavior for live execution. Use replay-only A/B research if needed.",
                )
            )

        if not suggestions:
            suggestions.append(
                ThresholdAdjustmentSuggestion(
                    threshold_name="current_calibration",
                    current_value="CURRENT",
                    suggested_value="CURRENT",
                    adjustment_direction="KEEP",
                    confidence=70.0,
                    reason="Replay calibration does not show enough evidence for threshold changes.",
                    safety_note=self.SAFETY_NOTE,
                )
            )
        return suggestions
