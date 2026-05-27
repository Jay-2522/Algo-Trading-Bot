import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "backend/broker_compatibility/__init__.py",
        "backend/broker_compatibility/broker_models.py",
        "backend/broker_compatibility/broker_registry.py",
        "backend/broker_compatibility/broker_symbol_mapper.py",
        "backend/broker_compatibility/broker_capability_checker.py",
        "backend/broker_compatibility/broker_demo_readiness.py",
        "backend/broker_compatibility/broker_compatibility_service.py",
        "backend/api/broker_compatibility_routes.py",
        "docs/phase-3-day-6-progress.md",
    ]
    return show("Broker compatibility package, router, and docs exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_registry_and_mapping() -> bool:
    try:
        from backend.broker_compatibility.broker_capability_checker import BrokerCapabilityChecker
        from backend.broker_compatibility.broker_registry import BrokerRegistry
        from backend.broker_compatibility.broker_symbol_mapper import BrokerSymbolMapper

        registry = BrokerRegistry()
        brokers = {broker.broker_id for broker in registry.list_brokers()}
        mapper = BrokerSymbolMapper(registry)
        checker = BrokerCapabilityChecker(registry, mapper)
        eur = checker.check_symbol_support("STARTRADER", "EURUSD")
        xau = checker.check_symbol_support("FXPRO", "XAUUSD")
        nifty = checker.check_symbol_support("VANTAGE", "NIFTY50")
        passed = (
            brokers == {"STARTRADER", "FXPRO", "VANTAGE"}
            and registry.is_supported_broker("startrader") is True
            and eur.supported is True
            and eur.broker_symbol == "EURUSD"
            and xau.supported is True
            and xau.broker_symbol == "XAUUSD"
            and nifty.supported is False
            and nifty.live_execution_enabled is False
            and "verify" in nifty.message.lower()
        )
        return show("Supported brokers and conservative symbol mappings are correct", passed)
    except Exception as exc:
        return show("Supported brokers and conservative symbol mappings are correct", False, str(exc))


def verify_demo_readiness_and_service() -> bool:
    try:
        from backend.broker_compatibility.broker_compatibility_service import BrokerCompatibilityService

        service = BrokerCompatibilityService()
        status = service.get_status()
        brokers = service.list_brokers()
        readiness = service.check_demo_readiness("STARTRADER")
        unsupported = service.check_demo_readiness("UNKNOWN")
        passed = (
            status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and len(brokers) == 3
            and readiness.broker_id == "STARTRADER"
            and readiness.simulation_only is True
            and readiness.live_execution_enabled is False
            and "EURUSD" in readiness.supported_symbols
            and "XAUUSD" in readiness.supported_symbols
            and "NIFTY50" in readiness.unsupported_symbols
            and unsupported.ready_for_demo_testing is False
        )
        return show("Broker compatibility service returns JSON-safe demo readiness", passed)
    except Exception as exc:
        return show("Broker compatibility service returns JSON-safe demo readiness", False, str(exc))


def verify_api_and_preserved_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        routes = {route.path for route in app.routes}
        expected = {
            "/brokers/status",
            "/brokers",
            "/brokers/{broker_id}",
            "/brokers/{broker_id}/symbols",
            "/brokers/{broker_id}/symbols/{symbol}",
            "/brokers/{broker_id}/demo-readiness",
            "/replay/status",
            "/replay/symbols",
        }
        status = client.get("/brokers/status")
        brokers = client.get("/brokers")
        startrader = client.get("/brokers/STARTRADER")
        eur = client.get("/brokers/STARTRADER/symbols/EURUSD")
        nifty = client.get("/brokers/STARTRADER/symbols/NIFTY50")
        readiness = client.get("/brokers/STARTRADER/demo-readiness")
        replay_status = client.get("/replay/status")
        safety = client.get("/system/safety-scan").json()
        passed = (
            expected <= routes
            and status.status_code == 200
            and brokers.status_code == 200
            and startrader.status_code == 200
            and eur.status_code == 200
            and eur.json()["supported"] is True
            and eur.json()["live_execution_enabled"] is False
            and nifty.status_code == 200
            and nifty.json()["supported"] is False
            and readiness.status_code == 200
            and readiness.json()["simulation_only"] is True
            and readiness.json()["live_execution_enabled"] is False
            and replay_status.status_code == 200
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
        )
        return show("Broker API is registered, JSON-safe, and preserves replay/safety routes", passed)
    except Exception as exc:
        return show("Broker API is registered, JSON-safe, and preserves replay/safety routes", False, str(exc))


def verify_system_health_module() -> bool:
    try:
        from backend.system_health.module_registry import get_module_registry

        modules = get_module_registry()
        match = next((module for module in modules if module["name"] == "broker_compatibility"), None)
        passed = (
            match is not None
            and match["route"] == "/brokers/status"
            and match["simulation_only"] is True
            and match["live_execution_enabled"] is False
        )
        return show("System health registry includes broker compatibility module", passed)
    except Exception as exc:
        return show("System health registry includes broker compatibility module", False, str(exc))


def main() -> int:
    print("Phase 3 Day 6 Broker Compatibility Verification")
    print("=" * 52)
    checks = [
        verify_files(),
        verify_registry_and_mapping(),
        verify_demo_readiness_and_service(),
        verify_api_and_preserved_routes(),
        verify_system_health_module(),
    ]
    print("=" * 52)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
