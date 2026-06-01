import importlib.util
from pathlib import Path


class MT5Monitor:
    """Read-only MT5 environment monitor for demo deployment."""

    COMMON_TERMINAL_PATHS = [
        Path("C:/Program Files/MetaTrader 5/terminal64.exe"),
        Path("C:/Program Files/MetaTrader 5/terminal.exe"),
        Path("C:/Program Files (x86)/MetaTrader 5/terminal64.exe"),
        Path("C:/Program Files (x86)/MetaTrader 5/terminal.exe"),
    ]

    def get_mt5_status(self) -> dict:
        package_available = importlib.util.find_spec("MetaTrader5") is not None
        terminal_detected = any(path.exists() for path in self.COMMON_TERMINAL_PATHS)
        warnings = []
        if not package_available:
            warnings.append("MetaTrader5 Python package is unavailable.")
        if not terminal_detected:
            warnings.append("MT5 terminal was not detected in common install paths.")
        return {
            "package_available": package_available,
            "terminal_detected": terminal_detected,
            "demo_mode": True,
            "autotrading_state_unknown_allowed": True,
            "live_account_support": False,
            "warnings": warnings,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }
