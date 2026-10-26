"""Shared fixtures: an isolated flyconn cache holding a small synthetic store (offline)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from flyconn.data.cache import store_dir
from flyconn.data.convert.common import write_parquet, write_provenance
from flyconn.data.registry import get_dataset
from flyconn.data.schema import conform_edges, conform_neurons
from flyconn.testing import synthetic_connectome


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("FLYCONN_CACHE", str(tmp_path))
    return tmp_path


def write_store(neurons: pd.DataFrame, edges: pd.DataFrame, ref: str = "malecns@1.0") -> Path:
    spec = get_dataset(ref)
    neurons = neurons.assign(dataset=spec.name, version=spec.version)
    edges = edges.assign(dataset=spec.name, version=spec.version)
    root = store_dir(spec)
    root.mkdir(parents=True)
    write_parquet(conform_neurons(neurons), root / "neurons.parquet")
    write_parquet(conform_edges(edges), root / "edges.parquet")
    write_provenance(
        root,
        dataset=spec.name,
        version=spec.version,
        converter="test",
        inputs=[],
        counts={"neurons": len(neurons), "edges": len(edges)},
        level="weights",
    )
    return root


# Hand-placed types on top of the random background (positions 0-5):
#   SRC x2 (ACh) -> TGT  10 + 6 synapses     INH (GABA) -> TGT  8 synapses
#   WEAK (ACh)   -> TGT  2 synapses (below the default threshold of 5)
#   TGT (ACh)    -> OUT  7 synapses
KNOWN_TYPES = {
    0: ("SRC", "sensory", "acetylcholine"),
    1: ("SRC", "sensory", "acetylcholine"),
    2: ("INH", "central_brain_intrinsic", "gaba"),
    3: ("TGT", "motor", "acetylcholine"),
    4: ("OUT", "motor", "glutamate"),
    5: ("WEAK", "sensory", "acetylcholine"),
}
KNOWN_EDGES = [(0, 3, 10), (1, 3, 6), (2, 3, 8), (5, 3, 2), (3, 4, 7)]


@pytest.fixture
def store(cache: Path) -> Path:
    neurons, edges = synthetic_connectome(n_neurons=40, n_edges=200, seed=21)
    ids = neurons["neuron_id"].to_numpy()
    for pos, (cell_type, super_class, nt) in KNOWN_TYPES.items():
        neurons.loc[pos, ["cell_type", "super_class", "nt_pred"]] = [cell_type, super_class, nt]
    known_ids = set(ids[list(KNOWN_TYPES)])
    background = edges[~edges["pre"].isin(known_ids) & ~edges["post"].isin(known_ids)]
    placed = pd.DataFrame(
        {
            "pre": [ids[a] for a, _, _ in KNOWN_EDGES],
            "post": [ids[b] for _, b, _ in KNOWN_EDGES],
            "weight": [w for _, _, w in KNOWN_EDGES],
        }
    )
    return write_store(neurons, pd.concat([background, placed], ignore_index=True))
