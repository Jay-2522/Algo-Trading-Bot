from backend.institutional_intelligence.setup_validator_models import SetupValidationResult
from backend.institutional_intelligence.simulation_decision_models import SimulationOrderIntent
from backend.institutional_intelligence.simulation_risk_estimator import SimulationRiskEstimator


class SimulationIntentBuilder:
    """Create an analytical simulation intent, never an execution request."""

    def __init__(self, risk_estimator: SimulationRiskEstimator | None = None) -> None:
        self.risk_estimator = risk_estimator or SimulationRiskEstimator()

    def build_order_intent(self, validation_result: SetupValidationResult | None) -> SimulationOrderIntent:
        if validation_result is None:
            return SimulationOrderIntent(symbol="", timeframe="", direction="NONE")
        action_direction = (
            "BUY" if validation_result.direction == "BULLISH"
            else "SELL" if validation_result.direction == "BEARISH"
            else "NONE"
        )
        active = validation_result.readiness in {"APPROVED", "CONDITIONAL"} and action_direction != "NONE"
        direction = action_direction if active else "NONE"
        rr = self.risk_estimator.estimate_rr(
            validation_result.entry_zone_low,
            validation_result.entry_zone_high,
            validation_result.invalidation_level,
            validation_result.target_level,
            direction,
        )
        return SimulationOrderIntent(
            symbol=validation_result.symbol,
            timeframe=validation_result.timeframe,
            direction=direction,
            entry_low=validation_result.entry_zone_low if active else None,
            entry_high=validation_result.entry_zone_high if active else None,
            invalidation_level=validation_result.invalidation_level if active else None,
            target_level=validation_result.target_level if active else None,
            estimated_rr=rr,
            risk_quality=self.risk_estimator.classify_risk_quality(rr, active),
            source_model_id=validation_result.source_model_id,
            source_validation_id=validation_result.validation_id,
            metadata={"analytical_intent_only": True, "validation_readiness": validation_result.readiness},
        )
