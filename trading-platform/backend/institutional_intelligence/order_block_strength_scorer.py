from typing import Any

from backend.institutional_intelligence.order_block_models import OrderBlock, OrderBlockStrengthScore


class OrderBlockStrengthScorer:
    """Produce bounded, explainable quality scores for validated order blocks."""

    def score_order_block(
        self,
        order_block: OrderBlock,
        candles: list[Any] | None,
        fvg_context: Any = None,
        sweep_context: Any = None,
        structure_bias: Any = None,
    ) -> OrderBlockStrengthScore:
        range_ratio = float(order_block.metadata.get("displacement_range_ratio", 0.0))
        body_ratio = float(order_block.metadata.get("displacement_body_ratio", 0.0))
        expansion_quality = min(range_ratio / 2.0, 1.0)
        displacement_score = (
            round(25.0 * ((expansion_quality + min(body_ratio, 1.0)) / 2.0), 2)
            if order_block.displacement_confirmed
            else 0.0
        )
        bos_score = 25.0 if order_block.bos_confirmed else 0.0
        freshness_score = {"FRESH": 20.0, "PARTIAL": 10.0, "MITIGATED": 0.0}[order_block.mitigation_status]
        mitigation_score = round(max(15.0 * (1.0 - order_block.mitigation_percent / 100.0), 0.0), 2)
        fvg_id = self._related_fvg(order_block, fvg_context)
        sweep_id = self._related_sweep(order_block, sweep_context)
        bias = self._bias(structure_bias)
        bias_aligned = bias == order_block.direction
        confluence_score = (5.0 if fvg_id else 0.0) + (5.0 if sweep_id else 0.0) + (5.0 if bias_aligned else 0.0)
        score = round(
            min(
                displacement_score + bos_score + freshness_score + mitigation_score + confluence_score,
                100.0,
            ),
            2,
        )
        return OrderBlockStrengthScore(
            score=score,
            displacement_score=displacement_score,
            bos_score=bos_score,
            freshness_score=freshness_score,
            mitigation_score=mitigation_score,
            confluence_score=confluence_score,
            reason=(
                f"{order_block.direction.lower()} order block is {order_block.mitigation_status.lower()}; "
                f"FVG={bool(fvg_id)}, sweep={bool(sweep_id)}, bias_aligned={bias_aligned}."
            ),
        )

    def find_related_fvg(self, order_block: OrderBlock, fvg_context: Any) -> str | None:
        return self._related_fvg(order_block, fvg_context)

    def find_related_sweep(self, order_block: OrderBlock, sweep_context: Any) -> str | None:
        return self._related_sweep(order_block, sweep_context)

    def _related_fvg(self, order_block: OrderBlock, context: Any) -> str | None:
        fvgs = self._items(context, "fresh_fvgs")
        for fvg in fvgs:
            direction = self._get(fvg, "direction")
            start_index = self._get(fvg, "start_index")
            if direction == order_block.direction and start_index is not None:
                if order_block.candle_index <= int(start_index) <= order_block.candle_index + 3:
                    return self._get(fvg, "fvg_id")
        return None

    def _related_sweep(self, order_block: OrderBlock, context: Any) -> str | None:
        sweeps = self._items(context, "sweeps")
        for sweep in reversed(sweeps):
            direction = self._get(sweep, "direction")
            index = self._get(sweep, "candle_index")
            valid = self._get(sweep, "valid")
            if direction == order_block.direction and valid and index is not None:
                if order_block.candle_index - 5 <= int(index) <= order_block.candle_index:
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
