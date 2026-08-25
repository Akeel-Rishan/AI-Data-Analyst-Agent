"""Data analysis API route placeholders."""

from fastapi import APIRouter


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/ask")
async def ask_question() -> dict[str, str]:
    """Return the placeholder for future analysis questions."""
    return {"message": "Ask question - coming in Step 3.4"}


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: int) -> dict[str, str]:
    """Return the placeholder for retrieving an analysis result."""
    _ = analysis_id
    return {"message": "Get analysis - coming in Step 3.4"}


@router.get("/dataset/{dataset_id}/history")
async def get_analysis_history(dataset_id: int) -> dict[str, str]:
    """Return the placeholder for a dataset's analysis history."""
    _ = dataset_id
    return {"message": "Analysis history - coming in Step 3.4"}
