from backend.operational_intelligence.operational_models import OperationalModuleStatus, WarningSummary


class WarningEngine:
    """Generate operational warnings from module state and known integration boundaries."""

    def build_warnings(self, module_statuses: list[OperationalModuleStatus]) -> list[WarningSummary]:
        warnings: list[WarningSummary] = []
        for status in module_statuses:
            if status.status in {"WARNING", "FAILED"}:
                warnings.append(
                    WarningSummary(
                        category=status.module_name,
                        severity="ERROR" if status.status == "FAILED" else "WARNING",
                        message=status.message,
                    )
                )
        warnings.append(
            WarningSummary(
                category="safety",
                severity="INFO",
                message="Live broker execution is disabled. Platform is operating in simulation-only mode.",
            )
        )
        warnings.append(
            WarningSummary(
                category="portfolio",
                severity="INFO",
                message="NIFTY50 remains blocked/conditional until Indian broker integration is implemented.",
            )
        )
        return warnings
