class DrawdownTracker:
    """Track realized simulated equity decline from its running peak."""

    def __init__(self, initial_balance: float = 10000.0) -> None:
        self.initial_balance = max(float(initial_balance), 0.01)
        self.peak_balance = self.initial_balance
        self.current_balance = self.initial_balance
        self.current_drawdown_percent = 0.0
        self.max_drawdown_percent = 0.0

    def update_equity(self, balance: float) -> dict:
        self.current_balance = float(balance)
        self.peak_balance = max(self.peak_balance, self.current_balance)
        decline = max(self.peak_balance - self.current_balance, 0.0)
        self.current_drawdown_percent = (
            decline / self.peak_balance * 100 if self.peak_balance else 0.0
        )
        self.max_drawdown_percent = max(self.max_drawdown_percent, self.current_drawdown_percent)
        return self.get_drawdown_status()

    def apply_pnl(self, pnl: float) -> dict:
        return self.update_equity(self.current_balance + float(pnl))

    def get_drawdown_status(self) -> dict:
        return {
            "peak_balance": round(self.peak_balance, 2),
            "current_balance": round(self.current_balance, 2),
            "current_drawdown_percent": round(self.current_drawdown_percent, 4),
            "max_drawdown_percent": round(self.max_drawdown_percent, 4),
        }
