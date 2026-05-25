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
from backend.institutional_intelligence.fair_value_gap_models import FairValueGap, FVGContext
from backend.institutional_intelligence.order_block_models import OrderBlock, OrderBlockContext
from backend.institutional_intelligence.breaker_block_models import BreakerBlock, BreakerBlockContext


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
            "FAIR_VALUE_GAPS",
            "ORDER_BLOCKS",
            "BREAKER_BLOCKS",
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


@router.get("/fvg/{symbol}", response_model=FVGContext)
async def get_fvg_context(symbol: str, timeframe: str = Query(default="M15")) -> FVGContext:
    return smc_service.analyze_fvgs(symbol, timeframe)


@router.get("/fvg/fresh/{symbol}", response_model=list[FairValueGap])
async def get_fresh_fvgs(symbol: str, timeframe: str = Query(default="M15")) -> list[FairValueGap]:
    return smc_service.analyze_fvgs(symbol, timeframe).fresh_fvgs


@router.get("/fvg/mitigated/{symbol}", response_model=list[FairValueGap])
async def get_mitigated_fvgs(symbol: str, timeframe: str = Query(default="M15")) -> list[FairValueGap]:
    return smc_service.analyze_fvgs(symbol, timeframe).mitigated_fvgs


@router.get("/fvg/high-quality/{symbol}", response_model=list[FairValueGap])
async def get_high_quality_fvgs(symbol: str, timeframe: str = Query(default="M15")) -> list[FairValueGap]:
    return smc_service.analyze_fvgs(symbol, timeframe).high_quality_fvgs


@router.get("/fvg/latest/{symbol}", response_model=FairValueGap | None)
async def get_latest_fvg(symbol: str, timeframe: str = Query(default="M15")) -> FairValueGap | None:
    return smc_service.analyze_fvgs(symbol, timeframe).latest_fvg


@router.get("/order-blocks/{symbol}", response_model=OrderBlockContext)
async def get_order_blocks(symbol: str, timeframe: str = Query(default="M15")) -> OrderBlockContext:
    return smc_service.analyze_order_blocks(symbol, timeframe)


@router.get("/order-blocks/fresh/{symbol}", response_model=list[OrderBlock])
async def get_fresh_order_blocks(symbol: str, timeframe: str = Query(default="M15")) -> list[OrderBlock]:
    return smc_service.analyze_order_blocks(symbol, timeframe).fresh_order_blocks


@router.get("/order-blocks/mitigated/{symbol}", response_model=list[OrderBlock])
async def get_mitigated_order_blocks(symbol: str, timeframe: str = Query(default="M15")) -> list[OrderBlock]:
    return smc_service.analyze_order_blocks(symbol, timeframe).mitigated_order_blocks


@router.get("/order-blocks/high-quality/{symbol}", response_model=list[OrderBlock])
async def get_high_quality_order_blocks(symbol: str, timeframe: str = Query(default="M15")) -> list[OrderBlock]:
    return smc_service.analyze_order_blocks(symbol, timeframe).high_quality_order_blocks


@router.get("/order-blocks/latest/{symbol}", response_model=OrderBlock | None)
async def get_latest_order_block(symbol: str, timeframe: str = Query(default="M15")) -> OrderBlock | None:
    return smc_service.analyze_order_blocks(symbol, timeframe).latest_order_block


@router.get("/order-blocks/context/{symbol}")
async def get_order_block_confluence_context(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    return smc_service.analyze_order_block_confluence(symbol, timeframe)


@router.get("/breakers/{symbol}", response_model=BreakerBlockContext)
async def get_breakers(symbol: str, timeframe: str = Query(default="M15")) -> BreakerBlockContext:
    return smc_service.analyze_breaker_blocks(symbol, timeframe)


@router.get("/breakers/fresh/{symbol}", response_model=list[BreakerBlock])
async def get_fresh_breakers(symbol: str, timeframe: str = Query(default="M15")) -> list[BreakerBlock]:
    return smc_service.analyze_breaker_blocks(symbol, timeframe).fresh_breakers


@router.get("/breakers/mitigated/{symbol}", response_model=list[BreakerBlock])
async def get_mitigated_breakers(symbol: str, timeframe: str = Query(default="M15")) -> list[BreakerBlock]:
    return smc_service.analyze_breaker_blocks(symbol, timeframe).mitigated_breakers


@router.get("/breakers/high-quality/{symbol}", response_model=list[BreakerBlock])
async def get_high_quality_breakers(symbol: str, timeframe: str = Query(default="M15")) -> list[BreakerBlock]:
    return smc_service.analyze_breaker_blocks(symbol, timeframe).high_quality_breakers


@router.get("/breakers/latest/{symbol}", response_model=BreakerBlock | None)
async def get_latest_breaker(symbol: str, timeframe: str = Query(default="M15")) -> BreakerBlock | None:
    return smc_service.analyze_breaker_blocks(symbol, timeframe).latest_breaker


@router.get("/breakers/context/{symbol}")
async def get_breaker_confluence_context(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    return smc_service.analyze_breaker_confluence(symbol, timeframe)
