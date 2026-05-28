from typing import Any

from backend.account_routing.symbol_risk_rules import SymbolRiskRules
from backend.portfolio.portfolio_models import PortfolioAccountSummary, PortfolioExposureSummary


class ExposureSummaryService:
    """Summarize simulated portfolio and symbol-level exposure readiness."""

    SYMBOLS = ["EURUSD", "XAUUSD", "NIFTY50"]

    def __init__(self, symbol_rules: SymbolRiskRules | None = None) -> None:
        self.symbol_rules = symbol_rules or SymbolRiskRules()

    def build_exposure(self, accounts: list[PortfolioAccountSummary]) -> PortfolioExposureSummary:
        enabled_accounts = [account for account in accounts if account.enabled]
        supported_symbols = sorted({symbol for account in enabled_accounts for symbol in account.supported_symbols})
        exposure_by_symbol: dict[str, Any] = {}
        blocked_symbols: list[str] = []

        for symbol in self.SYMBOLS:
            rules = self.symbol_rules.get_rules(symbol)
            supporting_accounts = [
                account.account_id for account in enabled_accounts if symbol in account.supported_symbols
            ]
            blocked = bool(rules.get("blocked")) or not supporting_accounts
            if blocked:
                blocked_symbols.append(symbol)
            exposure_by_symbol[symbol] = {
                "status": "BLOCKED_CONDITIONAL" if blocked else "READY",
                "supporting_accounts": supporting_accounts,
                "max_total_lot": rules.get("max_total_lot", 0.0),
                "max_risk": rules.get("max_risk", 0.0),
                "reason": rules.get("reason") if blocked else "Simulated exposure checks available.",
                "simulation_only": True,
                "live_execution_enabled": False,
            }

        total_balance = round(sum(account.balance for account in accounts), 2)
        total_equity = round(sum(account.equity for account in accounts), 2)
        return PortfolioExposureSummary(
            total_accounts=len(accounts),
            enabled_accounts=len(enabled_accounts),
            supported_symbols=supported_symbols,
            blocked_symbols=blocked_symbols,
            total_simulated_balance=total_balance,
            total_simulated_equity=total_equity,
            exposure_by_symbol=exposure_by_symbol,
            risk_summary={
                "portfolio_risk_status": "SIMULATION_READY",
                "account_level_limits": "Configured for demo previews.",
                "nifty50_status": "Blocked until Indian broker integration is implemented.",
                "live_execution_enabled": False,
            },
            simulation_only=True,
            live_execution_enabled=False,
        )
