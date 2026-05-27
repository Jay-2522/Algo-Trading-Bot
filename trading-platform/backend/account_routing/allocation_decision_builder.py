from typing import Any

from backend.account_routing.account_risk_profile import AccountRiskProfileEngine
from backend.account_routing.allocation_models import AllocationDecision
from backend.account_routing.lot_allocation_engine import LotAllocationEngine
from backend.account_routing.risk_distribution_engine import RiskDistributionEngine
from backend.account_routing.symbol_risk_rules import SymbolRiskRules
from backend.replay.symbol_normalizer import SymbolNormalizer


class AllocationDecisionBuilder:
    """Build complete allocation preview decisions."""

    def __init__(
        self,
        risk_profile_engine: AccountRiskProfileEngine | None = None,
        allocation_engine: LotAllocationEngine | None = None,
        distribution_engine: RiskDistributionEngine | None = None,
        symbol_rules: SymbolRiskRules | None = None,
        normalizer: SymbolNormalizer | None = None,
    ) -> None:
        self.risk_profile_engine = risk_profile_engine or AccountRiskProfileEngine()
        self.allocation_engine = allocation_engine or LotAllocationEngine()
        self.distribution_engine = distribution_engine or RiskDistributionEngine()
        self.symbol_rules = symbol_rules or SymbolRiskRules()
        self.normalizer = normalizer or SymbolNormalizer()

    def build_decision(self, signal: dict[str, Any], allocation_mode: str = "EQUAL") -> AllocationDecision:
        mode = str(signal.get("allocation_mode") or allocation_mode or "EQUAL").upper()
        symbol = self.normalizer.normalize(signal.get("canonical_symbol") or signal.get("symbol"))
        action = str(signal.get("action") or "UNKNOWN").upper()
        signal_id = str(signal.get("signal_id") or "allocation-preview")
        profiles = self.risk_profile_engine.get_profiles()
        rules = self.symbol_rules.get_rules(symbol)
        allocations = self.allocation_engine.allocate({**signal, "canonical_symbol": symbol}, profiles, mode)
        total_risk, exposure_summary, distribution_warnings = self.distribution_engine.distribute_risk(
            {"canonical_symbol": symbol},
            allocations,
        )
        approved_allocations = [
            allocation for allocation in allocations if allocation.allocation_status in {"APPROVED", "REDUCED"}
        ]
        rejection_reasons = sorted(
            {
                allocation.rejection_reason
                for allocation in allocations
                if allocation.rejection_reason
            }
        )
        if rules.get("blocked"):
            rejection_reasons.append(str(rules.get("reason", "Symbol allocation blocked.")))
        return AllocationDecision(
            signal_id=signal_id,
            canonical_symbol=symbol,
            action=action,
            allocation_mode=mode,
            allocations=allocations,
            total_allocated_lot=round(sum(allocation.allocated_lot for allocation in approved_allocations), 4),
            total_risk_percent=total_risk,
            exposure_summary=exposure_summary,
            routing_ready=bool(approved_allocations) and not rules.get("blocked", False),
            warnings=distribution_warnings,
            rejection_reasons=rejection_reasons,
            simulation_only=True,
            live_execution_enabled=False,
        )
