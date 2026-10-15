::: IEEEkeywords
RTL optimization, large language models, formal equivalence checking,
clock-domain crossing, timing closure, agentic EDA, design automation
:::

# Introduction

Timing closure remains one of the most labor-intensive stages of the
RTL-to-GDSII flow. An engineer identifies a critical path from a static
timing analysis (STA) report, proposes a restructuring of the offending
RTL, re-runs synthesis and STA to check whether the change actually
helped, and repeats---a loop that is slow, dependent on the individual
engineer's pattern recognition, and explores only a small fraction of
the available rewrite space for any given design [@drrtl2026].

Recent work has begun automating this loop with large language models.
LLMs have been applied to Verilog code generation from natural-language
specifications [@verigen2024], to automatic syntax-error
repair [@rtlfixer2024], and, more relevant to this work, directly to
RTL-level PPA optimization: RTLRewriter partitions a design into
sub-circuits and applies LLM-guided, cost-aware Monte Carlo tree search
over rewrites [@rtlrewriter2024]; SymRTLO combines LLM rewriting with a
corpus of symbolic optimization rules [@symrtlo2025]; RTL-OPT provides
paired suboptimal and human-optimized designs for evaluating such
optimizers [@rtlopt2026]; Dr. RTL introduces a closed-loop, multi-agent
framework with a continually self-improving library of optimization
skills, evaluated on human-written designs with a commercial synthesis
and sequential-equivalence flow [@drrtl2026]; and Ares adapts the
per-call reasoning effort of such an agent to reach deeper
improvements at a fraction of its token cost [@ares2027].

These frameworks share a common correctness strategy: verify each
candidate rewrite by simulation and/or formal equivalence checking
before accepting it. This is sound for combinational and
single-clock optimization targets, which is what all of them evaluate.
It is *not* sound, without qualification, for designs with asynchronous
clock-domain crossings (CDC). Simulation and equivalence checking reason
about clean 0/1 values on a common notion of time; metastability, glitches
on a crossing, and the multi-bit skew that Gray coding exists to tolerate
are invisible to both. A rewrite can therefore pass every simulated
stimulus and a formal equivalence proof while breaking a crossing: we
show such a rewrite in Section [10.4](#sec:guardrail){reference-type="ref"
reference="sec:guardrail"}, where moving the Gray-coded write pointer of
an asynchronous FIFO from a register to combinational logic produces zero
simulation mismatches over 57,144 compared samples. Only an explicit CDC
check rejects it.

Even the benchmarks reflect this. Every design in Dr. RTL's released
dataset is synthesized against a single clock, including its FIFO, which
has two independent clock ports; in that FIFO every "synchronizer" is
clocked by the *source* domain rather than the destination, so all 142
cross-domain register paths are in fact unsynchronized
(Section [10.1](#sec:phase1res){reference-type="ref"
reference="sec:phase1res"}). A single-clock flow neither times nor
checks those paths.

[Aegis]{.smallcaps} is designed around this blind spot. Before any
generation, it recovers the clock domains from the SDC, finds every
crossing in the elaborated netlist, classifies it, and locks what its own
verifiers cannot check: synchronizer chains, the launch and capture
registers of crossings, clock-generation logic, and, unless a formal
contract proves the Gray-code property, the logic that computes a
Gray pointer's next value. Locks are enforced by checksums that survive
code motion, before any lint, simulation, or formal compute is spent.
Because a lock alone cannot see a rewrite that breaks a crossing's
protocol *next to* a locked region, every surviving candidate is
re-analyzed after generation: the crossing classification is recomputed
on the candidate netlist and every CDC contract that held on the baseline
is re-proven with SymbiYosys. Only then does the candidate reach the
equivalence gate (Yosys EQY) and STA, scored per clock domain.

## Contributions

- A netlist-level CDC shield for LLM-driven RTL optimization: crossing
  detection and classification on the elaborated design, three lock
  tiers (immutable, contract-bound, free), and checksums that are robust
  to inserted or moved code. On seven multi-clock designs it finds every
  synchronizer, Gray bus, and qualified capture and flags the 142
  unsynchronized crossings of a published benchmark.

- A post-generation CDC re-check: crossings are re-classified on every
  candidate, and auto-generated, formally calibrated CDC contracts
  (Gray stepping, handshake, pulse, qualifier; plus a structural
  registered-launch rule) are re-proven at the latency they held on the
  baseline. This catches functionally equivalent but CDC-unsafe rewrites
  that simulation passes.

- A multi-clock adaptation of the Dr. RTL closed loop
  [@drrtl2026]: per-domain region selection and quotas, a five-candidate
  generation per region within a checked edit envelope, a domain-aware
  score whose terms are normalized by each domain's period, and a
  group-relative skill library seeded from Dr. RTL's published skills.

- An evaluation protocol that separates the framework from the model and
  from the synthesis tool: an unguarded *vanilla* mode with the same model
  and budget in which every guardrail is still measured, ablations of each
  mechanism, a timing-driven synthesis-only baseline, and a mutation-based
  guardrail test suite with known ground truth. All tools are open
  source (Yosys, OpenSTA, SymbiYosys, EQY), and the code, benchmarks, and
  run logs are released.

# Related Work

## LLM-Based RTL Generation and Repair

Early work applying LLMs to hardware description languages focused on
generating RTL from natural-language or high-level specifications.
VeriGen fine-tuned open-source LLMs specifically for Verilog
generation [@verigen2024]. AutoChip closed the loop with compiler and
simulation feedback to iteratively correct generated
HDL [@autochip2023]. RTLFixer targeted automatic repair of RTL syntax
errors [@rtlfixer2024]. These systems target *generation from
specification*, not optimization of an existing, working design---a
materially different problem, since an optimizer must preserve an
existing functional contract rather than satisfy a new one.

## LLM-Guided RTL and PPA Optimization

RTLRewriter partitions designs into sub-circuits and applies LLM-aided,
cost-aware Monte Carlo tree search, reporting improvements over the
Yosys flow [@rtlrewriter2024]. SymRTLO pairs LLM rewriting with a
symbolic rule corpus for datapath and FSM optimization [@symrtlo2025].
RTL-OPT contributes 36 handcrafted tasks, each pairing a suboptimal
design with a human-optimized reference; all are single-clock
blocks [@rtlopt2026]. Dr. RTL evaluates on 20 human-written designs
(128--4,615 lines) with Synopsys Design Compiler, Nangate45 at a 0.1 ns
clock, and Cadence Jasper sequential equivalence checking, and introduces
the multi-agent loop and group-relative skill library that
[Aegis]{.smallcaps} builds on [@drrtl2026]. Ares, which postdates Dr. RTL,
raises the per-call reasoning effort only when progress stalls and
evaluates on 24 single-module designs, 19 of them from Dr. RTL's
set [@ares2027].

None of these frameworks treats clock-domain crossings as a correctness
concern distinct from functional equivalence, and none evaluates on
multi-clock designs. The closest work is the benchmark study of Xu et
al. [@xu2025], whose 153 cases include 32 clock-domain cases created by
splitting single-clock logic across two or more domains of equal or
fixed-ratio frequency, with synchronizers or asynchronous protocols
inserted as stress mutations. They find that GPT-4, Claude 3.7 Sonnet and
RTLRewriter do no better than Yosys on those cases. That study measures
PPA only; it does not check CDC correctness and does not protect
crossings during optimization.

## Formal Equivalence and CDC Verification

Yosys EQY partitions a gold and a gate design at matched signals and
proves each partition equivalent, here with SymbiYosys and
$k$-induction [@eqy]; a candidate that fails is disqualified rather than
penalized, following recent practice of using equivalence as a hard
filter [@specloop2026]. EQY's notion of equivalence is a relation
between 0/1 output sequences; for multi-clock designs, Yosys models
clocks as sampled transitions of a global clock (`clk2fflogic`), in which
every register still holds a clean value [@yosysformal]. Metastability
is therefore not representable.

Industrial CDC tools (e.g., Cadence Jasper CDC, Synopsys VC SpyGlass CDC)
go well beyond structural synchronizer recognition: they analyze
convergence and reconvergence, auto-generate protocol properties such as
data stability across the destination edge and Gray stepping, and inject
metastability in formal or simulation runs [@cadencecdc; @mvcdc2024].
Open-source CDC tooling is far less mature [@vygescdc].
[Aegis]{.smallcaps} does not replace sign-off CDC verification. It uses
the subset that can run automatically after every LLM rewrite---structural
classification and formally proven protocol contracts, with open-source
tools---to guarantee that the optimizer never makes the CDC status of a
design worse than the status it started with.

## Comparative Positioning

::: table*
  **Framework**                         **Correctness gate**                                                **CDC handling**                                                                                              **Self-improvement**                                         **Benchmarks**
  ------------------------------------- ------------------------------------------------------------------- ------------------------------------------------------------------------------------------------------------- ------------------------------------------------------------ -----------------------------------------------------------------
  RTLRewriter [@rtlrewriter2024]        Simulation; cost-aware search                                        Not addressed                                                                                                 Per-design search                                             Small/large single-clock designs
  SymRTLO [@symrtlo2025]                Symbolic rules + checking                                           Not addressed                                                                                                 Retrieval corpus                                              RTLRewriter set + additions
  RTL-OPT [@rtlopt2026]                 Combinational equivalence (benchmark)                               Not addressed                                                                                                 ---                                                           36 single-clock tasks
  Xu et al. [@xu2025]                   PPA only (benchmark study)                                          Clock-domain *mutations* in 32 cases; no CDC check                                                            ---                                                           153 cases, 32 clock-domain
  Dr. RTL [@drrtl2026]                  Jasper sequential equivalence (hard)                                Not addressed; all designs single-clock                                                                       Group-relative skill library                                  20 human-written designs
  Ares [@ares2027]                      Sequential equivalence (hard)                                       Not addressed                                                                                                 Adaptive reasoning effort                                     24 single-module designs
  **[Aegis]{.smallcaps} (this work)**   EQY (hard) after checksum, envelope, lint, multi-clock simulation   **Netlist crossing classification, three lock tiers, CDC re-check and contract re-proof on every candidate**   Group-relative library, seeded from Dr. RTL                   7 multi-clock designs (2--4 clocks) + Dr. RTL's 20
:::

# Background

## Clock-Domain Crossings and Metastability

A signal crossing from one clock domain to an asynchronously related
domain can violate the setup/hold window of the receiving flip-flop,
which then becomes metastable and may resolve to either value after an
unbounded delay. The standard mitigation is a synchronizer---most
commonly two or three flip-flops in the destination domain with no logic
between them---which bounds the probability that metastability
propagates. Multi-bit values cross either as Gray-coded pointers, where
only one bit changes per step so that a skewed sample is still a valid
neighbor value, or through a handshake or qualifier that guarantees the
data are stable when sampled. Each of these schemes has a *structural*
part (registers, no logic in the wrong place) and a *protocol* part
(at most one bit changes; data hold while the request is pending).
Neither is visible to zero-delay functional simulation, which resolves
every setup/hold violation to a definite value [@mvcdc2024], nor to
equivalence checking.

## Formal Equivalence Checking with EQY

EQY elaborates a gold and a gate design, matches signals by name,
partitions both designs at the matched signals, and proves each
partition equivalent with a configurable strategy [@eqy]. We use the
SymbiYosys strategy with $k$-induction (depth 8) and require every
partition to pass. Partitioning makes EQY fast on local rewrites, but it
also makes it conservative: a rewrite that removes or renames a register
can leave a partition unmatched, so the check fails even if the designs
are sequentially equivalent. We report such cases as failures; they
are false rejections, never false acceptances.

# System Architecture

[Aegis]{.smallcaps} operates as a six-phase closed loop
(Table [1](#tab:pipeline){reference-type="ref" reference="tab:pipeline"}).
The foundational principle is *programmatic* protection rather than
prompt-based instruction: every safety invariant is enforced by
deterministic Python and EDA-tool logic outside the model, and the LLM is
called only for region diagnosis, skill ranking, and candidate generation.

::: {#tab:pipeline}
  **Phase**   **Name**               **Primary function**
  ----------- ---------------------- --------------------------------------------------------------------------------------------------------------------------------------------
  1           Ingestion & Shield     SDC clock tree, netlist crossing detection and classification, lock tiers, CDC contracts (proved with SymbiYosys), checksums.
  2           Reasoning Engine       Per-domain OpenSTA analysis, deterministic RTL mapping, region clustering, LLM diagnosis, per-domain quotas, skill ranking.
  3           Execution Engine       Five candidates per dispatched region (C1--C5) within a checked edit envelope.
  4           Verification Node      Checksum and envelope gate, lint, LCM multi-clock differential simulation, CDC re-classification and contract re-proof.
  5           Metric Evaluator       Yosys EQY hard gate on the region's modules, synthesis and OpenSTA, domain-aware score.
  5.5         The Librarian          Group-relative confidence update, anti-patterns, failure notes for the next prompts.

  : [Aegis]{.smallcaps} optimization pipeline phases.
:::

## Phase 1: Ingestion and the Shield {#sec:phase1}

### Clock relations and constraint audit

Phase 1 parses the design's clock tree from its SDC constraints: every
master clock, every generated clock with its master and divider ratio,
and every clock group and timing exception. It builds a clock-relation
table that classifies every ordered pair of clocks as *identical*,
*related* (a master and a clock generated from it, or two clocks generated
from the same master), or *asynchronous*. It then audits the constraints on
every asynchronous pair: the pair should either be declared exclusive
with `set_clock_groups -asynchronous` or have its crossings bounded with
`set_max_delay -datapath_only`. Pairs with neither, and multi-bit Gray
buses covered by a clock group or false path (whose bit skew is then
unbounded), are written to a *constraint-audit report*, to which Phase 2
later adds every asynchronous path that STA flags as violating
(Section [4.2.2](#sec:crossing){reference-type="ref"
reference="sec:crossing"}). A violation on an asynchronous crossing is a
constraint or CDC-integration issue rather than an RTL timing defect,
and [Aegis]{.smallcaps} never attempts to fix it by rewriting RTL.

### Crossing detection and classification

Crossings are found on the elaborated, flattened netlist (Yosys `proc`,
`flatten`, `opt_dff`), not on the source text, so that hierarchy,
naming, and coding style do not matter. `opt_dff` folds synchronous
resets and enables into the flip-flop cell, so a reset multiplexer in front
of a synchronizer stage does not hide a direct register-to-register
connection. Every flip-flop is assigned the SDC clock that drives it. For
every flip-flop, the combinational fan-in cone is traced back to source
flip-flops; a source in a clock domain asynchronous to the destination's
makes the pair a *crossing*. Crossings are classified as:

- *synchronizer*: the destination is driven directly by the source
  (no logic) and is followed by at least one more flip-flop in the same
  domain whose only input is its output;
- *gray candidate*: as above, for a multi-bit source;
- *qualified capture*: the destination's data or enable fan-in includes
  the output of a synchronizer (data captured under a synchronized
  qualifier, as in a handshake);
- *insufficient depth*: a single synchronizing flip-flop;
- *unsynchronized*: anything else.

The last two are reported as pre-existing CDC issues. [Aegis]{.smallcaps}
optimizes such designs but never makes the classification worse.

### Lock tiers

Every source statement is assigned one of three tiers:

- **Immutable.** Synchronizer flip-flops (the whole always block), flops
  marked `ASYNC_REG`/`keep`, clock-divider flops, `parameter`
  declarations, the launch and capture registers of every crossing that is
  not contract-bound, and---for a Gray candidate without a proven
  contract---every statement in the fan-in of the launch register. The
  last rule matters: without it, an LLM could rewrite the logic that
  computes the next Gray value into a binary increment while leaving the
  locked register untouched.

- **Contract-bound.** The fan-in logic of crossings whose CDC contract
  is proven on the baseline. Gray candidates get a contract automatically
  when the pointer is a port of a module with a reset; handshake, pulse,
  and qualifier crossings get one from an annotation file. A contract is
  a set of single-clock properties generated from templates (e.g., G1/G2:
  the pointer changes by at most one bit per clock and only on an
  increment; H1--H3: data stable while a request is pending), wrapped
  around the scope module and proven with SymbiYosys ($k$-induction, with
  a PDR fallback). Templates with a latency parameter are *calibrated*:
  the smallest latency at which the contract holds on the baseline is
  recorded, and candidates must prove the contract at that same latency.
  A contract that fails on the baseline is reported as a pre-existing
  issue and its logic stays immutable. Contract-bound crossings also
  carry the structural rule R4 (*registered launch*): every bit that
  crosses must be driven directly by a source-domain flip-flop, since a
  combinational launch can glitch, and no value-level property can see a
  glitch.

- **Free.** Everything else.

Clock dividers are immutable for a separate reason: divider ratios
determine the generated-clock periods in the SDC, so changing one would
silently invalidate every subsequent STA number.

### Checksum enforcement

For every immutable register, a SHA-256 digest is computed over its
normalized source (comments and whitespace removed): over the whole
always block for synchronizers and clock generation, and over the
register's own assignments for launch and capture registers. Parameter
declarations and locked Gray fan-in lines are hashed per statement. The
digests do not include line numbers. To check a candidate,
[Aegis]{.smallcaps} re-elaborates it, finds each locked register by name
through the source-location attributes Yosys attaches to cells, and
recomputes its digest; statement-level digests must appear somewhere in
the candidate. A candidate is rejected if a locked register is missing,
if any digest differs, or if the SDC file changed. Code inserted or
deleted elsewhere in a file leaves every digest unchanged. The check runs
before any lint, simulation, or formal compute and does not rely on the
LLM to report its own compliance.

## Phase 2: Reasoning Engine (Region Selection) {#sec:phase2}

Phase 2 decides where the optimizer works. Prior agentic flows rank a
global list of $K$ paths by slack [@drrtl2026], which suits single-clock
designs. In a multi-clock design this fails for three reasons. First,
slack in nanoseconds is not comparable across clock periods: $-0.2$ ns
on a 1 ns clock is a more severe violation than $-0.5$ ns on a 10 ns
clock, yet ranks lower. Second, near-critical paths from one domain can
fill every slot and starve the others. Third, many paths through one
structure, such as a multiplier, are a single optimization problem
rather than many.

[Aegis]{.smallcaps} therefore selects *regions*: groups of violating
endpoints in the same capture domain whose combinational fan-in cones
overlap. Regions are scored and allocated per domain using the same
domain weights and the same $\alpha$/$\beta$ schedule as the score of
Eq. [\[eq:score\]](#eq:score){reference-type="eqref"
reference="eq:score"}, so that selection targets what the score rewards.
The analysis is recomputed from the current baseline $B_n$ at every
iteration. The only state carried between iterations is the per-region
attempt record of Section [4.2.8](#sec:dispatch){reference-type="ref"
reference="sec:dispatch"}, which is logged explicitly.

### Endpoint collection and margin deficit {#sec:collection}

OpenSTA is run on a hierarchy-preserving synthesis of $B_n$, with FSM
re-encoding disabled, and reports WNS, TNS, and per-module cell area.
For each capture clock, it also reports the worst setup path to every
endpoint whose slack $s_e$ falls below a closure margin $m$. Only one
path is kept per endpoint, matching OpenSTA's endpoint-based definition
of TNS, so that no endpoint's slack is counted twice. Each endpoint $e$
is tagged with its capture clock $d(e)$, the domain whose period it must
meet, and with the launch clock of its worst path. Severity is measured
as the deficit against the margin, $$\begin{equation}
\delta_e = \max\left(0,\; m - s_e\right),
\label{eq:deficit}
\end{equation}$$ so that near-critical endpoints with small positive
slack contribute in proportion to how far they fall short of the margin.
With $m = 0$, the deficit reduces to the magnitude of negative slack.
The same margin $m$ defines timing closure throughout the pipeline .

### Crossing classification {#sec:crossing}

Each endpoint is classified by comparing the launch and capture clocks
of its worst path against the Phase 1 clock-relation table
(Table [2](#tab:crossing){reference-type="ref"
reference="tab:crossing"}). This step needs only the clock names in the
report, so it runs before the more expensive RTL mapping. Asynchronous
endpoints go to the constraint-audit report and are excluded from all
subsequent steps, so they cannot inflate any domain's deficit or weight.
Endpoints on related-clock paths are tagged as latency-sensitive.

::: {#tab:crossing}
  **Launch/capture relation**            **Disposition**
  -------------------------------------- ------------------------------------------------------------
  Identical clocks                       Optimization target
  Related clocks                         Optimization target; tagged latency-sensitive
  Asynchronous, no exception             Constraint-audit report (missing exception); excluded
  Asynchronous, `-datapath_only` bound   Constraint-audit report (CDC bus-skew violation); excluded

  : Crossing classification and disposition.
:::

### Deterministic RTL mapping

Each remaining endpoint is mapped to the RTL register that drives it.
Where they survive technology mapping, the source-location attributes
Yosys attaches to inferred registers are used directly. Otherwise,
register names are normalized by stripping hierarchy prefixes and
register suffixes and undoing bit-index renaming. The endpoint's cone
$\mathcal{C}(e)$ is then computed on the pre-synthesis design (Yosys
after `proc`) as the set of source statements in the combinational
fan-in of that register, back to registers or primary inputs. The
declarations and module context needed to read those statements are
recorded separately for prompting. A cone is generally not one
contiguous line range; it may span several always blocks, functions, and
modules.

Synthesis can merge, retime, or re-encode registers, or absorb them into
inferred memories, so some endpoints fail to map. These endpoints are
logged and excluded, and the resulting match rate is reported in
Section [10](#sec:results){reference-type="ref" reference="sec:results"}
as direct evidence for the determinism of the mapping.

### Lock filtering

Each cone is intersected with the locked set $\mathcal{L}$. An endpoint
whose cone lies entirely inside $\mathcal{L}$ is dropped, and its
deficit is recorded as *blocked* under the corresponding lock category.
An endpoint whose cone only partly overlaps $\mathcal{L}$ is kept, with
the locked statements removed from its editable cone, and is tagged
*lock-adjacent*. We report the blocked deficit per lock category in
Section [10](#sec:results){reference-type="ref"
reference="sec:results"}; it is the direct cost of the guardrail.

For each capture domain $d$, let $E_d$ be the set of endpoints that
survive classification, mapping, and lock filtering. The domain's worst
and total deficits are $$\begin{equation}
\Delta^{\max}_d = \max_{e \in E_d} \delta_e, \qquad
\Delta^{\Sigma}_d = \sum_{e \in E_d} \delta_e .
\label{eq:domaindeficit}
\end{equation}$$

### Region clustering

Endpoints within each domain are clustered into regions by cone overlap.
For endpoints $e_i, e_j \in E_d$, overlap is measured with the overlap
coefficient $$\begin{equation}
\mathrm{ov}(e_i, e_j) =
\frac{\left|\mathcal{C}'(e_i) \cap \mathcal{C}'(e_j)\right|}
{\min\left(\left|\mathcal{C}'(e_i)\right|, \left|\mathcal{C}'(e_j)\right|\right)},
\label{eq:overlap}
\end{equation}$$ which, unlike the Jaccard index, merges a small cone
nested inside a larger one. Here $\mathcal{C}'(e)$ is the cone with
control nets of fanout above $\varphi$ (shared enables, resets, valid
signals, mux selects) removed. These nets appear in nearly every cone
and would otherwise chain unrelated logic into a single region. They are
removed only for the overlap test and remain in the cone handed to the
LLM. Pairs with $\mathrm{ov} \ge \theta$ are merged with union-find. A
merge is skipped if the resulting region would exceed a size cap
$S_{\max}$ chosen so that each region fits in one prompt . Because the
unit of clustering is the endpoint, every endpoint belongs to exactly
one region, and no endpoint's deficit is counted in two regions.

### Root-cause diagnosis and amenability

Each region is diagnosed with a single LLM call rather than one call per
path. The call receives the region's cone, endpoints, slacks, and tags,
and returns, for every endpoint, a root cause drawn from long
combinational depth, wide fan-in/fan-out, complex arithmetic (adder,
multiplier, and comparator chains), control--data coupling, and
reconvergent fanout, together with an *amenability* label
(Table [3](#tab:amenability){reference-type="ref"
reference="tab:amenability"}) stating whether the optimizer can safely
act on it. Latency changes on endpoints tagged latency-sensitive are
always labeled *sequential-unsafe*. Labels are cached under the region's
endpoint set and a hash of its cone statements, so re-analyzing an
unchanged region reproduces its labels exactly.

::: {#tab:amenability}
  **Category**          **Description**                 **Action**
  --------------------- ------------------------------- ------------
  *combinational*       Logic restructuring             Can fix
  *sequential-safe*     Retiming, no latency change     Can fix
  *sequential-unsafe*   Requires latency change         Skip
  *out-of-scope*        Needs constraints or redesign   Skip

  : Amenability classification and optimizer disposition.
:::

The analyzer runs no synthesis or verification tools. It emits a
structured per-iteration diagnosis log recording the base and target
versions, the margin $m$, the per-domain quotas, the constraint-audit
entries, the unmapped endpoints and, for each region, its endpoints,
deficits, root causes, amenability labels, lock tags, and attempt
record. Optimization and result fields are left unpopulated at this
stage and filled by downstream phases, which keeps diagnosis strictly
decoupled from remediation.

### Region scoring and per-domain allocation

Domain $d$ is weighted by $w_d = f_d / f_{\max}$, the ratio of its
frequency to that of the fastest domain. This makes $w_d \cdot \delta$
proportional to the deficit as a fraction of the clock period, and it is
the same $w_d$ used in
Eq. [\[eq:score\]](#eq:score){reference-type="eqref"
reference="eq:score"}.

Let $E^{a}_r$ be the endpoints of region $r$ labeled *combinational* or
*sequential-safe*. With $\Delta^{\max}_r$ and $\Delta^{\Sigma}_r$ the
worst and total deficit over $E^{a}_r$, defined as in
Eq. [\[eq:domaindeficit\]](#eq:domaindeficit){reference-type="eqref"
reference="eq:domaindeficit"}, region $r$ in domain $d$ is scored as
$$\begin{equation}
P_r = \alpha\,\frac{\Delta^{\max}_r}{\Delta^{\max}_d}
    + \beta\,\frac{\Delta^{\Sigma}_r}{\Delta^{\Sigma}_d},
\label{eq:regionscore}
\end{equation}$$ where $\alpha$ and $\beta$ are the current iteration's
values from the adaptive schedule
(Table [5](#tab:schedule){reference-type="ref"
reference="tab:schedule"}). Normalizing each term by its own domain
total keeps both ratios in $[0,1]$. Without this normalization, the
total-deficit term, which grows with the number of violating endpoints,
would swamp the worst-deficit term and make $\alpha$ ineffective.
Restricting both terms to amenable endpoints means a region whose worst
endpoint needs a latency change is not ranked as if it were fixable. The
excluded deficit is logged as *unreachable* and reported alongside the
blocked deficit.

A budget of $B$ regions is distributed across the $n_v$ domains with
nonzero deficit. Every such domain receives one guaranteed slot, and the
remainder is split by weighted total deficit: $$\begin{equation}
Q_d = 1 + \left(B - n_v\right)
\frac{w_d\,\Delta^{\Sigma}_d}{\sum_{i} w_i\,\Delta^{\Sigma}_i}.
\label{eq:quota}
\end{equation}$$ Quotas are rounded with the largest-remainder method
and capped at the number of regions available in each domain, with
leftover slots passed to the remaining domains. If $n_v > B$, slots are
assigned in decreasing order of $w_d\,\Delta^{\Sigma}_d$. $B$ is set per
design from the number of violating regions .

Within each domain, regions with $P_r > 0$ that are not marked tabu
(Section [4.2.8](#sec:dispatch){reference-type="ref"
reference="sec:dispatch"}) are taken in decreasing order of $P_r$ until
either the quota is filled or the selected regions cover a fraction
$\rho$ of $\Delta^{\Sigma}_d$ . The per-domain lists are then merged
into a single ranked queue by repeatedly taking the list head with the
largest $w_d\,\Delta^{\Sigma}_r$. This preserves the $P_r$ ordering
within each domain while ordering regions from different domains by
weighted absolute impact.

### Dispatch and region tabu {#sec:dispatch}

The queue ranks candidate regions; it is not handed to the generator as
a single batch. Each iteration dispatches the first $R$ regions in the
queue that are pairwise disjoint, preferring regions in different
modules . Each dispatched region receives its own five-candidate
generation (Phase 3), its own skill match, and its own scoped
equivalence check. This keeps the EQY scope to one subtree per region,
prevents one failed region from discarding the progress on another, and
lets the Librarian attribute each outcome to a single pattern--strategy
pair.

The skill-rank exclusion and temperature escalation of
Section [\[sec:stall\]](#sec:stall){reference-type="ref"
reference="sec:stall"} are applied per region. A region keyed by its
endpoint register set that fails to promote is redispatched with Rank-3
and Rank-4 skills and an escalated $T_5$. A region that fails to promote
a second time is marked tabu for the remainder of the run, and the queue
advances. A region's attempt record is reset whenever a rewrite of that
region is promoted.

### Area-recovery mode

Once every domain meets the margin, so that $\Delta^{\Sigma}_d = 0$ for
all $d$, the timing queue is empty. This is also the point at which the
adaptive schedule shifts weight to area. When the schedule is in a
timing-met stage, regions that still carry deficit are dispatched first,
and the remaining dispatch slots are filled with area targets. Area
targets are leaf modules whose minimum endpoint slack exceeds $m$ by a
headroom $h$, ranked by cell area. The editable region is the module's
unlocked statements, split along always and continuous-assignment blocks
when the module exceeds $S_{\max}$. Any area candidate that pushes an
endpoint below $m$ is rejected regardless of its score .

### Skill library lookup

Each dispatched region keys into a skill library on its dominant root
cause, the one carrying the largest share of the region's amenable
deficit. The library has 65 entries. Entries 1--47 are Dr. RTL's published
pattern$\rightarrow$strategy pairs [@drrtl2026], of which Dr. RTL itself
marks 13 as "do not use"; entries 48--65 were added for
[Aegis]{.smallcaps}, including four for contract-bound CDC logic (for
example, keeping a binary register beside a Gray register, or comparing
directly on Gray codes) and several "do not use" entries that describe
CDC-breaking rewrites. In total, 41 entries are usable (11 high, 21
medium, 5 low confidence, 4 CDC contract-bound) and 24 are quoted to the
generator only as warnings. Each usable entry has a confidence score
$S_{\mathrm{conf}}$, initialized from its section (0.8, 0.5, 0.3), and the
Librarian keeps a per-root-cause anti-pattern list. Eligibility is
deterministic: an entry is eligible if it addresses one of the region's
root causes, is not an anti-pattern for it, has not already been tried on
the region, and, for the CDC entries, the region is contract-bound. An
LLM then ranks the eligible entries for the region and proposes a
direction for the zero-shot candidate; a ranking that names an
ineligible entry is rejected by the tool.

## Phase 3: Execution Engine (Parallel Generation) {#sec:phase3}

For each dispatched region $r$, the orchestrator issues five parallel LLM
calls. Each call receives the region's endpoints, slacks, root causes
and amenability labels, the assigned skill (pattern, strategy, example),
the warnings that apply to the region's tags, the Librarian's recent
failure notes for the root cause, and the source of every module that
contains the region with each line tagged *editable*, *locked*, or
*context*:

- **C1, C2.** The top-ranked skill: a direct application, and a
  structurally different variant of it.

- **C3, C4.** The second-ranked skill: conservative and bolder.

- **C5.** No skill: a latency-preserving structural rewrite following
  the ranker's direction (restructuring, resource sharing, retiming within
  the editable lines; never pipelining).

The slots are also assigned sampling temperatures $T = 0.1, 0.7, 0.3, 0.8$
and $T_5 = 0.5 + 0.1 \times$ (attempts on this region). Temperatures are
applied only where the backend supports them: current frontier Claude
models (Opus 5.5, Sonnet 5.5) reject non-default sampling parameters, and
the command-line backend used for the reported runs exposes none, so in
those runs candidate diversity comes from the slot roles and skills alone.
Every LLM call logs whether the requested temperature was applied. The
model returns complete rewritten modules; the orchestrator splices them
into copies of the baseline files, leaving every other byte unchanged.

### Edit envelope

Each candidate may edit only within the region's edit envelope,
$$\begin{equation}
\mathcal{E}(r) = \left(\mathcal{C}(r) \cup \mathcal{A}(r) \cup
\mathcal{D}_{\mathrm{new}}\right) \setminus \mathcal{L},
\label{eq:envelope}
\end{equation}$$ where $\mathcal{C}(r)$ is the union of the region's
editable cones, $\mathcal{A}(r)$ is the set of always blocks that assign
its endpoint registers, $\mathcal{D}_{\mathrm{new}}$ covers new
declarations and logic driving new signals inside the region's modules,
and $\mathcal{L}$ is the immutable set. The envelope is enforced, not
requested: the candidate is diffed against the baseline line by line after
normalization, every changed or deleted baseline statement must lie in
$\mathcal{C}(r) \cup \mathcal{A}(r)$, insertions must lie inside the
region's modules, and the elaborated module set and every module's port
list must be identical. Together with the checksum test, this runs before
any lint or simulation.

### Composing per-region winners

After Phases 4 and 5, let $W^{(r)}_n$ be the best-scoring candidate for
region $r$ that passed every check. Winners whose modules do not overlap
are applied together to $B_n$; the composed design is re-verified
(gate, lint, simulation, CDC) and re-timed. Because the modules are
disjoint and each was proven equivalent to its baseline module, the
composition needs no new equivalence proof. If the composed design scores
worse than the best single-region winner, which can happen when regions
interact through shared timing, the best single winner is used instead.
The selected design is the iteration winner $W_n$ in
Eq. [\[eq:promotion\]](#eq:promotion){reference-type="eqref"
reference="eq:promotion"}.

## Phase 4: Verification Node (Fast Pre-Filter)

Surviving candidates pass a sequential cascade, stopping at the first
hard failure:

1.  **Gate.** The checksum test and the edit-envelope test above.

2.  **Lint.** Icarus Verilog and Verilator. Only linters that accept the
    unmodified baseline are used, so a benchmark that already triggers a
    linter does not reject every candidate.

3.  **LCM multi-clock differential simulation.** Baseline and candidate
    are elaborated and flattened by Yosys and simulated side by side on
    identical random stimulus. Every SDC clock that is a top-level port is
    driven at its own period; all half-periods are made even and inputs
    change only at odd times, so no input change coincides with a clock
    edge. Resets are held for four periods of the slowest clock. The run
    length is
    $$\begin{equation}
    T_{\mathrm{sim}} = \max\!\left(\mathrm{LCM}\!\left(T_{\mathrm{clk}1},\dots,
    T_{\mathrm{clk}N}\right) \times K_{\mathrm{cycles}},\;
    200\,T_{\max}\right),
    \end{equation}$$ with $K_{\mathrm{cycles}} = 4$, capped at 60,000
    stimulus steps, for two seeds. Every output bit whose baseline value is
    known is compared at every step.

4.  **CDC re-check.** Phase 1 is re-run on the candidate. The candidate is
    rejected if it has a new unsynchronized or single-flop crossing, if any
    synchronizer, Gray, or qualified crossing of the baseline disappears or
    loses synchronizer depth, or if any contract proven on the baseline is
    no longer proven at the same latency. This is the stage that catches
    rewrites which are functionally equivalent but CDC-unsafe.

Each candidate also receives a graded score, the fraction of checks
passed (simulation counted per compared sample), which the Librarian
uses. A simulation mismatch proves non-equivalence, so it is a hard
failure rather than a soft penalty.

## Phase 5: Metric Evaluator

Each surviving candidate is checked for equivalence with the baseline
$B_n$ by Yosys EQY, one job per module that contains the region's edit
envelope (memories are mapped to flip-flops on both sides, since the
SymbiYosys back end does not reason about memory cells inside a
partition). This is a *hard gate*: a candidate passes only if every
partition of every scope proves equivalent; FAIL, ERROR, or timeout all
disqualify it, and failing candidates never enter the weighted score.
Scoping to modules keeps the check tractable, but the guarantee holds for
those modules at their default parameter values; we state this as a
limitation. Eligible candidates are synthesized with the same flow as the
baseline, timed with OpenSTA, and scored per
Section [7](#sec:scoring){reference-type="ref" reference="sec:scoring"}.

## Phase 5.5: The Librarian (Skill Library Update)

Scores are relative to the current baseline, which therefore scores 0,
so the improvement of candidate $k$ is
$\Delta_k = \mathrm{Score}_k - \mathrm{Score}(B_n) = \mathrm{Score}_k$
(lower is better). Within each region's group of eligible candidates, the
group-relative advantage is
$$\begin{equation}
A_k = \frac{\overline{\Delta} - \Delta_k}{\sigma_\Delta},
\end{equation}$$ which decouples the update from how hard the region is.
A skill whose candidate improved on the baseline ($\Delta_k < 0$) with
$A_k \ge 0$ gains $\delta = 0.05$ confidence ($2\delta$ if it produced the
promoted winner); one that did not improve and fell below the group mean
loses $\delta/2$. A candidate rejected by a correctness check (lock,
envelope, ports, lint, simulation mismatch, CDC, or EQY) costs its skill
$\delta$; two such failures for a root cause with no success make the
skill an anti-pattern for that root cause. Rejection reasons are kept per
root cause and quoted in the next prompts, so guidance improves within a
run; with a shared library, it carries forward to the next design.

## Termination and Instrumentation

The loop stops after $N_{\max} = 5$ iterations, when no region can be
dispatched (all regions tabu or every domain meets the margin), or when
two consecutive iterations improve the score by less than
$\varepsilon = 10^{-3}$. Every LLM call (tokens, latency, cost, applied
temperature), every candidate's verification record, and every
iteration's selection are logged; all tables in
Section [10](#sec:results){reference-type="ref" reference="sec:results"}
are generated from these logs by a script.

# Locking Rationale

The three tiers answer three different questions. *Immutable* logic is
logic whose correctness [Aegis]{.smallcaps}'s verifiers cannot establish
at all: a synchronizer rewritten into a single flop, or a launch register
turned into combinational logic, is still functionally equivalent, so
neither simulation nor EQY can object. *Contract-bound* logic is logic
whose CDC correctness can be stated as a property and proven on every
candidate; locking it would forgo optimizations (an incrementer feeding
a Gray pointer is often on the critical path) that the contract makes
safe. *Free* logic is covered by simulation and EQY. Clock dividers are
immutable for a different reason---SDC validity---which is a scope
decision that could be relaxed with SDC regeneration, not a claim that
divider optimization is unsafe.

# Baseline Promotion and Stall Recovery {#sec:promotion}

## Promotion Rule

Let $B_n$ denote the baseline entering iteration $n$, and $W_n$ the
iteration winner. Since scores are relative to $B_n$, which scores 0,
$$\begin{equation}
B_{n+1} =
\begin{cases}
W_n & \text{if } \mathrm{Score}(W_n) < 0\\
B_n & \text{otherwise (stall).}
\end{cases}
\label{eq:promotion}
\end{equation}$$ A winner that ties or regresses never overwrites the
baseline, including in the first iteration.

## Per-Region Stall Detection and Skill Exclusion {#sec:stall}

Stall recovery is per region, keyed by the region's endpoint set. A
region that is dispatched and not promoted has its attempt count
incremented and the skills it used recorded. When it is dispatched again,
the skills already tried are ineligible, so C1--C4 receive the next-ranked
entries (the Rank-3/Rank-4 substitution), and C5's temperature target is
raised:
$$\begin{equation}
T_5^{(a)} = \min\!\left(0.5 + 0.1\,a,\; 1.0\right),
\end{equation}$$ for attempt $a$. A region that fails to promote twice is
marked tabu for the rest of the run, and its record is reset whenever a
rewrite of it is promoted.

# Domain-Aware Dynamic Penalty Scoring {#sec:scoring}

## Deficits

For each capture clock $d$ and closure margin $m$, the worst and total
deficits of a design are computed from its per-endpoint setup slacks
$s_e$ over all endpoints whose launch and capture clocks are not
asynchronous (the same rule as region selection):
$$\begin{equation}
D^{\max}_d = \max_e \max(0, m - s_e), \qquad
D^{\Sigma}_d = \sum_e \max(0, m - s_e).
\end{equation}$$

## Scalar Baseline Formulation

The natural formulation, used by Dr. RTL, aggregates design-level
metrics into one score,
$$\begin{equation}
\mathrm{Score} = a\,\mathrm{WNS}^{\mathrm{norm}} + b\,\mathrm{TNS}^{\mathrm{norm}}
+ c\,\mathrm{Area}^{\mathrm{norm}} + 0.5\,[\mathrm{Area}^{\mathrm{norm}} > 0.1],
\label{eq:scalar}
\end{equation}$$ with $(a,b,c) = (0.5, 0.35, 0.15)$ and each term
normalized against the baseline. In a multi-clock design this can hide a
regression in a fast domain behind slack in a slow one, and it compares
nanoseconds across periods. We use it only as an ablation.

## Domain-Aware Formulation

$$\begin{equation}
\begin{aligned}
\mathrm{Score}_i = {} & \frac{\sum_{d} w_d \left( \alpha\,
\mathrm{W}_{i,d} + \beta\,\mathrm{T}_{i,d}
\right)}{\sum_d w_d} + \gamma\, f\!\left(A_i\right) + P_{\mathrm{CDC}} + P_{\mathrm{SEC}},\\
\mathrm{W}_{i,d} = {} & \frac{D^{\max}_{d}(i) - D^{\max}_{d}(B)}{\max\left(D^{\max}_{d}(B),\, 0.01\,T_d\right)},
\quad
\mathrm{T}_{i,d} = \frac{D^{\Sigma}_{d}(i) - D^{\Sigma}_{d}(B)}{\max\left(D^{\Sigma}_{d}(B),\, 0.01\,T_d\right)},
\end{aligned}
\label{eq:score}
\end{equation}$$ where $B$ is the current baseline,
$A_i = (\mathrm{Area}_i - \mathrm{Area}_B)/\mathrm{Area}_B$, and
$w_d = f_d / f_{\max}$.

- **Per-domain normalization.** Each domain's change is measured
  relative to that domain's own baseline deficit (floored at 1% of its
  period), so a regression in one domain cannot be masked by slack in
  another, and the same $w_d$ is used to allocate regions in Phase 2.

- **Smooth area penalty.**
  $$\begin{equation}
  f(A) =
  \begin{cases}
  A, & A \le 0.05\\
  A + \lambda (A - 0.05)^2, & A > 0.05,
  \end{cases}
  \end{equation}$$ with $\lambda = 10$, tolerating minor area overhead
  while steeply penalizing runaway growth.

- **Disqualifying penalties.** $P_{\mathrm{CDC}}$ and $P_{\mathrm{SEC}}$
  ($10^4$) encode the Phase 4 and Phase 5 hard gates in the same
  expression. They are a backstop; in normal operation such candidates
  never reach scoring.

## Adaptive $\alpha/\beta/\gamma$ Schedule

[Aegis]{.smallcaps} schedules $\alpha$, $\beta$, $\gamma$ across the
five-iteration budget (Table [2](#tab:schedule){reference-type="ref"
reference="tab:schedule"}), gated on whether every domain meets the
margin. In the final iteration, a candidate that increases the worst
deficit of any domain is rejected regardless of its composite score.

::: {#tab:schedule}
  **Stage**                         $\boldsymbol{\alpha}$   $\boldsymbol{\beta}$   $\boldsymbol{\gamma}$  **Intent**
  -------------------------------- ----------------------- ---------------------- ----------------------- ----------------------------------------------------
  Iteration 1                               0.60                    0.30                   0.10           Aggressive worst-deficit reduction
  Iteration 2                               0.50                    0.40                   0.10           Shift weight to total deficit
  Iteration 3 (all domains met)             0.35                    0.25                   0.40           Area recovery
  Iteration 3 (some domain not met)         0.55                    0.35                   0.10           Stay in timing mode
  Iterations 4--5 (met)                     0.30                    0.20                   0.50           PPA refinement
  Iterations 4--5 (not met)                 0.70                    0.30                   0.00           Freeze area; last structural fixes

  : Adaptive $\alpha/\beta/\gamma$ schedule.
:::

# Implementation Notes

Before settling on the current implementation, we explored three
realizations with progressively different levels of LLM autonomy. A
LangGraph of reasoning, synthesis, verification, and evaluation nodes,
with an orchestrator agent choosing the next action, made tool execution
non-reproducible and safety invariants hard to enforce. Coding-agent
harnesses (Codex CLI, OpenCode, Antigravity CLI) with the workflow
specified in Markdown agent files gave the model more freedom but more
nondeterminism, and the agent often stopped early when only marginal
improvements remained.

The final system is a Python orchestrator (about 4,000 lines of Python
including the Phase 1--2 tools). Deterministic code controls the pipeline,
verification gates, promotion, and termination; the LLM is invoked only
for region diagnosis, skill ranking, and candidate RTL, with the system
prompts taken from the same Markdown agent definitions, so the loop can
also be driven interactively from Claude Code. LLM backends are pluggable:
the Anthropic API, any OpenAI-compatible endpoint for open-weight models,
and the Claude Code command line, which was used for all reported runs.
No invariant depends on the model's compliance with an instruction.

# Experimental Setup

## Benchmarks

We use two suites (Table [3](#tab:benchmarks){reference-type="ref"
reference="tab:benchmarks"}); sources, licenses, and wrappers are listed
in the artifact.

**Multi-clock suite (7 designs, 2--4 clocks).** Six open-source designs:
a Cummings-style asynchronous FIFO (`async_fifo`, MIT) [@dpretetfifo]; the
ZipCPU asynchronous FIFO (`afifo`, Apache-2.0) [@wb2axip]; an AXI-Stream
asynchronous frame FIFO (`axis_async_fifo`, MIT, 32 entries via a wrapper)
and an AXI-Lite clock-domain bridge (`axil_cdc`, MIT) [@forencich]; a
three-clock 1G Ethernet MAC with RX/TX FIFOs (`eth_mac_1g_fifo`, MIT,
64-entry FIFOs via a wrapper) [@forencich]; and Dr. RTL's FIFO constrained
with both of its clocks (`drrtl_fifo_2clk`) [@drrtl2026]. A seventh,
`soc`, is a small four-clock test system we wrote (asynchronous FIFO with
Gray pointers, request/acknowledge handshake, pulse synchronizer, clock
divider, and two deliberately unsynchronized crossings). Clock periods
are calibrated per domain to 75% of the critical-path delay under the
synthesis-only flow, so every domain violates timing.

**Single-clock suite (20 designs).** Dr. RTL's released dataset, unchanged,
at Dr. RTL's 0.1 ns clock. Dr. RTL constrains input-to-output paths to
one period with `set_max_delay`; we use zero input and output delays
against the clock, which constrains the same paths and also
input-to-register and register-to-output paths.

::: {#tab:benchmarks}
  **Design**            **Clocks**   **FF cells**   **Sync**   **Gray**   **Qual.**   **Unsync.**   **Contracts**   **WNS raw**   **WNS synth**   **TNS synth**   **Area synth ($\mu$m$^2$)**
  ------------------- ------------ -------------- ---------- ---------- ----------- ------------- --------------- ------------- --------------- --------------- -----------------------------
  `soc`                          4             29          3          2           1             2               2         -0.38           -0.38           -3.34                         1,147
  `async_fifo`                   2             12          0          2           0             0               2         -0.16           -0.16           -2.87                         1,387
  `afifo`                        2             10          0          2           0             0               0         -0.17           -0.15          -11.21                         1,341
  `axis_async_fifo`              2             52          7          2           1             0               0         -0.50           -0.24          -25.86                         3,786
  `axil_cdc`                     2             44          4          0           9             0               0         -1.07           -0.09          -18.73                         2,041
  `eth_mac_1g_fifo`              3            127         12          3           2             0               0         -2.39           -0.33          -48.29                        15,108
  `drrtl_fifo_2clk`              2            145          0          0           0           142               0         -0.31           -0.20           -6.86                        35,928

  : Multi-clock suite: Phase 1 crossing classification and the two synthesis baselines (Nangate45, ns). FF cells are multi-bit flip-flop cells after elaboration. Contracts = Gray contracts proven automatically.
:::

## Tooling

Synthesis uses Yosys 0.67 with the Nangate45 open cell library (typical
corner). The *raw* flow maps with ABC's default area-oriented script; the
*synthesis-only* flow uses a timing-driven ABC script (delay-targeted
mapping at the fastest clock period, buffering, gate up- and down-sizing),
and every [Aegis]{.smallcaps} and vanilla design is measured with this
synthesis-only flow, so reported gains are gains over what the synthesis
tool finds on its own. STA uses OpenSTA 3.1.0; contracts use SymbiYosys
0.67 with Z3 5.1.0; equivalence uses Yosys EQY with the SymbiYosys
strategy; linting and simulation use Icarus Verilog 12.0 and Verilator
5.044. Power is not reported, since no activity-based power analysis was
run. Dr. RTL's own results were obtained with Design Compiler and Jasper;
we do not compare against its published numbers but re-measure all
designs in one flow.

## Models Evaluated

The generator is accessed through the Claude Code command line
(version 2.1.286, accessed October 2026) with Claude Sonnet 5.5
(`claude-sonnet-5-5`) for the main experiments, and Claude Opus 5.5
(`claude-opus-5-5`) and Claude Haiku 4.5 (`claude-haiku-4-5`) for the
cross-model study. Each model runs in two modes: (i) *vanilla*, in which
the model receives the RTL, per-domain timing, and the five worst paths
and returns a rewrite, with no locks, skill library, envelope, or gating,
and the best-scoring synthesizable candidate is promoted; and (ii)
*$+$[Aegis]{.smallcaps}*. Both modes use five candidates per iteration,
five iterations, and the same measurement flow, and every guardrail is
still *measured* in vanilla mode, so the comparison isolates the framework
rather than the prompt.

## Protocol and Reporting

Each configuration runs for up to $N_{\max} = 5$ iterations with five
candidates per dispatched region and up to three regions per iteration.
We report the synthesis-only baseline and the optimized result, the
fraction of candidates that pass EQY, the number of candidates that
modified locked logic or regressed a crossing (measured in every mode),
LLM tokens, and wall-clock time. Each configuration is repeated with
independent runs and reported as mean $\pm$ standard deviation; the number
of runs is given with each table. Ablations disable one mechanism at a
time: (a) locks (checksum measured but not enforced), (b) the skill
library (five zero-shot candidates), (c) the domain-aware score (scalar
score of Eq. [\[eq:scalar\]](#eq:scalar){reference-type="eqref"
reference="eq:scalar"}), (d) stall recovery, and (e) the Phase 4 CDC
re-check (measured but not enforced).

# Results {#sec:results}

## Phase 1 on the Multi-Clock Suite {#sec:phase1res}

Table [3](#tab:benchmarks){reference-type="ref"
reference="tab:benchmarks"} shows the crossing classification. On the six
designs whose synchronizers are correct, Phase 1 classifies every crossing
as a synchronizer, Gray bus, or qualified capture and reports none as
unsynchronized. On `soc`, it finds exactly the two crossings we left
unsynchronized. On `drrtl_fifo_2clk` it reports 142 unsynchronized
crossings and no synchronizers: Dr. RTL's FIFO registers each pointer
twice, but in the *source* clock domain, and the flush signal is likewise
re-registered in the writing domain before use in the reading domain. A
single-clock flow cannot see this. [Aegis]{.smallcaps} optimizes such a
design but, by the CDC re-check, never adds to the 142.

Two detector issues found during this evaluation were fixed before any
reported run: synchronizers with a synchronous reset were initially
classified as unsynchronized (the reset multiplexer hid the direct
register-to-register connection; fixed by folding resets into the
flip-flop cell), and Gray pointers without a provable contract initially
left their next-value logic editable (fixed by the immutable Gray fan-in
rule of Section [4.1](#sec:phase1){reference-type="ref"
reference="sec:phase1"}). Gray contracts are proven automatically only
when the pointer is a module port (`soc`, `async_fifo`); in the other
designs the Gray logic is immutable, which is safe but blocks
optimization of the pointer incrementers.

## Synthesis-Only Baseline

The timing-driven synthesis-only flow already removes much of the
negative slack of the raw flow (Table [3](#tab:benchmarks){reference-type="ref"
reference="tab:benchmarks"}): for example, from $-2.39$ to $-0.33$ ns on
`eth_mac_1g_fifo` and from $-1.07$ to $-0.09$ ns on `axil_cdc`; on the
single-clock suite, from $-37.80$ to $-7.80$ ns on `cpu_fsm`. All
optimization results below are relative to this stronger baseline.

## Optimization Results {#sec:optres}

[**\[PRELIMINARY: single runs with Claude Sonnet 5.5; the remaining
designs, repetitions, ablations, and models have not been run. Replace
with Table T1 of `bench/results/report.md` once runs exist.\]**]{style="color: red"}

Table [5](#tab:prelim){reference-type="ref" reference="tab:prelim"} reports
the three runs completed so far. "CDC regr." counts candidates whose
Phase 4 re-check found a new unsynchronized or single-flop crossing, a
lost or downgraded crossing, or a contract that no longer holds; in
vanilla mode these checks are measured but not enforced.

::: {#tab:prelim}
  **Design**     **Mode**                 **Candidates**   **EQY-equivalent**   **CDC regr.**   **Final WNS / TNS (ns)**   **Final area**   **Final design vs. original**
  -------------- ------------------------ ---------------- -------------------- --------------- -------------------------- ---------------- --------------------------------
  `soc`          vanilla                  25               1                    24              $-0.38$ / $-2.37$          $-3.4\%$         equivalent, no CDC regression
  `soc`          [Aegis]{.smallcaps}      15               8                    0               $-0.38$ / $-2.38$          $-3.4\%$         equivalent, no CDC regression
  `async_fifo`   vanilla$^\dagger$        20               0                    15              $-0.03$ / $-1.92$          $+8.6\%$         **not equivalent; CDC regression**

  : Preliminary optimization runs (Claude Sonnet 5.5, one run each). Baselines: `soc` $-0.38$/$-3.34$ ns, 1,147 $\mu$m$^2$; `async_fifo` $-0.16$/$-2.87$ ns, 1,387 $\mu$m$^2$. $^\dagger$Partial run: 20 of 25 candidates; the remaining LLM calls failed on an account usage limit. Aegis candidates are counted after the checksum and envelope gate; EQY for Aegis is against the current baseline on the region's modules, for vanilla against the original design on the top module.
:::

On `soc`, both modes reach the same result in the `clk_w` domain, which
closes (worst slack $-0.04 \to +0.04$ ns, total negative slack
$-0.96 \to 0$): the design-level WNS of $-0.38$ ns that remains is the
deliberately unsynchronized `fast_q`$\to$`aux_q` crossing, which is an
asynchronous path and is reported to the constraint audit rather than
optimized. The difference is in how the result is reached. 24 of the 25
unguarded candidates regressed a crossing---for example, introducing a
single-flop crossing into the `clk_x` domain---and the final vanilla
design is correct only because the one equivalent candidate happened to
score best. [Aegis]{.smallcaps} produced no CDC regression, and 8 of its
15 candidates were proven equivalent.

On `async_fifo`, the unguarded run shows what the paper is about: its
final design improves WNS from $-0.16$ to $-0.03$ ns, an apparent 81%
gain, but none of its 20 candidates is equivalent to the original, 15
regress a crossing, and the promoted design both fails equivalence and
breaks a crossing. Measured by timing alone, it would be reported as a
success.

## Guardrail Test Suite {#sec:guardrail}

To show which layer catches which class of error independently of any
LLM, we ran nine hand-written rewrites with known ground truth through
every check, with every check evaluated rather than short-circuited
(Table [6](#tab:guardrail){reference-type="ref"
reference="tab:guardrail"}).

::: {#tab:guardrail}
  **Design**     **Class**         **Rewrite**                                          **Lock**    **Lint**   **LCM sim (mismatches)**   **EQY**   **CDC re-check**
  -------------- ----------------- --------------------------------------------------- ---------- ---------- -------------------------- --------- ------------------
  `soc`          equivalent        full-flag compare as XOR-reduce                      pass       pass       pass                       PASS      pass
  `soc`          functional bug    full flag against un-inverted MSBs                   pass       pass       **fail** (8,157)           FAIL      ---
  `soc`          sync edit         second synchronizer stage samples input directly     **fail**   pass       **fail** (8,146)           FAIL      ---
  `soc`          Gray $\to$ binary write pointer launched in binary                     pass       pass       **fail** (2,541)           FAIL      ---
  `soc`          comb. launch      Gray pointer driven combinationally                   pass       pass       pass (0)                   FAIL$^*$  **fail**
  `async_fifo`   equivalent        full-flag compare as XOR-reduce                      pass       pass       pass                       PASS      pass
  `async_fifo`   functional bug    increment ignores the full flag                      pass       pass       pass (0)                   FAIL      pass
  `async_fifo`   sync edit         read-pointer synchronizer reduced to one stage       **fail**   pass       **fail** (4)               FAIL      ---
  `async_fifo`   Gray $\to$ binary write pointer launched in binary                     pass       pass       pass (0)                   FAIL      **fail**

  : Guardrail test suite. "---": not reached (the cascade stops at a simulation mismatch). $^*$EQY fails because the pointer register no longer exists and its partition cannot be matched, not because EQY models the crossing.
:::

Three observations. First, synchronizer edits are stopped by the lock
before any simulation. Second, the combinational-launch rewrite on `soc`
is functionally equivalent: simulation compares 57,144 output-bit samples
without a mismatch. Only the CDC re-check identifies it as unsafe: the
Gray crossing disappears, a new unsynchronized crossing appears, and the
Gray contract no longer proves. EQY's failure on it is incidental to
partition matching. Third, random multi-clock simulation is weak on
FIFO-full corner cases: it missed both the full-flag bug and the binary
pointer on `async_fifo`, which EQY and, for the pointer, the CDC
re-check caught. Simulation is a fast filter, not a proof.

## Guardrail Ablation {#sec:ablation}

[**\[PENDING RUNS: ablations (a)--(e) of the protocol on the multi-clock
suite, from `bench/run_suite.py --configs no_locks zero_shot scalar
no_stall no_cdc_check`; report EQY pass rate, final per-domain WNS, and
measured lock/CDC violations per configuration.\]**]{style="color: red"}

## Skill Library Evolution

[**\[PENDING RUNS: confidence and anti-pattern changes logged in
`library_state.json` history; cold-start versus warm-start
(`--library shared`) on held-out designs.\]**]{style="color: red"}

# Discussion and Threats to Validity

#### Construct validity

EQY pass rate measures the fraction of candidates that are proven
equivalent on the modules they edit, at those modules' default
parameters. Each final design is additionally checked end to end against
the original RTL (Phase 4 against $v0$ and EQY on the top module), and
those results are reported with the run logs. Neither is a sign-off CDC
or tape-out argument.

#### Internal validity

LLM output is stochastic, and with the command-line backend no sampling
temperature is applied, so diversity across C1--C5 comes from the slot
roles and skills. Results from single runs cannot separate framework
effects from sampling noise; we therefore report repeated runs with
standard deviations.

#### External validity

The multi-clock suite has seven designs of up to 15,000 $\mu$m$^2$ and
four clocks; it does not include a large SoC with many generated clocks.
Several designs are FIFOs and bridges, which are the most common
multi-clock blocks but have short critical paths. The single-clock suite
comes from Dr. RTL and is evaluated with a different synthesis tool than
in that work.

#### The guardrails are a floor, not a proof

[Aegis]{.smallcaps} guarantees that the optimizer does not make the CDC
status of a design worse, as measured by its structural classification
and proven contracts. It does not verify that the original design's CDC is
correct beyond reporting what it finds, it does not perform
metastability-injection analysis, and its structural checks are weaker
than those of commercial CDC tools: for example, convergence of separately
synchronized signals is not analyzed.

# Limitations

Equivalence is proven per module at default parameters, not for the full
chip; register renaming or retiming can make EQY fail conservatively, so
some correct rewrites are rejected. Gray contracts are generated only when
the pointer is a module port; handshake, pulse, and qualifier contracts
require an annotation file. Gated or multiplexed clocks are not traced and
their flip-flops are reported as unclocked. Area recovery after timing
closure is not implemented. The clock-divider lock forgoes a class of
legitimate optimizations. Power is not evaluated. Sampling temperatures
could not be applied with the frontier models used.

# Conclusion

[Aegis]{.smallcaps} makes LLM-driven RTL timing optimization safe to apply
to multi-clock designs by treating CDC correctness as a separate
obligation from functional equivalence: crossings are found and
classified on the netlist before generation, what the verifiers cannot
check is locked by code-motion-robust checksums, and every candidate is
re-classified and its CDC contracts re-proven before it reaches the
equivalence gate. On a mutation suite, this re-check is the only layer
that rejects a functionally equivalent rewrite that breaks a Gray
crossing. In preliminary runs, an unguarded LLM optimizer regressed a
crossing in 39 of 45 candidates on two designs and promoted a
non-equivalent, CDC-broken design that appeared 81% faster, while
[Aegis]{.smallcaps} closed the violating domain of its test system with no
CDC regression. [**\[Update after the full runs.\]**]{style="color: red"}

Future work includes metastability-injection checks with open-source
formal tools, convergence analysis, contracts for crossings inside a
single module, relaxing the clock-divider lock via SDC regeneration, and
larger multi-clock SoCs.

# Reproducibility {#reproducibility .unnumbered}

The orchestrator and all tools, the agent definitions, the skill library
with its seed state, the benchmark wrappers and SDC files, the
synthesis-only baselines, the guardrail test suite, and every run log
(LLM calls, candidates, verification records, iteration summaries) will
be released at [**\[URL\]**]{style="color: red"}. All EDA tools used are
open source. Third-party benchmark RTL is redistributed only where its
license permits; otherwise a download script is provided.

::: thebibliography
00

W. Fang, Y. Lu, S. Liu, J. Wang, Z. Guo, J. He, F. Tu, and Z. Xie, "Dr. RTL: Autonomous Agentic RTL Optimization through
Tool-Grounded Self-Improvement," in *Proc. IEEE/ACM ICCAD*, 2026,
arXiv:2604.14989.

S. Thakur, B. Ahmad, H. Pearce, B. Tan, B. Dolan-Gavitt, R. Karri, and
S. Garg, "VeriGen: A Large Language Model for Verilog Code Generation,"
*ACM Trans. Des. Autom. Electron. Syst.*, vol. 29, no. 3, pp. 1--31,
2024.

Y.-D. Tsai, M. Liu, and H. Ren, "RTLFixer: Automatically Fixing RTL
Syntax Errors with Large Language Models," *arXiv preprint
arXiv:2311.16543*, 2024.

S. Thakur, J. Blocklove, H. Pearce, B. Tan, S. Garg, and R. Karri,
"AutoChip: Automating HDL Generation Using LLM Feedback," *arXiv
preprint arXiv:2311.04887*, 2023.

X. Yao et al., "RTLRewriter: Methodologies for Large Models Aided RTL
Code Optimization," in *Proc. IEEE/ACM ICCAD*, 2024.

Y. Wang et al., "SymRTLO: Enhancing RTL Code Optimization with LLMs and
Neuron-Inspired Symbolic Reasoning," *arXiv preprint arXiv:2504.10369*,
2025.

Y. Lu, S. Liu, H. Zhou, W. Fang, Q. Zhang, and Z. Xie, "A New Benchmark
for the Appropriate Evaluation of RTL Code Optimization," *arXiv preprint
arXiv:2601.01765*, 2026.

[**\[VERIFY authors and title\]**]{style="color: red"} "Ares," in *Proc. ASP-DAC*, 2027, arXiv:2607.27879.

Xu, Li, and Wang (Southeast University), [**\[VERIFY title\]**]{style="color: red"}, *arXiv preprint arXiv:2507.16808*, 2025.

C. Wolf and N. Engelhardt, "EQY: Equivalence Checking with Yosys,"
YosysHQ. \[Online\]. Available: <https://github.com/YosysHQ/eqy>

YosysHQ, "Yosys formal commands (clk2fflogic, async2sync)." \[Online\].
Available: <https://yosyshq.readthedocs.io/projects/yosys/en/stable/cmd/index_formal.html>

Cadence Design Systems, "Clock Domain Crossing Verification," white
paper. \[Online\].

[**\[VERIFY authors and title\]**]{style="color: red"} (DVCon Europe 2023 CDC methodology), *arXiv preprint
arXiv:2406.06533*, 2024.

vyges-tools, "cdc: structural CDC/RDC lint." \[Online\]. Available:
<https://github.com/vyges-tools/cdc>

SpecLoop authors, "SpecLoop: An Agentic RTL-to-Specification Framework
with Formal Verification Feedback Loop," *arXiv preprint
arXiv:2603.02895*, 2026.

D. Pretet, "async_fifo." \[Online\]. Available:
<https://github.com/dpretet/async_fifo>

D. Gisselquist, "wb2axip." \[Online\]. Available:
<https://github.com/ZipCPU/wb2axip>

A. Forencich, "verilog-axis, verilog-axi, verilog-ethernet." \[Online\].
Available: <https://github.com/alexforencich>
:::
