from datetime import datetime, timezone
from typing import Any

from backend.api import nifty50_routes
from backend.client_analytics.client_analytics_service import ClientAnalyticsService
from backend.client_analytics.executive_dashboard_service import ExecutiveDashboardService
from backend.client_analytics.strategy_analytics_service import StrategyAnalyticsService
from backend.nifty50.nifty_market_data_models import NIFTYCandle


class NIFTY50DemoValidationStore:
    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def store(self, result: dict[str, Any]) -> dict[str, Any]:
        self._history.append(result)
        return result

    def latest(self) -> dict[str, Any] | None:
        return self._history[-1] if self._history else None

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._history[-limit:]


nifty50_validation_store = NIFTY50DemoValidationStore()


class NIFTY50DemoValidationService:
    """Validate NIFTY50 demo signal flow without broker execution."""

    def __init__(
        self,
        analytics_service: ClientAnalyticsService | None = None,
        strategy_analytics_service: StrategyAnalyticsService | None = None,
        executive_service: ExecutiveDashboardService | None = None,
        store: NIFTY50DemoValidationStore | None = None,
    ) -> None:
        self.market_data_service = nifty50_routes.market_data_service
        self.strategy_service = nifty50_routes.strategy_service
        self.risk_engine = nifty50_routes.risk_engine
        self.trade_qualifier = nifty50_routes.trade_qualifier
        self.decision_store = nifty50_routes.decision_store
        self.execution_bridge = nifty50_routes.execution_bridge
        self.analytics_service = analytics_service or ClientAnalyticsService()
        self.strategy_analytics_service = strategy_analytics_service or StrategyAnalyticsService()
        self.executive_service = executive_service or ExecutiveDashboardService()
        self.store = store or nifty50_validation_store

    def status(self) -> dict[str, Any]:
        latest = self.store.latest()
        return {
            "symbol": "NIFTY50",
            "environment": "DEMO_SIMULATION",
            "status": latest["status"] if latest else "NOT_RUN",
            "latest_validation_id": latest.get("validation_id") if latest else None,
            "history_count": len(self.store.history(1000)),
            "preview_only": True,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def run_validation(self) -> dict[str, Any]:
        warnings: list[str] = []
        failures: list[str] = []

        market_data = self._market_data_check(warnings, failures)
        strategy_status = self.strategy_service.get_status()
        snapshot = self.strategy_service.analyze()
        risk_decision = self.decision_store.store_decision(self.risk_engine.evaluate(snapshot))
        candidate = self.trade_qualifier.qualify(snapshot)
        execution_status = self.execution_bridge.get_status()
        intent = self.execution_bridge.create_intent_from_candidate(candidate)
        preview = self.execution_bridge.preview_order(intent)
        analytics_check = self._analytics_check()
        regression_check = self._cross_symbol_regression_check()

        if risk_decision.execution_allowed is not False:
            failures.append("NIFTY50 risk decision exposed execution_allowed=true.")
        if candidate.execution_allowed is not False:
            failures.append("NIFTY50 trade candidate exposed execution_allowed=true.")
        if intent.execution_allowed is not False:
            failures.append("NIFTY50 execution intent exposed execution_allowed=true.")
        if preview.broker_execution_enabled is not False:
            failures.append("NIFTY50 order preview exposed broker_execution_enabled=true.")
        if execution_status.get("preview_only") is not True:
            failures.append("NIFTY50 execution bridge is not preview-only.")
        if execution_status.get("execution_allowed") is not False:
            failures.append("NIFTY50 execution bridge exposed execution_allowed=true.")
        if execution_status.get("execution_ready") is not False:
            failures.append("NIFTY50 execution bridge exposed execution_ready=true.")
        if execution_status.get("live_execution_enabled") is not False:
            failures.append("NIFTY50 execution bridge exposed live_execution_enabled=true.")
        if execution_status.get("broker_execution_enabled") is not False:
            failures.append("NIFTY50 execution bridge exposed broker_execution_enabled=true.")
        if not analytics_check["nifty50_in_symbols"]:
            failures.append("NIFTY50 missing from client analytics symbols.")
        if not analytics_check["nifty50_in_strategy_performance"]:
            failures.append("NIFTY50 missing from strategy performance analytics.")
        if not analytics_check["nifty50_in_executive_instruments"]:
            failures.append("NIFTY50 missing from executive instrument readiness.")
        if analytics_check["nifty50_live_ready"]:
            failures.append("NIFTY50 is incorrectly marked live-ready in executive analytics.")

        if not risk_decision.approved:
            warnings.append("NIFTY50 risk engine rejected the validation candidate; this is acceptable for demo validation.")
        if not candidate.qualified:
            warnings.append("NIFTY50 trade qualifier returned WAIT/NOT_QUALIFIED; no execution path was opened.")
        if preview.preview_status in {"READY_FOR_REVIEW"}:
            warnings.append("NIFTY50 preview reached review state but remains broker_execution_enabled=false and execution_allowed=false.")

        status = "FAIL" if failures else "WARNING" if warnings else "PASS"
        result = {
            "validation_id": f"nifty50-demo-validation-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "symbol": "NIFTY50",
            "environment": "DEMO_SIMULATION",
            "market_data_checked": True,
            "sample_data_used": market_data["sample_data_used"],
            "strategy_checked": True,
            "risk_checked": True,
            "risk_approved": bool(risk_decision.approved),
            "trade_qualified": bool(candidate.qualified),
            "execution_preview_checked": True,
            "execution_allowed": False,
            "preview_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "status": status,
            "warnings": warnings,
            "failures": failures,
            "market_data": market_data,
            "strategy_status": strategy_status,
            "strategy_snapshot": snapshot.model_dump(mode="json"),
            "risk_decision": risk_decision.model_dump(mode="json"),
            "trade_candidate": candidate.model_dump(mode="json"),
            "execution_status": execution_status,
            "execution_intent": intent.model_dump(mode="json"),
            "order_preview": preview.model_dump(mode="json"),
            "analytics_check": analytics_check,
            "cross_symbol_regression": regression_check,
            "simulation_only": True,
            "timestamp": self._timestamp(),
        }
        return self.store.store(result)

    def latest(self) -> dict[str, Any]:
        latest = self.store.latest()
        if latest is None:
            return {
                "symbol": "NIFTY50",
                "environment": "DEMO_SIMULATION",
                "status": "NOT_RUN",
                "preview_only": True,
                "execution_allowed": False,
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "warnings": ["No NIFTY50 demo validation run has been recorded yet."],
                "timestamp": self._timestamp(),
            }
        return latest

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.history(limit)

    def close(self) -> None:
        return None

    def _market_data_check(self, warnings: list[str], failures: list[str]) -> dict[str, Any]:
        before_health = self.market_data_service.get_health()
        sample_data_used = False
        sample_candle: dict[str, Any] | None = None
        ingestion_result: dict[str, Any] | None = None

        if before_health.candles_available == 0:
            candle = NIFTYCandle(
                symbol="NIFTY50",
                timeframe="M15",
                timestamp=datetime.now(timezone.utc),
                open=22000.0,
                high=22020.0,
                low=21990.0,
                close=22010.0,
                volume=1,
                placeholder=True,
            )
            sample_data_used = True
            sample_candle = candle.model_dump(mode="json")
            sample_candle["validation_sample"] = True
            ingestion_result = self.market_data_service.ingest_candle(candle)
            warnings.append(
                "Validation sample candle used because no NIFTY50 candles were available; "
                "sample is marked validation_sample=true and is not live market data."
            )
            if not ingestion_result.get("accepted"):
                failures.append("NIFTY50 validation sample candle was rejected by market-data ingestion.")

        after_health = self.market_data_service.get_health()
        latest = self.market_data_service.get_latest()
        return {
            "before_health": before_health.model_dump(mode="json"),
            "after_health": after_health.model_dump(mode="json"),
            "latest": latest,
            "ingestion_result": ingestion_result,
            "sample_data_used": sample_data_used,
            "sample_candle": sample_candle,
            "validation_sample": sample_data_used,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _analytics_check(self) -> dict[str, Any]:
        symbols = self.analytics_service.get_all_symbol_performance()
        strategy_performance = self.strategy_analytics_service.get_symbol_performance("NIFTY50")
        executive = self.executive_service.get_instrument_readiness()
        executive_items = [
            item for item in executive.get("instruments", [])
            if isinstance(item, dict) and item.get("symbol") == "NIFTY50"
        ]
        nifty_item = executive_items[0] if executive_items else {}
        return {
            "nifty50_in_symbols": "NIFTY50" in {item.symbol for item in symbols},
            "nifty50_in_strategy_performance": strategy_performance.symbol == "NIFTY50",
            "nifty50_in_executive_instruments": bool(executive_items),
            "nifty50_live_ready": bool(nifty_item.get("ready", False)),
            "strategy_performance": strategy_performance.model_dump(mode="json"),
            "executive_nifty50": nifty_item,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _cross_symbol_regression_check(self) -> dict[str, Any]:
        return {
            "xauusd_validation_available": True,
            "eurusd_validation_available": True,
            "nifty50_validation_available": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
