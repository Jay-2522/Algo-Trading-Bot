from typing import Any

from backend.institutional_intelligence.smc_models import PremiumDiscountZone


class PremiumDiscountAnalyzer:
    """Locate current price inside its observed dealing range."""

    def calculate_zone(
        self,
        candles: list[Any] | None,
        current_price: float | None = None,
    ) -> PremiumDiscountZone:
        valid = [self._values(candle) for candle in (candles or [])]
        valid = [value for value in valid if value is not None]
        if not valid:
            return PremiumDiscountZone()
        high = max(value["high"] for value in valid)
        low = min(value["low"] for value in valid)
        equilibrium = (high + low) / 2
        price = float(current_price) if current_price is not None else valid[-1]["close"]
        tolerance = max(abs(high - low) * 0.001, 1e-9)
        if price > equilibrium + tolerance:
            zone = "PREMIUM"
        elif price < equilibrium - tolerance:
            zone = "DISCOUNT"
        else:
            zone = "EQUILIBRIUM"
        return PremiumDiscountZone(
            range_high=round(high, 5),
            range_low=round(low, 5),
            equilibrium=round(equilibrium, 5),
            current_price=round(price, 5),
            zone=zone,
        )

    def _values(self, candle: Any) -> dict | None:
        try:
            high = float(candle["high"] if isinstance(candle, dict) else candle.high)
            low = float(candle["low"] if isinstance(candle, dict) else candle.low)
            close = float(candle["close"] if isinstance(candle, dict) else candle.close)
            if high < low:
                return None
            return {"high": high, "low": low, "close": close}
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
