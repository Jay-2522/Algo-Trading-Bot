from backend.account_routing.allocation_models import LotAllocation


class RiskDistributionEngine:
    """Summarize allocation risk distribution across accounts."""

    def distribute_risk(self, signal: dict, allocations: list[LotAllocation]) -> tuple[float, dict, list[str]]:
        approved = [allocation for allocation in allocations if allocation.allocation_status in {"APPROVED", "REDUCED"}]
        total_risk = round(sum(allocation.risk_percent for allocation in approved), 4)
        total_lot = round(sum(allocation.allocated_lot for allocation in approved), 4)
        warnings: list[str] = []
        if not approved:
            warnings.append("No approved allocations available.")
        if any(allocation.allocation_status == "REDUCED" for allocation in approved):
            warnings.append("One or more allocations were reduced by lot constraints.")
        return total_risk, {
            "approved_accounts": len(approved),
            "total_accounts": len(allocations),
            "total_lot": total_lot,
            "symbol": str(signal.get("canonical_symbol") or signal.get("symbol") or "").upper(),
        }, warnings
