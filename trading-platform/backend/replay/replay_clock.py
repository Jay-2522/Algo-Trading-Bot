from typing import Any


class ReplayClock:
    """Create deterministic rolling replay step indexes."""

    def build_steps(
        self,
        candles: list[Any],
        window_size: int,
        step_size: int,
        max_steps: int | None = None,
    ) -> list[int]:
        if window_size <= 0:
            raise ValueError("window_size must be positive.")
        if step_size <= 0:
            raise ValueError("step_size must be positive.")
        if len(candles) < window_size:
            return []
        steps = list(range(window_size - 1, len(candles), step_size))
        return steps[:max_steps] if max_steps is not None else steps
