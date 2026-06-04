import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


ENDPOINTS = [
    "/health",
    "/status",
    "/client-analytics/overview",
    "/client-analytics/symbols",
    "/client-analytics/risk",
    "/client-analytics/accounts",
    "/client-analytics/strategy/overview",
    "/client-analytics/strategy/performance",
    "/client-analytics/strategy/rankings",
    "/client-analytics/reports/status",
    "/client-analytics/reports/daily",
    "/client-analytics/executive/summary",
    "/client-analytics/executive/readiness",
    "/nifty50/execution/status",
]

FAKE_METRIC_PATTERNS = [
    "+$900",
    "+$100",
    "100% win rate",
    "fake win",
    "fake profit",
    "Recent Trades",
    "Trading Results",
    "No fake profit display",
]


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


def verify_safety(result: ValidationResult, endpoint: str, payload: Any) -> None:
    for value_path, key, value in walk(payload):
        if key == "live_execution_enabled" and value is True:
            result.fail_check("Live execution enabled", f"{endpoint}:{value_path}=true")
        if key == "broker_execution_enabled" and value is True:
            result.fail_check("Broker execution enabled", f"{endpoint}:{value_path}=true")
        if key == "simulation_only" and value is False:
            result.fail_check("Simulation-only flag false", f"{endpoint}:{value_path}=false")


def verify_endpoint_group(result: ValidationResult, client: TestClient) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    for endpoint in ENDPOINTS:
        response = client.get(endpoint)
        if response.status_code != 200:
            result.fail_check(f"GET {endpoint}", f"status_code={response.status_code}")
            continue
        try:
            payload = response.json()
        except Exception as exc:
            result.fail_check(f"GET {endpoint}", f"invalid JSON: {exc}")
            continue
        payloads[endpoint] = payload
        verify_safety(result, endpoint, payload)
        result.pass_check(f"GET {endpoint}")
    return payloads


def verify_nifty50(result: ValidationResult, payloads: dict[str, Any]) -> None:
    payload = payloads.get("/nifty50/execution/status")
    if not isinstance(payload, dict):
        result.fail_check("NIFTY50 execution payload", "missing")
        return
    if payload.get("execution_allowed") is False:
        result.pass_check("NIFTY50 execution_allowed=false")
    else:
        result.fail_check("NIFTY50 execution_allowed=false", f"value={payload.get('execution_allowed')}")
    if payload.get("preview_only") is True:
        result.pass_check("NIFTY50 preview_only=true")
    else:
        result.fail_check("NIFTY50 preview_only=true", f"value={payload.get('preview_only')}")


def verify_executive(result: ValidationResult, payloads: dict[str, Any]) -> None:
    summary = payloads.get("/client-analytics/executive/summary")
    if not isinstance(summary, dict):
        result.fail_check("Executive summary payload", "missing")
        return
    completion = summary.get("overall_completion_percentage")
    if isinstance(completion, (int, float)) and completion < 100:
        result.pass_check("Executive completion is below 100 percent")
    else:
        result.fail_check("Executive completion is below 100 percent", f"value={completion}")


def verify_analytics_sources(result: ValidationResult, payloads: dict[str, Any]) -> None:
    symbols = payloads.get("/client-analytics/symbols")
    if isinstance(symbols, list) and {"XAUUSD", "EURUSD", "NIFTY50"} <= {item.get("symbol") for item in symbols if isinstance(item, dict)}:
        result.pass_check("Client analytics symbols come from backend and include all instruments")
    else:
        result.fail_check("Client analytics symbols include all instruments")

    overview = payloads.get("/client-analytics/overview")
    if isinstance(overview, dict) and all(isinstance(overview.get(key), (int, float)) and not isinstance(overview.get(key), bool) for key in ["total_signals", "total_demo_executions", "net_pnl", "win_rate"]):
        result.pass_check("Client analytics overview numeric metrics are backend-provided")
    else:
        result.fail_check("Client analytics overview numeric metrics are backend-provided")


def scan_fake_metrics(result: ValidationResult) -> None:
    offenders: list[str] = []
    for root_name in ["frontend", "backend"]:
        root = PROJECT_ROOT / root_name
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".json"}:
                continue
            if any(part in {"node_modules", ".next"} for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            lowered = text.lower()
            for pattern in FAKE_METRIC_PATTERNS:
                if pattern.lower() in lowered:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{pattern}")
    if offenders:
        result.fail_check("Hardcoded fake metric scan", ", ".join(offenders))
    else:
        result.pass_check("No hardcoded fake dashboard metrics in frontend/backend")


def print_summary(result: ValidationResult) -> int:
    print("=" * 72)
    print(f"Passed checks: {len(result.passed)}")
    print(f"Failed checks: {len(result.failed)}")
    print(f"Warnings: {len(result.warnings)}")
    print("=" * 72)
    if result.failed:
        print("VALIDATION DAY 3 RESULT: FAIL")
        return 1
    print("VALIDATION DAY 3 RESULT: PASS")
    return 0


def main() -> int:
    print("Validation Day 3 - Frontend & Dashboard Integrity")
    print("=" * 72)
    result = ValidationResult()
    try:
        from backend.main import app
    except Exception as exc:
        result.fail_check("Import backend.main app", str(exc))
        return print_summary(result)

    client = TestClient(app)
    payloads = verify_endpoint_group(result, client)
    verify_nifty50(result, payloads)
    verify_executive(result, payloads)
    verify_analytics_sources(result, payloads)
    scan_fake_metrics(result)
    return print_summary(result)


if __name__ == "__main__":
    raise SystemExit(main())
