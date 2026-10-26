"""list_datasets through a real MCP client session, against a temporary cache (offline)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from flyconn.data.cache import store_dir
from flyconn.data.registry import get_dataset
from mcp import Client

from flyconn_mcp.server import server

pytestmark = pytest.mark.anyio


def _fake_store(ref: str, level: str) -> None:
    root = store_dir(get_dataset(ref))
    root.mkdir(parents=True)
    (root / "provenance.json").write_text(json.dumps({"level": level}))


async def test_tool_is_listed_read_only() -> None:
    async with Client(server) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert "list_datasets" in tools
    ann = tools["list_datasets"].annotations
    assert ann is not None and ann.read_only_hint is True


async def test_empty_cache_marks_nothing_cached(cache: Path) -> None:
    async with Client(server) as client:
        result = await client.call_tool("list_datasets", {})
    assert not result.is_error
    data = result.structured_content
    assert data is not None
    assert data["cache_root"] == str(cache)
    by_ref = {d["ref"]: d for d in data["datasets"]}
    assert "malecns@1.0" in by_ref and "flywire@783" in by_ref
    assert all(d["cached_level"] is None for d in by_ref.values())


async def test_reports_cached_level_and_cumulative_sizes(cache: Path) -> None:
    _fake_store("malecns@1.0", "weights")
    async with Client(server) as client:
        result = await client.call_tool("list_datasets", {})
    data = result.structured_content
    assert data is not None
    malecns = next(d for d in data["datasets"] if d["ref"] == "malecns@1.0")
    assert malecns["cached_level"] == "weights"
    sizes = [lvl["download_mb"] for lvl in malecns["levels"]]
    assert sizes == sorted(sizes), "each level includes all lower ones"
    assert malecns["citation"]


async def test_corrupt_provenance_is_treated_as_not_cached(cache: Path) -> None:
    root = store_dir(get_dataset("flywire@783"))
    root.mkdir(parents=True)
    (root / "provenance.json").write_text("{not json")
    async with Client(server) as client:
        result = await client.call_tool("list_datasets", {})
    data = result.structured_content
    assert data is not None
    flywire = next(d for d in data["datasets"] if d["ref"] == "flywire@783")
    assert flywire["cached_level"] is None
