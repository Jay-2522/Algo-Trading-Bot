from typing import Any

from backend.account_routing.account_models import AccountRoutingDecision, AccountRoutingPolicy
from backend.account_routing.account_registry import AccountRegistry
from backend.account_routing.routing_policy_engine import RoutingPolicyEngine
from backend.account_routing.signal_account_matcher import SignalAccountMatcher
from backend.replay.symbol_normalizer import SymbolNormalizer


class RoutingDecisionBuilder:
    """Build account routing preview decisions for normalized signals."""

    def __init__(
        self,
        registry: AccountRegistry | None = None,
        matcher: SignalAccountMatcher | None = None,
        policy_engine: RoutingPolicyEngine | None = None,
        normalizer: SymbolNormalizer | None = None,
    ) -> None:
        self.registry = registry or AccountRegistry()
        self.matcher = matcher or SignalAccountMatcher()
        self.policy_engine = policy_engine or RoutingPolicyEngine()
        self.normalizer = normalizer or SymbolNormalizer()

    def build_decision(self, signal: Any, policy: AccountRoutingPolicy | None = None) -> AccountRoutingDecision:
        policy = policy or self.policy_engine.get_default_policy()
        symbol = self.normalizer.normalize(getattr(signal, "canonical_symbol", None) or signal.get("canonical_symbol"))
        action = getattr(signal, "action", None) or signal.get("action", "UNKNOWN")
        signal_id = getattr(signal, "signal_id", None) or signal.get("signal_id", "manual-signal")
        accounts = self.registry.list_accounts()
        matched, rejected = self.matcher.match_signal_to_accounts({"canonical_symbol": symbol}, accounts)
        eligible, rejected, warnings = self.policy_engine.apply_policy(signal, matched, rejected, policy)
        rejection_reasons = sorted({rejected_account.reason for rejected_account in rejected})
        if not eligible:
            rejection_reasons.append("No eligible accounts available for this signal.")
        return AccountRoutingDecision(
            signal_id=str(signal_id),
            canonical_symbol=symbol,
            action=str(action).upper(),
            routing_mode=policy.routing_mode,
            eligible_accounts=eligible,
            rejected_accounts=rejected,
            routing_ready=bool(eligible),
            rejection_reasons=rejection_reasons,
            warnings=warnings,
            simulation_only=True,
            live_execution_enabled=False,
        )
