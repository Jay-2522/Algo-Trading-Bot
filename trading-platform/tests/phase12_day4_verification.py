import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def seed_smc_candles(client: TestClient) -> None:
    base = datetime.now(timezone.utc).replace(microsecond=0)
    candles = [
        (100.0, 102.0, 99.0, 101.0),
        (101.0, 106.0, 100.0, 105.0),
        (105.0, 105.0, 101.0, 102.0),
        (102.0, 103.0, 97.0, 98.0),
        (104.0, 105.0, 102.0, 103.0),
        (104.0, 108.0, 104.0, 107.0),
        (107.0, 109.0, 104.0, 105.0),
    ]
    for index, (open_price, high, low, close) in enumerate(candles):
        client.post(
            "/nifty50/market-data/ingest-candle",
            json={
                "symbol": "NIFTY50",
                "timeframe": "M15",
                "timestamp": (base + timedelta(minutes=15 * index)).isoformat(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 100 + index,
                "placeholder": False,
            },
        )


def verify_files() -> bool:
    files = [
        "backend/nifty50/nifty_swing_detector.py",
        "backend/nifty50/nifty_bos_detector.py",
        "backend/nifty50/nifty_choch_detector.py",
        "backend/nifty50/nifty_regime_detector.py",
        "backend/nifty50/nifty_confidence_engine.py",
        "docs/phase-12-day-4-progress.md",
        "docs/nifty50-smc-detection.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Swing, BOS, CHOCH, regime, confidence detectors and docs exist", not missing, ", ".join(missing))


def verify_smc_detection() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        seed_smc_candles(client)
        liquidity = client.get("/nifty50/strategy/liquidity").json()
        structure = client.get("/nifty50/strategy/structure").json()
        fvg = client.get("/nifty50/strategy/fvg").json()
        order_block = client.get("/nifty50/strategy/order-block").json()
        snapshot = client.get("/nifty50/strategy/snapshot").json()
        passed = (
            liquidity["placeholder"] is False
            and liquidity["sweep_detected"] is True
            and liquidity["sweep_direction"] in {"BUY_SIDE", "SELL_SIDE"}
            and structure["placeholder"] is False
            and len(structure["swing_highs"]) >= 1
            and len(structure["swing_lows"]) >= 1
            and structure["structure_bias"] in {"BULLISH", "BEARISH", "NEUTRAL"}
            and fvg["placeholder"] is False
            and fvg["active_fvg_detected"] is True
            and fvg["fvg_direction"] in {"BULLISH", "BEARISH"}
            and order_block["placeholder"] is False
            and (order_block["bullish_order_blocks"] or order_block["bearish_order_blocks"])
            and snapshot["placeholder"] is False
            and snapshot["strategy_bias"] in {"BULLISH", "BEARISH", "NEUTRAL"}
            and snapshot["regime"] in {"TRENDING_BULLISH", "TRENDING_BEARISH", "RANGING", "UNKNOWN"}
            and 0 <= snapshot["confidence"] <= 100
        )
        return show("Liquidity, swing, FVG, order block, regime, bias, and confidence detections work", passed)
    except Exception as exc:
        return show("Liquidity, swing, FVG, order block, regime, bias, and confidence detections work", False, str(exc))


def verify_new_routes_and_readiness() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        seed_smc_candles(client)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        required = {"/nifty50/strategy/regime", "/nifty50/strategy/confidence", "/nifty50/strategy/bias"}
        regime = client.get("/nifty50/strategy/regime").json()
        confidence = client.get("/nifty50/strategy/confidence").json()
        bias = client.get("/nifty50/strategy/bias").json()
        readiness = client.get("/nifty50/readiness").json()
        instruments = client.get("/client-analytics/executive/instruments").json()
        summary = client.get("/client-analytics/executive/summary").json()
        nifty = next((item for item in instruments["instruments"] if item["symbol"] == "NIFTY50"), {})
        passed = (
            required <= route_paths
            and regime["regime"] in {"TRENDING_BULLISH", "TRENDING_BEARISH", "RANGING", "UNKNOWN"}
            and 0 <= confidence["confidence"] <= 100
            and bias["strategy_bias"] in {"BULLISH", "BEARISH", "NEUTRAL"}
            and readiness["status"] in {"SMC_INTELLIGENCE_READY", "RISK_QUALIFICATION_READY", "EXECUTION_BRIDGE_READY", "ANALYTICS_INTEGRATED"}
            and readiness["strategy_ready"] is True
            and readiness["execution_ready"] is False
            and readiness["broker_execution_enabled"] is False
            and nifty["status"] in {"SMC_INTELLIGENCE_READY", "RISK_QUALIFICATION_READY", "EXECUTION_BRIDGE_READY", "ANALYTICS_INTEGRATED"}
            and nifty["ready"] is False
            and summary["nifty50_ready"] is False
            and summary["overall_completion_percentage"] in {96, 97, 98, 99}
        )
        return show("Regime, confidence, bias routes and SMC readiness/executive status work", passed)
    except Exception as exc:
        return show("Regime, confidence, bias routes and SMC readiness/executive status work", False, str(exc))


def verify_no_broker_api_or_execution() -> bool:
    try:
        forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "yfinance", "kiteconnect", "smartapi", "dhanhq", "fyers_apiv3", "upstox_client"]
        offenders = []
        for path in (PROJECT_ROOT / "backend" / "nifty50").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in forbidden:
                if token.lower() in text:
                    offenders.append(f"{path.name}:{token}")
        token = "mt5." + "order_send"
        order_matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                order_matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        return show(
            "No broker APIs, no live execution, and no new mt5.order_send added",
            not offenders and order_matches == ["backend/demo_execution/mt5_demo_executor.py"],
            ", ".join(offenders + order_matches),
        )
    except Exception as exc:
        return show("No broker APIs, no live execution, and no new mt5.order_send added", False, str(exc))


def main() -> int:
    print("Phase 12 Day 4 NIFTY50 Structure Intelligence & SMC Detection Verification")
    print("=" * 82)
    checks = [
        verify_files(),
        verify_smc_detection(),
        verify_new_routes_and_readiness(),
        verify_no_broker_api_or_execution(),
    ]
    print("=" * 82)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
