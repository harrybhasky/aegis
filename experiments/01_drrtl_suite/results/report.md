# AEGIS benchmark report

Generated from 12 run summaries. Changes are relative to the synthesis-only baseline (Yosys + delay-driven ABC, Nangate45, OpenSTA); negative WNS/TNS % = less negative slack.

## T1. Results per design and configuration

| Design | Config | Model | Runs | ΔWNS % | ΔTNS % | ΔArea % | SEC pass % | Lock viol. | CDC viol. | Tokens (k) | Wall (min) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| async_fifo | vanilla | sonnet-5-5 | 1 | -81.25 | -33.10 | 8.59 | 0.00 | 0.00 | 15.00 | 174.10 | 4.37 |
| drrtl_communication | vanilla | sonnet-5-5 | 1 | -34.88 | -37.34 | 2.31 | 0.00 | 0.00 | 0.00 | 108.30 | 3.37 |
| drrtl_controller | aegis | sonnet-5-5 | 1 | -5.13 | -1.51 | 0.25 | 20.00 | 0.00 | 0.00 | 652.58 | 9.96 |
| drrtl_controller | drrtl | sonnet-5-5 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 295.43 | 3.78 |
| drrtl_controller | vanilla | sonnet-5-5 | 1 | -15.38 | -16.25 | 0.74 | 0.00 | 0.00 | 0.00 | 368.12 | 5.19 |
| drrtl_ticket_machine | aegis | sonnet-5-5 | 1 | -57.69 | -48.97 | -15.73 | 70.00 | 0.00 | 0.00 | 427.21 | 9.07 |
| drrtl_ticket_machine | drrtl | sonnet-5-5 | 1 | -23.08 | -18.04 | -7.49 | 16.00 | 0.00 | 0.00 | 242.31 | 3.65 |
| drrtl_ticket_machine | vanilla | sonnet-5-5 | 1 | -69.23 | -73.20 | -34.83 | 0.00 | 0.00 | 0.00 | 85.32 | 1.52 |
| drrtl_uart | drrtl | sonnet-5-5 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1605.36 | 10.01 |
| drrtl_uart | vanilla | sonnet-5-5 | 1 | -49.23 | -20.21 | 2.51 | 0.00 | 0.00 | 0.00 | 185.85 | 9.28 |
| soc | aegis | sonnet-5-5 | 1 | 0.00 | -28.74 | -3.43 | 53.33 | 0.00 | 0.00 | 132.39 | 4.06 |
| soc | vanilla | sonnet-5-5 | 1 | 0.00 | -29.04 | -3.43 | 4.00 | 0.00 | 24.00 | 228.35 | 5.55 |

ΔWNS/ΔTNS are reported as improvement (positive = better).

## T2. Per-domain WNS before / after (first run of each configuration)

| Design | Config | Domain | WNS base (ns) | WNS final (ns) | TNS base | TNS final |
|---|---|---|---|---|---|---|
| async_fifo | vanilla | rclk | -0.16 | 0.12 | -0.28 | 0 |
| async_fifo | vanilla | wclk | -0.12 | -0.03 | -2.59 | -1.92 |
| drrtl_communication | vanilla | asynchronous | 0.15 | 0.15 | 0 | 0 |
| drrtl_communication | vanilla | clk | -0.43 | -0.28 | -30.72 | -19.25 |
| drrtl_controller | aegis | asynchronous | 0.15 | 0.15 | 0 | 0 |
| drrtl_controller | aegis | clk | -0.39 | -0.37 | -9.29 | -9.15 |
| drrtl_controller | drrtl | asynchronous | 0.15 | 0.15 | 0 | 0 |
| drrtl_controller | drrtl | clk | -0.39 | -0.39 | -9.29 | -9.29 |
| drrtl_controller | vanilla | asynchronous | 0.15 | 0.15 | 0 | 0 |
| drrtl_controller | vanilla | clk | -0.39 | -0.33 | -9.29 | -7.78 |
| drrtl_ticket_machine | aegis | clk | -0.26 | -0.11 | -1.94 | -0.99 |
| drrtl_ticket_machine | drrtl | clk | -0.26 | -0.2 | -1.94 | -1.59 |
| drrtl_ticket_machine | vanilla | clk | -0.26 | -0.08 | -1.94 | -0.52 |
| drrtl_uart | drrtl | clk | -0.65 | -0.65 | -24.24 | -24.24 |
| drrtl_uart | vanilla | clk | -0.65 | -0.33 | -24.24 | -19.34 |
| soc | aegis | clk_div | 1.35 | 1.35 | 0 | 0 |
| soc | aegis | clk_r | 0.19 | 0.35 | 0 | 0 |
| soc | aegis | clk_w | -0.04 | 0.04 | -0.96 | 0 |
| soc | aegis | clk_x | -0.38 | -0.38 | -2.38 | -2.38 |
| soc | vanilla | clk_div | 1.35 | 1.35 | 0 | 0 |
| soc | vanilla | clk_r | 0.19 | 0.35 | 0 | 0 |
| soc | vanilla | clk_w | -0.04 | 0.04 | -0.96 | 0 |
| soc | vanilla | clk_x | -0.38 | -0.38 | -2.38 | -2.37 |

## T3. Candidate rejection reasons (summed over runs)

| Config | Model | Candidates | Reasons |
|---|---|---|---|
| aegis | sonnet-5-5 | 75 | sec_fail: 27, final_regression: 4, envelope: 2, no_code: 2 |
| drrtl | sonnet-5-5 | 75 | sec_fail: 33 |

## T4. End-to-end check of each final design against the original RTL

| Design | Run | Phase 4 vs v0 | Measured violations | EQY (top) vs v0 |
|---|---|---|---|---|
| async_fifo | vanilla.sonnet-5-5.r1 | pass | cdc | FAIL |
| drrtl_communication | vanilla.sonnet-5-5.r1 | pass | none | FAIL |
| drrtl_controller | aegis.sonnet-5-5.r1 | pass | none | PASS |
| drrtl_controller | vanilla.sonnet-5-5.r1 | reject | none | FAIL |
| drrtl_ticket_machine | aegis.sonnet-5-5.r1 | pass | none | PASS |
| drrtl_ticket_machine | drrtl.sonnet-5-5.r1 | reject | none | PASS |
| drrtl_ticket_machine | vanilla.sonnet-5-5.r1 | reject | none | FAIL |
| drrtl_uart | vanilla.sonnet-5-5.r1 | pass | none | FAIL |
| soc | aegis.sonnet-5-5.r1 | pass | none | PASS |
| soc | vanilla.sonnet-5-5.r1 | pass | none | PASS |
