import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"
SIGNAL_ENGINE_PATH = PROJECT_ROOT / "backend/strategy/real_signal_engine_service.py"
SIGNAL_ROUTES_PATH = PROJECT_ROOT / "backend/api/client_signal_engine_routes.py"
VANTAGE_PATH = PROJECT_ROOT / "backend/mt5_demo/vantage_xauusd_demo_validation_service.py"
GUARDED_PATH = PROJECT_ROOT / "backend/mt5_demo/guarded_demo_order_sender_service.py"
JOURNAL_PATH = PROJECT_ROOT / "backend/trade_journal/persistent_trade_journal_service.py"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_signal_audit_route() -> bool:
    from backend.main import app

    client = TestClient(app)
    response = client.get("/client-signals-engine/diagnostics/XAUUSD")
    payload = response.json()
    audit = payload.get("approval_audit", {})
    required = [
        "bos_result",
        "choch_result",
        "liquidity_sweep_result",
        "fvg_result",
        "order_block_result",
        "rr_result",
        "confidence_result",
        "final_approval_reason",
    ]
    passed = response.status_code == 200 and all(item in audit for item in required)
    return show("Signal diagnostics explain approve/wait/reject decisions", passed, str(audit))


def verify_dashboard_preview_flow() -> bool:
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    required_dashboard = [
        "fetchClientMarketPrices",
        "fetchClientSignals",
        "1000",
        "5000",
        "READY_SIGNAL_HOLD_SECONDS = 30",
        "Valid for",
        "Preview Trade",
        "PreviewPanel",
        "Confirm Demo Order",
        "duplicate_protection_status",
        "READY_FOR_PREVIEW",
        "risk_status",
        "syncClientPositionsToJournal",
        "syncClientLifecycle",
        "broker_source",
        "lastCandleTimestamp",
        "staleSignalBlockers",
        "refreshSignals",
    ]
    required_api = [
        "/mt5-demo/vantage/${symbolPath}/test-order/preview",
        "/mt5-demo/vantage/${symbolPath}/test-order",
        "signal_confidence",
        "signal_timestamp",
        "strategy_metadata",
    ]
    missing = [item for item in required_dashboard if item not in dashboard] + [item for item in required_api if item not in api]
    return show("Dashboard cards drive read-only preview and guarded confirm flow", not missing, ", ".join(missing))


def verify_vantage_preview_readiness_fields() -> bool:
    text = VANTAGE_PATH.read_text(encoding="utf-8")
    required = [
        '"would_send": False',
        '"duplicate_protection_status"',
        '"approval_status"',
        '"blockers"',
        '"account_type"',
        '"broker_source"',
        '"signal_confidence"',
        '"strategy_metadata"',
        "_revalidate_signal",
        "SIGNAL_EXPIRED",
        "SIGNAL_NO_LONGER_READY_FOR_PREVIEW",
        "SIGNAL_HASH_CHANGED",
    ]
    missing = [item for item in required if item not in text]
    return show("Vantage preview exposes readiness and duplicate-protection fields", not missing, ", ".join(missing))


def verify_journal_attribution_fields() -> bool:
    guarded = GUARDED_PATH.read_text(encoding="utf-8")
    journal = JOURNAL_PATH.read_text(encoding="utf-8")
    required = ["broker_source", "signal_confidence", "signal_hash", "setup_reason", "strategy_metadata"]
    missing = [item for item in required if item not in guarded or item not in journal]
    return show("Journal preserves broker and strategy attribution", not missing, ", ".join(missing))


def verify_no_execution_bypass() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    unsafe_flags = []
    for path in [SIGNAL_ENGINE_PATH, VANTAGE_PATH, API_PATH, DASHBOARD_PATH]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for forbidden in ['"live_execution_enabled": True', '"broker_execution_enabled": True', "live_execution_enabled: true", "broker_execution_enabled: true"]:
            if forbidden in text:
                unsafe_flags.append(f"{path.name}:{forbidden}")
    return show("No unrestricted order_send or live/broker execution enablement", sorted(matches) == allowed and not unsafe_flags, ", ".join(matches + unsafe_flags))


def main() -> int:
    print("Phase 21.1 AI Preview + Guarded Flow Verification")
    print("=" * 78)
    checks = [
        verify_signal_audit_route(),
        verify_dashboard_preview_flow(),
        verify_vantage_preview_readiness_fields(),
        verify_journal_attribution_fields(),
        verify_no_execution_bypass(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
