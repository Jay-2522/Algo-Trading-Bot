import runpy
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "trading-platform"
sys.path.insert(0, str(APP_ROOT))

runpy.run_path(str(APP_ROOT / "tests" / "phase9_day4_verification.py"), run_name="__main__")
