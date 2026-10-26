# Notes for flyconn (upstream)

Rough edges in flyconn's public API found while building flyconn-mcp. Nothing here has been
changed in flyconn; raise each as an issue or fix in a flyconn milestone.

1. **No scoped partner query.** `ConnectivityMatrix.from_store(neuron_ids=...)` filters
   neurons but still calls `store.edges(min_weight=...)` for *all* edges (25.6M on MaleCNS)
   before dropping the ones outside the selection. A `Store.edges(pre=..., post=...)` call
   exists but takes neuron ids, not types, and returns raw rows. flyconn-mcp therefore
   aggregates partners with its own SQL over `Store.query`. Suggestion: a
   `flyconn.graph.partners(store, cell_type, direction, min_weight)` that pushes the filter into
   DuckDB, so the MCP server and the CLI share one tested implementation.
2. **The sign table is not exposed as SQL.** flyconn-mcp rebuilds a `CASE nt_pred ...` from
   `flyconn.graph.signs.sign_table()`. That stays correct for the argmax policy only; a helper
   in flyconn would keep probabilistic signs consistent too.
3. **The cached level is read from a private helper.** `flyconn.data.pull._existing` reads the
   level from `provenance.json`; flyconn-mcp reimplements it. Suggestion: a public
   `cached_level(ref)` (or `Store.level`).
4. **Store-writing test helpers live in flyconn's `tests/` and are not packaged.** flyconn-mcp
   copies the `write_parquet` / `write_provenance` fixture pattern. A
   `flyconn.testing.write_synthetic_store(root, ...)` would let downstream packages test
   against the exact store layout.
5. **The Shiu 2024 neuron sets** (`tests/fixtures/shiu_2024_neuron_sets.json`) are not in the
   package. They are needed for the second demo clip (PLAN.md).
6. **Path analyses need the full matrix.** `find_paths` / `path_stability` take a
   `ConnectivityMatrix`; building one for MaleCNS peaks at ~2.5 GB. flyconn-mcp prunes in SQL
   first (`flyconn_mcp/paths.py`: a recursive CTE keeps the neurons with
   d(source) + d(target) ≤ max_hops), which is exact for simple paths. It would fit well as a
   `ConnectivityMatrix.path_subgraph(store, sources, targets, max_hops, min_weight)`.
7. **`sample_signs` depends on row order and count.** The same seed gives different draws on
   a subgraph than on the full matrix, so `sign_stability` from a subgraph matches a
   full-matrix run statistically, not bit for bit. Seeding per neuron id would make them
   identical.
8. **`path_stability` has no `max_paths`.** It calls `find_paths` with the 1,000,000 default.
   flyconn-mcp bounds the work by capping the subgraph size instead.
