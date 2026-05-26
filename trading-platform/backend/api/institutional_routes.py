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
from backend.institutional_intelligence.structure_shift_models import StructureEvent, StructureShiftContext
from backend.institutional_intelligence.confluence_models import (
    ConfluenceComponentScore,
    ConfluenceContext,
    InstitutionalConfluenceScore,
)
from backend.institutional_intelligence.multi_timeframe_models import (
    InstitutionalNarrative,
    MultiTimeframeAlignment,
    TimeframeDirectionalBias,
)
from backend.institutional_intelligence.session_models import (
    KillzoneStatus,
    SessionIntelligenceContext,
    SessionLiquidityProfile,
    SessionManipulationSignal,
    TradingSessionRange,
)
from backend.institutional_intelligence.entry_model_models import EntryModelContext, InstitutionalEntryModel
from backend.institutional_intelligence.setup_validator_models import SetupValidationContext, SetupValidationResult
from backend.institutional_intelligence.simulation_decision_models import (
    InstitutionalSimulationDecision,
    SimulationDecisionContext,
    SimulationOrderIntent,
)


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
            "STRUCTURE_SHIFT",
            "INSTITUTIONAL_CONFLUENCE",
            "MULTI_TIMEFRAME_ALIGNMENT",
            "SESSION_KILLZONE_INTELLIGENCE",
            "INSTITUTIONAL_ENTRY_MODELS",
            "SETUP_VALIDATION_READINESS",
            "SIMULATION_DECISION_PIPELINE",
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


@router.get("/structure-shift/{symbol}", response_model=StructureShiftContext)
async def get_structure_shift(symbol: str, timeframe: str = Query(default="M15")) -> StructureShiftContext:
    return smc_service.analyze_structure_shift(symbol, timeframe)


@router.get("/structure-shift/bos/{symbol}", response_model=list[StructureEvent])
async def get_bos_events(symbol: str, timeframe: str = Query(default="M15")) -> list[StructureEvent]:
    return smc_service.analyze_structure_shift(symbol, timeframe).bos_events


@router.get("/structure-shift/choch/{symbol}", response_model=list[StructureEvent])
async def get_choch_events(symbol: str, timeframe: str = Query(default="M15")) -> list[StructureEvent]:
    return smc_service.analyze_structure_shift(symbol, timeframe).choch_events


@router.get("/structure-shift/mss/{symbol}", response_model=list[StructureEvent])
async def get_mss_events(symbol: str, timeframe: str = Query(default="M15")) -> list[StructureEvent]:
    return smc_service.analyze_structure_shift(symbol, timeframe).mss_events


@router.get("/structure-shift/latest/{symbol}", response_model=StructureEvent | None)
async def get_latest_structure_event(symbol: str, timeframe: str = Query(default="M15")) -> StructureEvent | None:
    return smc_service.analyze_structure_shift(symbol, timeframe).latest_event


@router.get("/structure-shift/high-quality/{symbol}", response_model=list[StructureEvent])
async def get_high_quality_structure_events(symbol: str, timeframe: str = Query(default="M15")) -> list[StructureEvent]:
    return smc_service.analyze_structure_shift(symbol, timeframe).high_quality_events


@router.get("/structure-shift/context/{symbol}")
async def get_structure_shift_confluence(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    return smc_service.analyze_structure_shift_confluence(symbol, timeframe)


@router.get("/confluence/{symbol}", response_model=ConfluenceContext)
async def get_confluence(symbol: str, timeframe: str = Query(default="M15")) -> ConfluenceContext:
    return smc_service.analyze_confluence(symbol, timeframe)


@router.get("/confluence/score/{symbol}", response_model=InstitutionalConfluenceScore)
async def get_confluence_score(symbol: str, timeframe: str = Query(default="M15")) -> InstitutionalConfluenceScore:
    return smc_service.analyze_confluence(symbol, timeframe).confluence_score


@router.get("/confluence/explanation/{symbol}")
async def get_confluence_explanation(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    score = smc_service.analyze_confluence(symbol, timeframe).confluence_score
    return {
        "symbol": score.symbol,
        "timeframe": score.timeframe,
        "dominant_direction": score.dominant_direction,
        "explanation": score.explanation,
        "strengths": score.strengths,
        "weaknesses": score.weaknesses,
        "warnings": score.warnings,
    }


@router.get("/confluence/components/{symbol}", response_model=list[ConfluenceComponentScore])
async def get_confluence_components(symbol: str, timeframe: str = Query(default="M15")) -> list[ConfluenceComponentScore]:
    return smc_service.analyze_confluence(symbol, timeframe).confluence_score.component_scores


@router.get("/confluence/readiness/{symbol}")
async def get_confluence_readiness(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    score = smc_service.analyze_confluence(symbol, timeframe).confluence_score
    return {
        "symbol": score.symbol,
        "timeframe": score.timeframe,
        "setup_quality": score.setup_quality,
        "trade_readiness": score.trade_readiness,
        "overall_score": score.overall_score,
        "confidence": score.confidence,
        "simulation_only": True,
        "live_execution_enabled": False,
    }


@router.get("/alignment/{symbol}", response_model=MultiTimeframeAlignment)
async def get_alignment(symbol: str) -> MultiTimeframeAlignment:
    return smc_service.analyze_multi_timeframe_alignment(symbol)


@router.get("/alignment/narrative/{symbol}", response_model=InstitutionalNarrative)
async def get_alignment_narrative(symbol: str) -> InstitutionalNarrative:
    alignment = smc_service.analyze_multi_timeframe_alignment(symbol)
    return alignment.institutional_narrative or InstitutionalNarrative(symbol=alignment.symbol)


@router.get("/alignment/conflicts/{symbol}")
async def get_alignment_conflicts(symbol: str) -> dict:
    alignment = smc_service.analyze_multi_timeframe_alignment(symbol)
    return {
        "symbol": alignment.symbol,
        "overall_direction": alignment.overall_direction,
        "alignment_quality": alignment.alignment_quality,
        "conflicts": alignment.conflicts,
        "warnings": alignment.warnings,
        "simulation_only": True,
        "live_execution_enabled": False,
    }


@router.get("/alignment/timeframes/{symbol}", response_model=list[TimeframeDirectionalBias])
async def get_alignment_timeframes(symbol: str) -> list[TimeframeDirectionalBias]:
    alignment = smc_service.analyze_multi_timeframe_alignment(symbol)
    return [
        alignment.macro_bias,
        alignment.directional_bias,
        alignment.execution_bias,
        alignment.precision_bias,
    ]


@router.get("/session/{symbol}", response_model=SessionIntelligenceContext)
async def get_session_intelligence(symbol: str, timeframe: str = Query(default="M15")) -> SessionIntelligenceContext:
    return smc_service.analyze_session_intelligence(symbol, timeframe)


@router.get("/session/ranges/{symbol}", response_model=list[TradingSessionRange])
async def get_session_ranges(symbol: str, timeframe: str = Query(default="M15")) -> list[TradingSessionRange]:
    context = smc_service.analyze_session_intelligence(symbol, timeframe)
    return [context.asian_range, context.london_range, context.new_york_range]


@router.get("/session/killzone/{symbol}", response_model=KillzoneStatus)
async def get_session_killzone(symbol: str, timeframe: str = Query(default="M15")) -> KillzoneStatus:
    return smc_service.analyze_session_intelligence(symbol, timeframe).active_killzone


@router.get("/session/liquidity/{symbol}", response_model=SessionLiquidityProfile)
async def get_session_liquidity(symbol: str, timeframe: str = Query(default="M15")) -> SessionLiquidityProfile:
    return smc_service.analyze_session_intelligence(symbol, timeframe).liquidity_profile


@router.get("/session/manipulation/{symbol}", response_model=list[SessionManipulationSignal])
async def get_session_manipulation(
    symbol: str, timeframe: str = Query(default="M15")
) -> list[SessionManipulationSignal]:
    return smc_service.analyze_session_intelligence(symbol, timeframe).manipulation_signals


@router.get("/session/readiness/{symbol}")
async def get_session_readiness(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    context = smc_service.analyze_session_intelligence(symbol, timeframe)
    return {
        "symbol": context.symbol,
        "timeframe": context.timeframe,
        "current_session": context.current_session,
        "trade_timing_readiness": context.trade_timing_readiness,
        "session_quality_score": context.session_quality_score,
        "warnings": context.warnings,
        "simulation_only": True,
        "live_execution_enabled": False,
    }


@router.get("/entry-models/{symbol}", response_model=EntryModelContext)
async def get_entry_models(symbol: str, timeframe: str = Query(default="M15")) -> EntryModelContext:
    return smc_service.analyze_entry_models(symbol, timeframe)


@router.get("/entry-models/best/{symbol}", response_model=InstitutionalEntryModel | None)
async def get_best_entry_model(symbol: str, timeframe: str = Query(default="M15")) -> InstitutionalEntryModel | None:
    return smc_service.analyze_entry_models(symbol, timeframe).best_model


@router.get("/entry-models/ready/{symbol}", response_model=list[InstitutionalEntryModel])
async def get_ready_entry_models(symbol: str, timeframe: str = Query(default="M15")) -> list[InstitutionalEntryModel]:
    return smc_service.analyze_entry_models(symbol, timeframe).ready_models


@router.get("/entry-models/waiting/{symbol}", response_model=list[InstitutionalEntryModel])
async def get_waiting_entry_models(symbol: str, timeframe: str = Query(default="M15")) -> list[InstitutionalEntryModel]:
    return smc_service.analyze_entry_models(symbol, timeframe).waiting_models


@router.get("/entry-models/avoided/{symbol}", response_model=list[InstitutionalEntryModel])
async def get_avoided_entry_models(symbol: str, timeframe: str = Query(default="M15")) -> list[InstitutionalEntryModel]:
    return smc_service.analyze_entry_models(symbol, timeframe).avoided_models


@router.get("/entry-models/explanation/{symbol}")
async def get_entry_model_explanation(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    context = smc_service.analyze_entry_models(symbol, timeframe)
    best = context.best_model
    return {
        "symbol": context.symbol,
        "timeframe": context.timeframe,
        "overall_readiness": context.overall_readiness,
        "confidence": context.confidence,
        "best_model_type": best.model_type if best else None,
        "explanation": best.metadata.get("explanation", {}) if best else {},
        "simulation_only": True,
        "live_execution_enabled": False,
    }


@router.get("/setup-validation/{symbol}", response_model=SetupValidationContext)
async def get_setup_validation(symbol: str, timeframe: str = Query(default="M15")) -> SetupValidationContext:
    return smc_service.analyze_setup_validation(symbol, timeframe)


@router.get("/setup-validation/approved/{symbol}", response_model=list[SetupValidationResult])
async def get_approved_setups(symbol: str, timeframe: str = Query(default="M15")) -> list[SetupValidationResult]:
    return smc_service.analyze_setup_validation(symbol, timeframe).approved_setups


@router.get("/setup-validation/waiting/{symbol}", response_model=list[SetupValidationResult])
async def get_waiting_setups(symbol: str, timeframe: str = Query(default="M15")) -> list[SetupValidationResult]:
    return smc_service.analyze_setup_validation(symbol, timeframe).waiting_setups


@router.get("/setup-validation/rejected/{symbol}", response_model=list[SetupValidationResult])
async def get_rejected_setups(symbol: str, timeframe: str = Query(default="M15")) -> list[SetupValidationResult]:
    return smc_service.analyze_setup_validation(symbol, timeframe).rejected_setups


@router.get("/setup-validation/best/{symbol}", response_model=SetupValidationResult | None)
async def get_best_validated_setup(symbol: str, timeframe: str = Query(default="M15")) -> SetupValidationResult | None:
    return smc_service.analyze_setup_validation(symbol, timeframe).best_setup


@router.get("/setup-validation/readiness/{symbol}")
async def get_setup_execution_readiness(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    context = smc_service.analyze_setup_validation(symbol, timeframe)
    return {
        "symbol": context.symbol,
        "timeframe": context.timeframe,
        "simulation_eligible": context.simulation_eligible,
        "execution_readiness": context.execution_readiness,
        "confidence": context.confidence,
        "best_decision": context.best_decision,
        "simulation_only": True,
        "live_execution_enabled": False,
    }


@router.get("/simulation-decision/{symbol}", response_model=SimulationDecisionContext)
async def get_simulation_decision(symbol: str, timeframe: str = Query(default="M15")) -> SimulationDecisionContext:
    return smc_service.analyze_simulation_decision(symbol, timeframe)


@router.get("/simulation-decision/action/{symbol}", response_model=InstitutionalSimulationDecision)
async def get_simulation_action(symbol: str, timeframe: str = Query(default="M15")) -> InstitutionalSimulationDecision:
    return smc_service.analyze_simulation_decision(symbol, timeframe).decision


@router.get("/simulation-decision/intent/{symbol}", response_model=SimulationOrderIntent)
async def get_simulation_intent(symbol: str, timeframe: str = Query(default="M15")) -> SimulationOrderIntent:
    return smc_service.analyze_simulation_decision(symbol, timeframe).decision.order_intent


@router.get("/simulation-decision/explanation/{symbol}")
async def get_simulation_explanation(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    decision = smc_service.analyze_simulation_decision(symbol, timeframe).decision
    return {
        "symbol": decision.symbol,
        "timeframe": decision.timeframe,
        "action": decision.action,
        "explanation": decision.explanation,
        "approval_reasons": decision.approval_reasons,
        "rejection_reasons": decision.rejection_reasons,
        "warnings": decision.warnings,
        "simulation_only": True,
        "live_execution_enabled": False,
    }


@router.get("/simulation-decision/readiness/{symbol}")
async def get_simulation_readiness(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    decision = smc_service.analyze_simulation_decision(symbol, timeframe).decision
    return {
        "symbol": decision.symbol,
        "timeframe": decision.timeframe,
        "approved_for_simulation": decision.approved_for_simulation,
        "readiness": decision.readiness,
        "setup_quality": decision.setup_quality,
        "risk_quality": decision.order_intent.risk_quality,
        "simulation_only": decision.simulation_only,
        "live_execution_enabled": decision.live_execution_enabled,
    }
