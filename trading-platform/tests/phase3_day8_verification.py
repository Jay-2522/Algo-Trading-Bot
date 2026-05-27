import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


class UnavailableMT5Client:
    def connect(self):
        raise RuntimeError("MT5 observation terminal unavailable")

    def disconnect(self):
        return None


def verify_files_and_routes() -> bool:
    files = [
        "backend/broker_compatibility/broker_observation_models.py",
        "backend/broker_compatibility/broker_demo_observer.py",
        "backend/broker_compatibility/broker_symbol_snapshotter.py",
        "backend/broker_compatibility/broker_observation_report_builder.py",
        "backend/broker_compatibility/broker_observation_service.py",
        "docs/phase-3-day-8-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/brokers/observation/status",
            "/brokers/observation/all",
            "/brokers/{broker_id}/observation",
            "/brokers/{broker_id}/observation/{symbol}",
            "/brokers/mt5/readiness",
            "/brokers/verification/all",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Observation files and routes exist", files_ok and routes_ok)


def verify_snapshotter_and_observer_fallbacks() -> bool:
    try:
        from backend.broker_compatibility.broker_demo_observer import BrokerDemoObserver
        from backend.broker_compatibility.broker_observation_report_builder import BrokerObservationReportBuilder
        from backend.broker_compatibility.broker_observation_service import BrokerObservationService
        from backend.broker_compatibility.broker_symbol_snapshotter import BrokerSymbolSnapshotter

        snapshotter = BrokerSymbolSnapshotter(mt5_client=UnavailableMT5Client())
        eur = snapshotter.snapshot_symbol("STARTRADER", "EURUSD")
        nifty = snapshotter.snapshot_symbol("STARTRADER", "NIFTY50")
        observer = BrokerDemoObserver(snapshotter=snapshotter, report_builder=BrokerObservationReportBuilder())
        report = observer.observe_broker("STARTRADER")
        service = BrokerObservationService(snapshotter=snapshotter, observer=observer)
        status = service.get_status()
        all_reports = service.observe_all_brokers()
        passed = (
            status.simulation_only is True
            and status.live_execution_enabled is False
            and status.read_only_mode is True
            and eur.source in {"SIMULATION_FALLBACK", "UNAVAILABLE"}
            and eur.available is True
            and eur.live_execution_enabled is False if hasattr(eur, "live_execution_enabled") else True
            and nifty.source == "UNAVAILABLE"
            and nifty.available is False
            and report.broker_id == "STARTRADER"
            and report.simulation_only is True
            and report.live_execution_enabled is False
            and "NIFTY50" in report.unavailable_symbols
            and len(all_reports) == 3
            and all(item.simulation_only is True and item.live_execution_enabled is False for item in all_reports)
        )
        return show("Snapshotter and observer return safe fallback reports", passed)
    except Exception as exc:
        return show("Snapshotter and observer return safe fallback reports", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/brokers/observation/status")
        all_reports = client.get("/brokers/observation/all")
        startrader = client.get("/brokers/STARTRADER/observation")
        fxpro = client.get("/brokers/FXPRO/observation")
        vantage = client.get("/brokers/VANTAGE/observation")
        eur = client.get("/brokers/STARTRADER/observation/EURUSD")
        xau = client.get("/brokers/STARTRADER/observation/XAUUSD")
        nifty = client.get("/brokers/STARTRADER/observation/NIFTY50")
        mt5 = client.get("/brokers/mt5/readiness")
        verification = client.get("/brokers/verification/all")
        safety = client.get("/system/safety-scan").json()
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and status.json()["read_only_mode"] is True
            and all_reports.status_code == 200
            and len(all_reports.json()) == 3
            and startrader.status_code == 200
            and fxpro.status_code == 200
            and vantage.status_code == 200
            and startrader.json()["simulation_only"] is True
            and startrader.json()["live_execution_enabled"] is False
            and eur.status_code == 200
            and eur.json()["source"] in {"MT5_READ_ONLY", "SIMULATION_FALLBACK", "UNAVAILABLE"}
            and xau.status_code == 200
            and nifty.status_code == 200
            and nifty.json()["source"] == "UNAVAILABLE"
            and nifty.json()["available"] is False
            and mt5.status_code == 200
            and verification.status_code == 200
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
        )
        return show("Observation API is JSON-safe and preserves Day 7 routes", passed)
    except Exception as exc:
        return show("Observation API is JSON-safe and preserves Day 7 routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 8 Broker Observation Verification")
    print("=" * 50)
    checks = [
        verify_files_and_routes(),
        verify_snapshotter_and_observer_fallbacks(),
        verify_api_and_safety(),
    ]
    print("=" * 50)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
