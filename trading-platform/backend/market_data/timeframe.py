from typing import Dict

from backend.broker_integrations.mt5.mt5_client import mt5


FALLBACK_TIMEFRAMES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
    "H4": 16388,
    "D1": 16408,
}


def _mt5_timeframe(name: str) -> int:
    if mt5 is None:
        return FALLBACK_TIMEFRAMES[name]
    return getattr(mt5, f"TIMEFRAME_{name}", FALLBACK_TIMEFRAMES[name])


TIMEFRAME_MAP: Dict[str, int] = {
    "M1": _mt5_timeframe("M1"),
    "M5": _mt5_timeframe("M5"),
    "M15": _mt5_timeframe("M15"),
    "M30": _mt5_timeframe("M30"),
    "H1": _mt5_timeframe("H1"),
    "H4": _mt5_timeframe("H4"),
    "D1": _mt5_timeframe("D1"),
}

SUPPORTED_TIMEFRAMES = tuple(TIMEFRAME_MAP.keys())


def get_mt5_timeframe(timeframe: str) -> int:
    """Map an internal timeframe string to an MT5 timeframe constant."""

    normalized = timeframe.upper().strip()
    if normalized not in TIMEFRAME_MAP:
        supported = ", ".join(SUPPORTED_TIMEFRAMES)
        raise ValueError(f"Unsupported timeframe '{timeframe}'. Supported timeframes: {supported}.")
    return TIMEFRAME_MAP[normalized]

