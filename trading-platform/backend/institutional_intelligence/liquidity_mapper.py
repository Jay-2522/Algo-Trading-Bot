from typing import Any

from backend.institutional_intelligence.smc_models import LiquidityPool, SwingPoint


class LiquidityMapper:
    """Classify structural stop-liquidity levels without creating trade signals."""

    def detect_equal_highs(self, swings: list[SwingPoint], tolerance: float = 0.1) -> list[LiquidityPool]:
        return self._equal_pools(swings, "HIGH", "EQUAL_HIGHS", tolerance)

    def detect_equal_lows(self, swings: list[SwingPoint], tolerance: float = 0.1) -> list[LiquidityPool]:
        return self._equal_pools(swings, "LOW", "EQUAL_LOWS", tolerance)

    def map_liquidity_pools(self, candles: list[Any], swings: list[SwingPoint]) -> list[LiquidityPool]:
        symbol = self._symbol(candles)
        pools = self.detect_equal_highs(swings) + self.detect_equal_lows(swings)
        highs = [swing for swing in swings if swing.type == "HIGH"]
        lows = [swing for swing in swings if swing.type == "LOW"]
        if highs:
            external_high = max(highs, key=lambda swing: swing.price)
            pools.append(self._pool(symbol, external_high, "EXTERNAL_LIQUIDITY"))
            latest_high = highs[-1]
            pools.append(self._pool(symbol, latest_high, "PREVIOUS_HIGH"))
        if lows:
            external_low = min(lows, key=lambda swing: swing.price)
            pools.append(self._pool(symbol, external_low, "EXTERNAL_LIQUIDITY"))
            latest_low = lows[-1]
            pools.append(self._pool(symbol, latest_low, "PREVIOUS_LOW"))
        external_indexes = {
            pool.related_swings[0] for pool in pools if pool.liquidity_type == "EXTERNAL_LIQUIDITY"
        }
        for swing in swings:
            if swing.index not in external_indexes:
                pools.append(self._pool(symbol, swing, "INTERNAL_LIQUIDITY"))
        return self._deduplicate(pools, symbol)

    def mark_swept_liquidity(self, pools: list[LiquidityPool], current_price: float) -> list[LiquidityPool]:
        high_types = {"EQUAL_HIGHS", "PREVIOUS_HIGH"}
        low_types = {"EQUAL_LOWS", "PREVIOUS_LOW"}
        marked = []
        for pool in pools:
            swept = pool.swept
            if pool.liquidity_type in high_types:
                swept = current_price > pool.price_level
            elif pool.liquidity_type in low_types:
                swept = current_price < pool.price_level
            marked.append(pool.model_copy(update={"swept": swept}))
        return marked

    def _equal_pools(
        self,
        swings: list[SwingPoint],
        swing_type: str,
        liquidity_type: str,
        tolerance: float,
    ) -> list[LiquidityPool]:
        candidates = [swing for swing in swings if swing.type == swing_type]
        groups: list[list[SwingPoint]] = []
        for swing in candidates:
            matched = next(
                (group for group in groups if abs(swing.price - group[0].price) <= tolerance),
                None,
            )
            if matched is None:
                groups.append([swing])
            else:
                matched.append(swing)
        pools = []
        for group in groups:
            if len(group) >= 2:
                pools.append(
                    LiquidityPool(
                        symbol="UNKNOWN",
                        price_level=round(sum(swing.price for swing in group) / len(group), 5),
                        liquidity_type=liquidity_type,
                        strength=float(len(group)),
                        related_swings=[swing.index for swing in group],
                        timestamp=group[-1].timestamp,
                    )
                )
        return pools

    def _pool(self, symbol: str, swing: SwingPoint, liquidity_type: str) -> LiquidityPool:
        return LiquidityPool(
            symbol=symbol,
            price_level=swing.price,
            liquidity_type=liquidity_type,
            strength=max(1.0, round(swing.strength, 5)),
            related_swings=[swing.index],
            timestamp=swing.timestamp,
        )

    def _deduplicate(self, pools: list[LiquidityPool], symbol: str) -> list[LiquidityPool]:
        unique = {}
        for pool in pools:
            normalized = pool.model_copy(update={"symbol": symbol})
            key = (normalized.liquidity_type, tuple(normalized.related_swings), normalized.price_level)
            unique[key] = normalized
        return list(unique.values())

    def _symbol(self, candles: list[Any]) -> str:
        if not candles:
            return "UNKNOWN"
        first = candles[0]
        value = first.get("symbol", "UNKNOWN") if isinstance(first, dict) else getattr(first, "symbol", "UNKNOWN")
        return str(value).strip().upper() or "UNKNOWN"
