import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


STATUS_ENDPOINTS = [
    "/health",
    "/status",
    "/nifty50/status",
    "/nifty50/readiness",
    "/nifty50/execution/status",
    "/client-analytics/overview",
    "/client-analytics/symbols",
    "/client-analytics/accounts",
    "/client-analytics/reports/daily",
    "/client-analytics/executive/readiness",
]

SAFETY_FALSE_KEYS = {"execution_allowed", "live_execution_enabled", "broker_execution_enabled"}


class ValidationResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.warnings: list[str] = []

    def pass_check(self, name: str) -> None:
        self.passed.append(name)
        print(f"[PASS] {name}")

    def fail_check(self, name: str, detail: str = "") -> None:
        message = f"{name}{' - ' + detail if detail else ''}"
        self.failed.append(message)
        print(f"[FAIL] {message}")

    def warn(self, name: str, detail: str = "") -> None:
        message = f"{name}{' - ' + detail if detail else ''}"
        self.warnings.append(message)
        print(f"[WARN] {message}")


def walk(payload: Any, path: str = ""):
    if isinstance(payload, dict):
        for key, value in payload.items():
            current = f"{path}.{key}" if path else str(key)
            yield current, key, value
            yield from walk(value, current)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            yield from walk(item, f"{path}[{index}]")


def assert_backend_healthy(result: ValidationResult, client: TestClient, check_name: str) -> None:
    response = client.get("/health")
    if response.status_code == 200 and response.json().get("status") == "healthy":
        result.pass_check(check_name)
    else:
        result.fail_check(check_name, f"status_code={response.status_code}, body={response.text[:200]}")


def assert_no_unsafe_flags(result: ValidationResult, endpoint: str, payload: Any) -> None:
    for value_path, key, value in walk(payload):
        if key in SAFETY_FALSE_KEYS and value is not False:
            result.fail_check("Unsafe execution flag", f"{endpoint}:{value_path}={value!r}")
        if key == "simulation_only" and value is not True:
            result.fail_check("Simulation-only flag drift", f"{endpoint}:{value_path}={value!r}")


def verify_invalid_requests(result: ValidationResult, client: TestClient) -> None:
    base = {
        "symbol": "NIFTY50",
        "timeframe": "M15",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "open": 22000.0,
        "high": 22010.0,
        "low": 21990.0,
        "close": 22005.0,
        "volume": 10,
    }
    cases = [
        ("missing symbol", {key: value for key, value in base.items() if key != "symbol"}, {422}),
        ("missing timeframe", {key: value for key, value in base.items() if key != "timeframe"}, {422}),
        ("invalid timeframe", {**base, "timeframe": "M99"}, {200}),
        ("negative prices", {**base, "open": -10.0, "high": -5.0, "low": -20.0, "close": -8.0}, {200}),
        ("malformed timestamp", {**base, "timestamp": "not-a-date"}, {422}),
    ]
    for label, payload, expected_statuses in cases:
        response = client.post("/nifty50/market-data/ingest-candle", json=payload)
        if response.status_code not in expected_statuses:
            result.fail_check(f"Invalid candle rejected safely: {label}", f"status_code={response.status_code}, body={response.text[:200]}")
        elif response.status_code == 200 and response.json().get("accepted") is not False:
            result.fail_check(f"Invalid candle rejected safely: {label}", f"body={response.json()}")
        else:
            result.pass_check(f"Invalid candle rejected safely: {label}")
        assert_backend_healthy(result, client, f"Backend healthy after invalid candle: {label}")


def verify_empty_states(result: ValidationResult, client: TestClient) -> None:
    endpoints = [
        "/client-analytics/overview",
        "/client-analytics/symbols",
        "/client-analytics/accounts",
        "/client-analytics/reports/daily",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        if response.status_code != 200:
            result.fail_check(f"Empty-state endpoint {endpoint}", f"status_code={response.status_code}")
            continue
        payload = response.json()
        assert_no_unsafe_flags(result, endpoint, payload)
        if payload in ({}, [], None):
            result.fail_check(f"Empty-state endpoint {endpoint}", "returned an unusable empty payload")
        else:
            result.pass_check(f"Empty-state endpoint {endpoint}")

    overview = client.get("/client-analytics/overview").json()
    numeric_keys = ["total_signals", "total_demo_executions", "net_pnl", "win_rate"]
    if all(isinstance(overview.get(key), (int, float)) and not isinstance(overview.get(key), bool) for key in numeric_keys):
        result.pass_check("Analytics overview safe numeric defaults")
    else:
        result.fail_check("Analytics overview safe numeric defaults", str({key: overview.get(key) for key in numeric_keys}))


def verify_duplicate_requests(result: ValidationResult, client: TestClient) -> None:
    timestamp = "2026-06-05T09:15:00+00:00"
    candle = {
        "symbol": "NIFTY50",
        "timeframe": "M15",
        "timestamp": timestamp,
        "open": 22000.0,
        "high": 22020.0,
        "low": 21990.0,
        "close": 22010.0,
        "volume": 100,
    }
    before_health = client.get("/nifty50/market-data/health").json()
    first = client.post("/nifty50/market-data/ingest-candle", json=candle)
    second = client.post("/nifty50/market-data/ingest-candle", json=candle)
    after_health = client.get("/nifty50/market-data/health").json()
    before_count = int(before_health.get("candles_available", 0))
    after_count = int(after_health.get("candles_available", 0))
    if first.status_code == second.status_code == 200 and first.json().get("accepted") is True and second.json().get("accepted") is True and after_count <= before_count + 1:
        result.pass_check("Duplicate candle ingestion is idempotent")
    else:
        result.fail_check(
            "Duplicate candle ingestion is idempotent",
            f"before={before_count}, after={after_count}, first={first.status_code}, second={second.status_code}",
        )

    before_intents = client.get("/nifty50/execution/intents").json()
    first_intent = client.post("/nifty50/execution/create-intent")
    second_intent = client.post("/nifty50/execution/create-intent")
    after_intents = client.get("/nifty50/execution/intents").json()
    if (
        first_intent.status_code == second_intent.status_code == 200
        and len(after_intents) <= len(before_intents) + 1
        and all(item.get("execution_allowed") is False for item in after_intents)
    ):
        result.pass_check("Duplicate execution intent requests do not corrupt state")
    else:
        result.fail_check(
            "Duplicate execution intent requests do not corrupt state",
            f"before={len(before_intents)}, after={len(after_intents)}",
        )


def verify_execution_safety(result: ValidationResult, client: TestClient) -> None:
    blocked_signal = {
        "symbol": "XAUUSD",
        "action": "BUY",
        "confidence": 99,
        "trade_quality": "A_PLUS",
        "execution_allowed": False,
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
    bridge_response = client.post("/strategy-execution-bridge/evaluate-and-preview", json=blocked_signal)
    if bridge_response.status_code != 200:
        result.fail_check("Blocked strategy bridge request remains stable", f"status_code={bridge_response.status_code}")
    else:
        payload = bridge_response.json()
        assert_no_unsafe_flags(result, "/strategy-execution-bridge/evaluate-and-preview", payload)
        if (
            payload.get("eligible") is False
            and payload.get("bridge_status") == "REJECTED_EXECUTION_NOT_ALLOWED"
            and payload.get("live_execution_enabled") is False
            and payload.get("broker_execution_enabled") is False
        ):
            result.pass_check("Blocked strategy bridge request remains blocked")
        else:
            result.fail_check("Blocked strategy bridge request remains blocked", str(payload))

    preview_response = client.post("/nifty50/execution/preview-order")
    if preview_response.status_code != 200:
        result.fail_check("NIFTY50 preview-order request remains stable", f"status_code={preview_response.status_code}")
    else:
        payload = preview_response.json()
        assert_no_unsafe_flags(result, "/nifty50/execution/preview-order", payload)
        if payload.get("preview_status") in {"BLOCKED_EXECUTION_DISABLED", "BROKER_NOT_SELECTED", "REJECTED"}:
            result.pass_check("NIFTY50 execution preview refuses live order placement")
        else:
            result.fail_check("NIFTY50 execution preview refuses live order placement", str(payload))


def verify_nifty_safety(result: ValidationResult, client: TestClient) -> None:
    payload = client.get("/nifty50/execution/status").json()
    checks = {
        "preview_only": True,
        "execution_allowed": False,
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
    failures = {key: payload.get(key) for key, expected in checks.items() if payload.get(key) is not expected}
    if failures:
        result.fail_check("NIFTY50 safety flags", str(failures))
    else:
        result.pass_check("NIFTY50 safety flags")


def verify_status_endpoints_after_reimport(result: ValidationResult) -> None:
    from backend.main import app

    client = TestClient(app)
    for endpoint in STATUS_ENDPOINTS:
        response = client.get(endpoint)
        if response.status_code == 200:
            payload = response.json()
            assert_no_unsafe_flags(result, endpoint, payload)
            result.pass_check(f"Restart-recovery endpoint {endpoint}")
        else:
            result.fail_check(f"Restart-recovery endpoint {endpoint}", f"status_code={response.status_code}")


def scan_for_order_send(result: ValidationResult) -> None:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    if matches == ["backend/demo_execution/mt5_demo_executor.py"]:
        result.pass_check("No new mt5.order_send path added")
    else:
        result.fail_check("No new mt5.order_send path added", ", ".join(matches))


def print_summary(result: ValidationResult) -> int:
    print("=" * 76)
    print(f"Passed checks: {len(result.passed)}")
    print(f"Failed checks: {len(result.failed)}")
    print(f"Warnings: {len(result.warnings)}")
    print("=" * 76)
    if result.failed:
        print("VALIDATION DAY 4 RESULT: FAIL")
        return 1
    print("VALIDATION DAY 4 RESULT: PASS")
    return 0


def main() -> int:
    print("Validation Day 4 - Stability & Failure Recovery")
    print("=" * 76)
    result = ValidationResult()
    try:
        from backend.main import app
    except Exception as exc:
        result.fail_check("Import backend.main app", str(exc))
        return print_summary(result)

    with TestClient(app) as client:
        verify_invalid_requests(result, client)
        verify_empty_states(result, client)
        verify_duplicate_requests(result, client)
        verify_execution_safety(result, client)
        verify_nifty_safety(result, client)
        verify_status_endpoints_after_reimport(result)
        scan_for_order_send(result)
        assert_backend_healthy(result, client, "Backend healthy after all failure scenarios")
    return print_summary(result)


if __name__ == "__main__":
    raise SystemExit(main())
