from typing import Any

from backend.demo_execution.demo_execution_models import DemoExecutionRequest
from backend.demo_execution.mt5_demo_executor import MT5DemoExecutor
from backend.execution_queue.execution_queue_models import ExecutionIntent, ExecutionQueueItem
from backend.execution_queue.execution_audit_logger import ExecutionAuditLogger
from backend.multi_account_execution.account_execution_planner import AccountExecutionPlanner
from backend.multi_account_execution.multi_account_execution_guard import MultiAccountExecutionGuard
from backend.multi_account_execution.multi_account_models import (
    AccountDemoExecutionPlan,
    AccountExecutionResult,
    MultiAccountDemoExecutionResult,
)
from backend.multi_account_execution.multi_account_result_store import MultiAccountResultStore


class MultiAccountDemoExecutor:
    """Route one signal into guarded per-account MT5 demo execution attempts."""

    def __init__(
        self,
        planner: AccountExecutionPlanner | None = None,
        guard: MultiAccountExecutionGuard | None = None,
        demo_executor: MT5DemoExecutor | None = None,
        result_store: MultiAccountResultStore | None = None,
        audit_logger: ExecutionAuditLogger | None = None,
    ) -> None:
        self.result_store = result_store or MultiAccountResultStore()
        self.planner = planner or AccountExecutionPlanner()
        self.guard = guard or MultiAccountExecutionGuard(result_store=self.result_store)
        self.demo_executor = demo_executor or MT5DemoExecutor()
        self.audit_logger = audit_logger or ExecutionAuditLogger()

    def execute_batch(self, signal_payload: dict[str, Any]) -> MultiAccountDemoExecutionResult:
        plans = self.planner.build_plans(signal_payload)
        account_results: list[AccountExecutionResult] = []
        attempted_terminal = False
        for plan in plans[:3]:
            self._audit(plan, "MULTI_ACCOUNT_DEMO_ATTEMPT_REQUESTED", "Per-account demo routing attempt requested.")
            if self.result_store.has_account_execution(plan.signal_id, plan.account_id):
                result = self._account_result(plan, "SKIPPED_DUPLICATE", ["Duplicate demo execution attempt for this signal/account is blocked."])
                account_results.append(result)
                self._audit(plan, "MULTI_ACCOUNT_DEMO_DUPLICATE_BLOCKED", "Duplicate per-account demo execution blocked.")
                continue

            allowed, reasons = self.guard.validate_plan(plan)
            if not allowed:
                result = self._account_result(plan, "BLOCKED", reasons)
                account_results.append(result)
                self._audit(plan, "MULTI_ACCOUNT_DEMO_BLOCKED", "; ".join(reasons) or "Plan blocked.")
                continue

            if attempted_terminal:
                result = self._account_result(
                    plan,
                    "MT5_UNAVAILABLE",
                    ["Only one connected MT5 demo terminal can be attempted safely in Phase 5 Day 3."],
                )
                account_results.append(result)
                self._audit(plan, "MULTI_ACCOUNT_DEMO_MT5_UNAVAILABLE", result.rejection_reasons[0])
                continue

            attempted_terminal = True
            demo_result = self.demo_executor.execute_demo_order(
                self._queue_item_from_plan(plan),
                DemoExecutionRequest(
                    queue_id=f"multi_{plan.plan_id}",
                    confirm_demo_execution=bool(signal_payload.get("confirm_demo_execution")),
                    requested_by=str(signal_payload.get("requested_by") or "multi_account_demo"),
                    reason=str(signal_payload.get("reason") or "Multi-account demo execution batch."),
                ),
            )
            account_result = AccountExecutionResult(
                account_id=plan.account_id,
                broker_id=plan.broker_id,
                status=demo_result.status,
                mt5_retcode=demo_result.mt5_retcode,
                mt5_order=demo_result.mt5_order,
                mt5_deal=demo_result.mt5_deal,
                rejection_reasons=demo_result.rejection_reasons,
            )
            account_results.append(account_result)
            self._audit(plan, f"MULTI_ACCOUNT_DEMO_{demo_result.status}", "; ".join(demo_result.rejection_reasons) or demo_result.status)

        batch = MultiAccountDemoExecutionResult(
            signal_id=str(signal_payload.get("signal_id") or "multi-account-demo"),
            canonical_symbol=plans[0].canonical_symbol if plans else str(signal_payload.get("canonical_symbol") or ""),
            action=plans[0].action if plans else str(signal_payload.get("action") or ""),
            total_targets=len(plans[:3]),
            attempted=len([result for result in account_results if result.status in {"DEMO_FILLED", "DEMO_REJECTED", "MT5_UNAVAILABLE"}]),
            filled=len([result for result in account_results if result.status == "DEMO_FILLED"]),
            rejected=len([result for result in account_results if result.status == "DEMO_REJECTED"]),
            blocked=len([result for result in account_results if result.status in {"BLOCKED", "SKIPPED_DUPLICATE", "FAILED_SAFE"}]),
            account_results=account_results,
            warnings=["Multi-account demo routing only. Live and broker execution remain disabled."],
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        return self.result_store.store_result(batch)

    def _queue_item_from_plan(self, plan: AccountDemoExecutionPlan) -> ExecutionQueueItem:
        intent = ExecutionIntent(
            signal_id=plan.signal_id,
            account_id=plan.account_id,
            broker_id=plan.broker_id,
            canonical_symbol=plan.canonical_symbol,
            broker_symbol=plan.broker_symbol,
            action=plan.action,
            allocated_lot=plan.lot,
            order_type="MARKET",
            simulation_only=True,
            live_execution_enabled=False,
        )
        return ExecutionQueueItem(
            intent=intent,
            status="QUEUED",
            readiness="READY_FOR_DEMO_QUEUE",
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _account_result(self, plan: AccountDemoExecutionPlan, status: str, reasons: list[str]) -> AccountExecutionResult:
        return AccountExecutionResult(
            account_id=plan.account_id,
            broker_id=plan.broker_id,
            status=status,
            rejection_reasons=reasons,
        )

    def _audit(self, plan: AccountDemoExecutionPlan, event_type: str, message: str) -> None:
        self.audit_logger.log_event(
            plan.plan_id,
            event_type,
            message,
            {
                "signal_id": plan.signal_id,
                "account_id": plan.account_id,
                "broker_id": plan.broker_id,
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            },
        )
