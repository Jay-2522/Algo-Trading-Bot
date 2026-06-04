import re
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


CORE_STATUS_ENDPOINTS = [
    "/health",
    "/status",
    "/deployment/status",
    "/monitoring/status",
    "/security/status",
    "/production-readiness/status",
]

API_CONSISTENCY_ENDPOINTS = [
    "/client-analytics/status",
    "/client-analytics/overview",
    "/client-analytics/symbols",
    "/client-analytics/risk",
    "/client-analytics/accounts",
    "/client-analytics/reports/status",
    "/client-analytics/reports/daily",
    "/client-analytics/executive/status",
    "/client-analytics/executive/summary",
    "/client-analytics/executive/readiness",
    "/client-analytics/executive/completion",
    "/client-analytics/strategy/status",
    "/client-analytics/strategy/overview",
    "/client-analytics/strategy/performance",
    "/client-analytics/strategy/rankings",
    "/strategy/status",
    "/strategy/signals",
    "/strategy/confluence/xauusd",
    "/strategy/eurusd/confluence",
    "/nifty50/status",
    "/nifty50/readiness",
    "/nifty50/market-data/status",
    "/nifty50/strategy/status",
    "/nifty50/strategy/snapshot",
    "/nifty50/risk/status",
    "/nifty50/execution/status",
    "/nifty50/execution/intents",
    "/strategy-execution-bridge/status",
    "/strategy-execution-bridge/demo-approval/status",
    "/strategy-execution-bridge/final-demo-execution/status",
]

API_CONSISTENCY_POST_ENDPOINTS: list[str] = []

SAFETY_ENDPOINTS = [
    "/deployment/status",
    "/monitoring/status",
    "/security/status",
    "/production-readiness/status",
    "/strategy-execution-bridge/status",
    "/nifty50/execution/status",
    "/client-analytics/executive/summary",
]

REQUIRED_DOCS = {
    "architecture": [
        "README.md",
        "docs/nifty50-broker-architecture.md",
        "docs/nifty50-strategy-foundation.md",
    ],
    "validation": [
        "docs/validation-day-1-baseline-report.md",
        "docs/validation-day-2-schema-report.md",
        "docs/validation-day-3-dashboard-audit.md",
        "docs/validation-day-4-failure-handling.md",
        "docs/validation-day-4-restart-recovery.md",
    ],
    "deployment": [
        "docs/deployment-readiness-checklist.md",
        "docs/docker-deployment-guide.md",
        "docs/vps-deployment-checklist-final.md",
        "docs/vps-runtime-guide.md",
        "docs/deployment-rollback-guide.md",
        "docs/recovery-runbook.md",
        "docs/incident-response-guide.md",
        "docs/backup-strategy.md",
    ],
    "risk": [
        "docs/nifty50-risk-engine.md",
        "docs/security-hardening-guide.md",
        "docs/secrets-management-guide.md",
    ],
    "client": [
        "docs/client-mvp-readiness-summary.md",
        "docs/dashboard-visible-number-audit.md",
    ],
    "handover": [
        "docs/go-live-assessment.md",
        "docs/production-readiness-report.md",
    ],
}

DEPLOYMENT_FILES = [
    "Dockerfile.backend",
    "Dockerfile.frontend",
    "docker-compose.yml",
    "docker-compose.override.yml",
    "scripts/start_backend.ps1",
    "scripts/start_frontend.ps1",
    "scripts/restart_backend.ps1",
    "scripts/restart_frontend.ps1",
    "scripts/docker_up.ps1",
    "scripts/docker_down.ps1",
    "scripts/docker_healthcheck.ps1",
    "scripts/security_check.ps1",
    "scripts/recovery_check.ps1",
    "scripts/backup_status.ps1",
]

FAKE_CLIENT_PATTERNS = [
    "+$900",
    "+$100",
    "100% win rate",
    "fake profit",
    "fake win",
    "fake trade",
    "XAUUSD BUY history",
]

PLACEHOLDER_VALUES = {
    "",
    "changeme",
    "change_me",
    "placeholder",
    "example",
    "demo",
    "dummy",
    "your_key_here",
    "your-secret-here",
    "replace_me",
    "not-set",
    "none",
    "null",
}


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


def get_json(result: ValidationResult, client: TestClient, endpoint: str) -> Any | None:
    response = client.get(endpoint)
    if response.status_code != 200:
        result.fail_check(f"GET {endpoint}", f"status_code={response.status_code}")
        return None
    try:
        payload = response.json()
    except Exception as exc:
        result.fail_check(f"GET {endpoint}", f"malformed JSON: {exc}")
        return None
    if payload in ({}, None):
        result.fail_check(f"GET {endpoint}", "empty or malformed payload")
        return None
    result.pass_check(f"GET {endpoint}")
    return payload


def assert_no_unsafe_flags(result: ValidationResult, endpoint: str, payload: Any) -> None:
    for value_path, key, value in walk(payload):
        if key == "simulation_only" and value is not True:
            result.fail_check("simulation_only safety failure", f"{endpoint}:{value_path}={value!r}")
        if key == "live_execution_enabled" and value is not False:
            result.fail_check("live_execution_enabled safety failure", f"{endpoint}:{value_path}={value!r}")
        if key == "broker_execution_enabled" and value is not False:
            result.fail_check("broker_execution_enabled safety failure", f"{endpoint}:{value_path}={value!r}")
        if key == "execution_allowed" and value is not False:
            result.fail_check("execution_allowed safety failure", f"{endpoint}:{value_path}={value!r}")


def verify_core_status(result: ValidationResult, client: TestClient) -> dict[str, Any]:
    payloads = {}
    for endpoint in CORE_STATUS_ENDPOINTS:
        payload = get_json(result, client, endpoint)
        if payload is not None:
            payloads[endpoint] = payload
            assert_no_unsafe_flags(result, endpoint, payload)
    return payloads


def verify_execution_safety(result: ValidationResult, client: TestClient) -> None:
    for endpoint in SAFETY_ENDPOINTS:
        payload = get_json(result, client, endpoint)
        if payload is not None:
            assert_no_unsafe_flags(result, endpoint, payload)

    nifty_status = client.get("/nifty50/execution/status").json()
    expected = {
        "simulation_only": True,
        "preview_only": True,
        "execution_allowed": False,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
    failures = {key: nifty_status.get(key) for key, value in expected.items() if nifty_status.get(key) is not value}
    if failures:
        result.fail_check("NIFTY50 final execution lock", str(failures))
    else:
        result.pass_check("NIFTY50 final execution lock")

    bridge_status = client.get("/strategy-execution-bridge/status").json()
    if bridge_status.get("preview_only") is True and bridge_status.get("simulation_only") is True and bridge_status.get("broker_execution_enabled") is False:
        result.pass_check("Strategy execution bridge remains preview-only")
    else:
        result.fail_check("Strategy execution bridge remains preview-only", str(bridge_status))


def verify_api_consistency(result: ValidationResult, client: TestClient) -> None:
    for endpoint in API_CONSISTENCY_ENDPOINTS:
        payload = get_json(result, client, endpoint)
        if payload is not None:
            assert_no_unsafe_flags(result, endpoint, payload)
    for endpoint in API_CONSISTENCY_POST_ENDPOINTS:
        response = client.post(endpoint, json={})
        if response.status_code != 200:
            result.fail_check(f"POST {endpoint}", f"status_code={response.status_code}")
            continue
        try:
            payload = response.json()
        except Exception as exc:
            result.fail_check(f"POST {endpoint}", f"malformed JSON: {exc}")
            continue
        assert_no_unsafe_flags(result, endpoint, payload)
        result.pass_check(f"POST {endpoint}")

    symbols = client.get("/client-analytics/symbols").json()
    symbol_names = {item.get("symbol") for item in symbols if isinstance(item, dict)}
    if {"XAUUSD", "EURUSD", "NIFTY50"} <= symbol_names:
        result.pass_check("Client analytics exposes all three instruments")
    else:
        result.fail_check("Client analytics exposes all three instruments", str(symbol_names))

    executive = client.get("/client-analytics/executive/summary").json()
    if executive.get("nifty50_ready") is False and executive.get("overall_completion_percentage", 100) < 100:
        result.pass_check("Executive dashboard remains honest below 100 percent")
    else:
        result.fail_check("Executive dashboard remains honest below 100 percent", str(executive))


def iter_audit_files():
    suffixes = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yml", ".yaml", ".env", ".example", ".md"}
    skip_parts = {".git", "node_modules", ".next", "__pycache__", "logs", "frontend_old"}
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name in {"package-lock.json", "trading_platform.db"}:
            continue
        if any(part in skip_parts for part in path.parts):
            continue
        if path.suffix.lower() not in suffixes and not path.name.startswith(".env"):
            continue
        yield path


def verify_configuration_audit(result: ValidationResult) -> None:
    secret_findings: list[str] = []
    private_key_findings: list[str] = []
    assignment_pattern = re.compile(r"(?i)\\b(password|api[_-]?key|secret|token|private[_-]?key)\\b\\s*[:=]\\s*[\"']?([^\"'\\s,#}]+)")
    for path in iter_audit_files():
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if rel == "tests/validation_day5_final_audit.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "-----BEGIN PRIVATE KEY-----" in text or "-----BEGIN RSA PRIVATE KEY-----" in text or "-----BEGIN OPENSSH PRIVATE KEY-----" in text:
            private_key_findings.append(rel)
        if rel.startswith("docs/") or rel.startswith("tests/"):
            continue
        for match in assignment_pattern.finditer(text):
            key, value = match.group(1), match.group(2).strip().strip('"').strip("'")
            normalized = value.lower()
            if normalized in PLACEHOLDER_VALUES or normalized.startswith("your_") or normalized.startswith("${") or normalized.startswith("os.getenv"):
                continue
            if len(value) >= 12 and not value.startswith("settings."):
                secret_findings.append(f"{rel}:{key}")

    if private_key_findings:
        result.fail_check("No hardcoded private keys", ", ".join(private_key_findings))
    else:
        result.pass_check("No hardcoded private keys")

    if secret_findings:
        result.fail_check("No committed production credentials or API secrets", ", ".join(secret_findings[:10]))
    else:
        result.pass_check("No committed production credentials or API secrets")


def verify_hidden_execution_paths(result: ValidationResult) -> None:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    if matches == ["backend/demo_execution/mt5_demo_executor.py"]:
        result.pass_check("No hidden mt5.order_send path")
    else:
        result.fail_check("No hidden mt5.order_send path", ", ".join(matches))

    unsafe_assignment = re.compile(r"\\b(live_execution_enabled|broker_execution_enabled|execution_allowed)\\s*[:=]\\s*True\\b|\\bpreview_only\\s*[:=]\\s*False\\b")
    offenders = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        if unsafe_assignment.search(text):
            offenders.append(rel)
    if offenders:
        result.fail_check("No hardcoded unsafe execution flag assignments", ", ".join(offenders))
    else:
        result.pass_check("No hardcoded unsafe execution flag assignments")


def verify_deployment_artifacts(result: ValidationResult) -> None:
    missing = [path for path in DEPLOYMENT_FILES if not (PROJECT_ROOT / path).is_file()]
    if missing:
        result.fail_check("Deployment files and startup scripts exist", ", ".join(missing))
    else:
        result.pass_check("Deployment files and startup scripts exist")


def verify_documentation(result: ValidationResult) -> None:
    missing: list[str] = []
    low_quality: list[str] = []
    for group, paths in REQUIRED_DOCS.items():
        for path in paths:
            full_path = PROJECT_ROOT / path
            if not full_path.is_file():
                missing.append(f"{group}:{path}")
                continue
            text = full_path.read_text(encoding="utf-8", errors="ignore").strip()
            if len(text) < 80:
                low_quality.append(f"{group}:{path}")
    if missing:
        result.fail_check("Required documentation exists", ", ".join(missing))
    else:
        result.pass_check("Required documentation exists")
    if low_quality:
        result.fail_check("Required documentation has substantive content", ", ".join(low_quality))
    else:
        result.pass_check("Required documentation has substantive content")


def verify_client_honesty(result: ValidationResult) -> None:
    offenders: list[str] = []
    for root_name in ["frontend", "backend"]:
        root = PROJECT_ROOT / root_name
        for path in root.rglob("*"):
            if not path.is_file() or any(part in {"node_modules", ".next"} for part in path.parts):
                continue
            if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".json"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            text_for_scan = text.replace("no fake trade", "").replace("no fake trades", "")
            for pattern in FAKE_CLIENT_PATTERNS:
                if pattern.lower() in text_for_scan:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{pattern}")
    if offenders:
        result.fail_check("No fake client-facing metrics or trade history", ", ".join(offenders))
    else:
        result.pass_check("No fake client-facing metrics or trade history")

    dashboard_audit = (PROJECT_ROOT / "docs" / "dashboard-visible-number-audit.md").read_text(encoding="utf-8", errors="ignore")
    if "NIFTY50" in dashboard_audit and "placeholder" in dashboard_audit.lower():
        result.pass_check("Client-facing data source audit labels placeholders")
    else:
        result.fail_check("Client-facing data source audit labels placeholders")


def print_summary(result: ValidationResult) -> int:
    print("=" * 78)
    print(f"Passed checks: {len(result.passed)}")
    print(f"Failed checks: {len(result.failed)}")
    print(f"Warnings: {len(result.warnings)}")
    print("=" * 78)
    if result.failed:
        print("VALIDATION DAY 5 RESULT: FAIL")
        return 1
    print("VALIDATION DAY 5 RESULT: PASS")
    return 0


def main() -> int:
    print("Validation Day 5 - Final Pre-Production Audit")
    print("=" * 78)
    result = ValidationResult()
    try:
        from backend.main import app
    except Exception as exc:
        result.fail_check("Import backend.main app", str(exc))
        return print_summary(result)

    with TestClient(app) as client:
        verify_core_status(result, client)
        verify_execution_safety(result, client)
        verify_api_consistency(result, client)
    verify_configuration_audit(result)
    verify_hidden_execution_paths(result)
    verify_deployment_artifacts(result)
    verify_documentation(result)
    verify_client_honesty(result)
    return print_summary(result)


if __name__ == "__main__":
    raise SystemExit(main())
