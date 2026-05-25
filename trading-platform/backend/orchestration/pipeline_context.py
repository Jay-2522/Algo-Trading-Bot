from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineContext:
    """Mutable collection of engine outputs gathered during one pipeline run."""

    symbol: str
    timeframe: str
    market_data: dict[str, Any] | None = None
    strategy_snapshot: dict[str, Any] | None = None
    ai_decision: dict[str, Any] | None = None
    news_status: dict[str, Any] | None = None
    risk_status: dict[str, Any] | None = None
    execution_result: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_error(self, step: str, error: Exception | str) -> None:
        self.errors.append(f"{step}: {error}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "market_data": self.market_data,
            "strategy_snapshot": self.strategy_snapshot,
            "ai_decision": self.ai_decision,
            "news_status": self.news_status,
            "risk_status": self.risk_status,
            "execution_result": self.execution_result,
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }
