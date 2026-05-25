import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


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


def sample_candles() -> list[dict]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    prices = [
        (99, 100, 98, 99),
        (99, 102, 99, 101),
        (101, 101, 98.5, 100),
        (100, 104.00, 100, 103),
        (103, 102, 99, 100),
        (100, 103, 97.00, 98),
        (98, 103, 100, 102),
        (102, 104.05, 101, 103),
        (103, 103, 99, 100),
        (100, 102, 98, 99),
        (99, 103, 97.05, 102),
        (102, 104, 99, 103),
        (101, 111, 100, 110),
    ]
    return [
        {
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "time": start + timedelta(minutes=index * 15),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
        }
        for index, (open_price, high, low, close) in enumerate(prices)
    ]


def verify_routes() -> bool:
    try:
        from backend.main import app

        paths = {route.path for route in app.routes}
        required = {
            "/health",
            "/status",
            "/system/status",
            "/trade-journal/status",
            "/institutional/status",
            "/institutional/context/{symbol}",
            "/institutional/liquidity/{symbol}",
            "/institutional/bias/{symbol}",
        }
        missing = sorted(required - paths)
        passed = not missing
        print_result("Institutional router is registered and Phase 1 routes remain present", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("Institutional router is registered and Phase 1 routes remain present", False, str(exc))
        return False


def verify_swing_detector() -> bool:
    try:
        from backend.institutional_intelligence.swing_detector import SwingDetector

        detector = SwingDetector()
        swings = detector.detect_swings(sample_candles())
        passed = (
            len(swings) >= 4
            and detector.get_latest_swing_high(sample_candles()) is not None
            and detector.get_latest_swing_low(sample_candles()) is not None
            and detector.detect_swings([{"bad": True}]) == []
        )
        print_result("SwingDetector identifies highs/lows and handles malformed input", passed)
        return passed
    except Exception as exc:
        print_result("SwingDetector identifies highs/lows and handles malformed input", False, str(exc))
        return False


def verify_liquidity_mapper() -> bool:
    try:
        from backend.institutional_intelligence.liquidity_mapper import LiquidityMapper
        from backend.institutional_intelligence.swing_detector import SwingDetector

        swings = SwingDetector().detect_swings(sample_candles())
        mapper = LiquidityMapper()
        equal_highs = mapper.detect_equal_highs(swings)
        equal_lows = mapper.detect_equal_lows(swings)
        pools = mapper.map_liquidity_pools(sample_candles(), swings)
        passed = (
            bool(equal_highs)
            and bool(equal_lows)
            and any(pool.liquidity_type == "EXTERNAL_LIQUIDITY" for pool in pools)
            and all(pool.symbol == "XAUUSD" for pool in pools)
        )
        print_result("LiquidityMapper identifies equal and structural liquidity pools", passed)
        return passed
    except Exception as exc:
        print_result("LiquidityMapper identifies equal and structural liquidity pools", False, str(exc))
        return False


def verify_bias_zone_displacement() -> bool:
    try:
        from backend.institutional_intelligence.displacement_detector import DisplacementDetector
        from backend.institutional_intelligence.premium_discount import PremiumDiscountAnalyzer
        from backend.institutional_intelligence.smc_models import SwingPoint
        from backend.institutional_intelligence.structure_bias import StructureBiasAnalyzer

        now = datetime.now(timezone.utc)
        swings = [
            SwingPoint(index=1, timestamp=now, price=100, type="HIGH", strength=1),
            SwingPoint(index=2, timestamp=now, price=95, type="LOW", strength=1),
            SwingPoint(index=3, timestamp=now, price=105, type="HIGH", strength=1),
            SwingPoint(index=4, timestamp=now, price=98, type="LOW", strength=1),
        ]
        bias = StructureBiasAnalyzer().analyze_bias(swings)
        zone = PremiumDiscountAnalyzer().calculate_zone(sample_candles())
        displacement = DisplacementDetector().detect_displacement(sample_candles())
        passed = bias.bias == "BULLISH" and zone.zone == "PREMIUM" and bool(displacement)
        print_result("Bias, premium/discount, and displacement analytics return useful context", passed)
        return passed
    except Exception as exc:
        print_result("Bias, premium/discount, and displacement analytics return useful context", False, str(exc))
        return False


def verify_context_and_service() -> bool:
    try:
        from backend.institutional_intelligence.institutional_context import InstitutionalContextBuilder
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No terminal required for verification.")

            def close(self):
                return None

        context = InstitutionalContextBuilder().build_context("XAUUSD", "M15", sample_candles())
        safe = SMCService(market_data_service=UnavailableData()).analyze_symbol("XAUUSD")
        passed = (
            context.symbol == "XAUUSD"
            and bool(context.swings)
            and context.premium_discount.zone == "PREMIUM"
            and safe.symbol == "XAUUSD"
            and safe.swings == []
        )
        print_result("Institutional context and SMCService degrade safely without MT5", passed)
        return passed
    except Exception as exc:
        print_result("Institutional context and SMCService degrade safely without MT5", False, str(exc))
        return False


def verify_api_and_health() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/institutional/status")
        context = client.get("/institutional/context/XAUUSD")
        liquidity = client.get("/institutional/liquidity/XAUUSD")
        bias = client.get("/institutional/bias/XAUUSD")
        zone = client.get("/institutional/premium-discount/XAUUSD")
        displacement = client.get("/institutional/displacement/XAUUSD")
        readiness = client.get("/system/readiness")
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and all(response.status_code == 200 for response in [context, liquidity, bias, zone, displacement])
            and any(
                module["module_name"] == "institutional_intelligence"
                for module in readiness.json()["modules"]
            )
        )
        print_result("Institutional APIs are JSON-safe and registered in system health", passed)
        return passed
    except Exception as exc:
        print_result("Institutional APIs are JSON-safe and registered in system health", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 1 Institutional Intelligence Verification")
    print("=" * 50)
    checks = [
        verify_path("backend/institutional_intelligence", "institutional_intelligence package exists", is_dir=True),
        verify_path("backend/institutional_intelligence/smc_models.py", "smc_models.py exists"),
        verify_path("backend/institutional_intelligence/swing_detector.py", "swing_detector.py exists"),
        verify_path("backend/institutional_intelligence/liquidity_mapper.py", "liquidity_mapper.py exists"),
        verify_path("backend/institutional_intelligence/structure_bias.py", "structure_bias.py exists"),
        verify_path("backend/institutional_intelligence/premium_discount.py", "premium_discount.py exists"),
        verify_path("backend/institutional_intelligence/displacement_detector.py", "displacement_detector.py exists"),
        verify_path("backend/institutional_intelligence/institutional_context.py", "institutional_context.py exists"),
        verify_path("backend/institutional_intelligence/smc_service.py", "smc_service.py exists"),
        verify_path("backend/api/institutional_routes.py", "institutional_routes.py exists"),
        verify_routes(),
        verify_swing_detector(),
        verify_liquidity_mapper(),
        verify_bias_zone_displacement(),
        verify_context_and_service(),
        verify_api_and_health(),
    ]
    print("=" * 50)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
