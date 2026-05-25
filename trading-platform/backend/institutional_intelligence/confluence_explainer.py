from backend.institutional_intelligence.confluence_models import InstitutionalConfluenceScore


class ConfluenceExplainer:
    """Create dashboard-facing prose from transparent component scores."""

    def explain(self, score_model: InstitutionalConfluenceScore) -> dict[str, object]:
        strengths: list[str] = []
        weaknesses: list[str] = []
        warnings: list[str] = []
        for component in score_model.component_scores:
            label = component.component.replace("_", " ").title()
            if component.direction in {"BULLISH", "BEARISH"} and component.score >= 60:
                strengths.append(f"{label} supports {component.direction.lower()} conditions.")
            elif component.component in {"STRUCTURE_BIAS", "STRUCTURE_SHIFT"} and component.score < 40:
                weaknesses.append(f"{label} provides limited directional confirmation.")
            elif component.component in {"FVG", "ORDER_BLOCK", "BREAKER_BLOCK"} and component.score < 40:
                weaknesses.append(f"No strong fresh {label.lower()} confirmation is available.")
            if component.component == "RISK" and component.score == 0:
                warnings.append("Risk readiness is blocked; simulation readiness is withheld.")
        if score_model.dominant_direction == "CONFLICTED":
            weaknesses.append("Signals are directionally conflicted.")
            warnings.append("Directional conflict prevents a qualified setup.")
        if score_model.trade_readiness == "WAIT_FOR_CONFIRMATION":
            warnings.append("Setup requires confirmation before simulation.")
        if score_model.setup_quality in {"LOW_QUALITY", "NO_TRADE"}:
            warnings.append("No high-quality confluence setup is confirmed.")
        direction = score_model.dominant_direction.lower().replace("_", " ")
        explanation = (
            f"{score_model.setup_quality.replace('_', ' ')} institutional assessment: "
            f"{direction} direction, overall score {score_model.overall_score:.2f}, "
            f"confidence {score_model.confidence:.2f}, readiness {score_model.trade_readiness.replace('_', ' ').lower()}."
        )
        return {
            "explanation": explanation,
            "strengths": list(dict.fromkeys(strengths)),
            "weaknesses": list(dict.fromkeys(weaknesses)),
            "warnings": list(dict.fromkeys(warnings)),
        }
