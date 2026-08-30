"""Integration tests for configurable dataset cleaning operations."""

from collections.abc import AsyncGenerator
from io import BytesIO
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.services.cleaner_service import CleaningOperation


DIRTY_CSV = """id,Name ,age,salary,department,join_date
1,Alice,30,75000,Engineering,2020-01-15
2,Bob,25,,Marketing,2021-03-20
3,Charlie,,90000,Engineering,2019-07-10
4,Diana,28,62000,Sales ,2022-01-05
5,Eve,32,80000,Engineering,2020-11-30
1,Alice,30,75000,Engineering,2020-01-15
6,Frank,29,,Marketing,2021-06-15
7,,27,58000,Sales,2023-02-01
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


async def _upload_dirty_dataset(client: AsyncClient, session_id: str) -> int:
    """Upload the dirty CSV fixture and return its dataset identifier."""
    response = await client.post(
        "/api/datasets/upload",
        headers={"X-Session-ID": session_id},
        files={
            "file": (
                "dirty_data.csv",
                BytesIO(DIRTY_CSV.encode("utf-8")),
                "text/csv",
            )
        },
    )
    assert response.status_code == 201
    return int(response.json()["data"]["dataset"]["id"])


async def _inspect(
    client: AsyncClient,
    dataset_id: int,
    session_id: str,
) -> dict[str, Any]:
    """Inspect an uploaded dataset and return its generated profile."""
    response = await client.post(
        f"/api/datasets/{dataset_id}/inspect",
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 200
    return response.json()["data"]["profile"]


async def _clean(
    client: AsyncClient,
    dataset_id: int,
    session_id: str,
    operations: list[str],
    endpoint: str = "clean",
) -> Response:
    """Submit cleaning operations to an apply or preview endpoint."""
    return await client.post(
        f"/api/datasets/{dataset_id}/{endpoint}",
        headers={"X-Session-ID": session_id},
        json={"operations": operations, "dry_run": False},
    )


async def test_dry_run_does_not_modify_file(client: AsyncClient) -> None:
    """Verify preview reports changes without replacing the cached profile."""
    session_id = "cleaner-preview"
    dataset_id = await _upload_dirty_dataset(client, session_id)
    await _inspect(client, dataset_id, session_id)

    response = await _clean(
        client,
        dataset_id,
        session_id,
        ["remove_duplicates", "impute_numeric_median"],
        endpoint="clean/preview",
    )
    profile_response = await client.get(
        f"/api/datasets/{dataset_id}/profile",
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 200
    assert response.json()["data"]["dry_run"] is True
    assert profile_response.json()["data"]["profile"]["basic_info"][
        "row_count"
    ] == 8


async def test_remove_duplicates(client: AsyncClient) -> None:
    """Verify exact duplicate rows are removed and reported."""
    session_id = "cleaner-duplicates"
    dataset_id = await _upload_dirty_dataset(client, session_id)

    response = await _clean(
        client,
        dataset_id,
        session_id,
        ["remove_duplicates"],
    )

    assert response.status_code == 200
    assert response.json()["data"]["rows_removed"] == 1
    assert response.json()["data"]["changes"][0]["operation"] == (
        "remove_duplicates"
    )


async def test_impute_numeric_median(client: AsyncClient) -> None:
    """Verify numeric nulls are filled using rounded median values."""
    session_id = "cleaner-numeric-median"
    dataset_id = await _upload_dirty_dataset(client, session_id)
    await _inspect(client, dataset_id, session_id)

    response = await _clean(
        client,
        dataset_id,
        session_id,
        ["impute_numeric_median"],
    )
    change = next(
        item
        for item in response.json()["data"]["changes"]
        if item["operation"] == "impute_numeric_median"
    )

    assert response.status_code == 200
    assert change["rows_affected"] > 0


async def test_strip_whitespace(client: AsyncClient) -> None:
    """Verify whitespace is stripped and affected columns are identified."""
    session_id = "cleaner-whitespace"
    dataset_id = await _upload_dirty_dataset(client, session_id)

    response = await _clean(
        client,
        dataset_id,
        session_id,
        ["strip_whitespace"],
    )
    change = response.json()["data"]["changes"][0]

    assert response.status_code == 200
    assert change["operation"] == "strip_whitespace"
    assert change["affected_columns"]


async def test_standardize_column_names(client: AsyncClient) -> None:
    """Verify untidy headers are normalized and the mapping is reported."""
    session_id = "cleaner-column-names"
    dataset_id = await _upload_dirty_dataset(client, session_id)

    response = await _clean(
        client,
        dataset_id,
        session_id,
        ["standardize_column_names"],
    )

    assert response.status_code == 200
    assert "Renamed columns" in response.json()["data"]["changes"][0][
        "description"
    ]


async def test_cleaning_suggestions(client: AsyncClient) -> None:
    """Verify profiling issues produce explained cleaning recommendations."""
    session_id = "cleaner-suggestions"
    dataset_id = await _upload_dirty_dataset(client, session_id)
    await _inspect(client, dataset_id, session_id)

    response = await client.get(
        f"/api/datasets/{dataset_id}/cleaning-suggestions",
        headers={"X-Session-ID": session_id},
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert "remove_duplicates" in data["suggested_operations"]
    assert "impute_numeric_median" in data["suggested_operations"]
    assert set(data["suggested_operations"]) == set(data["reasons"])


async def test_invalid_operation(client: AsyncClient) -> None:
    """Verify unknown operation names are rejected during body validation."""
    response = await client.post(
        "/api/datasets/1/clean",
        headers={"X-Session-ID": "cleaner-invalid-operation"},
        json={"operations": ["not_a_real_operation"]},
    )

    assert response.status_code == 422


async def test_full_cleaning_pipeline(client: AsyncClient) -> None:
    """Verify the complete pipeline updates the file, profile, and model state."""
    session_id = "cleaner-full-pipeline"
    dataset_id = await _upload_dirty_dataset(client, session_id)
    await _inspect(client, dataset_id, session_id)

    response = await _clean(
        client,
        dataset_id,
        session_id,
        [operation.value for operation in CleaningOperation],
    )
    dataset_response = await client.get(
        f"/api/datasets/{dataset_id}",
        headers={"X-Session-ID": session_id},
    )
    profile_response = await client.get(
        f"/api/datasets/{dataset_id}/profile",
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 200
    assert response.json()["data"]["rows_removed"] >= 1
    assert dataset_response.json()["data"]["is_cleaned"] is True
    profile = profile_response.json()["data"]["profile"]
    assert profile["basic_info"]["row_count"] == 7
    assert "name" in [item["name"] for item in profile["column_profiles"]]
