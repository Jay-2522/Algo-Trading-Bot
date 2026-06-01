from fastapi import APIRouter

from backend.deployment.go_live_assessment import GoLiveAssessmentService
from backend.deployment.production_readiness_models import GoLiveAssessment, ProductionReadinessReport
from backend.deployment.production_readiness_service import ProductionReadinessService


router = APIRouter(prefix="/production-readiness", tags=["Production Readiness"])
production_readiness_service = ProductionReadinessService()
go_live_assessment_service = GoLiveAssessmentService(production_readiness_service=production_readiness_service)


@router.get("/status", response_model=ProductionReadinessReport)
async def get_production_readiness_status() -> ProductionReadinessReport:
    return production_readiness_service.get_report()


@router.get("/report", response_model=ProductionReadinessReport)
async def get_production_readiness_report() -> ProductionReadinessReport:
    return production_readiness_service.get_report()


@router.get("/assessment", response_model=GoLiveAssessment)
async def get_go_live_assessment() -> GoLiveAssessment:
    return go_live_assessment_service.run_assessment()


@router.get("/blockers")
async def get_production_readiness_blockers() -> dict:
    report = production_readiness_service.get_report()
    return {
        "blockers": report.blockers,
        "readiness_score": report.readiness_score,
        "simulation_only": True,
        "demo_execution": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }


@router.get("/recommendations")
async def get_production_readiness_recommendations() -> dict:
    report = production_readiness_service.get_report()
    return {
        "recommendations": report.recommendations,
        "readiness_score": report.readiness_score,
        "overall_status": report.overall_status,
        "simulation_only": True,
        "demo_execution": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
