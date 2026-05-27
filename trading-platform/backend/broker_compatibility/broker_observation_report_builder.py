from backend.broker_compatibility.broker_observation_models import BrokerObservationReport, BrokerSymbolSnapshot


class BrokerObservationReportBuilder:
    """Build summarized broker observation reports from symbol snapshots."""

    def build_report(self, broker_id: str, snapshots: list[BrokerSymbolSnapshot]) -> BrokerObservationReport:
        broker_id = str(broker_id or "").strip().upper()
        observed = [snapshot.canonical_symbol for snapshot in snapshots if snapshot.available]
        unavailable = [snapshot.canonical_symbol for snapshot in snapshots if not snapshot.available]
        sources = {snapshot.source for snapshot in snapshots}
        if not snapshots or not observed:
            mode = "UNAVAILABLE"
            status = "UNAVAILABLE"
        elif sources == {"MT5_READ_ONLY"}:
            mode = "READ_ONLY"
            status = "OPERATIONAL"
        elif "MT5_READ_ONLY" in sources or "SIMULATION_FALLBACK" in sources:
            mode = "SIMULATION_FALLBACK" if "SIMULATION_FALLBACK" in sources else "READ_ONLY"
            status = "PARTIAL" if unavailable else "OPERATIONAL"
        else:
            mode = "UNAVAILABLE"
            status = "UNAVAILABLE"

        if "NIFTY50" in {snapshot.canonical_symbol for snapshot in snapshots} and "NIFTY50" not in observed:
            if "NIFTY50" not in unavailable:
                unavailable.append("NIFTY50")

        return BrokerObservationReport(
            broker_id=broker_id,
            observation_mode=mode,
            symbols_observed=observed,
            snapshots=snapshots,
            unavailable_symbols=unavailable,
            observation_status=status,
            simulation_only=True,
            live_execution_enabled=False,
        )
