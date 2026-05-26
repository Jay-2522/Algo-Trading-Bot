import json

from backend.institutional_intelligence.institutional_orchestration_models import (
    InstitutionalHealthResult,
    InstitutionalOrchestrationReport,
)


class InstitutionalHealthChecker:
    """Check report completeness and the non-negotiable simulation-only boundary."""

    def check_institutional_health(self, report: InstitutionalOrchestrationReport) -> InstitutionalHealthResult:
        failed = [step.step_name for step in report.pipeline_steps if step.status == "FAILED"]
        warnings: list[str] = []
        try:
            json.dumps(report.model_dump(mode="json"))
            json_safe = True
        except (TypeError, ValueError):
            json_safe = False
            warnings.append("Report serialization failed JSON-safe readiness validation.")
        safety_ok = report.simulation_only and not report.live_execution_enabled
        if not safety_ok:
            warnings.append("Orchestration safety flags violate simulation-only policy.")
        route_ready = len(report.pipeline_steps) == 14
        if not route_ready:
            warnings.append("Institutional pipeline step inventory is incomplete.")
        if failed:
            warnings.append(f"{len(failed)} pipeline step(s) failed safely.")
        passed = safety_ok and json_safe and route_ready and not failed
        status = "HEALTHY" if passed else ("SAFE_MODE" if not safety_ok or not json_safe else "DEGRADED")
        return InstitutionalHealthResult(
            status=status,
            passed=passed,
            available_steps=sum(1 for step in report.pipeline_steps if step.success),
            failed_steps=failed,
            simulation_only=report.simulation_only,
            live_execution_enabled=report.live_execution_enabled,
            json_safe=json_safe,
            route_ready=route_ready,
            warnings=warnings,
            metadata={"pipeline_step_count": len(report.pipeline_steps)},
        )
