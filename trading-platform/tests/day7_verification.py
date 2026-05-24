import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_path(path: str, label: str) -> bool:
    passed = (PROJECT_ROOT / path).is_file()
    print_result(label, passed, "" if passed else path)
    return passed


def verify_app_routes() -> bool:
    try:
        from backend.main import app

        routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        required = {
            "/health",
            "/status",
            "/market-data/timeframes",
            "/strategy/session",
            "/risk/status",
            "/execution/status",
            "/mt5/status",
            "/database/status",
        }
        missing = sorted(required - routes)
        print_result("FastAPI app imports and database/old routes registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("FastAPI app imports and database/old routes registered", False, str(exc))
        return False


def verify_base_import() -> bool:
    try:
        from backend.database.base import Base

        passed = Base is not None
        print_result("SQLAlchemy Base imports", passed)
        return passed
    except Exception as exc:
        print_result("SQLAlchemy Base imports", False, str(exc))
        return False


def verify_database_init() -> bool:
    try:
        from backend.database.database import init_db

        passed = callable(init_db) and init_db()
        print_result("database init function exists and works", passed)
        return passed
    except Exception as exc:
        print_result("database init function exists and works", False, str(exc))
        return False


def verify_database_health() -> bool:
    try:
        from backend.database.db_health import DatabaseHealthService

        status = DatabaseHealthService().get_database_status()
        passed = status["connected"] is True and status["database_type"] == "sqlite"
        print_result("database health service works with SQLite fallback", passed, str(status) if not passed else "")
        return passed
    except Exception as exc:
        print_result("database health service works with SQLite fallback", False, str(exc))
        return False


def verify_records_exist() -> bool:
    try:
        from backend.database.models import ExecutionLogRecord, TradeRecord

        passed = TradeRecord.__tablename__ == "trade_records" and ExecutionLogRecord.__tablename__ == "execution_log_records"
        print_result("TradeRecord and ExecutionLogRecord models exist", passed)
        return passed
    except Exception as exc:
        print_result("TradeRecord and ExecutionLogRecord models exist", False, str(exc))
        return False


def verify_persistence_service() -> bool:
    try:
        from backend.database.persistence_service import PersistenceService

        service = PersistenceService()
        try:
            passed = service.initialize_database()
        finally:
            service.close()
        print_result("PersistenceService can be instantiated", passed)
        return passed
    except Exception as exc:
        print_result("PersistenceService can be instantiated", False, str(exc))
        return False


def main() -> int:
    print("Day 7 Database Persistence Verification")
    print("=" * 39)

    checks = [
        verify_path("backend/database/database.py", "database.py exists"),
        verify_path("backend/database/base.py", "base.py exists"),
        verify_path("backend/database/models.py", "models.py exists"),
        verify_path("backend/database/repositories.py", "repositories.py exists"),
        verify_path("backend/database/persistence_service.py", "persistence_service.py exists"),
        verify_path("backend/database/db_health.py", "db_health.py exists"),
        verify_path("backend/database/seed.py", "seed.py exists"),
        verify_path("backend/api/database_routes.py", "database_routes.py exists"),
        verify_app_routes(),
        verify_base_import(),
        verify_database_init(),
        verify_database_health(),
        verify_records_exist(),
        verify_persistence_service(),
    ]

    print("=" * 39)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

