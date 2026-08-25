"""Application and infrastructure health-check routes."""

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.utils.logger import get_logger


router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger(__name__)


def _utc_timestamp() -> str:
    """Return the current timezone-aware UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


async def _database_is_connected() -> tuple[bool, str | None]:
    """Run a minimal query and return database connectivity information."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # Database drivers expose several exception types.
        logger.exception("Database health check failed")
        return False, str(exc)


@router.get("")
async def health_check() -> dict[str, str]:
    """Return basic application identity and liveness information."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "timestamp": _utc_timestamp(),
    }


@router.get("/db")
async def database_health_check() -> JSONResponse:
    """Verify that the application can execute a database query."""
    connected, detail = await _database_is_connected()
    if connected:
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "database": "connected"},
        )

    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "database": "disconnected",
            "detail": detail,
        },
    )


@router.get("/full")
async def full_health_check() -> dict[str, Any]:
    """Return combined database, upload directory, and LLM configuration health."""
    database_ok, _ = await _database_is_connected()
    upload_directory = Path(settings.UPLOAD_DIR)
    upload_ok = upload_directory.is_dir() and os.access(upload_directory, os.W_OK)
    llm_configured = bool(settings.OPENAI_API_KEY.strip())

    checks: dict[str, str | bool] = {
        "database": "ok" if database_ok else "error",
        "upload_directory": "ok" if upload_ok else "error",
        "llm_configured": llm_configured,
    }
    all_healthy = database_ok and upload_ok and llm_configured

    return {
        "status": "ok" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": _utc_timestamp(),
    }
