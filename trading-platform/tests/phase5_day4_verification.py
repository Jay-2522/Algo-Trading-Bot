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
        "backend/trade_copier/__init__.py",
        "backend/trade_copier/trade_copier_models.py",
        "backend/trade_copier/copy_batch_builder.py",
        "backend/trade_copier/copy_synchronization_engine.py",
        "backend/trade_copier/copy_status_tracker.py",
        "backend/trade_copier/copy_duplicate_guard.py",
        "backend/trade_copier/trade_copier_service.py",
        "backend/api/trade_copier_routes.py",
        "docs/phase-5-day-4-progress.md",
    ]
    return show("Trade copier package, router, and docs exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_routes() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/trade-copier/status",
            "/trade-copier/batches",
            "/trade-copier/batches/{copy_batch_id}",
            "/trade-copier/preview-copy",
            "/trade-copier/create-batch",
            "/trade-copier/batches/{copy_batch_id}/synchronize",
            "/multi-account-execution/status",
            "/multi-account-execution/execute-demo-batch",
        }
        return show("Trade copier routes and Day 3 routes registered", expected <= routes)
    except Exception as exc:
        return show("Trade copier routes and Day 3 routes registered", False, str(exc))


def verify_preview_and_symbol_blocks() -> bool:
    try:
        from backend.trade_copier.trade_copier_service import TradeCopierService

        service = TradeCopierService()
        eurusd = service.preview_copy({"signal_id": "copy-demo-001", "canonical_symbol": "EURUSD", "action": "BUY", "total_lot": 0.03})
        xau = service.preview_copy({"signal_id": "copy-demo-xau", "canonical_symbol": "XAUUSD", "action": "BUY", "total_lot": 0.03})
        nifty = service.preview_copy({"signal_id": "copy-demo-nifty", "canonical_symbol": "NIFTY50", "action": "BUY", "total_lot": 0.03})
        passed = (
            eurusd.canonical_symbol == "EURUSD"
            and eurusd.source_signal_id == "copy-demo-001"
            and eurusd.copy_status == "READY"
            and len(eurusd.target_accounts) == 3
            and all(result.status == "PLANNED" for result in eurusd.account_copy_results)
            and all(result.copied is False for result in eurusd.account_copy_results)
            and xau.copy_status == "BLOCKED"
            and all(result.status == "BLOCKED" for result in xau.account_copy_results)
            and nifty.copy_status == "BLOCKED"
            and all(result.status == "BLOCKED" for result in nifty.account_copy_results)
        )
        return show("Preview creates READY/PLANNED EURUSD batch and blocks XAUUSD/NIFTY50", passed)
    except Exception as exc:
        return show("Preview creates READY/PLANNED EURUSD batch and blocks XAUUSD/NIFTY50", False, str(exc))


def verify_duplicate_guard_and_tracker() -> bool:
    try:
        from backend.trade_copier.trade_copier_service import TradeCopierService

        service = TradeCopierService()
        payload = {"signal_id": "copy-duplicate-001", "canonical_symbol": "EURUSD", "action": "SELL", "total_lot": 0.03}
        first = service.create_copy_batch(payload)
        second = service.create_copy_batch(payload)
        fetched = service.get_batch(first.copy_batch_id)
        listed = service.list_batches()
        passed = (
            fetched is not None
            and len(listed) == 2
            and first.duplicate_blocked is False
            and all(result.status == "PLANNED" for result in first.account_copy_results)
            and second.duplicate_blocked is True
            and all(result.status == "SKIPPED_DUPLICATE" for result in second.account_copy_results)
            and all("Duplicate trade copy attempt" in " ".join(result.rejection_reasons) for result in second.account_copy_results)
        )
        return show("Duplicate guard explicitly blocks repeated signal/account/symbol/action copy batches", passed)
    except Exception as exc:
        return show("Duplicate guard explicitly blocks repeated signal/account/symbol/action copy batches", False, str(exc))


def verify_duplicate_creation_api() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        payload = {"signal_id": "copy-demo-002", "canonical_symbol": "EURUSD", "action": "BUY", "total_lot": 0.03}
        first = client.post("/trade-copier/create-batch", json=payload)
        second = client.post("/trade-copier/create-batch", json=payload)
        first_json = first.json()
        second_json = second.json()
        second_statuses = [result.get("status") for result in second_json.get("account_copy_results", [])]
        passed = (
            first.status_code == 200
            and second.status_code == 200
            and first_json.get("duplicate_blocked") is False
            and first_json.get("simulation_only") is True
            and first_json.get("live_execution_enabled") is False
            and first_json.get("broker_execution_enabled") is False
            and (
                second_json.get("duplicate_blocked") is True
                or second_json.get("copy_status") == "BLOCKED"
                or all(status == "SKIPPED_DUPLICATE" for status in second_statuses)
            )
            and second_json.get("simulation_only") is True
            and second_json.get("live_execution_enabled") is False
            and second_json.get("broker_execution_enabled") is False
        )
        return show("API duplicate create-batch detects repeated copy-demo-002 signal", passed, str(second_statuses))
    except Exception as exc:
        return show("API duplicate create-batch detects repeated copy-demo-002 signal", False, str(exc))


def verify_synchronization_summary() -> bool:
    try:
        from backend.trade_copier.copy_synchronization_engine import CopySynchronizationEngine
        from backend.trade_copier.trade_copier_models import AccountCopyStatus, TradeCopyBatch

        batch = TradeCopyBatch(
            source_signal_id="partial-copy",
            canonical_symbol="EURUSD",
            action="BUY",
            target_accounts=["A1", "A2", "A3"],
            account_copy_results=[
                AccountCopyStatus(account_id="A1", broker_id="B1", status="COPIED", copied=True),
                AccountCopyStatus(account_id="A2", broker_id="B2", status="MT5_UNAVAILABLE", rejection_reasons=["Unavailable"]),
                AccountCopyStatus(account_id="A3", broker_id="B3", status="BLOCKED", rejection_reasons=["Blocked"]),
            ],
        )
        summary = CopySynchronizationEngine().summarize(batch)
        passed = (
            summary.total_targets == 3
            and summary.copied_count == 1
            and summary.unavailable_count == 1
            and summary.blocked_count == 1
            and summary.partial_copy is True
            and summary.synchronization_status == "PARTIAL"
        )
        return show("Synchronization summary detects partial copied trades", passed)
    except Exception as exc:
        return show("Synchronization summary detects partial copied trades", False, str(exc))


def verify_api_and_safety_flags() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/trade-copier/status")
        preview = client.post(
            "/trade-copier/preview-copy",
            json={"signal_id": "copy-api-preview", "canonical_symbol": "EURUSD", "action": "BUY", "total_lot": 0.03},
        )
        created = client.post(
            "/trade-copier/create-batch",
            json={"signal_id": "copy-api-create", "canonical_symbol": "EURUSD", "action": "BUY", "total_lot": 0.03},
        )
        created_json = created.json()
        synchronized = client.post(f"/trade-copier/batches/{created_json.get('copy_batch_id')}/synchronize")
        listed = client.get("/trade-copier/batches")
        fetched = client.get(f"/trade-copier/batches/{created_json.get('copy_batch_id')}")
        status_json = status.json()
        preview_json = preview.json()
        passed = (
            status.status_code == 200
            and preview.status_code == 200
            and created.status_code == 200
            and synchronized.status_code == 200
            and listed.status_code == 200
            and fetched.status_code == 200
            and status_json.get("demo_execution") is True
            and status_json.get("simulation_only") is True
            and status_json.get("live_execution_enabled") is False
            and status_json.get("broker_execution_enabled") is False
            and preview_json.get("simulation_only") is True
            and preview_json.get("copy_status") == "READY"
            and all(result.get("status") == "PLANNED" and result.get("copied") is False for result in preview_json.get("account_copy_results", []))
            and created_json.get("simulation_only") is True
            and created_json.get("live_execution_enabled") is False
            and created_json.get("broker_execution_enabled") is False
            and synchronized.json().get("copy_batch_id") == created_json.get("copy_batch_id")
        )
        return show("Trade copier APIs are JSON-safe and preserve safety flags", passed)
    except Exception as exc:
        return show("Trade copier APIs are JSON-safe and preserve safety flags", False, str(exc))


def verify_module_registry() -> bool:
    try:
        from backend.system_health.module_registry import get_module_registry

        modules = get_module_registry()
        passed = any(module["name"] == "demo_trade_copier" and module["route"] == "/trade-copier/status" for module in modules)
        return show("Trade copier appears in module registry", passed)
    except Exception as exc:
        return show("Trade copier appears in module registry", False, str(exc))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def main() -> int:
    print("Phase 5 Day 4 Demo Trade Copier Coordination Verification")
    print("=" * 63)
    checks = [
        verify_files(),
        verify_routes(),
        verify_preview_and_symbol_blocks(),
        verify_duplicate_guard_and_tracker(),
        verify_duplicate_creation_api(),
        verify_synchronization_summary(),
        verify_api_and_safety_flags(),
        verify_module_registry(),
        verify_order_send_isolated(),
    ]
    print("=" * 63)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
