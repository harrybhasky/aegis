#!/bin/bash
# wait for the running tranche, re-run it (resumable: completed runs are skipped), then build the report
cd "$(dirname "$0")/.."
while pgrep -f "bench/run_suite.py" >/dev/null; do sleep 30; done
python3 bench/run_suite.py --designs soc async_fifo afifo axis_async_fifo axil_cdc drrtl_fifo_2clk eth_mac_1g_fifo \
  --configs aegis vanilla --reps 1 --model claude-sonnet-5-5 --parallel 2 >> bench/tranche1.log 2>&1
python3 bench/report.py > bench/results/report_stdout.txt 2>&1
echo "tranche1 complete $(date)" >> bench/tranche1.log
