# AEGIS

### Guardrailed LLM optimization of multi-clock RTL for timing closure

![Status](https://img.shields.io/badge/status-research--prototype-7c3aed)
![Domain](https://img.shields.io/badge/domain-RTL%20%7C%20EDA%20%7C%20CDC-0f766e)
![Verification](https://img.shields.io/badge/verification-EQY%20%2B%20CDC%20structural%20checks-15803d)
![License](https://img.shields.io/badge/license-research%20release-lightgrey)

AEGIS is a research prototype for **tool-grounded, correctness-first RTL optimization**. It uses an LLM to propose timing-oriented rewrites, but does not treat “the code compiles” or “formal equivalence passed” as sufficient evidence for a multi-clock design. Instead, AEGIS first discovers clock-domain crossings, classifies the associated logic into lock tiers, and prevents unsafe edits to synchronizers, CDC contracts, reset crossings, clock dividers, and other constraint-sensitive structures.

The result is an auditable optimization loop:

```text
RTL + SDC
   │
   ├── Phase 1: ingest clocks, crossings, lock tiers, checksums, contracts
   ├── Baseline: Yosys synthesis + OpenSTA timing
   ├── Select: domain-aware critical regions
   ├── Generate: multiple LLM candidates within an edit envelope
   ├── Verify: checksum gate → lint → simulation → EQY → CDC re-check
   ├── Evaluate: WNS/TNS/area with per-domain safeguards
   └── Learn: update the reusable RTL skill library
```

## Why this project matters

LLM-based RTL optimization is attractive because timing closure is iterative, expensive, and rich in expert pattern recognition. It is also risky: asynchronous CDC correctness depends on metastability behavior that ordinary simulation and equivalence checking do not model. AEGIS addresses that gap with a **hard structural guardrail upstream of generation**, while preserving the useful parts of an LLM-driven search loop.

### Research contributions

- **Checksum-enforced lock map:** immutable, contract-bound, and free regions are identified from RTL/SDC structure before generation.
- **CDC-aware optimization:** synchronizer chains, Gray-pointer protocols, qualified captures, reset crossings, and clock-divider logic receive explicit protection.
- **Domain-aware scoring:** WNS/TNS are evaluated per clock domain so a gain in one domain cannot hide a regression in another.
- **Formal hard gates:** EQY failures reject candidates instead of becoming a soft penalty.
- **Self-improving skills:** the Librarian tracks pattern-level outcomes, confidence, anti-patterns, and reuse across designs.
- **Reproducible artifacts:** benchmark inputs, design constraints, the CDC mutation generator and labeler, and the experiment harness are included.

## Repository map

```text
.
├── aegis_agents/              Deterministic tools, agent prompts, and benchmark harness
│   ├── tools/                 Ingest, STA, selection, generation, verification, evaluation
│   ├── bench/                 Baselines, CDC mutation tests, suites, and report generation
│   └── .claude/               Agent and RTL optimization skill definitions
├── benchmarks/                Benchmark provenance and redistribution notes
├── experiments/               Reproducible experiment manifests
├── scripts/                   Yosys, OpenSTA, Verilator, and EQY wrappers
├── src/                       Minimal example RTL
├── tests/                     Unit tests for parser and scoring helpers
├── orchestrator_langgraph.py  Standalone LangGraph/Gemini prototype
└── rtl-timing-analyzer.md     Project-facing timing analysis notes
```

## Quick start

### 1. Install the EDA toolchain

AEGIS is designed around Python 3.10+, Yosys, OpenSTA 3.1+, Verilator and/or Icarus Verilog, SymbiYosys, a solver such as Z3, EQY, and Nangate45 liberty data. The exact assumptions and setup notes are documented in [`aegis_agents/README.md`](aegis_agents/README.md).

### 2. Run the lightweight tests

```bash
python3 -m pytest -q tests
```

### 3. Inspect the deterministic tools

```bash
python3 aegis_agents/tools/aegis_ingest.py --help
python3 aegis_agents/tools/aegis_sta.py --help
python3 aegis_agents/tools/aegis_run.py --help
python3 aegis_agents/bench/report.py --help
```

### 4. Reproduce report generation

```bash
python3 aegis_agents/bench/report.py --out aegis_agents/bench/results
```

Full EDA runs require the tools, liberty files, and benchmark sources described in the benchmark documentation. Generated netlists, solver workspaces, downloaded third-party repositories, and local credentials are intentionally not part of this public release.

## Scope and limitations

AEGIS is a research prototype, not a signoff replacement. Its structural checks are conservative and can produce false positives or miss RTL idioms they do not recognize. Known limitations include in vector synchronizer recognition, Gray-bus inference, reset-domain crossings, port-sourced data crossings, and calibration of some contract-bound logic. Physical placement/routing effects are not modeled by the synthesis-only timing flow.

## Responsible release notes

This repository contains original AEGIS code and documentation. Third-party benchmark provenance and license notes are preserved in [`benchmarks/README.md`](benchmarks/README.md); full upstream benchmark copies and unrelated local media are not redistributed here. Before using an upstream design in a public experiment, follow its license and request permission where the provenance notes require it.
