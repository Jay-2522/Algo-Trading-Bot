from backend.nifty50.nifty_risk_engine import NIFTYRiskEngine
from backend.nifty50.nifty_risk_models import NIFTYTradeCandidate
from backend.nifty50.nifty_strategy_models import NIFTYStrategySnapshot
from backend.nifty50.nifty_trade_decision_store import NIFTYTradeDecisionStore


class NIFTYTradeQualifier:
    def __init__(self, risk_engine: NIFTYRiskEngine | None = None, decision_store: NIFTYTradeDecisionStore | None = None) -> None:
        self.risk_engine = risk_engine or NIFTYRiskEngine()
        self.decision_store = decision_store or NIFTYTradeDecisionStore()

    def qualify(self, snapshot: NIFTYStrategySnapshot) -> NIFTYTradeCandidate:
        decision = self.decision_store.store_decision(self.risk_engine.evaluate(snapshot))
        action = "WAIT"
        qualified = False
        if decision.approved and snapshot.strategy_bias == "BULLISH":
            action = "BUY"
            qualified = True
        elif decision.approved and snapshot.strategy_bias == "BEARISH":
            action = "SELL"
            qualified = True
        candidate = NIFTYTradeCandidate(
            action=action,
            confidence=snapshot.confidence,
            strategy_bias=snapshot.strategy_bias,
            trade_quality=decision.trade_quality,
            risk_decision_id=decision.decision_id,
            qualified=qualified,
            rejection_reasons=decision.rejection_reasons,
            execution_allowed=False,
        )
        return self.decision_store.store_candidate(candidate)
