from fastapi import APIRouter

from backend.deployment.backup_models import BackupReadinessStatus
from backend.deployment.backup_readiness_service import BackupReadinessService
from backend.deployment.recovery_runbook_service import RecoveryRunbookService


router = APIRouter(prefix="/backup", tags=["Backup & Recovery"])


@router.get("/status", response_model=BackupReadinessStatus)
async def get_backup_status() -> BackupReadinessStatus:
    return BackupReadinessService().get_status()


@router.get("/strategy")
async def get_backup_strategy() -> dict:
    return BackupReadinessService().get_backup_plan()


@router.get("/recovery")
async def get_backup_recovery() -> dict:
    return RecoveryRunbookService().get_full_recovery_plan()


@router.get("/rollback")
async def get_backup_rollback() -> dict:
    return BackupReadinessService().get_rollback_plan()


@router.get("/incident-response")
async def get_backup_incident_response() -> dict:
    return {
        "api_outage": "Check /health, backend process, logs/platform.log, and restart backend manually if needed.",
        "mt5_unavailable": "Restart MT5 manually and verify demo account only.",
        "deployment_failure": "Rollback to previous known-good commit or image and restore env from secure vault.",
        "high_error_rate": "Inspect /monitoring/logs/errors and pause deployment changes.",
        "security_incident": "Rotate secrets outside repo, preserve logs, and keep live/broker execution disabled.",
        "simulation_only": True,
        "demo_execution": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
