from backend.institutional_intelligence.entry_model_models import InstitutionalEntryModel


class EntryModelExplainer:
    """Produce concise reasoning suitable for dashboards and journals."""

    LABELS = {
        "SWEEP_FVG_CONTINUATION": "sweep plus fresh FVG continuation",
        "ORDER_BLOCK_RETRACEMENT": "order block retracement",
        "BREAKER_RETEST": "breaker block retest",
        "MSS_REVERSAL": "market structure shift reversal",
        "LIQUIDITY_REVERSAL": "liquidity reversal",
        "NO_TRADE": "no-trade",
    }

    def explain_model(self, model: InstitutionalEntryModel) -> dict[str, object]:
        if model.model_type == "NO_TRADE":
            summary = "No trade because institutional confirmation is insufficient or blocked."
        else:
            summary = f"{model.direction.title()} {self.LABELS[model.model_type]} model detected."
            if model.readiness == "WAIT_FOR_CONFIRMATION":
                summary += " Setup is waiting for complete simulation confirmation."
            elif model.readiness == "AVOID":
                summary += " Setup is blocked from simulation consideration."
        return {
            "summary": summary,
            "supporting_factors": model.supporting_factors,
            "blocking_factors": model.blocking_factors,
            "warnings": model.warnings,
        }
