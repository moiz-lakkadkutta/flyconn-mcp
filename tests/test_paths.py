"""find_paths through a real MCP client session (offline), on the hand-placed fixture types.

Fixture wiring (tests/conftest.py): SRC x2 (ACh) -> TGT (10, 6), INH (GABA) -> TGT (8),
WEAK -> TGT (2), TGT (ACh) -> OUT (7). The store has no input_synapses_total, so input
totals are column sums at min_weight: TGT 24, OUT 7.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from flyconn_mcp import paths
from flyconn_mcp.server import server

pytestmark = pytest.mark.anyio


async def call(args: dict[str, Any]) -> dict[str, Any]:
    async with Client(server) as client:
        result = await client.call_tool("find_paths", args)
    assert not result.is_error, result.content
    assert result.structured_content is not None
    return result.structured_content


async def test_two_hop_type_path_with_strength_and_stability(store: Path) -> None:
    out = await call({"source_type": "SRC", "target_type": "OUT"})
    assert out["source"] == {"cell_type": "SRC", "n_neurons": 2}
    assert out["target"] == {"cell_type": "OUT", "n_neurons": 1}
    assert out["n_paths"] == 2
    (top,) = out["type_paths"]
    assert top["types"] == ["SRC", "TGT", "OUT"]
    assert top["hops"] == 2
    assert top["n_paths"] == 2
    assert top["strength"] == pytest.approx(10 / 24 + 6 / 24, abs=1e-4)
    assert top["modal_sign"] == 1
    assert top["sign_stability"] == pytest.approx(1.0)
    # Thresholds 5, 10, 20: TGT -> OUT (7 synapses) only survives the first.
    assert top["threshold_presence"] == pytest.approx(1 / 3, abs=1e-3)
    prov = out["provenance"]
    assert prov["dataset"] == "malecns@1.0" and prov["min_weight"] == 5
    assert prov["params"]["thresholds"] == [5, 10, 20]
    assert prov["params"]["seed"] == 0


async def test_inhibitory_path_has_negative_sign(store: Path) -> None:
    out = await call({"source_type": "INH", "target_type": "OUT"})
    (top,) = out["type_paths"]
    assert top["types"] == ["INH", "TGT", "OUT"]
    assert top["modal_sign"] == -1


async def test_max_hops_limits_paths(store: Path) -> None:
    out = await call({"source_type": "SRC", "target_type": "OUT", "max_hops": 1})
    assert out["n_paths"] == 0
    assert out["type_paths"] == []
    assert "max_hops" in out["note"]


async def test_min_weight_admits_weak_edge(store: Path) -> None:
    strict = await call({"source_type": "WEAK", "target_type": "OUT"})
    loose = await call({"source_type": "WEAK", "target_type": "OUT", "min_weight": 1})
    assert strict["n_paths"] == 0
    assert loose["n_paths"] == 1
    assert loose["type_paths"][0]["types"] == ["WEAK", "TGT", "OUT"]


async def test_unknown_type_is_a_tool_error(store: Path) -> None:
    async with Client(server) as client:
        result = await client.call_tool("find_paths", {"source_type": "SRC", "target_type": "nope"})
    assert result.is_error
    text = " ".join(getattr(c, "text", "") for c in result.content)
    assert "find_neurons" in text


async def test_oversized_subgraph_is_refused(store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "MAX_SUBGRAPH_NEURONS", 2)
    async with Client(server) as client:
        result = await client.call_tool("find_paths", {"source_type": "SRC", "target_type": "OUT"})
    assert result.is_error
    text = " ".join(getattr(c, "text", "") for c in result.content)
    assert "min_weight" in text and "max_hops" in text
