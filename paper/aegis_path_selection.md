# AEGIS Phase 2: Domain-Aware Path and Region Selection

Status: design proposal. Nothing here has been run or ablated yet. Parameters marked **(tunable)** need experiments before the paper quotes them.

## Why not a global top-K by WNS

A global top-K list ranks paths by their individual slack in nanoseconds. That fails on multi-clock designs for one reason: **slack in ns cannot be compared across clock domains.** A -0.5 ns violation on a 10 ns clock is 5% of its period. A -0.2 ns violation on a 1 ns clock is 20% of its period and far more serious, but a global list ranks it lower. Near-critical paths from one domain can then fill the remaining slots.

Dr. RTL (the closest prior work) does not address this, because all 20 designs in its `design_all.json` are single-clock. To describe it accurately:

- Its timing-analyzer agent picks K between 10 and 25 paths from `timing_word.json`, ranked by worst slack.
- Its orchestrator varies path selection across the 5 minor attempts (top-K, path ranges, endpoint clustering, high fanout, module focus, random sample).
- Its `try_different_paths` hint reads the previous two iterations' logs and excludes paths already tried.

So say "Dr. RTL does not handle multiple clock domains", not "Dr. RTL breaks". And do not claim it treats a 32-bit multiplier as 32 separate problems unless you measure that.

AEGIS selects **regions** instead: a region is the logic cone shared by a group of related violating endpoints.

---

## Step 1: Collect Paths Per Capturing Clock

Run OpenSTA with one path group per clock and collect every path that violates timing **or falls below the closure margin** (for example slack under +100 ps, the same margin the closure gate uses). Tag each path with its **capturing** clock, because that is the domain whose period it has to meet.

Output: a list of paths, each with slack, startpoint, endpoint, capturing clock and launching clock.

## Step 2: Map Each Path to RTL Deterministically

For each path:

1. Take the startpoint and endpoint register names from the report.
2. Normalize the names (strip hierarchy prefixes and `_reg` suffixes, undo bit-index renaming).
3. Compute the combinational cone between those registers in the **pre-synthesis** design, and record the source lines it touches.

Tooling note: Pyverilog parses Verilog-2001 only, not SystemVerilog. Use Yosys source-line attributes after `proc` (with `sv2v` or the slang frontend for full SystemVerilog), or pyslang. Disable FSM recoding in analysis runs.

Be honest about reliability: names usually survive synthesis but not always. Registers can be merged, retimed, recoded or folded into inferred memories. Paths that fail to map are logged and excluded, and **the match rate is reported in the paper**. That number is your evidence for the "deterministic mapping" claim.

The cone is not one contiguous line range. It can span several always blocks, functions and modules. Keep it as a set of statements plus the declarations and module context needed to read them.

## Step 3: Classify Each Path by Crossing Type

Compare launching and capturing clocks:

| Crossing type | Action |
|---|---|
| Same clock (intra-domain) | Normal optimization target |
| Related clocks (master and generated) | Optimizable, but latency-sensitive: tag for the latency-aware rules |
| Asynchronous clocks | **Do not optimize.** Send to the Phase 0 constraint report: a violation here means a missing `set_clock_groups -asynchronous` or `set_max_delay -datapath_only`, which is an SDC bug, not an RTL bug |

Asynchronous paths are also excluded from baseline TNS, so they cannot inflate any domain's weight.

## Step 4: Lock-Tier Filter and Tagging

Use the Phase 1 lock map on the cone from Step 2. This has to run after mapping, because you cannot tell whether a path lies in locked logic until it is mapped to RTL.

- **Entirely inside the immutable tier** (synchronizer chains, reset synchronizers, launch flops, clock dividers, gating cells, clock muxes): drop it.
- **Contains contract-bound logic** (Gray pointer logic, handshake logic, pulse toggles, qualifier buses, capture registers): keep it, and tag it. It may be rewritten, but the candidate must pass the contract proofs.
- **Touches the immutable tier at its edge:** tag as lock-adjacent.
- **Free logic:** keep.

Log the TNS blocked by each tier. That number is the cost of the guardrail, and reviewers will ask for it.

## Step 5: Calculate Domain Weights (w_d)

```
w_d = f_d / f_max
```

where f_d is the frequency of domain d and f_max is the fastest domain's frequency. This makes w_d × slack proportional to slack divided by the clock period, so picoseconds become relative impact:

- -500 ps on a 1 GHz clock (1,000 ps period) is 50% of the cycle.
- -500 ps on a 100 MHz clock (10,000 ps period) is 5% of the cycle.
- The weights (1.0 and 0.1) give the same 10:1 ratio.

**Use the same w_d as the scoring function (Eq. 8)**, so selection optimizes what the score rewards.

## Step 6: Cluster Paths into Regions

Group paths whose cones overlap, so ten paths through the same multiplier become one region.

1. For each pair of paths in the same domain, compute the overlap of their cones (for example the Jaccard overlap of their register and statement sets).
2. Merge pairs whose overlap is at least a threshold **(tunable)**, using union-find.
3. Assign each path to exactly one region, so TNS is never double-counted across overlapping regions.

Paths in one region share *overlapping* cones, not necessarily identical ones. The threshold decides how aggressively they merge.

## Step 7: Score Each Region (P_r)

For region r in domain d, normalize each term against its own domain so the scales are comparable:

```
P_r = ( α · |WNS_r| / |WNS_d|  +  β · |TNS_r| / |TNS_d| ) · A_r
```

- `|WNS_r|`: the worst slack among the region's paths.
- `|TNS_r|`: the sum of negative slack over the region's own paths.
- `|WNS_d|`, `|TNS_d|`: the domain totals, so both ratios lie between 0 and 1. Without this, TNS (which grows with the number of violating paths) would swamp WNS and α would barely matter.
- `A_r`: the fraction of the region's paths whose amenability is combinational or sequential-safe. This is the fraction of paths the optimizer can fix, not a fraction of code.
- `α, β`: not free knobs. Take the current run's values from the adaptive schedule (early runs favor the single worst path, later runs favor total slack), so selection stays consistent with the score.

Note: within one domain, w_d is a constant, so it does not change the ordering of regions. It matters in Step 8, where domains compete for slots.

## Step 8: Allocate Quotas Per Clock Domain

Choose a total budget B of regions per iteration (for example B = 10). Set it per design from the number of violating regions, not from a size table like Dr. RTL's.

1. **Guaranteed slot:** every domain with violations gets at least 1 slot.
2. **Proportional split:** distribute the remaining slots by weighted share, using absolute TNS:

```
Quota_d = 1 + (B - n_viol) · ( w_d · |TNS_d| ) / Σ_i ( w_i · |TNS_i| )
```

3. Round with the largest-remainder method.
4. Cap each quota at the number of regions that exist in that domain, and pass leftover slots to the other domains.
5. If the number of violating domains exceeds B, give slots to domains in order of w_d × |TNS_d|.

Worked example (B = 10, two violating domains, CPU holds 70% of weighted TNS): remaining slots = 8, CPU gets 1 + 5.6 and USB gets 1 + 2.4, which rounds to 7 and 3.

## Step 9: Pick Regions Greedily Within Each Domain

For each domain, sort its regions by P_r. Take the top region, then the next, and stop when either:

- the domain's quota is full, or
- the selected regions cover a target share of the domain's negative slack **(tunable, for example 80%)**.

The |WNS_r| term keeps the worst path in each domain in play, and the closure gate (WNS above the margin) still decides when to stop optimizing.

## Step 10 (Optional): Bandit Layer

After a region has been tried, adjust its priority with past outcomes:

```
Score_r = P_r · X̄_r  +  c · sqrt( ln N / n_r )
```

- `X̄_r`: smoothed success rate, with reward defined as normalized score improvement for candidates that pass equivalence and 0 otherwise.
- `n_r`: attempts on region r. `N`: total attempts in the design.
- Key each region by its endpoint registers so it can be tracked after a rewrite, and discount old rewards because a promoted rewrite changes the region.

Caveats: the budget is at most 5 iterations × 5 candidates = 25 attempts, so UCB's guarantees do not apply and it will behave like "try each region once, then favor what worked". **Keep it only if an ablation shows it beats plain greedy and a simple tabu list.** The bandit chooses *where* to optimize. The Librarian chooses *how*. Keep them separate.

## Step 11: Pass the Region Cones to Phase 3

For each selected region, hand the LLM:

- the cone's statements, plus the declarations and module context needed to read them,
- the region's paths, slacks and amenability labels.

All five candidates in an iteration target the same selected regions, so Phase 5 compares like with like. (This is a proposed choice. Dr. RTL varies targets across attempts instead.)

After generation, diff each candidate against the original and **reject any edit outside the selected region**, the same way the lock check rejects edits to locked regions.

---

## Summary of the Flow

| Order | Step | Purpose |
|---|---|---|
| 1 | Collect per capturing clock | Paths belong to the domain that has to meet them |
| 2 | Map to RTL cones | Deterministic location; report match rate |
| 3 | Crossing classification | Async paths go to the constraint report |
| 4 | Lock-tier filter and tagging | Drop immutable-only paths; log TNS blocked per tier |
| 5 | Domain weights | Make slack comparable across clocks |
| 6 | Cluster into regions | One problem, one region |
| 7 | Score regions | Rank within each domain, normalized |
| 8 | Per-domain quotas | A slow domain cannot take every slot |
| 9 | Greedy pick | Fill quota or reach the coverage target |
| 10 | Optional bandit | Only if it wins its ablation |
| 11 | Hand cones to Phase 3 | Exact region, edits confined to it |

## What to Report and Ablate

- Mapping match rate (Step 2), and TNS blocked per lock tier (Step 4).
- Selection overlap with Dr. RTL's top-K on the same designs, and final PPA from each selection method.
- Ablations: global top-K by WNS versus per-domain quotas, regions versus individual paths, region score with and without normalization, greedy versus bandit versus tabu list.
- Sensitivity to the overlap threshold, the coverage target and the budget B.

## Open Parameters

| Parameter | Suggested start | Needs |
|---|---|---|
| Near-critical margin | +100 ps | Sweep |
| Overlap threshold (Step 6) | to be chosen | Sweep |
| Budget B | 10 | Per-design rule |
| Coverage target | 80% | Sweep |
| Bandit constant c | to be chosen | Only if kept |
