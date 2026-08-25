"""Integration tests for dataset upload and ownership endpoints."""

from collections.abc import AsyncGenerator
from io import BytesIO, StringIO
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous client connected directly to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client


def _csv_file() -> BytesIO:
    """Create a small in-memory CSV file for upload tests."""
    csv_text = StringIO()
    csv_text.write("name,value\nalpha,1\nbeta,2\n")
    return BytesIO(csv_text.getvalue().encode("utf-8"))


async def _upload_csv(client: AsyncClient, session_id: str) -> dict[str, Any]:
    """Upload a CSV and return the decoded response payload."""
    response = await client.post(
        "/api/datasets/upload",
        headers={"X-Session-ID": session_id},
        files={"file": ("sales_data.csv", _csv_file(), "text/csv")},
    )
    assert response.status_code == 201
    return response.json()


async def test_upload_valid_csv(client: AsyncClient) -> None:
    """Verify a valid in-memory CSV is stored and registered."""
    payload = await _upload_csv(client, "test-session-001")

    assert payload["success"] is True
    dataset = payload["data"]["dataset"]
    assert dataset["id"]
    assert dataset["file_type"] == "csv"


async def test_upload_invalid_extension(client: AsyncClient) -> None:
    """Verify unsupported file extensions receive a validation error."""
    response = await client.post(
        "/api/datasets/upload",
        headers={"X-Session-ID": "test-invalid-extension"},
        files={"file": ("notes.txt", BytesIO(b"not a dataset"), "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["success"] is False


async def test_upload_file_too_large(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify files above the configured limit receive a size error."""
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 0)
    response = await client.post(
        "/api/datasets/upload",
        headers={"X-Session-ID": "test-oversized-file"},
        files={"file": ("oversized.csv", BytesIO(b"a,b\n1,2\n"), "text/csv")},
    )

    assert response.status_code == 400
    assert "exceeds maximum allowed size" in response.json()["message"]


async def test_list_datasets(client: AsyncClient) -> None:
    """Verify a session can list its uploaded datasets."""
    session_id = "test-list-datasets"
    await _upload_csv(client, session_id)

    response = await client.get(
        "/api/datasets",
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 200
    assert isinstance(response.json()["data"]["datasets"], list)
    assert len(response.json()["data"]["datasets"]) >= 1


async def test_get_dataset_by_id(client: AsyncClient) -> None:
    """Verify a session can retrieve its uploaded dataset by identifier."""
    session_id = "test-get-dataset"
    upload = await _upload_csv(client, session_id)
    dataset_id = upload["data"]["dataset"]["id"]

    response = await client.get(
        f"/api/datasets/{dataset_id}",
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 200
    assert response.json()["data"]["filename"] == "sales_data.csv"


async def test_get_dataset_wrong_session(client: AsyncClient) -> None:
    """Verify one browser session cannot retrieve another session's dataset."""
    upload = await _upload_csv(client, "test-owner-session-a")
    dataset_id = upload["data"]["dataset"]["id"]

    response = await client.get(
        f"/api/datasets/{dataset_id}",
        headers={"X-Session-ID": "test-owner-session-b"},
    )

    assert response.status_code == 404


async def test_delete_dataset(client: AsyncClient) -> None:
    """Verify deletion removes a dataset from subsequent retrieval."""
    session_id = "test-delete-dataset"
    upload = await _upload_csv(client, session_id)
    dataset_id = upload["data"]["dataset"]["id"]

    delete_response = await client.delete(
        f"/api/datasets/{dataset_id}",
        headers={"X-Session-ID": session_id},
    )
    get_response = await client.get(
        f"/api/datasets/{dataset_id}",
        headers={"X-Session-ID": session_id},
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True
    assert get_response.status_code == 404
