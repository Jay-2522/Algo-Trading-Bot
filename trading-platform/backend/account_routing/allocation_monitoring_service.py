from typing import Any

from backend.account_routing.account_balance_snapshot import AccountBalanceSnapshotEngine
from backend.account_routing.account_risk_profile import AccountRiskProfileEngine
from backend.account_routing.allocation_decision_builder import AllocationDecisionBuilder
from backend.account_routing.allocation_models import AccountBalanceSnapshot, AccountRiskProfile, AllocationDecision
from backend.account_routing.symbol_risk_rules import SymbolRiskRules


class AllocationMonitoringService:
    """Service facade for allocation previews and account-level risk monitoring."""

    def __init__(
        self,
        risk_profile_engine: AccountRiskProfileEngine | None = None,
        balance_snapshot_engine: AccountBalanceSnapshotEngine | None = None,
        decision_builder: AllocationDecisionBuilder | None = None,
        symbol_rules: SymbolRiskRules | None = None,
    ) -> None:
        self.risk_profile_engine = risk_profile_engine or AccountRiskProfileEngine()
        self.balance_snapshot_engine = balance_snapshot_engine or AccountBalanceSnapshotEngine(self.risk_profile_engine)
        self.decision_builder = decision_builder or AllocationDecisionBuilder(self.risk_profile_engine)
        self.symbol_rules = symbol_rules or SymbolRiskRules()

    def get_status(self) -> dict[str, Any]:
        profiles = self.risk_profile_engine.get_profiles()
        return {
            "status": "operational",
            "mode": "ACCOUNT_ALLOCATION_PREVIEW_ONLY",
            "profiles": len(profiles),
            "enabled_profiles": len([profile for profile in profiles if profile.enabled]),
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def get_profiles(self) -> list[AccountRiskProfile]:
        return self.risk_profile_engine.get_profiles()

    def get_snapshots(self) -> list[AccountBalanceSnapshot]:
        return self.balance_snapshot_engine.get_all_snapshots()

    def preview_allocation(self, signal: dict[str, Any]) -> AllocationDecision:
        return self.decision_builder.build_decision(signal, signal.get("allocation_mode", "EQUAL"))

    def get_symbol_rules(self, symbol: str) -> dict:
        return self.symbol_rules.get_rules(symbol)
