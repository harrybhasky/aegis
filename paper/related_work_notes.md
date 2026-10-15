# Related-work notes for Aegis and the CDC mutation benchmark

Compiled 2026-10-08. The BibTeX is in `related_work.bib`, and each key below matches an entry there. Every entry was checked against a primary or bibliographic page: the arXiv abstract or HTML full text, the Crossref record of the DOI, NSF-PAR, Google Patents, a conference program, or GitHub/Zenodo. Fields that could not be confirmed carry `note = {UNVERIFIED: ...}` in the .bib file.

Section names refer to the headings in `main 2.md`. "Benchmark section" means the section that releases the CDC mutation benchmark, which the draft does not have yet. Until it exists, use Results > Guardrail Test Suite.

---

## NOVELTY RISKS (read first)

No released benchmark of **CDC-breaking RTL rewrites of real multi-clock designs** was found. Three works come close enough to need explicit differentiation in the paper.

1. **SV-Gap (`svgap2026`): moderate risk, the closest artifact.**
   - An open-source evaluation layer for AI-generated RTL by Shraddha Sridhar (NVIDIA, per Zenodo). It is on PyPI as `svgap`, with releases from 2026-07-02 (0.1.0-a1) to 2026-09-08 (0.3.0-a14).
   - It ships **paired safe/unsafe "witness" fixtures**. In each pair, both variants pass the same functional testbench, and only a structural CDC/RDC oracle (Yosys-based) flags the unsafe one.
   - The CDC families are:
     - `level_crossing`: single direct sample vs. two-flop synchronizer
     - `comb_crossing`: logic before the synchronizer
     - `gray_counter`: binary bus vs. Gray-coded transfer
     - `pulse_crossing`
     - `toggle_crossing`
     - `handshake_crossing`: no acknowledgment return
     - `cdc_reconvergence`
     - `async_fifo`: binary pointer vs. Gray pointer
     - `synchronizer_depth`: 2 vs. 3 stages
   - This is conceptually very close to the benchmark's core claim that CDC-breaking variants are invisible to functional checks.
   - **How we differ:**
     - The fixtures are small, hand-built calibration pairs. Its README says they "do not establish real-world prevalence."
     - They are not mutations of real multi-clock IP, and they are not produced by an optimizer.
     - There is no equivalence-checking dimension, so it does not show that a rewrite can pass EQY-style checking while breaking a crossing.
     - There is no PPA or timing motivation.
     - It does not mention multi-clock simulation; its oracle is structural.
   - **Action:** cite it and state the difference explicitly in Related Work and in the benchmark section.

2. **Xu, Li & Wang 2025 (`xu2025`, arXiv 2507.16808): moderate risk, the closest paper.**
   - Its 32 "clock-domain" metamorphic cases deliberately:
     - split a single-clock logic chain across two or more clock domains of identical or fixed-multiple frequency;
     - **insert new clock-domain crossings and synchronizer stages**; and
     - replace standard synchronizers with "more convoluted asynchronous protocols".
   - The transformations are claimed to be **semantics-preserving**. Equivalence is said to be checked with ABC and Icarus simulation. The paper notes that the clocks have matching frequency, "so there is no actual clock drift between domains."
   - **What it lacks:** no CDC check of any kind, no CDC-breaking (unsafe) variants, and no stated release of the benchmark (no URL in the paper).
   - The goal is to test whether LLM optimizers handle complex timing logic. LLMs underperform Yosys on clock-domain cases.
   - **How we differ:** our mutants **break** CDC safety while staying functionally equivalent under zero-delay simulation and EQY, and they are labeled by a CDC oracle.
   - **Action:** reviewers who know this paper will ask about it. The draft's comparison-table row ("Clock-domain *mutations* in 32 cases; no CDC check") is accurate, but it should say "semantics-preserving metamorphic transformations that add domains/synchronizers" rather than "mutations", so it is not read as CDC-bug injection.

3. **ViTAD (`vitad2025`, arXiv 2508.13257): low-to-moderate risk.**
   - An LLM-based debugging tool for timing violations. Its 54-case dataset is seeded from open-source RTL such as PicoRV32 and OpenRISC, with injected violations.
   - It includes CDC sub-scenarios:
     - `single_bit_trans`: "Single-bit signals are transmitted directly between clock domains without proper synchronizers."
     - `multi_bits_trans`
   - It is an injected-CDC-bug dataset paired with an LLM, but:
     - it gives no per-subscenario count;
     - it names no CDC checking tool (only Vivado timing analysis);
     - **no release URL was found**; and
     - it targets repair of violations, not guardrailing an optimizer.

**Lower-risk adjacent items:**
- **GateTruth** has a Tier-2 "CDC synchronizer" generation task and a Track-B "CDC safety for a FIFO" repair objective. Its own text says CDC is "modeled structurally, not via true multi-clock metastability simulation", and its mutants are generic, with none CDC-specific.
- **Arch** (`arch2026`) is an AI-native HDL whose type system makes unsynchronized crossings compile-time errors.
- **The Synopsys patent** (`gupta2018cdcmutation`) defines CDC-specific mutations, but as a proprietary verification-robustness method with no released benchmark.

---

## Gap statement (supported by the evidence below)

- We found no released benchmark of CDC-*breaking* RTL rewrites of realistic multi-clock designs.
- Existing LLM RTL bug and debug benchmarks contain no CDC-specific mutation operators. Some explicitly filter clock and reset signals out of mutation (AssertLLM2).
- Their multi-clock content is incidental at most: 2 of 50 RTLLM v2.0 designs, one GateTruth task, and failure-cluster labels in CVDP.
- The one LLM-optimization study that adds clock domains (Xu et al., 2025) uses semantics-*preserving* transformations, does no CDC checking, and gives no release.
- CDC-specific mutation exists in industry (Synopsys US 9,990,453 B2: eight mutation types), but as a patented testbench-qualification method, not an open dataset.
- The nearest open artifact, SV-Gap (Jul–Sep 2026), ships nine small hand-built safe/unsafe CDC fixture pairs for calibrating oracles. They are not mutants of real multi-clock IP, not optimizer-style rewrites, and not paired with an equivalence-checking verdict.
- A benchmark of functionally equivalent, EQY-passing, CDC-breaking rewrites of real multi-clock RTL, labeled by a CDC oracle, therefore appears to be new. The claim should be worded "to our knowledge" and should cite SV-Gap and Xu et al. explicitly.

---

## A. LLM RTL optimization (PPA / timing)

### `drrtl2026`: Dr. RTL (arXiv 2604.14989)
- **What it does:** An agentic, multi-agent framework for RTL timing optimization. It analyzes critical paths, generates parallel rewrites, checks them with tools, and distills successful patterns into a skill library (47 entries) through group-relative learning. On 20 real-world designs it reports 21%/17% WNS/TNS gains and 6% area reduction over a commercial synthesis flow.
- **How Aegis differs:** Dr. RTL assumes single-clock designs and does not mention CDC. Aegis adds crossing classification, lock tiers, and a CDC re-check and contract re-proof for every candidate, and runs on multi-clock designs.
- **Cite in:** Introduction; Related Work > LLM-Guided RTL and PPA Optimization; Comparative Positioning; Experimental Setup > Benchmarks (the 20 designs).
- **Verification:** The arXiv page lists no venue, so the draft's "ICCAD 2026" is UNVERIFIED.

### `rtlrewriter2024`: RTLRewriter (ICCAD 2024)
- **What it does:** LLM-aided RTL optimization using circuit partitioning, multimodal analysis, retrieval of optimization guides, cost-aware MCTS, and a faster verification step. It introduces the Large and Small Rewriter benchmarks and compares against Yosys and e-graph tools.
- **How Aegis differs:** RTLRewriter's checking is simulation and equivalence oriented, and its designs are single-clock. Xu et al. show RTLRewriter mishandles clock-domain logic.
- **Cite in:** Related Work > LLM-Guided Optimization; Comparative Positioning.

### `symrtlo2025`: SymRTLO (NeurIPS 2025)
- **What it does:** Combines LLM rewriting with retrieval of optimization rules, AST templates, and a symbolic FSM optimizer. It verifies with formal equivalence plus tests, and reports large PPA gains on the RTLRewriter benchmark with Design Compiler and Yosys.
- **How Aegis differs:** It has no notion of clock domains. Its FSM state merging could silently alter crossing structure, which is exactly the failure mode Aegis guards against.
- **Cite in:** Related Work > LLM-Guided Optimization; Comparative Positioning.

### `rtlopt2026`: RTL-OPT benchmark (arXiv 2601.01765)
- **What it does:** 36 handcrafted designs, each pairing suboptimal RTL with a human-optimized reference. It comes with an automated correctness and PPA evaluation flow.
- **How Aegis differs:** All tasks are single-clock and nothing on the page mentions CDC. Our benchmark targets the correctness dimension RTL-OPT cannot exercise.
- **Cite in:** Related Work; Comparative Positioning; benchmark section (benchmark-design contrast).

### `xu2025`: Rethinking LLM-Based RTL Code Optimization via Timing Logic Metamorphosis (arXiv 2507.16808)
- **What it does:** A metamorphic study. It applies semantics-preserving complexity-increasing transformations to 153 seed cases from VerilogEval, RTLLM, and GitHub:
  - 54 logic-operation
  - 27 data-path
  - 40 timing-control-flow
  - 32 clock-domain
- **Clock-domain transformations:** split a chain across two or more domains with equal or fixed-multiple frequencies, insert crossings and synchronizer stages, and replace standard synchronizers with convoluted asynchronous protocols.
- **Method:** Equivalence is claimed via ABC and Icarus. It evaluates GPT-4, Claude-3.7-Sonnet, and RTLRewriter against Yosys. LLMs beat Yosys on logic operations but lose on timing-control-flow and clock-domain optimization.
- **Missing:** no CDC/metastability analysis and no release URL.
- **How Aegis differs:** see NOVELTY RISK 2. Our variants are CDC-unsafe by construction, and we check CDC on every candidate.
- **Cite in:** Introduction (evidence that LLMs struggle with clock-domain logic); Related Work; Comparative Positioning; benchmark section.

### `veriopt2025`: VeriOpt (ICCAD 2025)
- **What it does:** Multi-role prompting (Planner, Programmer, Reviewer, Evaluator) with PPA constraints and synthesis-report and timing feedback for Verilog *generation*. It reports large power, area, and timing gains over baseline LLM RTL, with 86% functional success.
- **How Aegis differs:** It is generation, not guarded rewriting of existing IP, and it has no equivalence or CDC gate.
- **Cite in:** Related Work > LLM-Guided Optimization.

### `ares2027`: ARES (arXiv 2607.27879)
- **What it does:** Cost-aware LLM RTL PPA optimization. It normalizes dollar cost per call, finds that engineered long-term memory gives no reliable benefit over plain concatenation, and escalates reasoning effort only when progress stalls. It reports a deeper figure of merit than Dr. RTL at 12% of the tokens.
- **How Aegis differs:** It is single-module and single-clock with no CDC handling. Its negative result on memory is relevant to our skill-library claims.
- **Cite in:** Related Work; Comparative Positioning; Discussion (skill library).
- **Verification:** The arXiv page lists no venue, so the draft's "ASP-DAC 2027" is UNVERIFIED, and the draft's "[VERIFY authors and title]" can now be filled in from the .bib.

### `aspen2025`: ASPEN (MLCAD 2025)
- **What it does:** An LLM agent proposes and selects e-graph rewrite rules for datapath RTL, with real EDA feedback for extraction. It reports 16.5% area and 6.7% delay gains over prior e-graph approaches.
- **How Aegis differs:** It is datapath-only and correct-by-construction through rewrite rules, but those rules are single-clock combinational/datapath identities. CDC is out of scope.
- **Cite in:** Related Work > LLM-Guided Optimization (symbolic/e-graph line).
- **Verification:** DOI is UNVERIFIED.

### `coward2022egraph`: Automatic Datapath Optimization using E-Graphs (ARITH 2022)
- **What it does:** The foundational e-graph (egg) approach to RTL datapath rewriting, with up to 71% area reduction.
- **How Aegis differs:** Its rewrites are provably equivalent combinational identities. Aegis handles free-form LLM rewrites of sequential multi-clock RTL, where equivalence alone does not imply CDC safety.
- **Cite in:** Related Work (one sentence on symbolic/e-graph rewriting).

---

## B. LLM RTL bug / mutation / debugging benchmarks

For each entry, **CDC content** records any multi-clock, CDC, or synchronizer content that was found.

### `veribugbench2026`: VeriBugBench (arXiv 2609.18022)
- **What it does:** Builds 2,608 single-fault instances from 45 open-source projects using 19 inverse mutation operators mined from real bug-fix histories. The operator families are Expression, Bit-vector, Assignment, Timing (EdgeFlip/Insert/Delete), and Port (IOFlip). LLM-generated testbenches improve fault observability. Released at github.com/wndif/VeriBugBench. It extends MANTRA (DAC 2023).
- **CDC content:** **None.** The full text never mentions CDC, multi-clock, synchronizers, metastability, async FIFOs, or Gray code.
- **How we differ:** Its faults are functional and output-observable by construction. Ours are functionally invisible and CDC-only.
- **Cite in:** Related Work (new paragraph on bug/mutation benchmarks); benchmark section.

### `mantra2023`: MANTRA (DAC 2023)
- **What it does:** Mutation testing of HDL code with operators derived from real bugs. It is the predecessor of VeriBugBench.
- **CDC content:** None in the derived operator set (see VeriBugBench).
- **How we differ:** Our operators are derived from CDC failure modes, not from bug-fix histories.
- **Cite in:** Related Work (mutation testing for hardware); benchmark section.

### `fixbenchrtl2025`: Fixbench-RTL (AsianHOST 2025)
- **What it does:** An LLM RTL-debugging benchmark. Each case has buggy RTL, the fix, a natural-language description, and a simulation testbench. It covers syntax, functional, and security bugs.
- **CDC content:** None mentioned in the project-page description or the AsianHOST program. The full text could not be read (compressed PDF), so this is partially UNVERIFIED.
- **How we differ:** Its bugs are detected by testbenches. Ours pass testbenches by design.
- **Cite in:** Related Work (bug benchmarks).

### `hwfixbench2025`: HWFixBench (GLSVLSI 2025)
- **What it does:** A hardware fault-repair benchmark derived from 500 pull requests and 1,481 bug fixes across 12 open-source hardware projects.
- **CDC content:** None mentioned on the NSF-PAR record or the project page. The ACM full text was inaccessible, so this is partially UNVERIFIED.
- **Cite in:** Related Work (bug benchmarks).

### `hwebench2026`: HWE-Bench (arXiv 2604.14709)
- **What it does:** 417 repository-level bug-repair tasks from real PRs in six projects (OpenTitan, Caliptra, XiangShan, Ibex, CVA6, Rocket Chip), evaluated in containers with each project's own regressions. The best agent resolves 70.7% of tasks.
- **CDC content:** **Negligible.** Its taxonomy has a "timing and synchronization issues" category, and one Rocket Chip BootROM "clock-domain issue" appears as an example. No CDC, synchronizer, or metastability terms appear, and there are no CDC-specific tasks.
- **How we differ:** Real bugs are found by project regressions, whereas our mutants are, by construction, missed by regressions.
- **Cite in:** Related Work (bug benchmarks).

### `cirfix2022`: CirFix (ASPLOS 2022)
- **What it does:** Automated repair of Verilog defects using hardware-specific fault localization and a fitness function. It releases a benchmark of 32 defect scenarios, with 21 plausible and 16 correct repairs.
- **CDC content:** None mentioned.
- **How we differ:** CirFix needs a failing testbench. CDC mutants give it nothing to localize.
- **Cite in:** Related Work > LLM-Based RTL Generation and Repair (classic repair).

### `buggen2025`: BugGen (arXiv 2506.10501)
- **What it does:** A multi-agent LLM pipeline that inserts and validates realistic functional bugs. It produced 500 bugs in five OpenTitan IPs with 94% functional accuracy and found 104 regression blind spots. It is compared against Certitude.
- **CDC content:** None on the abstract page. Mutation targets are functional logic.
- **How we differ:** BugGen keeps a bug only if it is functionally detectable. We keep a mutant only if it is functionally *undetectable* yet CDC-unsafe.
- **Cite in:** Related Work; benchmark section (contrast in selection criterion).

### `assertllm2_2026`: AssertLLM2 (arXiv 2605.27472)
- **What it does:** 83 designs with specs, golden RTL, and buggy RTL from 17 AST mutation operators. It evaluates assertion generation in bug-prevention and bug-hunting modes and is released on GitHub.
- **CDC content:** **None, by design.** The paper states "Clock and reset signals are explicitly filtered" from mutation targets.
- **How we differ:** CDC is precisely the class AssertLLM2 excludes.
- **Cite in:** Related Work; benchmark section (strong supporting quote for the gap statement).

### `gatetruth2026`: GateTruth (arXiv 2608.12635)
- **What it does:** Audits RTL benchmark testbenches through mutation-kill rates using nine generic operators (comparator flips, operator, logic, and bitwise inversions, reset polarity, and others). It finds most RTLLM v2.0 testbenches below 95% kill, and three at zero.
- **CDC content:** **Small.**
  - A Tier-2 "clock-domain-crossing synchronizers" generation task, plus a Track-B "CDC safety for a FIFO" repair objective.
  - The paper says CDC is "modeled structurally, not via true multi-clock metastability simulation."
  - It reports a 50% kill rate on its synchronizer design.
  - There are no CDC-specific mutants.
  - Its RTLLM audit notes that `asyn_fifo` fails under Icarus.
- **How we differ:** Its operators are generic, and its CDC is a single-clock structural model.
- **Cite in:** Related Work; benchmark section; Threats to Validity (testbench weakness).

### `cvdp2025`: NVIDIA CVDP (arXiv 2506.14074)
- **What it does:** 783 problems in 13 categories (generation, completion, modification, lint/QoR, testbench, assertion, debugging, Q&A) in agentic and non-agentic formats.
- **CDC content:** **Negligible and unquantified.** It has no CDC task category. "Clock Domain; Protocol Violations" and "Metastability hazards" appear only as LLM failure-cluster labels in its error analysis (Table 5), which suggests some problems involve multiple clocks. There are no CDC mutants.
- **Cite in:** Related Work (benchmarks); Introduction (LLM RTL evaluation landscape).

### `verilogeval2023`: VerilogEval (ICCAD 2023)
- **What it does:** 156 HDLBits problems evaluated by simulation against references.
- **CDC content:** None mentioned. The problems come from HDLBits, but a per-problem multi-clock audit was not done.
- **Cite in:** Related Work > LLM-Based RTL Generation.

### `rtllm2024`: RTLLM (ASP-DAC 2024)
- **What it does:** An open benchmark for natural-language-to-RTL, scored on syntax, function, and design quality (PPA). v2.0 has 50 designs.
- **CDC content:** **2 of 50 designs are multi-clock**, as generation targets rather than mutants:
  - `asyn_fifo`: wclk/rclk, Gray pointers, 2-flop pointer synchronizers.
  - `synchronizer`: clk_a/clk_b, 2-flop enable synchronizer with an unsynchronized multi-bit data register that relies on stated hold assumptions.
- **Cite in:** Related Work; benchmark section. These are possible extra seed designs, license permitting.

### `vitad2025`: ViTAD (arXiv 2508.13257)
- **What it does:** LLM debugging of timing violations via a Signal Timing Dependency Graph and a RAG knowledge base. The 54-case dataset has injected violations, including CDC `single_bit_trans` and `multi_bits_trans` cases. It reports a 73.7% repair rate.
- **CDC content:** **Yes, but small and unreleased.** See NOVELTY RISK 3. No CDC checker is named, and no release was found.
- **How we differ:** Our benchmark is released, oracle-labeled, and equivalence-preserving, and it targets optimizer guardrails.
- **Cite in:** Related Work; benchmark section.

---

## C. CDC verification, CDC mutation, CDC tooling

### `gupta2018cdcmutation`: Synopsys US 9,990,453 B2
- **Bibliographic data:** Gupta, Forey, Narwade, Toma. Assignee Synopsys. Filed 30 Mar 2015, granted 5 Jun 2018.
- **What it does:** Adds activation-controlled CDC-specific mutations to synchronizer circuitry and checks whether each test both activates a mutation and toggles the CDC signal. One mutation models legal silicon behavior and the rest model incorrect designs, to grade verification robustness. The **eight mutation types** are:
  1. Extra sequential stage (one-cycle phase-dependent delay; the only "silicon behavior" mutation)
  2. Synchronizer bypass via mux
  3. Glitch insertion
  4. Extra pulse via negative-edge flop
  5. Bypass of data-path gating circuitry
  6. Constant acknowledgment on a req/ack handshake
  7. Constant memory-empty flag in a FIFO
  8. Raw asynchronous reset applied directly to a flop that should get the synchronized reset
- **How we differ:**
  - The patent is a proprietary method for qualifying testbenches. No dataset is released, and mutants are activation-gated inside simulation.
  - Our mutants are standalone, functionally equivalent RTL rewrites used to test optimizers and CDC oracles.
  - Our operator set should be mapped against these eight types, and the overlap acknowledged (bypass, gating bypass, and reset are likely shared).
- **Cite in:** Related Work > Formal Equivalence and CDC Verification; benchmark section (operator taxonomy comparison).

### `cummings2002fifo`: Cummings, async FIFO (SNUG San Jose 2002)
- **What it does:** The canonical Gray-pointer asynchronous FIFO, with 2-flop pointer synchronizers and full/empty logic.
- **Relevance:** It is the protocol that the Aegis Gray-stepping contract and FIFO mutants encode.
- **Cite in:** Background > Clock-Domain Crossings and Metastability; benchmark section.

### `cummings2008cdc`: Cummings, CDC Design & Verification Techniques Using SystemVerilog (SNUG Boston 2008)
- **What it does:** The standard practitioner reference on synchronizers, fast-to-slow transfer, multi-bit transfer (async FIFO, 1-deep 2-register FIFO), and CDC verification.
- **Relevance:** It is the source of the safe idioms our mutants break.
- **Cite in:** Background; Locking Rationale.

### `li2009cdc`: Li & Kwok, Automatic formal verification of CDC signals (ASP-DAC 2009)
- **What it does:** An early automated formal CDC verification flow from Mentor Graphics authors, covering structural recognition of synchronizers plus formal checking of protocol properties.
- **How Aegis differs:** Aegis re-runs a lightweight open-source analog of this on every LLM candidate, as a regression gate (no worse than baseline) rather than for sign-off.
- **Cite in:** Related Work > CDC Verification; Background.

### `mvcdc2024`: Kumar, Khan & Mittra, Pragmatic Formal Verification Methodology for CDC (DVCon Europe 2023; arXiv 2406.06533)
- **What it does:** Formal CDC verification with metastability injection (MSI) on CDC paths. It reuses IP-level setup at SoC level and generates SVA for synchronizer schemes.
- **Relevance:** It is the basis for the claim that zero-delay simulation misses CDC bugs.
- **Cite in:** Background (already cited); Related Work.
- **Draft fix:** the draft's "[VERIFY authors and title]" placeholder can now be filled in from the .bib.

### `litterick2006cdc`: Litterick, Pragmatic Simulation-Based Verification of CDC Signals and Jitter Using SVA (DVCon 2006)
- **What it does:** Simulation-based CDC checking with SVA, plus emulation of CDC jitter to stress downstream logic. It is the classic simulation-side metastability and jitter injection reference.
- **Relevance:** It supports the threats-to-validity discussion of our multi-clock simulation, which does not inject jitter.
- **Cite in:** Background; Threats to Validity.

### `accellera2026cdc`: Accellera CDC/RDC Standard 1.0 (approved, press release 2 Mar 2026)
- **What it does:** A tool-neutral IP abstraction for CDC/RDC intent, used in hierarchical sign-off.
- **Relevance:** Aegis's crossing manifest and lock tiers could be exported in this format. It also signals that CDC intent is now standardizable.
- **Cite in:** Related Work > CDC Verification; Discussion / Future Work.

### `moyeen2025cdcai`: Moyeen & Pathak, AI/ML-Driven CDC/RDC Constraint Generation (DVCon India 2025)
- **What it does:** Siemens Questa CDC-Assist (AI/ML) suggests CDC setup constraints, which are then validated formally and functionally.
- **How Aegis differs:** It is AI for CDC *setup* in commercial sign-off. It is not LLM-based as far as the page shows, and it does not optimize RTL or release a benchmark.
- **Cite in:** Related Work (AI + CDC sentence).
- **Verification:** Title tail and venue are partially UNVERIFIED.

### `opencdc`: OpenCDC (GitHub)
- **What it does:** An open-source slang-based static CDC analyzer with 13 rules, including unsynchronized crossings, multi-bit crossings, reconvergence, and RDC. It has 278 tests and a `benchmarks` folder of unknown content.
- **Relevance:** It is a candidate second oracle for labeling our mutants, which would reduce oracle-specific bias.
- **Cite in:** Related Work ("open-source CDC tooling is immature"); benchmark section (cross-oracle labeling).

### `vygescdc`: vyges-cdc (GitHub)
- **What it does:** A netlist-level structural CDC/RDC checker that takes netlist, Liberty, and SDC input.
- **Gaps:** Its README lists reconvergence, Gray-code/handshake recognition, data stability, and glitch analysis as unimplemented. It ships no seeded CDC bug suite.
- **Cite in:** Related Work (already cited in the draft).

### `svgap2026`: SV-Gap
- **Summary:** See NOVELTY RISK 1.
- **Cite in:** Related Work (bug/eval benchmarks and CDC tooling); benchmark section (explicit differentiation); Introduction (if the "functional checks miss CDC" claim is made there).

---

## D. LLMs combined with clock domains or multi-clock design (2025–2026)

**Search coverage:**
- arXiv API abstract queries for "clock domain crossing", "clock domain", CDC, multi-clock, metastability, or synchronizer combined with LLM / language model, sorted by date to October 2026.
- An arXiv query for (Verilog OR RTL) AND (CDC-related terms).
- Web searches over DAC, ICCAD, DATE, MLCAD, LAD/ICLAD, and DVCon.
- DVCon proceedings 2025 and 2026 title listings.

**Results:**
- Only `xu2025`, `arch2026`, and `verirefine2026` surfaced on arXiv.
- `vitad2025` surfaced through web search (its abstract does not say "clock domain").
- `moyeen2025cdcai` and SV-Gap surfaced outside arXiv.
- No DAC, ICCAD, DATE, MLCAD, or LAD paper pairing LLMs with CDC was found.

### `arch2026`: Arch, AI-native HDL (arXiv 2604.05983)
- **What it does:** An HDL designed for LLM generation. Clocks and resets are types (`Clock<D>`, `Reset<...>`), so unsynchronized crossings are compile-time type errors. It emits SystemVerilog and reports 428 of 431 VerilogEval/CVDP tests passing.
- **How Aegis differs:** Arch prevents CDC errors in *new* code written in a new language. Aegis protects *existing* Verilog IP under LLM rewriting.
- **Cite in:** Related Work; Discussion (alternative "correct-by-construction" route).

### `verirefine2026`: VeriRefine (arXiv 2607.18519)
- **What it does:** A spec-refinement stage that commits each signal's clock domain and reset behavior before LLM code generation. It reports 94.0% on RTLLM v2.0 and 98.1% on VerilogEval-Human v2.
- **How Aegis differs:** It is generation-time intent capture with no CDC checking or benchmark. It is relevant as evidence that the community is starting to treat clock-domain intent explicitly.
- **Cite in:** Related Work (one clause).

Also see `xu2025`, `vitad2025`, `svgap2026`, and `moyeen2025cdcai` above.

---

## E. Mutation testing for hardware

### `mcy`: MCY, Mutation Cover with Yosys (YosysHQ)
- **What it does:** Generates thousands of mutations on the post-synthesis netlist (Yosys `mutate`). It uses formal equivalence to discard mutants that cannot change outputs, then runs the surviving mutants against a self-checking testbench to measure testbench coverage.
- **How we differ:** MCY's filter keeps only **output-changing** mutants and drops the rest. Our generator keeps mutants that are **output-equivalent but CDC-unsafe**, the exact set MCY's equivalence filter would discard. This is a crisp, citable contrast. MCY is also netlist-level and CDC-agnostic.
- **Cite in:** Related Work (mutation testing); benchmark section (generator design, since we also use Yosys).

### `yosysmutate`: Yosys `mutate` pass
- **What it does:** Modes (from `passes/sat/mutate.cc`): `inv`, `const0`, `const1`, `cnot0`, `cnot1`, and `none`. These are single-bit cell-port perturbations with even sampling via `-list N` and an optional `-ctrl` activation signal.
- **How we differ:** None of these modes is CDC-structural, since none adds or removes a flop or moves logic across a synchronizer. That motivates our custom operators.
- **Cite in:** benchmark section.

### `hampton2009fq`: Hampton, Functional qualification: a technical brief (Certess/Certitude, 2009)
- **What it does:** Describes Certitude's mutation-based functional qualification. Artificial bugs are injected into RTL, and a mutant counts as killed only if a test fails. It frames qualification in terms of activation, propagation, and detection.
- **How we differ:** Certitude-style qualification assumes a detecting checker exists. CDC mutants have no functional effect for a checker to detect, so qualification needs a structural or CDC oracle instead.
- **Cite in:** Related Work (mutation testing, classic); benchmark section.

---

## Draft fixes noticed while verifying

- **[VERIFY] placeholders that can now be filled in from the .bib:**
  - "Ares": Cuyckens et al., ARES. The ASP-DAC 2027 venue remains unverified.
  - `xu2025` title: "Rethinking LLM-Based RTL Code Optimization Via Timing Logic Metamorphosis". Authors are Zhihao Xu, Bixin Li, and Lulu Wang. The Southeast University affiliation was not checked.
  - arXiv 2406.06533: Kumar, Khan, and Mittra, "Pragmatic Formal Verification Methodology for Clock Domain Crossing (CDC)", DVCon Europe 2023.
- **Dr. RTL's ICCAD 2026 venue:** not shown on arXiv. Confirm it before camera-ready.
- **Comparison table, Xu et al. row:** change "Clock-domain *mutations*" to "semantics-preserving clock-domain transformations (added domains/synchronizers)", so it is not read as CDC-bug injection.
