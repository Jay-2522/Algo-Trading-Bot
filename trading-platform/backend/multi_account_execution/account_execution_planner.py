from typing import Any

from backend.account_routing.account_registry import AccountRegistry
from backend.multi_account_execution.multi_account_models import AccountDemoExecutionPlan
from backend.replay.symbol_normalizer import SymbolNormalizer


class AccountExecutionPlanner:
    """Create per-account MT5 demo execution plans for Phase 5 routing."""

    TARGET_ACCOUNT_IDS = ["STARTRADER_DEMO_1", "FXPRO_DEMO_1", "VANTAGE_DEMO_1"]
    MAX_LOT = 0.01

    def __init__(
        self,
        account_registry: AccountRegistry | None = None,
        normalizer: SymbolNormalizer | None = None,
    ) -> None:
        self.account_registry = account_registry or AccountRegistry()
        self.normalizer = normalizer or SymbolNormalizer()

    def build_plans(self, signal_payload: dict[str, Any]) -> list[AccountDemoExecutionPlan]:
        symbol = self.normalizer.normalize(signal_payload.get("canonical_symbol") or signal_payload.get("symbol"))
        action = str(signal_payload.get("action") or "").upper()
        signal_id = str(signal_payload.get("signal_id") or "multi-account-demo")
        requested_total_lot = float(signal_payload.get("total_lot") or self.MAX_LOT)
        per_account_lot = min(self.MAX_LOT, max(0.0, requested_total_lot / max(1, len(self.TARGET_ACCOUNT_IDS))))
        if requested_total_lot <= self.MAX_LOT:
            per_account_lot = min(self.MAX_LOT, requested_total_lot)
        per_account_lot = round(per_account_lot, 2)

        plans: list[AccountDemoExecutionPlan] = []
        for account_id in self.TARGET_ACCOUNT_IDS:
            account = self.account_registry.get_account(account_id)
            broker_id = account.broker_id if account is not None else account_id.replace("_DEMO_1", "")
            reasons = self._plan_rejections(symbol, action, per_account_lot, account)
            plans.append(
                AccountDemoExecutionPlan(
                    signal_id=signal_id,
                    account_id=account_id,
                    broker_id=broker_id,
                    canonical_symbol=symbol,
                    broker_symbol=symbol,
                    action=action,
                    lot=per_account_lot,
                    order_type=str(signal_payload.get("order_type") or "MARKET").upper(),
                    eligible=not reasons,
                    rejection_reasons=reasons,
                    simulation_only=True,
                    demo_execution=True,
                    live_execution_enabled=False,
                )
            )
        return plans

    def _plan_rejections(self, symbol: str, action: str, lot: float, account: Any) -> list[str]:
        reasons: list[str] = []
        if account is None:
            reasons.append("Target demo account profile is unavailable.")
        elif not account.enabled or not account.demo_ready:
            reasons.append("Target account is not enabled for demo routing.")
        if symbol != "EURUSD":
            reasons.append("Phase 5 Day 3 multi-account demo routing allows EURUSD only.")
        if action not in {"BUY", "SELL"}:
            reasons.append("Phase 5 Day 3 multi-account demo routing allows BUY/SELL only.")
        if lot <= 0:
            reasons.append("Per-account demo lot must be greater than zero.")
        if lot > self.MAX_LOT:
            reasons.append("Per-account demo lot must be <= 0.01.")
        return reasons
