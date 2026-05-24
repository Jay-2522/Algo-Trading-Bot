import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FOLDERS = [
    "backend/strategy_engine",
    "backend/execution_engine",
    "backend/ai_engine",
    "backend/risk_engine",
    "backend/news_engine",
    "backend/analytics",
    "backend/broker_integrations/mt5",
    "backend/broker_integrations/indian_brokers",
    "backend/websocket",
    "backend/database",
    "backend/config",
    "backend/utils",
    "frontend/dashboard",
    "frontend/admin",
    "deployment/docker",
    "deployment/nginx",
    "deployment/scripts",
    "docs",
    "tests",
    "logs",
]


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_required_folders() -> bool:
    missing = [folder for folder in REQUIRED_FOLDERS if not (PROJECT_ROOT / folder).is_dir()]
    print_result("required folders", not missing, ", ".join(missing))
    return not missing


def verify_import(module_name: str, label: str) -> bool:
    try:
        importlib.import_module(module_name)
        print_result(label, True)
        return True
    except Exception as exc:
        print_result(label, False, str(exc))
        return False


def verify_settings() -> bool:
    try:
        from backend.config.settings import get_settings

        settings = get_settings()
        passed = bool(settings.app_name and settings.database_url and settings.redis_url)
        print_result("settings.py works", passed)
        return passed
    except Exception as exc:
        print_result("settings.py works", False, str(exc))
        return False


def verify_logger() -> bool:
    try:
        from backend.utils.logger import get_logger

        logger = get_logger("day1_verification")
        logger.info("Logger verification message")
        print_result("logger.py works", True)
        return True
    except Exception as exc:
        print_result("logger.py works", False, str(exc))
        return False


def verify_database_models() -> bool:
    try:
        from backend.database.models import (
            MarketSnapshot,
            Position,
            RiskEvent,
            StrategyLog,
            SystemLog,
            Trade,
        )

        models = [Trade, Position, StrategyLog, RiskEvent, MarketSnapshot, SystemLog]
        passed = all(getattr(model, "__tablename__", None) for model in models)
        print_result("database models exist", passed)
        return passed
    except Exception as exc:
        print_result("database models exist", False, str(exc))
        return False


def verify_files() -> bool:
    required_files = [
        ".env.example",
        "README.md",
        "docs/day-1-progress.md",
        "backend/main.py",
        "backend/database/schema_plan.md",
    ]
    missing = [file_name for file_name in required_files if not (PROJECT_ROOT / file_name).is_file()]
    print_result("required documentation and env files", not missing, ", ".join(missing))
    return not missing


def main() -> int:
    print("Day 1 Foundation Verification")
    print("=" * 36)

    checks = [
        verify_required_folders(),
        verify_import("backend.main", "FastAPI app imports correctly"),
        verify_settings(),
        verify_logger(),
        verify_import("backend.broker_integrations.mt5.mt5_client", "MT5 module exists"),
        verify_database_models(),
        verify_files(),
    ]

    print("=" * 36)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

