from backend.account_routing.account_models import AccountRoutingPolicy, BrokerAccountProfile, RejectedAccountReason


class RoutingPolicyEngine:
    """Apply simulation-only routing policy constraints to matched accounts."""

    def get_default_policy(self) -> AccountRoutingPolicy:
        return AccountRoutingPolicy()

    def apply_policy(
        self,
        signal,
        matched_accounts: list[BrokerAccountProfile],
        rejected_accounts: list[RejectedAccountReason],
        policy: AccountRoutingPolicy | None = None,
    ) -> tuple[list[BrokerAccountProfile], list[RejectedAccountReason], list[str]]:
        policy = policy or self.get_default_policy()
        warnings: list[str] = []
        if policy.routing_mode == "DISABLED":
            rejected_accounts.extend(
                RejectedAccountReason(
                    account_id=account.account_id,
                    broker_id=account.broker_id,
                    reason="Routing policy is disabled.",
                )
                for account in matched_accounts
            )
            return [], rejected_accounts, warnings

        filtered: list[BrokerAccountProfile] = []
        for account in matched_accounts:
            reason = self._policy_rejection_reason(account, policy)
            if reason:
                rejected_accounts.append(
                    RejectedAccountReason(
                        account_id=account.account_id,
                        broker_id=account.broker_id,
                        reason=reason,
                    )
                )
            else:
                filtered.append(account)

        if policy.routing_mode == "PRIMARY_ONLY" and filtered:
            filtered = filtered[:1]
        elif policy.routing_mode in {"BROKER_SPECIFIC", "SYMBOL_SPECIFIC", "COPY_TO_ALL"}:
            filtered = filtered[: max(0, policy.max_accounts_per_signal)]

        if len(matched_accounts) > len(filtered):
            warnings.append("Routing policy reduced eligible account count.")
        return filtered, rejected_accounts, warnings

    def _policy_rejection_reason(self, account: BrokerAccountProfile, policy: AccountRoutingPolicy) -> str | None:
        if account.broker_id not in policy.enabled_brokers:
            return "Broker is not enabled by routing policy."
        if policy.require_demo_ready and not account.demo_ready:
            return "Account is not demo-ready."
        if policy.require_read_only_verified and not account.read_only:
            return "Account is not read-only verified."
        if policy.live_execution_enabled or account.live_execution_enabled:
            return "Live execution is disabled for all routing previews."
        return None
