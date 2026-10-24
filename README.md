# flyconn-mcp

An MCP server that lets Claude, Cursor or any MCP client query public *Drosophila* connectomes
and run in-silico experiments on them through [flyconn](https://github.com/moiz-lakkadkutta/flyconn).
It runs locally. Every answer carries flyconn's controls, uncertainty and provenance.

> Status: pre-alpha (M0 scaffold). Only `list_datasets` exists so far; see `PLAN.md`.

## Install (from source, for now)

```sh
git clone https://github.com/moiz-lakkadkutta/flyconn-mcp && cd flyconn-mcp
uv sync
claude mcp add flyconn -- uv --directory "$PWD" run flyconn-mcp
```

Once released on PyPI: `claude mcp add flyconn -- uvx flyconn-mcp`.

Data lives in flyconn's cache (`$FLYCONN_CACHE`, default `~/.cache/flyconn`). Pull a dataset
with `flyconn data pull malecns@1.0 --level weights` (about 1.1 GB).

## Tools

| Tool | Does |
|---|---|
| `list_datasets` | Registered datasets with licence, citation, download size per level, and the locally cached level |

## Honesty

Wiring is measured; neurotransmitter signs are predicted; simulation outputs are model
predictions. Experiments run with rewire / sign-shuffle controls on by default.

## Development

`scripts/check.sh` runs ruff, format check, pyright (strict) and the offline tests.

Licence: Apache-2.0.
