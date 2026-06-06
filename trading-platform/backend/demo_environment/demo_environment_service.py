from datetime import datetime, timezone


class DemoEnvironmentService:
    """Single source of truth for Phase 14 demo-environment readiness."""

    def get_status(self) -> dict:
        return {
            "phase": "PHASE_14",
            "environment": "DEMO",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "mt5_demo_configured": False,
            "mt5_demo_connected": False,
            "vps_ready": False,
            "monitoring_ready": False,
            "telegram_ready": False,
            "demo_execution_authorized": False,
            "status": "NOT_READY",
            "timestamp": self._timestamp(),
        }

    def get_readiness(self) -> dict:
        status = self.get_status()
        blockers = [
            "MT5 demo account is not configured.",
            "MT5 demo connection is not verified.",
            "Windows VPS is not marked ready.",
            "Monitoring and alerting are not fully validated.",
            "Demo execution authorization is not granted.",
        ]
        return {
            **status,
            "readiness_score": 0,
            "ready_for_demo_execution": False,
            "blockers": blockers,
            "warnings": [
                "Phase 14 Day 1 is planning and readiness only.",
                "Do not connect production broker credentials.",
                "Do not enable live execution or broker execution.",
            ],
        }

    def get_checklist(self) -> dict:
        return {
            "phase": "PHASE_14",
            "environment": "DEMO",
            "status": "NOT_READY",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "sections": [
                {
                    "name": "MT5",
                    "items": [
                        self._item("MT5 installed"),
                        self._item("MT5 demo account created"),
                        self._item("MT5 login verified"),
                        self._item("Market data available"),
                    ],
                },
                {
                    "name": "VPS",
                    "items": [
                        self._item("Windows VPS selected"),
                        self._item("Server reachable"),
                        self._item("Timezone configured"),
                        self._item("Auto restart configured"),
                    ],
                },
                {
                    "name": "MONITORING",
                    "items": [
                        self._item("Health endpoint active", completed=True),
                        self._item("Monitoring active"),
                        self._item("Logs active"),
                        self._item("Alerting active"),
                    ],
                },
                {
                    "name": "SAFETY",
                    "items": [
                        self._item("Simulation only", completed=True),
                        self._item("Live execution disabled", completed=True),
                        self._item("Broker execution disabled", completed=True),
                        self._item("Risk engine enabled", completed=True),
                        self._item("News engine enabled", completed=True),
                    ],
                },
            ],
            "timestamp": self._timestamp(),
        }

    def _item(self, label: str, completed: bool = False) -> dict:
        return {"label": label, "completed": completed}

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
