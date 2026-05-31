class HeadlineClassifier:
    """Classify manually ingested real-time headline text for XAUUSD relevance."""

    SUPPORTED_CATEGORIES = [
        "FED",
        "INFLATION",
        "CPI",
        "NFP",
        "FOMC",
        "GEOPOLITICAL",
        "WAR",
        "DXY",
        "YIELDS",
        "GOLD",
        "USD",
        "RISK_OFF",
        "RISK_ON",
        "OTHER",
    ]

    def classify(self, headline_text: str | None) -> dict:
        text = (headline_text or "").upper()
        categories: set[str] = set()
        symbols: set[str] = set()
        currencies: set[str] = set()
        sentiment = "UNKNOWN"
        impact = "LOW"
        risk_level = "LOW"

        def has_any(tokens: list[str]) -> bool:
            return any(token in text for token in tokens)

        if has_any(["FED", "POWELL", "FOMC", "RATE DECISION", "CENTRAL BANK"]):
            categories.add("FED")
            currencies.add("USD")
            impact = "MEDIUM"
            risk_level = "MEDIUM"
        if has_any(["INFLATION", "CPI", "PCE", "PRICE PRESSURE"]):
            categories.add("INFLATION")
            currencies.add("USD")
        if "CPI" in text:
            categories.add("CPI")
        if has_any(["NON-FARM", "NONFARM", "NFP", "PAYROLL"]):
            categories.add("NFP")
            currencies.add("USD")
        if "FOMC" in text or "RATE DECISION" in text:
            categories.add("FOMC")
            currencies.add("USD")
        if has_any(["WAR", "MISSILE", "INVASION", "ESCALATION", "GEOPOLITICAL"]):
            categories.update({"GEOPOLITICAL", "WAR"})
        if has_any(["DXY", "DOLLAR INDEX", "US DOLLAR"]):
            categories.add("DXY")
            symbols.add("DXY")
            currencies.add("USD")
        if has_any(["YIELD", "US10Y", "10-YEAR", "TREASURY"]):
            categories.add("YIELDS")
            symbols.add("US10Y")
            currencies.add("USD")
        if has_any(["GOLD", "XAU", "XAUUSD"]):
            categories.add("GOLD")
            symbols.add("XAUUSD")
        if has_any(["USD", "DOLLAR"]):
            categories.add("USD")
            currencies.add("USD")
        if has_any(["RISK OFF", "SAFE HAVEN", "FLIGHT TO SAFETY"]):
            categories.add("RISK_OFF")
        if has_any(["RISK ON", "RISK APPETITE"]):
            categories.add("RISK_ON")

        hawkish = has_any(["HAWKISH", "TOO HIGH", "HOT", "STICKY", "HIGHER FOR LONGER", "RATE HIKE", "YIELDS RISING", "YIELD SPIKE", "DXY SPIKE"])
        dovish = has_any(["DOVISH", "COOLING", "CUT", "RATE CUT", "EASING", "YIELDS FALLING", "YIELD FALL", "DXY FALL", "INFLATION SLOWS"])
        surprise = has_any(["SURPRISE", "SHOCK", "UNEXPECTED", "EMERGENCY"])
        geopolitical = bool({"GEOPOLITICAL", "WAR"} & categories)

        if hawkish:
            sentiment = "BEARISH_GOLD"
            impact = "HIGH"
            risk_level = "HIGH"
        if dovish:
            sentiment = "BULLISH_GOLD" if sentiment == "UNKNOWN" else "MIXED"
            impact = "HIGH"
            risk_level = "HIGH"
        if geopolitical:
            sentiment = "BULLISH_GOLD"
            impact = "HIGH"
            risk_level = "EXTREME" if has_any(["ESCALATION", "INVASION", "MISSILE", "EMERGENCY"]) else "HIGH"
        if surprise and ({"FOMC", "CPI", "NFP"} & categories or "POWELL" in text):
            impact = "EXTREME"
            risk_level = "EXTREME"
        elif {"CPI", "NFP", "FOMC"} & categories and (hawkish or dovish):
            impact = "HIGH"
            risk_level = "HIGH"

        if not categories:
            categories.add("OTHER")
        if sentiment == "UNKNOWN" and ({"USD", "DXY", "YIELDS", "FED", "INFLATION"} & categories):
            sentiment = "MIXED"
        if sentiment == "UNKNOWN":
            sentiment = "NEUTRAL"

        gold_relevance = bool({"FED", "INFLATION", "CPI", "NFP", "FOMC", "GEOPOLITICAL", "WAR", "DXY", "YIELDS", "GOLD", "USD", "RISK_OFF"} & categories)
        usd_relevance = "USD" in currencies or bool({"FED", "INFLATION", "CPI", "NFP", "FOMC", "DXY", "YIELDS", "USD"} & categories)

        return {
            "categories": sorted(categories),
            "symbols": sorted(symbols),
            "currencies": sorted(currencies),
            "impact": impact,
            "sentiment": sentiment,
            "risk_level": risk_level,
            "gold_relevance": gold_relevance,
            "usd_relevance": usd_relevance,
        }
