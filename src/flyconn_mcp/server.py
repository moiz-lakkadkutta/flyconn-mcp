"""The flyconn MCP server and its tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from flyconn_mcp import __version__, paths, queries
from flyconn_mcp.datasets import DatasetCatalogue, catalogue
from flyconn_mcp.paths import PathSearch
from flyconn_mcp.queries import Direction, NeuronSearch, Partners

INSTRUCTIONS = """\
flyconn queries public Drosophila connectomes (MaleCNS, FlyWire, BANC, ...) offline and runs
in-silico experiments on them. Wiring is measured; neurotransmitter signs are predicted;
simulation outputs are model predictions. Report results with their controls and provenance,
and never download a dataset without telling the user its size first.
"""

server = MCPServer(
    name="flyconn",
    title="flyconn: Drosophila connectome experiments",
    instructions=INSTRUCTIONS,
    website_url="https://github.com/moiz-lakkadkutta/flyconn-mcp",
    version=__version__,
)


@server.tool(
    annotations=ToolAnnotations(
        title="List connectome datasets",
        read_only_hint=True,
        open_world_hint=False,
    )
)
def list_datasets() -> DatasetCatalogue:
    """List the connectome datasets flyconn knows, with licence, citation, download size per
    level, and which level (if any) is already cached on this machine."""
    return catalogue()


_QUERY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
DEFAULT_DATASET = "malecns@1.0"


@server.tool(annotations=_QUERY)
def find_neurons(
    cell_type: Annotated[
        str | None,
        Field(description="Case-insensitive glob on cell type, e.g. 'GNG23*' or 'MN9'."),
    ] = None,
    super_class: Annotated[
        str | None, Field(description="Exact super class, e.g. 'sensory', 'motor'.")
    ] = None,
    dataset: Annotated[str, Field(description="Dataset ref from list_datasets.")] = (
        DEFAULT_DATASET
    ),
    top_n: Annotated[int, Field(ge=1, le=200)] = 20,
) -> NeuronSearch:
    """Search neurons by cell type pattern and/or super class. Returns the match count,
    counts per super class, and the largest matching cell types with their predicted NT."""
    return queries.find_neurons(dataset, cell_type, super_class, top_n)


@server.tool(annotations=_QUERY)
def neuron_partners(
    cell_type: Annotated[str, Field(description="Exact cell type, e.g. 'MN9'.")],
    direction: Annotated[
        Direction, Field(description="upstream (inputs), downstream (outputs), or both.")
    ] = "both",
    min_weight: Annotated[
        int, Field(ge=1, description="Minimum synapses per neuron pair to count an edge.")
    ] = 5,
    dataset: Annotated[str, Field(description="Dataset ref from list_datasets.")] = (
        DEFAULT_DATASET
    ),
    top_n: Annotated[int, Field(ge=1, le=100)] = 10,
) -> Partners:
    """Top upstream and/or downstream partner cell types of a cell type, with synapse counts,
    share of input/output, and signed synapse counts from predicted neurotransmitters."""
    return queries.neuron_partners(dataset, cell_type, direction, min_weight, top_n)


@server.tool(annotations=_QUERY)
def find_paths(
    source_type: Annotated[str, Field(description="Exact source cell type, e.g. 'LB3c'.")],
    target_type: Annotated[str, Field(description="Exact target cell type, e.g. 'MN9'.")],
    max_hops: Annotated[int, Field(ge=1, le=paths.MAX_HOPS)] = 3,
    min_weight: Annotated[
        int, Field(ge=1, description="Base threshold; stability also checks 2x and 4x.")
    ] = 5,
    dataset: Annotated[str, Field(description="Dataset ref from list_datasets.")] = (
        DEFAULT_DATASET
    ),
    top_n: Annotated[int, Field(ge=1, le=50)] = 10,
    seed: Annotated[int, Field(description="Seed for NT-sign sampling.")] = 0,
) -> PathSearch:
    """Paths from one cell type to another, summarized by cell-type sequence: strength,
    net sign from predicted neurotransmitters, and how stable each path is across synapse
    thresholds and NT-sign samples."""
    return paths.find_paths(dataset, source_type, target_type, max_hops, min_weight, top_n, seed)


def main() -> None:
    """Console entry point: serve over stdio."""
    server.run()


if __name__ == "__main__":
    main()
