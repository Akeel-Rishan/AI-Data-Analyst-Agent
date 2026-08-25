"""Main FastAPI application entry point for AI Data Analyst Agent."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_all_tables
from app.middleware import RequestLoggingMiddleware
from app.routers import (
    analysis_router,
    conversations_router,
    datasets_router,
    health_router,
    reports_router,
)
from app.utils.exceptions import DataAnalystException
from app.utils.logger import logger
from app.utils.responses import error_response


APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize application resources and log lifecycle events."""
    logger.info("Starting %s version %s", settings.APP_NAME, APP_VERSION)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    await create_all_tables()
    logger.info("Database connected successfully")
    logger.info("Application startup complete")
    yield
    logger.info("Application shutting down")


app: FastAPI = FastAPI(
    title=settings.APP_NAME,
    description="Intelligent data analysis platform powered by AI",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(health_router)
app.include_router(datasets_router)
app.include_router(analysis_router)
app.include_router(conversations_router)
app.include_router(reports_router)


@app.exception_handler(DataAnalystException)
async def data_analyst_exception_handler(
    _request: Request,
    exc: DataAnalystException,
) -> JSONResponse:
    """Convert an expected application exception into a JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.message,
            status_code=exc.status_code,
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log unexpected exceptions and return a safe generic response."""
    logger.exception("Unhandled application exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Return application discovery links and version information."""
    return {
        "app": settings.APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
