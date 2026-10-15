#!/usr/bin/env python3
"""
orchestrator_langgraph.py
Stateful multi-agent RTL timing optimization orchestrator using LangGraph (if installed)
and Google Gemini via langchain-google-genai (ChatGoogleGenerativeAI).

Contains: StateDict, EDA runners, GenAI optimizer node, evaluation node, PPA scoring,
formal verification hooks (wrappers call external scripts), and testable parser functions.

Run: python orchestrator_langgraph.py --rtl src/example_top.v --max-iterations 5
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from typing import TypedDict, Optional

# Optional imports
try:
    import langgraph as lg  # type: ignore
    HAS_LANGGRAPH = True
except Exception:
    HAS_LANGGRAPH = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
    from langchain.schema import HumanMessage  # type: ignore
    HAS_GEMINI = True
except Exception:
    HAS_GEMINI = False

# State definition
class StateDict(TypedDict):
    original_rtl: str
    current_rtl: str
    wns: float
    tns: float
    area: float
    sta_report: str
    iteration: int
    max_iterations: int
    status: str
    history: list

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("orchestrator")

# Utilities
def safe_run(cmd, cwd=None, timeout=300):
    logger.debug("Running command: %s", cmd)
    try:
        completed = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False)
        return completed.returncode, completed.stdout
    except subprocess.TimeoutExpired as e:
        logger.error("Command timed out: %s", cmd)
        return 1, f"TIMEOUT: {e}"

# Parsers (exported for tests)
def parse_wns_from_opensta(output: str) -> Optional[float]:
    patterns = [r"WNS[: ]+(-?\d+\.\d+)", r"Worst negative slack.*?(-?\d+\.\d+)", r"worst.*slack[:= ]+(-?\d+\.\d+)", r"worst_slack[: =]+(-?\d+\.\d+)"]
    for p in patterns:
        m = re.search(p, output, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                continue
    return None

def parse_tns_from_opensta(output: str) -> Optional[float]:
    patterns = [r"TNS[: ]+(-?\d+\.\d+)", r"Total negative slack.*?(-?\d+\.\d+)", r"tns[: =]+(-?\d+\.\d+)"]
    for p in patterns:
        m = re.search(p, output, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                continue
    return None

def parse_area_from_yosys(output: str) -> Optional[float]:
    patterns = [r"Estimated area[:= ]+([\d,]+(?:\.\d+)?)", r"area[:= ]+([\d,]+(?:\.\d+)?)", r"Total area[:= ]+([\d,]+(?:\.\d+)?)"]
    for p in patterns:
        m = re.search(p, output, re.IGNORECASE)
        if m:
            text = m.group(1).replace(",", "")
            try:
                return float(text)
            except Exception:
                continue
    return None

# PPA scoring
def compute_ppa_score(wns: float, tns: float, area: float, alpha: float, beta: float, gamma: float) -> float:
    inv_area = (1.0 / area) if area > 0 else 0.0
    return alpha * wns + beta * tns + gamma * inv_area

# Node implementations

def run_eda_tools_node(state: StateDict) -> StateDict:
    logger.info("Node: run_eda_tools_node (iteration %d)", state["iteration"])
    os.makedirs("src", exist_ok=True)
    top_path = os.path.join("src", "top_opt.v")
    with open(top_path, "w", encoding="utf-8") as f:
        f.write(state["current_rtl"])
    logger.debug("Wrote RTL to %s", top_path)

    # Export RTL_FILE for synth.tcl
    prev = os.environ.get("RTL_FILE")
    os.environ["RTL_FILE"] = top_path
    try:
        rc_y, out_y = safe_run(["yosys", "-c", "scripts/synth.tcl"])
    finally:
        if prev is None:
            os.environ.pop("RTL_FILE", None)
        else:
            os.environ["RTL_FILE"] = prev

    # Run OpenSTA via wrapper
    rc_s, out_s = safe_run(["bash", "scripts/run_opensta.sh"])

    state["sta_report"] = "\n\n=== YOSYS OUTPUT ===\n\n" + out_y + "\n\n=== OPENSTA OUTPUT ===\n\n" + out_s
    wns = parse_wns_from_opensta(out_s) or parse_wns_from_opensta(out_y)
    tns = parse_tns_from_opensta(out_s) or parse_tns_from_opensta(out_y) or 0.0
    area = parse_area_from_yosys(out_y) or -1.0

    state["wns"] = wns if wns is not None else -9999.0
    state["tns"] = tns
    state["area"] = area

    # record history
    entry = {"iteration": state["iteration"], "wns": state["wns"], "tns": state["tns"], "area": state["area"], "status": state.get("status")}
    state.setdefault("history", []).append(entry)
    # persist brief log
    try:
        with open("logs/iteration_history.json", "w") as h:
            json.dump(state["history"], h, indent=2)
    except Exception:
        logger.debug("Could not write history log")

    logger.info("Parsed WNS=%s TNS=%s Area=%s", state["wns"], state["tns"], state["area"])
    return state


def genai_optimizer_node(state: StateDict, model: Optional[ChatGoogleGenerativeAI] = None) -> StateDict:
    logger.info("Node: genai_optimizer_node (iteration %d)", state["iteration"])
    prompt = f"""
You are a hardware RTL optimization assistant. Inputs:
- Current RTL:
{state['current_rtl']}

- STA report:
{state['sta_report']}

Task: analyze critical path and provide a minimal modified Verilog module (or modules) that improves timing. Return only a fenced ```verilog ... ``` block when possible.
"""
    response_text = None
    if HAS_GEMINI and model is not None:
        try:
            human = HumanMessage(content=prompt)
            result = model.generate([[human]]) if hasattr(model, "generate") else model([human])
            if hasattr(result, "generations"):
                response_text = result.generations[0][0].text
            elif isinstance(result, list):
                response_text = result[0].text if result else ""
            else:
                response_text = str(result)
        except Exception as e:
            logger.exception("Gemini call failed: %s", e)
            response_text = None
    else:
        logger.warning("Gemini not available; using placeholder optimization.")
        response_text = """```verilog
// placeholder top module with one pipeline stage
module top(input clk, input rst, input [31:0] in, output reg [31:0] out);
  reg [31:0] s1;
  always @(posedge clk) begin
    if (rst) begin s1 <= 0; out <= 0; end else begin s1 <= in; out <= s1; end
  end
endmodule
```"""

    # Ensure logs dir exists and save raw genai response for auditing
    try:
        os.makedirs("logs", exist_ok=True)
        resp_path = os.path.join("logs", f"genai_resp_iter_{state['iteration']}.txt")
        with open(resp_path, "w", encoding="utf-8") as rf:
            rf.write(response_text if response_text is not None else "")
        logger.info("Saved raw GenAI response to %s", resp_path)
    except Exception:
        logger.exception("Failed to write GenAI response log")

    if not response_text:
        logger.error("No response from Gemini; skipping change.")
        state["iteration"] += 1
        return state

    m = re.search(r"```(?:verilog)?\s*(.*?)```", response_text, re.DOTALL | re.IGNORECASE)
    if m:
        verilog_code = m.group(1).strip()
    else:
        m2 = re.search(r"(module\b.*?endmodule)", response_text, re.DOTALL | re.IGNORECASE)
        verilog_code = m2.group(1).strip() if m2 else None

    if not verilog_code:
        logger.warning("Could not extract Verilog from model response.")
        state["iteration"] += 1
        return state

    # Update RTL (replace top if a top module present, else replace entire file)
    state["current_rtl"] = verilog_code
    state["iteration"] += 1
    logger.info("Updated RTL; iteration=%d", state["iteration"])

    # Run quick syntax check (verilator / iverilog wrapper)
    rc_v, out_v = safe_run(["bash", "scripts/run_verilator.sh"])
    if rc_v != 0:
        logger.warning("Verilator/iverilog reported issues; saving output to logs/verif_%d.log", state["iteration"])
        with open(f"logs/verif_{state['iteration']}.log", "w") as vf:
            vf.write(out_v)
    else:
        logger.info("Syntax check passed (verilator/iverilog)")

    # Optional formal verification hook: run modular EQY on modified submodule
    rc_eqy, out_eqy = safe_run(["bash", "scripts/run_eqy.sh"])
    if rc_eqy != 0:
        logger.warning("Formal EQY reported issues (rc=%d). Output logged.", rc_eqy)
        with open(f"logs/eqy_{state['iteration']}.log", "w") as ef:
            ef.write(out_eqy)
    else:
        logger.info("Formal verifier returned success (or was mocked)")

    return state


def evaluate_result_node(state: StateDict, alpha=1.0, beta=1.0, gamma=1.0) -> StateDict:
    logger.info("Node: evaluate_result_node (iteration %d)", state["iteration"])
    if state["wns"] >= 0.0:
        state["status"] = "SUCCESS"
    elif state["iteration"] >= state["max_iterations"]:
        state["status"] = "MAX_ITERATIONS_REACHED"
    else:
        state["status"] = "CONTINUE"
    # compute PPA score and attach
    score = compute_ppa_score(state.get("wns", -9999.0), state.get("tns", 0.0), state.get("area", -1.0), alpha, beta, gamma)
    state.setdefault("history", []).append({"ppa_score": score, "iter": state["iteration"]})
    logger.info("Status=%s PPA_score=%.6f", state["status"], score)
    return state

# Orchestration loop (fallback if langgraph not available)
def run_orchestration(initial_state: StateDict, alpha=1.0, beta=1.0, gamma=1.0):
    logger.info("Starting orchestration. LangGraph=%s Gemini=%s", HAS_LANGGRAPH, HAS_GEMINI)
    model = None
    if HAS_GEMINI:
        try:
            model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
        except Exception:
            model = None
    state = initial_state.copy()

    # initial synthesis/sta baseline
    state = run_eda_tools_node(state)

    while True:
        state = evaluate_result_node(state, alpha=alpha, beta=beta, gamma=gamma)
        if state["status"] in ("SUCCESS", "MAX_ITERATIONS_REACHED"):
            break
        state = genai_optimizer_node(state, model)
        state = run_eda_tools_node(state)
        state = evaluate_result_node(state, alpha=alpha, beta=beta, gamma=gamma)
        if state["status"] in ("SUCCESS", "MAX_ITERATIONS_REACHED"):
            break
        if state["iteration"] >= state["max_iterations"]:
            state["status"] = "MAX_ITERATIONS_REACHED"
            break
        time.sleep(0.2)
    logger.info("Orchestration finished with status=%s", state["status"])
    return state

# CLI & helper

def print_ppasummary(state: StateDict, alpha=1.0, beta=1.0, gamma=1.0):
    header = f"{'Iter':>4} | {'WNS':>8} | {'TNS':>8} | {'Area':>10} | {'Status':>20} | {'PPA':>8}"
    print(header)
    print("-" * len(header))
    score = compute_ppa_score(state.get('wns', -9999.0), state.get('tns', 0.0), state.get('area', -1.0), alpha, beta, gamma)
    print(f"{state['iteration']:4d} | {state['wns']:8.3f} | {state['tns']:8.3f} | {state['area']:10.3f} | {state['status']:>20} | {score:8.6f}")
    print("-" * len(header))


def load_rtl_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rtl', required=True)
    parser.add_argument('--max-iterations', type=int, default=5)
    parser.add_argument('--alpha', type=float, default=1.0)
    parser.add_argument('--beta', type=float, default=1.0)
    parser.add_argument('--gamma', type=float, default=1.0)
    args = parser.parse_args()

    initial_rtl = load_rtl_file(args.rtl)
    state: StateDict = {
        'original_rtl': initial_rtl,
        'current_rtl': initial_rtl,
        'wns': -9999.0,
        'tns': 0.0,
        'area': -1.0,
        'sta_report': '',
        'iteration': 0,
        'max_iterations': args.max_iterations,
        'status': 'NOT_STARTED',
        'history': [],
    }

    final = run_orchestration(state, alpha=args.alpha, beta=args.beta, gamma=args.gamma)
    print_ppasummary(final, alpha=args.alpha, beta=args.beta, gamma=args.gamma)

if __name__ == '__main__':
    main()
