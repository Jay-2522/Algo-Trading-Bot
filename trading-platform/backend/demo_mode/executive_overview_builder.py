from backend.demo_mode.demo_mode_models import ClientDemoOverview, ExecutiveKPI


class ExecutiveOverviewBuilder:
    """Build a concise client-facing demo overview from completed platform capabilities."""

    def build_kpis(self) -> list[ExecutiveKPI]:
        return [
            ExecutiveKPI(
                label="Backend Ready",
                value="Online",
                status="READY",
                description="FastAPI backend, monitoring, dashboard context, and readiness services are available.",
            ),
            ExecutiveKPI(
                label="Webhook Ready",
                value="TradingView",
                status="READY",
                description="TradingView webhook ingestion, validation, security, and orchestration bridge are prepared.",
            ),
            ExecutiveKPI(
                label="Broker Mapping Ready",
                value="3 Brokers",
                status="READY",
                description="STARTRADER, FxPro, and Vantage compatibility metadata and symbol mapping are available.",
            ),
            ExecutiveKPI(
                label="Account Routing Ready",
                value="Demo Preview",
                status="READY",
                description="EURUSD and XAUUSD can be routed to demo account previews across supported brokers.",
            ),
            ExecutiveKPI(
                label="Simulation Queue Ready",
                value="Non-Executing",
                status="ACTIVE",
                description="Execution queue and simulated lifecycle are available without broker order placement.",
            ),
            ExecutiveKPI(
                label="Live Trading",
                value="Disabled",
                status="DISABLED",
                description="Live broker execution is intentionally disabled across the platform.",
            ),
        ]

    def build_pipeline_summary(self) -> list[str]:
        return [
            "TradingView Signal",
            "AI Orchestration",
            "Risk Check",
            "Account Routing",
            "Allocation",
            "Execution Queue",
            "Simulation Lifecycle",
        ]

    def build_safety_summary(self) -> list[str]:
        return [
            "Simulation-only mode is active.",
            "Broker execution is disabled.",
            "No live orders are placed.",
            "Manual safety controls and audit trail are available.",
        ]

    def build_overview(self) -> ClientDemoOverview:
        return ClientDemoOverview(
            system_status="ONLINE",
            client_mvp_status="CLIENT_DEMO_READY",
            supported_markets=["EUR/USD", "XAU/USD", "NIFTY 50 (conditional placeholder)"],
            supported_brokers=["STARTRADER", "FxPro", "Vantage"],
            pipeline_summary=self.build_pipeline_summary(),
            safety_summary=self.build_safety_summary(),
            kpis=self.build_kpis(),
            next_steps=[
                "Demo execution bridge",
                "Indian broker integration",
                "Mumbai VPS deployment",
                "Production hardening",
                "Live execution approval workflow",
            ],
            simulation_only=True,
            live_execution_enabled=False,
        )
