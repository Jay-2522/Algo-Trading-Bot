from backend.broker_compatibility.mt5_demo_models import MT5TerminalReadiness


class MT5DemoReadinessChecker:
    """Read-only MT5 terminal readiness probe with safe unavailable fallback."""

    def __init__(self, mt5_client=None) -> None:
        self.mt5_client = mt5_client

    def check_terminal_readiness(self) -> MT5TerminalReadiness:
        client = self.mt5_client or self._default_client()
        if client is None:
            return MT5TerminalReadiness(
                terminal_available=False,
                initialized=False,
                account_available=False,
                broker_server=None,
                message="MT5 client package or terminal is unavailable; read-only demo verification skipped safely.",
            )
        try:
            initialized = bool(client.connect())
            account = None
            broker_server = None
            if initialized:
                try:
                    account = client.get_account_info()
                    broker_server = getattr(account, "server", None)
                except Exception:
                    account = None
            return MT5TerminalReadiness(
                terminal_available=initialized,
                initialized=initialized,
                account_available=account is not None,
                broker_server=broker_server,
                message="MT5 terminal is available for read-only demo observation." if initialized else "MT5 terminal is not initialized.",
            )
        except Exception as exc:
            return MT5TerminalReadiness(
                terminal_available=False,
                initialized=False,
                account_available=False,
                broker_server=None,
                message=f"MT5 unavailable for read-only demo verification: {exc}",
            )
        finally:
            try:
                if client is not None:
                    client.disconnect()
            except Exception:
                pass

    def _default_client(self):
        try:
            from backend.broker_integrations.mt5.mt5_client import MT5Client

            return MT5Client()
        except Exception:
            return None
