from backend.nifty50.nifty_strategy_models import NIFTYFVGContext


class NIFTYFVGService:
    def __init__(self, market_data_service=None) -> None:
        self.market_data_service = market_data_service

    def get_status(self) -> dict:
        return {
            "status": "PLACEHOLDER_READY",
            "component": "NIFTY50_FVG",
            "placeholder": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def analyze_fvg(self) -> NIFTYFVGContext:
        if not self.market_data_service:
            return NIFTYFVGContext()
        candles = self.market_data_service.candle_store.get_recent(limit=200)
        if len(candles) < 3:
            return NIFTYFVGContext()
        gaps: list[dict] = []
        for index in range(2, len(candles)):
            first = candles[index - 2]
            third = candles[index]
            if third.low > first.high:
                gaps.append(
                    {
                        "direction": "BULLISH",
                        "lower_bound": first.high,
                        "upper_bound": third.low,
                        "timestamp": third.timestamp.isoformat(),
                    }
                )
            elif third.high < first.low:
                gaps.append(
                    {
                        "direction": "BEARISH",
                        "lower_bound": third.high,
                        "upper_bound": first.low,
                        "timestamp": third.timestamp.isoformat(),
                    }
                )
        latest = gaps[-1] if gaps else None
        return NIFTYFVGContext(
            fair_value_gaps=gaps,
            active_fvg_detected=bool(gaps),
            fvg_direction=latest["direction"] if latest else "NONE",
            confidence=60.0 if gaps else 0.0,
            placeholder=False,
        )

    def get_snapshot(self) -> NIFTYFVGContext:
        return self.analyze_fvg()
