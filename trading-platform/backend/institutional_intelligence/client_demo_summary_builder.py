from collections.abc import Callable
from typing import Any

from backend.institutional_intelligence.client_demo_models import (
    ClientDemoModule,
    ClientDemoReport,
    ClientDemoSummary,
)


class ClientDemoSummaryBuilder:
    """Present existing institutional outputs in short client-demo language."""

    MODULE_COPY = {
        "institutional_foundation": ("Market structure", "Maps structure, liquidity, and price location."),
        "liquidity_sweeps": ("Liquidity behavior", "Identifies price raids and rejection behavior."),
        "fair_value_gaps": ("Imbalance zones", "Highlights unfilled institutional price inefficiencies."),
        "order_blocks": ("Order blocks", "Tracks potential institutional reaction zones."),
        "breaker_blocks": ("Breaker blocks", "Recognizes failed blocks converted into new zones."),
        "structure_shift": ("Structure change", "Detects BOS, CHOCH, and MSS transitions."),
        "confluence": ("Confluence score", "Ranks evidence into a transparent setup quality view."),
        "multi_timeframe_alignment": ("Top-down alignment", "Compares macro direction with timing structure."),
        "session_killzone": ("Session timing", "Rates London and New York timing quality."),
        "entry_models": ("Entry models", "Forms structured simulation candidates."),
        "setup_validation": ("Validation gates", "Rejects weak or contradictory candidates."),
        "simulation_decision": ("Simulation decision", "Produces paper-only intent after approval."),
        "paper_trade_lifecycle": ("Paper lifecycle", "Tracks simulated entries and outcomes."),
        "position_management": ("Position management", "Protects and manages simulated positions."),
        "institutional_orchestration": ("Orchestration", "Coordinates the complete analytical pipeline."),
        "ai_reasoning": ("Market narrative", "Explains state and action in clear language."),
        "performance_analytics": ("Performance analytics", "Reviews simulated outcomes and improvements."),
        "dashboard_context": ("Dashboard context", "Delivers concise decision-ready cards."),
        "phase2_completion": ("Completion audit", "Certifies route coverage and safety controls."),
    }

    def __init__(
        self,
        dashboard_provider: Callable[[str, str], Any] | None = None,
        reasoning_provider: Callable[[str, str], Any] | None = None,
        phase2_provider: Callable[[], Any] | None = None,
    ) -> None:
        self.dashboard_provider = dashboard_provider
        self.reasoning_provider = reasoning_provider
        self.phase2_provider = phase2_provider

    def build_demo_summary(
        self,
        symbol: str,
        timeframe: str,
        dashboard_context: Any = None,
        reasoning_report: Any = None,
        phase2_report: Any = None,
    ) -> ClientDemoSummary:
        dashboard = dashboard_context or self._provide(self.dashboard_provider, symbol, timeframe)
        reasoning = reasoning_report or self._provide(self.reasoning_provider, symbol, timeframe)
        phase2 = phase2_report or self._provide(self.phase2_provider)
        recommendation = self._get(self._get(dashboard, "final_recommendation"), "action", "MONITOR")
        dashboard_status = self._get(dashboard, "dashboard_status", "INACTIVE")
        state = dashboard_status
        narrative = self._get(reasoning, "narrative")
        institutional_bias = self._get(narrative, "institutional_bias", "UNCLEAR")
        confidence = float(self._get(reasoning, "confidence", 0.0) or 0.0)
        explanation = self._explanation(recommendation, self._get(narrative, "headline", ""))
        safety = self._get(phase2, "safety_audit")
        safety_status = (
            "Simulation-only safeguards verified; broker execution remains disabled."
            if self._get(safety, "passed", False)
            else "Safety verification requires review before demonstration."
        )
        strengths = list(self._get(narrative, "key_drivers", []) or [])[:3]
        risks = list(self._get(narrative, "risks", []) or [])[:3]
        return ClientDemoSummary(
            symbol=symbol.strip().upper(),
            timeframe=timeframe.strip().upper(),
            system_status=state,
            institutional_bias=institutional_bias,
            dashboard_status=dashboard_status,
            recommendation=recommendation,
            confidence=confidence,
            explanation=explanation,
            key_strengths=strengths,
            key_risks=risks,
            safety_status=safety_status,
        )

    def build_demo_modules(self, phase2_report: Any = None) -> list[ClientDemoModule]:
        phase2 = phase2_report or self._provide(self.phase2_provider)
        statuses = self._get(phase2, "module_statuses", []) or []
        modules: list[ClientDemoModule] = []
        for status in statuses:
            name = self._get(status, "module_name", "unknown")
            purpose, client_value = self.MODULE_COPY.get(
                name, (name.replace("_", " ").title(), "Supports institutional analysis.")
            )
            modules.append(
                ClientDemoModule(
                    module_name=name,
                    status=self._get(status, "status", "NOT_AVAILABLE"),
                    purpose=purpose,
                    client_value=client_value,
                )
            )
        return modules

    def build_demo_report(
        self,
        symbol: str,
        timeframe: str,
        dashboard_context: Any = None,
        reasoning_report: Any = None,
        phase2_report: Any = None,
    ) -> ClientDemoReport:
        phase2 = phase2_report or self._provide(self.phase2_provider)
        summary = self.build_demo_summary(symbol, timeframe, dashboard_context, reasoning_report, phase2)
        modules = self.build_demo_modules(phase2)
        safe = (
            summary.simulation_only
            and not summary.live_execution_enabled
            and self._get(phase2, "overall_status", "WARNING") == "READY"
            and self._get(self._get(phase2, "safety_audit"), "passed", False)
        )
        return ClientDemoReport(
            summary=summary,
            modules=modules,
            demo_talking_points=[
                "The system reads institutional structure and ranks simulation opportunities.",
                "Validation gates can reject or delay low-quality conditions.",
                "All displayed actions are simulation-only; broker execution remains disabled.",
            ],
            safe_to_demo=safe,
        )

    def _explanation(self, recommendation: str, headline: str) -> str:
        copy = {
            "READY_FOR_SIMULATION": "Ready for simulation. Risk and structure gates passed.",
            "WAIT": "Wait for confirmation. Setup quality is not ready.",
            "AVOID": "Avoid simulation now. Institutional conditions are not fully aligned.",
            "MANAGE_POSITION": "Manage the current paper position under protection rules.",
            "REVIEW_SYSTEM": "Review system status before demonstrating a decision.",
            "MONITOR": "Monitor conditions. No approved simulated setup is present.",
        }
        return copy.get(recommendation, headline or "Institutional conditions are under monitoring.")

    def _provide(self, provider: Callable | None, *args):
        return provider(*args) if provider is not None else None

    def _get(self, value: Any, key: str, default: Any = None) -> Any:
        if value is None:
            return default
        return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)
