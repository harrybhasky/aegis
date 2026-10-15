# AEGIS Technical Project Report

## Executive summary

AEGIS is a correctness-first framework for using large language models to optimize multi-clock RTL for timing closure. Its central design decision is to treat clock-domain-crossing safety as a distinct verification problem: formal equivalence and simulation can establish valuable properties, but they do not model metastability. AEGIS therefore discovers CDC structures before generation, assigns lock tiers, and rejects candidates that alter protected structure or violate their checksums.

The project combines deterministic EDA tooling with LLM judgment:

1. Parse RTL and SDC to build clocks, crossings, lock maps, and contracts.
2. Establish a synthesis-only baseline with Yosys and OpenSTA.
3. Select timing-critical regions per clock domain.
4. Generate several candidates inside a computed edit envelope.
5. Gate candidates through structural checks, lint, simulation, EQY, and CDC re-checks.
6. Score timing and area while protecting every domain.
7. Update a reusable skill library from observed outcomes.

## Technical architecture

### Lock tiers

- **Immutable:** synchronizer chains, reset synchronizers, clock dividers, clock gating/mux logic, and constraint-sensitive launch/capture structures.
- **Contract-bound:** protocol logic such as Gray-pointer FIFOs, handshakes, pulse synchronizers, and qualified captures; edits are allowed only when the contract is re-proven.
- **Free:** ordinary combinational and sequential logic that is inside the selected timing envelope and passes all downstream checks.

### Verification policy

The candidate gate is intentionally ordered so cheap and high-signal checks happen before expensive EDA work:

```text
checksum / edit envelope
        ↓
lint and elaboration
        ↓
simulation or LCM checks
        ↓
EQY / formal equivalence
        ↓
CDC structural re-check
        ↓
timing, area, and per-domain score
```

Any hard-gate failure rejects the candidate. It is not converted into a favorable score through averaging.

## Benchmark methodology

The release includes CDC primitives, single-clock and Dr. RTL-style designs, baseline synthesis/OpenSTA measurements, mutation-based guardrail tests, and end-to-end run summaries. The public tree retains source provenance and reports while omitting downloaded upstream repositories, generated solver workspaces, and media unrelated to the research artifact.

## Measured results

### Baseline characterization

| Design | Clocks | Flops | CDC structure | Synth WNS (ns) | Synth area (um²) |
|---|---:|---:|---|---:|---:|
| `prim_pulse_sync` | 2 | 4 | 1 synchronizer | -0.050 | 24.472 |
| `async_fifo` | 2 | 12 | 2 Gray buses | -0.160 | 1,387.456 |
| `soc` | 4 | 29 | 3 sync, 2 Gray, 1 qualified | -0.380 | 1,146.992 |
| `eth_mac_1g_fifo` | 3 | 127 | 12 sync, 3 Gray, 2 qualified | -0.330 | 15,108.268 |

### Guardrail mutation results

| Mutation class | Expected outcome | Observed outcome |
|---|---|---|
| Equivalent rewrite | Accept | Lint, simulation, EQY, and CDC re-check pass |
| Functional bug | Reject | Simulation and EQY fail |
| Synchronizer stage edit | Reject | Lock checksum fails before unsafe promotion |
| Binary launch replacing Gray launch | Reject | EQY and CDC checks fail |
| Combinational CDC launch | Reject | CDC re-check and/or EQY fail |

### End-to-end experiment results

The included experiment report contains 12 completed run summaries. The most informative comparison is the CDC-heavy `soc` design:

| Configuration | SEC pass rate | Lock violations | CDC violations | Area delta | Top-level EQY |
|---|---:|---:|---:|---:|---|
| AEGIS | 53.33% | 0 | 0 | -3.43% | PASS |
| Vanilla | 4.00% | 0 | 24 | -3.43% | PASS |

The AEGIS run improved the `clk_w` domain from -0.04 ns to +0.04 ns and preserved the `clk_r` improvement from +0.19 ns to +0.35 ns. The `clk_x` domain remained at -0.38 ns, which is a documented residual deficit rather than an omitted result. Across the full report, AEGIS runs also include cases with regressions and low pass rates; the framework is not presented as universally successful.

## What the results support

The results support three bounded claims:

1. **Structural guardrails catch classes of unsafe edits that ordinary equivalence alone is not designed to model.**
2. **A domain-aware, tool-grounded loop can produce formally accepted timing/area improvements on selected designs.**
3. **Candidate rejection telemetry and a persistent skill library make failures inspectable and reusable across runs.**

They do not support a claim that AEGIS always improves WNS, replaces signoff CDC tools, or generalizes to arbitrary RTL without calibration.

## Known limitations

- Vector shift-register synchronizers can be missed by the current structural recognizer.
- Bitwise Gray synchronization can be under-recognized as a bus-level Gray contract.
- Qualifiers folded into reset pins can be invisible to the current data-flow extraction.
- Port-sourced data crossings and reset-domain crossings need explicit modeling.
- Some launch registers are named through aliases, which can result in vacuous lock hashes.
- Synthesis-only STA does not model placement and routing delay.
- Benchmark licensing differs across upstream projects; provenance is preserved and redistribution is intentionally conservative.

## Reproduction checklist

```bash
python3 -m pytest -q tests
python3 aegis_agents/bench/report.py --out aegis_agents/bench/results
python3 aegis_agents/tools/aegis_ingest.py --help
python3 aegis_agents/tools/aegis_run.py --help
```

For full synthesis, STA, formal, and mutation runs, install the versions listed in [`aegis_agents/README.md`](aegis_agents/README.md) and obtain third-party benchmark sources under their respective licenses.

## Target conferences

The work was shaped toward **ICCAD** (core EDA automation and correctness guardrails), **DAC** (practical design automation and timing closure), **MLCAD** (LLM orchestration, learned skill reuse, and ablations), with **ASP-DAC** and **DATE** as secondary targets for the multi-clock verification and reproducibility angle. Venue names indicate research targeting only; they are not publication or acceptance claims.
