import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REAL_ENGINE_PATH = PROJECT_ROOT / "backend/strategy/real_signal_engine_service.py"
CLIENT_ENGINE_PATH = PROJECT_ROOT / "backend/strategy/client_signal_engine.py"
ROUTES_PATH = PROJECT_ROOT / "backend/api/client_signal_engine_routes.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"
VANTAGE_PATH = PROJECT_ROOT / "backend/mt5_demo/vantage_xauusd_demo_validation_service.py"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def candle(index: int, open_price: float, high: float, low: float, close: float) -> dict:
    return {"time": f"2026-01-01T00:{index % 60:02d}:00+00:00", "open": open_price, "high": high, "low": low, "close": close, "tick_volume": 100}


def trend_candles(start: float, step: float, count: int = 60) -> list[dict]:
    candles = []
    price = start
    for index in range(count):
        open_price = price
        close = price + step
        high = max(open_price, close) + abs(step) * 0.6
        low = min(open_price, close) - abs(step) * 0.6
        candles.append(candle(index, open_price, high, low, close))
        price = close
    return candles


def bullish_m15() -> list[dict]:
    candles = trend_candles(100.0, 0.05, 57)
    candles[-8] = candle(52, 102.5, 102.7, 101.8, 102.0)  # bearish order block
    candles[-5] = candle(55, 103.0, 103.4, 102.9, 103.3)
    candles[-3] = candle(57, 103.8, 104.0, 103.7, 103.9)
    candles[-1] = candle(59, 103.9, 105.2, 99.7, 105.0)  # liquidity sweep + BOS
    return candles


def bearish_m15() -> list[dict]:
    candles = trend_candles(100.0, -0.05, 57)
    candles[-8] = candle(52, 97.5, 98.2, 97.3, 98.0)  # bullish order block
    candles[-5] = candle(55, 97.0, 97.1, 96.4, 96.5)
    candles[-3] = candle(57, 96.0, 96.1, 95.7, 95.8)
    candles[-1] = candle(59, 95.8, 100.3, 94.8, 95.0)  # liquidity sweep + BOS
    return candles


def engine_with_session():
    from backend.strategy.real_signal_engine_service import RealSignalEngineService

    service = RealSignalEngineService()
    service._session_context = lambda: {"name": "London/New York overlap", "valid": True, "quality": 1.0}  # type: ignore[method-assign]
    return service


def verify_files_and_routes() -> bool:
    route_text = ROUTES_PATH.read_text(encoding="utf-8")
    client_text = CLIENT_ENGINE_PATH.read_text(encoding="utf-8")
    required = [
        "RealSignalEngineService",
        "REAL_SMC_MULTI_TIMEFRAME_SIGNAL_ENGINE",
        '@router.get("/latest")',
        '@router.get("/debug/{symbol}")',
        "SMC_MULTI_TIMEFRAME_RULE_ENGINE",
    ]
    missing = [item for item in required if item not in route_text + client_text + REAL_ENGINE_PATH.read_text(encoding="utf-8")]
    return show("Real signal engine files and latest route exist", not missing, ", ".join(missing))


def verify_buy_signal_generation() -> bool:
    service = engine_with_session()
    signal = service.analyze_from_candles(
        "XAUUSD",
        {"H4": trend_candles(90, 0.2), "H1": trend_candles(95, 0.15), "M15": bullish_m15()},
        {"status": "OK", "bid": 105.0, "ask": 105.2, "spread": 0.2, "freshness": "READY"},
    )
    passed = (
        signal["signal"] == "BUY"
        and signal["confidence"] >= 75
        and signal["entry"] > 0
        and signal["stop_loss"] < signal["entry"] < signal["take_profit"]
        and signal["risk_reward"] >= 1.5
        and signal["execution_status"] == "READY_FOR_PREVIEW"
        and signal["strategy_components"]["liquidity_sweep"] is True
        and signal["strategy_components"]["bos"] is True
    )
    return show("XAUUSD BUY signal generation produces complete trade plan", passed, str(signal))


def verify_sell_signal_generation() -> bool:
    service = engine_with_session()
    signal = service.analyze_from_candles(
        "EURUSD",
        {"H4": trend_candles(1.2, -0.001), "H1": trend_candles(1.18, -0.0008), "M15": bearish_m15()},
        {"status": "OK", "bid": 95.0, "ask": 95.01, "spread": 0.0001, "freshness": "READY"},
    )
    passed = (
        signal["signal"] == "SELL"
        and signal["confidence"] >= 75
        and signal["take_profit"] < signal["entry"] < signal["stop_loss"]
        and signal["risk_reward"] >= 1.5
        and signal["execution_status"] == "READY_FOR_PREVIEW"
    )
    return show("EURUSD SELL signal generation produces complete trade plan", passed, str(signal))


def verify_component_detectors_and_wait_honesty() -> bool:
    service = engine_with_session()
    wait = service.analyze_from_candles(
        "EURUSD",
        {"H4": trend_candles(1.1, 0.0), "H1": trend_candles(1.1, 0.0), "M15": trend_candles(1.1, 0.0)},
        {"status": "OK", "bid": 1.1, "ask": 1.1001, "spread": 0.0001, "freshness": "READY"},
    )
    smc_buy = service._smc_components(bullish_m15(), "BUY")
    smc_sell = service._smc_components(bearish_m15(), "SELL")
    passed = (
        wait["signal"] == "WAIT"
        and "timeframe alignment" in wait["reason"].lower()
        and smc_buy["liquidity_sweep"] is True
        and smc_buy["bos"] is True
        and smc_buy["fvg"] is True
        and smc_buy["order_block"] is True
        and smc_sell["liquidity_sweep"] is True
        and smc_sell["bos"] is True
    )
    return show("SMC detectors work and WAIT is honest when alignment is missing", passed, str(wait))


def verify_live_signal_routes() -> bool:
    from backend.main import app

    client = TestClient(app)
    eurusd = client.get("/client-signals-engine/EURUSD")
    xauusd = client.get("/client-signals-engine/XAUUSD")
    status = client.get("/client-signals-engine/status")
    latest = client.get("/client-signals-engine/latest")
    valid = True
    for response in [eurusd, xauusd]:
        payload = response.json()
        valid = valid and payload["signal"] in {"BUY", "SELL", "WAIT"} and "setup_reason" in payload and "market_structure_state" in payload
        candle_source = payload.get("candle_source", {})
        timeframes = candle_source.get("timeframes", {})
        valid = valid and {"M15", "H1", "H4"}.issubset(set(timeframes))
        valid = valid and all("returned_count" in timeframes[item] and "last_candle_timestamp" in timeframes[item] for item in ["M15", "H1", "H4"])
        valid = valid and "server" in candle_source and "account_login" in candle_source and "broker_source" in candle_source
        if payload["signal"] == "WAIT":
            confidence = payload.get("confidence")
            valid = valid and payload.get("entry") is None and (confidence is None or 0 <= confidence < 75)
        else:
            valid = valid and payload.get("confidence", 0) >= 75 and payload.get("risk_reward", 0) >= 1.5
    passed = eurusd.status_code == xauusd.status_code == status.status_code == latest.status_code == 200 and valid
    return show("Live EURUSD/XAUUSD signal routes return real structured signals or honest WAIT", passed)


def verify_debug_diagnostics_routes() -> bool:
    from backend.main import app

    client = TestClient(app)
    responses = [client.get("/client-signals-engine/debug/EURUSD"), client.get("/client-signals-engine/debug/XAUUSD")]
    required_components = {
        "trend_alignment_score",
        "bos_score",
        "choch_score",
        "liquidity_sweep_score",
        "fvg_score",
        "order_block_score",
        "session_score",
        "spread_score",
        "volatility_score",
        "rr_score",
    }
    valid = True
    details = []
    for response in responses:
        payload = response.json()
        details.append(payload.get("symbol"))
        components = payload.get("confidence_components", {})
        counts = payload.get("candles_analyzed", {})
        raw_trend = payload.get("raw_trend_direction", {})
        calculation = payload.get("final_confidence_calculation", {})
        valid = valid and response.status_code == 200
        valid = valid and required_components.issubset(set(components))
        valid = valid and all(key in counts for key in ["total_m15_candles_analyzed", "total_h1_candles_analyzed", "total_h4_candles_analyzed"])
        valid = valid and {"M15", "H1", "H4"}.issubset(set(raw_trend))
        valid = valid and payload.get("market_regime") in {"trend", "range", "chop", "unknown"}
        valid = valid and "final_confidence" in calculation and "formula" in calculation
        valid = valid and "exact_reason_buy_not_generated" in payload and "exact_reason_sell_not_generated" in payload
        valid = valid and payload.get("diagnostics_only") is True and payload.get("strategy_logic_changed") is False and payload.get("thresholds_changed") is False
        valid = valid and components["rr_score"].get("included_in_confidence") is False
        valid = valid and components["choch_score"].get("included_in_confidence") is False
    return show("Debug diagnostics routes expose component scoring, trend, regime, candle counts, and rejection reasons", valid, ", ".join(details))


def verify_dashboard_and_preview_integration() -> bool:
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    vantage = VANTAGE_PATH.read_text(encoding="utf-8")
    required = [
        "setup_reason",
        "market_structure_state",
        "READY_FOR_PREVIEW",
        "/mt5-demo/vantage/${symbolPath}/test-order/preview",
        "/mt5-demo/vantage/${symbolPath}/test-order",
        "allow_eurusd_vantage_demo_test",
    ]
    missing = [item for item in required if item not in dashboard + api + vantage]
    return show("Dashboard and preview integration use generated signal trade plans", not missing, ", ".join(missing))


def verify_no_unrestricted_order_send() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    real_text = REAL_ENGINE_PATH.read_text(encoding="utf-8")
    forbidden = ["forced_signal", '"live_execution_enabled": True', '"broker_execution_enabled": True', "order_send("]
    present = [item for item in forbidden if item in real_text]
    return show("No fake/forced signals and no new unrestricted order_send", sorted(matches) == allowed and not present, ", ".join(matches + present))


def main() -> int:
    print("Phase 21 Real Signal Engine Activation Verification")
    print("=" * 78)
    checks = [
        verify_files_and_routes(),
        verify_buy_signal_generation(),
        verify_sell_signal_generation(),
        verify_component_detectors_and_wait_honesty(),
        verify_live_signal_routes(),
        verify_debug_diagnostics_routes(),
        verify_dashboard_and_preview_integration(),
        verify_no_unrestricted_order_send(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
