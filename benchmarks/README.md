# Benchmarks for the Aegis paper

Shallow git clones, downloaded 2026-10-02. Re-fetch with `git clone --depth 1 <url>`.

## A. Benchmarks used by Dr. RTL (for head-to-head comparison)

| Dir | Source | Contents | License |
|---|---|---|---|
| `Dr_RTL/` | github.com/hkust-zhiyao/Dr_RTL | 20 human-written designs in `rtl_dataset/` (v0), DC/Jasper SEC TCL in `syn_flow_eda/scr/`, Nangate45 `.db`, agent + skill files in `.claude/` | **No LICENSE file**: ask the authors before redistributing |
| `RTLRewriter-Bench/` | github.com/yaoxufeng/RTLRewriter-Bench | short_benchmark + long_benchmark (cpu, huffman, cnn, fft, vending_machine). Dr. RTL Sec. 5.3 uses "all large designs" from it | No LICENSE file |
| `RTL-OPT/` | github.com/hkust-zhiyao/RTL-OPT | 40 design + `_ref` pairs (arXiv:2601.01765), cited as [23] in Dr. RTL | See `RTL-OPT/LICENSE` |

Dr. RTL protocol (to reproduce): DC + Nangate45, clock period **0.1 ns**, Jasper SEC,
10 iterations x 5 candidates, 4-fold cross-validation for the skill library, Claude Opus backbone.
Design top/clk/rst table: `Dr_RTL/syn_flow/design_all.json`.

### Multi-clock designs inside Dr. RTL's set (each is constrained on ONE clock only)
- `FIFO.v0.v`: dual-clock (`clk_in`/`clk_out`). Every synchronizer (`read_sync`, `write_sync`,
  `flush_sync`) is clocked by the **source** domain, not the destination, so the crossings
  are effectively unsynchronized. Their `syn.tcl` creates a single clock.
- `communication.v0.v`: gated derived `serial_clk`.
- `i2c.v0.v`, `simple_spi.v0.v`, `SPI.v0.v`: secondary edges (`sck`, `nReset`).

## B. Multi-clock / CDC benchmarks (`multiclock/`)

| Dir | Source | Useful modules | License |
|---|---|---|---|
| `async_fifo/` | github.com/dpretet/async_fifo | Cummings-style gray FIFO (`sync_r2w`, `sync_w2r`, `wptr_full`, `rptr_empty`) + bidirectional variants | MIT |
| `common_cells/` | github.com/pulp-platform/common_cells | `cdc_2phase`, `cdc_4phase`, `cdc_fifo_gray`, `cdc_fifo_2phase`, `cdc_reset_ctrlr` (+ clearable) | Solderpad 0.51 |
| `opentitan/` (sparse: `hw/ip/prim*/rtl`) | github.com/lowRISC/opentitan | `prim_fifo_async`, `prim_sync_reqack(_data)`, `prim_pulse_sync`, `prim_multibit_sync`, `prim_reg_cdc`, `prim_sync_slow_fast`, `prim_cdc_rand_delay` (metastability-delay model) | Apache-2.0 |
| `verilog-axis/` | github.com/alexforencich/verilog-axis | `axis_async_fifo`, `axis_async_fifo_adapter` | MIT |
| `verilog-axi/` | github.com/alexforencich/verilog-axi | `axil_cdc`, `axil_cdc_rd/wr` | MIT |
| `verilog-ethernet/` | github.com/alexforencich/verilog-ethernet | `eth_mac_1g_*_fifo`, `eth_mac_10g_fifo` (logic + RX + TX clocks) | MIT |
| `ethmac/` | github.com/freecores/ethmac | OpenCores `eth_top` (wb_clk, mtx_clk, mrx_clk; likely the source of our `eth_top`) | LGPL |
| `wb2axip/` | github.com/ZipCPU/wb2axip | `afifo`, `axixclk`, `wbxclk`, `apbxclk`, with formal (SBY) properties | Apache-2.0 |
| `uart16550/` | github.com/olofk/uart16550 | baud-tick domain | LGPL |

Suggested tiers: (1) small CDC primitives, for lock-precision/recall tests;
(2) mid-size async FIFOs/bridges (axis_async_fifo, afifo, cdc_fifo_gray, prim_fifo_async);
(3) system-scale designs (eth_mac_1g_rgmii_fifo, ethmac eth_top, our soc_top).

## C. CDC protocol primitives added as Aegis designs (2026-10-08)

Added to broaden the CDC suite beyond Gray FIFOs, with handshake, pulse, req/ack and reset/clear-sequencing protocols.
They are set up with `python3 bench/setup_designs.py --suite cdc --calibrate --only <name...>`; `--only` leaves every
other design untouched. Phase 1 and the baselines come from `bench/run_baseline.py --designs <name...>`, and the rows are
in `aegis_agents/bench/results/baseline.{json,md}`.

**Conversion.** The SystemVerilog sources (PULP, OpenTitan) are converted once to plain Verilog-2005 with
sv2v 0.0.13 (Homebrew arm64 bottle) by `multiclock/converted/convert.sh`. The output goes to `converted/<design>/<design>.v`,
alongside the upstream `LICENSE`, the parameter shim (`*_w8.sv` / `*_cfg.sv`, which only fixes widths and type parameters)
and a `SOURCE.txt` giving the exact sv2v command and source commit. Upstream RTL is not edited. `-DSYNTHESIS` selects the
dummy assertion macros. sv2v drops comments, so convert.sh prepends a 4-line provenance and license header.
Source commits: common_cells `e73baaec`, tech_cells_generic v0.2.14 `3a3de736` (cloned for `tc_sync`, pinned by
common_cells' Bender.lock), and opentitan `0cd56ca0`. The wb2axip designs are used as-is, as plain Verilog, from commit `2e8d3bc2`.
Each design has a thin plain-Verilog `bench_top.v` (`<design>_bench`) that exposes every port; it is inline in setup_designs.py.

**Lint.** Every design passes iverilog `-g2012` and Verilator with the Phase 4 flags (`-Wno-lint -Wno-style -Wno-MULTIDRIVEN`).
The converted designs also pass iverilog `-g2005`. Under `verilator -Wall` the only warnings are WIDTHEXPAND, from sv2v
rendering `'0` as `1'sh0`, and UNUSED. apbxclk and wbxclk need `-g2012`, as the existing `afifo` already does: upstream
uses a localparam in the parameter port list and an output port driven onto a reg.

Crossings are listed as sync / gray / qualified / R2 (1-flop) / R1 (unsynchronized). Every design has two asynchronous
clocks, and every Phase 1 ingest took 0.3 to 0.5 s. Contracts: **0 proven on every design**; see the issues below.
WNS is the timing-driven synthesis baseline at the calibrated periods (ratio 0.75).

| Design | Upstream module(s) | Protocol | Clocks (calibrated ns) | Flops | Crossings s/g/q/R2/R1 | Locked lines | WNS synth (ns) | License |
|---|---|---|---|---|---|---|---|---|
| `cc_cdc_2phase` | common_cells `cc_cdc_2phase` (+ `tc_sync`), 8-bit | 2-phase handshake | src_clk_i 0.22, dst_clk_i 0.25 | 7 | 0/0/0/1/2 | 30 | -0.07 | SHL-0.51 |
| `cc_cdc_4phase` | `cc_cdc_4phase`, Decoupled=1, + `cc_spill_register` | 4-phase handshake | 0.21 / 0.32 | 11 | 0/0/0/0/3 | 34 | -0.07 | SHL-0.51 |
| `cc_cdc_fifo_gray` | `cc_cdc_fifo_gray`, Width 8, LogDepth 3 | Gray FIFO (per-bit synced pointers) | 0.73 / 0.96 | 15 | 0/0/0/0/9 | 30 | -0.32 | SHL-0.51 |
| `cc_cdc_fifo_2phase` | `cc_cdc_fifo_2phase` (pointers carried by `cc_cdc_2phase`) | FIFO over 2-phase handshakes | 0.40 / 0.38 | 24 | 0/0/0/2/4 | 22 | -0.13 | SHL-0.51 |
| `cc_cdc_reset_ctrlr` | `cc_cdc_reset_ctrlr` (+ `cc_cdc_4phase` Decoupled=0, SendResetMsg=1) | reset/clear sequencing over a 4-phase CDC | a 0.31 / b 0.31 | 22 | 0/0/0/2/4 | 34 | -0.10 | SHL-0.51 |
| `cc_cdc_2phase_clearable` | `cc_cdc_2phase_clearable` (+ `cc_cdc_reset_ctrlr_half`), SyncStages 3 | 2-phase handshake + clear/reset sequencing | 0.39 / 0.34 | 33 | 0/0/0/3/6 | 56 | -0.13 | SHL-0.51 |
| `prim_fifo_async` | OpenTitan `prim_fifo_async` (+ `prim_flop_2sync`, `prim_flop`), Width 8, Depth 4 | Gray FIFO | wr 0.32 / rd 0.35 | 9 | 0/2/0/0/0 | 34 | -0.11 | Apache-2.0 |
| `prim_sync_reqack` | `prim_sync_reqack`, NRZ | req/ack (2-phase) | 0.14 / 0.14 | 8 | 2/0/0/0/0 | 16 | -0.05 | Apache-2.0 |
| `prim_sync_reqack_data` | `prim_sync_reqack_data`, Width 8, DataSrc2Dst=0, DataReg=1 | req/ack + data register | src 0.14 / dst 0.22 | 9 | 2/0/0/0/0 | 21 | -0.08 | Apache-2.0 |
| `prim_pulse_sync` | `prim_pulse_sync` | pulse (toggle + 2FF + edge detect) | src 0.13 / dst 0.10 | 4 | 1/0/0/0/0 | 12 | -0.05 | Apache-2.0 |
| `prim_reg_cdc` | `prim_reg_cdc` + `prim_reg_cdc_arb` (DstWrReq=1) + `prim_pulse_sync` + `prim_sync_reqack`, 8-bit | register CDC: pulse + req/ack + qualified data | src 0.34 / dst 0.35 | 19 | 3/0/4/0/0 | 33 | -0.12 | Apache-2.0 |
| `apbxclk` | wb2axip `apbxclk`, AW 8, DW 8, OPT_REGISTERED=1 | 4-phase req/ack + reset synchronizers | S 0.19 / M 0.24 | 23 | 2/0/1/1/0 | 22 | -0.07 | Apache-2.0 (file header) |
| `wbxclk` | wb2axip `wbxclk` + `afifo`, AW 8, DW 8, LGFIFO 3 | 2 Gray FIFOs + reset sync | wb 0.52 / xclk 0.49 | 36 | 0/4/0/0/0 | 34 | -0.17 | Apache-2.0 (file header) |
| `axixclk` | wb2axip `axixclk` + 5x `afifo`, ID 2, DATA 8, ADDR 6, LGFIFO 3 | 5 Gray FIFOs + 3-flop reset sync | S 0.42 / M 0.57 | 51 | 0/10/0/0/0 | 45 | -0.19 | Apache-2.0 (file header) |

wb2axip has no LICENSE file in the repo; each file states Apache-2.0 in its header, and the files are copied unchanged.

Not added:
- `eth_mac_10g_fifo`: Yosys elaboration does not finish. It ran over 8 min at DATA_WIDTH 64 and hit a 120 s limit at 32.
  The cause is the function-based CRC mask in `verilog-ethernet/rtl/lfsr.v:220-257`, used by `axis_xgmii_tx_*`.
- `eth_mac_1g_rgmii_fifo`: needs DDR I/O primitives and a 90-degree clock, and adds no protocol type beyond `eth_mac_1g_fifo`.

### Phase 1 issues on these designs (tool findings; `tools/` not modified)

**No pre-existing CDC bug was found in any of these designs.** Every R1/R2 that Phase 1 reports is a tool false positive:

1. **Vector shift-register synchronizers are not recognized.** This produces **21 false R1/R2s across all six PULP designs.**
   `tc_sync` keeps its stages in one vector: `reg_q <= {reg_q[Stages-2:0], serial_i}` (`tech_cells_generic/src/rtl/tc_sync.sv:30-34`).
   Yosys builds a single 2-bit `$adff` with `D = {reg_q[0], <async input>}`. `aegis_ingest.py:370/375` marks the edge
   non-direct because the D pin has two driving cells, and `next_stage()` (`:379-388`) looks for a separate cell.
   So `async_req`/`async_ack` into `i_sync.reg_q` is reported as R1. The data captures they qualify are reported as R2,
   or as R1 for the spill-register captures. Example: `data_dst_q`, loaded only when `req_synced != req_synced_q1`
   (`common_cells/src/cc_cdc_2phase.sv:175,196`), is reported as `R2: u.i_cdc.async_data -> dst_data_o`.
   Check: replacing `tc_sync` with two discrete flops, in a scratch copy only, turns all 21 into 2 to 8 synchronizers
   plus 1 to 3 qualified captures per design, with zero issues left.
2. **A Gray bus synchronized bit by bit is not seen as a Gray bus.** This is a false negative for Gray contracts.
   `cc_cdc_fifo_gray` syncs each pointer bit through its own `tc_sync` (`cc_cdc_fifo_gray.sv:329-330, 392-393`).
   Even with the fix from item 1, the tool sees 8 one-bit synchronizers and no `gray_candidate`, because
   `aegis_ingest.py:431` needs `bits > 1` per (src, dst) register pair. No Gray contract or Gray audit is produced.
3. **A qualifier folded into a sync-reset pin is ignored.** This is the false R2 on apbxclk.
   `if (s_request && s_ack) s_prdata <= m_prdata; else s_prdata <= 0;` (`wb2axip/rtl/apbxclk.v:251-255`) becomes a
   `$sdff` with `D = m_prdata` and `SRST = s_request && s_ack`. `ff_data_bits` skips SRST (`aegis_ingest.py:42, 276`),
   so the synchronized `s_ack` qualifier is invisible and the crossing is reported as a 1-flop synchronizer.
4. **Gray contracts are never calibrated** on prim_fifo_async, wbxclk or axixclk. The warning is "launch register is
   not a port of a module with a reset; left immutable" (`aegis_ingest.py:521, 542`). This is the same limitation that
   gives 0 contracts on the existing afifo, axis_async_fifo and eth_mac_1g_fifo; only async_fifo and soc prove Gray
   contracts. The affected Gray logic stays immutable, so this is conservative.
5. **A register named after a net alias gets a vacuous lock** (hash of the empty string, no lines locked):
   - prim_fifo_async launch registers `fifo_{w,r}ptr_gray_q` (`prim_fifo_async.sv:67-72, 100-105`) are named `u.u_fifo.sync_{w,r}ptr.d_i`.
   - In prim_reg_cdc, `src_q` is named `dst_wd_o`, `src_busy_q` is named `src_busy_o`, and the launch register `u.u_reg.dst_qs` gets the same empty lock.
   - In apbxclk, `s_pslverr` is named `u.S_APB_PSLVERR`.

   The assignment regex in `lock_ff_block` searches for `<alias> <=` and never matches. This also affects existing designs:
   axil_cdc (9 entries) and soc (`hs_data`, `hs_out`).
6. **Crossings Phase 1 cannot see:**
   - **Port-sourced data crossings.** Examples: apbxclk `m_paddr <= S_APB_PADDR` (`apbxclk.v:226-228`), the data outputs
     of `prim_sync_reqack_data`, and `prim_reg_cdc` `dst_wd_o`. Ports have no clock domain in the SDC.
   - **Reset-domain crossings.** ARST pins are skipped. Examples: apbxclk `full_reset` is reset by M-domain `M_PRESETn`
     (`apbxclk.v:94-98`), and wbxclk `xck_reset` is set by wb-domain `bus_abort` (`wbxclk.v:181-186`).
   - **Port-fed reset synchronizers** are not locked. Examples: axixclk `mreset` (`axixclk.v:155-161`) and apbxclk
     `M_PRESETn` (`apbxclk.v:89-93`). axixclk's `(* ASYNC_REG *)` sits on the `initial` statement rather than the reg, so
     the attribute lock misses it too. OpenSTA does check these resets (recovery/removal, path group `asynchronous`).
   - **R1/R2 crossings get no launch/capture lock**, despite the module docstring (`aegis_ingest.py:609-638` covers only
     sync, gray and qualified crossings). On the PULP designs the `dont_touch` attributes still lock most of these flops.
