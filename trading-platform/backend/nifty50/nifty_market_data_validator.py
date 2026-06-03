from backend.nifty50.nifty_market_data_models import NIFTYCandle, NIFTYTick


class NIFTYMarketDataValidator:
    def validate_candle(self, candle: NIFTYCandle) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if candle.symbol.upper() != "NIFTY50":
            errors.append("Only NIFTY50 candles are accepted.")
        if candle.high < candle.low:
            errors.append("Candle high must be greater than or equal to low.")
        if not candle.low <= candle.open <= candle.high:
            errors.append("Candle open must be within high-low range.")
        if not candle.low <= candle.close <= candle.high:
            errors.append("Candle close must be within high-low range.")
        if candle.volume < 0:
            errors.append("Candle volume must be non-negative.")
        return not errors, errors

    def validate_tick(self, tick: NIFTYTick) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if tick.symbol.upper() != "NIFTY50":
            errors.append("Only NIFTY50 ticks are accepted.")
        if tick.price <= 0:
            errors.append("Tick price must be positive.")
        return not errors, errors

    def validate_snapshot(self, snapshot: dict) -> tuple[bool, list[str]]:
        if snapshot.get("symbol") != "NIFTY50":
            return False, ["Snapshot symbol must be NIFTY50."]
        return True, []
