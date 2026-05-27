from typing import Any


class ReplayWindowBuilder:
    """Build visible candle windows without exposing future candles."""

    def build_window(self, candles: list[Any], end_index: int, window_size: int) -> list[Any]:
        if not candles or end_index < 0 or window_size <= 0:
            return []
        safe_end = min(end_index, len(candles) - 1)
        start = max(0, safe_end - window_size + 1)
        return list(candles[start : safe_end + 1])
