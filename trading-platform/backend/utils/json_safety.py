from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


def to_json_safe(value: Any) -> Any:
    """Recursively convert common Python/Pydantic objects into JSON-safe values."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def safe_error_payload(message: str, module: str = "unknown") -> dict[str, Any]:
    return {
        "status": "unavailable",
        "module": module,
        "message": message,
        "simulation_only": True,
        "live_execution_enabled": False,
    }
