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
        raise RuntimeError("MT5 test terminal unavailable")

    def disconnect(self):
        return None


def verify_files_and_routes() -> bool:
    files = [
        "backend/broker_compatibility/mt5_demo_models.py",
        "backend/broker_compatibility/mt5_symbol_verifier.py",
        "backend/broker_compatibility/mt5_demo_readiness_checker.py",
        "backend/broker_compatibility/broker_symbol_verification_report.py",
        "backend/broker_compatibility/broker_demo_verification_service.py",
        "docs/phase-3-day-7-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/brokers/mt5/readiness",
            "/brokers/verification/all",
            "/brokers/{broker_id}/verification",
            "/brokers/{broker_id}/verification/{symbol}",
            "/brokers/status",
            "/brokers/{broker_id}/symbols",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("MT5 demo-readiness files and verification routes exist", files_ok and routes_ok)


def verify_readiness_and_symbol_verifier() -> bool:
    try:
        from backend.broker_compatibility.mt5_demo_readiness_checker import MT5DemoReadinessChecker
        from backend.broker_compatibility.mt5_symbol_verifier import MT5SymbolVerifier

        readiness = MT5DemoReadinessChecker(mt5_client=UnavailableMT5Client()).check_terminal_readiness()
        verification = MT5SymbolVerifier(mt5_client=UnavailableMT5Client()).verify_symbol(
            "EURUSD", "EURUSD", "STARTRADER"
        )
        passed = (
            readiness.terminal_available is False
            and readiness.initialized is False
            and readiness.read_only_mode is True
            and readiness.simulation_only is True
            and readiness.live_execution_enabled is False
            and verification.verification_status == "MT5_UNAVAILABLE"
            and verification.mt5_symbol_found is False
        )
        return show("MT5 readiness and symbol verifier fail safely without terminal", passed)
    except Exception as exc:
        return show("MT5 readiness and symbol verifier fail safely without terminal", False, str(exc))


def verify_broker_report_and_service() -> bool:
    try:
        from backend.broker_compatibility.broker_demo_verification_service import BrokerDemoVerificationService
        from backend.broker_compatibility.broker_symbol_verification_report import BrokerSymbolVerificationReportBuilder
        from backend.broker_compatibility.mt5_demo_readiness_checker import MT5DemoReadinessChecker
        from backend.broker_compatibility.mt5_symbol_verifier import MT5SymbolVerifier

        readiness_checker = MT5DemoReadinessChecker(mt5_client=UnavailableMT5Client())
        verifier = MT5SymbolVerifier(mt5_client=UnavailableMT5Client())
        builder = BrokerSymbolVerificationReportBuilder(
            readiness_checker=readiness_checker,
            symbol_verifier=verifier,
        )
        report = builder.build_report("STARTRADER")
        service = BrokerDemoVerificationService(
            readiness_checker=readiness_checker,
            symbol_verifier=verifier,
            report_builder=builder,
        )
        all_reports = service.verify_all_brokers()
        single = service.verify_symbol_for_broker("STARTRADER", "EURUSD")
        nifty = service.verify_symbol_for_broker("STARTRADER", "NIFTY50")
        symbols = {item.canonical_symbol for item in report.symbol_verifications}
        passed = (
            symbols == {"EURUSD", "XAUUSD", "NIFTY50"}
            and "NIFTY50" in report.conditional_symbols
            and report.simulation_only is True
            and report.live_execution_enabled is False
            and report.ready_for_demo_execution is False
            and len(all_reports) == 3
            and all(item.simulation_only is True and item.live_execution_enabled is False for item in all_reports)
            and single.verification_status == "MT5_UNAVAILABLE"
            and nifty.verification_status == "CONDITIONAL"
        )
        return show("Broker verification reports include all symbols and conservative NIFTY50 handling", passed)
    except Exception as exc:
        return show("Broker verification reports include all symbols and conservative NIFTY50 handling", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        readiness = client.get("/brokers/mt5/readiness")
        all_reports = client.get("/brokers/verification/all")
        startrader = client.get("/brokers/STARTRADER/verification")
        fxpro = client.get("/brokers/FXPRO/verification")
        vantage = client.get("/brokers/VANTAGE/verification")
        eur = client.get("/brokers/STARTRADER/verification/EURUSD")
        nifty = client.get("/brokers/STARTRADER/verification/NIFTY50")
        status = client.get("/brokers/status")
        symbols = client.get("/brokers/STARTRADER/symbols")
        safety = client.get("/system/safety-scan").json()
        passed = (
            readiness.status_code == 200
            and readiness.json()["simulation_only"] is True
            and readiness.json()["live_execution_enabled"] is False
            and all_reports.status_code == 200
            and len(all_reports.json()) == 3
            and startrader.status_code == 200
            and fxpro.status_code == 200
            and vantage.status_code == 200
            and eur.status_code == 200
            and eur.json()["verification_status"] in {"MT5_UNAVAILABLE", "VERIFIED", "NOT_FOUND"}
            and nifty.status_code == 200
            and nifty.json()["verification_status"] == "CONDITIONAL"
            and startrader.json()["ready_for_demo_execution"] is False
            and startrader.json()["simulation_only"] is True
            and startrader.json()["live_execution_enabled"] is False
            and status.status_code == 200
            and symbols.status_code == 200
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
        )
        return show("Broker verification API is JSON-safe and preserves safety boundaries", passed)
    except Exception as exc:
        return show("Broker verification API is JSON-safe and preserves safety boundaries", False, str(exc))


def main() -> int:
    print("Phase 3 Day 7 MT5 Demo Verification")
    print("=" * 43)
    checks = [
        verify_files_and_routes(),
        verify_readiness_and_symbol_verifier(),
        verify_broker_report_and_service(),
        verify_api_and_safety(),
    ]
    print("=" * 43)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
