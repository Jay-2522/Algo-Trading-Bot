from backend.news_intelligence.news_filter_models import NewsFilterDecision


class NewsBlockReasonBuilder:
    """Build client and technical explanations for news filter decisions."""

    def build_client_message(self, decision: NewsFilterDecision) -> str:
        if decision.trade_action == "BLOCK":
            if decision.risk_level == "EXTREME":
                return "Trading is paused because an extreme-impact USD news event is active or approaching."
            return "Trading is paused because a high-impact USD news event is active or approaching."
        if decision.trade_action == "WAIT_FOR_STABILIZATION":
            return "Trading is paused while the market stabilizes after a major news event."
        if decision.trade_action == "REDUCE_RISK":
            return "Trading confidence is reduced because medium-impact news is approaching."
        return "No relevant news risk is active."

    def build_technical_message(self, decision: NewsFilterDecision) -> str:
        event = (decision.active_events or decision.upcoming_events or [None])[0]
        if event is None:
            return "News filter ALLOW: no relevant event window."
        timing = "active" if decision.active_events else "upcoming"
        return (
            f"News filter {decision.trade_action}: {event.category} {event.currency} event "
            f"{timing}; risk={decision.risk_level}; confidence_cap={decision.confidence_cap}; "
            f"confidence_penalty={decision.confidence_penalty}."
        )
