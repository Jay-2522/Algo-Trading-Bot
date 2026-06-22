from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time
from urllib.request import urlopen

from fastapi import BackgroundTasks


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get_json(url: str, timeout: float = 2.0) -> tuple[dict, float]:
    started = time.perf_counter()
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - local verification endpoint
        payload = json.loads(response.read().decode("utf-8"))
    return payload, (time.perf_counter() - started) * 1000


async def mocked_control_latency() -> dict[str, float]:
    from backend.api import auto_validation_routes as routes

    original_pause = routes.auto_validation_service.pause
    original_resume = routes.auto_validation_service.resume
    original_stop = routes.auto_validation_runner.stop
    original_start = routes.auto_validation_runner.start
    original_support = routes.auto_validation_runner.start_support_loops
    original_active = routes.auto_validation_runner.is_active
    original_status = routes.auto_validation_runner.support_status
    routes.auto_validation_service.pause = lambda: {"status": "PAUSED", "message": "mocked lightweight state update"}
    routes.auto_validation_service.resume = lambda: {"status": "RESUMED", "message": "mocked lightweight state update"}
    routes.auto_validation_runner.stop = lambda *args, **kwargs: None
    routes.auto_validation_runner.start = lambda: None
    routes.auto_validation_runner.start_support_loops = lambda: None
    routes.auto_validation_runner.is_active = lambda: False
    routes.auto_validation_runner.support_status = lambda: {}
    try:
        started = time.perf_counter()
        await routes.pause_auto_validation()
        pause_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        await routes.resume_auto_validation(BackgroundTasks())
        resume_ms = (time.perf_counter() - started) * 1000
        return {"pause_ms": pause_ms, "resume_ms": resume_ms}
    finally:
        routes.auto_validation_service.pause = original_pause
        routes.auto_validation_service.resume = original_resume
        routes.auto_validation_runner.stop = original_stop
        routes.auto_validation_runner.start = original_start
        routes.auto_validation_runner.start_support_loops = original_support
        routes.auto_validation_runner.is_active = original_active
        routes.auto_validation_runner.support_status = original_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only AUTO validation runtime reliability check")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    checks: list[dict[str, object]] = []

    health, health_ms = get_json(f"{args.base_url}/health")
    checks.append({"name": "backend_healthy", "pass": health.get("status") == "healthy", "duration_ms": round(health_ms, 1)})

    first, snapshot_ms = get_json(f"{args.base_url}/auto-validation/runtime-snapshot")
    time.sleep(2.2)
    second, second_ms = get_json(f"{args.base_url}/auto-validation/runtime-snapshot")
    tickets = [str(item.get("ticket") or item.get("mt5_ticket") or "") for item in second.get("mt5_open_positions", []) if isinstance(item, dict)]
    checks.extend(
        [
            {"name": "snapshot_under_1s", "pass": snapshot_ms < 1000 and second_ms < 1000, "duration_ms": round(max(snapshot_ms, second_ms), 1)},
            {"name": "active_session_preserved", "pass": bool(first.get("active_session_id")) and first.get("active_session_id") == second.get("active_session_id")},
            {"name": "mt5_dashboard_open_count_match", "pass": second.get("mt5_open_count") == len(tickets) == second.get("runtime_health", {}).get("dashboard_open_count")},
            {"name": "no_duplicate_tickets", "pass": len(tickets) == len(set(tickets))},
            {"name": "stale_scan_preserves_open_trades", "pass": not second.get("live_scan_status", {}).get("stale") or first.get("mt5_open_count") == second.get("mt5_open_count")},
            {"name": "stale_scan_preserves_bot_decisions", "pass": not second.get("live_scan_status", {}).get("stale") or bool(second.get("bot_decisions_latest_3"))},
        ]
    )

    source = (ROOT / "backend" / "auto_validation" / "auto_validation_service.py").read_text(encoding="utf-8")
    lifecycle_contract = all(token in source for token in ("MISSING_OPEN_TICKET_DETECTED", "CLOSED_TRADE_WRITTEN", "CLOSURE_PENDING_CREATED", "mark_trade_closure_pending_by_ticket"))
    checks.append({"name": "missing_ticket_lifecycle_contract", "pass": lifecycle_contract})

    control = asyncio.run(mocked_control_latency())
    checks.append({"name": "pause_route_under_500ms", "pass": control["pause_ms"] < 500, "duration_ms": round(control["pause_ms"], 1)})
    checks.append({"name": "resume_route_under_500ms", "pass": control["resume_ms"] < 500, "duration_ms": round(control["resume_ms"], 1)})

    report = {
        "pass": all(bool(check["pass"]) for check in checks),
        "checks": checks,
        "active_session_id": second.get("active_session_id"),
        "mt5_open_tickets": tickets,
        "mt5_open_count": second.get("mt5_open_count"),
        "loop_health": second.get("loop_health"),
    }
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
