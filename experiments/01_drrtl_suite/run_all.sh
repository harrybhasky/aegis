#!/usr/bin/env bash
# All 20 Dr. RTL designs x {aegis, vanilla, drrtl}, configs interleaved per design (smallest first).
# Resumable; when runs fail on the Claude session limit, waits 20 min and retries (up to MAX_PASSES).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; AEGIS="$HERE/../../aegis_agents"
export PATH="$HOME/.local/bin:$PATH"; MAX_PASSES="${MAX_PASSES:-12}"
cd "$AEGIS"
for pass in $(seq 1 "$MAX_PASSES"); do
  echo "=== pass $pass $(date '+%F %T')"
  python3 bench/run_suite.py --designs $(cat "$HERE/designs_all.txt") --configs aegis vanilla drrtl \
      --reps 1 --parallel 3 2>&1 | tee -a "$HERE/results/run_all.log"
  missing=0
  for d in $(cat "$HERE/designs_all.txt"); do for c in aegis vanilla drrtl; do
    [ -f "flow/runs/$d/$c.sonnet-5-5.r1/summary.json" ] || missing=$((missing+1)); done; done
  echo "=== pass $pass: $missing runs missing"
  python3 bench/report.py --out "$HERE/results" >/dev/null 2>&1 || true
  [ "$missing" -eq 0 ] && break
  if grep -qs "session limit\|usage limit" flow/runs/drrtl_*/*.log; then
    echo "=== session limit hit; sleeping 20 min"; sleep 1200
  else
    echo "=== remaining failures are not session-limit failures; stopping for a human to look"; break
  fi
done
echo "=== finished $(date '+%F %T')"
