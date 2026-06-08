from typing import Any

from fastapi import APIRouter, Body

from backend.mt5_demo.demo_execution_simulator_service import DemoExecutionSimulatorService
from backend.mt5_demo.demo_execution_readiness_service import DemoExecutionReadinessService
from backend.mt5_demo.demo_final_approval_service import DemoFinalApprovalService
from backend.mt5_demo.demo_approval_workflow_service import DemoApprovalWorkflowService
from backend.mt5_demo.demo_order_authorization_service import DemoOrderAuthorizationService
from backend.mt5_demo.demo_order_dry_run_service import DemoOrderDryRunService
from backend.mt5_demo.demo_order_preflight_service import DemoOrderPreflightService
from backend.mt5_demo.demo_trade_test_plan_service import DemoTradeTestPlanService
from backend.mt5_demo.guarded_demo_order_sender_service import GuardedDemoOrderSenderService
from backend.mt5_demo.market_snapshot_service import MarketSnapshotService
from backend.mt5_demo.mt5_demo_service import MT5DemoService
from backend.mt5_demo.mt5_historical_backfill_service import MT5HistoricalBackfillService
from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService
from backend.mt5_demo.mt5_demo_position_sync_service import MT5DemoPositionSyncService
from backend.mt5_demo.mt5_position_monitoring_service import MT5PositionMonitoringService
from backend.mt5_demo.mt5_trade_close_sync_service import MT5TradeCloseSyncService
from backend.mt5_demo.mt5_trade_lifecycle_service import MT5TradeLifecycleService
from backend.mt5_demo.mt5_strategy_consumption_service import MT5StrategyConsumptionService
from backend.mt5_demo.mt5_strategy_feed_adapter import MT5StrategyFeedAdapter
from backend.mt5_demo.mt5_risk_qualification_service import MT5RiskQualificationService
from backend.mt5_demo.mt5_execution_gate_validation_service import MT5ExecutionGateValidationService


router = APIRouter(prefix="/mt5-demo", tags=["MT5 Demo"])
service = MT5DemoService()
demo_order_authorization_service = DemoOrderAuthorizationService()
market_data_service = MT5MarketDataService()
market_snapshot_service = MarketSnapshotService(market_data_service=market_data_service)
historical_backfill_service = MT5HistoricalBackfillService(market_data_service=market_data_service)
strategy_feed_adapter = MT5StrategyFeedAdapter(backfill_service=historical_backfill_service)
strategy_consumption_service = MT5StrategyConsumptionService(feed_adapter=strategy_feed_adapter)
risk_qualification_service = MT5RiskQualificationService(strategy_consumption_service=strategy_consumption_service)
execution_gate_service = MT5ExecutionGateValidationService(
    risk_qualification_service=risk_qualification_service,
    market_snapshot_service=market_snapshot_service,
    backfill_service=historical_backfill_service,
)
demo_order_dry_run_service = DemoOrderDryRunService(
    authorization_service=demo_order_authorization_service,
    execution_gate_service=execution_gate_service,
)
demo_order_preflight_service = DemoOrderPreflightService(
    authorization_service=demo_order_authorization_service,
    dry_run_service=demo_order_dry_run_service,
    risk_qualification_service=risk_qualification_service,
    execution_gate_service=execution_gate_service,
    market_data_service=market_data_service,
)
demo_execution_simulator_service = DemoExecutionSimulatorService(
    preflight_service=demo_order_preflight_service,
)
demo_execution_readiness_service = DemoExecutionReadinessService(
    mt5_demo_service=service,
    market_data_service=market_data_service,
    market_snapshot_service=market_snapshot_service,
    historical_backfill_service=historical_backfill_service,
    strategy_feed_adapter=strategy_feed_adapter,
    strategy_consumption_service=strategy_consumption_service,
    risk_qualification_service=risk_qualification_service,
    execution_gate_service=execution_gate_service,
    authorization_service=demo_order_authorization_service,
    dry_run_service=demo_order_dry_run_service,
    preflight_service=demo_order_preflight_service,
    simulator_service=demo_execution_simulator_service,
)
demo_trade_test_plan_service = DemoTradeTestPlanService()
demo_final_approval_service = DemoFinalApprovalService(
    mt5_demo_service=service,
    market_data_service=market_data_service,
    strategy_feed_adapter=strategy_feed_adapter,
    risk_qualification_service=risk_qualification_service,
    execution_gate_service=execution_gate_service,
    authorization_service=demo_order_authorization_service,
    dry_run_service=demo_order_dry_run_service,
    preflight_service=demo_order_preflight_service,
    simulator_service=demo_execution_simulator_service,
    readiness_service=demo_execution_readiness_service,
    test_plan_service=demo_trade_test_plan_service,
)
demo_approval_workflow_service = DemoApprovalWorkflowService(
    authorization_service=demo_order_authorization_service,
    dry_run_service=demo_order_dry_run_service,
    preflight_service=demo_order_preflight_service,
    simulator_service=demo_execution_simulator_service,
    readiness_service=demo_execution_readiness_service,
    test_plan_service=demo_trade_test_plan_service,
    final_approval_service=demo_final_approval_service,
)
mt5_demo_position_sync_service = MT5DemoPositionSyncService()
mt5_trade_lifecycle_service = MT5TradeLifecycleService()
mt5_trade_close_sync_service = MT5TradeCloseSyncService()
mt5_position_monitoring_service = MT5PositionMonitoringService(mt5_demo_position_sync_service)
guarded_demo_order_sender_service = GuardedDemoOrderSenderService(
    mt5_demo_service=service,
    approval_workflow_service=demo_approval_workflow_service,
    final_approval_service=demo_final_approval_service,
    dry_run_service=demo_order_dry_run_service,
    preflight_service=demo_order_preflight_service,
    simulator_service=demo_execution_simulator_service,
    readiness_service=demo_execution_readiness_service,
)


@router.get("/status")
async def get_mt5_demo_status() -> dict:
    return service.get_status()


@router.get("/account")
async def get_mt5_demo_account() -> dict:
    return service.get_account()


@router.get("/symbols")
async def get_mt5_demo_symbols() -> dict:
    return service.get_symbols()


@router.get("/health")
async def get_mt5_demo_health() -> dict:
    return service.get_health()


@router.get("/market-watch")
async def get_mt5_demo_market_watch() -> dict:
    return service.get_market_watch()


@router.get("/overview")
async def get_mt5_demo_overview() -> dict:
    return market_snapshot_service.get_overview()


@router.get("/market-data/status")
async def get_mt5_demo_market_data_status() -> dict:
    return market_data_service.get_market_data_status()


@router.get("/market-data/tick/{symbol}")
async def get_mt5_demo_symbol_tick(symbol: str) -> dict:
    return market_data_service.get_symbol_tick(symbol)


@router.get("/market-data/candles/{symbol}/{timeframe}")
async def get_mt5_demo_symbol_candles(symbol: str, timeframe: str, count: int = 50) -> dict:
    return market_data_service.get_symbol_candles(symbol, timeframe, count)


@router.get("/market-data/spread/{symbol}")
async def get_mt5_demo_symbol_spread(symbol: str) -> dict:
    return market_data_service.get_symbol_spread(symbol)


@router.get("/history/status")
async def get_mt5_demo_history_status() -> dict:
    return historical_backfill_service.get_status()


@router.get("/history/{symbol}/{timeframe}")
async def get_mt5_demo_history(symbol: str, timeframe: str, count: int = 500) -> dict:
    return historical_backfill_service.fetch_history(symbol, timeframe, count)


@router.get("/history/{symbol}/{timeframe}/summary")
async def get_mt5_demo_history_summary(symbol: str, timeframe: str) -> dict:
    return historical_backfill_service.summarize_backfill(symbol, timeframe)


@router.get("/history/{symbol}/{timeframe}/validate")
async def validate_mt5_demo_history(symbol: str, timeframe: str, count: int = 500) -> dict:
    history = historical_backfill_service.fetch_history(symbol, timeframe, count)
    return {
        "symbol": history.get("symbol"),
        "timeframe": history.get("timeframe"),
        "requested_count": history.get("requested_count"),
        "returned_count": history.get("returned_count"),
        "validation": history.get("validation"),
        "status": history.get("status"),
        "source": "MT5_DEMO",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }


@router.get("/strategy-feed/{symbol}")
async def get_mt5_demo_strategy_feed(symbol: str) -> dict:
    return strategy_feed_adapter.build_strategy_feed(symbol)


@router.get("/strategy-feed/{symbol}/htf")
async def get_mt5_demo_strategy_feed_htf(symbol: str) -> dict:
    return strategy_feed_adapter.get_htf_context(symbol)


@router.get("/strategy-feed/{symbol}/ltf")
async def get_mt5_demo_strategy_feed_ltf(symbol: str) -> dict:
    return strategy_feed_adapter.get_ltf_context(symbol)


@router.get("/strategy-consumption/status")
async def get_mt5_demo_strategy_consumption_status() -> dict:
    return strategy_consumption_service.get_status()


@router.post("/strategy-consumption/{symbol}/analyze")
async def analyze_mt5_demo_strategy_consumption(symbol: str) -> dict:
    return strategy_consumption_service.analyze_symbol_from_mt5_feed(symbol)


@router.post("/strategy-consumption/analyze-all")
async def analyze_all_mt5_demo_strategy_consumption() -> dict:
    return strategy_consumption_service.analyze_all_symbols_from_mt5_feed()


@router.get("/strategy-consumption/{symbol}/latest")
async def get_latest_mt5_demo_strategy_consumption(symbol: str) -> dict:
    return strategy_consumption_service.latest(symbol)


@router.get("/strategy-consumption/history")
async def get_mt5_demo_strategy_consumption_history(limit: int = 100) -> list[dict]:
    return strategy_consumption_service.history(limit)


@router.get("/risk-qualification/status")
async def get_mt5_demo_risk_qualification_status() -> dict:
    return risk_qualification_service.get_status()


@router.post("/risk-qualification/{symbol}/evaluate")
async def evaluate_mt5_demo_risk_qualification(symbol: str) -> dict:
    return risk_qualification_service.qualify_symbol_from_mt5_strategy(symbol)


@router.post("/risk-qualification/evaluate-all")
async def evaluate_all_mt5_demo_risk_qualification() -> dict:
    return risk_qualification_service.qualify_all_symbols_from_mt5_strategy()


@router.get("/risk-qualification/{symbol}/latest")
async def get_latest_mt5_demo_risk_qualification(symbol: str) -> dict:
    return risk_qualification_service.get_latest_risk_result(symbol)


@router.get("/risk-qualification/history")
async def get_mt5_demo_risk_qualification_history(limit: int = 100) -> list[dict]:
    return risk_qualification_service.history(limit)


@router.get("/execution-gate/status")
async def get_mt5_demo_execution_gate_status() -> dict:
    return execution_gate_service.get_status()


@router.post("/execution-gate/{symbol}/evaluate")
async def evaluate_mt5_demo_execution_gate(symbol: str) -> dict:
    return execution_gate_service.evaluate_symbol(symbol)


@router.post("/execution-gate/evaluate-all")
async def evaluate_all_mt5_demo_execution_gate() -> dict:
    return execution_gate_service.evaluate_all()


@router.get("/execution-gate/{symbol}/latest")
async def get_latest_mt5_demo_execution_gate(symbol: str) -> dict:
    return execution_gate_service.latest(symbol)


@router.get("/execution-gate/history")
async def get_mt5_demo_execution_gate_history(limit: int = 100) -> list[dict]:
    return execution_gate_service.history(limit)


@router.get("/pipeline-summary")
async def get_mt5_demo_pipeline_summary() -> dict:
    return execution_gate_service.pipeline_summary()


@router.get("/demo-authorization/status")
async def get_demo_order_authorization_status() -> dict:
    return demo_order_authorization_service.get_status()


@router.post("/demo-authorization/request")
async def request_demo_order_authorization(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return demo_order_authorization_service.request_demo_authorization(payload)


@router.post("/demo-authorization/revoke")
async def revoke_demo_order_authorization() -> dict:
    return demo_order_authorization_service.revoke_demo_authorization()


@router.get("/demo-authorization/checklist")
async def get_demo_order_authorization_checklist() -> dict:
    return demo_order_authorization_service.get_checklist()


@router.get("/demo-order-dry-run/status")
async def get_demo_order_dry_run_status() -> dict:
    return demo_order_dry_run_service.get_status()


@router.post("/demo-order-dry-run/create")
async def create_demo_order_dry_run(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return demo_order_dry_run_service.create_dry_run(payload)


@router.get("/demo-order-dry-run/latest")
async def get_latest_demo_order_dry_run() -> dict:
    return demo_order_dry_run_service.get_latest()


@router.get("/demo-order-dry-run/history")
async def get_demo_order_dry_run_history(limit: int = 100) -> list[dict]:
    return demo_order_dry_run_service.list_history(limit)


@router.get("/preflight/status")
async def get_demo_order_preflight_status() -> dict:
    return demo_order_preflight_service.get_status()


@router.post("/preflight/run")
async def run_demo_order_preflight(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return demo_order_preflight_service.run_preflight(payload)


@router.get("/preflight/latest")
async def get_latest_demo_order_preflight() -> dict:
    return demo_order_preflight_service.get_latest()


@router.get("/preflight/history")
async def get_demo_order_preflight_history(limit: int = 100) -> list[dict]:
    return demo_order_preflight_service.list_history(limit)


@router.get("/execution-simulator/status")
async def get_demo_execution_simulator_status() -> dict:
    return demo_execution_simulator_service.get_status()


@router.post("/execution-simulator/run")
async def run_demo_execution_simulation(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return demo_execution_simulator_service.simulate_execution(payload)


@router.get("/execution-simulator/latest")
async def get_latest_demo_execution_simulation() -> dict:
    return demo_execution_simulator_service.get_latest()


@router.get("/execution-simulator/history")
async def get_demo_execution_simulation_history(limit: int = 100) -> list[dict]:
    return demo_execution_simulator_service.list_history(limit)


@router.get("/readiness/status")
async def get_demo_execution_readiness_status() -> dict:
    return demo_execution_readiness_service.get_status()


@router.post("/readiness/run-audit")
async def run_demo_execution_readiness_audit() -> dict:
    return demo_execution_readiness_service.run_readiness_audit()


@router.get("/readiness/latest")
async def get_latest_demo_execution_readiness_audit() -> dict:
    return demo_execution_readiness_service.get_latest_audit()


@router.get("/readiness/history")
async def get_demo_execution_readiness_history(limit: int = 100) -> list[dict]:
    return demo_execution_readiness_service.get_audit_history(limit)


@router.get("/test-plan/status")
async def get_demo_trade_test_plan_status() -> dict:
    return demo_trade_test_plan_service.get_status()


@router.post("/test-plan/generate")
async def generate_demo_trade_test_plan() -> dict:
    return demo_trade_test_plan_service.generate_test_plan()


@router.get("/test-plan/latest")
async def get_latest_demo_trade_test_plan() -> dict:
    return demo_trade_test_plan_service.get_latest_test_plan()


@router.get("/test-plan/history")
async def get_demo_trade_test_plan_history(limit: int = 100) -> list[dict]:
    return demo_trade_test_plan_service.get_test_plan_history(limit)


@router.get("/final-demo-approval/status")
async def get_final_demo_approval_status() -> dict:
    return demo_final_approval_service.get_status()


@router.post("/final-demo-approval/run-review")
async def run_final_demo_approval_review() -> dict:
    return demo_final_approval_service.run_final_approval_review()


@router.get("/final-demo-approval/latest")
async def get_latest_final_demo_approval() -> dict:
    return demo_final_approval_service.get_latest_approval()


@router.get("/final-demo-approval/history")
async def get_final_demo_approval_history(limit: int = 100) -> list[dict]:
    return demo_final_approval_service.get_approval_history(limit)


@router.post("/final-demo-approval/revoke")
async def revoke_final_demo_approval() -> dict:
    return demo_final_approval_service.revoke_final_approval()


@router.get("/demo-approval-workflow/status")
async def get_demo_approval_workflow_status() -> dict:
    return demo_approval_workflow_service.get_status()


@router.post("/demo-approval-workflow/run")
async def run_demo_approval_workflow(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return demo_approval_workflow_service.run_workflow(payload)


@router.get("/demo-approval-workflow/latest")
async def get_latest_demo_approval_workflow() -> dict:
    return demo_approval_workflow_service.get_latest()


@router.get("/demo-approval-workflow/history")
async def get_demo_approval_workflow_history(limit: int = 100) -> list[dict]:
    return demo_approval_workflow_service.list_history(limit)


@router.get("/guarded-demo-order/status")
async def get_guarded_demo_order_status() -> dict:
    return guarded_demo_order_sender_service.get_status()


@router.post("/guarded-demo-order/prepare")
async def prepare_guarded_demo_order(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return guarded_demo_order_sender_service.prepare_order(payload)


@router.post("/guarded-demo-order/send")
async def send_guarded_demo_order(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return guarded_demo_order_sender_service.send_order(payload)


@router.get("/guarded-demo-order/latest")
async def get_latest_guarded_demo_order() -> dict:
    return guarded_demo_order_sender_service.get_latest()


@router.get("/guarded-demo-order/history")
async def get_guarded_demo_order_history(limit: int = 100) -> list[dict]:
    return guarded_demo_order_sender_service.list_history(limit)


@router.get("/positions/status")
async def get_mt5_demo_positions_status() -> dict:
    return mt5_demo_position_sync_service.get_status()


@router.get("/positions/open")
async def get_mt5_demo_open_positions() -> dict:
    return mt5_demo_position_sync_service.get_open_positions()


@router.get("/positions/open/{symbol}")
async def get_mt5_demo_open_positions_by_symbol(symbol: str) -> dict:
    return mt5_demo_position_sync_service.get_open_positions_by_symbol(symbol)


@router.post("/positions/sync-journal")
async def sync_mt5_demo_positions_to_journal() -> dict:
    return mt5_demo_position_sync_service.sync_journal()


@router.get("/positions/latest-sync")
async def get_latest_mt5_demo_position_sync() -> dict:
    return mt5_demo_position_sync_service.get_latest_sync()


@router.get("/lifecycle/status")
async def get_mt5_demo_lifecycle_status() -> dict:
    return mt5_trade_lifecycle_service.get_status()


@router.post("/lifecycle/sync")
async def sync_mt5_demo_trade_lifecycle() -> dict:
    return mt5_trade_lifecycle_service.sync()


@router.get("/lifecycle/latest")
async def get_latest_mt5_demo_trade_lifecycle() -> dict:
    return mt5_trade_lifecycle_service.get_latest()


@router.get("/lifecycle/history")
async def get_mt5_demo_trade_lifecycle_history(limit: int = 100) -> list[dict]:
    return mt5_trade_lifecycle_service.get_history(limit)


@router.get("/lifecycle/analytics")
async def get_mt5_demo_trade_lifecycle_analytics() -> dict:
    return mt5_trade_lifecycle_service.get_analytics()


@router.get("/position-monitor/status")
async def get_mt5_demo_position_monitor_status() -> dict:
    return mt5_position_monitoring_service.get_status()


@router.get("/position-monitor/open")
async def get_mt5_demo_position_monitor_open() -> dict:
    return mt5_position_monitoring_service.get_open_positions()


@router.get("/position-monitor/open/{symbol}")
async def get_mt5_demo_position_monitor_open_by_symbol(symbol: str) -> dict:
    return mt5_position_monitoring_service.get_open_positions_by_symbol(symbol)


@router.get("/position-monitor/ticket/{ticket}")
async def get_mt5_demo_position_monitor_by_ticket(ticket: str) -> dict:
    return mt5_position_monitoring_service.get_position_by_ticket(ticket)


@router.post("/position-monitor/sync")
async def sync_mt5_demo_position_monitor() -> dict:
    return mt5_position_monitoring_service.sync()


@router.get("/close-sync/status")
async def get_mt5_demo_close_sync_status() -> dict:
    return mt5_trade_close_sync_service.get_status()


@router.post("/close-sync/run")
async def run_mt5_demo_close_sync() -> dict:
    return mt5_trade_close_sync_service.run()


@router.get("/close-sync/latest")
async def get_latest_mt5_demo_close_sync() -> dict:
    return mt5_trade_close_sync_service.get_latest()


@router.get("/close-sync/history")
async def get_mt5_demo_close_sync_history(limit: int = 100) -> list[dict]:
    return mt5_trade_close_sync_service.get_history(limit)


@router.get("/close-sync/analytics")
async def get_mt5_demo_close_sync_analytics() -> dict:
    return mt5_trade_close_sync_service.get_analytics()


@router.post("/order-send")
async def block_order_send() -> dict:
    return service.block_execution_attempt("order_send")


@router.post("/position-open")
async def block_position_open() -> dict:
    return service.block_execution_attempt("position_open")


@router.post("/market-buy")
async def block_market_buy() -> dict:
    return service.block_execution_attempt("market_buy")


@router.post("/market-sell")
async def block_market_sell() -> dict:
    return service.block_execution_attempt("market_sell")
