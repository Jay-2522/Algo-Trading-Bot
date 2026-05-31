from backend.news_intelligence.headline_models import HeadlineEvent, HeadlineRiskContext


class HeadlineRiskEngine:
    """Evaluate headline risk and aggregate recent headline context for XAUUSD."""

    RISK_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "EXTREME": 3}

    def evaluate(self, headline: HeadlineEvent) -> HeadlineEvent:
        text = f"{headline.title} {headline.body}".upper()
        categories = set(headline.categories)

        if (
            ("FOMC" in categories and self._has_any(text, ["SURPRISE", "SHOCK", "UNEXPECTED"]))
            or ("POWELL" in text and self._has_any(text, ["SHOCK", "EMERGENCY", "SURPRISE"]))
            or ("WAR" in categories and self._has_any(text, ["ESCALATION", "INVASION", "MISSILE"]))
            or self._has_any(text, ["EMERGENCY FED", "EMERGENCY RATE"])
        ):
            headline.risk_level = "EXTREME"
            headline.impact = "EXTREME"
        elif (
            {"CPI", "NFP", "FED", "FOMC"} & categories
            or self._has_any(text, ["YIELD SPIKE", "YIELDS RISING", "DXY SPIKE", "DOLLAR SPIKE"])
            or headline.risk_level == "HIGH"
        ):
            headline.risk_level = "HIGH"
            headline.impact = "HIGH"
        elif {"USD", "DXY", "YIELDS", "INFLATION"} & categories or "FED" in text:
            headline.risk_level = "MEDIUM"
            headline.impact = "MEDIUM"
        else:
            headline.risk_level = "LOW"
            headline.impact = "LOW"

        if headline.risk_level == "LOW":
            headline.active = False
        return headline

    def build_context(self, headlines: list[HeadlineEvent]) -> HeadlineRiskContext:
        recent = list(headlines)
        active = [headline for headline in recent if headline.active and headline.risk_level != "LOW"]
        highest = "LOW"
        for headline in active or recent:
            if self.RISK_RANK.get(headline.risk_level, 0) > self.RISK_RANK[highest]:
                highest = headline.risk_level

        gold_sentiment = self._dominant_gold_sentiment(active or recent)
        trade_action = self._trade_action(highest)
        confidence_adjustment = self._confidence_adjustment(trade_action)
        reason = self._reason(highest, trade_action, active)
        return HeadlineRiskContext(
            active_headlines=active,
            recent_headlines=recent,
            highest_risk_level=highest,
            gold_sentiment=gold_sentiment,
            usd_sentiment="RISK_ACTIVE" if any(headline.usd_relevance for headline in active) else "UNKNOWN",
            headline_trade_action=trade_action,
            confidence_adjustment=confidence_adjustment,
            reason=reason,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _dominant_gold_sentiment(self, headlines: list[HeadlineEvent]) -> str:
        sentiments = [headline.sentiment for headline in headlines if headline.gold_relevance]
        if not sentiments:
            return "UNKNOWN"
        if "BULLISH_GOLD" in sentiments and "BEARISH_GOLD" in sentiments:
            return "MIXED"
        if "BULLISH_GOLD" in sentiments:
            return "BULLISH_GOLD"
        if "BEARISH_GOLD" in sentiments:
            return "BEARISH_GOLD"
        if "MIXED" in sentiments:
            return "MIXED"
        return "NEUTRAL"

    def _trade_action(self, risk_level: str) -> str:
        if risk_level == "EXTREME":
            return "BLOCK"
        if risk_level == "HIGH":
            return "WAIT_FOR_CONFIRMATION"
        if risk_level == "MEDIUM":
            return "REDUCE_RISK"
        return "ALLOW"

    def _confidence_adjustment(self, trade_action: str) -> float:
        if trade_action == "BLOCK":
            return -100.0
        if trade_action == "WAIT_FOR_CONFIRMATION":
            return -25.0
        if trade_action == "REDUCE_RISK":
            return -15.0
        return 0.0

    def _reason(self, risk_level: str, trade_action: str, active: list[HeadlineEvent]) -> str:
        if not active:
            return "No active gold-relevant real-time headline risk."
        first = active[0]
        return f"{risk_level} headline risk from {first.source}: {first.title}. Action={trade_action}."

    def _has_any(self, text: str, tokens: list[str]) -> bool:
        return any(token in text for token in tokens)
