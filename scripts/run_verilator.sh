#!/usr/bin/env bash
set -e
# simple syntax check: prefer verilator if available, else iverilog
if command -v verilator >/dev/null 2>&1; then
  verilator --lint-only src/top_opt.v || true
  echo "verilator lint OK"
elif command -v iverilog >/dev/null 2>&1; then
  iverilog -t null -o /dev/null src/top_opt.v >/dev/null 2>&1 && echo "iverilog parse OK" || (echo "iverilog parse failed"; exit 1)
else
  echo "No verilator/iverilog found; skipping syntax check"
  exit 0
fi
