from typing import Any

from backend.mt5_demo.mt5_historical_backfill_service import MT5HistoricalBackfillService


class MT5StrategyFeedAdapter:
    """Prepare read-only MT5 demo historical candles for strategy consumers."""

    strategy_timeframes = {"M5": 300, "H1": 200, "H4": 100}

    def __init__(self, backfill_service: MT5HistoricalBackfillService | None = None) -> None:
        self.backfill_service = backfill_service or MT5HistoricalBackfillService()

    def build_strategy_feed(self, symbol: str) -> dict[str, Any]:
        warnings: list[str] = []
        timeframes: dict[str, list[dict[str, Any]]] = {}
        validation: dict[str, Any] = {}
        for timeframe, count in self.strategy_timeframes.items():
            history = self.backfill_service.fetch_history(symbol, timeframe, count=count)
            timeframes[timeframe] = history.get("candles", [])
            validation[timeframe] = history.get("validation")
            if history.get("status") != "OK":
                warnings.append(f"{timeframe} history unavailable: {history.get('message', history.get('status'))}")
            elif history.get("validation", {}).get("stale"):
                warnings.append(f"{timeframe} history is stale.")
            if history.get("validation", {}).get("gaps_detected"):
                warnings.append(f"{timeframe} history has gaps.")

        feed_ready = all(timeframes.get(timeframe) for timeframe in self.strategy_timeframes)
        return {
            "symbol": str(symbol or "").strip().upper(),
            "source": "MT5_DEMO_HISTORY",
            "timeframes": timeframes,
            "validation": validation,
            "feed_ready": feed_ready,
            "warnings": warnings,
            "forced_signal": False,
            "execution_triggered": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def get_htf_context(self, symbol: str) -> dict[str, Any]:
        feed = self.build_strategy_feed(symbol)
        return {
            "symbol": feed["symbol"],
            "source": feed["source"],
            "timeframes": {
                "H1": feed["timeframes"].get("H1", []),
                "H4": feed["timeframes"].get("H4", []),
            },
            "feed_ready": bool(feed["timeframes"].get("H1")) and bool(feed["timeframes"].get("H4")),
            "warnings": [warning for warning in feed["warnings"] if warning.startswith(("H1", "H4"))],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def get_ltf_context(self, symbol: str) -> dict[str, Any]:
        feed = self.build_strategy_feed(symbol)
        return {
            "symbol": feed["symbol"],
            "source": feed["source"],
            "timeframes": {
                "M5": feed["timeframes"].get("M5", []),
            },
            "feed_ready": bool(feed["timeframes"].get("M5")),
            "warnings": [warning for warning in feed["warnings"] if warning.startswith("M5")],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }
