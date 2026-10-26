"""Provenance attached to every query result."""

from __future__ import annotations

from typing import Any

import flyconn
from flyconn.data.store import Store
from pydantic import BaseModel, Field

from flyconn_mcp import __version__


class Provenance(BaseModel):
    dataset: str = Field(description="Dataset reference queried, name@version.")
    store_converter: str = Field(description="flyconn converter that built the local store.")
    store_created_utc: str = Field(description="When the local store was converted.")
    store_flyconn_version: str = Field(description="flyconn version that converted the store.")
    flyconn_version: str = Field(description="flyconn version answering this query.")
    flyconn_mcp_version: str
    params: dict[str, Any] = Field(description="Query parameters, including thresholds.")
    min_weight: int | None = Field(
        default=None, description="Minimum synapses per neuron pair for an edge to count."
    )
    sign_policy: str | None = None


def provenance(store: Store, **params: Any) -> Provenance:
    prov = store.provenance
    converter = str(prov.get("converter", ""))
    if prov.get("converter_version"):
        converter += f" v{prov['converter_version']}"
    return Provenance(
        dataset=store.ref,
        store_converter=converter,
        store_created_utc=str(prov.get("created_utc", "")),
        store_flyconn_version=str(prov.get("flyconn_version", "")),
        flyconn_version=flyconn.__version__,
        flyconn_mcp_version=__version__,
        params=params,
    )
