"""find_neurons and neuron_partners through a real MCP client session (offline)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from flyconn.data.store import Store
from mcp import Client

from flyconn_mcp.server import server

pytestmark = pytest.mark.anyio


async def call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    async with Client(server) as client:
        result = await client.call_tool(tool, args)
    assert not result.is_error, result.content
    assert result.structured_content is not None
    return result.structured_content


async def call_error(tool: str, args: dict[str, Any]) -> str:
    async with Client(server) as client:
        result = await client.call_tool(tool, args)
    assert result.is_error
    return " ".join(getattr(c, "text", "") for c in result.content)


def assert_provenance(prov: dict[str, Any]) -> None:
    assert prov["dataset"] == "malecns@1.0"
    assert prov["flyconn_version"] and prov["flyconn_mcp_version"]
    assert prov["store_converter"] == "test"


# --- find_neurons ---------------------------------------------------------------------------


async def test_find_neurons_exact_type(store: Path) -> None:
    out = await call("find_neurons", {"cell_type": "SRC"})
    assert out["n_neurons"] == 2
    assert out["by_super_class"] == {"sensory": 2}
    assert out["top_types"][0] == {
        "cell_type": "SRC",
        "n_neurons": 2,
        "super_class": "sensory",
        "nt_pred": "acetylcholine",
    }
    assert_provenance(out["provenance"])


async def test_find_neurons_glob_is_case_insensitive(store: Path) -> None:
    out = await call("find_neurons", {"cell_type": "t0*"})
    expected = Store(store).query("SELECT count(*) AS n FROM neurons WHERE cell_type LIKE 'T0%'")[
        "n"
    ][0]
    assert out["n_neurons"] == expected > 0
    assert all(t["cell_type"].startswith("T0") for t in out["top_types"])


async def test_find_neurons_super_class_and_top_n(store: Path) -> None:
    out = await call("find_neurons", {"super_class": "sensory", "top_n": 2})
    assert set(out["by_super_class"]) == {"sensory"}
    assert len(out["top_types"]) <= 2
    assert out["n_types"] >= len(out["top_types"])
    counts = [t["n_neurons"] for t in out["top_types"]]
    assert counts == sorted(counts, reverse=True)


async def test_find_neurons_no_match_explains_next_step(store: Path) -> None:
    out = await call("find_neurons", {"cell_type": "NOPE*"})
    assert out["n_neurons"] == 0
    assert "super_class" in out["note"] and "sensory" in out["note"]


async def test_uncached_dataset_says_how_to_pull(store: Path) -> None:
    msg = await call_error("find_neurons", {"dataset": "flywire@783", "cell_type": "MN9"})
    assert "flyconn data pull flywire@783" in msg and "MB" in msg


# --- neuron_partners ------------------------------------------------------------------------


async def test_upstream_partners_are_signed_and_thresholded(store: Path) -> None:
    out = await call("neuron_partners", {"cell_type": "TGT", "direction": "upstream"})
    up = out["upstream"]
    assert out["downstream"] is None
    assert out["query"] == {"cell_type": "TGT", "n_neurons": 1, "nt_pred": "acetylcholine"}
    assert up["total_synapses"] == 24  # WEAK (2 synapses) is under min_weight=5
    by_type = {p["cell_type"]: p for p in up["partners"]}
    assert set(by_type) == {"SRC", "INH"}
    assert by_type["SRC"] == {
        "cell_type": "SRC",
        "n_neurons": 2,
        "synapses": 16,
        "fraction": pytest.approx(16 / 24, abs=1e-3),
        "signed_synapses": 16,
        "nt_pred": "acetylcholine",
    }
    assert by_type["INH"]["signed_synapses"] == -8
    assert [p["cell_type"] for p in up["partners"]] == ["SRC", "INH"]
    assert out["provenance"]["min_weight"] == 5
    assert "argmax" in out["provenance"]["sign_policy"]


async def test_min_weight_changes_the_partner_set(store: Path) -> None:
    out = await call(
        "neuron_partners", {"cell_type": "TGT", "direction": "upstream", "min_weight": 1}
    )
    by_type = {p["cell_type"]: p for p in out["upstream"]["partners"]}
    assert by_type["WEAK"]["synapses"] == 2
    assert out["upstream"]["total_synapses"] == 26


async def test_downstream_sign_comes_from_the_query_type(store: Path) -> None:
    out = await call("neuron_partners", {"cell_type": "TGT", "direction": "downstream"})
    assert out["upstream"] is None
    (only,) = out["downstream"]["partners"]
    # OUT is glutamatergic, but the TGT -> OUT connection is signed by TGT (ACh): positive.
    assert only["cell_type"] == "OUT" and only["signed_synapses"] == 7
    assert only["nt_pred"] == "glutamate"


async def test_both_directions_by_default(store: Path) -> None:
    out = await call("neuron_partners", {"cell_type": "TGT"})
    assert out["upstream"] is not None and out["downstream"] is not None
    assert "predicted" in out["note"]
    assert_provenance(out["provenance"])


async def test_unknown_type_suggests_close_matches(store: Path) -> None:
    msg = await call_error("neuron_partners", {"cell_type": "tgt"})
    assert "TGT" in msg and "find_neurons" in msg
