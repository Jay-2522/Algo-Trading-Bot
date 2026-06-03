from backend.nifty50.nifty_candle_store import NIFTYCandleStore
from backend.nifty50.nifty_market_data_models import NIFTYCandle, NIFTYMarketDataHealth, NIFTYTick
from backend.nifty50.nifty_market_data_validator import NIFTYMarketDataValidator
from backend.nifty50.nifty_snapshot_builder import NIFTYSnapshotBuilder


class NIFTYMarketDataAdapter:
    def __init__(
        self,
        candle_store: NIFTYCandleStore | None = None,
        validator: NIFTYMarketDataValidator | None = None,
        snapshot_builder: NIFTYSnapshotBuilder | None = None,
    ) -> None:
        self.candle_store = candle_store or NIFTYCandleStore()
        self.validator = validator or NIFTYMarketDataValidator()
        self.snapshot_builder = snapshot_builder or NIFTYSnapshotBuilder(candle_store=self.candle_store)

    def ingest_candle(self, candle: NIFTYCandle) -> dict:
        valid, errors = self.validator.validate_candle(candle)
        if not valid:
            self.candle_store.record_invalid_candle()
            return {"accepted": False, "errors": errors, "simulation_only": True, "broker_execution_enabled": False}
        stored = self.candle_store.add_candle(candle)
        return {"accepted": True, "candle": stored.model_dump(mode="json"), "simulation_only": True, "broker_execution_enabled": False}

    def ingest_tick(self, tick: NIFTYTick) -> dict:
        valid, errors = self.validator.validate_tick(tick)
        if not valid:
            return {"accepted": False, "errors": errors, "simulation_only": True, "broker_execution_enabled": False}
        stored = self.candle_store.add_tick(tick)
        return {"accepted": True, "tick": stored.model_dump(mode="json"), "simulation_only": True, "broker_execution_enabled": False}

    def get_health(self) -> NIFTYMarketDataHealth:
        return self.snapshot_builder.get_health()
