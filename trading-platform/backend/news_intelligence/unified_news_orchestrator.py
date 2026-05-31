from typing import Any

from backend.news_intelligence.unified_news_models import UnifiedNewsRiskDecision


class UnifiedNewsOrchestrator:
    """Combine calendar, event-filter, macro, and headline risk into one XAUUSD decision."""

    RISK_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "EXTREME": 3}

    def evaluate_xauusd(
        self,
        calendar_context: Any | None = None,
        news_filter_decision: Any | None = None,
        macro_context: Any | None = None,
        headline_context: Any | None = None,
    ) -> UnifiedNewsRiskDecision:
        calendar_risk = self._risk(self._get(calendar_context, "risk_level", "LOW"))
        headline_risk = self._risk(self._get(headline_context, "highest_risk_level", "LOW"))
        macro_risk = self._risk(self._get(macro_context, "macro_risk_level", "LOW"))
        final_action = "ALLOW"
        confidence_adjustment = 0.0
        confidence_cap: float | None = None
        blocking: list[str] = []
        supportive: list[str] = []

        news_action = self._get(news_filter_decision, "trade_action", self._get(calendar_context, "trade_action", "ALLOW"))
        headline_action = self._get(headline_context, "headline_trade_action", "ALLOW")
        macro_alignment = self._get(macro_context, "macro_alignment", "UNKNOWN")

        if calendar_risk == "EXTREME" or headline_risk == "EXTREME":
            final_action = "BLOCK"
            confidence_cap = 0.0
            blocking.append("Extreme calendar or headline risk is active.")
        if calendar_risk == "HIGH" and (self._get(calendar_context, "high_impact_event_active", False) or news_action == "BLOCK"):
            final_action = "BLOCK"
            confidence_cap = 20.0 if confidence_cap is None else min(confidence_cap, 20.0)
            blocking.append("High-impact calendar risk is active.")
        if self._get(news_filter_decision, "blocked", False):
            final_action = "BLOCK"
            cap = self._get(news_filter_decision, "confidence_cap", 20.0)
            confidence_cap = float(cap if cap is not None else 20.0) if confidence_cap is None else min(confidence_cap, float(cap if cap is not None else 20.0))
            blocking.append(self._get(news_filter_decision, "reason", "News filter is blocking analysis."))
        if headline_action == "BLOCK":
            final_action = "BLOCK"
            confidence_cap = 0.0
            blocking.append("Headline filter is blocking analysis.")

        stabilization = news_action == "WAIT_FOR_STABILIZATION"
        if final_action != "BLOCK" and stabilization:
            final_action = "WAIT_FOR_STABILIZATION"
            confidence_cap = 30.0
            blocking.append("Post-news stabilization window is active.")

        if macro_alignment == "CONFLICTING":
            confidence_adjustment -= 20.0
            blocking.append("DXY/US10Y macro context conflicts with the current XAUUSD candidate.")
            if final_action == "ALLOW":
                final_action = "REDUCE_RISK"
        elif macro_alignment == "ALIGNED":
            confidence_adjustment += 5.0
            supportive.append("DXY/US10Y macro context supports the current XAUUSD candidate.")

        if headline_risk == "HIGH" and final_action != "BLOCK":
            confidence_adjustment -= 15.0
            blocking.append("High real-time headline risk reduces confidence.")
            if final_action == "ALLOW":
                final_action = "REDUCE_RISK"

        if calendar_risk == "MEDIUM" and final_action not in {"BLOCK", "WAIT_FOR_STABILIZATION"}:
            confidence_adjustment -= 10.0
            blocking.append("Medium calendar risk reduces confidence.")
            if final_action == "ALLOW":
                final_action = "REDUCE_RISK"

        if self._get(news_filter_decision, "trade_action", "ALLOW") == "REDUCE_RISK" and final_action == "ALLOW":
            confidence_adjustment -= float(self._get(news_filter_decision, "confidence_penalty", 10.0) or 10.0)
            blocking.append("News filter requests reduced risk.")
            final_action = "REDUCE_RISK"

        final_risk = self._highest_risk(calendar_risk, headline_risk, macro_risk, "MEDIUM" if final_action == "REDUCE_RISK" else "LOW")
        if final_action == "BLOCK" and final_risk == "LOW":
            final_risk = "HIGH"
        if final_action == "WAIT_FOR_STABILIZATION":
            final_risk = self._highest_risk(final_risk, "HIGH")

        if final_action == "ALLOW" and not supportive:
            supportive.append("Calendar, macro, and headline contexts are clear.")

        return UnifiedNewsRiskDecision(
            symbol="XAUUSD",
            calendar_risk_level=calendar_risk,
            headline_risk_level=headline_risk,
            macro_risk_level=macro_risk,
            final_risk_level=final_risk,
            final_trade_action=final_action,
            confidence_adjustment=confidence_adjustment,
            confidence_cap=confidence_cap,
            blocking_reasons=blocking,
            supportive_reasons=supportive,
            client_summary=self._client_summary(final_action, blocking, supportive),
            technical_summary=self._technical_summary(calendar_risk, headline_risk, macro_risk, final_action, confidence_adjustment, confidence_cap),
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _client_summary(self, action: str, blocking: list[str], supportive: list[str]) -> str:
        if action == "BLOCK":
            return "Trading analysis is paused because unified news risk is blocking the setup."
        if action == "WAIT_FOR_STABILIZATION":
            return "The bot is waiting for post-news market stabilization before trusting XAUUSD signals."
        if action == "REDUCE_RISK":
            return "The bot reduced confidence because one or more news, macro, or headline risks are not ideal."
        return supportive[0] if supportive else "No unified news, macro, or headline risk is blocking XAUUSD analysis."

    def _technical_summary(
        self,
        calendar_risk: str,
        headline_risk: str,
        macro_risk: str,
        action: str,
        adjustment: float,
        cap: float | None,
    ) -> str:
        return (
            f"Unified news risk {action}: calendar={calendar_risk}, headline={headline_risk}, "
            f"macro={macro_risk}, adjustment={adjustment}, confidence_cap={cap}."
        )

    def _risk(self, risk: Any) -> str:
        normalized = str(risk or "LOW").upper()
        return normalized if normalized in self.RISK_RANK else "LOW"

    def _highest_risk(self, *risks: str) -> str:
        return max((self._risk(risk) for risk in risks), key=lambda risk: self.RISK_RANK[risk])

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
