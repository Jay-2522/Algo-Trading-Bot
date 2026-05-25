from backend.system_health.health_models import PhaseCompletionReport, SystemReadiness


class PhaseReportBuilder:
    """Build the final backend-foundation delivery statement."""

    COMPLETED_DAYS = [f"Day {day}" for day in range(1, 16)]
    COMPLETED_MODULES = [
        "FastAPI backend foundation",
        "Market Data Engine",
        "Strategy Engine",
        "Risk Management Engine",
        "Execution Engine Foundation",
        "MT5 Broker Data Layer",
        "Database Persistence",
        "AI Decision Engine",
        "News Intelligence",
        "Trading Orchestration",
        "Backtesting Engine",
        "Live Streaming Engine",
        "Background Trading Loop",
        "Trade Journal + Advanced Risk Analytics",
        "System Health + Hardening",
    ]
    REMAINING_ITEMS = [
        "frontend dashboard",
        "paper trading governance",
        "Indian broker integration",
        "external news feed integration",
        "VPS deployment",
        "production auth",
        "live trading approval workflow",
    ]

    def build(self, readiness: SystemReadiness) -> PhaseCompletionReport:
        safety_status = "PASSED" if readiness.safety_passed else "FAILED"
        return PhaseCompletionReport(
            phase="PHASE_1_BACKEND_FOUNDATION",
            completed_days=self.COMPLETED_DAYS,
            completed_modules=self.COMPLETED_MODULES,
            remaining_items=self.REMAINING_ITEMS,
            safety_status=safety_status,
            readiness_status=readiness.overall_status,
            summary=(
                "Phase 1 backend foundation is complete in simulation-only mode."
                if readiness.overall_status == "READY"
                else "Phase 1 backend components exist but readiness findings require review."
            ),
        )
