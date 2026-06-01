import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8", errors="ignore")


def verify_files() -> bool:
    files = [
        "Dockerfile.backend",
        "Dockerfile.frontend",
        "docker-compose.yml",
        "docker-compose.override.yml",
        ".dockerignore",
        ".env.example",
        ".env.production.example",
        "scripts/docker_build.ps1",
        "scripts/docker_up.ps1",
        "scripts/docker_down.ps1",
        "scripts/docker_logs.ps1",
        "scripts/docker_healthcheck.ps1",
        "docs/docker-deployment-guide.md",
        "docs/phase-10-day-2-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Dockerfiles, compose files, env templates, scripts, and docs exist", not missing, ", ".join(missing))


def verify_file_contents() -> bool:
    try:
        backend = read("Dockerfile.backend")
        frontend = read("Dockerfile.frontend")
        compose = read("docker-compose.yml")
        override = read("docker-compose.override.yml")
        env_example = read(".env.example")
        env_prod = read(".env.production.example")
        passed = (
            "python:3.11-slim" in backend
            and "uvicorn" in backend
            and "backend.main:app" in backend
            and "LIVE_EXECUTION_ENABLED=false" in backend
            and "BROKER_EXECUTION_ENABLED=false" in backend
            and "node:lts" in frontend
            and "npm run build" in frontend
            and "npm\", \"run\", \"start" in frontend
            and "8000:8000" in compose
            and "3000:3000" in compose
            and "./logs:/app/logs" in compose
            and "/health" in compose
            and "--reload" in override
            and "SIMULATION_ONLY=true" in env_example
            and "DEMO_EXECUTION=true" in env_example
            and "LIVE_EXECUTION_ENABLED=false" in env_example
            and "BROKER_EXECUTION_ENABLED=false" in env_example
            and "LIVE_EXECUTION_ENABLED=false" in env_prod
            and "BROKER_EXECUTION_ENABLED=false" in env_prod
            and "must remain false" in env_prod
        )
        return show("Docker and env files contain safe expected commands and defaults", passed)
    except Exception as exc:
        return show("Docker and env files contain safe expected commands and defaults", False, str(exc))


def verify_deployment_readiness_detects_docker() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        readiness = client.get("/deployment/readiness")
        payload = readiness.json()
        passed = (
            readiness.status_code == 200
            and payload["docker_ready"] is True
            and payload["compose_ready"] is True
            and payload["env_templates_ready"] is True
            and payload["simulation_only"] is True
            and payload["demo_execution"] is True
            and payload["live_execution_enabled"] is False
            and payload["broker_execution_enabled"] is False
        )
        return show("Deployment readiness detects Docker assets and preserves safety flags", passed)
    except Exception as exc:
        return show("Deployment readiness detects Docker assets and preserves safety flags", False, str(exc))


def verify_preserved_routes_and_safety() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registered_get_routes = {
            route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path for route in app.routes if route.__class__.__name__ == "APIWebSocketRoute"
        }
        required = {
            "/deployment/status",
            "/deployment/readiness",
            "/strategy-execution-bridge/status",
            "/strategy-execution-bridge/operations/status",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not missing and not missing_ws and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("Phase 10 Day 1 and Phase 9 routes plus order_send isolation are preserved", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Phase 10 Day 1 and Phase 9 routes plus order_send isolation are preserved", False, str(exc))


def main() -> int:
    print("Phase 10 Day 2 Docker Deployment Verification")
    print("=" * 55)
    checks = [
        verify_files(),
        verify_file_contents(),
        verify_deployment_readiness_detects_docker(),
        verify_preserved_routes_and_safety(),
    ]
    print("=" * 55)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
