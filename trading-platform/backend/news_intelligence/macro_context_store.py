from backend.news_intelligence.macro_models import MacroInstrumentContext


class MacroContextStore:
    """In-memory store for manually supplied DXY and US10Y contexts."""

    _contexts: dict[str, MacroInstrumentContext] = {}

    def update_instrument_context(self, context: MacroInstrumentContext) -> MacroInstrumentContext:
        self._contexts[context.symbol.upper()] = context
        return context

    def get_instrument_context(self, symbol: str) -> MacroInstrumentContext | None:
        return self._contexts.get(symbol.upper())

    def get_all_contexts(self) -> list[MacroInstrumentContext]:
        return list(self._contexts.values())

    def clear(self) -> None:
        self._contexts.clear()
