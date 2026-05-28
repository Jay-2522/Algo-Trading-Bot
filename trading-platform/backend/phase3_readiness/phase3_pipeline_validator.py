from backend.account_routing.account_routing_service import AccountRoutingService
from backend.execution_queue.execution_queue_service import ExecutionQueueService
from backend.monitoring.monitoring_service import MonitoringService
from backend.phase3_readiness.phase3_readiness_models import Phase3PipelineValidation
from backend.webhooks.tradingview_signal_normalizer import TradingViewSignalNormalizer
from backend.webhooks.webhook_orchestration_service import WebhookOrchestrationService


class Phase3PipelineValidator:
    """Validate the full signal-to-simulation pipeline without execution."""

    def validate_pipeline(self) -> Phase3PipelineValidation:
        issues: list[str] = []
        try:
            payload = {
                "symbol": "EURUSD",
                "action": "BUY",
                "timeframe": "M15",
                "strategy": "Phase 3 Readiness",
                "price": 1.085,
                "confidence": 80,
                "signal_id": "phase3-readiness-signal",
                "canonical_symbol": "EURUSD",
                "allocation_mode": "EQUAL",
                "total_lot": 0.03,
            }
            signal = TradingViewSignalNormalizer().normalize(payload)
            webhook_ready = signal.orchestration_ready and signal.simulation_only and not signal.live_execution_enabled
            orchestration_decision = WebhookOrchestrationService().process_signal(signal)
            if orchestration_decision.live_execution_enabled:
                issues.append("Webhook orchestration live execution flag is enabled.")
            account_service = AccountRoutingService()
            route_decision = account_service.preview_route(payload)
            allocation = account_service.preview_allocation(payload)
            queue_service = ExecutionQueueService()
            queue_items = queue_service.enqueue_preview(payload)
            lifecycle = queue_service.simulate_latest()
            monitoring = MonitoringService().get_status()
            routing_ready = route_decision.routing_ready
            allocation_ready = allocation.routing_ready
            execution_queue_ready = bool(queue_items)
            simulation_lifecycle_ready = lifecycle is not None and lifecycle.status == "SIMULATED_FILLED"
            monitoring_ready = monitoring.get("simulation_only") is True and monitoring.get("live_execution_enabled") is False
        except Exception as exc:
            issues.append(f"Pipeline validation failed safe: {exc}")
            webhook_ready = routing_ready = allocation_ready = execution_queue_ready = simulation_lifecycle_ready = monitoring_ready = False
        ready = all(
            [
                webhook_ready,
                routing_ready,
                allocation_ready,
                execution_queue_ready,
                simulation_lifecycle_ready,
                monitoring_ready,
            ]
        )
        return Phase3PipelineValidation(
            webhook_ready=webhook_ready,
            routing_ready=routing_ready,
            allocation_ready=allocation_ready,
            execution_queue_ready=execution_queue_ready,
            simulation_lifecycle_ready=simulation_lifecycle_ready,
            monitoring_ready=monitoring_ready,
            pipeline_status="READY" if ready and not issues else "WARNING" if ready else "FAILED_SAFE",
            issues=issues,
            simulation_only=True,
            live_execution_enabled=False,
        )
