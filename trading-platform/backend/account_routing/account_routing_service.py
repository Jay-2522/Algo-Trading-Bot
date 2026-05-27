from typing import Any

from backend.account_routing.account_group_manager import AccountGroupManager
from backend.account_routing.account_models import AccountRoutingDecision, AccountRoutingPolicy, BrokerAccountProfile
from backend.account_routing.account_registry import AccountRegistry
from backend.account_routing.allocation_models import AccountBalanceSnapshot, AccountRiskProfile, AllocationDecision
from backend.account_routing.allocation_monitoring_service import AllocationMonitoringService
from backend.account_routing.routing_decision_builder import RoutingDecisionBuilder
from backend.account_routing.routing_policy_engine import RoutingPolicyEngine


class AccountRoutingService:
    """Service facade for multi-account routing preview."""

    def __init__(
        self,
        registry: AccountRegistry | None = None,
        group_manager: AccountGroupManager | None = None,
        policy_engine: RoutingPolicyEngine | None = None,
        decision_builder: RoutingDecisionBuilder | None = None,
        allocation_service: AllocationMonitoringService | None = None,
    ) -> None:
        self.registry = registry or AccountRegistry()
        self.group_manager = group_manager or AccountGroupManager(self.registry)
        self.policy_engine = policy_engine or RoutingPolicyEngine()
        self.decision_builder = decision_builder or RoutingDecisionBuilder(self.registry, policy_engine=self.policy_engine)
        self.allocation_service = allocation_service or AllocationMonitoringService()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "operational",
            "mode": "MULTI_ACCOUNT_ROUTING_PREVIEW_ONLY",
            "accounts": len(self.registry.list_accounts()),
            "enabled_accounts": len(self.registry.list_enabled_accounts()),
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def list_accounts(self) -> list[BrokerAccountProfile]:
        return self.registry.list_accounts()

    def get_account(self, account_id: str) -> BrokerAccountProfile | None:
        return self.registry.get_account(account_id)

    def preview_route(self, signal_payload: dict[str, Any]) -> AccountRoutingDecision:
        return self.decision_builder.build_decision(signal_payload)

    def list_groups(self) -> dict[str, list[BrokerAccountProfile]]:
        return self.group_manager.list_groups()

    def get_default_policy(self) -> AccountRoutingPolicy:
        return self.policy_engine.get_default_policy()

    def get_allocation_status(self) -> dict[str, Any]:
        return self.allocation_service.get_status()

    def get_risk_profiles(self) -> list[AccountRiskProfile]:
        return self.allocation_service.get_profiles()

    def get_balance_snapshots(self) -> list[AccountBalanceSnapshot]:
        return self.allocation_service.get_snapshots()

    def get_symbol_rules(self, symbol: str) -> dict:
        return self.allocation_service.get_symbol_rules(symbol)

    def preview_allocation(self, signal_payload: dict[str, Any]) -> AllocationDecision:
        return self.allocation_service.preview_allocation(signal_payload)
