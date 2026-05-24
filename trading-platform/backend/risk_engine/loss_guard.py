from typing import Any, Dict


class ConsecutiveLossGuard:
    """Protect against continued activity after a losing sequence."""

    def check_consecutive_losses(self, current_losses: int, max_allowed_losses: int) -> Dict[str, Any]:
        if current_losses < 0:
            raise ValueError("Current consecutive losses cannot be negative.")
        if max_allowed_losses <= 0:
            raise ValueError("Maximum allowed losses must be greater than zero.")

        if current_losses >= max_allowed_losses:
            return {
                "allowed": False,
                "reason": "Maximum consecutive losses reached or exceeded.",
                "severity": "BLOCKED",
            }
        return {
            "allowed": True,
            "reason": "Consecutive losses are within limit.",
            "severity": "LOW",
        }

