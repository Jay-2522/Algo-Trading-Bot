from backend.news_intelligence.macro_models import MacroInstrumentContext, XAUUSDMacroBiasContext


class MacroBiasEngine:
    """Build manual DXY/US10Y macro context and infer gold bias."""

    def build_instrument_context(
        self,
        symbol: str,
        current_value: float | None,
        previous_value: float | None,
    ) -> MacroInstrumentContext:
        if current_value is None or previous_value is None or previous_value == 0:
            return MacroInstrumentContext(symbol=symbol.upper())
        change = round(float(current_value) - float(previous_value), 5)
        change_percent = round((change / abs(float(previous_value))) * 100, 5)
        direction = "UNKNOWN"
        if change > 0:
            direction = "UP"
        elif change < 0:
            direction = "DOWN"
        else:
            direction = "FLAT"

        abs_change_percent = abs(change_percent)
        if abs_change_percent >= 0.5:
            momentum = "STRONG"
        elif abs_change_percent >= 0.2:
            momentum = "MODERATE"
        else:
            momentum = "WEAK"

        confidence = 80.0 if direction in {"UP", "DOWN"} else 50.0 if direction == "FLAT" else 0.0
        if momentum == "STRONG":
            confidence = min(confidence + 15.0, 100.0)
        elif momentum == "MODERATE":
            confidence = min(confidence + 5.0, 100.0)

        return MacroInstrumentContext(
            symbol=symbol.upper(),
            current_value=float(current_value),
            previous_value=float(previous_value),
            change=change,
            change_percent=change_percent,
            direction=direction,
            momentum=momentum,
            confidence=confidence,
        )

    def build_xauusd_macro_bias(
        self,
        dxy_context: MacroInstrumentContext | None = None,
        us10y_context: MacroInstrumentContext | None = None,
    ) -> XAUUSDMacroBiasContext:
        if dxy_context is None or us10y_context is None:
            return XAUUSDMacroBiasContext(
                dxy_context=dxy_context,
                us10y_context=us10y_context,
                gold_bias="UNKNOWN",
                macro_alignment="UNKNOWN",
                macro_risk_level="MEDIUM",
                reason="DXY or US10Y context is missing.",
            )
        dxy = dxy_context.direction
        us10y = us10y_context.direction
        if dxy == "DOWN" and us10y == "DOWN":
            bias = "BULLISH"
            risk = "LOW"
            reason = "Macro bias is bullish for gold because DXY and US10Y are both declining."
        elif dxy == "UP" and us10y == "UP":
            bias = "BEARISH"
            risk = "LOW"
            reason = "Macro bias is bearish for gold because DXY and US10Y are both rising."
        elif dxy in {"UP", "DOWN"} and us10y in {"UP", "DOWN"}:
            bias = "MIXED"
            risk = "MEDIUM"
            reason = "Macro bias is mixed because DXY and US10Y are moving in opposite directions."
        elif dxy == "FLAT" and us10y == "FLAT":
            bias = "MIXED"
            risk = "MEDIUM"
            reason = "Macro bias is mixed because DXY and US10Y are flat."
        else:
            bias = "UNKNOWN"
            risk = "HIGH"
            reason = "Macro bias is unknown because DXY or US10Y direction is unavailable."
        return XAUUSDMacroBiasContext(
            dxy_context=dxy_context,
            us10y_context=us10y_context,
            gold_bias=bias,
            macro_alignment="UNKNOWN",
            macro_risk_level=risk,
            reason=reason,
        )
