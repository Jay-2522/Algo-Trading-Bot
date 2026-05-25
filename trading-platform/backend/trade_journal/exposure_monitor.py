from collections import defaultdict

from backend.trade_journal.journal_models import ExposureStatus, JournalEntry


class ExposureMonitor:
    """Measure risk-at-stop for currently open simulated journal positions."""

    def __init__(self, warning_threshold_percent: float = 2.0) -> None:
        self.warning_threshold_percent = warning_threshold_percent

    def exposure_by_symbol(self, entries: list[JournalEntry]) -> dict[str, float]:
        exposures: dict[str, float] = defaultdict(float)
        for entry in entries:
            if entry.outcome != "OPEN" or not entry.entry_price or entry.stop_loss is None:
                continue
            risk_percent = abs(entry.entry_price - entry.stop_loss) / entry.entry_price * 100
            exposures[entry.symbol] += risk_percent
        return {symbol: round(exposure, 4) for symbol, exposure in exposures.items()}

    def calculate_exposure(self, entries: list[JournalEntry]) -> ExposureStatus:
        by_symbol = self.exposure_by_symbol(entries)
        total = round(sum(by_symbol.values()), 4)
        highest = max(by_symbol, key=by_symbol.get) if by_symbol else None
        warning = None
        if total >= self.warning_threshold_percent:
            warning = "Total simulated exposure exceeds configured analytics threshold."
        elif highest and by_symbol[highest] >= self.warning_threshold_percent / 2:
            warning = f"Concentrated simulated exposure detected for {highest}."
        return ExposureStatus(
            total_exposure_percent=total,
            symbols_exposed=sorted(by_symbol),
            highest_risk_symbol=highest,
            exposure_warning=warning,
        )
