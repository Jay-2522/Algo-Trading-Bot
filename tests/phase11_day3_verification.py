import runpy
from pathlib import Path


TRADING_PLATFORM = Path(__file__).resolve().parents[1] / "trading-platform"
SCRIPT = TRADING_PLATFORM / "tests" / "phase11_day3_verification.py"


if __name__ == "__main__":
    runpy.run_path(str(SCRIPT), run_name="__main__")
