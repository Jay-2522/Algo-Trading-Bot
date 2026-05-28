from pathlib import Path


class Phase3SafetyAuditor:
    """Scan Phase 3/backend code for forbidden live-execution patterns."""

    FORBIDDEN = (
        "mt5." + "order_send",
        "order_" + "send(",
        "live_execution_enabled" + "=True",
        "real_trading_enabled" + "=True",
        "enable_live_" + "trading",
    )

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2]

    def run_safety_audit(self):
        from backend.phase3_readiness.phase3_readiness_models import Phase3SafetyAudit

        warnings: list[str] = []
        for path in (self.root / "backend").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in self.FORBIDDEN:
                if pattern in text:
                    warnings.append(f"{pattern} found in {path.relative_to(self.root)}")
        order_token = "order_" + "send"
        live_token = "live_execution_enabled" + "=True"
        real_trading_token = "real_trading_enabled"
        live_trading_token = "enable_live_" + "trading"
        no_order_send = not any(order_token in warning for warning in warnings)
        live_disabled = not any(live_token in warning for warning in warnings)
        broker_disabled = not any(
            real_trading_token in warning or live_trading_token in warning for warning in warnings
        )
        simulation_confirmed = no_order_send and live_disabled and broker_disabled
        return Phase3SafetyAudit(
            no_order_send_detected=no_order_send,
            live_execution_disabled=live_disabled,
            broker_execution_disabled=broker_disabled,
            simulation_only_confirmed=simulation_confirmed,
            safety_status="PASSED" if simulation_confirmed else "FAILED",
            warnings=warnings,
        )
