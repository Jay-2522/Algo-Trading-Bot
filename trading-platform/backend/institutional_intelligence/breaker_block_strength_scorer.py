from typing import Any

from backend.institutional_intelligence.breaker_block_models import BreakerBlock, BreakerBlockStrengthScore


class BreakerBlockStrengthScorer:
    """Rank breaker reactions with explicit structure-shift and confluence factors."""

    def score_breaker_block(
        self,
        breaker_block: BreakerBlock,
        fvg_context: Any = None,
        sweep_context: Any = None,
        structure_bias: Any = None,
    ) -> BreakerBlockStrengthScore:
        range_ratio = float(breaker_block.metadata.get("displacement_range_ratio", 0.0))
        body_ratio = float(breaker_block.metadata.get("displacement_body_ratio", 0.0))
        expansion_quality = min(range_ratio / 2.0, 1.0)
        displacement_score = round(25.0 * ((expansion_quality + min(body_ratio, 1.0)) / 2.0), 2)
        structure_shift_score = 25.0 if breaker_block.valid and breaker_block.structure_shift_confirmed else 0.0
        freshness_score = {
            "FRESH": 20.0,
            "PARTIALLY_MITIGATED": 10.0,
            "MITIGATED": 0.0,
        }[breaker_block.mitigation_status]
        mitigation_score = round(max(15.0 * (1.0 - breaker_block.mitigation_percent / 100.0), 0.0), 2)
        fvg_id = self.find_related_fvg(breaker_block, fvg_context)
        sweep_id = self.find_related_sweep(breaker_block, sweep_context)
        bias = self._bias(structure_bias)
        bias_aligned = bias == breaker_block.direction
        confluence_score = (5.0 if fvg_id else 0.0) + (5.0 if sweep_id else 0.0) + (5.0 if bias_aligned else 0.0)
        score = round(
            min(
                displacement_score
                + structure_shift_score
                + freshness_score
                + mitigation_score
                + confluence_score,
                100.0,
            ),
            2,
        )
        return BreakerBlockStrengthScore(
            score=score,
            displacement_score=displacement_score,
            structure_shift_score=structure_shift_score,
            freshness_score=freshness_score,
            mitigation_score=mitigation_score,
            confluence_score=confluence_score,
            reason=(
                f"{breaker_block.direction.lower()} breaker is {breaker_block.mitigation_status.lower()}; "
                f"FVG={bool(fvg_id)}, sweep={bool(sweep_id)}, bias_aligned={bias_aligned}."
            ),
        )

    def find_related_fvg(self, breaker_block: BreakerBlock, context: Any) -> str | None:
        for fvg in self._items(context, "fresh_fvgs"):
            direction = self._get(fvg, "direction")
            start_index = self._get(fvg, "start_index")
            if direction == breaker_block.direction and start_index is not None:
                if breaker_block.candle_index - 1 <= int(start_index) <= breaker_block.candle_index + 2:
                    return self._get(fvg, "fvg_id")
        return None

    def find_related_sweep(self, breaker_block: BreakerBlock, context: Any) -> str | None:
        for sweep in reversed(self._items(context, "sweeps")):
            direction = self._get(sweep, "direction")
            index = self._get(sweep, "candle_index")
            valid = self._get(sweep, "valid")
            if direction == breaker_block.direction and valid and index is not None:
                if breaker_block.candle_index - 5 <= int(index) <= breaker_block.candle_index:
                    return self._get(sweep, "sweep_id")
        return None

    def _items(self, context: Any, key: str) -> list[Any]:
        if context is None:
            return []
        value = context.get(key, []) if isinstance(context, dict) else getattr(context, key, [])
        return list(value or [])

    def _get(self, value: Any, key: str) -> Any:
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)

    def _bias(self, context: Any) -> str | None:
        if context is None:
            return None
        if isinstance(context, str):
            return context
        return context.get("bias") if isinstance(context, dict) else getattr(context, "bias", None)
