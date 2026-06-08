from typing import Any

from backend.mt5_demo.mt5_position_monitoring_service import MT5PositionMonitoringService
from backend.mt5_demo.mt5_trade_lifecycle_service import MT5TradeLifecycleService


class DemoPositionAnalyticsService:
    """Client-facing demo position analytics from real MT5/journal monitoring data."""

    def __init__(
        self,
        position_monitoring_service: MT5PositionMonitoringService | None = None,
        lifecycle_service: MT5TradeLifecycleService | None = None,
    ) -> None:
        self.position_monitoring_service = position_monitoring_service or MT5PositionMonitoringService()
        self.lifecycle_service = lifecycle_service or MT5TradeLifecycleService()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "READY",
            "environment": "DEMO",
            "data_source": "MT5_DEMO_POSITION_MONITOR",
            **self._safety_flags(),
        }

    def get_open_positions(self) -> dict[str, Any]:
        return self.position_monitoring_service.get_open_positions()

    def get_summary(self) -> dict[str, Any]:
        monitor = self.position_monitoring_service.get_open_positions()
        positions = monitor.get("positions", [])
        floating_values = [float(position.get("floating_pnl") or 0.0) for position in positions]
        symbols = sorted({str(position.get("symbol") or "") for position in positions if position.get("symbol")})
        lifecycle = self.lifecycle_service.get_analytics()
        return {
            "status": "READY",
            "environment": "DEMO",
            "open_positions": len(positions),
            "total_floating_pnl": round(sum(floating_values), 2) if floating_values else 0.0,
            "symbols": symbols,
            "largest_floating_profit": round(max(floating_values), 2) if floating_values else 0.0,
            "largest_floating_loss": round(min(floating_values), 2) if floating_values else 0.0,
            "lifecycle_open_count": lifecycle.get("open_trades", 0),
            "lifecycle_closed_count": lifecycle.get("closed_trades", 0),
            "empty_state": len(positions) == 0,
            "message": "No open MT5 demo positions." if not positions else "Demo position summary from MT5 and journal data.",
            **self._safety_flags(),
        }

    def _safety_flags(self) -> dict[str, bool]:
        return {
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "mt5_order_send_used": False,
        }
