"""find_paths: type-level paths between two cell types, with threshold and NT-sign stability.

flyconn's ``path_stability`` needs a ``ConnectivityMatrix``, and building one for all of
MaleCNS peaks at ~2.5 GB. Instead, SQL keeps only neurons within ``max_hops`` of both a
source and a target (every simple path of at most ``max_hops`` lies inside that set), and
the matrix is built on that subgraph. Input totals come from the full store, so per-hop
input fractions, and hence strengths, match a full-matrix run.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd
from flyconn.graph import ConnectivityMatrix
from flyconn.uncertainty.stability import path_stability
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from flyconn_mcp.provenance import Provenance, provenance
from flyconn_mcp.queries import UNTYPED, open_store, rows, text, unknown_type

MAX_HOPS = 4
MAX_SUBGRAPH_NEURONS = 20_000
N_SAMPLES = 100
THRESHOLD_FACTORS = (1, 2, 4)
SIGN_POLICY = f"sampled from per-neuron NT probabilities, {N_SAMPLES} draws (flyconn nt_model auto)"

_SUBGRAPH_SQL = """
WITH RECURSIVE
fwd(id, d) AS (
    SELECT neuron_id, 0 FROM neurons WHERE cell_type = ?
    UNION
    SELECT e.post, f.d + 1 FROM fwd f JOIN edges e ON e.pre = f.id
    WHERE f.d < ? AND e.weight >= ?
),
bwd(id, d) AS (
    SELECT neuron_id, 0 FROM neurons WHERE cell_type = ?
    UNION
    SELECT e.pre, b.d + 1 FROM bwd b JOIN edges e ON e.post = b.id
    WHERE b.d < ? AND e.weight >= ?
)
SELECT f.id
FROM (SELECT id, min(d) AS d FROM fwd GROUP BY id) f
JOIN (SELECT id, min(d) AS d FROM bwd GROUP BY id) b USING (id)
WHERE f.d + b.d <= ?
ORDER BY f.id
"""


class Endpoint(BaseModel):
    cell_type: str
    n_neurons: int


class TypePath(BaseModel):
    types: list[str] = Field(description="Cell types along the path, source first.")
    hops: int
    n_paths: int = Field(description="Neuron-level paths with this type sequence.")
    strength: float = Field(
        description="Sum over neuron paths of the product of per-hop input fractions."
    )
    modal_sign: int = Field(description="+1 net excitatory, -1 net inhibitory, 0 unknown.")
    sign_stability: float = Field(description="Mean share of NT samples giving the modal sign.")
    threshold_presence: float = Field(
        description="Mean share of synapse thresholds at which the paths exist."
    )


class PathSearch(BaseModel):
    source: Endpoint
    target: Endpoint
    n_paths: int = Field(description="Neuron-level paths found at the base threshold or above.")
    n_type_paths: int
    type_paths: list[TypePath] = Field(description="Strongest type-level paths.")
    note: str
    provenance: Provenance


def _type_ids(store: Any, cell_type: str) -> list[int]:
    found = rows(store, "SELECT neuron_id FROM neurons WHERE cell_type = ? ORDER BY 1", [cell_type])
    if not found:
        raise unknown_type(store, cell_type)
    return [int(r["neuron_id"]) for r in found]


def _subgraph_neurons(store: Any, keep: list[int], min_weight: int) -> pd.DataFrame:
    neurons = store.query(
        "SELECT * FROM neurons WHERE neuron_id IN (SELECT unnest(?::BIGINT[]))", [keep]
    )
    has_totals = "input_synapses_total" in neurons.columns and not rows(
        store, "SELECT 1 FROM neurons WHERE input_synapses_total IS NULL LIMIT 1", []
    )
    if not has_totals:
        # Same fallback as flyconn's full matrix: column sums at the matrix threshold.
        totals = store.query(
            "SELECT post AS neuron_id, sum(weight) AS total FROM edges "
            "WHERE weight >= ? AND post IN (SELECT unnest(?::BIGINT[])) GROUP BY post",
            [min_weight, keep],
        )
        by_id = dict(zip(totals["neuron_id"], totals["total"], strict=True))
        neurons["input_synapses_total"] = [float(by_id.get(i, 0)) for i in neurons["neuron_id"]]
    return neurons


def _summarize(paths: pd.DataFrame, top_n: int) -> tuple[int, list[TypePath]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for r in paths.to_dict("records"):
        labels = tuple(text(v) or UNTYPED for v in r["labels"])
        groups[labels].append({str(k): v for k, v in r.items()})
    summaries: list[TypePath] = []
    for labels, members in groups.items():
        strength = sum(float(m["strength_mean"]) for m in members)
        by_sign: dict[int, float] = defaultdict(float)
        for m in members:
            by_sign[int(m["modal_sign"])] += float(m["strength_mean"])
        summaries.append(
            TypePath(
                types=list(labels),
                hops=int(members[0]["hops"]),
                n_paths=len(members),
                strength=round(strength, 6),
                modal_sign=max(by_sign, key=lambda s: by_sign[s]),
                sign_stability=round(
                    sum(float(m["sign_stability"]) for m in members) / len(members), 4
                ),
                threshold_presence=round(
                    sum(float(m["threshold_presence"]) for m in members) / len(members), 4
                ),
            )
        )
    summaries.sort(key=lambda t: (-t.strength, t.types))
    return len(summaries), summaries[:top_n]


def find_paths(
    dataset: str,
    source_type: str,
    target_type: str,
    max_hops: int,
    min_weight: int,
    top_n: int,
    seed: int,
) -> PathSearch:
    store = open_store(dataset)
    try:
        sources = _type_ids(store, source_type)
        targets = _type_ids(store, target_type)
        thresholds = [min_weight * f for f in THRESHOLD_FACTORS]
        keep = [
            int(r["id"])
            for r in rows(
                store,
                _SUBGRAPH_SQL,
                [source_type, max_hops, min_weight, target_type, max_hops, min_weight, max_hops],
            )
        ]
        if len(keep) > MAX_SUBGRAPH_NEURONS:
            msg = (
                f"{len(keep):,} neurons lie on paths of <= {max_hops} hops at "
                f"min_weight={min_weight}, over the limit of {MAX_SUBGRAPH_NEURONS:,}. "
                "Raise min_weight or lower max_hops and try again."
            )
            raise ToolError(msg)
        kept = set(keep)
        src = [i for i in sources if i in kept]
        tgt = [i for i in targets if i in kept]
        prov = provenance(
            store,
            source_type=source_type,
            target_type=target_type,
            max_hops=max_hops,
            min_weight=min_weight,
            thresholds=thresholds,
            n_samples=N_SAMPLES,
            seed=seed,
            subgraph_neurons=len(keep),
            top_n=top_n,
        )
        prov.min_weight = min_weight
        prov.sign_policy = SIGN_POLICY
        n_paths, n_type_paths, type_paths = 0, 0, []
        if src and tgt:
            m = ConnectivityMatrix.from_frames(
                _subgraph_neurons(store, keep, min_weight),
                store.edges(min_weight=min_weight, pre=keep, post=keep),
                min_weight=min_weight,
                provenance={"dataset": store.ref, "subgraph_neurons": len(keep)},
            )
            result = path_stability(
                m,
                src,
                tgt,
                max_hops=max_hops,
                n_samples=N_SAMPLES,
                seed=seed,
                thresholds=thresholds,
                label="cell_type",
            )
            n_paths = len(result.paths)
            n_type_paths, type_paths = _summarize(result.paths, top_n)
        if n_paths:
            note = (
                "strength: product of per-hop input fractions, summed over neuron paths. "
                "Signs come from predicted neurotransmitters; sign_stability is the share of "
                f"{N_SAMPLES} NT samples that give the modal sign. threshold_presence is the "
                f"share of thresholds {thresholds} at which the paths exist."
            )
        else:
            note = (
                f"No paths of <= {max_hops} hops at min_weight={min_weight}. Try a larger "
                f"max_hops (up to {MAX_HOPS}) or a lower min_weight."
            )
        return PathSearch(
            source=Endpoint(cell_type=source_type, n_neurons=len(sources)),
            target=Endpoint(cell_type=target_type, n_neurons=len(targets)),
            n_paths=n_paths,
            n_type_paths=n_type_paths,
            type_paths=type_paths,
            note=note,
            provenance=prov,
        )
    finally:
        store.close()
