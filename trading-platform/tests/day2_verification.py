import importlib
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_path(path: str, label: str, is_dir: bool = False) -> bool:
    target = PROJECT_ROOT / path
    passed = target.is_dir() if is_dir else target.is_file()
    print_result(label, passed, "" if passed else path)
    return passed


def verify_import(module_name: str, label: str) -> bool:
    try:
        importlib.import_module(module_name)
        print_result(label, True)
        return True
    except Exception as exc:
        print_result(label, False, str(exc))
        return False


def verify_router_registered() -> bool:
    try:
        from backend.main import app

        paths = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        required_paths = {
            "/health",
            "/status",
            "/market-data/timeframes",
            "/market-data/tick/{symbol}",
            "/market-data/candles/{symbol}",
            "/market-data/snapshot/{symbol}",
        }
        missing = sorted(required_paths - paths)
        print_result("market data router is registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("market data router is registered", False, str(exc))
        return False


def verify_supported_timeframes() -> bool:
    try:
        from backend.market_data.timeframe import SUPPORTED_TIMEFRAMES, get_mt5_timeframe

        required = {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}
        passed = required.issubset(set(SUPPORTED_TIMEFRAMES))
        get_mt5_timeframe("M15")
        print_result("supported timeframes exist", passed)
        return passed
    except Exception as exc:
        print_result("supported timeframes exist", False, str(exc))
        return False


def verify_validation_functions() -> bool:
    try:
        from backend.market_data.validators import (
            validate_candle_count,
            validate_symbol_name,
            validate_timeframe,
        )

        passed = (
            validate_symbol_name(" xauusd ") == "XAUUSD"
            and validate_candle_count(100) == 100
            and validate_timeframe("m15") == "M15"
        )

        try:
            validate_candle_count(5001)
            passed = False
        except ValueError:
            pass

        print_result("validation functions work", passed)
        return passed
    except Exception as exc:
        print_result("validation functions work", False, str(exc))
        return False


def verify_candle_model() -> bool:
    try:
        from backend.market_data.candle import Candle

        candle = Candle(
            symbol="XAUUSD",
            timeframe="M15",
            time=datetime.now(timezone.utc),
            open=2300.0,
            high=2310.0,
            low=2295.0,
            close=2305.0,
            tick_volume=1200,
            spread=20,
            real_volume=0,
        )
        passed = candle.to_dict()["symbol"] == "XAUUSD"
        print_result("Candle model can be instantiated", passed)
        return passed
    except Exception as exc:
        print_result("Candle model can be instantiated", False, str(exc))
        return False


def main() -> int:
    print("Day 2 Market Data Engine Verification")
    print("=" * 42)

    checks = [
        verify_path("backend/market_data", "market_data folder exists", is_dir=True),
        verify_path("backend/market_data/candle.py", "candle.py exists"),
        verify_path("backend/market_data/timeframe.py", "timeframe.py exists"),
        verify_path("backend/market_data/market_data_service.py", "market_data_service.py exists"),
        verify_path("backend/market_data/market_snapshot.py", "market_snapshot.py exists"),
        verify_path("backend/market_data/validators.py", "validators.py exists"),
        verify_path("backend/api/market_data_routes.py", "api/market_data_routes.py exists"),
        verify_import("backend.main", "FastAPI app imports correctly"),
        verify_router_registered(),
        verify_supported_timeframes(),
        verify_validation_functions(),
        verify_candle_model(),
    ]

    print("=" * 42)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

