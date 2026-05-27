from backend.account_routing.account_models import BrokerAccountProfile
from backend.replay.symbol_normalizer import SymbolNormalizer


class AccountRegistry:
    """Static account profile registry for simulation-only routing preview."""

    def __init__(self, normalizer: SymbolNormalizer | None = None) -> None:
        self.normalizer = normalizer or SymbolNormalizer()
        self._accounts = {
            "STARTRADER_DEMO_1": BrokerAccountProfile(
                account_id="STARTRADER_DEMO_1",
                broker_id="STARTRADER",
                display_name="STARTRADER Demo Account 1",
                account_mode="DEMO",
                supported_symbols=["EURUSD", "XAUUSD"],
                account_group="FOREX_CFD_GROUP",
                enabled=True,
                read_only=True,
                demo_ready=True,
                notes="Simulation routing profile for STARTRADER demo observation.",
            ),
            "FXPRO_DEMO_1": BrokerAccountProfile(
                account_id="FXPRO_DEMO_1",
                broker_id="FXPRO",
                display_name="FxPro Demo Account 1",
                account_mode="DEMO",
                supported_symbols=["EURUSD", "XAUUSD"],
                account_group="FOREX_CFD_GROUP",
                enabled=True,
                read_only=True,
                demo_ready=True,
                notes="Simulation routing profile for FxPro demo observation.",
            ),
            "VANTAGE_DEMO_1": BrokerAccountProfile(
                account_id="VANTAGE_DEMO_1",
                broker_id="VANTAGE",
                display_name="Vantage Demo Account 1",
                account_mode="DEMO",
                supported_symbols=["EURUSD", "XAUUSD"],
                account_group="FOREX_CFD_GROUP",
                enabled=True,
                read_only=True,
                demo_ready=True,
                notes="Simulation routing profile for Vantage demo observation.",
            ),
            "ZERODHA_PLACEHOLDER": BrokerAccountProfile(
                account_id="ZERODHA_PLACEHOLDER",
                broker_id="ZERODHA",
                display_name="Zerodha Placeholder",
                account_mode="LIVE_DISABLED",
                supported_symbols=["NIFTY50"],
                account_group="INDIAN_BROKER_GROUP",
                enabled=False,
                read_only=True,
                demo_ready=False,
                notes="Future Indian broker integration placeholder.",
            ),
            "ANGELONE_PLACEHOLDER": BrokerAccountProfile(
                account_id="ANGELONE_PLACEHOLDER",
                broker_id="ANGELONE",
                display_name="AngelOne Placeholder",
                account_mode="LIVE_DISABLED",
                supported_symbols=["NIFTY50"],
                account_group="INDIAN_BROKER_GROUP",
                enabled=False,
                read_only=True,
                demo_ready=False,
                notes="Future Indian broker integration placeholder.",
            ),
            "UPSTOX_PLACEHOLDER": BrokerAccountProfile(
                account_id="UPSTOX_PLACEHOLDER",
                broker_id="UPSTOX",
                display_name="Upstox Placeholder",
                account_mode="LIVE_DISABLED",
                supported_symbols=["NIFTY50"],
                account_group="INDIAN_BROKER_GROUP",
                enabled=False,
                read_only=True,
                demo_ready=False,
                notes="Future Indian broker integration placeholder.",
            ),
        }

    def list_accounts(self) -> list[BrokerAccountProfile]:
        return list(self._accounts.values())

    def get_account(self, account_id: str) -> BrokerAccountProfile | None:
        return self._accounts.get(str(account_id or "").strip().upper())

    def list_enabled_accounts(self) -> list[BrokerAccountProfile]:
        return [account for account in self.list_accounts() if account.enabled]

    def list_accounts_by_broker(self, broker_id: str) -> list[BrokerAccountProfile]:
        broker_key = str(broker_id or "").strip().upper()
        return [account for account in self.list_accounts() if account.broker_id == broker_key]

    def list_accounts_by_symbol(self, symbol: str) -> list[BrokerAccountProfile]:
        canonical = self.normalizer.normalize(symbol)
        return [account for account in self.list_accounts() if canonical in account.supported_symbols]
