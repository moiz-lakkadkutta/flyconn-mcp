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
