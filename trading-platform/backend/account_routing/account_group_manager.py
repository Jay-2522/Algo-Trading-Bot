from backend.account_routing.account_models import BrokerAccountProfile
from backend.account_routing.account_registry import AccountRegistry


class AccountGroupManager:
    """Manage static account groups used by routing preview policies."""

    GROUPS = {
        "FOREX_CFD_GROUP": ["STARTRADER_DEMO_1", "FXPRO_DEMO_1", "VANTAGE_DEMO_1"],
        "INDIAN_BROKER_GROUP": ["ZERODHA_PLACEHOLDER", "ANGELONE_PLACEHOLDER", "UPSTOX_PLACEHOLDER"],
    }

    def __init__(self, registry: AccountRegistry | None = None) -> None:
        self.registry = registry or AccountRegistry()

    def get_group(self, group_name: str) -> list[BrokerAccountProfile]:
        account_ids = self.GROUPS.get(str(group_name or "").strip().upper(), [])
        return [account for account_id in account_ids if (account := self.registry.get_account(account_id)) is not None]

    def list_groups(self) -> dict[str, list[BrokerAccountProfile]]:
        return {group_name: self.get_group(group_name) for group_name in self.GROUPS}
