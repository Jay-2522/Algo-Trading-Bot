from datetime import datetime, timezone
from uuid import uuid4

from backend.execution_engine.execution_logger import ExecutionLogger
from backend.execution_engine.execution_models import (
    ExecutionLog,
    ExecutionResult,
    ExecutionStatus,
    OrderRequest,
    OrderValidationResult,
)
from backend.execution_engine.mt5_executor import MT5Executor
from backend.execution_engine.order_validator import OrderValidator
from backend.execution_engine.simulated_executor import SimulatedExecutor
from backend.risk_engine.risk_models import RiskCheckRequest
from backend.risk_engine.risk_service import RiskService, get_risk_service


class ExecutionService:
    """Simulation-only execution workflow gated by existing risk controls."""

    def __init__(
        self,
        risk_service: RiskService | None = None,
        logger: ExecutionLogger | None = None,
    ) -> None:
        self.order_validator = OrderValidator()
        self.simulated_executor = SimulatedExecutor()
        self.mt5_executor = MT5Executor()
        self.execution_logger = logger or ExecutionLogger()
        self.risk_service = risk_service or get_risk_service()
        self._statuses: dict[str, ExecutionStatus] = {}

    def validate_order(self, order: OrderRequest) -> OrderValidationResult:
        return self.order_validator.validate_order(order)

    def simulate_order(self, order: OrderRequest) -> ExecutionResult:
        """Validate, risk-check, and simulate; no broker request can occur here."""

        validation = self.validate_order(order)
        if not validation.valid:
            result = self._failed_result(order, "VALIDATION_FAILED", "; ".join(validation.errors))
            self.execution_logger.log_event(
                result.execution_id,
                "VALIDATION_FAILED",
                result.message,
                {"errors": validation.errors, "warnings": validation.warnings},
            )
            self._record_status(result)
            return result

        provisional_id = str(uuid4())
        self.execution_logger.log_event(
            provisional_id,
            "VALIDATED",
            "Order request passed execution validation.",
            {"warnings": validation.warnings},
        )
        risk_check = self.risk_service.evaluate_trade_permission(
            RiskCheckRequest(
                symbol=order.symbol.strip().upper(),
                account_balance=10000,
                current_drawdown_percent=0,
                consecutive_losses=0,
                current_spread=10,
                expected_slippage=2,
            )
        )
        self.execution_logger.log_event(
            provisional_id,
            "RISK_CHECK",
            "Risk permission evaluated before simulation.",
            risk_check.model_dump(mode="json"),
        )
        if not risk_check.allowed:
            result = self._failed_result(order, "RISK_BLOCKED", "; ".join(risk_check.reasons), provisional_id)
            self.execution_logger.log_event(
                provisional_id,
                "SIMULATION_BLOCKED",
                result.message,
                {"risk_level": risk_check.risk_level},
            )
            self._record_status(result)
            return result

        result = self.simulated_executor.execute(order)
        self._move_provisional_logs(provisional_id, result.execution_id)
        self.execution_logger.log_event(
            result.execution_id,
            "SIMULATED_EXECUTION",
            result.message,
            {"execution_mode": result.execution_mode, "status": result.status},
        )
        self._record_status(result)
        return result

    def prepare_mt5_order(self, order: OrderRequest) -> dict:
        """Prepare a disabled live-execution preview after validating the order."""

        validation = self.validate_order(order)
        if not validation.valid:
            return {
                "prepared": False,
                "validation": validation.model_dump(mode="json"),
                "message": "Order payload was not prepared because validation failed.",
            }
        return {
            "prepared": True,
            "validation": validation.model_dump(mode="json"),
            "payload": self.mt5_executor.prepare_order_payload(order),
            "message": "MT5 payload preview only. Real execution is disabled.",
        }

    def get_execution_logs(self, execution_id: str) -> list[ExecutionLog]:
        return self.execution_logger.get_logs(execution_id)

    def get_recent_logs(self, limit: int = 50) -> list[ExecutionLog]:
        return self.execution_logger.get_recent_logs(limit)

    def get_execution_status(self, execution_id: str) -> ExecutionStatus | None:
        return self._statuses.get(execution_id)

    def _failed_result(
        self,
        order: OrderRequest,
        status: str,
        message: str,
        execution_id: str | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            execution_id=execution_id or str(uuid4()),
            symbol=order.symbol.strip().upper(),
            side=order.side.strip().upper(),
            lot_size=order.lot_size,
            execution_mode="SIMULATION",
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _record_status(self, result: ExecutionResult) -> None:
        self._statuses[result.execution_id] = ExecutionStatus(
            execution_id=result.execution_id,
            status=result.status,
            symbol=result.symbol,
            side=result.side,
            created_at=result.timestamp,
            updated_at=result.timestamp,
        )

    def _move_provisional_logs(self, provisional_id: str, execution_id: str) -> None:
        for log in self.execution_logger.get_logs(provisional_id):
            log.execution_id = execution_id

