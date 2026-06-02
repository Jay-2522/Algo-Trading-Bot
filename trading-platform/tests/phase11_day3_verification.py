import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "frontend/components/trade-journal/TradeJournalSection.tsx",
        "frontend/components/trade-journal/TradeHistoryTable.tsx",
        "frontend/components/trade-journal/ExecutionTimeline.tsx",
        "frontend/components/trade-journal/TradeDetailDrawer.tsx",
        "frontend/components/trade-journal/ExecutionStatusBadge.tsx",
        "frontend/components/trade-journal/TradeJournalEmptyState.tsx",
        "frontend/lib/tradeJournalApi.ts",
        "docs/phase-11-day-3-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Trade journal UI files and API client exist", not missing, ", ".join(missing))


def verify_dashboard_integration_and_labels() -> bool:
    try:
        page = (PROJECT_ROOT / "frontend" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        section = (PROJECT_ROOT / "frontend" / "components" / "trade-journal" / "TradeJournalSection.tsx").read_text(encoding="utf-8")
        passed = (
            "TradeJournalSection" in page
            and "Trade Journal & Execution History" in section
            and "DEMO ONLY" in section
            and "LIVE DISABLED" in section
            and "AUDIT READY" in section
        )
        return show("Dashboard imports trade journal section and safety labels exist", passed)
    except Exception as exc:
        return show("Dashboard imports trade journal section and safety labels exist", False, str(exc))


def verify_lifecycle_and_empty_state() -> bool:
    try:
        api = (PROJECT_ROOT / "frontend" / "lib" / "tradeJournalApi.ts").read_text(encoding="utf-8")
        empty = (PROJECT_ROOT / "frontend" / "components" / "trade-journal" / "TradeJournalEmptyState.tsx").read_text(encoding="utf-8")
        steps = [
            "Strategy Signal",
            "Bridge Validation",
            "Risk Check",
            "Queue Preview",
            "Approval",
            "Demo Candidate",
            "Final Demo Execution",
            "Trade Copier",
            "Confirmation",
        ]
        passed = all(step in api for step in steps) and "No demo execution history yet" in empty
        return show("Lifecycle steps and empty state are present", passed)
    except Exception as exc:
        return show("Lifecycle steps and empty state are present", False, str(exc))


def verify_no_fake_profit_strings() -> bool:
    try:
        paths = [
            *list((PROJECT_ROOT / "frontend" / "components" / "trade-journal").glob("*.tsx")),
            PROJECT_ROOT / "frontend" / "lib" / "tradeJournalApi.ts",
        ]
        suspicious: list[str] = []
        fake_profit_pattern = re.compile(r"[\+\$]\s?(?:[1-9]\d{2,}|900|1000|5000)")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for match in fake_profit_pattern.finditer(text):
                snippet = text[max(0, match.start() - 30) : match.end() + 30]
                if "Number(value" in snippet or "toFixed" in snippet:
                    continue
                suspicious.append(f"{path.name}: {match.group(0)}")
        return show("No hardcoded fake trade/PnL strings are present", not suspicious, ", ".join(suspicious))
    except Exception as exc:
        return show("No hardcoded fake trade/PnL strings are present", False, str(exc))


def verify_phase11_preserved_and_order_send() -> bool:
    try:
        from backend.main import app

        required = {
            "/client-analytics/status",
            "/client-analytics/overview",
            "/client-analytics/symbols",
            "/client-analytics/sessions",
            "/client-analytics/risk",
            "/client-analytics/snapshots/latest",
        }
        registered = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = required <= registered and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("Phase 11 Day 1-2 routes are preserved and no new order_send exists", passed, ", ".join(matches))
    except Exception as exc:
        return show("Phase 11 Day 1-2 routes are preserved and no new order_send exists", False, str(exc))


def verify_frontend_build() -> bool:
    try:
        result = subprocess.run(
            ["npm.cmd", "run", "build"],
            cwd=PROJECT_ROOT / "frontend",
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        detail = (result.stderr or result.stdout).splitlines()[-1] if result.returncode else ""
        return show("Frontend build expected to pass", result.returncode == 0, detail)
    except Exception as exc:
        return show("Frontend build expected to pass", False, str(exc))


def main() -> int:
    print("Phase 11 Day 3 Trade Journal & Execution History UI Verification")
    print("=" * 68)
    checks = [
        verify_files(),
        verify_dashboard_integration_and_labels(),
        verify_lifecycle_and_empty_state(),
        verify_no_fake_profit_strings(),
        verify_phase11_preserved_and_order_send(),
        verify_frontend_build(),
    ]
    print("=" * 68)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
