import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SENDER_PATH = PROJECT_ROOT / "backend/mt5_demo/guarded_demo_order_sender_service.py"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def sender_text() -> str:
    return SENDER_PATH.read_text(encoding="utf-8")


def verify_filling_mode_selection_logic() -> bool:
    text = sender_text()
    required = [
        'symbol_info = mt5.symbol_info("EURUSD")',
        "def _select_supported_filling_mode",
        'getattr(symbol_info, "filling_mode", None)',
        "ORDER_FILLING_IOC",
        "ORDER_FILLING_FOK",
        "ORDER_FILLING_RETURN",
        '"type_filling": selected_filling_mode',
        '"selected_filling_mode": selected_filling_mode',
    ]
    missing = [token for token in required if token not in text]
    ioc_index = text.find('getattr(mt5, "ORDER_FILLING_IOC", None)')
    fok_index = text.find('getattr(mt5, "ORDER_FILLING_FOK", None)')
    return_index = text.find('getattr(mt5, "ORDER_FILLING_RETURN", None)')
    preferred_order = -1 not in {ioc_index, fok_index, return_index} and ioc_index < fok_index < return_index
    return show("Supported filling mode selection exists", not missing and preferred_order, ", ".join(missing))


def verify_unsupported_filling_mode_retry_condition() -> bool:
    text = sender_text()
    required = [
        "def _unsupported_filling_mode_retry_available",
        "def _is_unsupported_filling_mode_rejection",
        "demo_attempts != 1",
        'result.get("status") == "DEMO_ORDER_REJECTED"',
        'result.get("mt5_order_sent") is False',
        'str(result.get("ticket")) == "0"',
        'str(result.get("retcode")) == "10030"',
        '"unsupported filling mode" in str(result.get("comment", "")).lower()',
        "self._demo_send_attempted and not self._unsupported_filling_mode_retry_available()",
        "SINGLE_DEMO_TRADE_LIMIT_REACHED",
    ]
    missing = [token for token in required if token not in text]
    return show("Unsupported filling mode retry is restricted", not missing, ", ".join(missing))


def verify_no_unrestricted_order_send_added() -> bool:
    token = "mt5." + "order_send"
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    text = sender_text()
    scoped = (
        text.count("mt5.order_send(order_request)") == 1
        and "execute_single_demo_order_now" in text
        and "DEMO" in text
        and "RUNTIME_SYMBOL_NOT_ENABLED" in text
        and "LOT_MUST_BE_EXACTLY_0_01" in text
    )
    return show("No unrestricted mt5.order_send added", sorted(matches) == allowed and scoped, ", ".join(matches))


def verify_execution_flags_remain_disabled() -> bool:
    text = sender_text()
    required = [
        '"live_execution_enabled": False',
        '"broker_execution_enabled": False',
        'if payload.get("live_execution_enabled") is True:',
        'if payload.get("broker_execution_enabled") is True:',
        "LIVE_TRADING_ENABLED",
        "PRODUCTION_BROKER_EXECUTION_ENABLED",
    ]
    missing = [token for token in required if token not in text]
    return show("Live and broker execution remain disabled", not missing, ", ".join(missing))


def main() -> int:
    print("Phase 17 Day 3 Filling Mode Retry Verification")
    print("=" * 78)
    checks = [
        verify_filling_mode_selection_logic(),
        verify_unsupported_filling_mode_retry_condition(),
        verify_no_unrestricted_order_send_added(),
        verify_execution_flags_remain_disabled(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
