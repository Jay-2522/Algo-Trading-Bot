from typing import Any


class NewsCommandCenter:
    """Consolidated read-only command center for Phase 7 news intelligence."""

    def __init__(self, news_service: Any | None = None) -> None:
        self.news_service = news_service

    def get_overview(self) -> dict:
        return {
            "status": "OPERATIONAL",
            "calendar_status": self.get_calendar_status(),
            "headline_status": self.get_headline_status(),
            "macro_status": self.get_macro_status(),
            "unified_risk_status": self.get_unified_risk_status(),
            "strategy_news_status": self.get_strategy_news_status(),
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def get_calendar_status(self) -> dict:
        events = self.news_service.list_calendar_events() if self.news_service else []
        context = self.news_service.get_news_risk_context() if self.news_service else None
        return {
            "engine_ready": True,
            "events_loaded": len(events),
            "risk_level": self._get(context, "risk_level", "LOW"),
            "trade_action": self._get(context, "trade_action", "ALLOW"),
            "active_events": len(self._get(context, "active_events", [])),
        }

    def get_headline_status(self) -> dict:
        headlines = self.news_service.list_headlines() if self.news_service else []
        context = self.news_service.get_headline_risk_context() if self.news_service else None
        return {
            "engine_ready": True,
            "headlines_loaded": len(headlines),
            "highest_risk_level": self._get(context, "highest_risk_level", "LOW"),
            "headline_trade_action": self._get(context, "headline_trade_action", "ALLOW"),
            "active_headlines": len(self._get(context, "active_headlines", [])),
        }

    def get_macro_status(self) -> dict:
        contexts = self.news_service.list_macro_contexts() if self.news_service else []
        bias = self.news_service.get_xauusd_macro_bias() if self.news_service else None
        return {
            "engine_ready": True,
            "contexts_loaded": len(contexts),
            "gold_bias": self._get(bias, "gold_bias", "UNKNOWN"),
            "macro_alignment": self._get(bias, "macro_alignment", "UNKNOWN"),
            "macro_risk_level": self._get(bias, "macro_risk_level", "MEDIUM"),
        }

    def get_unified_risk_status(self) -> dict:
        decision = self.news_service.evaluate_unified_xauusd_risk(action="WAIT") if self.news_service else None
        return {
            "engine_ready": True,
            "final_risk_level": self._get(decision, "final_risk_level", "LOW"),
            "final_trade_action": self._get(decision, "final_trade_action", "ALLOW"),
            "confidence_cap": self._get(decision, "confidence_cap", None),
            "confidence_adjustment": self._get(decision, "confidence_adjustment", 0.0),
        }

    def get_strategy_news_status(self) -> dict:
        return {
            "strategy_integration_ready": True,
            "xauusd_metadata_enabled": True,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
