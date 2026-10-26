"""Golden checks on cached malecns@1.0 (read-only). Run with `uv run pytest -m golden`."""

from __future__ import annotations

import pytest
from flyconn.data.registry import get_dataset
from flyconn.data.store import Store
from flyconn.graph import ConnectivityMatrix
from flyconn.uncertainty.stability import path_stability

from flyconn_mcp import paths, queries
from flyconn_mcp.datasets import cached_level

REF = "malecns@1.0"
pytestmark = [
    pytest.mark.golden,
    pytest.mark.skipif(cached_level(get_dataset(REF)) is None, reason=f"{REF} not cached"),
]


def test_gng232_partners_match_readme() -> None:
    out = queries.neuron_partners(REF, "GNG232", "both", 5, 5)
    assert out.upstream is not None and out.downstream is not None
    assert out.upstream.total_synapses == 2295
    assert [(p.cell_type, p.synapses) for p in out.upstream.partners[:2]] == [
        ("LB3c", 481),
        ("LB3d", 452),
    ]
    assert out.downstream.partners[0].cell_type == "GNG041"
    assert out.downstream.partners[0].synapses == 403


def test_mn9_upstream_matches_readme() -> None:
    out = queries.neuron_partners(REF, "MN9", "upstream", 5, 5)
    assert out.upstream is not None
    assert out.upstream.total_synapses == 6085
    assert out.upstream.n_partner_types == 74
    assert out.upstream.partners[0].cell_type == "DNge062"


def test_subgraph_paths_equal_full_matrix_paths() -> None:
    """The SQL-pruned subgraph finds exactly the paths and strengths of the full matrix.

    Builds the full MaleCNS matrix once (~2.5 GB peak).
    """
    store = Store.open(REF)
    ids = {
        ct: store.query("SELECT neuron_id FROM neurons WHERE cell_type = ?", [ct])[
            "neuron_id"
        ].tolist()
        for ct in ("GNG232", "MN9")
    }
    full = ConnectivityMatrix.from_store(store, min_weight=5)
    ref = path_stability(
        full, ids["GNG232"], ids["MN9"], max_hops=3, thresholds=[5, 10, 20], label="cell_type"
    ).paths
    store.close()

    out = paths.find_paths(REF, "GNG232", "MN9", 3, 5, 1000, 0)
    assert out.n_paths == len(ref) == 1401

    by_types: dict[tuple[str, ...], float] = {}
    for labels, strength in zip(ref["labels"], ref["strength_mean"], strict=True):
        key = tuple(str(x) for x in labels)
        by_types[key] = by_types.get(key, 0.0) + float(strength)
    assert out.n_type_paths == len(by_types)
    for tp in out.type_paths:
        assert tp.strength == pytest.approx(by_types[tuple(tp.types)], rel=1e-4, abs=1e-6)
