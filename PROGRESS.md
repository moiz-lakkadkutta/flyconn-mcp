# Progress

Resume here. Scope and decisions: `PLAN.md`.

## 2026-10-26: find_paths, golden tests, PR #1

- Repo is public: github.com/moiz-lakkadkutta/flyconn-mcp. PR #1 is `m1-queries` → `main`.
  PR #2 (`m1-paths`) is stacked on it. The owner approved opening PRs; merging still needs
  their yes.
- **CI has never run.** Actions is enabled and the `ci` workflow is active, but GitHub created
  no Actions check suite for any push or PR (only Vercel's). Total runs: 0. Possibly an
  account-level Actions/billing setting; the owner needs to look.
- `find_paths`: SQL prunes to the neurons within max_hops of both ends, then flyconn's
  `path_stability` runs on that subgraph. It matches the full matrix exactly (golden), at ~1/3
  of the RAM. Defaults: max_hops 3 (cap 4), min_weight 5, thresholds 1×/2×/4×, 100 NT samples,
  seed 0. It refuses subgraphs over 20,000 neurons with an error saying what to change.
- Golden tests: `uv run pytest -m golden` (needs cached malecns@1.0; ~5 s, 2.5 GB peak from
  the full-matrix comparison). 3 pass.
- Next: `compare_across_datasets` with the MaleCNS ↔ FlyWire 783 resolver, then M2.

## 2026-10-24: M0 done, M1 started

Branches: `m0-scaffold` (1 commit) → `m1-queries` (on top).

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
1. ~~`find_paths`~~ (done 2026-10-26).
2. `compare_across_datasets` with a MaleCNS ↔ FlyWire 783 name resolver (MN9 = CB0701,
   GNG232 = CB0616), using the `fafb_783_cell_type` column in MaleCNS neurons.
3. ~~Golden-marked tests on cached MaleCNS~~ (done 2026-10-26).
Then M2: experiments as background jobs (no full-dataset sims until then).

**Open for the owner**
- Land `docs/flyconn-adr-draft.md` as ADR-0013 in flyconn once M14 is committed.
- ~~Create the GitHub repo and push~~ (done by the owner 2026-10-25).
- Find out why GitHub Actions never runs (see the 2026-10-26 entry).
