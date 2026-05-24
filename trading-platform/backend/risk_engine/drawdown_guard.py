from typing import Any, Dict

from backend.risk_engine.validators import validate_drawdown


class DrawdownGuard:
    """Block future trading permission at the configured daily drawdown limit."""

    def check_daily_drawdown(
        self,
        current_drawdown_percent: float,
        max_daily_drawdown_percent: float,
    ) -> Dict[str, Any]:
        validate_drawdown(current_drawdown_percent)
        validate_drawdown(max_daily_drawdown_percent)

        if current_drawdown_percent >= max_daily_drawdown_percent:
            return {
                "allowed": False,
                "reason": "Daily drawdown limit reached or exceeded.",
                "severity": "BLOCKED",
            }
        return {
            "allowed": True,
            "reason": "Daily drawdown is within limit.",
            "severity": "LOW",
        }

