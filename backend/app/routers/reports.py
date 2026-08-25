"""Report API route placeholders."""

from fastapi import APIRouter


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/generate")
async def generate_report() -> dict[str, str]:
    """Return the placeholder for future report generation."""
    return {"message": "Report generation - coming in Step 5.3"}


@router.get("/{report_id}/download")
async def download_report(report_id: int) -> dict[str, str]:
    """Return the placeholder for downloading a generated report."""
    _ = report_id
    return {"message": "Report download - coming in Step 5.3"}
