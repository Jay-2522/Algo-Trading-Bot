from collections.abc import Iterable

from backend.institutional_intelligence.phase2_completion_models import Phase2ReadinessReport
from backend.institutional_intelligence.phase2_module_registry import Phase2ModuleRegistry
from backend.institutional_intelligence.phase2_safety_auditor import Phase2SafetyAuditor


class Phase2ReadinessChecker:
    """Validate the complete institutional API surface and its safety boundary."""

    REQUIRED_INSTITUTIONAL_ROUTES = [
        "/institutional/status",
        "/institutional/context/{symbol}",
        "/institutional/swings/{symbol}",
        "/institutional/liquidity/{symbol}",
        "/institutional/bias/{symbol}",
        "/institutional/premium-discount/{symbol}",
        "/institutional/displacement/{symbol}",
        "/institutional/sweeps/{symbol}",
        "/institutional/latest-sweep/{symbol}",
        "/institutional/high-quality-sweeps/{symbol}",
        "/institutional/fvg/{symbol}",
        "/institutional/fvg/fresh/{symbol}",
        "/institutional/fvg/mitigated/{symbol}",
        "/institutional/fvg/high-quality/{symbol}",
        "/institutional/fvg/latest/{symbol}",
        "/institutional/order-blocks/{symbol}",
        "/institutional/order-blocks/fresh/{symbol}",
        "/institutional/order-blocks/mitigated/{symbol}",
        "/institutional/order-blocks/high-quality/{symbol}",
        "/institutional/order-blocks/latest/{symbol}",
        "/institutional/order-blocks/context/{symbol}",
        "/institutional/breakers/{symbol}",
        "/institutional/breakers/fresh/{symbol}",
        "/institutional/breakers/mitigated/{symbol}",
        "/institutional/breakers/high-quality/{symbol}",
        "/institutional/breakers/latest/{symbol}",
        "/institutional/breakers/context/{symbol}",
        "/institutional/structure-shift/{symbol}",
        "/institutional/structure-shift/bos/{symbol}",
        "/institutional/structure-shift/choch/{symbol}",
        "/institutional/structure-shift/mss/{symbol}",
        "/institutional/structure-shift/latest/{symbol}",
        "/institutional/structure-shift/high-quality/{symbol}",
        "/institutional/structure-shift/context/{symbol}",
        "/institutional/confluence/{symbol}",
        "/institutional/confluence/score/{symbol}",
        "/institutional/confluence/explanation/{symbol}",
        "/institutional/confluence/components/{symbol}",
        "/institutional/confluence/readiness/{symbol}",
        "/institutional/alignment/{symbol}",
        "/institutional/alignment/narrative/{symbol}",
        "/institutional/alignment/conflicts/{symbol}",
        "/institutional/alignment/timeframes/{symbol}",
        "/institutional/session/{symbol}",
        "/institutional/session/ranges/{symbol}",
        "/institutional/session/killzone/{symbol}",
        "/institutional/session/liquidity/{symbol}",
        "/institutional/session/manipulation/{symbol}",
        "/institutional/session/readiness/{symbol}",
        "/institutional/entry-models/{symbol}",
        "/institutional/entry-models/best/{symbol}",
        "/institutional/entry-models/ready/{symbol}",
        "/institutional/entry-models/waiting/{symbol}",
        "/institutional/entry-models/avoided/{symbol}",
        "/institutional/entry-models/explanation/{symbol}",
        "/institutional/setup-validation/{symbol}",
        "/institutional/setup-validation/approved/{symbol}",
        "/institutional/setup-validation/waiting/{symbol}",
        "/institutional/setup-validation/rejected/{symbol}",
        "/institutional/setup-validation/best/{symbol}",
        "/institutional/setup-validation/readiness/{symbol}",
        "/institutional/simulation-decision/{symbol}",
        "/institutional/simulation-decision/action/{symbol}",
        "/institutional/simulation-decision/intent/{symbol}",
        "/institutional/simulation-decision/explanation/{symbol}",
        "/institutional/simulation-decision/readiness/{symbol}",
        "/institutional/paper-trades/{symbol}",
        "/institutional/paper-trades/candidates/{symbol}",
        "/institutional/paper-trades/active/{symbol}",
        "/institutional/paper-trades/closed/{symbol}",
        "/institutional/paper-trades/latest/{symbol}",
        "/institutional/paper-trades/summary/{symbol}",
        "/institutional/position-management/{symbol}",
        "/institutional/position-management/active/{symbol}",
        "/institutional/position-management/exits/{symbol}",
        "/institutional/position-management/emergency/{symbol}",
        "/institutional/position-management/state/{symbol}",
        "/institutional/position-management/context/{symbol}",
        "/institutional/orchestration/{symbol}",
        "/institutional/orchestration/state/{symbol}",
        "/institutional/orchestration/report/{symbol}",
        "/institutional/orchestration/summary/{symbol}",
        "/institutional/orchestration/health/{symbol}",
        "/institutional/reasoning/{symbol}",
        "/institutional/reasoning/narrative/{symbol}",
        "/institutional/reasoning/summary/{symbol}",
        "/institutional/reasoning/dashboard/{symbol}",
        "/institutional/reasoning/quality/{symbol}",
        "/institutional/performance/{symbol}",
        "/institutional/performance/setups/{symbol}",
        "/institutional/performance/decisions/{symbol}",
        "/institutional/performance/paper-trades/{symbol}",
        "/institutional/performance/position-management/{symbol}",
        "/institutional/performance/recommendations/{symbol}",
        "/institutional/dashboard/{symbol}",
        "/institutional/dashboard/cards/{symbol}",
        "/institutional/dashboard/alerts/{symbol}",
        "/institutional/dashboard/recommendation/{symbol}",
        "/institutional/dashboard/status/{symbol}",
        "/institutional/phase2/status",
        "/institutional/phase2/readiness",
        "/institutional/phase2/safety-audit",
        "/institutional/phase2/completion-report",
        "/institutional/phase2/modules",
        "/institutional/demo/{symbol}",
        "/institutional/demo/summary/{symbol}",
        "/institutional/demo/modules/{symbol}",
        "/institutional/demo/talking-points/{symbol}",
    ]

    def __init__(
        self,
        registry: Phase2ModuleRegistry | None = None,
        safety_auditor: Phase2SafetyAuditor | None = None,
    ) -> None:
        self.registry = registry or Phase2ModuleRegistry()
        self.safety_auditor = safety_auditor or Phase2SafetyAuditor()

    def check_readiness(self, app_routes: Iterable[str] | None = None) -> Phase2ReadinessReport:
        routes = sorted(set(app_routes or []))
        institutional_routes = [route for route in routes if route.startswith("/institutional/")]
        missing = sorted(set(self.REQUIRED_INSTITUTIONAL_ROUTES) - set(institutional_routes))
        module_statuses = self.registry.get_module_statuses(institutional_routes)
        safety = self.safety_auditor.run_safety_audit()
        completed = [module.module_name for module in module_statuses if module.status == "READY"]
        modules_ready = len(completed) == len(module_statuses)
        if not safety.passed:
            overall_status = "FAILED"
        elif missing or not modules_ready:
            overall_status = "WARNING"
        else:
            overall_status = "READY"
        summary = (
            "Phase 2 Institutional Intelligence Layer is complete in simulation-only mode."
            if overall_status == "READY"
            else "Phase 2 institutional readiness requires review before simulation-only completion is certified."
        )
        return Phase2ReadinessReport(
            overall_status=overall_status,
            completed_modules=completed,
            module_statuses=module_statuses,
            total_routes=len(routes),
            institutional_routes=institutional_routes,
            missing_routes=missing,
            safety_audit=safety,
            dashboard_ready="/institutional/dashboard/{symbol}" in institutional_routes,
            reasoning_ready="/institutional/reasoning/{symbol}" in institutional_routes,
            orchestration_ready="/institutional/orchestration/{symbol}" in institutional_routes,
            performance_ready="/institutional/performance/{symbol}" in institutional_routes,
            simulation_only=safety.passed,
            live_execution_enabled=safety.live_execution_enabled,
            summary=summary,
        )
