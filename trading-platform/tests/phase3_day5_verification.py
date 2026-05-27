import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_registry() -> bool:
    files = [
        "backend/replay/client_symbol_models.py",
        "backend/replay/client_symbol_registry.py",
        "backend/replay/symbol_normalizer.py",
        "backend/replay/symbol_metadata_service.py",
        "backend/replay/multi_symbol_replay_service.py",
        "docs/phase-3-day-5-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.replay.client_symbol_registry import ClientSymbolRegistry

        registry = ClientSymbolRegistry()
        symbols = {item.canonical_symbol for item in registry.list_supported_symbols()}
        passed = files_ok and {"EURUSD", "XAUUSD", "NIFTY50"} <= symbols
        return show("Client symbol files exist and registry lists target instruments", passed)
    except Exception as exc:
        return show("Client symbol files exist and registry lists target instruments", False, str(exc))


def verify_normalization_and_metadata() -> bool:
    try:
        from backend.replay.client_symbol_registry import ClientSymbolRegistry
        from backend.replay.symbol_metadata_service import SymbolMetadataService
        from backend.replay.symbol_normalizer import SymbolNormalizer

        normalizer = SymbolNormalizer()
        registry = ClientSymbolRegistry()
        metadata = SymbolMetadataService(registry)
        aliases_ok = (
            normalizer.normalize("EUR/USD") == "EURUSD"
            and normalizer.normalize("EUR-USD") == "EURUSD"
            and normalizer.normalize("eurusd") == "EURUSD"
            and normalizer.normalize("XAU/USD") == "XAUUSD"
            and normalizer.normalize("GOLD") == "XAUUSD"
            and normalizer.normalize("gold") == "XAUUSD"
            and normalizer.normalize("NIFTY 50") == "NIFTY50"
            and normalizer.normalize("NIFTY") == "NIFTY50"
            and normalizer.normalize("nifty") == "NIFTY50"
        )
        unsupported = registry.resolve_symbol("BTCUSD")
        passed = (
            aliases_ok
            and registry.resolve_symbol("GOLD").canonical_symbol == "XAUUSD"
            and registry.resolve_symbol("NIFTY").market_type == "INDIAN_INDEX"
            and unsupported.supported is False
            and metadata.get_metadata("EUR/USD").market_type == "FOREX"
            and metadata.get_metadata("XAUUSD").market_type == "COMMODITY_CFD"
            and metadata.get_metadata("NIFTY").market_type == "INDIAN_INDEX"
        )
        return show("Aliases normalize correctly and metadata is available", passed)
    except Exception as exc:
        return show("Aliases normalize correctly and metadata is available", False, str(exc))


def verify_symbol_specific_loader() -> bool:
    try:
        from backend.replay.historical_replay_loader import HistoricalReplayLoader

        loader = HistoricalReplayLoader()
        eur = loader.load_candles("EUR/USD", "M15", limit=5)
        xau = loader.load_candles("GOLD", "M15", limit=5)
        nifty = loader.load_candles("NIFTY", "M15", limit=5)
        eur_close = eur[0]["close"]
        xau_close = xau[0]["close"]
        nifty_close = nifty[0]["close"]
        passed = (
            1.08 <= eur_close <= 1.12
            and 2300 <= xau_close <= 2500
            and 21000 <= nifty_close <= 23000
            and eur == loader.load_candles("EURUSD", "M15", limit=5)
            and xau == loader.load_candles("XAUUSD", "M15", limit=5)
            and nifty == loader.load_candles("NIFTY50", "M15", limit=5)
        )
        return show("Historical loader generates deterministic symbol-specific price scales", passed)
    except Exception as exc:
        return show("Historical loader generates deterministic symbol-specific price scales", False, str(exc))


def verify_replay_service_symbols() -> bool:
    try:
        from backend.replay.replay_models import ReplayRequest
        from backend.replay.replay_service import ReplayService

        service = ReplayService()
        runs = [
            service.run_replay(symbol, request=ReplayRequest(symbol=symbol, window_size=30, step_size=10, max_steps=1))
            for symbol in ["EUR/USD", "GOLD", "NIFTY"]
        ]
        unsupported_failed = False
        try:
            service.run_replay("BTCUSD", request=ReplayRequest(symbol="XAUUSD", window_size=30, step_size=10, max_steps=1))
        except ValueError:
            unsupported_failed = True
        comparison = service.compare_client_symbols("M15")
        passed = (
            {run.symbol for run in runs} == {"EURUSD", "XAUUSD", "NIFTY50"}
            and all(run.simulation_only is True and run.live_execution_enabled is False for run in runs)
            and unsupported_failed
            and comparison.simulation_only is True
            and comparison.live_execution_enabled is False
        )
        return show("Replay service runs each client symbol and rejects unsupported symbols safely", passed)
    except Exception as exc:
        return show("Replay service runs each client symbol and rejects unsupported symbols safely", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        routes = {route.path for route in app.routes}
        expected_routes = {
            "/replay/symbols",
            "/replay/symbols/{symbol}",
            "/replay/run-all-client-symbols",
            "/replay/compare/client-symbols",
            "/replay/status",
        }
        symbols = client.get("/replay/symbols")
        gold = client.get("/replay/symbols/GOLD")
        unsupported = client.get("/replay/symbols/BTCUSD")
        eur_run = client.post(
            "/replay/run/EUR-USD",
            json={"window_size": 30, "step_size": 10, "max_steps": 1, "simulation_only": True},
        )
        all_run = client.post("/replay/run-all-client-symbols?timeframe=M15")
        comparison = client.get("/replay/compare/client-symbols?timeframe=M15")
        safety = client.get("/system/safety-scan").json()
        passed = (
            expected_routes <= routes
            and symbols.status_code == 200
            and len(symbols.json()) == 3
            and gold.json()["canonical_symbol"] == "XAUUSD"
            and unsupported.json()["supported"] is False
            and eur_run.status_code == 200
            and eur_run.json()["symbol"] == "EURUSD"
            and eur_run.json()["simulation_only"] is True
            and eur_run.json()["live_execution_enabled"] is False
            and all_run.status_code == 200
            and set(all_run.json()["symbols"]) == {"EURUSD", "XAUUSD", "NIFTY50"}
            and all_run.json()["simulation_only"] is True
            and comparison.status_code == 200
            and comparison.json()["simulation_only"] is True
            and comparison.json()["live_execution_enabled"] is False
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
        )
        return show("Replay symbol API is JSON-safe and preserves simulation-only safety", passed)
    except Exception as exc:
        return show("Replay symbol API is JSON-safe and preserves simulation-only safety", False, str(exc))


def main() -> int:
    print("Phase 3 Day 5 Multi-Symbol Replay Verification")
    print("=" * 52)
    checks = [
        verify_files_and_registry(),
        verify_normalization_and_metadata(),
        verify_symbol_specific_loader(),
        verify_replay_service_symbols(),
        verify_api_and_safety(),
    ]
    print("=" * 52)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
