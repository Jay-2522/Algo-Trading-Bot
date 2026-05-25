from typing import Any

from backend.ai_engine.ai_orchestrator import AIOrchestrator
from backend.execution_engine.execution_models import OrderRequest
from backend.execution_engine.execution_service import ExecutionService
from backend.market_data.market_data_service import MarketDataService
from backend.news_engine.news_filter_service import NewsFilterService
from backend.orchestration.orchestration_models import OrchestrationDecision
from backend.orchestration.pipeline_context import PipelineContext
from backend.risk_engine.risk_models import RiskCheckRequest
from backend.risk_engine.risk_service import RiskService, get_risk_service
from backend.strategy_engine.liquidity_detector import LiquidityDetector
from backend.strategy_engine.session_manager import SessionManager
from backend.strategy_engine.strategy_service import StrategyService
from backend.strategy_engine.structure_analyzer import StructureAnalyzer
from backend.strategy_engine.trend_analyzer import TrendAnalyzer
from backend.strategy_engine.validators import validate_strategy_symbol, validate_strategy_timeframe


class PipelineRunner:
    """Run engine collection and simulation preparation in recoverable steps."""

    ANALYSIS_STEPS = [
        "collect_market_data",
        "run_strategy_analysis",
        "run_ai_decision",
        "run_news_filter",
        "run_risk_check",
        "prepare_execution_decision",
    ]

    def __init__(
        self,
        market_data_service: MarketDataService | None = None,
        strategy_service: StrategyService | None = None,
        ai_orchestrator: AIOrchestrator | None = None,
        news_service: NewsFilterService | None = None,
        risk_service: RiskService | None = None,
        execution_service: ExecutionService | None = None,
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.strategy_service = strategy_service or StrategyService()
        self.ai_orchestrator = ai_orchestrator or AIOrchestrator()
        self.news_service = news_service or NewsFilterService()
        self.risk_service = risk_service or get_risk_service()
        self.execution_service = execution_service or ExecutionService(self.risk_service)

    def collect_context(self, symbol: str, timeframe: str = "M15") -> tuple[PipelineContext, list[str]]:
        normalized_symbol = validate_strategy_symbol(symbol)
        normalized_timeframe = validate_strategy_timeframe(timeframe)
        context = PipelineContext(normalized_symbol, normalized_timeframe)
        steps_run: list[str] = []

        self.collect_market_data(context)
        steps_run.append("collect_market_data")
        self.run_strategy_analysis(context)
        steps_run.append("run_strategy_analysis")
        self.run_ai_decision(context)
        steps_run.append("run_ai_decision")
        self.run_news_filter(context)
        steps_run.append("run_news_filter")
        self.run_risk_check(context)
        steps_run.append("run_risk_check")
        context.metadata["execution_mode"] = "SIMULATION_ONLY"
        steps_run.append("prepare_execution_decision")
        return context, steps_run

    def collect_market_data(self, context: PipelineContext) -> None:
        try:
            tick = self.market_data_service.get_latest_tick(context.symbol)
            context.market_data = {"latest_tick": tick, "status": "available"}
        except Exception as exc:
            context.market_data = {"status": "unavailable", "message": str(exc)}
            context.add_error("collect_market_data", exc)

    def run_strategy_analysis(self, context: PipelineContext) -> None:
        try:
            context.strategy_snapshot = self.strategy_service.analyze_symbol(
                context.symbol,
                context.timeframe,
            )
        except Exception as exc:
            context.strategy_snapshot = self._foundation_strategy_context(context)
            context.add_error("run_strategy_analysis", exc)

    def run_ai_decision(self, context: PipelineContext) -> None:
        try:
            package = self.ai_orchestrator.generate_full_analysis(
                context.symbol,
                context.strategy_snapshot,
                persist=False,
            )
            context.ai_decision = package["decision"].model_dump(mode="json")
            context.metadata["ai_explanation"] = package["explanation"].model_dump(mode="json")
        except Exception as exc:
            context.ai_decision = {
                "symbol": context.symbol,
                "action": "AVOID",
                "approved": False,
                "confidence": 0.0,
                "rejection_reason": "AI evaluation unavailable.",
            }
            context.add_error("run_ai_decision", exc)

    def run_news_filter(self, context: PipelineContext) -> None:
        try:
            context.news_status = self.news_service.get_news_risk_status(
                context.symbol,
                persist=False,
            ).model_dump(mode="json")
        except Exception as exc:
            context.news_status = {
                "trading_allowed": False,
                "risk_level": "BLOCKED",
                "reason": "News risk evaluation unavailable; trading blocked by default.",
            }
            context.add_error("run_news_filter", exc)

    def run_risk_check(self, context: PipelineContext) -> None:
        try:
            risk_check = self.risk_service.evaluate_trade_permission(
                RiskCheckRequest(
                    symbol=context.symbol,
                    account_balance=10000,
                    current_drawdown_percent=0,
                    consecutive_losses=0,
                    current_spread=10,
                    expected_slippage=2,
                )
            )
            context.risk_status = risk_check.model_dump(mode="json")
        except Exception as exc:
            context.risk_status = {
                "allowed": False,
                "risk_level": "BLOCKED",
                "reasons": ["Risk permission evaluation unavailable; trading blocked by default."],
            }
            context.add_error("run_risk_check", exc)

    def simulate_if_approved(
        self,
        context: PipelineContext,
        decision: OrchestrationDecision,
    ) -> dict[str, Any] | None:
        if not decision.approved or decision.final_action not in {"BUY", "SELL"}:
            return None
        try:
            result = self.execution_service.simulate_order(
                OrderRequest(
                    symbol=context.symbol,
                    side=decision.final_action,
                    order_type="MARKET",
                    lot_size=0.01,
                    stop_loss=1.0,
                    take_profit=1.0,
                    comment="Day 10 orchestration simulation only",
                )
            )
            context.execution_result = result.model_dump(mode="json")
            return context.execution_result
        except Exception as exc:
            context.add_error("simulate_execution", exc)
            context.execution_result = {
                "success": False,
                "status": "SIMULATION_UNAVAILABLE",
                "message": str(exc),
                "execution_mode": "SIMULATION",
            }
            return context.execution_result

    def _foundation_strategy_context(self, context: PipelineContext) -> dict[str, Any]:
        return {
            "symbol": context.symbol,
            "timeframe": context.timeframe,
            "trend_analysis": TrendAnalyzer().determine_trend([]),
            "liquidity_analysis": LiquidityDetector().detect_liquidity_zones([]),
            "structure_analysis": StructureAnalyzer().analyze_market_structure([]),
            "session_info": SessionManager().get_session_info(),
            "status": "market_data_unavailable",
        }
