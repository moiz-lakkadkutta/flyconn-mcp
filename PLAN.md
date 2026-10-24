# flyconn-mcp — plan and handoff

Written 2026-10-24 at the end of a brainstorming session in the `flyconn` repo
(`/Users/moizp/google-fly`, github.com/moiz-lakkadkutta/flyconn, v0.4.0 on PyPI).
A new session starts here. Read this file, then flyconn's `CLAUDE.md` and `docs/caveats.md`.

## What and why

A standalone MCP server that lets anyone using Claude / Cursor / any MCP client query and run
in-silico experiments on public *Drosophila* connectomes through flyconn, locally, with
flyconn's controls, uncertainty and provenance carried into every answer.

> "Silence GNG232 in the male fly, drive the sugar neurons, what happens to MN9 — and does it
> survive a rewired control?" → it actually runs, and says honestly what the result is.

Owner goals: (1) learn and build skills, (2) lots of people using it.

Evidence from the 2026-10-24 research pass (web; numbers as read that day):
- No MCP server runs connectome experiments. VirtualFlyBrain's `VFB3-MCP` only looks things up;
  `navis-org/coda-mcp` (Coda, beta since 2026-08) only authors workflows and runs nothing.
  GitHub search found no neuPrint / FlyWire / Drosophila MCP server.
- Community pain: auth tokens, v630-vs-v783 version confusion, one client per platform,
  correctness bugs in forks of the Shiu model. flyconn's offline store + validated sim fix these.
- Mood has shifted to scepticism (Eon Systems "uploaded fly" critique; Tuthill/Brunton
  "digital sphinx" worm-wiring control). Controls-on-by-default is a selling point, not a cost.
- flyconn today: 0 GitHub stars, ~320 PyPI downloads a month. This project is the adoption vehicle.

## Decisions already made (owner-approved)

- **Standalone repo and PyPI package `flyconn-mcp`** that depends on `flyconn`. It is not an
  extra inside flyconn. Reasons: its own README, demo and stars for discoverability; a clean
  `uvx flyconn-mcp` / `claude mcp add flyconn -- uvx flyconn-mcp`; the fast-moving MCP SDK is
  kept apart from the slow, validated science library; and it dogfoods flyconn's public API.
  `flyconn-mcp` was free on PyPI and GitHub on 2026-10-24.
- Write an ADR in the flyconn repo recording this build-vs-reuse choice (flyconn convention).

## Defaults (my calls; owner can override)

- Python ≥3.11, `uv`, `ruff`, `pyright`, `pytest`, and Apache-2.0, all matching flyconn.
- Official MCP Python SDK, `mcp>=2.3,<3`. In v2, `FastMCP` was renamed `MCPServer`
  (`mcp.server.mcpserver`) and the v1 module raises on import. Tests use the in-process
  `mcp.Client(server)`. stdio transport first.
- Pin `flyconn>=0.4,<0.5` with the `sim` extra.
- Unit tests stay offline and use flyconn's synthetic connectome (`flyconn.testing`); golden
  tests need cached MaleCNS.
- The server never downloads multi-GB data silently. The pull tool states the size and needs an
  explicit call. Default cache is flyconn's (`FLYCONN_CACHE`).

## Carry flyconn's principles into tool outputs

- Every experiment result says it is a **model prediction**, that NT signs are **predicted**,
  and which control results apply (rewire / sign-shuffle). Never drop the controls to save time
  unless the user asks, and then say so in the output.
- Every result returns provenance: dataset@version, thresholds, seed, package versions, and
  report path.
- Return compact summaries (top-N tables, significance, effect sizes). Put full tables and the
  HTML report on disk and return their paths or MCP resources. Don't dump huge frames into context.

## flyconn API to build on (verified 2026-10-24, flyconn 0.4.0)

- Data: `flyconn.data.registry.list_datasets()`, `get_dataset(ref)`;
  `flyconn.data.store.Store.open("malecns@1.0")`. CLI: `flyconn data list | info | pull`.
- Graph: `flyconn.graph.ConnectivityMatrix.from_store(store, min_weight=...)`, `find_paths`,
  `effective_connectivity`, `aggregate`, `sign_table`.
- Experiments: `flyconn.experiments.spec_from_dict` / `load_spec` → `ExperimentSpec`;
  `flyconn.experiments.runner.run_experiment(spec, out_dir=...)`;
  `flyconn.experiments.sweep.run_sweep`; `flyconn.experiments.robustness.run_robust_screen`.
  Mirror `flyconn/cli/main.py::run_cmd`, which dispatches on `spec.robustness` / `spec.sweep`.
  Spec example: `examples/specs/w2_malecns_lb3_silence_gng232.yaml` in the flyconn repo.
- Uncertainty: `flyconn.uncertainty.path_stability`, `degree_preserving_rewire`, `sample_signs`.
- Cross-dataset: `flyconn.compare.compare_type`, `match_types`, `build_atlas`, `classify`.
- Genetic access: `flyconn.access.attach_lines`, `load_catalog`.

## Draft tool surface (refine in the first session)

| Tool | Does | Notes |
|---|---|---|
| `list_datasets` | registry + which are cached locally | fast |
| `pull_dataset` | download one dataset at one level | states size first; long-running job |
| `find_neurons` | search by cell type / class / pattern, with counts | fast |
| `neuron_partners` | top up/downstream partners of a type, signed | fast |
| `find_paths` | paths between two selections + stability across thresholds | medium |
| `start_experiment` | validate a spec dict (or a YAML path), start it as a background job, return job id | sims take minutes; never block a tool call |
| `experiment_status` / `experiment_result` | progress; summary + controls + provenance + report path | |
| `compare_across_datasets` | the same type in MaleCNS / FlyWire / BANC | |
| `driver_lines` | split-GAL4 lines for a type | |

Also consider MCP **resources** (report HTML, provenance.json) and one or two **prompts**
(for example "design a silencing experiment").

Main technical risk: a MaleCNS simulation can take minutes and lots of RAM (the robustness
screen peaked at 12.6 GB). Run jobs in a separate process with one job at a time by default,
and pick sensible small defaults (trials, duration) that the user can raise.

## Milestones (one branch each, tests green per commit)

1. **M0 scaffold:** repo, uv, CI (ruff / pyright / pytest), stdio server with `list_datasets`,
   and an ADR in flyconn. Done when `claude mcp add` works locally and the tool shows up.
   Status 2026-10-24: done. `list_datasets`, 4 offline tests, `claude mcp add` connected.
   The ADR draft is `docs/flyconn-adr-draft.md` (ADR-0013); land it in flyconn once M14 lands.
2. **M1 read-only queries:** `find_neurons`, `neuron_partners`, `find_paths`,
   `compare_across_datasets` with a cross-dataset name resolver (MaleCNS ↔ FlyWire 783),
   and offline tests on the synthetic fixture.
3. **M2 experiments as jobs:** start / status / result, controls on, provenance, report
   resource, and an UNCALIBRATED flag for non-MaleCNS sims. Golden check: the W2 GNG232 → MN9
   result through MCP matches the flyconn CLI.
4. **M3 polish:** `pull_dataset`, `driver_lines`, prompts, error messages written for an LLM
   reader (say what to do next), and an MCPB bundle (`server.type: "uv"`).
5. **M4 launch:** PyPI release, README with a GIF/video of the demo prompt, an MCP Registry
   listing (pypi + mcpb), a post (Show HN / Bluesky / FlyWire community), a link from flyconn's
   README.
6. **M5 hosted read-only tier:** Streamable HTTP on a free HF Space, query tools only.

## Launch decisions (2026-10-24, owner delegated; research notes in session scratchpad)

**Demo prompt (drives M2 defaults).** Primary, verbatim:
> "In the male fly brain, stimulate the taste neurons on the proboscis and watch MN9, the motor
> neuron that makes the fly extend its proboscis to feed (Shiu et al., Nature 2024). Now silence
> GNG232. Does MN9 drop, and does the effect survive the controls?"

This is golden run W2 (`w2_malecns_lb3_silence_gng232.yaml`): MN9 30.1 → 14.1 Hz, d −3.5,
q 9e-8. Rewired control: MN9 0 Hz. The sign shuffle runs away and must read "uninformative",
not "passed". The robustness tier is *Conditional* (5 of 8 sign variants). It took 190 s on the
M4 Pro. The spec drives all LB3 neurons (sugar and water), so the prompt says "taste", not "sugar".
The honest "conditional" verdict is the hook. Second clip: reproduce Shiu 2024 on shiu@630
(66.5 vs 65.7 Hz published, 13 s); this needs named root-ID sets shipped in flyconn-mcp.
- **M2 defaults:**
  - MaleCNS: 20 trials × 500 ms, rewire ×2, sign-shuffle ×2 (always reported, with the runaway
    caveat), unstimulated baseline, seed 0, CPU float32, one job at a time.
  - shiu@630: 30 × 1000 ms.
  - `robustness:` is an opt-in "audit" job that warns it takes ~18 min and ~12.6 GB.
- **Before recording:** measure peak RAM for W2 alone on a 16 GB machine.

**Datasets at launch:** malecns@1.0 + flywire@783, with shiu@630 as the validation reference.
All three are public, need no token, are CC BY 4.0 (shiu: MIT), and are golden-tested.
- **Download sizes at the weights level:** about 1.1 GB, 123 MB and 90 MB.
- **Uncalibrated:** only MaleCNS is in `CALIBRATIONS`, so FlyWire sims must say UNCALIBRATED.
- **Names differ:** MN9 is CB0701 and GNG232 is CB0616 in FlyWire 783, so M1 needs a
  cross-dataset name resolver.
- **Fast-follow:** banc@888.

**Hosting:** local-first; a hosted read-only tier after launch.
- **Launch:**
  - `uvx flyconn-mcp` over stdio.
  - An MCPB bundle with `server.type: "uv"` (manifest 0.4+, host-managed Python, ~100 KB).
  - An official MCP Registry listing with pypi + mcpb packages; prove ownership with
    `mcp-name:` in the README.
- **M5: hosted read-only queries over Streamable HTTP, no sims.**
  - Where: a Hugging Face Space, CPU Basic, free: 2 vCPU / 16 GB (stores ≈ 230 MB).
  - Why: Claude.ai custom connectors are remote-only, open to all plans (Free: one connector),
    can be added with "No sign in", and call from Anthropic's cloud.
  - ChatGPT: full MCP is Business / Enterprise only, so it is a smaller audience. Pro users
    get read / fetch only, which a read-only tier suits.
  - VirtualFlyBrain's remote `vfb3-mcp` (registry, 2026-10-21) is the timing pressure.
- **Hosted sims:** only behind auth and rate limits. Options: HF CPU Upgrade (8 vCPU / 32 GB,
  $0.03/h as listed) or per-run serverless. Fly performance-2x 16 GB is $138/month always-on.
- **Later idea:** Claude "interactive connectors" (MCP Apps) could render result charts inline.

## Later directions (not this project)

From the same research, for after flyconn-mcp ships:
- "Honest fly" flyconn → FlyGym brain–body bridge with shuffled/worm-wiring controls and a
  public scoreboard (the flagship idea).
- Harmonized connectome Parquet plus a benchmark on Hugging Face, with Colab course notebooks.
