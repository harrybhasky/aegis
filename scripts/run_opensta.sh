#!/usr/bin/env bash
set -e
if command -v opensta >/dev/null 2>&1; then
  opensta scripts/sta.tcl
elif command -v sta >/dev/null 2>&1; then
  sta scripts/sta.tcl
else
  echo "opensta/sta not found on PATH — mocking output"
  echo "Worst negative slack (WNS) -0.500"
  echo "Total negative slack (TNS) -15.0"
fi
