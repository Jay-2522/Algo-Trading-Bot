from typing import Any

from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
from backend.demo_execution.demo_execution_models import MT5DemoAccountStatus


class MT5DemoAccountVerifier:
    """Verify that an MT5 terminal is connected to a demo account before any demo execution."""

    def __init__(self, connection_manager: MT5ConnectionManager | None = None) -> None:
        self.connection_manager = connection_manager or MT5ConnectionManager()

    def verify_demo_account(self) -> MT5DemoAccountStatus:
        reasons: list[str] = []
        if self.connection_manager.mt5 is None:
            return MT5DemoAccountStatus(
                rejection_reasons=["MetaTrader5 package or terminal is unavailable."],
                simulation_only=True,
                live_execution_enabled=False,
            )

        if not self.connection_manager.is_initialized():
            status = self.connection_manager.initialize()
            if not status.initialized:
                return MT5DemoAccountStatus(
                    terminal_available=status.terminal_available,
                    rejection_reasons=[status.message or "MT5 terminal is unavailable."],
                    simulation_only=True,
                    live_execution_enabled=False,
                )

        try:
            account = self.connection_manager.mt5.account_info()
        except Exception as exc:
            account = None
            reasons.append(f"MT5 account info unavailable: {exc}")

        if account is None:
            reasons.append("MT5 account is not connected.")
            return MT5DemoAccountStatus(
                terminal_available=True,
                account_connected=False,
                rejection_reasons=reasons,
                simulation_only=True,
                live_execution_enabled=False,
            )

        trade_mode = getattr(account, "trade_mode", None)
        is_demo = self._is_demo_trade_mode(trade_mode)
        if not is_demo:
            reasons.append("Connected MT5 account is not verified as DEMO.")

        return MT5DemoAccountStatus(
            terminal_available=True,
            account_connected=True,
            account_login=getattr(account, "login", None),
            broker_server=getattr(account, "server", None),
            account_trade_mode=trade_mode,
            is_demo_account=is_demo,
            demo_execution_allowed=is_demo,
            rejection_reasons=reasons,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _is_demo_trade_mode(self, trade_mode: Any) -> bool:
        mt5 = self.connection_manager.mt5
        demo_constant = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None) if mt5 is not None else None
        if demo_constant is not None and trade_mode == demo_constant:
            return True
        if isinstance(trade_mode, str) and "DEMO" in trade_mode.upper():
            return True
        return False
