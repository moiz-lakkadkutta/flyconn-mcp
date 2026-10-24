"""The flyconn MCP server and its tools."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from flyconn_mcp import __version__
from flyconn_mcp.datasets import DatasetCatalogue, catalogue

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


def main() -> None:
    """Console entry point: serve over stdio."""
    server.run()


if __name__ == "__main__":
    main()
