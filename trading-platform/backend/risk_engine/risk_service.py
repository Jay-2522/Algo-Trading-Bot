from typing import Any, Dict

from backend.risk_engine.drawdown_guard import DrawdownGuard
from backend.risk_engine.kill_switch import KillSwitch
from backend.risk_engine.loss_guard import ConsecutiveLossGuard
from backend.risk_engine.position_sizer import PositionSizer
from backend.risk_engine.risk_config import get_default_risk_config
from backend.risk_engine.risk_models import (
    PositionSizeRequest,
    PositionSizeResponse,
    RiskCheckRequest,
    RiskCheckResponse,
    RiskConfig,
    RiskStatus,
)
from backend.risk_engine.spread_guard import SpreadGuard
from backend.risk_engine.validators import validate_positive_number, validate_slippage


class RiskService:
    """Central analysis-only risk policy service for future execution gating."""

    def __init__(
        self,
        config: RiskConfig | None = None,
        kill_switch: KillSwitch | None = None,
    ) -> None:
        self.config = config or get_default_risk_config()
        self.position_sizer = PositionSizer()
        self.drawdown_guard = DrawdownGuard()
        self.loss_guard = ConsecutiveLossGuard()
        self.spread_guard = SpreadGuard()
        self.kill_switch = kill_switch or KillSwitch()
        self._last_checks = {
            "daily_drawdown_ok": True,
            "consecutive_losses_ok": True,
            "spread_ok": True,
            "slippage_ok": True,
        }

    def calculate_position_size(self, request: PositionSizeRequest) -> PositionSizeResponse:
        """Calculate size while enforcing the centralized risk-per-trade ceiling."""

        if request.risk_percent > self.config.max_risk_per_trade_percent:
            raise ValueError(
                f"Risk percent exceeds configured maximum of {self.config.max_risk_per_trade_percent}%."
            )
        return self.position_sizer.calculate_lot_size(
            request.account_balance,
            request.risk_percent,
            request.stop_loss_pips,
            request.pip_value,
        )

    def evaluate_trade_permission(self, request: RiskCheckRequest) -> RiskCheckResponse:
        """Evaluate safety controls only; this never submits an order."""

        validate_positive_number(request.account_balance, "Account balance")
        validate_slippage(request.expected_slippage)

        drawdown = self.drawdown_guard.check_daily_drawdown(
            request.current_drawdown_percent,
            self.config.max_daily_drawdown_percent,
        )
        losses = self.loss_guard.check_consecutive_losses(
            request.consecutive_losses,
            self.config.max_consecutive_losses,
        )
        spread = self.spread_guard.check_spread(
            request.current_spread,
            self.config.max_allowed_spread,
        )
        slippage = self._check_slippage(request.expected_slippage)

        self._last_checks = {
            "daily_drawdown_ok": drawdown["allowed"],
            "consecutive_losses_ok": losses["allowed"],
            "spread_ok": spread["allowed"],
            "slippage_ok": slippage["allowed"],
        }

        reasons: list[str] = []
        if self.kill_switch.is_active():
            reasons.append("Emergency kill switch is active.")
        if not self.config.trading_enabled:
            reasons.append("Trading is disabled by risk configuration.")
        for check in (drawdown, losses, spread, slippage):
            if not check["allowed"]:
                reasons.append(check["reason"])

        allowed = not reasons
        return RiskCheckResponse(
            allowed=allowed,
            reasons=reasons or ["All risk controls passed."],
            risk_level=self._risk_level(request, allowed),
        )

    def get_risk_status(self) -> RiskStatus:
        """Report operational risk readiness and most recently evaluated checks."""

        blocked = (
            not self.config.trading_enabled
            or self.kill_switch.is_active()
            or not all(self._last_checks.values())
        )
        return RiskStatus(
            trading_enabled=self.config.trading_enabled,
            kill_switch_active=self.kill_switch.is_active(),
            daily_drawdown_ok=self._last_checks["daily_drawdown_ok"],
            consecutive_losses_ok=self._last_checks["consecutive_losses_ok"],
            spread_ok=self._last_checks["spread_ok"],
            slippage_ok=self._last_checks["slippage_ok"],
            overall_status="BLOCKED" if blocked else "OPERATIONAL",
        )

    def activate_kill_switch(self, reason: str) -> Dict[str, Any]:
        return self.kill_switch.activate(reason)

    def deactivate_kill_switch(self) -> Dict[str, Any]:
        return self.kill_switch.deactivate()

    def _check_slippage(self, expected_slippage: float) -> Dict[str, Any]:
        if expected_slippage > self.config.max_allowed_slippage:
            return {
                "allowed": False,
                "reason": "Expected slippage exceeds the permitted limit.",
                "severity": "BLOCKED",
            }
        return {
            "allowed": True,
            "reason": "Expected slippage is within limit.",
            "severity": "LOW",
        }

    def _risk_level(self, request: RiskCheckRequest, allowed: bool) -> str:
        if not allowed:
            return "BLOCKED"

        utilization = [
            request.current_drawdown_percent / self.config.max_daily_drawdown_percent,
            request.consecutive_losses / self.config.max_consecutive_losses,
            request.current_spread / self.config.max_allowed_spread,
            request.expected_slippage / self.config.max_allowed_slippage,
        ]
        highest_utilization = max(utilization)
        if highest_utilization >= 0.9:
            return "HIGH"
        if highest_utilization >= 0.75:
            return "MEDIUM"
        return "LOW"

