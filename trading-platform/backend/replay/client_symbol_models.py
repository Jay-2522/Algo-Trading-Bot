from typing import Literal

from pydantic import BaseModel, Field


class ClientInstrument(BaseModel):
    canonical_symbol: str
    display_name: str
    market_type: Literal["FOREX", "COMMODITY_CFD", "INDIAN_INDEX"]
    base_asset: str
    quote_asset: str
    supported_timeframes: list[str] = Field(default_factory=lambda: ["M5", "M15", "H1", "H4"])
    broker_aliases: list[str] = Field(default_factory=list)
    replay_supported: bool = True
    simulation_only: bool = True


class ClientSymbolResolution(BaseModel):
    input_symbol: str
    canonical_symbol: str | None = None
    supported: bool = False
    market_type: str | None = None
    message: str
