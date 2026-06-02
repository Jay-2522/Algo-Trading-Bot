import csv
import io

from backend.client_analytics.report_builder import ReportBuilder
from backend.client_analytics.report_models import ClientReport


class ExportService:
    """Export client reports as safe JSON or CSV."""

    def __init__(self, report_builder: ReportBuilder | None = None) -> None:
        self.report_builder = report_builder or ReportBuilder()

    def export_json(self, report: ClientReport | None = None) -> dict:
        report = report or self.report_builder.build_daily_report()
        return report.model_dump(mode="json")

    def export_csv(self, report: ClientReport | None = None) -> str:
        report = report or self.report_builder.build_daily_report()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["report_id", "report_type", "period", "symbol", "total_signals", "demo_executions", "win_rate", "net_pnl"])
        if report.symbol_performance:
            for symbol in report.symbol_performance:
                writer.writerow(
                    [
                        report.report_id,
                        report.report_type,
                        report.period,
                        symbol.get("symbol", ""),
                        symbol.get("total_signals", 0),
                        symbol.get("demo_executions", 0),
                        symbol.get("win_rate", 0),
                        symbol.get("net_pnl", 0),
                    ]
                )
        return output.getvalue()
