from backend.replay.replay_models import ReplayStepResult
from backend.replay.replay_report_models import ReplayEquityPoint


class ReplayEquityCurveBuilder:
    """Build a deterministic equity curve from closed replay paper outcomes."""

    CLOSED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN"}

    def build_equity_curve(
        self, step_results: list[ReplayStepResult], initial_balance: float = 10000.0
    ) -> list[ReplayEquityPoint]:
        if not step_results:
            return []

        balance = float(initial_balance)
        peak = balance
        cumulative_rr = 0.0
        risk_unit = max(balance * 0.01, 1.0)
        last_signature: tuple[str | None, float | None] | None = None
        points: list[ReplayEquityPoint] = []

        for step in step_results:
            outcome = step.paper_trade_state.get("latest_outcome")
            rr = float(step.paper_trade_state.get("latest_rr", 0.0) or 0.0)
            signature = (outcome, rr)
            if outcome in self.CLOSED_OUTCOMES and signature != last_signature:
                cumulative_rr = round(cumulative_rr + rr, 4)
                balance = round(float(initial_balance) + cumulative_rr * risk_unit, 2)
                last_signature = signature

            equity = balance
            peak = max(peak, equity)
            points.append(
                ReplayEquityPoint(
                    step_index=step.step_index,
                    replay_time=step.replay_time,
                    balance=balance,
                    equity=equity,
                    drawdown=round(max(0.0, peak - equity), 2),
                    cumulative_rr=cumulative_rr,
                )
            )
        return points
