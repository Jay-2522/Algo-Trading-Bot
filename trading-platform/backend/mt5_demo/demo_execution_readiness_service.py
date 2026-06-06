from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.mt5_demo.demo_execution_simulator_service import DemoExecutionSimulatorService
from backend.mt5_demo.demo_order_authorization_service import DemoOrderAuthorizationService
from backend.mt5_demo.demo_order_dry_run_service import DemoOrderDryRunService
from backend.mt5_demo.demo_order_preflight_service import DemoOrderPreflightService
from backend.mt5_demo.market_snapshot_service import MarketSnapshotService
from backend.mt5_demo.mt5_demo_service import MT5DemoService
from backend.mt5_demo.mt5_execution_gate_validation_service import MT5ExecutionGateValidationService
from backend.mt5_demo.mt5_historical_backfill_service import MT5HistoricalBackfillService
from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService
from backend.mt5_demo.mt5_risk_qualification_service import MT5RiskQualificationService
from backend.mt5_demo.mt5_strategy_consumption_service import MT5StrategyConsumptionService
from backend.mt5_demo.mt5_strategy_feed_adapter import MT5StrategyFeedAdapter


class DemoExecutionReadinessService:
    """Audits whether the demo pipeline is technically ready for a future single demo trade."""

    def __init__(
        self,
        mt5_demo_service: MT5DemoService,
        market_data_service: MT5MarketDataService,
        market_snapshot_service: MarketSnapshotService,
        historical_backfill_service: MT5HistoricalBackfillService,
        strategy_feed_adapter: MT5StrategyFeedAdapter,
        strategy_consumption_service: MT5StrategyConsumptionService,
        risk_qualification_service: MT5RiskQualificationService,
        execution_gate_service: MT5ExecutionGateValidationService,
        authorization_service: DemoOrderAuthorizationService,
        dry_run_service: DemoOrderDryRunService,
        preflight_service: DemoOrderPreflightService,
        simulator_service: DemoExecutionSimulatorService,
    ) -> None:
        self.mt5_demo_service = mt5_demo_service
        self.market_data_service = market_data_service
        self.market_snapshot_service = market_snapshot_service
        self.historical_backfill_service = historical_backfill_service
        self.strategy_feed_adapter = strategy_feed_adapter
        self.strategy_consumption_service = strategy_consumption_service
        self.risk_qualification_service = risk_qualification_service
        self.execution_gate_service = execution_gate_service
        self.authorization_service = authorization_service
        self.dry_run_service = dry_run_service
        self.preflight_service = preflight_service
        self.simulator_service = simulator_service
        self._history: list[dict[str, Any]] = []

    def run_readiness_audit(self) -> dict[str, Any]:
        mt5_status = self.mt5_demo_service.get_status()
        market_status = self.market_data_service.get_market_data_status()
        historical_status = self._historical_readiness_status()
        strategy_feed = self.strategy_feed_adapter.build_strategy_feed("EURUSD")
        strategy_consumption = self.strategy_consumption_service.get_status()
        risk_status = self.risk_qualification_service.get_status()
        gate_status = self.execution_gate_service.get_status()
        authorization = self.authorization_service.get_status()
        dry_run = self.dry_run_service.get_latest()
        preflight = self.preflight_service.get_latest()
        simulator = self.simulator_service.get_latest()

        component_scores = {
            "mt5_connection": self._score(mt5_status.get("status") == "CONNECTED"),
            "market_data": self._score(market_status.get("status") == "READY"),
            "historical_data": self._score(historical_status.get("status") == "READY"),
            "strategy_feed": self._score(strategy_feed.get("feed_ready") is True or strategy_feed.get("status") in {"READY", "OK"}),
            "strategy_consumption": self._score(strategy_consumption.get("status") == "STRATEGY_CONSUMPTION_READY"),
            "risk_qualification": self._score(risk_status.get("status") == "RISK_QUALIFICATION_READY"),
            "execution_gate": self._score(gate_status.get("status") == "EXECUTION_GATE_VALIDATION_READY"),
            "authorization_layer": self._score(authorization.get("status") == "READY_FOR_DEMO_ORDER_TESTING"),
            "preflight_validation": self._score(preflight.get("validation_passed") is True),
            "execution_simulator": self._score(simulator.get("simulation_passed") is True),
        }
        blockers = self._blockers(
            mt5_status,
            market_status,
            historical_status,
            strategy_feed,
            authorization,
            dry_run,
            preflight,
            simulator,
        )
        overall_score = sum(component_scores.values())
        result = {
            "audit_id": f"demo-readiness-{uuid4()}",
            "overall_score": overall_score,
            "overall_status": self._overall_status(overall_score, blockers),
            "component_scores": component_scores,
            "blockers": blockers,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }
        self._history.append(result)
        return result

    def get_latest_audit(self) -> dict[str, Any]:
        if self._history:
            return self._history[-1]
        return {
            "status": "NOT_RUN",
            "overall_score": 0,
            "overall_status": "NOT_READY",
            "blockers": ["AUDIT_NOT_RUN"],
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def get_audit_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def get_status(self) -> dict[str, Any]:
        latest = self.get_latest_audit()
        return {
            "status": "READINESS_AUDIT_READY",
            "latest_overall_score": latest.get("overall_score", 0),
            "latest_overall_status": latest.get("overall_status", "NOT_READY"),
            "history_count": len(self._history),
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def _score(self, passed: bool) -> int:
        return 10 if passed else 0

    def _overall_status(self, score: int, blockers: list[str]) -> str:
        non_execution_blockers = [blocker for blocker in blockers if blocker != "EXECUTION_DISABLED"]
        if score >= 90 and not non_execution_blockers:
            return "READY"
        if score >= 50:
            return "PARTIALLY_READY"
        return "NOT_READY"

    def _blockers(
        self,
        mt5_status: dict[str, Any],
        market_status: dict[str, Any],
        historical_status: dict[str, Any],
        strategy_feed: dict[str, Any],
        authorization: dict[str, Any],
        dry_run: dict[str, Any],
        preflight: dict[str, Any],
        simulator: dict[str, Any],
    ) -> list[str]:
        blockers = ["EXECUTION_DISABLED"]
        if mt5_status.get("status") != "CONNECTED":
            blockers.append("DEMO_ACCOUNT_OFFLINE")
        if market_status.get("status") != "READY":
            blockers.append("MARKET_DATA_STALE")
        if historical_status.get("status") != "READY":
            blockers.append("HISTORICAL_DATA_UNAVAILABLE")
        if not (strategy_feed.get("feed_ready") is True or strategy_feed.get("status") in {"READY", "OK"}):
            blockers.append("STRATEGY_FEED_UNAVAILABLE")
        if authorization.get("status") != "READY_FOR_DEMO_ORDER_TESTING":
            blockers.append("AUTHORIZATION_LOCKED")
        if dry_run.get("validation_passed") is not True:
            blockers.append("DRY_RUN_NOT_VALIDATED")
        if preflight.get("validation_passed") is not True:
            blockers.append("PRECHECK_FAILED")
        if simulator.get("simulation_passed") is not True:
            blockers.append("SIMULATION_NOT_RUN")
        return blockers

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _historical_readiness_status(self) -> dict[str, Any]:
        eurusd = self.historical_backfill_service.summarize_backfill("EURUSD", "H1")
        xauusd = self.historical_backfill_service.summarize_backfill("XAUUSD", "H1")
        summaries = [eurusd, xauusd]
        ready = all(
            item.get("status") == "OK"
            and int(item.get("returned_count") or 0) > 0
            and (item.get("validation") or {}).get("valid") is True
            for item in summaries
        )
        return {
            "status": "READY" if ready else "UNAVAILABLE",
            "summaries": summaries,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }
