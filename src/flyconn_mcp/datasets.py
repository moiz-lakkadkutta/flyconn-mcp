"""Dataset catalogue: flyconn's registry joined with what is cached on this machine."""

from __future__ import annotations

import json
from pathlib import Path

from flyconn.data.cache import cache_root, store_dir
from flyconn.data.registry import LEVELS, DatasetSpec, get_dataset, list_datasets
from pydantic import BaseModel, Field


class LevelSize(BaseModel):
    level: str = Field(description="Download level; each level includes all lower ones.")
    download_mb: float = Field(description="Total download size to reach this level, in MB.")


class DatasetInfo(BaseModel):
    ref: str = Field(description="Dataset reference to pass to other tools, name@version.")
    title: str
    license: str
    cached_level: str | None = Field(
        description="Highest level converted in the local cache, or null when not cached."
    )
    levels: list[LevelSize] = Field(description="Download size per available level.")
    citation: str = Field(description="Primary citation to credit when reporting results.")


class DatasetCatalogue(BaseModel):
    cache_root: str = Field(description="Local flyconn cache ($FLYCONN_CACHE).")
    datasets: list[DatasetInfo]
    note: str


def cached_level(spec: DatasetSpec) -> str | None:
    """Level recorded in the local store's provenance.json, or None if absent or unreadable."""
    prov = store_dir(spec) / "provenance.json"
    try:
        level = json.loads(prov.read_text()).get("level")
    except (OSError, ValueError):
        return None
    return level if level in LEVELS else None


def _levels(spec: DatasetSpec) -> list[LevelSize]:
    present = {f.level for f in spec.files}
    return [
        LevelSize(
            level=lvl,
            download_mb=round(sum(f.bytes for f in spec.files_for_level(lvl)) / 1e6, 1),
        )
        for lvl in LEVELS
        if lvl in present
    ]


def dataset_info(spec: DatasetSpec) -> DatasetInfo:
    return DatasetInfo(
        ref=spec.ref,
        title=spec.title,
        license=spec.license,
        cached_level=cached_level(spec),
        levels=_levels(spec),
        citation=spec.citations[0].text if spec.citations else "",
    )


def catalogue() -> DatasetCatalogue:
    return DatasetCatalogue(
        cache_root=str(Path(cache_root())),
        datasets=[dataset_info(get_dataset(ref)) for ref in list_datasets()],
        note=(
            "Datasets with cached_level=null must be pulled before querying. "
            "Downloads can be multi-GB; check download_mb and ask the user first."
        ),
    )
