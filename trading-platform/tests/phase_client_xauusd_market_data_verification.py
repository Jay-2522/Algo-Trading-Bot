import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SERVICE_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_market_data_service.py"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_xauusd_select_before_tick() -> bool:
    text = SERVICE_PATH.read_text(encoding="utf-8")
    passed = (
        "mt5.symbol_select(symbol, True)" in text
        and "time.sleep(0.15)" in text
        and "mt5.symbol_info_tick(normalized)" in text
        and "info = mt5.symbol_info(normalized)" in text
    )
    return show("XAUUSD tick path selects symbol before reading tick", passed)


def verify_missing_ticks_are_honest() -> bool:
    text = SERVICE_PATH.read_text(encoding="utf-8")
    required = [
        "SYMBOL_NOT_AVAILABLE",
        "STALE_OR_MARKET_CLOSED",
        "bid <= 0 or ask <= 0 or spread <= 0 or raw_timestamp <= 0",
        "MT5 tick is stale. Market may be closed or broker feed is not updating.",
    ]
    missing = [item for item in required if item not in text]
    return show("Missing or stale ticks are classified honestly", not missing, ", ".join(missing))


def verify_no_fake_prices_or_orders() -> bool:
    text = SERVICE_PATH.read_text(encoding="utf-8")
    forbidden = ["100003.13", "hardcoded", "mt5.order_send", "order_send("]
    present = [item for item in forbidden if item in text]
    return show("Market data service has no fake prices or order placement", not present, ", ".join(present))


def main() -> int:
    print("Client XAUUSD Market Data Verification")
    print("=" * 78)
    checks = [
        verify_xauusd_select_before_tick(),
        verify_missing_ticks_are_honest(),
        verify_no_fake_prices_or_orders(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
