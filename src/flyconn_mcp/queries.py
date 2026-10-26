"""Read-only connectome queries, answered with DuckDB over the local flyconn store.

Queries aggregate in SQL rather than building a ``ConnectivityMatrix``: MaleCNS has 25.6M
edges, and loading them all for one cell type's partners would cost GBs of RAM.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Literal

from flyconn.data.cache import store_dir
from flyconn.data.registry import get_dataset
from flyconn.data.store import Store
from flyconn.graph.signs import sign_table
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from flyconn_mcp.datasets import cached_level, dataset_info
from flyconn_mcp.provenance import Provenance, provenance

Direction = Literal["upstream", "downstream", "both"]
UNTYPED = "(untyped)"
SIGN_POLICY = "argmax: sign of each presynaptic neuron's predicted NT (flyconn ADR-0007)"
NT_NOTE = (
    "Wiring is measured; neurotransmitters, and so signs, are predicted. "
    "signed_synapses = synapses x presynaptic sign (+1 excitatory, -1 inhibitory, 0 unknown)."
)


def open_store(ref: str) -> Store:
    """Open a cached store, or raise a ToolError telling the caller how to get it."""
    try:
        spec = get_dataset(ref)
    except (KeyError, ValueError) as exc:
        raise ToolError(f"{exc}. Call list_datasets to see valid references.") from None
    if cached_level(spec) is None:
        sizes = {lvl.level: lvl.download_mb for lvl in dataset_info(spec).levels}
        level = "weights" if "weights" in sizes else next(iter(sizes))
        msg = (
            f"{ref} is not cached in {store_dir(spec)}. Ask the user before downloading; "
            f"they can run `flyconn data pull {ref} --level {level}` ({sizes[level]:,.0f} MB)."
        )
        raise ToolError(msg)
    return Store.open(ref)


def glob_to_like(pattern: str) -> str:
    escaped = pattern.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return escaped.replace("*", "%").replace("?", "_")


def rows(store: Store, sql: str, params: Sequence[Any]) -> list[dict[str, Any]]:
    return [{str(k): v for k, v in r.items()} for r in store.query(sql, params).to_dict("records")]


def text(v: Any) -> str | None:
    """A text cell as str, with SQL NULL / pandas NaN as None."""
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)


def unknown_type(store: Store, cell_type: str) -> ToolError:
    """A ToolError for a cell type with no neurons, naming close matches."""
    close = [
        str(r["cell_type"])
        for r in rows(
            store,
            "SELECT DISTINCT cell_type FROM neurons WHERE cell_type ILIKE ? ORDER BY 1 LIMIT 10",
            [f"%{glob_to_like(cell_type)}%"],
        )
    ]
    hint = f" Close matches: {', '.join(close)}." if close else ""
    return ToolError(
        f"No neurons of cell_type {cell_type!r} in {store.ref} (exact, case-sensitive)."
        f"{hint} Use find_neurons to search by pattern."
    )


def _sign_sql(column: str) -> str:
    cases = " ".join(f"WHEN '{nt}' THEN {s}" for nt, s in sign_table().items())
    return f"(CASE {column} {cases} ELSE 0 END)"


# --- find_neurons ---------------------------------------------------------------------------


class TypeCount(BaseModel):
    cell_type: str
    n_neurons: int
    super_class: str | None = Field(description="Most common super_class of this type.")
    nt_pred: str | None = Field(description="Most common predicted neurotransmitter.")


class NeuronSearch(BaseModel):
    n_neurons: int
    n_types: int = Field(description="Distinct cell types among the matches.")
    by_super_class: dict[str, int]
    top_types: list[TypeCount] = Field(description="Largest matching types, by neuron count.")
    note: str
    provenance: Provenance


def find_neurons(
    dataset: str, cell_type: str | None, super_class: str | None, top_n: int
) -> NeuronSearch:
    store = open_store(dataset)
    try:
        clauses: list[str] = []
        params: list[object] = []
        if cell_type:
            clauses.append("cell_type ILIKE ? ESCAPE '\\'")
            params.append(glob_to_like(cell_type))
        if super_class:
            clauses.append("super_class = ?")
            params.append(super_class)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        by_class = rows(
            store,
            f"SELECT coalesce(super_class, 'unknown') AS sc, count(*) AS n FROM neurons {where} "
            "GROUP BY 1 ORDER BY n DESC, sc",
            params,
        )
        types = rows(
            store,
            f"SELECT coalesce(cell_type, '{UNTYPED}') AS cell_type, count(*) AS n, "
            "mode(super_class) AS super_class, mode(nt_pred) AS nt_pred "
            f"FROM neurons {where} GROUP BY 1 ORDER BY n DESC, cell_type",
            params,
        )
        n = sum(int(r["n"]) for r in by_class)
        if n:
            note = "cell_type matching is a case-insensitive glob (* and ?)."
        else:
            known = rows(store, "SELECT DISTINCT super_class AS sc FROM neurons ORDER BY 1", [])
            names = ", ".join(s for r in known if (s := text(r["sc"])))
            note = (
                "No neurons matched. cell_type is a case-insensitive glob such as 'GNG23*'; "
                f"super_class must be exact, one of: {names}."
            )
        return NeuronSearch(
            n_neurons=n,
            n_types=len(types),
            by_super_class={str(r["sc"]): int(r["n"]) for r in by_class},
            top_types=[
                TypeCount(
                    cell_type=str(r["cell_type"]),
                    n_neurons=int(r["n"]),
                    super_class=text(r["super_class"]),
                    nt_pred=text(r["nt_pred"]),
                )
                for r in types[:top_n]
            ],
            note=note,
            provenance=provenance(store, cell_type=cell_type, super_class=super_class, top_n=top_n),
        )
    finally:
        store.close()


# --- neuron_partners ------------------------------------------------------------------------


class Partner(BaseModel):
    cell_type: str
    n_neurons: int = Field(description="Partner neurons of this type connected at threshold.")
    synapses: int
    fraction: float = Field(description="Share of the query type's thresholded input/output.")
    signed_synapses: int = Field(description="Synapses x presynaptic sign (predicted).")
    nt_pred: str | None = Field(description="The partner type's most common predicted NT.")


class PartnerSet(BaseModel):
    total_synapses: int
    n_partner_types: int
    partners: list[Partner] = Field(description="Top partner types by synapse count.")


class QueryType(BaseModel):
    cell_type: str
    n_neurons: int
    nt_pred: str | None


class Partners(BaseModel):
    query: QueryType
    upstream: PartnerSet | None = Field(description="Inputs to the query type, or null.")
    downstream: PartnerSet | None = Field(description="Outputs of the query type, or null.")
    note: str
    provenance: Provenance


def _partner_set(
    store: Store, cell_type: str, upstream: bool, min_weight: int, top_n: int
) -> PartnerSet:
    # Upstream: partners are presynaptic, so the partner's NT signs the edge.
    # Downstream: the query type is presynaptic, so its NT signs the edge.
    q_side, p_side = ("post", "pre") if upstream else ("pre", "post")
    signer = "p" if upstream else "q"
    found = rows(
        store,
        f"SELECT coalesce(p.cell_type, '{UNTYPED}') AS cell_type, "
        f"count(DISTINCT e.{p_side}) AS n, sum(e.weight) AS w, "
        f"sum(e.weight * {_sign_sql(f'{signer}.nt_pred')}) AS sw, "
        "mode(p.nt_pred) AS nt "
        f"FROM edges e JOIN neurons q ON e.{q_side} = q.neuron_id "
        f"JOIN neurons p ON e.{p_side} = p.neuron_id "
        "WHERE q.cell_type = ? AND e.weight >= ? GROUP BY 1 ORDER BY w DESC, cell_type",
        [cell_type, min_weight],
    )
    total = sum(int(r["w"]) for r in found)
    return PartnerSet(
        total_synapses=total,
        n_partner_types=len(found),
        partners=[
            Partner(
                cell_type=str(r["cell_type"]),
                n_neurons=int(r["n"]),
                synapses=int(r["w"]),
                fraction=round(int(r["w"]) / total, 4),
                signed_synapses=int(r["sw"]),
                nt_pred=text(r["nt"]),
            )
            for r in found[:top_n]
        ],
    )


def neuron_partners(
    dataset: str, cell_type: str, direction: Direction, min_weight: int, top_n: int
) -> Partners:
    store = open_store(dataset)
    try:
        (q,) = rows(
            store,
            "SELECT count(*) AS n, mode(nt_pred) AS nt FROM neurons WHERE cell_type = ?",
            [cell_type],
        )
        n = int(q["n"])
        if n == 0:
            raise unknown_type(store, cell_type)
        prov = provenance(
            store, cell_type=cell_type, direction=direction, min_weight=min_weight, top_n=top_n
        )
        prov.min_weight = min_weight
        prov.sign_policy = SIGN_POLICY
        return Partners(
            query=QueryType(cell_type=cell_type, n_neurons=n, nt_pred=text(q["nt"])),
            upstream=(
                _partner_set(store, cell_type, True, min_weight, top_n)
                if direction in ("upstream", "both")
                else None
            ),
            downstream=(
                _partner_set(store, cell_type, False, min_weight, top_n)
                if direction in ("downstream", "both")
                else None
            ),
            note=NT_NOTE,
            provenance=prov,
        )
    finally:
        store.close()
