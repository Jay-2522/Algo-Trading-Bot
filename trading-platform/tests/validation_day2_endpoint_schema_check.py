import csv
import io
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


JSON_ENDPOINTS = [
    "/health",
    "/status",
    "/deployment/status",
    "/deployment/readiness",
    "/production-readiness/status",
    "/monitoring/status",
    "/monitoring/health",
    "/security/status",
    "/security/secrets-audit",
    "/strategy/status",
    "/strategy-execution-bridge/status",
    "/strategy-execution-bridge/operations/status",
    "/nifty50/status",
    "/nifty50/readiness",
    "/nifty50/strategy/status",
    "/nifty50/risk/status",
    "/nifty50/execution/status",
    "/client-analytics/overview",
    "/client-analytics/symbols",
    "/client-analytics/sessions",
    "/client-analytics/risk",
    "/client-analytics/accounts",
    "/client-analytics/strategy/status",
    "/client-analytics/executive/summary",
    "/client-analytics/executive/completion",
    "/client-analytics/reports/status",
    "/client-analytics/reports/daily",
    "/client-analytics/reports/weekly",
    "/client-analytics/reports/export/json",
]

CSV_ENDPOINT = "/client-analytics/reports/export/csv"
EXECUTION_ENDPOINTS = {
    "/strategy-execution-bridge/status",
    "/strategy-execution-bridge/operations/status",
    "/nifty50/execution/status",
}
NIFTY_EXECUTION_ENDPOINT = "/nifty50/execution/status"
SAFETY_FALSE_KEYS = {"live_execution_enabled", "broker_execution_enabled", "execution_allowed"}
BOOLEAN_SUFFIXES = ("_ready", "_enabled", "_allowed", "_only", "_active", "_available", "_detected", "_approved")
NUMERIC_EXACT_KEYS = {
    "confidence",
    "deployment_score",
    "health_score",
    "overall_completion_percentage",
    "net_pnl",
    "win_rate",
    "profit_factor",
    "max_drawdown",
    "wins",
    "losses",
    "demo_executions",
    "strategy_score",
}
NUMERIC_PREFIXES = ("total_", "avg_", "max_", "min_", "best_", "worst_")
NUMERIC_SUFFIXES = ("_score", "_percentage", "_rate", "_count", "_pnl", "_drawdown", "_factor", "_confidence")
TEMPORAL_KEYS = {"timestamp", "created_at", "updated_at", "generated_at", "scheduled_time", "last_sync_time"}


class ValidationResult:
    def __init__(self) -> None:
        self.endpoints_checked = 0
        self.schema_failures: list[str] = []
        self.safety_failures: list[str] = []
        self.warnings: list[str] = []
        self.passed: list[str] = []

    def pass_check(self, name: str) -> None:
        self.passed.append(name)
        print(f"[PASS] {name}")

    def schema_fail(self, name: str, detail: str) -> None:
        message = f"{name} - {detail}"
        self.schema_failures.append(message)
        print(f"[SCHEMA FAIL] {message}")

    def safety_fail(self, name: str, detail: str) -> None:
        message = f"{name} - {detail}"
        self.safety_failures.append(message)
        print(f"[SAFETY FAIL] {message}")

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


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_boolean_key(key: str) -> bool:
    return key in {"simulation_only", "demo_execution"} or key.endswith(BOOLEAN_SUFFIXES)


def is_numeric_metric_key(key: str) -> bool:
    lowered = key.lower()
    if is_boolean_key(lowered):
        return False
    if lowered.endswith(("_id", "_name", "_type", "_status", "_summary")):
        return False
    if lowered in {"version", "port", "volume"}:
        return False
    return lowered in NUMERIC_EXACT_KEYS or lowered.startswith(NUMERIC_PREFIXES) or lowered.endswith(NUMERIC_SUFFIXES)


def is_temporal_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in TEMPORAL_KEYS or lowered.endswith("_timestamp")


def validate_json_schema(endpoint: str, payload: Any, result: ValidationResult) -> None:
    if payload is None:
        result.schema_fail(endpoint, "response is null")
        return
    if not isinstance(payload, (dict, list)):
        result.schema_fail(endpoint, f"response must be dict or list, got {type(payload).__name__}")
        return

    for value_path, key, value in walk(payload):
        if is_temporal_key(key) and value is not None and not isinstance(value, str):
            result.schema_fail(endpoint, f"{value_path} should be string when present")
        if key == "status" and value is not None and not isinstance(value, str):
            result.schema_fail(endpoint, f"{value_path} should be string")
        if is_boolean_key(key) and value is not None and not isinstance(value, bool):
            result.schema_fail(endpoint, f"{value_path} should be boolean")
        if is_numeric_metric_key(key) and value is not None and not is_number(value):
            result.schema_fail(endpoint, f"{value_path} should be numeric")


def validate_safety(endpoint: str, payload: Any, result: ValidationResult) -> None:
    for value_path, key, value in walk(payload):
        if key in SAFETY_FALSE_KEYS and value is True:
            result.safety_fail(endpoint, f"{value_path}=true")

    if endpoint in EXECUTION_ENDPOINTS:
        if not isinstance(payload, dict) or payload.get("execution_allowed") is not False:
            result.safety_fail(endpoint, "execution_allowed must be false")

    if endpoint == NIFTY_EXECUTION_ENDPOINT:
        if payload.get("preview_only") is not True:
            result.safety_fail(endpoint, "preview_only must be true")
        if payload.get("execution_ready") is not False:
            result.safety_fail(endpoint, "execution_ready must be false")


def validate_analytics(payloads: dict[str, Any], result: ValidationResult) -> None:
    overview = payloads.get("/client-analytics/overview")
    if not isinstance(overview, dict):
        result.schema_fail("analytics overview", "payload missing")
        return
    for key in ["net_pnl", "win_rate", "total_signals", "total_demo_executions"]:
        if not is_number(overview.get(key)):
            result.schema_fail("analytics overview", f"{key} must be numeric")
    if is_number(overview.get("net_pnl")) and overview["net_pnl"] >= 0:
        result.pass_check("Analytics overview metrics are numeric and non-negative")
    elif is_number(overview.get("net_pnl")):
        result.warn("Analytics overview net_pnl is numeric but negative", str(overview["net_pnl"]))

    symbols_payload = payloads.get("/client-analytics/symbols")
    symbols = {item.get("symbol") for item in symbols_payload if isinstance(item, dict)} if isinstance(symbols_payload, list) else set()
    if {"XAUUSD", "EURUSD", "NIFTY50"} <= symbols:
        result.pass_check("Analytics symbols include XAUUSD, EURUSD, and NIFTY50")
    else:
        result.schema_fail("analytics symbols", f"found={sorted(symbols)}")

    executive = payloads.get("/client-analytics/executive/summary") or {}
    if executive.get("nifty50_ready") is False:
        result.pass_check("NIFTY50 is not marked fully production ready")
    else:
        result.safety_fail("NIFTY50 readiness", "nifty50_ready must remain false")


def validate_reports(payloads: dict[str, Any], csv_response, result: ValidationResult) -> None:
    for endpoint in ["/client-analytics/reports/daily", "/client-analytics/reports/weekly"]:
        report = payloads.get(endpoint)
        if not isinstance(report, dict):
            result.schema_fail(endpoint, "report payload missing")
            continue
        required = ["report_id", "report_type", "period", "summary", "simulation_only"]
        missing = [field for field in required if field not in report]
        if missing:
            result.schema_fail(endpoint, f"missing fields: {', '.join(missing)}")
        if report.get("live_execution_enabled") is not False:
            result.safety_fail(endpoint, "live_execution_enabled must be false")
        if report.get("broker_execution_enabled") is not False:
            result.safety_fail(endpoint, "broker_execution_enabled must be false")
        if not missing:
            result.pass_check(f"{endpoint} report required fields exist")

    if csv_response.status_code != 200:
        result.schema_fail(CSV_ENDPOINT, f"status_code={csv_response.status_code}")
        return
    content_type = csv_response.headers.get("content-type", "")
    if "text" not in content_type and "csv" not in content_type:
        result.schema_fail(CSV_ENDPOINT, f"unexpected content-type={content_type}")
    text = csv_response.text
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    headers = rows[0] if rows else []
    required_headers = {"report_id", "report_type", "period", "symbol", "total_signals"}
    if required_headers <= set(headers):
        result.pass_check("CSV export returns text with required headers")
    else:
        result.schema_fail(CSV_ENDPOINT, f"missing headers from {headers}")


def validate_executive_completion(payloads: dict[str, Any], result: ValidationResult) -> None:
    completion = payloads.get("/client-analytics/executive/completion")
    if not isinstance(completion, dict):
        result.schema_fail("executive completion", "payload missing")
        return
    completion_pct = completion.get("overall_completion_percentage")
    pending = completion.get("pending", [])
    required_pending = {"Demo Broker Validation", "VPS Deployment", "Extended Stability Testing"}
    if is_number(completion_pct) and completion_pct <= 99:
        result.pass_check("Executive completion is <= 99 and not 100")
    else:
        result.safety_fail("executive completion", f"overall_completion_percentage={completion_pct}")
    if isinstance(pending, list) and required_pending <= set(pending):
        result.pass_check("Executive completion includes required pending items")
    else:
        result.schema_fail("executive completion", f"pending missing required items; found={pending}")


def print_summary(result: ValidationResult) -> int:
    print("=" * 76)
    print(f"Endpoints checked: {result.endpoints_checked}")
    print(f"Schema failures: {len(result.schema_failures)}")
    print(f"Safety failures: {len(result.safety_failures)}")
    print(f"Warnings: {len(result.warnings)}")
    print("Recommendations:")
    print("- Continue with Validation Day 3 frontend smoke and dashboard data rendering checks.")
    print("- Keep broker execution and live trading disabled until explicit approval.")
    print("- Keep NIFTY50 marked not production-ready until broker demo validation and VPS validation pass.")
    print("=" * 76)
    if result.schema_failures or result.safety_failures:
        print("VALIDATION DAY 2 RESULT: FAIL")
        return 1
    print("VALIDATION DAY 2 RESULT: PASS")
    return 0


def main() -> int:
    print("Validation Day 2 - Deep Endpoint Schema & Data Consistency Check")
    print("=" * 76)
    result = ValidationResult()
    try:
        from backend.main import app
    except Exception as exc:
        result.schema_fail("backend.main import", str(exc))
        return print_summary(result)

    client = TestClient(app)
    payloads: dict[str, Any] = {}
    for endpoint in JSON_ENDPOINTS:
        response = client.get(endpoint)
        result.endpoints_checked += 1
        if response.status_code != 200:
            result.schema_fail(endpoint, f"status_code={response.status_code}")
            continue
        try:
            payload = response.json()
        except Exception as exc:
            result.schema_fail(endpoint, f"invalid JSON: {exc}")
            continue
        payloads[endpoint] = payload
        validate_json_schema(endpoint, payload, result)
        validate_safety(endpoint, payload, result)
        result.pass_check(f"Checked {endpoint}")

    csv_response = client.get(CSV_ENDPOINT)
    result.endpoints_checked += 1
    validate_analytics(payloads, result)
    validate_reports(payloads, csv_response, result)
    validate_executive_completion(payloads, result)
    return print_summary(result)


if __name__ == "__main__":
    raise SystemExit(main())
