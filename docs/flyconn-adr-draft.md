# ADR-0013: Ship the MCP server as a separate package, `flyconn-mcp`, built on the official MCP SDK

Status: Accepted (2026-10-24, owner approved). Draft kept in flyconn-mcp until flyconn M14 lands;
copy to flyconn `docs/adr/` and add a row to its index.

## Context

LLM clients (Claude, Cursor, ChatGPT and others) reach tools through the Model Context
Protocol. A 2026-10-24 search found no MCP server that *runs* connectome experiments:
VirtualFlyBrain's `VFB3-MCP` only looks things up, and `navis-org/coda-mcp` (beta since
2026-08) only authors workflows. flyconn has 0 GitHub stars and about 320 PyPI downloads a
month; an MCP front end is its adoption vehicle. The MCP Python SDK moves fast: v2 (2.3.0 on
2026-10-24) renamed `FastMCP` to `MCPServer` and removed the v1 module.

## Decision

- A standalone repo and PyPI package, `flyconn-mcp`, that depends on `flyconn[sim]>=0.4,<0.5`
  and uses only flyconn's public API.
- Built on the official `mcp` SDK (`mcp>=2.3,<3`, `mcp.server.mcpserver.MCPServer`), stdio
  transport first. Not the third-party `fastmcp` package.
- flyconn's principles hold in every tool output: model-prediction and predicted-sign
  labelling, controls on by default, provenance, compact summaries with full artefacts on disk.

## Alternatives considered

- An `mcp` extra inside flyconn (`flyconn[mcp]`): rejected. It would tie flyconn's slow,
  validated release cycle to the SDK's fast one, and give the server no README, demo or stars
  of its own for discoverability. `uvx flyconn-mcp` is also a cleaner install line.
- The standalone `fastmcp` package: rejected for now; one more dependency with its own churn,
  and the official SDK already covers tools, resources, prompts and in-process test clients.
- Reuse an existing server (VFB3-MCP, coda-mcp): neither runs simulations or carries controls.

## Consequences

- Two packages to release; flyconn-mcp pins a minor range of flyconn and must be bumped with it.
- flyconn-mcp dogfoods flyconn's public API, so gaps it finds become flyconn issues.

## Evidence

`flyconn-mcp/PLAN.md` (research pass of 2026-10-24); PyPI metadata for `mcp` 2.3.0.
