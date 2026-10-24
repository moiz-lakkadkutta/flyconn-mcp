# Progress

Resume here. Scope and decisions: `PLAN.md`.

## 2026-10-24: M0 done, M1 started

Branches: `m0-scaffold` (1 commit) → `m1-queries` (on top). Nothing pushed; no GitHub repo
yet. Each needs the owner's yes.

**Works**
- uv project, src layout, Apache-2.0, ruff + strict pyright + pytest, `scripts/check.sh`,
  `.github/workflows/ci.yml` (not yet run on GitHub).
- stdio server on the official SDK `mcp` 2.3 (`MCPServer`; v2 renamed FastMCP). Entry point
  `flyconn-mcp`.
- Tools: `list_datasets`, `find_neurons`, `neuron_partners`. Each is read-only and returns
  provenance. Errors are `ToolError`s that say what to do next (pull command + size; close
  type matches).
- 14 offline tests through the in-process `mcp.Client`, using a synthetic store with
  hand-placed types for exact assertions (`tests/conftest.py`).
- Smoke test on cached malecns@1.0 over stdio: ≤0.1 s per query, ~340 MB peak RSS (see README).
- Registered locally as `flyconn` (`claude mcp get flyconn` shows Connected).

**Defaults chosen (owner can override)**
- `dataset` defaults to `malecns@1.0`; `min_weight` defaults to 5 (the common FlyWire
  threshold; flyconn's own default is 1); `top_n` is 20 for types and 10 for partners.
- Signs use the argmax policy (flyconn's default). Downstream edges are signed by the query
  type; upstream edges by the partner.
- Partner queries are DuckDB aggregations through `Store.query`, not a `ConnectivityMatrix`
  (see `docs/upstream-notes.md`).

**Next (M1 remainder)**
1. `find_paths` (flyconn `find_paths` + path stability), kept small on MaleCNS.
2. `compare_across_datasets` with a MaleCNS ↔ FlyWire 783 name resolver (MN9 = CB0701,
   GNG232 = CB0616), using the `fafb_783_cell_type` column in MaleCNS neurons.
3. Golden-marked tests on cached MaleCNS (numbers above) under `pytest -m golden`.
Then M2: experiments as background jobs (no full-dataset sims until then).

**Open for the owner**
- Land `docs/flyconn-adr-draft.md` as ADR-0013 in flyconn once M14 is committed.
- Create the GitHub repo and push (outward-facing; not done).
