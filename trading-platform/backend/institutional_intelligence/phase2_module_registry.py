from collections.abc import Iterable

from backend.institutional_intelligence.phase2_completion_models import Phase2ModuleStatus


class Phase2ModuleRegistry:
    """Describe each completed institutional module and its primary API contract."""

    MODULE_ROUTES = [
        ("institutional_foundation", "/institutional/context/{symbol}"),
        ("liquidity_sweeps", "/institutional/sweeps/{symbol}"),
        ("fair_value_gaps", "/institutional/fvg/{symbol}"),
        ("order_blocks", "/institutional/order-blocks/{symbol}"),
        ("breaker_blocks", "/institutional/breakers/{symbol}"),
        ("structure_shift", "/institutional/structure-shift/{symbol}"),
        ("confluence", "/institutional/confluence/{symbol}"),
        ("multi_timeframe_alignment", "/institutional/alignment/{symbol}"),
        ("session_killzone", "/institutional/session/{symbol}"),
        ("entry_models", "/institutional/entry-models/{symbol}"),
        ("setup_validation", "/institutional/setup-validation/{symbol}"),
        ("simulation_decision", "/institutional/simulation-decision/{symbol}"),
        ("paper_trade_lifecycle", "/institutional/paper-trades/{symbol}"),
        ("position_management", "/institutional/position-management/{symbol}"),
        ("institutional_orchestration", "/institutional/orchestration/{symbol}"),
        ("ai_reasoning", "/institutional/reasoning/{symbol}"),
        ("performance_analytics", "/institutional/performance/{symbol}"),
        ("dashboard_context", "/institutional/dashboard/{symbol}"),
        ("phase2_completion", "/institutional/phase2/status"),
    ]

    def primary_routes(self) -> list[str]:
        return [route for _, route in self.MODULE_ROUTES]

    def get_module_statuses(self, app_routes: Iterable[str] | None = None) -> list[Phase2ModuleStatus]:
        routes = set(app_routes or [])
        statuses: list[Phase2ModuleStatus] = []
        for module_name, route in self.MODULE_ROUTES:
            available = route in routes
            statuses.append(
                Phase2ModuleStatus(
                    module_name=module_name,
                    route_available=available,
                    status="READY" if available else "NOT_AVAILABLE",
                    message=(
                        f"Primary route {route} is registered."
                        if available
                        else f"Primary route {route} is not registered."
                    ),
                )
            )
        return statuses
