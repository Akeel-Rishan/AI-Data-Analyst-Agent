"""Helpers for building standardized API response payloads."""

from typing import Any


def success_response(
    data: Any,
    message: str = "Success",
    status_code: int = 200,
) -> dict[str, Any]:
    """Build a successful API response payload."""
    _ = status_code
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(
    message: str,
    detail: str | None = None,
    status_code: int = 400,
) -> dict[str, Any]:
    """Build an unsuccessful API response payload."""
    _ = status_code
    return {
        "success": False,
        "message": message,
        "detail": detail,
    }


def paginated_response(
    data: list[Any],
    total: int,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Build a successful response with pagination metadata."""
    total_pages = (total + page_size - 1) // page_size
    return {
        "success": True,
        "data": data,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    }
