from fastapi import APIRouter

from backend.security.security_models import AccessPolicyStatus, SecretsAuditResult, SecurityReadinessStatus
from backend.security.security_readiness_service import SecurityReadinessService


router = APIRouter(prefix="/security", tags=["Security Readiness"])


@router.get("/status", response_model=SecurityReadinessStatus)
async def get_security_status() -> SecurityReadinessStatus:
    return SecurityReadinessService().get_status()


@router.get("/secrets-audit", response_model=SecretsAuditResult)
async def get_security_secrets_audit() -> SecretsAuditResult:
    return SecurityReadinessService().secrets_auditor.audit()


@router.get("/access-policy", response_model=AccessPolicyStatus)
async def get_security_access_policy() -> AccessPolicyStatus:
    return SecurityReadinessService().get_access_policy()


@router.get("/blockers")
async def get_security_blockers() -> dict:
    return SecurityReadinessService().get_blockers()


@router.get("/warnings")
async def get_security_warnings() -> dict:
    return SecurityReadinessService().get_warnings()


@router.get("/audit-events")
async def get_security_audit_events(limit: int = 100) -> list[dict]:
    return SecurityReadinessService().list_audit_events(limit)
