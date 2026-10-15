#!/usr/bin/env bash
# Experiment 01: Dr. RTL's 20 single-clock designs.
#   ./run.sh pilot            2 smallest designs x {aegis,vanilla} x 1 rep
#   ./run.sh full [REPS]      all 20 designs x CONFIGS x REPS (default 1)
# CONFIGS (env) defaults to "aegis scalar vanilla". Resumable: finished runs are skipped.
# Spends Claude usage (claude -p). Runs land in aegis_agents/flow/runs/<design>/<config>.<model>.r<k>/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
AEGIS="$HERE/../../aegis_agents"
export PATH="$HOME/.local/bin:$PATH"
STAGE="${1:-pilot}"; REPS="${2:-1}"
MODEL="${MODEL:-claude-sonnet-5-5}"
if [ "$STAGE" = pilot ]; then CONFIGS="${CONFIGS:-aegis vanilla}"; LIST="$HERE/designs_pilot.txt"
else CONFIGS="${CONFIGS:-aegis scalar vanilla}"; LIST="$HERE/designs_all.txt"; fi
cd "$AEGIS"
python3 bench/run_suite.py --designs $(cat "$LIST") --configs $CONFIGS --reps "$REPS" \
    --model "$MODEL" --parallel 2 2>&1 | tee -a "$HERE/results/$STAGE.log"
python3 bench/report.py --out "$HERE/results"
