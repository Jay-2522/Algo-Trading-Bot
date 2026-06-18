from pathlib import Path


_APP_BACKEND = Path(__file__).resolve().parents[1] / "trading-platform" / "backend"
if _APP_BACKEND.is_dir():
    __path__.append(str(_APP_BACKEND))
