"""MCP server for in-silico experiments on public Drosophila connectomes via flyconn."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("flyconn-mcp")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0"

__all__ = ["__version__"]
