import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_routes() -> bool:
    files = [
        "backend/account_routing/allocation_models.py",
        "backend/account_routing/account_risk_profile.py",
        "backend/account_routing/account_balance_snapshot.py",
        "backend/account_routing/lot_allocation_engine.py",
        "backend/account_routing/risk_distribution_engine.py",
        "backend/account_routing/symbol_risk_rules.py",
        "backend/account_routing/exposure_validation_engine.py",
        "backend/account_routing/broker_lot_constraints.py",
        "backend/account_routing/allocation_decision_builder.py",
        "backend/account_routing/allocation_monitoring_service.py",
        "docs/phase-3-day-16-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/accounts/allocation/status",
            "/accounts/risk-profiles",
            "/accounts/balance-snapshots",
            "/accounts/symbol-rules/{symbol}",
            "/accounts/allocation/preview",
            "/accounts/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Allocation files and routes exist", files_ok and routes_ok)


def verify_profiles_and_constraints() -> bool:
    try:
        from backend.account_routing.account_risk_profile import AccountRiskProfileEngine
        from backend.account_routing.broker_lot_constraints import BrokerLotConstraints
        from backend.account_routing.exposure_validation_engine import ExposureValidationEngine
        from backend.account_routing.symbol_risk_rules import SymbolRiskRules

        profile_engine = AccountRiskProfileEngine()
        profiles = profile_engine.get_profiles()
        forex = [profile for profile in profiles if profile.broker_id in {"STARTRADER", "FXPRO", "VANTAGE"}]
        indian = [profile for profile in profiles if profile.broker_id in {"ZERODHA", "ANGELONE", "UPSTOX"}]
        lot_ok, adjusted, _ = BrokerLotConstraints().validate_lot("STARTRADER", 0.015)
        lot_bad, _, bad_reason = BrokerLotConstraints().validate_lot("FXPRO", 0.001)
        exposure_ok, exposure_issues = ExposureValidationEngine().validate_exposure(forex[0], "EURUSD", 0.5)
        exposure_bad, bad_issues = ExposureValidationEngine().validate_exposure(forex[0], "EURUSD", 5.0)
        rules = SymbolRiskRules()
        passed = (
            len(forex) == 3
            and all(profile.enabled and profile.demo_ready and profile.read_only for profile in forex)
            and all(profile.live_execution_enabled is False and profile.simulation_only is True for profile in profiles)
            and all(profile.enabled is False and profile.demo_ready is False for profile in indian)
            and lot_ok is True
            and adjusted == 0.02
            and lot_bad is False
            and "minimum" in bad_reason
            and exposure_ok is True
            and not exposure_issues
            and exposure_bad is False
            and any("max risk" in issue.lower() for issue in bad_issues)
            and rules.get_rules("EURUSD")["max_total_lot"] == 3.0
            and rules.get_rules("XAUUSD")["max_risk"] == 0.75
            and rules.get_rules("NIFTY50")["blocked"] is True
        )
        return show("Risk profiles, exposure validation, lot constraints, and symbol rules work", passed)
    except Exception as exc:
        return show("Risk profiles, exposure validation, lot constraints, and symbol rules work", False, str(exc))


def verify_allocation_decisions() -> bool:
    try:
        from backend.account_routing.allocation_monitoring_service import AllocationMonitoringService

        service = AllocationMonitoringService()
        eur = service.preview_allocation(
            {"signal_id": "alloc-test-001", "canonical_symbol": "EURUSD", "action": "BUY", "allocation_mode": "EQUAL", "total_lot": 0.03}
        )
        xau = service.preview_allocation(
            {"signal_id": "alloc-test-002", "canonical_symbol": "XAUUSD", "action": "SELL", "allocation_mode": "RISK_WEIGHTED", "total_lot": 0.06}
        )
        nifty = service.preview_allocation(
            {"signal_id": "alloc-test-003", "canonical_symbol": "NIFTY50", "action": "BUY", "allocation_mode": "EQUAL", "total_lot": 1}
        )
        passed = (
            eur.routing_ready is True
            and len([a for a in eur.allocations if a.allocation_status in {"APPROVED", "REDUCED"}]) == 3
            and eur.total_allocated_lot == 0.03
            and round(eur.total_risk_percent, 2) == 3.0
            and all(allocation.allocated_lot == 0.01 for allocation in eur.allocations if allocation.allocation_status == "APPROVED")
            and xau.routing_ready is True
            and xau.total_allocated_lot == 0.06
            and round(xau.total_risk_percent, 2) == 2.25
            and all(allocation.risk_percent == 0.75 for allocation in xau.allocations if allocation.allocation_status == "APPROVED")
            and nifty.routing_ready is False
            and nifty.total_allocated_lot == 0.0
            and any("NIFTY50" in reason for reason in nifty.rejection_reasons)
            and eur.simulation_only is True
            and eur.live_execution_enabled is False
        )
        return show("Allocation decisions approve EURUSD/XAUUSD and block NIFTY50 safely", passed)
    except Exception as exc:
        return show("Allocation decisions approve EURUSD/XAUUSD and block NIFTY50 safely", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/accounts/allocation/status")
        profiles = client.get("/accounts/risk-profiles")
        snapshots = client.get("/accounts/balance-snapshots")
        rules = client.get("/accounts/symbol-rules/EURUSD")
        eur = client.post(
            "/accounts/allocation/preview",
            json={"signal_id": "api-eur", "canonical_symbol": "EURUSD", "action": "BUY", "allocation_mode": "EQUAL", "total_lot": 0.03},
        )
        xau = client.post(
            "/accounts/allocation/preview",
            json={"signal_id": "api-xau", "canonical_symbol": "XAUUSD", "action": "SELL", "allocation_mode": "RISK_WEIGHTED", "total_lot": 0.06},
        )
        nifty = client.post(
            "/accounts/allocation/preview",
            json={"signal_id": "api-nifty", "canonical_symbol": "NIFTY50", "action": "BUY", "allocation_mode": "EQUAL", "total_lot": 1},
        )
        day15 = client.get("/accounts/status")
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and profiles.status_code == 200
            and len(profiles.json()) == 6
            and snapshots.status_code == 200
            and len(snapshots.json()) == 6
            and rules.status_code == 200
            and rules.json()["symbol"] == "EURUSD"
            and eur.status_code == 200
            and eur.json()["routing_ready"] is True
            and xau.status_code == 200
            and xau.json()["routing_ready"] is True
            and nifty.status_code == 200
            and nifty.json()["routing_ready"] is False
            and day15.status_code == 200
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Allocation APIs are JSON-safe and preserve Day 15 routes", passed)
    except Exception as exc:
        return show("Allocation APIs are JSON-safe and preserve Day 15 routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 16 Account Allocation Verification")
    print("=" * 58)
    checks = [
        verify_files_and_routes(),
        verify_profiles_and_constraints(),
        verify_allocation_decisions(),
        verify_api_and_safety(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
