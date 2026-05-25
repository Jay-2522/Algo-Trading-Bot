from typing import Any

from backend.institutional_intelligence.confluence_explainer import ConfluenceExplainer
from backend.institutional_intelligence.confluence_models import ConfluenceComponentScore, InstitutionalConfluenceScore
from backend.institutional_intelligence.setup_quality_classifier import SetupQualityClassifier


class InstitutionalConfluenceScorer:
    """Combine available institutional evidence into one deterministic assessment."""

    WEIGHTS = {
        "STRUCTURE_BIAS": 15.0,
        "LIQUIDITY_SWEEP": 15.0,
        "FVG": 15.0,
        "ORDER_BLOCK": 15.0,
        "BREAKER_BLOCK": 10.0,
        "STRUCTURE_SHIFT": 15.0,
        "PREMIUM_DISCOUNT": 5.0,
        "DISPLACEMENT": 5.0,
        "SESSION": 2.5,
        "RISK": 2.5,
    }

    def __init__(
        self,
        classifier: SetupQualityClassifier | None = None,
        explainer: ConfluenceExplainer | None = None,
    ) -> None:
        self.classifier = classifier or SetupQualityClassifier()
        self.explainer = explainer or ConfluenceExplainer()

    def score_confluence(
        self,
        symbol: str,
        timeframe: str,
        institutional_context: Any = None,
        sweep_context: Any = None,
        fvg_context: Any = None,
        order_block_context: Any = None,
        breaker_context: Any = None,
        structure_shift_context: Any = None,
        session_context: Any = None,
        risk_status: Any = None,
    ) -> InstitutionalConfluenceScore:
        components = [
            self._structure_bias(institutional_context),
            self._best_directional("LIQUIDITY_SWEEP", sweep_context, "sweeps", "strength"),
            self._zone_component("FVG", fvg_context, "fresh_fvgs", "mitigated_fvgs"),
            self._zone_component("ORDER_BLOCK", order_block_context, "fresh_order_blocks", "mitigated_order_blocks"),
            self._zone_component("BREAKER_BLOCK", breaker_context, "fresh_breakers", "mitigated_breakers"),
            self._structure_shift(structure_shift_context),
            self._premium_discount(institutional_context),
            self._displacement(institutional_context),
            self._session(session_context),
            self._risk(risk_status),
        ]
        bullish = round(sum(component.weighted_score for component in components if component.direction == "BULLISH"), 2)
        bearish = round(sum(component.weighted_score for component in components if component.direction == "BEARISH"), 2)
        neutral = round(sum(component.weighted_score for component in components if component.direction == "NEUTRAL"), 2)
        higher = max(bullish, bearish)
        lower = min(bullish, bearish)
        conflict_ratio = lower / higher if higher else 0.0
        severe_conflict = higher >= 20.0 and conflict_ratio >= 0.7
        if severe_conflict:
            direction = "CONFLICTED"
        elif bullish > bearish:
            direction = "BULLISH"
        elif bearish > bullish:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"
        overall = round(min(higher + neutral, 100.0), 2)
        evidence_weight = sum(component.weight for component in components if component.score > 0)
        coverage = evidence_weight / 100.0
        confidence = round(min(overall * (1.0 - (0.65 * conflict_ratio)) * max(coverage, 0.25), 100.0), 2)
        quality, readiness = self.classifier.classify_setup(overall, confidence, severe_conflict)
        if self._get(risk_status, "overall_status") == "BLOCKED":
            readiness = "BLOCKED_BY_RISK"
        scored = InstitutionalConfluenceScore(
            symbol=symbol.strip().upper(),
            timeframe=timeframe.strip().upper(),
            bullish_score=bullish,
            bearish_score=bearish,
            neutral_score=neutral,
            overall_score=overall,
            dominant_direction=direction,
            confidence=confidence,
            setup_quality=quality,
            trade_readiness=readiness,
            component_scores=components,
        )
        explanation = self.explainer.explain(scored)
        return scored.model_copy(update=explanation)

    def _component(self, name: str, direction: str, score: float, reason: str) -> ConfluenceComponentScore:
        bounded = round(min(max(float(score), 0.0), 100.0), 2)
        weight = self.WEIGHTS[name]
        return ConfluenceComponentScore(
            component=name,
            direction=direction,
            score=bounded,
            weight=weight,
            weighted_score=round(bounded * weight / 100.0, 2),
            reason=reason,
        )

    def _structure_bias(self, context: Any) -> ConfluenceComponentScore:
        bias = self._get(self._get(context, "structure_bias"), "bias")
        confidence = self._get(self._get(context, "structure_bias"), "confidence") or 0.0
        if bias in {"BULLISH", "BEARISH"}:
            return self._component("STRUCTURE_BIAS", bias, confidence, f"Structure bias is {bias.lower()} at {confidence:.2f}% confidence.")
        return self._component("STRUCTURE_BIAS", "NEUTRAL", 25.0 if bias == "RANGING" else 0.0, "Structure bias is not directional.")

    def _best_directional(self, name: str, context: Any, key: str, score_key: str) -> ConfluenceComponentScore:
        items = [item for item in self._items(context, key) if self._get(item, "valid") is not False]
        if not items:
            return self._component(name, "NEUTRAL", 0.0, f"No validated {name.lower().replace('_', ' ')} is available.")
        best = max(items, key=lambda item: float(self._get(item, score_key) or 0.0))
        direction = self._get(best, "direction") or "NEUTRAL"
        score = float(self._get(best, score_key) or 0.0)
        return self._component(name, direction, score, f"Strongest {name.lower().replace('_', ' ')} is {direction.lower()} with quality {score:.2f}.")

    def _zone_component(self, name: str, context: Any, fresh_key: str, mitigated_key: str) -> ConfluenceComponentScore:
        fresh = [item for item in self._items(context, fresh_key) if self._get(item, "valid") is not False]
        if fresh:
            best = max(fresh, key=lambda item: float(self._get(item, "strength") or 0.0))
            score = max(float(self._get(best, "strength") or 0.0), 60.0)
            direction = self._get(best, "direction") or "NEUTRAL"
            return self._component(name, direction, score, f"Fresh {direction.lower()} {name.lower().replace('_', ' ')} is available.")
        mitigated = [item for item in self._items(context, mitigated_key) if self._get(item, "valid") is not False]
        if mitigated:
            best = max(mitigated, key=lambda item: float(self._get(item, "strength") or 0.0))
            score = float(self._get(best, "strength") or 0.0) * 0.5
            direction = self._get(best, "direction") or "NEUTRAL"
            return self._component(name, direction, score, f"Only mitigated {direction.lower()} {name.lower().replace('_', ' ')} evidence remains.")
        return self._component(name, "NEUTRAL", 0.0, f"No qualified {name.lower().replace('_', ' ')} is available.")

    def _structure_shift(self, context: Any) -> ConfluenceComponentScore:
        events = [item for item in self._items(context, "events") if self._get(item, "valid") is not False]
        if not events:
            return self._component("STRUCTURE_SHIFT", "NEUTRAL", 0.0, "No validated BOS, CHOCH, or MSS event is available.")
        rank = {"MSS": 3, "BOS": 2, "CHOCH": 1}
        best = max(events, key=lambda item: (rank.get(self._get(item, "event_type"), 0), float(self._get(item, "strength") or 0.0)))
        direction = self._get(best, "direction") or "NEUTRAL"
        base = float(self._get(best, "strength") or 0.0)
        type_floor = {"MSS": 80.0, "BOS": 65.0, "CHOCH": 50.0}.get(self._get(best, "event_type"), 0.0)
        score = max(base, type_floor)
        return self._component("STRUCTURE_SHIFT", direction, score, f"{self._get(best, 'event_type')} supports {direction.lower()} structure.")

    def _premium_discount(self, context: Any) -> ConfluenceComponentScore:
        zone = self._get(self._get(context, "premium_discount"), "zone")
        if zone == "DISCOUNT":
            return self._component("PREMIUM_DISCOUNT", "BULLISH", 100.0, "Current price is positioned in discount.")
        if zone == "PREMIUM":
            return self._component("PREMIUM_DISCOUNT", "BEARISH", 100.0, "Current price is positioned in premium.")
        return self._component("PREMIUM_DISCOUNT", "NEUTRAL", 25.0 if zone == "EQUILIBRIUM" else 0.0, "Price is not in a directional dealing-range zone.")

    def _displacement(self, context: Any) -> ConfluenceComponentScore:
        moves = [move for move in self._items(context, "displacement") if self._get(move, "valid") is not False]
        if not moves:
            return self._component("DISPLACEMENT", "NEUTRAL", 0.0, "No qualifying displacement move is present.")
        latest = moves[-1]
        direction = self._get(latest, "direction") or "NEUTRAL"
        return self._component("DISPLACEMENT", direction, 80.0, f"Recent {direction.lower()} displacement is confirmed.")

    def _session(self, context: Any) -> ConfluenceComponentScore:
        if not context:
            return self._component("SESSION", "NEUTRAL", 0.0, "Session quality is unavailable.")
        high_liquidity = bool(self._get(context, "high_liquidity"))
        session = self._get(context, "current_session") or "Unknown"
        return self._component("SESSION", "NEUTRAL", 100.0 if high_liquidity else 35.0, f"{session} session liquidity quality evaluated.")

    def _risk(self, status: Any) -> ConfluenceComponentScore:
        readiness = self._get(status, "overall_status")
        if readiness == "OPERATIONAL":
            return self._component("RISK", "NEUTRAL", 100.0, "Risk controls report operational readiness.")
        if readiness == "BLOCKED":
            return self._component("RISK", "NEUTRAL", 0.0, "Risk controls currently block readiness.")
        return self._component("RISK", "NEUTRAL", 0.0, "Risk readiness is unavailable.")

    def _items(self, context: Any, key: str) -> list[Any]:
        if context is None:
            return []
        value = context.get(key, []) if isinstance(context, dict) else getattr(context, key, [])
        return list(value or [])

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
