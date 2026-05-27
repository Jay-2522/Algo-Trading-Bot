from typing import Any

from backend.account_routing.account_models import BrokerAccountProfile, RejectedAccountReason
from backend.replay.symbol_normalizer import SymbolNormalizer


class SignalAccountMatcher:
    """Match normalized signals to eligible account profiles without execution."""

    def __init__(self, normalizer: SymbolNormalizer | None = None) -> None:
        self.normalizer = normalizer or SymbolNormalizer()

    def match_signal_to_accounts(
        self,
        signal: Any,
        accounts: list[BrokerAccountProfile],
    ) -> tuple[list[BrokerAccountProfile], list[RejectedAccountReason]]:
        symbol = self.normalizer.normalize(getattr(signal, "canonical_symbol", None) or signal.get("canonical_symbol"))
        eligible: list[BrokerAccountProfile] = []
        rejected: list[RejectedAccountReason] = []

        for account in accounts:
            reason = self._rejection_reason(symbol, account)
            if reason:
                rejected.append(
                    RejectedAccountReason(
                        account_id=account.account_id,
                        broker_id=account.broker_id,
                        reason=reason,
                    )
                )
            else:
                eligible.append(account)
        return eligible, rejected

    def _rejection_reason(self, symbol: str, account: BrokerAccountProfile) -> str | None:
        if account.live_execution_enabled:
            return "Live execution is not allowed for routing preview."
        if not account.enabled:
            return "Account is disabled."
        if symbol not in account.supported_symbols:
            return f"{symbol} is not supported by this account."
        if symbol == "NIFTY50":
            return "NIFTY50 Indian broker routing is placeholder-only until integration is complete."
        return None
