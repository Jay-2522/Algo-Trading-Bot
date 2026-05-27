from backend.replay.replay_models import ReplayRunResult, ReplayStepResult


class ReplayMetricsCalculator:
    """Summarize replay decisions and paper outcomes."""

    def calculate_metrics(
        self,
        step_results: list[ReplayStepResult],
        replay_id: str,
        symbol: str,
        timeframe: str,
    ) -> ReplayRunResult:
        actions = [step.simulation_decision.get("action", "NO_TRADE") for step in step_results]
        outcomes = [step.paper_trade_state.get("latest_outcome") for step in step_results]
        rr_values = [
            float(step.paper_trade_state.get("latest_rr", 0.0) or 0.0)
            for step in step_results
            if step.paper_trade_state.get("latest_rr") is not None
        ]
        first_time = step_results[0].replay_time if step_results else None
        last_time = step_results[-1].replay_time if step_results else None
        decisions = sum(action in {"SIMULATE_BUY", "SIMULATE_SELL", "WAIT", "AVOID"} for action in actions)
        simulated = sum(action in {"SIMULATE_BUY", "SIMULATE_SELL"} for action in actions)
        net_rr = round(sum(rr_values), 4)
        return ReplayRunResult(
            replay_id=replay_id,
            symbol=symbol,
            timeframe=timeframe,
            start_time=first_time,
            end_time=last_time,
            total_steps=len(step_results),
            decisions_count=decisions,
            simulated_trades_count=simulated,
            blocked_count=sum(action in {"AVOID", "NO_TRADE"} for action in actions),
            wait_count=sum(action == "WAIT" for action in actions),
            avoid_count=sum(action == "AVOID" for action in actions),
            win_count=sum(outcome == "WIN" for outcome in outcomes),
            loss_count=sum(outcome == "LOSS" for outcome in outcomes),
            breakeven_count=sum(outcome == "BREAKEVEN" for outcome in outcomes),
            net_rr=net_rr,
            max_drawdown=round(min(0.0, net_rr), 4),
            summary=(
                "Replay completed with no visible steps."
                if not step_results
                else f"Replay completed {len(step_results)} step(s), {decisions} decision event(s), "
                f"and {simulated} simulated trade intent(s)."
            ),
            step_results=step_results,
        )
