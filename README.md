# flyconn-mcp

An MCP server that lets Claude, Cursor or any MCP client query public *Drosophila* connectomes
and run in-silico experiments on them through [flyconn](https://github.com/moiz-lakkadkutta/flyconn).
It runs locally. Every answer carries flyconn's provenance and honesty labels.

> Status: pre-alpha. Read-only queries work; experiments-as-jobs is the next milestone
> (see `PLAN.md`, `PROGRESS.md`).

## Install (from source, for now)

```sh
git clone https://github.com/moiz-lakkadkutta/flyconn-mcp && cd flyconn-mcp
uv sync
claude mcp add flyconn -- uv --directory "$PWD" run flyconn-mcp
```

Once released on PyPI: `claude mcp add flyconn -- uvx flyconn-mcp`.

Data lives in flyconn's cache (`$FLYCONN_CACHE`, default `~/.cache/flyconn`). The server never
downloads data itself. Pull a dataset with `flyconn data pull malecns@1.0 --level weights`
(about 1.1 GB); `list_datasets` reports sizes and what is cached.

## Tools

| Tool | Does |
|---|---|
| `list_datasets` | Registered datasets: licence, citation, download size per level, locally cached level |
| `find_neurons` | Neurons by cell-type glob (`GNG23*`, case-insensitive) and/or super class: counts per super class, top types with predicted NT |
| `neuron_partners` | Top upstream / downstream partner types of a cell type: synapses, share of input/output, signed synapses; `min_weight` threshold (default 5) |

Every query result includes `provenance`: dataset@version, the store's converter and build
date, flyconn and flyconn-mcp versions, every parameter, the threshold and the sign policy.

### Measured on MaleCNS v1.0 (2026-10-24, M4 Pro, 166,700 neurons, 25.6M edges)

`neuron_partners(cell_type="GNG232", top_n=5)` over stdio, excerpt:

```
query:    GNG232, 2 neurons, acetylcholine (predicted)
upstream: 2,295 synapses at min_weight=5, 39 partner types
  LB3c     13 neurons  481 syn  21.0%  signed +481  acetylcholine
  LB3d     19 neurons  452 syn  19.7%  signed +452  acetylcholine
  GNG452    4 neurons  209 syn   9.1%  signed -209  gaba
downstream: 2,073 synapses, 53 partner types
  GNG041    2 neurons  403 syn  19.4%  signed +403  (GNG232's sign: ACh)
```

`neuron_partners(cell_type="MN9", direction="upstream")`: 6,085 input synapses from 74
types; the top one is DNge062 (556 synapses, +). Each query took ≤0.1 s, and the server's peak
RSS was about 340 MB.

## Honesty

Wiring is measured; neurotransmitters, and so edge signs, are **predicted** (argmax policy,
flyconn ADR-0007). Simulation outputs, when they arrive, are model predictions and run with
rewire / sign-shuffle controls on by default.

## Development

`scripts/check.sh` runs ruff, format check, pyright (strict) and the offline tests. Tests use
flyconn's synthetic connectome and drive the tools through the SDK's in-process MCP client.

Licence: Apache-2.0.
