import sys
from pathlib import Path


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


def verify_routes() -> bool:
    try:
        from backend.main import app

        routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        required = {
            "/health",
            "/status",
            "/market-data/timeframes",
            "/strategy/session",
            "/risk/status",
            "/execution/status",
            "/mt5/status",
            "/database/status",
            "/ai/status",
            "/news/status",
            "/news/upcoming",
            "/news/high-impact",
            "/news/risk-status/{symbol}",
            "/news/allow-trading/{symbol}",
            "/news/blackout-windows",
            "/news/macro-score/{symbol}",
        }
        missing = sorted(required - routes)
        print_result("FastAPI app imports and news/old routes registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("FastAPI app imports and news/old routes registered", False, str(exc))
        return False


def verify_calendar() -> bool:
    try:
        from backend.news_engine.economic_calendar import EconomicCalendarService

        events = EconomicCalendarService().get_upcoming_events()
        categories = {event.category for event in events}
        passed = len(events) >= 4 and {"CPI", "NFP", "FOMC", "FED_SPEECH"}.issubset(categories)
        print_result("EconomicCalendarService returns events", passed)
        return passed
    except Exception as exc:
        print_result("EconomicCalendarService returns events", False, str(exc))
        return False


def verify_impact_classifier() -> bool:
    try:
        from backend.news_engine.economic_calendar import EconomicCalendarService
        from backend.news_engine.impact_classifier import ImpactClassifier

        event = EconomicCalendarService().get_high_impact_events()[0]
        classifier = ImpactClassifier()
        passed = classifier.is_high_impact(event) and classifier.is_gold_sensitive(event)
        print_result("ImpactClassifier detects high impact", passed)
        return passed
    except Exception as exc:
        print_result("ImpactClassifier detects high impact", False, str(exc))
        return False


def verify_blackout_window() -> bool:
    try:
        from backend.news_engine.blackout_window import BlackoutWindowService
        from backend.news_engine.economic_calendar import EconomicCalendarService

        events = EconomicCalendarService().get_high_impact_events()
        service = BlackoutWindowService()
        window = service.create_blackout_window(events[0])
        passed = window is not None and service.is_in_blackout_window(events)
        print_result("BlackoutWindowService creates windows", passed)
        return passed
    except Exception as exc:
        print_result("BlackoutWindowService creates windows", False, str(exc))
        return False


def verify_macro_scorer() -> bool:
    try:
        from backend.news_engine.economic_calendar import EconomicCalendarService
        from backend.news_engine.macro_risk_scorer import MacroRiskScorer

        score = MacroRiskScorer().calculate_macro_risk(EconomicCalendarService().get_upcoming_events())
        passed = score.risk_level == "BLOCKED" and score.event_risk_score == 100
        print_result("MacroRiskScorer returns score", passed, str(score) if not passed else "")
        return passed
    except Exception as exc:
        print_result("MacroRiskScorer returns score", False, str(exc))
        return False


def verify_filter_service() -> bool:
    try:
        from backend.news_engine.news_filter_service import NewsFilterService

        status = NewsFilterService().get_news_risk_status("XAUUSD", persist=False)
        passed = not status.trading_allowed and status.active_blackout and status.risk_level == "BLOCKED"
        print_result("NewsFilterService returns NewsRiskStatus", passed, str(status) if not passed else "")
        return passed
    except Exception as exc:
        print_result("NewsFilterService returns NewsRiskStatus", False, str(exc))
        return False


def main() -> int:
    print("Day 9 News Intelligence Verification")
    print("=" * 38)

    checks = [
        verify_path("backend/news_engine", "news_engine folder exists", is_dir=True),
        verify_path("backend/news_engine/news_models.py", "news_models.py exists"),
        verify_path("backend/news_engine/economic_calendar.py", "economic_calendar.py exists"),
        verify_path("backend/news_engine/impact_classifier.py", "impact_classifier.py exists"),
        verify_path("backend/news_engine/blackout_window.py", "blackout_window.py exists"),
        verify_path("backend/news_engine/macro_risk_scorer.py", "macro_risk_scorer.py exists"),
        verify_path("backend/news_engine/news_filter_service.py", "news_filter_service.py exists"),
        verify_path("backend/news_engine/news_logger.py", "news_logger.py exists"),
        verify_path("backend/news_engine/validators.py", "validators.py exists"),
        verify_path("backend/api/news_routes.py", "news_routes.py exists"),
        verify_routes(),
        verify_calendar(),
        verify_impact_classifier(),
        verify_blackout_window(),
        verify_macro_scorer(),
        verify_filter_service(),
    ]

    print("=" * 38)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

