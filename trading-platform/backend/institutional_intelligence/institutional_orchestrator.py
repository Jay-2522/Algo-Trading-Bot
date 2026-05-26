from typing import Any

from backend.institutional_intelligence.institutional_health_checker import InstitutionalHealthChecker
from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport
from backend.institutional_intelligence.institutional_pipeline_runner import InstitutionalPipelineRunner
from backend.institutional_intelligence.institutional_report_builder import InstitutionalReportBuilder
from backend.institutional_intelligence.institutional_state_resolver import InstitutionalStateResolver


class InstitutionalOrchestrator:
    """Coordinate the complete analysis and paper-management pipeline without execution."""

    def __init__(
        self,
        service: Any,
        pipeline_runner: InstitutionalPipelineRunner | None = None,
        state_resolver: InstitutionalStateResolver | None = None,
        report_builder: InstitutionalReportBuilder | None = None,
        health_checker: InstitutionalHealthChecker | None = None,
    ) -> None:
        self.service = service
        self.pipeline_runner = pipeline_runner or InstitutionalPipelineRunner(service)
        self.state_resolver = state_resolver or InstitutionalStateResolver()
        self.report_builder = report_builder or InstitutionalReportBuilder()
        self.health_checker = health_checker or InstitutionalHealthChecker()

    def analyze(self, symbol: str, timeframe: str = "M15") -> InstitutionalOrchestrationReport:
        try:
            candles = self.service.market_data_service.get_candles(symbol, timeframe, count=250)
            return self.analyze_from_candles(symbol, timeframe, candles)
        except Exception:
            return self.analyze_from_candles(symbol, timeframe, [])
        finally:
            self.service.market_data_service.close()

    def analyze_from_candles(
        self, symbol: str, timeframe: str, candles: list[Any] | None
    ) -> InstitutionalOrchestrationReport:
        report = self.pipeline_runner.run_pipeline(symbol, timeframe, candles)
        state = self.state_resolver.resolve_state(report)
        report = report.model_copy(update={"system_state": state})
        return report.model_copy(
            update={
                "executive_summary": self.report_builder.build_executive_summary(report),
                "strengths": self.report_builder.extract_strengths(report),
                "weaknesses": self.report_builder.extract_weaknesses(report),
                "warnings": self.report_builder.extract_warnings(report),
                "simulation_only": True,
                "live_execution_enabled": False,
            }
        )
