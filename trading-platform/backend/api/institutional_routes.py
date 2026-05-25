from fastapi import APIRouter, Query

from backend.institutional_intelligence.smc_models import (
    DisplacementMove,
    InstitutionalContext,
    LiquidityPool,
    PremiumDiscountZone,
    StructureBias,
    SwingPoint,
)
from backend.institutional_intelligence.smc_service import SMCService
from backend.institutional_intelligence.liquidity_sweep_models import LiquiditySweep, SweepContext


router = APIRouter(prefix="/institutional", tags=["Institutional Intelligence"])
smc_service = SMCService()


@router.get("/status")
async def get_institutional_status() -> dict:
    return {
        "status": "operational",
        "mode": "MARKET_STRUCTURE_ANALYSIS_ONLY",
        "simulation_only": True,
        "live_execution_enabled": False,
        "concepts_supported": [
            "SWINGS",
            "LIQUIDITY_POOLS",
            "STRUCTURE_BIAS",
            "PREMIUM_DISCOUNT",
            "DISPLACEMENT",
            "LIQUIDITY_SWEEPS",
        ],
    }


@router.get("/context/{symbol}", response_model=InstitutionalContext)
async def get_context(symbol: str, timeframe: str = Query(default="M15")) -> InstitutionalContext:
    return smc_service.analyze_symbol(symbol, timeframe)


@router.get("/swings/{symbol}", response_model=list[SwingPoint])
async def get_swings(symbol: str, timeframe: str = Query(default="M15")) -> list[SwingPoint]:
    return smc_service.analyze_symbol(symbol, timeframe).swings


@router.get("/liquidity/{symbol}", response_model=list[LiquidityPool])
async def get_liquidity(symbol: str, timeframe: str = Query(default="M15")) -> list[LiquidityPool]:
    return smc_service.analyze_symbol(symbol, timeframe).liquidity_pools


@router.get("/bias/{symbol}", response_model=StructureBias)
async def get_bias(symbol: str, timeframe: str = Query(default="M15")) -> StructureBias:
    return smc_service.analyze_symbol(symbol, timeframe).structure_bias


@router.get("/premium-discount/{symbol}", response_model=PremiumDiscountZone)
async def get_premium_discount(symbol: str, timeframe: str = Query(default="M15")) -> PremiumDiscountZone:
    return smc_service.analyze_symbol(symbol, timeframe).premium_discount


@router.get("/displacement/{symbol}", response_model=list[DisplacementMove])
async def get_displacement(symbol: str, timeframe: str = Query(default="M15")) -> list[DisplacementMove]:
    return smc_service.analyze_symbol(symbol, timeframe).displacement


@router.get("/sweeps/{symbol}", response_model=SweepContext)
async def get_sweeps(symbol: str, timeframe: str = Query(default="M15")) -> SweepContext:
    return smc_service.analyze_liquidity_sweeps(symbol, timeframe)


@router.get("/latest-sweep/{symbol}", response_model=LiquiditySweep | None)
async def get_latest_sweep(symbol: str, timeframe: str = Query(default="M15")) -> LiquiditySweep | None:
    return smc_service.analyze_liquidity_sweeps(symbol, timeframe).latest_sweep


@router.get("/high-quality-sweeps/{symbol}", response_model=list[LiquiditySweep])
async def get_high_quality_sweeps(symbol: str, timeframe: str = Query(default="M15")) -> list[LiquiditySweep]:
    return smc_service.analyze_liquidity_sweeps(symbol, timeframe).high_quality_sweeps
