from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.portfolio.portfolio_service import PortfolioService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/portfolio", tags=["Portfolio Analytics"])
portfolio_service = PortfolioService()


@router.get("/status")
async def get_portfolio_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(portfolio_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Portfolio status unavailable: {exc}", "portfolio"))


@router.get("/overview")
async def get_portfolio_overview() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(portfolio_service.get_overview()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Portfolio overview unavailable: {exc}", "portfolio"))


@router.get("/accounts")
async def get_portfolio_accounts() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(portfolio_service.get_accounts()))
    except Exception:
        return JSONResponse(content=[])


@router.get("/exposure")
async def get_portfolio_exposure() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(portfolio_service.get_exposure()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Portfolio exposure unavailable: {exc}", "portfolio"))


@router.get("/pnl-summary")
async def get_portfolio_pnl_summary() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(portfolio_service.get_pnl_summary()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Portfolio P&L unavailable: {exc}", "portfolio"))
