"""Integration tests for dataset inspection and cached profiles."""

from collections.abc import AsyncGenerator
from io import BytesIO
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


SAMPLE_CSV = """id,name,age,salary,department,join_date
1,Alice,30,75000,Engineering,2020-01-15
2,Bob,25,55000,Marketing,2021-03-20
3,Charlie,35,90000,Engineering,2019-07-10
4,Diana,28,62000,Sales,2022-01-05
5,Eve,32,80000,Engineering,2020-11-30
1,Alice,30,75000,Engineering,2020-01-15
"""


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous client connected directly to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client


async def _upload_dataset(client: AsyncClient, session_id: str) -> int:
    """Upload the sample dataset and return its database identifier."""
    response = await client.post(
        "/api/datasets/upload",
        headers={"X-Session-ID": session_id},
        files={
            "file": (
                "sample_inspection.csv",
                BytesIO(SAMPLE_CSV.encode("utf-8")),
                "text/csv",
            )
        },
    )
    assert response.status_code == 201
    return int(response.json()["data"]["dataset"]["id"])


async def _upload_and_inspect(
    client: AsyncClient,
    session_id: str,
) -> tuple[int, dict[str, Any]]:
    """Upload and inspect the sample dataset, returning its profile."""
    dataset_id = await _upload_dataset(client, session_id)
    response = await client.post(
        f"/api/datasets/{dataset_id}/inspect",
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 200
    return dataset_id, response.json()["data"]["profile"]


def _column(profile: dict[str, Any], name: str) -> dict[str, Any]:
    """Find one named column profile in a complete dataset profile."""
    return next(
        item for item in profile["column_profiles"] if item["name"] == name
    )


async def test_inspect_endpoint(client: AsyncClient) -> None:
    """Verify inspection reports rows and duplicate records."""
    _, profile = await _upload_and_inspect(client, "inspect-endpoint")

    assert profile["basic_info"]["row_count"] == 6
    assert profile["basic_info"]["duplicate_count"] == 1
    assert profile["basic_info"]["has_duplicates"] is True


async def test_column_profiles_present(client: AsyncClient) -> None:
    """Verify every column is profiled with the expected category."""
    _, profile = await _upload_and_inspect(client, "inspect-columns")

    assert len(profile["column_profiles"]) == 6
    assert _column(profile, "age")["category"] == "numeric"
    assert _column(profile, "department")["category"] == "categorical"


async def test_numeric_stats(client: AsyncClient) -> None:
    """Verify numeric column statistics are correctly calculated."""
    _, profile = await _upload_and_inspect(client, "inspect-numerics")
    salary = _column(profile, "salary")

    assert salary["mean"] == pytest.approx(73500, abs=1000)
    assert salary["min"] == 55000.0
    assert salary["max"] == 90000.0


async def test_missing_analysis_empty(client: AsyncClient) -> None:
    """Verify a complete dataset produces no missing-value recommendations."""
    _, profile = await _upload_and_inspect(client, "inspect-missing")

    assert profile["missing_analysis"] == []


async def test_get_profile_before_inspect(client: AsyncClient) -> None:
    """Verify an uninspected dataset does not expose a cached profile."""
    session_id = "inspect-before-profile"
    dataset_id = await _upload_dataset(client, session_id)

    response = await client.get(
        f"/api/datasets/{dataset_id}/profile",
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 404
    assert "not been inspected yet" in response.json()["message"]


async def test_get_profile_after_inspect(client: AsyncClient) -> None:
    """Verify a generated profile can be retrieved from the database cache."""
    session_id = "inspect-after-profile"
    dataset_id, _ = await _upload_and_inspect(client, session_id)

    response = await client.get(
        f"/api/datasets/{dataset_id}/profile",
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 200
    assert response.json()["data"]["profile"] is not None


async def test_categorical_top_values(client: AsyncClient) -> None:
    """Verify categorical frequencies exclude exact duplicate records."""
    _, profile = await _upload_and_inspect(client, "inspect-categories")
    department = _column(profile, "department")

    assert isinstance(department["top_values"], list)
    engineering = next(
        item
        for item in department["top_values"]
        if item["value"] == "Engineering"
    )
    assert engineering["count"] == 3
