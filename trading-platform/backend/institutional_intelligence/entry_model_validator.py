from typing import Any

from backend.institutional_intelligence.entry_model_models import EntryModelValidationResult, InstitutionalEntryModel


class EntryModelValidator:
    """Apply non-execution qualification gates to detected entry patterns."""

    def validate_model(
        self,
        model: InstitutionalEntryModel,
        confluence_context: Any = None,
        alignment_context: Any = None,
        session_context: Any = None,
    ) -> EntryModelValidationResult:
        if model.model_type == "NO_TRADE":
            readiness = "AVOID" if model.blocking_factors else "NO_SETUP"
            return EntryModelValidationResult(
                valid=True,
                readiness=readiness,
                reason="No-trade model records blocked or insufficient institutional evidence.",
                blocking_factors=model.blocking_factors,
                confidence=100.0 if model.blocking_factors else 80.0,
            )

        missing = []
        if model.direction not in {"BULLISH", "BEARISH"}:
            missing.append("Directional bias is required.")
        if model.entry_zone_low is None or model.entry_zone_high is None:
            missing.append("An actionable entry zone is required.")
        elif model.entry_zone_high <= model.entry_zone_low:
            missing.append("Entry zone boundaries are invalid.")
        if model.invalidation_level is None:
            missing.append("Invalidation level is required.")
        if model.target_level is None:
            missing.append("Target level is required.")
        if len(model.supporting_factors) < 2:
            missing.append("At least two institutional supporting factors are required.")
        blocks = self._blocks(model, confluence_context, alignment_context, session_context)
        if missing:
            return EntryModelValidationResult(
                valid=False,
                readiness="NO_SETUP",
                reason="Candidate is missing actionable institutional requirements.",
                missing_requirements=missing,
                blocking_factors=blocks,
                confidence=0.0,
            )
        if blocks:
            return EntryModelValidationResult(
                valid=True,
                readiness="AVOID",
                reason="Candidate exists but higher-order controls prevent simulation readiness.",
                blocking_factors=blocks,
                confidence=30.0,
            )
        session_readiness = self._get(session_context, "trade_timing_readiness")
        confluence_readiness = self._get(self._get(confluence_context, "confluence_score"), "trade_readiness")
        ready = session_readiness == "HIGH_QUALITY_WINDOW" and confluence_readiness == "READY_FOR_SIMULATION"
        return EntryModelValidationResult(
            valid=True,
            readiness="READY_FOR_SIMULATION" if ready else "WAIT_FOR_CONFIRMATION",
            reason="Entry model satisfies geometry and institutional gating checks.",
            confidence=90.0 if ready else 65.0,
        )

    def _blocks(self, model: InstitutionalEntryModel, confluence: Any, alignment: Any, session: Any) -> list[str]:
        blocks = list(model.blocking_factors)
        session_readiness = self._get(session, "trade_timing_readiness")
        if session_readiness in {"AVOID_NEWS_WINDOW", "AVOID_LOW_LIQUIDITY"}:
            blocks.append("Session timing prevents simulated entry qualification.")
        score = self._get(confluence, "confluence_score")
        if self._get(score, "trade_readiness") == "BLOCKED_BY_RISK":
            blocks.append("Risk controls block setup qualification.")
        alignment_direction = self._get(alignment, "overall_direction")
        if alignment_direction == "CONFLICTED":
            blocks.append("Multi-timeframe alignment is conflicted.")
        if model.direction in {"BULLISH", "BEARISH"} and alignment_direction in {"BULLISH", "BEARISH"}:
            if model.direction != alignment_direction:
                blocks.append("Candidate direction opposes higher-timeframe alignment.")
        return list(dict.fromkeys(blocks))

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
