import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


GET_ENDPOINTS = [
    "/health",
    "/status",
    "/deployment/status",
    "/production-readiness/status",
    "/monitoring/status",
    "/monitoring/health",
    "/security/status",
    "/strategy/status",
    "/strategy/analyze/eurusd",
    "/strategy-execution-bridge/status",
    "/nifty50/status",
    "/nifty50/readiness",
    "/nifty50/strategy/status",
    "/nifty50/risk/status",
    "/nifty50/execution/status",
    "/client-analytics/overview",
    "/client-analytics/symbols",
    "/client-analytics/risk",
    "/client-analytics/accounts",
    "/client-analytics/strategy/status",
    "/client-analytics/executive/status",
    "/client-analytics/executive/completion",
    "/client-analytics/reports/status",
    "/client-analytics/reports/daily",
    "/client-analytics/reports/export/json",
    "/client-analytics/reports/export/csv",
]

POST_ENDPOINTS = [
    ("/strategy/analyze/xauusd", {}),
]

REQUIRED_ROUTE_GROUPS = [
    "/deployment",
    "/monitoring",
    "/security",
    "/production-readiness",
    "/client-analytics",
    "/nifty50",
    "/strategy-execution-bridge",
]

SAFETY_FALSE_KEYS = {"live_execution_enabled", "broker_execution_enabled", "execution_allowed"}
SAFETY_TRUE_KEYS = {"simulation_only"}
EXECUTION_ROUTES = {"/strategy-execution-bridge/status", "/nifty50/execution/status"}
FAKE_DATA_PATTERNS = ["+900", "+100", "100% win rate", "fake win", "fake profit"]


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


def registered_route_paths(app) -> set[str]:
    return {route.path for route in app.routes if hasattr(route, "methods")}


def route_group_exists(route_paths: set[str], prefix: str) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for path in route_paths)


def walk_values(payload: Any, path: str = ""):
    if isinstance(payload, dict):
        for key, value in payload.items():
            current = f"{path}.{key}" if path else str(key)
            yield current, key, value
            yield from walk_values(value, current)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            yield from walk_values(item, f"{path}[{index}]")


def response_json(response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    return {"plain_text_response": response.text}


def verify_endpoint(client: TestClient, result: ValidationResult, method: str, path: str, payload: dict | None = None) -> Any | None:
    response = client.get(path) if method == "GET" else client.post(path, json=payload or {})
    if response.status_code != 200:
        result.fail_check(f"{method} {path}", f"status_code={response.status_code}")
        return None
    result.pass_check(f"{method} {path}")
    body = response_json(response)
    verify_safety_flags(result, path, body)
    return body


def verify_safety_flags(result: ValidationResult, route: str, payload: Any) -> None:
    for value_path, key, value in walk_values(payload):
        if key in SAFETY_FALSE_KEYS and value is True:
            result.fail_check("Safety flag violation", f"{route}:{value_path}=true")
        if key in SAFETY_TRUE_KEYS and value is False:
            result.fail_check("Safety flag violation", f"{route}:{value_path}=false")

    if route in EXECUTION_ROUTES:
        if isinstance(payload, dict):
            if payload.get("execution_allowed") is not False:
                result.fail_check("Execution route safety", f"{route} execution_allowed is not false")
            if "preview_only" in payload and payload.get("preview_only") is not True:
                result.fail_check("Execution route safety", f"{route} preview_only is not true")


def verify_route_groups(app, result: ValidationResult) -> None:
    route_paths = registered_route_paths(app)
    for prefix in REQUIRED_ROUTE_GROUPS:
        if route_group_exists(route_paths, prefix):
            result.pass_check(f"Registered route group {prefix}")
        else:
            result.fail_check(f"Registered route group {prefix}", "missing")


def verify_instrument_presence(result: ValidationResult, analytics_payloads: dict[str, Any]) -> None:
    symbols_payload = analytics_payloads.get("/client-analytics/symbols") or []
    symbols = {item.get("symbol") for item in symbols_payload if isinstance(item, dict)}
    required = {"XAUUSD", "EURUSD", "NIFTY50"}
    if required <= symbols:
        result.pass_check("Client analytics includes XAUUSD, EURUSD, and NIFTY50")
    else:
        result.fail_check("Client analytics includes XAUUSD, EURUSD, and NIFTY50", f"found={sorted(symbols)}")

    completion = analytics_payloads.get("/client-analytics/executive/completion") or {}
    completion_pct = completion.get("overall_completion_percentage")
    if completion_pct is not None and completion_pct < 100:
        result.pass_check("Executive completion remains below 100 percent")
    else:
        result.fail_check("Executive completion remains below 100 percent", f"value={completion_pct}")


def fake_data_scan(result: ValidationResult) -> None:
    production_roots = [PROJECT_ROOT / "backend", PROJECT_ROOT / "frontend"]
    fail_matches: list[str] = []
    warning_matches: list[str] = []
    for root in production_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md"}:
                continue
            if any(part in {"node_modules", ".next"} for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            lowered = text.lower()
            for pattern in FAKE_DATA_PATTERNS:
                if pattern.lower() not in lowered:
                    continue
                relative = path.relative_to(PROJECT_ROOT).as_posix()
                if pattern.lower() in {"fake win", "fake profit"} and f"no {pattern.lower()}" in lowered:
                    warning_matches.append(f"{relative}:{pattern}")
                else:
                    fail_matches.append(f"{relative}:{pattern}")

    if fail_matches:
        result.fail_check("Fake profit string scan", ", ".join(fail_matches))
    else:
        result.pass_check("Fake profit string scan found no production fake data")
    for match in warning_matches:
        result.warn("Safety wording contains fake-data phrase", match)


def print_summary(result: ValidationResult) -> int:
    print("=" * 72)
    print(f"Passed checks: {len(result.passed)}")
    print(f"Failed checks: {len(result.failed)}")
    print(f"Warnings: {len(result.warnings)}")
    print("Safety status:", "PASS" if not result.failed else "FAIL")
    print("Next recommendations:")
    recommendations = [
        "Run Validation Day 2 focused endpoint payload and schema checks.",
        "Run a longer frontend smoke test against the production dashboard.",
        "Continue to keep live execution, broker execution, and credentials disabled.",
    ]
    for recommendation in recommendations:
        print(f"- {recommendation}")
    print("=" * 72)
    if result.failed:
        print("VALIDATION DAY 1 RESULT: FAIL")
        return 1
    print("VALIDATION DAY 1 RESULT: PASS")
    return 0


def main() -> int:
    print("Validation Day 1 - Full System Safety & Baseline Check")
    print("=" * 72)
    result = ValidationResult()

    try:
        from backend.main import app
    except Exception as exc:
        result.fail_check("Import backend.main app", str(exc))
        return print_summary(result)

    client = TestClient(app)
    verify_route_groups(app, result)
    payloads: dict[str, Any] = {}

    for endpoint in GET_ENDPOINTS:
        payloads[endpoint] = verify_endpoint(client, result, "GET", endpoint)
    for endpoint, payload in POST_ENDPOINTS:
        payloads[endpoint] = verify_endpoint(client, result, "POST", endpoint, payload)

    verify_instrument_presence(result, payloads)
    fake_data_scan(result)
    return print_summary(result)


if __name__ == "__main__":
    raise SystemExit(main())
