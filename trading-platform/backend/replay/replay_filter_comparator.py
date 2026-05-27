from collections import Counter

from backend.replay.replay_calibration_models import ReplayCalibrationReport
from backend.replay.replay_comparison_models import ReplayFilterComparison


class ReplayFilterComparator:
    """Compare replay calibration gates across scenarios."""

    def compare_filters(self, calibration_reports: list[ReplayCalibrationReport]) -> ReplayFilterComparison:
        if not calibration_reports:
            return ReplayFilterComparison()

        gate_counts: Counter[str] = Counter()
        total_blocked = 0
        for report in calibration_reports:
            total_blocked += report.block_reason_metrics.total_blocked
            for gate, count in report.block_reason_metrics.gate_counts.items():
                gate_counts[gate] += int(count)

        if not gate_counts:
            return ReplayFilterComparison(
                filters_compared=[],
                insight="Calibration reports did not contain restrictive filter counts.",
            )

        denominator = max(1, total_blocked)
        filter_rates = {
            gate: round((count / denominator) * 100.0, 2)
            for gate, count in sorted(gate_counts.items())
        }
        most = max(filter_rates.items(), key=lambda item: item[1])[0]
        least = min(filter_rates.items(), key=lambda item: item[1])[0]
        return ReplayFilterComparison(
            filters_compared=sorted(filter_rates),
            most_restrictive_filter=most,
            least_restrictive_filter=least,
            filter_block_rates=filter_rates,
            insight=f"{most} is the most restrictive replay filter across compared scenarios.",
        )
