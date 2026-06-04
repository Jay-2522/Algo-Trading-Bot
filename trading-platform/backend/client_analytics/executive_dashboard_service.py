from backend.client_analytics.executive_models import ExecutiveDashboardSummary, ExecutiveSystemHealth
from backend.client_analytics.readiness_aggregator import ReadinessAggregator


class ExecutiveDashboardService:
    def __init__(self, aggregator: ReadinessAggregator | None = None) -> None:
        self.aggregator = aggregator or ReadinessAggregator()

    def get_status(self) -> dict:
        return {
            "status": "OPERATIONAL",
            "executive_dashboard_ready": True,
            "client_acceptance_dashboard_ready": True,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_summary(self) -> ExecutiveDashboardSummary:
        instruments = {item.symbol: item.ready for item in self.aggregator.get_instrument_status()}
        return ExecutiveDashboardSummary(
            analytics_ready=self.aggregator.get_analytics_status().status == "READY",
            reports_ready=self.aggregator.get_reporting_status().status == "READY",
            accounts_ready=self.aggregator.get_account_status().status == "READY",
            copier_ready=self.aggregator.get_copier_status().status == "READY",
            strategy_ready=self.aggregator.get_strategy_status().status == "READY",
            deployment_ready=self.aggregator.get_deployment_status().status == "READY",
            monitoring_ready=self.aggregator.get_monitoring_status().status == "READY",
            security_ready=self.aggregator.get_security_status().status == "READY",
            production_ready=False,
            xauusd_ready=instruments["XAUUSD"],
            eurusd_ready=instruments["EURUSD"],
            nifty50_ready=instruments["NIFTY50"],
            overall_completion_percentage=self.aggregator.get_overall_completion(),
        )

    def get_readiness_matrix(self) -> dict:
        items = [
            self.aggregator.get_analytics_status(),
            self.aggregator.get_reporting_status(),
            self.aggregator.get_account_status(),
            self.aggregator.get_copier_status(),
            self.aggregator.get_strategy_status(),
            self.aggregator.get_deployment_status(),
            self.aggregator.get_monitoring_status(),
            self.aggregator.get_security_status(),
            self.aggregator.get_production_status(),
        ]
        return {
            "items": [item.model_dump(mode="json") for item in items],
            "overall_completion_percentage": self.aggregator.get_overall_completion(),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_instrument_readiness(self) -> dict:
        return {
            "instruments": [item.model_dump(mode="json") for item in self.aggregator.get_instrument_status()],
            "xauusd_status": "READY",
            "eurusd_status": "READY",
            "nifty50_status": "ANALYTICS_INTEGRATED",
            "nifty50_readiness_detail": "BROKER_INTEGRATION_DEMO_VALIDATION_VPS_DEPLOYMENT_PENDING",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_system_health(self) -> ExecutiveSystemHealth:
        return ExecutiveSystemHealth(
            deployment_score=self.aggregator.get_deployment_status().score,
            monitoring_score=self.aggregator.get_monitoring_status().score,
            security_score=self.aggregator.get_security_status().score,
            production_score=self.aggregator.get_production_status().score,
        )

    def get_completion_report(self) -> dict:
        return {
            "overall_completion_percentage": self.aggregator.get_overall_completion(),
            "completed": [
                "Analytics Layer",
                "Reporting Layer",
                "Trade Journal",
                "Account Analytics",
                "Strategy Intelligence",
                "Deployment Readiness",
                "Monitoring",
                "Security",
                "NIFTY50 Broker Architecture Foundation",
                "NIFTY50 Strategy Foundation",
                "NIFTY50 Market Data Integration",
                "NIFTY50 SMC Intelligence",
                "NIFTY50 Risk Qualification",
                "NIFTY50 Execution Bridge Preview",
                "NIFTY50 Analytics Integration",
            ],
            "pending": [
                "NIFTY50 Broker Integration",
                "NIFTY50 Demo Validation",
                "NIFTY50 VPS Deployment",
                "Demo Broker Validation",
                "VPS Deployment",
                "Extended Stability Testing",
            ],
            "phase11_complete": True,
            "ready_for_phase12_nifty50": True,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }
