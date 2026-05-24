from typing import Any, Dict

from backend.risk_engine.validators import validate_spread


class SpreadGuard:
    """Block future trading permission when spread conditions are unsafe."""

    def check_spread(self, current_spread: float, max_allowed_spread: float) -> Dict[str, Any]:
        validate_spread(current_spread)
        validate_spread(max_allowed_spread)

        if current_spread > max_allowed_spread:
            return {
                "allowed": False,
                "reason": "Current spread exceeds the permitted limit.",
                "severity": "BLOCKED",
            }
        return {
            "allowed": True,
            "reason": "Current spread is within limit.",
            "severity": "LOW",
        }

