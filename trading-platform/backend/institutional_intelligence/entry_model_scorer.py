from typing import Any

from backend.institutional_intelligence.entry_model_models import EntryModelScore, InstitutionalEntryModel


class EntryModelScorer:
    """Rank candidate entry models using bounded, deterministic evidence weights."""

    def score_model(
        self,
        model: InstitutionalEntryModel,
        confluence_context: Any = None,
        alignment_context: Any = None,
        session_context: Any = None,
    ) -> EntryModelScore:
        if model.model_type == "NO_TRADE":
            return EntryModelScore(reason="No-trade models are not simulation candidates.")
        alignment = self._alignment(model, alignment_context)
        confluence = self._confluence(model, confluence_context)
        session = self._session(session_context)
        structure = self._structure(model)
        risk = self._risk(confluence_context)
        freshness = self._freshness(model)
        total = alignment + confluence + session + structure + risk + freshness
        if model.invalidation_level is None or model.target_level is None:
            total -= 20.0
        return EntryModelScore(
            score=round(min(max(total, 0.0), 100.0), 2),
            alignment_score=alignment,
            confluence_score=confluence,
            session_score=session,
            structure_score=structure,
            risk_score=risk,
            freshness_score=freshness,
            reason="Weighted institutional alignment, confluence, timing, structure, risk, and freshness assessment.",
        )

    def _alignment(self, model: InstitutionalEntryModel, context: Any) -> float:
        direction = self._get(context, "overall_direction")
        score = float(self._get(context, "alignment_score") or 0.0)
        if direction == model.direction:
            return round(min(score / 100.0 * 20.0, 20.0), 2)
        if direction in {None, "NEUTRAL"}:
            return 5.0
        return 0.0

    def _confluence(self, model: InstitutionalEntryModel, context: Any) -> float:
        score_context = self._get(context, "confluence_score")
        direction = self._get(score_context, "dominant_direction")
        score = float(self._get(score_context, "overall_score") or 0.0)
        if direction == model.direction:
            return round(min(score / 100.0 * 25.0, 25.0), 2)
        if direction in {None, "NEUTRAL"}:
            return 5.0
        return 0.0

    def _session(self, context: Any) -> float:
        readiness = self._get(context, "trade_timing_readiness")
        if readiness in {"AVOID_NEWS_WINDOW", "AVOID_LOW_LIQUIDITY"}:
            return 0.0
        score = float(self._get(context, "session_quality_score") or 0.0)
        return round(min(score / 100.0 * 15.0, 15.0), 2)

    def _structure(self, model: InstitutionalEntryModel) -> float:
        event = model.related_structure_event
        if not event:
            return 4.0
        event_type = self._get(event, "event_type")
        strength = float(self._get(event, "strength") or 0.0)
        floor = {"MSS": 80.0, "BOS": 65.0, "CHOCH": 50.0}.get(event_type, 0.0)
        return round(min(max(strength, floor) / 100.0 * 15.0, 15.0), 2)

    def _risk(self, context: Any) -> float:
        readiness = self._get(self._get(context, "confluence_score"), "trade_readiness")
        return 0.0 if readiness == "BLOCKED_BY_RISK" else 10.0

    def _freshness(self, model: InstitutionalEntryModel) -> float:
        related = [model.related_fvg, model.related_order_block, model.related_breaker]
        if any(item is not None and self._get(item, "fresh") is not False for item in related):
            return 15.0
        return 0.0

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
