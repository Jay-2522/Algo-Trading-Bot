from typing import Any

from backend.account_routing.allocation_models import AccountRiskProfile, LotAllocation
from backend.account_routing.broker_lot_constraints import BrokerLotConstraints
from backend.account_routing.exposure_validation_engine import ExposureValidationEngine
from backend.account_routing.symbol_risk_rules import SymbolRiskRules
from backend.replay.symbol_normalizer import SymbolNormalizer


class LotAllocationEngine:
    """Calculate simulation-only lot allocations across account risk profiles."""

    def __init__(
        self,
        lot_constraints: BrokerLotConstraints | None = None,
        exposure_validator: ExposureValidationEngine | None = None,
        symbol_rules: SymbolRiskRules | None = None,
        normalizer: SymbolNormalizer | None = None,
    ) -> None:
        self.lot_constraints = lot_constraints or BrokerLotConstraints()
        self.exposure_validator = exposure_validator or ExposureValidationEngine()
        self.symbol_rules = symbol_rules or SymbolRiskRules()
        self.normalizer = normalizer or SymbolNormalizer()

    def allocate(
        self,
        signal: dict[str, Any],
        accounts: list[AccountRiskProfile],
        allocation_mode: str = "EQUAL",
    ) -> list[LotAllocation]:
        mode = str(allocation_mode or signal.get("allocation_mode") or "EQUAL").upper()
        symbol = self.normalizer.normalize(signal.get("canonical_symbol") or signal.get("symbol"))
        action = str(signal.get("action") or "UNKNOWN").upper()
        total_lot = float(signal.get("total_lot") or self._default_total_lot(symbol, mode))
        rules = self.symbol_rules.get_rules(symbol)
        if rules.get("blocked"):
            return [
                self._rejected(profile, symbol, action, mode, rules.get("reason", "Symbol blocked."))
                for profile in accounts
            ]
        total_lot = min(total_lot, float(rules["max_total_lot"]))
        active_accounts = [profile for profile in accounts if profile.enabled and symbol in self._supported_symbols(profile)]
        if not active_accounts:
            return [self._rejected(profile, symbol, action, mode, "No active account supports this symbol.") for profile in accounts]

        lot_parts = self._split_lots(total_lot, active_accounts, mode)
        allocations: list[LotAllocation] = []
        for profile, lot in zip(active_accounts, lot_parts):
            valid_lot, adjusted_lot, lot_warning = self.lot_constraints.validate_lot(profile.broker_id, lot)
            risk_percent = min(float(rules["max_risk"]), profile.max_risk_percent)
            if mode == "CONSERVATIVE":
                risk_percent *= 0.5
            exposure_ok, exposure_issues = self.exposure_validator.validate_exposure(profile, symbol, risk_percent)
            if not valid_lot:
                allocations.append(self._rejected(profile, symbol, action, mode, lot_warning or "Invalid lot."))
            elif not exposure_ok:
                allocations.append(self._rejected(profile, symbol, action, mode, "; ".join(exposure_issues)))
            else:
                status = "REDUCED" if lot_warning or adjusted_lot < lot else "APPROVED"
                allocations.append(
                    LotAllocation(
                        account_id=profile.account_id,
                        broker_id=profile.broker_id,
                        canonical_symbol=symbol,
                        action=action,
                        allocation_mode=mode,
                        allocated_lot=round(adjusted_lot, 2),
                        risk_percent=round(risk_percent, 4),
                        risk_amount=round(profile.balance * risk_percent / 100.0, 2),
                        exposure_percent=round(risk_percent, 4),
                        allocation_status=status,
                        rejection_reason=lot_warning if status == "REDUCED" else None,
                        simulation_only=True,
                        live_execution_enabled=False,
                    )
                )
        inactive_accounts = [profile for profile in accounts if profile not in active_accounts]
        allocations.extend(
            self._rejected(profile, symbol, action, mode, "Account disabled or symbol unsupported.")
            for profile in inactive_accounts
        )
        return allocations

    def _split_lots(self, total_lot: float, accounts: list[AccountRiskProfile], mode: str) -> list[float]:
        if not accounts or mode == "DISABLED":
            return []
        if mode == "FIXED_LOT":
            return [total_lot for _ in accounts]
        if mode == "CONSERVATIVE":
            return [round((total_lot * 0.5) / len(accounts), 4) for _ in accounts]
        if mode == "RISK_WEIGHTED":
            total_equity = sum(account.equity for account in accounts) or 1.0
            return [round(total_lot * (account.equity / total_equity), 4) for account in accounts]
        min_lot = float(self.lot_constraints.DEFAULTS["min"])
        if total_lot < min_lot * len(accounts):
            remaining = round(total_lot, 4)
            lots: list[float] = []
            for _account in accounts:
                if remaining >= min_lot:
                    lots.append(min_lot)
                    remaining = round(remaining - min_lot, 4)
                else:
                    lots.append(0.0)
            return lots
        return [round(total_lot / len(accounts), 4) for _ in accounts]

    def _default_total_lot(self, symbol: str, mode: str) -> float:
        if symbol == "XAUUSD" or mode == "CONSERVATIVE":
            return 0.06
        return 0.03

    def _supported_symbols(self, profile: AccountRiskProfile) -> list[str]:
        if profile.broker_id in {"STARTRADER", "FXPRO", "VANTAGE"}:
            return ["EURUSD", "XAUUSD"]
        return ["NIFTY50"]

    def _rejected(self, profile: AccountRiskProfile, symbol: str, action: str, mode: str, reason: str) -> LotAllocation:
        return LotAllocation(
            account_id=profile.account_id,
            broker_id=profile.broker_id,
            canonical_symbol=symbol,
            action=action,
            allocation_mode=mode,
            allocated_lot=0.0,
            risk_percent=0.0,
            risk_amount=0.0,
            exposure_percent=0.0,
            allocation_status="BLOCKED" if not profile.enabled else "REJECTED",
            rejection_reason=reason,
            simulation_only=True,
            live_execution_enabled=False,
        )
