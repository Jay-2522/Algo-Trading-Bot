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


def verify_fallback_logic_exists() -> bool:
    text = sender_text()
    required = [
        "def _build_filling_mode_candidates",
        'getattr(symbol_info, "filling_mode", None)',
        'getattr(mt5, "ORDER_FILLING_IOC", None)',
        'getattr(mt5, "ORDER_FILLING_FOK", None)',
        'getattr(mt5, "ORDER_FILLING_RETURN", None)',
        "for filling_mode in filling_mode_candidates:",
        'order_request["type_filling"] = filling_mode',
        "mt5.order_send(order_request)",
        "unsupported_filling_retcode = 10030",
        'retcode != unsupported_filling_retcode or "unsupported filling mode" not in comment.lower()',
    ]
    missing = [token for token in required if token not in text]
    ioc_index = text.find('getattr(mt5, "ORDER_FILLING_IOC", None)')
    fok_index = text.find('getattr(mt5, "ORDER_FILLING_FOK", None)')
    return_index = text.find('getattr(mt5, "ORDER_FILLING_RETURN", None)')
    preferred_order = -1 not in {ioc_index, fok_index, return_index} and ioc_index < fok_index < return_index
    return show("Filling mode fallback logic exists", not missing and preferred_order, ", ".join(missing))


def verify_attempts_are_recorded() -> bool:
    text = sender_text()
    required = [
        "filling_mode_attempts: list[dict[str, Any]] = []",
        '"mode": filling_mode',
        '"retcode": retcode',
        '"comment": comment',
        '"order": getattr(mt5_result, "order", 0) or 0',
        '"deal": getattr(mt5_result, "deal", 0) or 0',
        "filling_mode_attempts.append(attempt)",
        '"filling_mode_attempts": filling_mode_attempts or []',
        '"selected_filling_mode": selected_filling_mode',
        '"final_retcode": final_retcode',
        '"final_comment": final_comment if final_comment is not None else comment',
    ]
    missing = [token for token in required if token not in text]
    return show("Filling mode attempts are recorded", not missing, ", ".join(missing))


def verify_only_guarded_sender_contains_fallback_loop() -> bool:
    order_send_token = "mt5." + "order_send"
    loop_token = "for filling_mode in filling_mode_candidates:"
    order_send_matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if order_send_token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    fallback_loop_matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if loop_token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed_order_send = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    return show(
        "Only guarded sender contains fallback order_send loop",
        sorted(order_send_matches) == allowed_order_send
        and fallback_loop_matches == ["backend/mt5_demo/guarded_demo_order_sender_service.py"],
        ", ".join(order_send_matches + fallback_loop_matches),
    )


def verify_execution_flags_remain_disabled() -> bool:
    text = sender_text()
    required = [
        '"live_execution_enabled": False',
        '"broker_execution_enabled": False',
        'if payload.get("live_execution_enabled") is True:',
        'if payload.get("broker_execution_enabled") is True:',
        "LIVE_TRADING_ENABLED",
        "PRODUCTION_BROKER_EXECUTION_ENABLED",
        "execute_single_demo_order_now",
        "MT5_DEMO_ACCOUNT_NOT_VALIDATED",
    ]
    forbidden = [
        '"live_execution_enabled": True',
        '"broker_execution_enabled": True',
        "live_execution_enabled=True",
        "broker_execution_enabled=True",
    ]
    missing = [token for token in required if token not in text]
    present_forbidden = [token for token in forbidden if token in text]
    return show("Live and broker execution remain disabled", not missing and not present_forbidden, ", ".join(missing + present_forbidden))


def main() -> int:
    print("Phase 17 Day 3 Filling Mode Fallback Verification")
    print("=" * 78)
    checks = [
        verify_fallback_logic_exists(),
        verify_attempts_are_recorded(),
        verify_only_guarded_sender_contains_fallback_loop(),
        verify_execution_flags_remain_disabled(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
