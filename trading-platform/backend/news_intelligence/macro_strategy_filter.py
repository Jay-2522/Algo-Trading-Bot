from backend.news_intelligence.macro_models import XAUUSDMacroBiasContext


class MacroStrategyFilter:
    """Evaluate XAUUSD action alignment with DXY and US10Y macro bias."""

    def evaluate_xauusd(self, action: str, macro_context: XAUUSDMacroBiasContext) -> XAUUSDMacroBiasContext:
        normalized_action = action.upper()
        if macro_context.gold_bias == "BULLISH" and normalized_action == "BUY":
            return self._updated(macro_context, "ALIGNED", 10.0, "Macro supports BUY because gold bias is bullish.")
        if macro_context.gold_bias == "BEARISH" and normalized_action == "SELL":
            return self._updated(macro_context, "ALIGNED", 10.0, "Macro supports SELL because gold bias is bearish.")
        if macro_context.gold_bias == "BEARISH" and normalized_action == "BUY":
            return self._updated(macro_context, "CONFLICTING", -20.0, "Macro conflicts with BUY because gold bias is bearish.")
        if macro_context.gold_bias == "BULLISH" and normalized_action == "SELL":
            return self._updated(macro_context, "CONFLICTING", -20.0, "Macro conflicts with SELL because gold bias is bullish.")
        if macro_context.gold_bias == "MIXED":
            return self._updated(macro_context, "NEUTRAL", -10.0, "Macro is mixed; confidence is reduced.")
        return self._updated(macro_context, "UNKNOWN", 0.0, "Macro alignment is unknown.")

    def _updated(
        self,
        context: XAUUSDMacroBiasContext,
        alignment: str,
        adjustment: float,
        reason: str,
    ) -> XAUUSDMacroBiasContext:
        context.macro_alignment = alignment
        context.confidence_adjustment = adjustment
        context.reason = f"{context.reason} {reason}"
        if alignment == "CONFLICTING":
            context.macro_risk_level = "HIGH"
        elif alignment == "NEUTRAL":
            context.macro_risk_level = "MEDIUM"
        elif alignment == "ALIGNED":
            context.macro_risk_level = "LOW"
        return context
