from datetime import datetime, timezone


class NewsReadinessService:
    """Report pending macro-data integrations without enabling live feeds."""

    def status(self) -> dict:
        return {
            "status": "PENDING_EXTERNAL_INTEGRATIONS",
            "architecture_ready": True,
            "integrations": {
                "forex_factory": "MANUAL_INGESTION_READY",
                "financial_juice": "PENDING",
                "dxy": "PENDING",
                "us10y": "PENDING",
            },
            "pending_items": [
                "Forex Factory live integration pending; manual adapter ready",
                "Financial Juice integration pending",
                "DXY integration pending",
                "US10Y integration pending",
            ],
            "external_api_calls_enabled": False,
            "scraping_enabled": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
