from backend.orchestration.orchestration_models import OrchestrationDecision
from backend.orchestration.pipeline_context import PipelineContext


class DecisionCoordinator:
    """Apply deterministic permission priority to collected engine outcomes."""

    def create_final_decision(self, context: PipelineContext) -> OrchestrationDecision:
        ai_decision = context.ai_decision or {}
        news_status = context.news_status or {}
        risk_status = context.risk_status or {}
        strategy_snapshot = context.strategy_snapshot or {}
        confidence = float(ai_decision.get("confidence", 0.0))

        if not news_status.get("trading_allowed", False):
            return self._blocked(
                context,
                "NEWS",
                [str(news_status.get("reason", "News intelligence has blocked trading."))],
                confidence,
            )
        if not risk_status.get("allowed", False):
            reasons = risk_status.get("reasons") or ["Risk management has blocked trading."]
            return self._blocked(context, "RISK", list(reasons), confidence)
        if not ai_decision.get("approved", False):
            reason = ai_decision.get("rejection_reason") or "AI decision has not approved this setup."
            return self._blocked(context, "AI", [str(reason)], confidence)

        trend = strategy_snapshot.get("trend_analysis", {}).get("trend", "ranging")
        if trend not in {"bullish", "bearish"}:
            return OrchestrationDecision(
                symbol=context.symbol,
                approved=False,
                final_action="WAIT",
                confidence=confidence,
                blocked_by="STRATEGY",
                reasons=["Strategy context lacks directional market structure alignment."],
                ai_decision=ai_decision,
                news_status=news_status,
                risk_status=risk_status,
                strategy_snapshot=strategy_snapshot,
            )

        action = ai_decision.get("action", "WAIT")
        if action not in {"BUY", "SELL"}:
            return self._blocked(
                context,
                "AI",
                ["AI approval did not provide a simulation-eligible direction."],
                confidence,
            )
        return OrchestrationDecision(
            symbol=context.symbol,
            approved=True,
            final_action=action,
            confidence=confidence,
            blocked_by="NONE",
            reasons=["All analysis and permission gates passed for simulation only."],
            ai_decision=ai_decision,
            news_status=news_status,
            risk_status=risk_status,
            strategy_snapshot=strategy_snapshot,
        )

    def block_after_execution_validation(
        self,
        decision: OrchestrationDecision,
        message: str,
    ) -> OrchestrationDecision:
        """Convert an approved advisory outcome when simulation validation fails."""

        return decision.model_copy(
            update={
                "approved": False,
                "final_action": "AVOID",
                "blocked_by": "EXECUTION_VALIDATION",
                "reasons": [message],
            }
        )

    def _blocked(
        self,
        context: PipelineContext,
        blocked_by: str,
        reasons: list[str],
        confidence: float,
    ) -> OrchestrationDecision:
        return OrchestrationDecision(
            symbol=context.symbol,
            approved=False,
            final_action="AVOID",
            confidence=confidence,
            blocked_by=blocked_by,
            reasons=reasons,
            ai_decision=context.ai_decision or {},
            news_status=context.news_status or {},
            risk_status=context.risk_status or {},
            strategy_snapshot=context.strategy_snapshot or {},
        )
