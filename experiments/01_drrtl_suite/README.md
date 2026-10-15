# Experiment 01: Dr. RTL single-clock suite

Dr. RTL's 20 released designs (`benchmarks/Dr_RTL/rtl_dataset`, v0, unchanged), already set up as
`aegis_agents/flow/designs/drrtl_*` with Dr. RTL's 0.1 ns clock. Phase 1 and the synthesis-only baselines
are in `aegis_agents/bench/results/baseline.md`; all 20 designs violate timing.

## Configurations

| Config | What it is | Role |
|---|---|---|
| `aegis` | full pipeline, 65-entry skill library (`Skill.md`) | ours |
| `scalar` | Aegis loop with Dr. RTL's global scalar score | Dr. RTL-style loop in the same flow |
| `vanilla` | same model, RTL + timing summary, no locks/library/envelope/gating | unguided LLM baseline |

All three use Yosys 0.67 + Nangate45 (typical) + OpenSTA 3.1.0 + EQY, 5 iterations x 5 candidates,
`claude-sonnet-5-5`. Dr. RTL's published numbers (Design Compiler + Jasper, 10 iterations) are not
directly comparable; we report each configuration's relative change against the same synthesis-only baseline.

## Running

```
./run.sh pilot          # ticket_machine + controller, aegis + vanilla, 1 rep
./run.sh full 1         # 20 designs x aegis/scalar/vanilla, 1 rep
./run.sh full 3         # adds reps 2-3 (finished runs are skipped)
```

Runs are written to `aegis_agents/flow/runs/<design>/<config>.sonnet-5-5.r<k>/`; tables go to `results/`
(`report.md`, `runs.csv`). Every number in the paper must come from these files.
