from typing import Any

from backend.news_intelligence.headline_models import HeadlineFilterDecision, HeadlineRiskContext


class HeadlineStrategyFilter:
    """Apply real-time headline context to analysis-only XAUUSD strategy output."""

    def evaluate_xauusd(self, action: str = "WAIT", headline_context: HeadlineRiskContext | dict | None = None) -> HeadlineFilterDecision:
        context = headline_context if isinstance(headline_context, HeadlineRiskContext) else HeadlineRiskContext(**(headline_context or {}))
        normalized_action = (action or "WAIT").upper()
        trade_action = context.headline_trade_action
        blocked = False
        confidence_cap: float | None = None
        confidence_penalty = 0.0
        confidence_adjustment = 0.0
        reason = context.reason

        if trade_action == "BLOCK":
            blocked = True
            confidence_cap = 0.0
            reason = f"Headline risk block active. {context.reason}"
        elif trade_action == "WAIT_FOR_CONFIRMATION":
            confidence_cap = 40.0
            confidence_penalty = 0.0
            reason = f"Waiting for confirmation after high-risk headline. {context.reason}"
        elif trade_action == "REDUCE_RISK":
            confidence_penalty = 15.0
            reason = f"Headline risk reduces confidence. {context.reason}"

        sentiment_adjustment = self._sentiment_adjustment(normalized_action, context.gold_sentiment)
        if sentiment_adjustment < 0:
            confidence_penalty += abs(sentiment_adjustment)
            reason = f"Headline gold sentiment conflicts with {normalized_action}. {reason}"
        elif sentiment_adjustment > 0 and not blocked:
            confidence_adjustment += sentiment_adjustment
            reason = f"Headline gold sentiment aligns with {normalized_action}. {reason}"

        return HeadlineFilterDecision(
            symbol="XAUUSD",
            blocked=blocked,
            action_override="WAIT" if blocked else None,
            confidence_cap=confidence_cap,
            confidence_penalty=confidence_penalty,
            confidence_adjustment=confidence_adjustment,
            risk_level=context.highest_risk_level,
            trade_action=trade_action,
            gold_sentiment=context.gold_sentiment,
            reason=reason,
            client_message=self._client_message(blocked, trade_action, context),
            technical_message=self._technical_message(blocked, trade_action, context, confidence_cap, confidence_penalty, confidence_adjustment),
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _sentiment_adjustment(self, action: str, sentiment: str) -> float:
        if action == "BUY" and sentiment == "BULLISH_GOLD":
            return 5.0
        if action == "SELL" and sentiment == "BEARISH_GOLD":
            return 5.0
        if action == "BUY" and sentiment == "BEARISH_GOLD":
            return -15.0
        if action == "SELL" and sentiment == "BULLISH_GOLD":
            return -15.0
        return 0.0

    def _client_message(self, blocked: bool, trade_action: str, context: HeadlineRiskContext) -> str:
        if blocked:
            return "Trading is paused because an extreme real-time headline risk is active."
        if trade_action == "WAIT_FOR_CONFIRMATION":
            return "Trading confidence is capped while the market digests a high-impact headline."
        if trade_action == "REDUCE_RISK":
            return "Trading confidence is reduced because relevant headline risk is active."
        return "No real-time headline risk is active."

    def _technical_message(
        self,
        blocked: bool,
        trade_action: str,
        context: HeadlineRiskContext,
        confidence_cap: float | None,
        confidence_penalty: float,
        confidence_adjustment: float,
    ) -> str:
        active_title = context.active_headlines[0].title if context.active_headlines else "none"
        return (
            f"Headline filter {trade_action}: blocked={blocked}, risk={context.highest_risk_level}, "
            f"gold_sentiment={context.gold_sentiment}, active_headline={active_title}, "
            f"confidence_cap={confidence_cap}, penalty={confidence_penalty}, adjustment={confidence_adjustment}."
        )
