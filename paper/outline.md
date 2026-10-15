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
the available rewrite space for any given design [@drrtl2026].

Recent work has begun automating this loop with large language models.
LLMs have been applied to Verilog code generation from natural-language
specifications [@verigen2024], to automatic syntax-error
repair [@rtlfixer2024], and, more relevant to this work, directly to
RTL-level PPA optimization: RTLRewriter partitions a design into
sub-circuits and applies LLM-guided, cost-aware Monte Carlo tree search
over rewrites [@rtlrewriter2024]; SymRTLO combines LLM rewriting with a
corpus of symbolic optimization rules [@symrtlo2025]; ASPEN uses an LLM
agent to propose and select e-graph rewrite rules under PPA
feedback [@aspen2025]; and Dr. RTL introduces a closed-loop, multi-agent
framework with a continually self-improving library of optimization
skills, evaluated on realistic industrial-scale designs rather than
small hand-degraded benchmarks [@drrtl2026].

These frameworks share a common correctness strategy: verify each
candidate rewrite via simulation and/or formal equivalence checking
(typically Yosys EQY [@eqy]) before accepting it. This is sound for
purely combinational or single-clock-domain optimization targets. It is
*not* sound, without qualification, for designs containing asynchronous
clock-domain crossings. A two-flop synchronizer or CDC handshake can be
rewritten into a version that is functionally indistinguishable under
every simulated stimulus and every equivalence-checking assumption
available to EQY's bounded, deterministic verification model, while
being metastability-broken in actual silicon---because metastability is
a physical, probabilistic phenomenon that neither simulation nor
combinational/inductive equivalence checking models. An LLM rewriting
engine that treats "passes sim and passes EQY" as sufficient evidence of
correctness will, on a CDC-heavy design, eventually accept a rewrite
that silently breaks synchronization.

[Aegis]{.smallcaps} is designed around this specific blind spot. Rather
than relying solely on downstream verification to catch all classes of
error, [Aegis]{.smallcaps} performs an upfront, checksum-enforced
structural lock of the regions its own verification stack cannot
adequately check---synchronizer chains---before generation begins, so
that no candidate touching those regions can reach the verification
stages at all. This is a scope decision, not merely a caution: it is a
*hard* lock because it addresses a specific, known blind spot in the
pipeline's own verifiers, distinct from clock-divider logic, which is
locked for the separate reason that changing divider ratios silently
invalidates the SDC constraints the rest of the flow depends on.

A second, less visible problem concerns *where* the optimizer works.
Existing flows choose their targets by ranking critical paths globally
by slack [@drrtl2026], which is appropriate when every path is timed
against the same clock. In a multi-clock design it is not: slack in
nanoseconds is not comparable across clock periods, a single domain's
near-critical paths can occupy every slot, and many paths through one
structure are presented to the generator as many separate problems.
[Aegis]{.smallcaps} therefore replaces global path ranking with
domain-aware *region* selection. Violating endpoints are measured
against a closure margin, grouped into regions by shared logic cones,
filtered against the locks and the SDC clock relations, and allocated
per clock domain using the same domain weights as the scoring function,
so that the optimizer is pointed at exactly what the score rewards.

## Contributions

- A checksum-enforced AST guardrail mechanism that programmatically
  excludes CDC synchronizer chains and clock-divider logic from
  LLM-proposed rewrites, closing a correctness gap that simulation- and
  equivalence-only verification pipelines do not address. Digests are
  position-independent, so edits elsewhere in a file never trigger
  false rejections, and an SDC constraint audit routes asynchronous
  timing violations to a report instead of to the RTL rewriter.

- A domain-aware region selection method for multi-clock designs that
  measures each endpoint's deficit against a closure margin, clusters
  endpoints into regions by cone overlap, and allocates per-domain
  quotas using the same domain weights and adaptive schedule as the
  scoring function, together with explicit accounting of the timing
  that the guardrails block and that the optimizer cannot reach.

- A structural, pattern-keyed skill library---seeded from Dr. RTL's
  published pattern--strategy pairs [@drrtl2026] and updated via
  group-relative confidence scoring after every iteration---that
  improves both within a single design's optimization run and across
  subsequent designs.

- A stratified five-candidate generation strategy per dispatched
  region, combining conservative template-guided rewrites with a
  zero-shot, structurally unconstrained candidate, confined to an
  explicit edit envelope, with per-region winners composed into a single
  baseline update. A per-region stall-recovery policy excludes exhausted
  skill ranks, escalates exploration temperature, and retires regions
  that repeatedly fail to improve.

- A domain-aware dynamic penalty scoring function that evaluates
  margin deficits per clock domain rather than global WNS and TNS,
  preventing a regression in a fast critical domain from being masked
  by unrelated slack in a low-frequency control domain, and sharing its
  weights with region selection.

- A cross-model evaluation isolating the contribution of the
  orchestration layer from that of the underlying LLM, together with a
  three-column (raw RTL, synthesis-only baseline, GenAI-optimized) PPA
  reporting methodology that separates framework gains from gains a
  synthesis tool would already find unaided.

# Related Work

## LLM-Based RTL Generation and Repair

Early work applying LLMs to hardware description languages focused on
generating RTL from natural-language or high-level specifications.
VeriGen fine-tuned open-source LLMs specifically for Verilog
generation [@verigen2024]. AutoChip closed the loop with compiler and
simulation feedback to iteratively correct generated
HDL [@autochip2023]. RTLFixer targeted a narrower but practically
important problem: automatically repairing RTL syntax errors using
LLM-driven feedback [@rtlfixer2024]. These systems establish that LLMs
can produce syntactically and often functionally valid RTL, but they
target *generation from specification*, not optimization of an existing,
working design---a materially different problem, since an optimizer must
preserve an existing functional contract rather than satisfy a new one.

## LLM-Guided RTL and PPA Optimization

Closer to [Aegis]{.smallcaps}'s problem setting, several recent
frameworks apply LLMs directly to PPA-driven rewriting of existing RTL.
RTLRewriter partitions designs into sub-circuits and applies LLM-aided,
cost-aware Monte Carlo tree search, reporting improvements over both the
Yosys synthesis flow and e-graph-based optimizers such as
E-Syn [@rtlrewriter2024]. SymRTLO pairs LLM rewriting with a
symbolic-reasoning rule corpus for datapath and FSM
optimization [@symrtlo2025]. ASPEN uses an LLM agent to propose new
e-graph rewrite rules together with machine-checked correctness proofs,
then guides extraction with PPA feedback [@aspen2025]. Dr. RTL evaluates
on more realistic, larger-scale industrial RTL than prior benchmarks and
introduces a multi-agent, closed-loop architecture with a continually
updated skill library that is the direct basis for [Aegis]{.smallcaps}'s
own skill-library seeding [@drrtl2026]. Its timing analyzer selects
between 10 and 25 critical paths ranked by worst slack, and its
evaluation designs are single-clock, so the question of how to compare
and allocate violations across clock domains does not arise there.

None of these frameworks explicitly discuss clock-domain-crossing
correctness as a distinct concern from general functional equivalence.
Their correctness arguments rest on the combination of simulation and/or
EQY-style equivalence checking being sufficient evidence of a valid
rewrite---an assumption that holds for combinational and single-domain
sequential logic but not, in general, for asynchronous synchronizer
structures. [Aegis]{.smallcaps}'s checksum-locking mechanism is designed
to close exactly this gap without requiring the rest of the pipeline to
change. Likewise, none describes how optimization targets should be
chosen when violations are spread across asynchronous clock domains with
different periods, which is the problem [Aegis]{.smallcaps}'s region
selection addresses.

## Formal Equivalence Checking as a Correctness Gate

Yosys EQY constructs a miter between a reference and a candidate design
and discharges equivalence as a combination of combinational SAT
checking and bounded sequential $k$-induction [@eqy]. This gives
exhaustive, simulation-independent correctness evidence for the class of
properties it checks, and recent LLM-for-RTL work increasingly adopts it
as a hard filter on generated or rewritten candidates rather than a soft
scoring signal [@specloop2026]. [Aegis]{.smallcaps} follows this same
hard-gate philosophy---a candidate that fails EQY is disqualified
outright rather than penalized in a weighted score---but restricts EQY's
role to what it can actually certify, treating CDC correctness as a
separate, upstream, structurally-enforced concern rather than something
the equivalence checker is expected to catch.

## Comparative Positioning

Table [\[tab:comparison\]](#tab:comparison){reference-type="ref"
reference="tab:comparison"} summarizes how [Aegis]{.smallcaps}'s
correctness and self-improvement mechanisms relate to the four most
directly comparable LLM-based RTL optimization frameworks. Entries are
drawn from what each framework's own published methodology and
evaluation report; where a mechanism is not described in the source
material, we mark it *not reported* rather than assuming its absence,
since a framework may employ a mechanism without foregrounding it in the
paper we cite.

::: table*
  **Framework**                       **Correctness Gate**                                                                  **CDC-Aware Locking**                                                                            **Target Selection**                                                                    **Cross-Design Self-Improvement**                                                                        **Reported Benchmark Structure**
  ----------------------------------- ------------------------------------------------------------------------------------- ------------------------------------------------------------------------------------------------ --------------------------------------------------------------------------------------- -------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------
  RTLRewriter [@rtlrewriter2024]      Cost-aware MCTS search over rewrites; explicit formal-equivalence gating not reported Not reported                                                                                     Sub-circuit partitioning; clock-domain awareness not reported                           Not reported (search is per-design, not library-based)                                                   CPU designs and neural-network datapaths; not reported as multi-clock/CDC-dense
  SymRTLO [@symrtlo2025]              Symbolic rule corpus $+$ LLM rewriting; embedding-based template retrieval            Not reported                                                                                     Not reported                                                                            Retrieval corpus of templates, not a confidence-scored library updated via group-relative feedback       Derived from RTLRewriter's benchmark plus additional examples; not reported as CDC-dense
  ASPEN [@aspen2025]                  Z3-proved correctness of individual rewrite *rules* prior to use                      Not reported                                                                                     Not reported                                                                            Rule proposal is design-specific per run; not reported as persisting across designs                      Arithmetic/datapath circuits; not reported as multi-clock/CDC-dense
  Dr. RTL [@drrtl2026]                Tool-grounded closed-loop verification against industrial EDA tools                   Not reported as an explicit structural lock                                                      Global top-$K$ paths ($K \in [10,25]$) ranked by slack; single-clock evaluation designs Yes---continually self-improving skill library across designs (basis for [Aegis]{.smallcaps}'s seed set) Realistic, larger-scale industrial RTL; CDC density not specified
  **[Aegis]{.smallcaps} (this work)** Yosys EQY hard gate, disqualifying (not penalizing) failing candidates                **Explicit**: checksum-enforced pre-generation lock on synchronizers (hard) and dividers (scope) **Domain-aware**: margin-deficit regions with per-domain quotas                         Yes---group-relative confidence update per pattern, seeded from Dr. RTL                                  5 asynchronous clock domains, 21 generated clocks, $\sim$`<!-- -->`{=html}50K cells (CDC-dense by construction)

  [**\[DATA: Verify the Dr. RTL target-selection entry against its paper before submission; it is taken from our reading of its timing-analyzer description and released design list.\]**]{style="color: red"}
:::

The comparison isolates [Aegis]{.smallcaps}'s specific contribution
relative to this line of work: existing LLM-guided RTL optimization
frameworks verify correctness through search validity, rule-level formal
proofs, or tool-grounded closed-loop checking, but none of the cited
methodologies describe an explicit, checksum-enforced structural lock
addressing the specific class of error---CDC metastability---that their
own simulation- and equivalence-based verification cannot certify, and
none describes target selection that accounts for multiple clock
domains. [Aegis]{.smallcaps}'s skill-library mechanism is deliberately
continuous with Dr. RTL's rather than a competing alternative to it; the
contributions here are the guardrail layer and the domain-aware
selection layer placed upstream of that generation-and-verification
loop, not a replacement for it.

# Background

## Clock-Domain Crossings and Metastability

A signal crossing from one clock domain to an asynchronously related
clock domain risks violating the setup/hold timing of the receiving
flip-flop, producing metastability: a transient, unbounded-duration
invalid output state that can propagate as an unpredictable logic value.
The standard mitigation is a synchronizer---most commonly a two-flop
chain---that bounds the probability of metastability escaping to the
rest of the design to an acceptably low level. This is a physical,
timing- and process-dependent phenomenon; it is not visible to a purely
functional simulation (which evaluates signals at discrete logical time
steps under an idealized delta-cycle model) or to
combinational/inductive equivalence checking (which reasons about
functional behavior under a fixed clocking discipline, not about
metastable intermediate states). This is the specific verification gap
motivating [Aegis]{.smallcaps}'s hard-lock policy.

## Formal Equivalence Checking with EQY

EQY operates by building a miter circuit that feeds identical inputs to
a "gold" reference and a "gate" candidate design, XOR-reducing
corresponding outputs to a single equivalence signal, and discharging
the resulting property with a SAT-based combinational check
(`equiv_simple`) and a bounded $k$-induction sequential check
(`equiv_induct`) [@eqy]. An UNSAT result on the combinational check
proves equivalence across all possible input assignments---exhaustive
coverage that no finite testbench can offer---but this guarantee is with
respect to the functional, clocked semantics of the two designs; it says
nothing about metastable behavior in physical synchronizer hardware,
which is precisely why [Aegis]{.smallcaps} does not rely on EQY to
police CDC-sensitive regions.

# System Architecture

[Aegis]{.smallcaps} operates as a six-phase closed loop, summarized in
Table [1](#tab:pipeline){reference-type="ref" reference="tab:pipeline"}
and illustrated in Fig. [1](#fig:pipeline){reference-type="ref"
reference="fig:pipeline"}. The foundational principle is *programmatic*
protection rather than prompt-based instruction: prompts alone cannot
reliably enforce hard hardware safety constraints, so every safety
invariant in [Aegis]{.smallcaps} is enforced by deterministic Python
logic outside the model.

<figure id="fig:pipeline" data-latex-placement="t">

<figcaption><span class="smallcaps">Aegis</span>’s six-phase closed-loop
pipeline. The feedback edge from Phase 5.5 back into Phase 2 represents
the updated skill library and the per-region attempt record informing
the next iteration’s region selection and root-cause-to-strategy
lookup.</figcaption>
</figure>

::: {#tab:pipeline}
  **Phase** **Name**           **Primary function**
  --------- ------------------ --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  1         Ingestion & Shield Parses SDC/RTL, builds the clock-relation table and constraint audit, builds AST, locks CDC sync chains and clock dividers, computes position-independent AST hashes.
  2         Reasoning Engine   Runs OpenSTA, measures endpoint deficits against the closure margin, maps endpoints to RTL cones, clusters them into regions, diagnoses root cause and amenability, allocates per-domain quotas, dispatches regions.
  3         Execution Engine   Issues five parallel LLM transformations per dispatched region across stratified temperatures ($T=0.1$--$0.8$) and template strategies; enforces locks and the edit envelope; composes per-region winners.
  4         Verification Node  Syntax linting, LCM multi-domain simulation, structural CDC lint, graded scoring.
  5         Metric Evaluator   Scoped Yosys EQY formal equivalence, post-synthesis OpenSTA extraction, domain-aware scoring.
  5.5       The Librarian      Computes baseline-relative deltas, updates skill confidence, logs anti-patterns, adapts prompt templates.

  : [Aegis]{.smallcaps} optimization pipeline phases.
:::

## Phase 1: Ingestion and the Shield (AST Guardrails) {#sec:phase1}

[Aegis]{.smallcaps} first parses the design's clock tree directly from
its SDC constraints, identifying every asynchronous master clock domain,
every generated clock, and the divider ratio
$N_{\mathrm{div}} = f_{\mathrm{master}}
/ f_{\mathrm{gen}}$ relating each generated clock to its master. In the
representative target system, this yields five asynchronous master
domains and 21 generated clocks.

### Clock relations and constraint audit

From the parsed clock tree, Phase 1 builds a clock-relation table that
classifies every ordered pair of clocks as *identical*, *related* (a
master and a clock generated from it, or two clocks generated from the
same master), or *asynchronous*. It then audits the constraints on every
asynchronous pair: the pair should either be declared exclusive with
`set_clock_groups -asynchronous` or have its crossings bounded with
`set_max_delay -datapath_only`. Pairs with neither are written to a
*constraint-audit report*, to which Phase 2 later adds every
asynchronous crossing that STA flags as violating
(Section [4.2.2](#sec:crossing){reference-type="ref"
reference="sec:crossing"}). A violation on an asynchronous crossing is a
constraint or CDC-integration issue rather than an RTL timing defect,
and [Aegis]{.smallcaps} never attempts to fix it by rewriting RTL.

### Locked regions

A complete abstract syntax tree (AST) of the RTL is then constructed
[**\[DATA: frontend; Pyverilog parses Verilog-2001 only, so state pyslang or Yosys with sv2v if any benchmark uses SystemVerilog. Phases 1 and 2 must use the same frontend\]**]{style="color: red"},
and two categories of region are identified and locked, for two distinct
reasons:

- **Synchronizer chains (hard lock).** All two- and three-flop CDC
  synchronizers, Gray-code counters, and request/acknowledge handshake
  state machines are locked unconditionally. Neither the functional
  pre-filter (Phase 4) nor EQY (Phase 5) can detect a metastability
  regression introduced here, so an LLM-proposed change could pass every
  downstream check in the pipeline while being silicon-broken. This lock
  is therefore a correctness necessity, not merely a conservative
  default.

- **Clock dividers (scope lock).** Divider ratios determine the periods
  and multicycle-path exceptions in the SDC file that every downstream
  STA number depends on. Changing a divider without regenerating and
  re-validating the SDC invalidates all subsequent timing analysis. This
  is permissible in principle---given SDC regeneration and re-validation
  on every change---but is excluded in the current pipeline to keep
  iteration turnaround tractable.

The union of both categories forms the locked statement set
$\mathcal{L}$. Locks are recorded as sets of source statements, the same
representation Phase 2 uses for logic cones, so whether a cone touches
locked logic is a direct set intersection.

### Checksum enforcement

For every locked AST node $i$, a SHA-256 digest $\mathcal{H}_i$ is
computed as $$\begin{equation}
\mathcal{H}_i = \mathrm{SHA\text{-}256}\!\left(\mathrm{Tok}(i)
\,\Vert\, \mathrm{Id}(i)\right),
\label{eq:hash}
\end{equation}$$ where $\mathrm{Tok}(i)$ is the node's token stream with
whitespace and comments removed, and $\mathrm{Id}(i)$ identifies the
node by its enclosing module and the set of signals it assigns. Neither
term depends on line numbers, so a candidate that inserts or deletes
code elsewhere in a file leaves every $\mathcal{H}_i$ unchanged, while
any edit to a locked node changes its digest.

Every candidate is re-parsed immediately after generation. For each
locked node $i$, the node with identifier $\mathrm{Id}(i)$ is located in
the candidate and its digest recomputed. The candidate is rejected if
any locked node is missing, if any digest differs, or if any statement
outside the locked nodes assigns a signal that a locked node assigns.
Rejection happens before any lint, simulation, or formal compute is
spent, and does not rely on the LLM to report its own compliance.

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
Eq. [\[eq:domain\]](#eq:domain){reference-type="eqref"
reference="eq:domain"}, so that selection targets what the score rewards.
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
The same margin $m$ defines timing closure throughout the pipeline
[**\[DATA: value of $m$; $+100$ ps is the suggested starting point, to be swept\]**]{style="color: red"}.

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
$S_{\max}$ chosen so that each region fits in one prompt
[**\[DATA: values of $\theta$, $\varphi$ and $S_{\max}$\]**]{style="color: red"}. Because the
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
Eq. [\[eq:domain\]](#eq:domain){reference-type="eqref"
reference="eq:domain"}.

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
design from the number of violating regions
[**\[DATA: rule for $B$\]**]{style="color: red"}.

Within each domain, regions with $P_r > 0$ that are not marked tabu
(Section [4.2.8](#sec:dispatch){reference-type="ref"
reference="sec:dispatch"}) are taken in decreasing order of $P_r$ until
either the quota is filled or the selected regions cover a fraction
$\rho$ of $\Delta^{\Sigma}_d$
[**\[DATA: value of $\rho$; 0.8 suggested\]**]{style="color: red"}. The per-domain lists are then merged
into a single ranked queue by repeatedly taking the list head with the
largest $w_d\,\Delta^{\Sigma}_r$. This preserves the $P_r$ ordering
within each domain while ordering regions from different domains by
weighted absolute impact.

### Dispatch and region tabu {#sec:dispatch}

The queue ranks candidate regions; it is not handed to the generator as
a single batch. Each iteration dispatches the first $R$ regions in the
queue that are pairwise disjoint, preferring regions in different
modules
[**\[DATA: value of $R$; 1--3 suggested\]**]{style="color: red"}. Each dispatched region receives its own five-candidate
generation (Phase 3), its own skill match, and its own scoped
equivalence check. This keeps the EQY scope to one subtree per region,
prevents one failed region from discarding the progress on another, and
lets the Librarian attribute each outcome to a single pattern--strategy
pair.

The skill-rank exclusion and temperature escalation of
Section [\[sec:promotion\]](#sec:promotion){reference-type="ref"
reference="sec:promotion"} are applied per region. A region keyed by its
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
endpoint below $m$ is rejected regardless of its score
[**\[DATA: value of $h$\]**]{style="color: red"}.

### Skill library lookup

Each dispatched region keys into a JSON skill library on its dominant
root cause, the one carrying the largest share of the region's amenable
deficit. The library is seeded at project start from Dr. RTL's 47
published pattern$\rightarrow$strategy pairs [@drrtl2026], giving the
system a non-trivial prior instead of learning every template from a
cold start. Each entry retains strategy pattern templates
(e.g. tree-based reduction, speculative compute, retiming); a confidence
score $S_{\mathrm{conf}}$ adjusted from pass/fail history; and an
anti-patterns list of strategies that previously caused formal failure
or a lock violation for that pattern, which excludes them from future
generation.

## Phase 3: Execution Engine (Parallel Generation) {#sec:phase3}

For each dispatched region $r$, a Python orchestrator issues five
parallel LLM calls under stratified temperature sampling, with skills
matched to $r$'s dominant root cause. Each call receives the region's
cone, the declarations and module context needed to read it, and its
endpoints, slacks, and amenability labels:

- **C1 (strict conservative).** Matched skill template, $T=0.1$. Direct
  application of the known pattern rewrite.

- **C2 (creative variant).** Matched skill template, $T=0.7$. Explores
  structural variation within the template.

- **C3 (alternate strategy).** Secondary skill template, $T=0.3$.

- **C4 (exploratory alt).** Secondary skill template, $T=0.8$.

- **C5 (zero-shot architectural break).** No template, $T=0.5$,
  explicitly prompted to propose a structurally distinct implementation
  (retiming, resource sharing, pipelining).

All five candidates for a region target the same region, so Phase 5
compares like with like.

### Edit envelope

Each candidate may edit only within the region's edit envelope,
$$\begin{equation}
\mathcal{E}(r) = \left(\mathcal{C}(r) \cup \mathcal{A}(r) \cup
\mathcal{D}_{\mathrm{new}}\right) \setminus \mathcal{L},
\label{eq:envelope}
\end{equation}$$ where $\mathcal{C}(r)$ is the union of the region's
editable cones, $\mathcal{A}(r)$ is the set of always blocks that assign
its endpoint registers, and $\mathcal{D}_{\mathrm{new}}$ covers new wire
and register declarations within the enclosing modules. Including
$\mathcal{A}(r)$ lets C5 retime across the region boundary. Port
declarations are excluded, so module interfaces never change.
Immediately after generation, each candidate is diffed against the
baseline at AST level, together with the checksum test of
Eq. [\[eq:hash\]](#eq:hash){reference-type="eqref" reference="eq:hash"}.
A candidate is discarded if it changes any statement outside
$\mathcal{E}(r)$, before it consumes a lint or simulation cycle.

### Composing per-region winners

After Phases 4 and 5, let $W^{(r)}_n$ be the best equivalence-passing
candidate for each dispatched region $r$. Because the regions are
disjoint and module interfaces are unchanged, the winners are applied
together to $B_n$. The union is then synthesized once more and timed
with OpenSTA. When two winners fall in the same module, the scoped EQY
check is repeated on that module for the composed version, since neither
individual check covered the combination. If the composed design scores
worse under Eq. [\[eq:domain\]](#eq:domain){reference-type="eqref"
reference="eq:domain"} than the best single-region winner, which can
happen when regions interact through shared timing, the best
single-region winner is used instead. The selected design is the
iteration winner $W_n$ in the promotion rule of
Eq. [\[eq:promotion\]](#eq:promotion){reference-type="eqref"
reference="eq:promotion"}.

## Phase 4: Verification Node (Fast Pre-Filter)

Surviving candidates pass a sequential pre-filter cascade:

1.  **Syntax lint.** Verilator and Icarus Verilog; syntax errors or
    undeclared signals trigger immediate logging and rejection.

2.  **LCM-domain functional simulation.** Testbench duration is set to
    $$\begin{equation}
    T_{\mathrm{sim}} = \mathrm{LCM}\!\left(T_{\mathrm{clk}1},\dots,
    T_{\mathrm{clk}5}\right) \times K_{\mathrm{cycles}},
    \end{equation}$$ so that even the slowest asynchronous domain
    completes multiple full periods, rather than using a fixed cycle
    budget.

3.  **Structural CDC lint.** Yosys CDC analysis detects newly introduced
    reconvergence or unaligned cross-domain transfers elsewhere in the
    change---issues functional simulation alone does not surface.

Candidates are scored by the graded fraction of checks and assertions
passed rather than binary pass/fail, so a candidate passing 95% of
checks is carried forward with that information for Phase 5.5. Hard
failures in this phase---syntax errors and structural CDC
violations---are discarded immediately with the specific failure reason
logged for feedback. Lock and edit-envelope violations never reach this
phase; they are rejected in Phase 3.

## Phase 5: Metric Evaluator

Each surviving candidate is checked for formal equivalence against the
current baseline using Yosys EQY, scoped to the modules that contain
its region's edit envelope, with explicit boundary assumptions, rather
than performing full-chip re-verification on every
iteration---full-chip EQY at every iteration is not tractable at this
design's scale within a practical runtime budget. Because the edit
envelope excludes port declarations, every module boundary in the
checked scope is unchanged, which keeps the boundary assumptions
simple. This is enforced as a *hard gate*: candidates failing formal
equivalence are disqualified outright and are not scoring-eligible,
rather than being folded into a weighted score as a penalty term.
Eligible candidates are synthesized and re-measured via OpenSTA for
per-domain deficits and area. Two closure guards then apply
independently of the score: in a timing-met stage of the schedule, a
candidate that introduces a deficit at any endpoint that met the margin
in $B_n$ is rejected, and in the final iteration a candidate that does
not meet the margin in every domain is rejected. Remaining candidates
are scored per
Section [7](#sec:scoring){reference-type="ref" reference="sec:scoring"}.

## Phase 5.5: The Librarian (Skill Library Update)

For every dispatched region, the outcomes of all five candidates---including
failures---are evaluated against the current rolling baseline $B_n$,
$$\begin{equation}
\Delta_k = \frac{\mathrm{Score}_k - \mathrm{Score}(B_n)}
{\max\left(\left|\mathrm{Score}(B_n)\right|,\; \epsilon\right)},
\end{equation}$$ rather than against an absolute PPA scale, since raw
PPA values are not comparable across designs or rounds; evaluating
against the rolling baseline also decouples updates from the cohort
variance inherent to small-batch LLM generation. The floor $\epsilon$
keeps the ratio defined once every domain meets the margin and the
baseline's timing terms reach zero. Each outcome is attributed to the
pattern--strategy pair the candidate used, keyed by the region's
dominant root cause, which is possible because each candidate edits a
single region. Winning pattern--strategy pairs have their confidence
incremented
($S_{\mathrm{conf}} \leftarrow S_{\mathrm{conf}} + \delta$); strategies
that fail formal equivalence, violate a lock, or consistently
underperform their candidate group are demoted, and repeated failure
moves a strategy into that pattern's anti-patterns list. Failure reasons
logged in Phases 4 and 5 are summarized into the next round's prompts,
so guidance improves within the current design's run and carries forward
to the next design. The Librarian decides *how* a region is rewritten;
the attempt record of Section [\[sec:dispatch\]](#sec:dispatch){reference-type="ref"
reference="sec:dispatch"} decides *where* the optimizer works. The two
are kept separate, so a strategy is not demoted because its region is
intrinsically hard, and a region is not retired because a single
strategy failed on it.

## Termination and Instrumentation

A live dashboard displays the regions selected in each domain, each
dispatched region's logic before and after every accepted change,
per-domain deficit and area trends across iterations, skill library
growth, and the pass/fail/disqualified breakdown of each region's five
candidates. The loop terminates at the first of four conditions: after
$N_{\max}=5$ iterations; when every domain meets the margin and an
area-recovery iteration fails to promote; when the region queue is
exhausted because every remaining region is tabu or has no amenable
deficit; or at a pre-computed worst-case runtime ceiling. Timing
closure alone does not end the run, because the timing-met stages of
the schedule are where area is recovered. Each iteration evaluates at
most $5R$ candidates, each requiring lint, simulation, scoped EQY, and
synthesis with STA, plus one confirming synthesis and STA run for the
composed winner. The worst case is therefore at most $N_{\max}(5R+1)$
synthesis/STA runs and $N_{\max} \cdot 5R$ scoped EQY runs, and the
corresponding wall-clock time is computed and stated up front rather
than discovered during execution
[**\[DATA: measured per-run times for synthesis, STA and scoped EQY on each benchmark, and the resulting ceiling\]**]{style="color: red"}.

# Locking Rationale

The distinction between [Aegis]{.smallcaps}'s two lock categories is
worth stating explicitly, since it is a common point of scrutiny.
Synchronizers are locked because the pipeline's own verification
stack---simulation and EQY alike---cannot detect the class of regression
(metastability) that a rewrite in this region could introduce; this is a
hard correctness constraint. Clock dividers are locked because SDC and
STA validity depends on fixed divider ratios; this is a scope constraint
adopted to keep the pipeline tractable, not a claim that divider
optimization is unsafe in principle. The former is a statement about a
specific, known blind spot in [Aegis]{.smallcaps}'s own verifiers; the
latter is an engineering trade-off that could be relaxed given SDC
regeneration and re-validation on every change.

Two related design choices follow the same reasoning. First, the
constraint audit of Phase 1 is diagnostic only: [Aegis]{.smallcaps}
reports missing asynchronous exceptions and violated
`-datapath_only` bounds but never edits the SDC, since an automatically
added exception could hide a real CDC defect. Second, Gray-pointer and
handshake logic remain inside the hard lock even though some rewrites
of them would be safe. Admitting them would require a weaker tier in
which a rewrite is accepted only after it is proven to preserve the
structure's contract, for example that a Gray pointer changes at most
one bit per cycle. No such proof step exists in the current pipeline, so
we leave this tier to future work rather than relax the lock on the
strength of simulation and EQY alone.

# Baseline Promotion and Stall Recovery {#sec:promotion}

Phase 5.5 governs how skill library confidence weights evolve *within* a
single design. A separate, orchestrator-level policy governs how the
working baseline evolves *across* iterations, and how skill and
temperature selection adapt for a region whose rewrites stop improving
the baseline.

## Promotion Rule

Let $B_n$ denote the baseline entering iteration $n$, and $W_n$ the
iteration winner: the composition of the best-scoring,
formally-equivalent candidates of every region dispatched in iteration
$n$, or the best single-region winner when the composition scores worse
(Section [\[sec:phase3\]](#sec:phase3){reference-type="ref"
reference="sec:phase3"}). Adopting the convention that *lower scores are
better* under Eq. [\[eq:domain\]](#eq:domain){reference-type="eqref"
reference="eq:domain"}, $$\begin{equation}
B_{n+1} =
\begin{cases}
W_n & \text{if } \mathrm{Score}(W_n) < \mathrm{Score}(B_n)\\
B_n & \text{otherwise (stall).}
\end{cases}
\label{eq:promotion}
\end{equation}$$ The rule is applied identically at every iteration,
including the first: $B_1$ is the raw, unoptimized RTL, and $W_1$
replaces it only if it scores strictly better. A winner that merely ties
or regresses does not overwrite the baseline. If no dispatched region
produces an equivalence-passing candidate, there is no $W_n$ and the
iteration stalls.

## Per-Region Stall Detection and Skill Exclusion

Because each iteration works on several regions, stall recovery is
tracked per region rather than per iteration. Each region $r$, keyed by
its endpoint register set so that it can be recognized across
baselines, carries an attempt counter $a_r$, initially zero. After
iteration $n$, for every region dispatched in that iteration,
$$\begin{equation}
a_r \leftarrow
\begin{cases}
0       & \text{if } r\text{'s rewrite is part of } B_{n+1} \neq B_n \text{ (promoted)}\\
a_r     & \text{if } r\text{'s winner was dropped only by the composition fallback}\\
a_r + 1 & \text{otherwise (stalled).}
\end{cases}
\label{eq:attempts}
\end{equation}$$ A region whose winner was equivalence-passing and
improving, but was set aside because it interacted badly with another
region's winner, is not charged an attempt, since its strategy was not
shown to be insufficient.

When a region is dispatched with $a_r = 1$, the skill-matching step
excludes the Rank-1 and Rank-2 skills already assigned to its
candidates C1--C4 and substitutes the next-ranked entries (Rank-3,
Rank-4), since re-querying the same diagnosed pattern would simply
reselect the same top-two skills and repeat a rewrite already shown
insufficient. The region's zero-shot temperature is simultaneously
escalated: $$\begin{equation}
T_5^{(r)} \leftarrow \min\!\left(T_5^{(r)} + \Delta T,\; T_{\max}\right),
\end{equation}$$ with $T_5^{(r)} = 0.5$ initially, $\Delta T = 0.1$, and
$T_{\max}=1.0$ by default---once matched-skill strategies have proven
insufficient on a region, the zero-shot candidate is given more latitude
to propose a structurally distinct rewrite. When $a_r$ reaches 2, the
region is marked *tabu* for the remainder of the run and the queue
advances to the next region. Escalation and tabu status are
per region, so a hard region does not raise the exploration temperature
applied to an unrelated one.
Table [4](#tab:promotion){reference-type="ref"
reference="tab:promotion"} traces a representative sequence with
$R = 1$.

::: {#tab:promotion}
   **Iter.**  **Baseline**         **Region**   **$a_r$**   **Skills, C1--C4**               **$T_5^{(r)}$**   **Outcome**
  ----------- ------------------- ------------ ----------- -------------------------------- ----------------- --------------------------
       1      Raw RTL ($v0$)        $r_1$          0        Rank-1, Rank-1, Rank-2, Rank-2         0.5          Promoted
       2      $W_1$ (promoted)      $r_2$          0        Rank-1, Rank-1, Rank-2, Rank-2         0.5          Stall; $a_{r_2} = 1$
       3      $W_1$ (unchanged)     $r_2$          1        Rank-3, Rank-3, Rank-4, Rank-4         0.6          Stall; $r_2$ tabu
       4      $W_1$ (unchanged)     $r_3$          0        Rank-1, Rank-1, Rank-2, Rank-2         0.5          ---

  : Per-region promotion and stall recovery ($R = 1$). After iteration
  1, re-analysis of the promoted baseline ranks $r_2$ first; after $r_2$
  fails twice it is retired and the queue advances to $r_3$.
:::

# Domain-Aware Dynamic Penalty Scoring {#sec:scoring}

## Scalar Baseline Formulation

The natural formulation aggregates the three metrics into a single
global score per candidate, $$\begin{equation}
\mathrm{Score} = a\,\mathrm{WNS}^{\mathrm{norm}} + b\,\mathrm{TNS}^{\mathrm{norm}}
+ c\,\mathrm{Area}^{\mathrm{norm}},
\label{eq:scalar}
\end{equation}$$ with each term normalized against the current
iteration's baseline so scores are comparable within a round. For a
design with multiple independent asynchronous clock domains, however,
this aggregation can obscure a regression that is severe in one critical
domain but outweighed in the global average by unrelated slack in a
low-frequency control domain. We therefore use
Eq. [\[eq:scalar\]](#eq:scalar){reference-type="eqref"
reference="eq:scalar"} only as an ablation baseline
(Section [10.2](#sec:ablation){reference-type="ref"
reference="sec:ablation"}).

## Domain-Aware Formulation

$$\begin{equation}
\begin{aligned}
\mathrm{Score}_i = {} & \sum_{d \in D} w_d \left( \alpha\,
\mathrm{WNS}_{i,d}^{\mathrm{norm}} + \beta\,\mathrm{TNS}_{i,d}^{\mathrm{norm}}
\right)\\
& + \gamma\, f\!\left(\mathrm{Area}_i^{\mathrm{norm}}\right)
+ P_{\mathrm{CDC}} + P_{\mathrm{SEC}}.
\end{aligned}
\label{eq:domain}
\end{equation}$$

- **Per-domain breakdown ($w_d$).** The timing terms are computed
  independently for each master or generated clock domain $d \in D$,
  with $w_d = f_d / f_{\max}$, the same weight Phase 2 uses for region
  allocation, so a regression in a critical domain cannot be masked by
  slack elsewhere.

- **Margin-deficit timing terms.** To keep the score consistent with
  region selection, both timing terms are built from the margin
  deficits of Eq. [\[eq:deficit\]](#eq:deficit){reference-type="eqref"
  reference="eq:deficit"} rather than from raw negative slack:
  $$\begin{equation}
  \mathrm{WNS}^{\mathrm{norm}}_{i,d} =
  \frac{\Delta^{\max}_{i,d}}{\max\left(\Delta^{\max}_{B,d},\, m\right)},
  \qquad
  \mathrm{TNS}^{\mathrm{norm}}_{i,d} =
  \frac{\Delta^{\Sigma}_{i,d}}{\max\left(\Delta^{\Sigma}_{B,d},\, m\right)},
  \label{eq:timingnorm}
  \end{equation}$$ where $\Delta_{i,d}$ and $\Delta_{B,d}$ are the
  worst and total deficits of candidate $i$ and of the baseline $B_n$
  over *all* synchronous endpoints of domain $d$. Unlike selection, the
  score includes locked and unmapped endpoints, because a rewrite can
  degrade timing into logic it is not allowed to edit. With raw negative
  slack, a candidate that lifts near-critical endpoints toward the margin
  would score the same as the baseline even though selection had
  targeted exactly those endpoints. The floor $m$ in the denominator
  keeps the terms defined for a domain that already meets the margin: it
  contributes zero unless a candidate introduces a new deficit there.

- **Smooth quadratic area penalty.** The abrupt step-function cutoff is
  replaced with $$\begin{equation}
  f(A_i) =
  \begin{cases}
  A_i, & A_i \le 0.05\\
  A_i + \lambda (A_i - 0.05)^2, & A_i > 0.05,
  \end{cases}
  \end{equation}$$ where $A_i = \mathrm{Area}_i^{\mathrm{norm}}$ and
  $\lambda = 10.0$, and
  $\mathrm{Area}_i^{\mathrm{norm}} = (A_i - A_{B})/A_{B}$ is the relative
  change in cell area against the baseline, so that area reductions
  score negatively and growth up to 5% is tolerated while runaway growth
  beyond that threshold is steeply penalized.

- **Hard disqualifying penalties.** $P_{\mathrm{CDC}}$ is applied if a
  candidate modifies a synchronizer chain, Gray-code counter, or
  clock-divider enable---a scoring-level backstop consistent with,
  though not a substitute for, the Phase 1 checksum lock.
  $P_{\mathrm{SEC}}$ analogously encodes the Phase 5 EQY hard gate
  within the same expression. Both are implemented as a large finite
  constant ($10^4$) that renders any affected candidate unselectable in
  practice.

## Adaptive $\alpha/\beta/\gamma$ Schedule

In an asynchronous multi-clock design where timing closure is the
primary bottleneck, the relative weighting of timing and area should
shift as the run progresses. [Aegis]{.smallcaps} schedules $\alpha$,
$\beta$, $\gamma$ across the five-iteration budget as shown in
Table [5](#tab:schedule){reference-type="ref" reference="tab:schedule"},
gated on whether timing has closed. Closure is defined against the same
margin $m$ used throughout the pipeline: timing is met when every domain
has zero deficit, $\Delta^{\max}_d = 0$, which is equivalent to every
synchronous endpoint having slack of at least $m$. The same $\alpha$ and
$\beta$ weight region selection in Phase 2, and the timing-met stages
are where area-recovery targets are dispatched. Independently of the
composite score, the closure guards of Phase 5 apply: in the final
iteration, a candidate that does not meet the margin in every domain is
rejected.

::: {#tab:schedule}
  **Stage**                 $\boldsymbol{\alpha}$   $\boldsymbol{\beta}$   $\boldsymbol{\gamma}$  **Intent**
  ------------------------ ----------------------- ---------------------- ----------------------- ----------------------------------------------------
  Run 1                             0.60                    0.30                   0.10           Aggressive WNS slash; structural changes permitted
  Run 2                             0.50                    0.40                   0.10           Bleed weight from WNS to TNS
  Run 3 (WNS $\ge m$)               0.35                    0.25                   0.40           Bloat strip
  Run 3 (WNS $< m$)                 0.55                    0.35                   0.10           Stay in timing mode; area reduction blocked
  Runs 4--5 (timing met)            0.30                    0.20                   0.50           PPA refinement
  Runs 4--5 (not met)               0.70                    0.30                   0.00           Freeze area; last-ditch structural fix

  : Adaptive $\alpha/\beta/\gamma$ schedule across the five-iteration
  loop. The Run 3 gate on $\mathrm{WNS}\ge m$ (every domain meets the
  closure margin) and the Run 4 timing-met gate, defined the same way,
  determine whether the remaining budget strips area bloat or holds
  timing pressure.
:::

# Implementation Notes

Before settling on the current implementation, we explored three
alternative realizations of the [Aegis]{.smallcaps} architecture with
progressively different levels of LLM autonomy. We first modeled the
workflow as a LangGraph of reasoning, synthesis, verification, and
evaluation nodes, allowing an orchestrator agent to determine the next
action from intermediate results; tool execution became
non-reproducible, safety invariants were harder to enforce, and state
synchronization grew complex. We then implemented the same architecture
using coding-agent harnesses---Codex CLI, OpenCode, and Antigravity
CLI---with workflow, skills, and safety rules specified through Markdown
agent and skill files. These gave the model greater freedom to perform
architectural transformations but introduced additional nondeterminism
and made execution control more difficult; the agent would frequently
terminate early when only marginal improvements were available.

We therefore adopted a Python orchestrator for the final system.
Deterministic program logic controls the pipeline, verification gates,
baseline promotion, and termination criteria, while the LLM is invoked
only for selected high-value decisions: diagnosing the root cause and
amenability of each region, ranking applicable strategies, and
generating candidate RTL. Which regions exist, how they are scored and
allocated, and which ones are dispatched are all decided by
deterministic code, and the LLM's diagnosis labels are cached per region
so that re-analysis of an unchanged region reproduces them. This
separation is what makes the safety argument checkable: no invariant in
[Aegis]{.smallcaps} depends on the model's compliance with an
instruction.

# Experimental Setup

## Benchmarks

We evaluate on four CDC-dense designs, summarized in
Table [6](#tab:benchmarks){reference-type="ref"
reference="tab:benchmarks"}. The primary system spans five asynchronous
master clock domains and 21 generated clocks at approximately 50,000
cells, chosen specifically for its CDC density to stress-test the
locking mechanism.

::: {#tab:benchmarks}
  **Design**                          **Cells**                          **Clock domains**            **Source / character**
  --------------------- -------------------------------------- -------------------------------------- ---------------------------------------------------------
  `eth_top`                   $\sim$`<!-- -->`{=html}50K                 5 async $+$ 21 gen           [**\[DATA: source & provenance\]**]{style="color: red"}
  `dual_clk_mac_alu`     [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}  Arithmetic; MAC/ALU datapath
  `async_fifo`           [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}  Deep pipelining; CDC FIFO
  `cdc_packet_framer`    [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}  Dual-clock communication

  : Benchmark designs.
:::

[**\[DATA: State, for each benchmark: origin (open-source project,
in-house, or derived from a published suite), target clock constraint,
and standard-cell library / PDK. Reviewers will treat unsourced
benchmarks as self-constructed.\]**]{style="color: red"}

## Tooling

Static timing analysis uses OpenSTA, run on a hierarchy-preserving Yosys
synthesis with FSM re-encoding disabled and reporting one worst path per
endpoint for each capture clock; syntax and functional linting use
Icarus Verilog and Verilator; structural CDC checking uses Yosys CDC
scripts; RTL parsing for the locks and cones uses
[**\[DATA: frontend and version\]**]{style="color: red"}; and formal equivalence uses Yosys EQY,
scoped as described in Phase 5. The skill library is seeded from Dr. RTL's 47 published
pattern--strategy pairs [@drrtl2026];
RTLRewriter-Bench [@rtlrewriter2024] supplies complementary
pattern-labeled cases for candidate slots C3 and C4. [**\[DATA: Confirm
whether RTLRewriter-Bench was actually used in the reported runs or only
identified as a source --- the two claims are not
interchangeable.\]**]{style="color: red"}

## Models Evaluated

To separate the contribution of the orchestration layer from that of any
particular backend, we evaluate [Aegis]{.smallcaps} across multiple LLMs
spanning frontier, mid-tier, and open-weight classes, each run in two
modes: (i) *vanilla*, in which the model receives the RTL and the timing
report and is asked directly for an optimized rewrite, with no locks, no
skill library, and no verification gating; and (ii)
*$+$[Aegis]{.smallcaps}*, in which the same model serves as the
generator inside the full pipeline. Both modes receive the same
iteration budget and the same measurement flow, so the comparison
isolates the framework rather than the prompt.

[**\[DATA: Fix the model roster before submission. Record for each:
exact model identifier and version string, provider, API date of access,
and the number of independent runs per configuration. Do not report a
model identifier that cannot be resolved to a real published version ---
a single unverifiable model name invalidates the table for
reviewers.\]**]{style="color: red"}

## Selection Parameters

Table [\[tab:params\]](#tab:params){reference-type="ref"
reference="tab:params"} lists the parameters of Phase 2. None is
fixed by the method; each is set per the rule shown and its sensitivity
is reported in Section [\[sec:ablation\]](#sec:ablation){reference-type="ref"
reference="sec:ablation"}.

::: {#tab:params}
  **Parameter**                        **Symbol**     **Setting**
  ----------------------------------- ------------- ---------------------------------------------------------------
  Closure margin                           $m$       [**\[DATA: value; $+100$ ps suggested start, swept\]**]{style="color: red"}
  Cone-overlap threshold                $\theta$     [**\[DATA: value, swept\]**]{style="color: red"}
  Control-net fanout cutoff             $\varphi$    [**\[DATA: value\]**]{style="color: red"}
  Region size cap                      $S_{\max}$    [**\[DATA: value, set by prompt budget\]**]{style="color: red"}
  Region budget per iteration              $B$       [**\[DATA: per-design rule from number of violating regions\]**]{style="color: red"}
  Domain coverage target                 $\rho$      [**\[DATA: value; 0.8 suggested, swept\]**]{style="color: red"}
  Regions dispatched per iteration         $R$       [**\[DATA: value; 1--3 suggested\]**]{style="color: red"}
  Area-mode slack headroom                 $h$       [**\[DATA: value\]**]{style="color: red"}

  : Phase 2 selection parameters.
:::

## Protocol and Reporting {#sec:protocol}

Each configuration is run for $N_{\max} = 5$ iterations, each
dispatching up to $R$ regions with five candidates per region, giving at
most $25R$ generation attempts per design per configuration. [**\[DATA: Report the number of independent repetitions
per configuration and present mean $\pm$ standard deviation rather than
single-run point estimates; LLM sampling variance at $T$ up to $0.8$ is
large enough that single runs are not
defensible.\]**]{style="color: red"}

Following the three-column reporting practice noted in Section I, we
report PPA at three stages---raw (unoptimized) RTL, a synthesis-only
baseline with no LLM involvement, and [Aegis]{.smallcaps}'s optimized
output post-synthesis---so that gains attributable to the framework are
isolated from gains a synthesis tool realizes unaided. [**\[DATA: The
synthesis-only column is the single most important baseline for reviewer
credibility and is currently absent from the results; populate it for
all four benchmarks.\]**]{style="color: red"}

# Results {#sec:results}

[**\[DATA: All results in this section were produced by the earlier pipeline, which selected a global top-$K$ list of paths and generated five candidates per iteration. They do not yet reflect the region selection, edit envelope, per-region dispatch, margin-based closure, or deficit-based score described in Sections 4--7. Every table and figure below must be regenerated with the current pipeline before submission, or explicitly labeled as results of the earlier version.\]**]{style="color: red"}

## Cross-Model Comparison

Table [\[tab:crossmodel\]](#tab:crossmodel){reference-type="ref"
reference="tab:crossmodel"} reports formal-equivalence pass rate and
average frequency gain for each backend in both execution modes. Two
effects are visible. First, the pass-rate gap between vanilla and
$+$[Aegis]{.smallcaps} is large and consistent in sign across every
model: unguarded rewriting produces formally-equivalent output in a
minority of attempts regardless of backend capability. Second, the
residual spread in frequency gain among [Aegis]{.smallcaps}-guarded
configurations is substantially narrower than the spread in raw
capability between the same models, indicating that the orchestration
layer supplies most of the achieved improvement and the backend supplies
the remainder.

The failure-mode column is the more decisive result for this paper's
claim. Every vanilla configuration exhibited at least one class of
CDC-structural violation---synchronizer chain modification, divider
enable alteration, or CDC boundary timing violation---and every
[Aegis]{.smallcaps}-guarded configuration exhibited none, because such
candidates are rejected at the checksum barrier before reaching any
verification stage.

::: table*
  **Model & execution mode**             **Formal equiv. pass rate (%)**   **Avg. freq. gain (%)**  **Primary failure mode / behavior**
  ------------------------------------- --------------------------------- ------------------------- --------------------------------------------------------
  Model A (vanilla)                                    24                          $+21.0$          High: introduces CDC boundary timing violations
  **Model A $+$ [Aegis]{.smallcaps}**                **90**                   $\mathbf{+33.2}$      **None: blocked by AST locks and Phase 4 checks**
  Model B (vanilla)                                    19                          $+2.0$           Moderate: alters clock divider enable logic
  **Model B $+$ [Aegis]{.smallcaps}**                **86**                   $\mathbf{+26.4}$      **None: blocked by Phase 1 lock and phase interlocks**
  Model C (vanilla)                                    22                          $+8.0$           High: breaks multi-stage synchronizer chains
  **Model C $+$ [Aegis]{.smallcaps}**                **82**                   $\mathbf{+24.1}$      **None: constrained by skill library filters**
  Model D (vanilla)                                    15                            n/a            Very high: emits non-synthesizable constructs
  **Model D $+$ [Aegis]{.smallcaps}**                **76**                   $\mathbf{+12.8}$      **None: constrained by anti-pattern rules**

\

[**\[DATA: Replace Model A--D with the exact model identifiers and
version strings actually used. Every identifier must be resolvable to a
real, published model release.\]**]{style="color: red"}
:::

## Selection Diagnostics {#sec:selectiondiag}

Table [\[tab:selectiondiag\]](#tab:selectiondiag){reference-type="ref"
reference="tab:selectiondiag"} reports, for each benchmark, how the
baseline's deficit is accounted for by Phase 2: the fraction of
violating endpoints that map deterministically to RTL, the deficit sent
to the constraint-audit report as asynchronous, the deficit blocked by
each lock category, and the deficit that remains unreachable because
its endpoints require a latency change. The mapping match rate is the
direct evidence for the claim that mapping is deterministic, and the
blocked deficit is the direct cost of the guardrail.

::: {#tab:selectiondiag}
  **Design**             **Match rate**   **Async (audit)**   **Blocked: hard**   **Blocked: scope**   **Unreachable**   **Regions**
  --------------------- ---------------- ------------------- ------------------- -------------------- ----------------- -------------
  `eth_top`                 [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}
  `dual_clk_mac_alu`        [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}
  `async_fifo`              [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}
  `cdc_packet_framer`       [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}   [**\[DATA: \]**]{style="color: red"}

  : Phase 2 selection diagnostics on the unoptimized baseline. Deficits
  are given as a percentage of total weighted deficit
  $\sum_d w_d \Delta^{\Sigma}_d$ before filtering.
:::

## Ablations {#sec:ablation}

[**\[DATA: This subsection is required and currently has no data behind it. Each ablation holds everything else fixed and reports EQY pass rate, final per-domain deficit, final area, and the count of candidates rejected at the lock and envelope checks.\]**]{style="color: red"}

*Guardrail and generation ablations.* (a) Checksum locks disabled;
(b) the skill library replaced by zero-shot prompting at all five
candidate slots; (c) the scalar score of
Eq. [\[eq:scalar\]](#eq:scalar){reference-type="eqref"
reference="eq:scalar"} substituted for the domain-aware score of
Eq. [\[eq:domain\]](#eq:domain){reference-type="eqref"
reference="eq:domain"}; (d) per-region stall recovery and tabu
disabled.

*Selection ablations.* (e) A global top-$K$ list ranked by slack in
place of per-domain quotas; (f) individual endpoints in place of
regions; (g) the region score of
Eq. [\[eq:regionscore\]](#eq:regionscore){reference-type="eqref"
reference="eq:regionscore"} without per-domain normalization;
(h) raw negative slack in place of the margin deficit, in both
selection and scoring. We also report the overlap between the regions
selected by [Aegis]{.smallcaps} and the paths a global top-$K$ selector
picks on the same baseline, and the sensitivity of final results to
$\theta$, $\rho$, $B$, and $R$.

Without these ablations, the paper asserts that each mechanism matters
but demonstrates it only for the locks, and only indirectly.

## Macro-Level Optimization Telemetry

Table [\[tab:telemetry\]](#tab:telemetry){reference-type="ref"
reference="tab:telemetry"} traces the primary benchmark across all five
optimization rounds. WNS improves monotonically from $-0.84$ ns to
$+0.15$ ns and TNS from $-15.42$ ns to $0.00$ ns, with timing first
closing in round 3. Maximum operating frequency rises from $92.25$ MHz
to $100.65$ MHz ($+9.11\%$) while total cell area falls $3.26\%$,
confirming that the area term of
Eq. [\[eq:domain\]](#eq:domain){reference-type="eqref"
reference="eq:domain"} is not merely tolerated but actively exploited
once timing pressure relaxes under the Run 3 gate.

Round 3's EQY pass rate of 60% (3/5) is notable: it coincides with the
scheduler's transition into area-reduction mode, where candidates
attempt more aggressive structural rewrites. The hard gate discards the
two non-equivalent candidates without their scores influencing baseline
selection, and the round still promotes.
[**\[DATA: With $R$ regions per iteration, each round evaluates up to $5R$ candidates; report EQY pass rate as passing/evaluated over all dispatched regions, and add a row for the number of regions dispatched and promoted per round. State closure against the margin $m$ rather than WNS $\ge 0$.\]**]{style="color: red"}


::: table*
  **Metric**                      **Baseline**   **Round 1**   **Round 2**   **Round 3**   **Round 4**   **Round 5**    **Overall $\Delta$**
  ------------------------------ -------------- ------------- ------------- ------------- ------------- ------------- -------------------------
  WNS (ns)                          $-0.84$        $-0.53$       $-0.19$       $+0.01$       $+0.12$       $+0.15$             $+0.99$
  TNS (ns)                          $-15.42$      $-10.33$       $-4.95$       $-1.29$       $+0.15$       $0.00$             $+15.42$
  Max frequency (MHz)               $92.25$        $95.02$       $98.43$       $99.65$      $102.05$      $100.65$       $+8.40$ ($+9.11\%$)
  Total cell area ($\mu$m$^2$)    $418{,}724$    $413{,}712$   $408{,}527$   $405{,}299$   $405{,}009$   $405{,}062$   $-13{,}662$ ($-3.26\%$)
  EQY pass rate                       ---         80% (4/5)    100% (5/5)     60% (3/5)    100% (5/5)    100% (5/5)           88% mean
:::

## Comprehensive PPA Results

Table [7](#tab:ppa){reference-type="ref" reference="tab:ppa"} summarizes
PPA across all four benchmarks. `dual_clk_mac_alu` shows the largest
gains on every axis, consistent with arithmetic datapaths offering the
richest space of equivalence-preserving restructurings (tree reduction,
resource sharing, carry-chain reorganization). `cdc_packet_framer` shows
the smallest, consistent with a design whose critical path lies
predominantly in locked or locked-adjacent CDC logic---the guardrails
constrain achievable gain exactly where they are most needed, which is
the intended trade-off rather than a deficiency. The blocked deficit in
Table [\[tab:selectiondiag\]](#tab:selectiondiag){reference-type="ref"
reference="tab:selectiondiag"} quantifies this directly
[**\[DATA: confirm that the blocked share for cdc_packet_framer is in fact high; otherwise this explanation must change\]**]{style="color: red"}.

::: {#tab:ppa}
  **Design**             **Freq.**     **Area**     **Power**    **Timing status**
  --------------------- ------------ ------------ -------------- --------------------------------------------------------------------------------------------------
  `dual_clk_mac_alu`     $+35.05\%$   $-51.10\%$   $\sim18.5\%$  Closed ($+2.24$ ns)
  `async_fifo`           $+28.96\%$   $-4.45\%$    $\sim12.0\%$  [**\[DATA: reported as $-71.49$ ns --- still negative; restate honestly\]**]{style="color: red"}
  `cdc_packet_framer`    $+3.57\%$    $-10.00\%$   $\sim4.2\%$   [**\[DATA: $+0.02$ ns is below a $+100$ ps margin; report as closed only if it meets the margin $m$ used\]**]{style="color: red"}
  `eth_top`              $+9.11\%$    $-3.26\%$    $\sim7.5\%$   Closed ($+0.15$ ns)

  : PPA results across benchmark designs.
:::

\

[**\[DATA: The $51.10\%$ area reduction on `dual_clk_mac_alu` will be
challenged. Either characterize the baseline (e.g. unshared arithmetic
resources) so the figure is explicable, or report it against the
synthesis-only baseline where it will be smaller and more defensible.
Also state how power was estimated (vectorless vs. activity-based);
$\sim$ figures without a stated method read as
estimates.\]**]{style="color: red"}

## Frequency Trajectory

<figure id="fig:freqtraj" data-latex-placement="t">

<figcaption>Maximum operating frequency across five <span
class="smallcaps">Aegis</span> optimization rounds for each benchmark.
Round 0 is the unoptimized baseline.</figcaption>
</figure>

Across benchmarks, frequency scales consistently over rounds
(Fig. [2](#fig:freqtraj){reference-type="ref"
reference="fig:freqtraj"}). Deep-pipelining designs such as `async_fifo`
improve steadily across all five rounds, whereas arithmetic-dominated
designs realize most of their gain in the first two rounds and then
plateau. At that point the per-region stall-recovery policy of
Section [6](#sec:promotion){reference-type="ref"
reference="sec:promotion"} applies: regions that fail to improve are
redispatched with Rank-3/Rank-4 skills and an escalated zero-shot
temperature, and then retired, so the remaining budget moves to
lower-ranked regions.

## Manual versus Automated Effort

Table [\[tab:human\]](#tab:human){reference-type="ref"
reference="tab:human"} compares baseline human-written RTL against
[Aegis]{.smallcaps}-optimized output on four common hardware blocks.

::: table*
  **Module**                       **Baseline (WNS / area)**       **[Aegis]{.smallcaps} (WNS / area)**   **Est. manual effort**   **[Aegis]{.smallcaps} runtime**         **EQY pass rate**
  ---------------------------- ---------------------------------- -------------------------------------- ------------------------ --------------------------------- --------------------------------
  Dual-port FIFO (`fifomem`)    $-1.82$ ns / $1{,}420\,\mu$m$^2$       $-0.15$ ns / $120\,\mu$m$^2$            $\sim5.0$ h                     3.4 min                 72% (boundary cycle shift)
  32-bit ALU & hazard unit      $-1.24$ ns / $3{,}450\,\mu$m$^2$     $-0.18$ ns / $3{,}210\,\mu$m$^2$          $\sim6.5$ h                     4.2 min               95% (combinational AST match)
  8-tap MAC / adder tree        $-2.10$ ns / $5{,}100\,\mu$m$^2$     $-0.35$ ns / $4{,}850\,\mu$m$^2$          $\sim10.0$ h                    5.8 min               88% (re-parenting equivalence)
  16-level priority arbiter       $-0.95$ ns / $890\,\mu$m$^2$         $-0.04$ ns / $820\,\mu$m$^2$            $\sim3.3$ h                     2.5 min               98% (pure Boolean equivalence)

\

[**\[DATA: The manual-effort column is an estimate, not a measurement,
and must be labeled as such in the caption with its basis stated
(e.g. author estimate, practitioner survey). The `fifomem` row reports a
$12\times$ area reduction at 72% EQY pass --- explain what the baseline
contained, or drop the row.\]**]{style="color: red"}
:::

[Aegis]{.smallcaps} reaches comparable or better slack in minutes rather
than hours of engineering time. We stress that the manual-effort figures
are estimates and that the comparison measures wall-clock throughput,
not engineering judgment: [Aegis]{.smallcaps} explores only the rewrite
space its skill library encodes, whereas a human engineer may
reformulate the microarchitecture entirely.

## Skill Library Evolution

<figure id="fig:skilllib" data-latex-placement="t">

<figcaption>Evolution of the JSON skill library over five optimization
iterations on the dual-clock communication benchmark, seeded with 44
active patterns and 6 anti-patterns.</figcaption>
</figure>

Seeded with 44 active patterns and 6 anti-patterns, the library
contracts to 38 active patterns over five iterations as suboptimal
heuristics are pruned, while 19 confidence reinforcements accumulate on
the strategies that survive and the anti-pattern registry grows to 12
entries (Fig. [3](#fig:skilllib){reference-type="ref"
reference="fig:skilllib"}). Register retiming and carry-chain
restructuring accumulate the most reinforcement; mux reordering is
registered as an anti-pattern after repeatedly failing equivalence on
reconvergent paths. Because pruning is driven by observed outcomes
rather than a fixed schedule, the library carried forward to a
subsequent design is strictly better conditioned than its seed state.
[**\[DATA: Quantify this claim: report a cold-start run versus a
warm-start run using the library evolved on a different design. As
written, cross-design transfer is asserted but not
measured.\]**]{style="color: red"}

# Discussion and Threats to Validity

#### Construct validity

EQY pass rate measures the fraction of candidates that survive a bounded
equivalence check scoped to a subtree, not full-chip functional
correctness. A high pass rate is evidence that generated rewrites are
well-formed within the checked boundary; it is not a tape-out
correctness argument. Similarly, region selection sees only the
endpoints it can map to RTL. An endpoint lost to register merging,
retiming, or memory inference is excluded from selection, though not
from scoring, so a low match rate would leave part of the design's
deficit invisible to the optimizer. Reporting the match rate per
benchmark makes the size of this blind spot explicit.

#### Internal validity

LLM sampling is stochastic and candidate temperatures reach $0.8$.
Results reported from a small number of runs may not separate framework
effects from sampling noise. The root-cause and amenability labels that
drive region scoring also come from an LLM; caching makes them stable
within a run, but a different first labeling can change which regions
are dispatched. This is the principal internal threat to the
cross-model comparison and is addressed by the repetition protocol
described in Section [\[sec:protocol\]](#sec:protocol){reference-type="ref"
reference="sec:protocol"}.

#### External validity

Four benchmarks, with only one at $\sim$`<!-- -->`{=html}50K cells, is a
narrow base from which to claim generality. The designs are CDC-dense by
construction, which is appropriate for testing the guardrail hypothesis
but means the reported gains should not be read as representative of
arbitrary RTL. Evaluation on a published suite such as RTLRewriter-Bench
would strengthen external validity considerably.

#### The guardrails are a floor, not a proof

[Aegis]{.smallcaps} does not verify CDC correctness; it refuses to
modify CDC structures. This closes the specific failure mode of an LLM
silently breaking an existing synchronizer, but it offers no protection
against a design whose synchronizers were already wrong, and it forgoes
any optimization that would require touching them.

# Limitations

The current implementation scopes EQY equivalence checking to the
modules containing each dispatched region's edit envelope rather than
the full chip, which is a practical necessity at this design's scale but means
equivalence guarantees are local to the checked boundary and depend on
the correctness of the boundary assumptions used. The five-iteration
budget was chosen for tractability and is not established as sufficient
for convergence. With several regions per iteration, the five
iterations may still leave lower-ranked regions untried on large designs.
Region selection depends on parameters (Table [\[tab:params\]](#tab:params){reference-type="ref"
reference="tab:params"}) that are set by rule rather than learned, and
the area-recovery mode uses a simple module-level ranking by cell area
under a slack-headroom constraint rather than a dedicated area
diagnosis. Composing per-region winners assumes that disjoint edits
interact only through shared timing; the composition fallback catches
regressions from such interactions but does not search for a better
combination. Power figures are derived from [**\[DATA: state
estimation method\]**]{style="color: red"}. The clock-divider scope lock
forgoes a class of optimization that is legitimate in principle.
[**\[DATA: Add the observed CDC-lint false-positive/false-negative
behavior if it was characterized during
evaluation.\]**]{style="color: red"}

# Conclusion

[Aegis]{.smallcaps} demonstrates that GenAI-assisted RTL timing closure
can be made safe for CDC-heavy designs not by assuming downstream
simulation and formal equivalence checking are sufficient, but by
explicitly identifying and closing the specific blind
spot---synchronizer metastability---that those verification stages
cannot cover, through a checksum-enforced structural lock applied before
generation. A second element makes the approach fit multi-clock designs:
optimization targets are chosen as regions of related violating
endpoints, measured against a closure margin and allocated per clock
domain with the same weights the scoring function uses, so that no
single domain monopolizes the budget and the optimizer works on what the
score rewards. Across four CDC-dense benchmarks, the framework raises
formal-equivalence pass rates substantially over unguarded rewriting on
every evaluated backend, eliminates CDC-structural failure modes
entirely, and delivers frequency gains up to $+35.1\%$ with concurrent
area and power reduction. The cross-model study indicates these gains
derive primarily from the orchestration layer rather than from backend
capability, which is the practically relevant claim: the framework
should continue to pay off as the underlying models change.

Future work includes relaxing the clock-divider scope lock via automated
SDC regeneration and re-validation; admitting Gray-pointer and
handshake logic to a contract-checked tier in which rewrites are
accepted only after proving the structure's protocol properties;
outcome-aware region prioritization once iteration budgets are large
enough to learn from; extending evaluation to published benchmark
suites and larger industrial designs; and replacing scoped equivalence
checking with an incremental full-chip strategy that remains tractable
across iterations.

# Reproducibility {#reproducibility .unnumbered}

[**\[DATA: Strongly recommended. State whether the orchestrator, skill
library seed, benchmark RTL, SDC files, and run logs will be released,
and where. Venues in this area (LAD, MLCAD) explicitly highlight papers
with open artifacts, and an artifact release is the cheapest available
answer to most of the credibility concerns
above.\]**]{style="color: red"}

::: thebibliography
00

Dr. RTL authors, "Dr. RTL: Autonomous Agentic RTL Optimization through
Tool-Grounded Self-Improvement," *arXiv preprint arXiv:2604.14989*,
2026.

S. Thakur, B. Ahmad, H. Pearce, B. Tan, B. Dolan-Gavitt, R. Karri, and
S. Garg, "VeriGen: A Large Language Model for Verilog Code Generation,"
*ACM Trans. Des. Autom. Electron. Syst.*, vol. 29, no. 3, pp. 1--31,
2024.

Y.-D. Tsai, M. Liu, and H. Ren, "RTLFixer: Automatically Fixing RTL
Syntax Errors with Large Language Models," *arXiv preprint
arXiv:2311.16543*, 2024.

S. Thakur, J. Blocklove, H. Pearce, B. Tan, S. Garg, and R. Karri,
"AutoChip: Automating HDL Generation Using LLM Feedback," *arXiv
preprint arXiv:2311.04887*, 2023.

X. Yao et al., "RTLRewriter: Methodologies for Large Models Aided RTL
Code Optimization," in *Proc. 43rd IEEE/ACM Int. Conf. Computer-Aided
Design (ICCAD)*, 2024.

Y. Wang et al., "SymRTLO: Enhancing RTL Code Optimization with LLMs and
Neuron-Inspired Symbolic Reasoning," *arXiv preprint arXiv:2504.10369*,
2025.

Zhang et al., "ASPEN: LLM-Guided E-Graph Rewriting for RTL Datapath
Optimization," in *Proc. Machine Learning for CAD (MLCAD)*, 2025.

C. Wolf and N. Engelhardt, "EQY: Equivalence Checking with Yosys,"
YosysHQ. \[Online\]. Available: <https://github.com/YosysHQ/eqy>

SpecLoop authors, "SpecLoop: An Agentic RTL-to-Specification Framework
with Formal Verification Feedback Loop," *arXiv preprint
arXiv:2603.02895*, 2026.
:::
