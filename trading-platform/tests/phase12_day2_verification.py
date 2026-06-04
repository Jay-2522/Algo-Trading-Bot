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
        "backend/nifty50/nifty_strategy_models.py",
        "backend/nifty50/nifty_liquidity_service.py",
        "backend/nifty50/nifty_structure_service.py",
        "backend/nifty50/nifty_fvg_service.py",
        "backend/nifty50/nifty_order_block_service.py",
        "backend/nifty50/nifty_strategy_service.py",
        "docs/phase-12-day-2-progress.md",
        "docs/nifty50-strategy-foundation.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("NIFTY strategy models and services exist", not missing, ", ".join(missing))


def verify_strategy_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        required = {
            "/nifty50/strategy/status",
            "/nifty50/strategy/liquidity",
            "/nifty50/strategy/structure",
            "/nifty50/strategy/fvg",
            "/nifty50/strategy/order-block",
            "/nifty50/strategy/snapshot",
            "/nifty50/strategy/analyze",
        }
        status = client.get("/nifty50/strategy/status")
        liquidity = client.get("/nifty50/strategy/liquidity")
        structure = client.get("/nifty50/strategy/structure")
        fvg = client.get("/nifty50/strategy/fvg")
        order_block = client.get("/nifty50/strategy/order-block")
        snapshot = client.get("/nifty50/strategy/snapshot")
        analyze = client.post("/nifty50/strategy/analyze")
        status_payload = status.json()
        liquidity_payload = liquidity.json()
        structure_payload = structure.json()
        fvg_payload = fvg.json()
        order_block_payload = order_block.json()
        snapshot_payload = snapshot.json()
        analyze_payload = analyze.json()
        passed = (
            required <= route_paths
            and status.status_code == 200
            and liquidity.status_code == 200
            and structure.status_code == 200
            and fvg.status_code == 200
            and order_block.status_code == 200
            and snapshot.status_code == 200
            and analyze.status_code == 200
            and status_payload["status"] in {"STRATEGY_FOUNDATION_READY", "SMC_INTELLIGENCE_READY"}
            and status_payload["broker_execution_enabled"] is False
            and liquidity_payload["placeholder"] is True
            and liquidity_payload["sweep_detected"] is False
            and liquidity_payload["previous_day_high"] is None
            and liquidity_payload["previous_day_low"] is None
            and structure_payload["placeholder"] is True
            and structure_payload["bos_detected"] is False
            and structure_payload["choch_detected"] is False
            and fvg_payload["placeholder"] is True
            and fvg_payload["active_fvg_detected"] is False
            and order_block_payload["placeholder"] is True
            and order_block_payload["active_order_block"] is None
            and snapshot_payload["placeholder"] is True
            and snapshot_payload["strategy_bias"] == "NEUTRAL"
            and snapshot_payload["regime"] == "UNKNOWN"
            and snapshot_payload["confidence"] == 0
            and analyze_payload["placeholder"] is True
            and analyze_payload["confidence"] == 0
        )
        return show("NIFTY strategy routes and placeholder outputs work", passed)
    except Exception as exc:
        return show("NIFTY strategy routes and placeholder outputs work", False, str(exc))


def verify_no_fake_market_data_or_broker_calls() -> bool:
    try:
        forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "yfinance", "kiteconnect", "smartapi", "dhanhq", "fyers_apiv3", "upstox_client"]
        offenders = []
        for path in (PROJECT_ROOT / "backend" / "nifty50").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in forbidden:
                if token.lower() in text:
                    offenders.append(f"{path.name}:{token}")
        fake_prices = []
        price_tokens = ["22000", "22500", "23000", "nifty price ="]
        for path in (PROJECT_ROOT / "backend" / "nifty50").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in price_tokens:
                if token in text:
                    fake_prices.append(f"{path.name}:{token}")
        return show("No fake NIFTY market data and no broker API calls added", not offenders and not fake_prices, ", ".join(offenders + fake_prices))
    except Exception as exc:
        return show("No fake NIFTY market data and no broker API calls added", False, str(exc))


def verify_readiness_and_executive_update() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        readiness = client.get("/nifty50/readiness").json()
        instruments = client.get("/client-analytics/executive/instruments").json()
        summary = client.get("/client-analytics/executive/summary").json()
        nifty = next((item for item in instruments["instruments"] if item["symbol"] == "NIFTY50"), {})
        passed = (
            readiness["status"] in {"STRATEGY_FOUNDATION_READY", "MARKET_DATA_READY", "SMC_INTELLIGENCE_READY", "RISK_QUALIFICATION_READY", "EXECUTION_BRIDGE_READY"}
            and readiness["execution_ready"] is False
            and readiness["live_execution_enabled"] is False
            and readiness["broker_execution_enabled"] is False
            and nifty["status"] in {"STRATEGY_FOUNDATION_READY", "MARKET_DATA_READY", "SMC_INTELLIGENCE_READY", "RISK_QUALIFICATION_READY", "EXECUTION_BRIDGE_READY"}
            and nifty["ready"] is False
            and (
                "market data" in nifty["reason"].lower()
                or "risk qualification" in nifty["reason"].lower()
                or "execution bridge" in nifty["reason"].lower()
            )
            and summary["nifty50_ready"] is False
            and 92 <= summary["overall_completion_percentage"] < 100
        )
        return show("Readiness and executive dashboard upgraded honestly", passed)
    except Exception as exc:
        return show("Readiness and executive dashboard upgraded honestly", False, str(exc))


def verify_no_order_send() -> bool:
    try:
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        return show("No new mt5.order_send added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))
    except Exception as exc:
        return show("No new mt5.order_send added", False, str(exc))


def main() -> int:
    print("Phase 12 Day 2 NIFTY50 Strategy Foundation Verification")
    print("=" * 68)
    checks = [
        verify_files(),
        verify_strategy_routes(),
        verify_no_fake_market_data_or_broker_calls(),
        verify_readiness_and_executive_update(),
        verify_no_order_send(),
    ]
    print("=" * 68)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
