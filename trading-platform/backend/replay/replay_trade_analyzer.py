from backend.replay.replay_models import ReplayStepResult
from backend.replay.replay_report_models import ReplayTradeAnalytics


class ReplayTradeAnalyzer:
    """Analyze closed simulated paper outcomes from replay steps."""

    CLOSED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN"}

    def analyze_trades(self, step_results: list[ReplayStepResult]) -> ReplayTradeAnalytics:
        trade_events = self._closed_trade_events(step_results)
        rr_values = [event["rr"] for event in trade_events]
        total = len(trade_events)
        wins = sum(event["outcome"] == "WIN" for event in trade_events)
        losses = sum(event["outcome"] == "LOSS" for event in trade_events)
        breakeven = sum(event["outcome"] == "BREAKEVEN" for event in trade_events)
        net_rr = round(sum(rr_values), 4)
        average_rr = round(net_rr / total, 4) if total else 0.0
        holding_steps = [event["holding_steps"] for event in trade_events if event["holding_steps"] > 0]

        return ReplayTradeAnalytics(
            total_trades=total,
            wins=wins,
            losses=losses,
            breakeven=breakeven,
            win_rate=round((wins / total) * 100.0, 2) if total else 0.0,
            loss_rate=round((losses / total) * 100.0, 2) if total else 0.0,
            average_rr=average_rr,
            net_rr=net_rr,
            best_trade_rr=round(max(rr_values), 4) if rr_values else 0.0,
            worst_trade_rr=round(min(rr_values), 4) if rr_values else 0.0,
            average_holding_steps=round(sum(holding_steps) / len(holding_steps), 2) if holding_steps else 0.0,
            expectancy=average_rr,
        )

    def _closed_trade_events(self, step_results: list[ReplayStepResult]) -> list[dict]:
        events: list[dict] = []
        active_start: int | None = None
        last_signature: tuple[str | None, float | None] | None = None

        for step in step_results:
            active_positions = int(step.paper_trade_state.get("active_positions", 0) or 0)
            if active_positions > 0 and active_start is None:
                active_start = step.step_index

            outcome = step.paper_trade_state.get("latest_outcome")
            if outcome not in self.CLOSED_OUTCOMES:
                continue

            rr = float(step.paper_trade_state.get("latest_rr", 0.0) or 0.0)
            signature = (outcome, rr)
            if signature == last_signature:
                continue

            holding_steps = step.step_index - active_start if active_start is not None else 0
            events.append({"outcome": outcome, "rr": rr, "holding_steps": max(0, holding_steps)})
            last_signature = signature
            active_start = None
        return events
