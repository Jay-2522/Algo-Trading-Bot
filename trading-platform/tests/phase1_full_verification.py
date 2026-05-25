import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_PACKAGES = [
    "market_data",
    "strategy_engine",
    "risk_engine",
    "execution_engine",
    "broker_integrations/mt5",
    "database",
    "ai_engine",
    "news_engine",
    "orchestration",
    "backtesting",
    "streaming",
    "trading_loop",
    "trade_journal",
    "system_health",
]


def main() -> int:
    try:
        for package in REQUIRED_PACKAGES:
            if not (PROJECT_ROOT / "backend" / package).is_dir():
                return 1

        from backend.backtesting.backtest_service import BacktestService
        from backend.main import app
        from backend.trade_journal.journal_service import JournalService
        from backend.trading_loop.loop_service import TradingLoopService
        from backend.system_health.system_health_service import SystemHealthService

        if (PROJECT_ROOT / "backend/main.py").read_text(encoding="utf-8").count("app = FastAPI(") != 1:
            return 1

        service = SystemHealthService(app)
        if not service.run_safety_scan().passed:
            return 1
        if not service.audit_routes().passed:
            return 1
        readiness = service.get_readiness()
        if readiness.overall_status != "READY" or readiness.live_execution_enabled:
            return 1
        if len(readiness.modules) != 15:
            return 1

        BacktestService()
        JournalService()
        TradingLoopService()
        if service.get_system_status()["live_execution_enabled"]:
            return 1

        print("PHASE 1 VERIFICATION PASS")
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
