import importlib.util
from pathlib import Path

from backend.deployment.deployment_models import MT5EnvironmentCheck


class MT5EnvironmentChecker:
    """Check MT5 demo-readiness without opening any execution path."""

    COMMON_TERMINAL_PATHS = [
        Path("C:/Program Files/MetaTrader 5/terminal64.exe"),
        Path("C:/Program Files/MetaTrader 5/terminal.exe"),
        Path("C:/Program Files (x86)/MetaTrader 5/terminal64.exe"),
        Path("C:/Program Files (x86)/MetaTrader 5/terminal.exe"),
    ]

    def check(self) -> MT5EnvironmentCheck:
        warnings: list[str] = []
        blockers: list[str] = []
        package_available = importlib.util.find_spec("MetaTrader5") is not None
        terminal_detected = any(path.exists() for path in self.COMMON_TERMINAL_PATHS)

        if not package_available:
            warnings.append("MetaTrader5 Python package is not available in the current interpreter.")
        if not terminal_detected:
            warnings.append("MT5 terminal was not detected in common install paths; configure it on the VPS before demo execution.")

        return MT5EnvironmentCheck(
            mt5_python_package_available=package_available,
            mt5_terminal_detected=terminal_detected,
            demo_account_required=True,
            live_account_blocked=True,
            autotrading_required_for_demo=True,
            mt5_ready_for_demo=package_available and terminal_detected,
            warnings=[
                *warnings,
                "AutoTrading must be enabled only for guarded demo execution tests.",
                "Live accounts remain blocked by platform policy.",
            ],
            blockers=blockers,
        )
