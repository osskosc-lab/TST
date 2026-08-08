import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase1"))

from tst_phase1.config import CFG
from tst_phase1.generator import generate_series
from tst_phase1.learner import run_learner

SCENARIOS = ("S5", "S7", "S9")
SEED_BASE = 20_000_000
SEED_OFFSET = 50_000


def wilson(k: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return center - half, center + half


def seed_for(scenario: str, index: int) -> int:
    sid = int(scenario[1:])
    return SEED_BASE + sid * 1_000_000 + SEED_OFFSET + index


def raw_block_permute(x: np.ndarray, seed: int, block_size: int = 20) -> np.ndarray:
    """Preserve the Phase-1 baseline and permute post-baseline raw-X blocks jointly."""
    rng = np.random.default_rng(seed)
    y = x.copy()
    start = CFG.analysis_start
    end = CFG.T
    n_blocks = (end - start) // block_size
    usable = n_blocks * block_size
    blocks = y[start : start + usable].reshape(n_blocks, block_size, CFG.n_nodes).copy()
    order = rng.permutation(n_blocks)
    y[start : start + usable] = blocks[order].reshape(usable, CFG.n_nodes)
    return y


def run_one(scenario: str, index: int, raw_permuted: bool = False):
    seed = seed_for(scenario, index)
    x, truth = generate_series(scenario, seed, CFG)
    if raw_permuted:
        x = raw_block_permute(x, seed + 777_777)
    out = run_learner(x, CFG)
    ts, tq, tt = out["tau_S"], out["tau_Q"], out["tau_T"]
    complete = ts is not None and tq is not None and tt is not None
    ordered = bool(complete and ts < tq < tt)
    return {
        "scenario": scenario,
        "index": index,
        "seed": seed,
        "raw_permuted": raw_permuted,
        "tc": truth["tc"],
        "tc2": truth["tc2"],
        "tau_S": ts,
        "tau_Q": tq,
        "tau_T": tt,
        "complete": complete,
        "ordered": ordered,
    }


def stratified_event_time_null(rows, n_perm: int, seed: int = 20260808):
    triads = [r for r in rows if r["complete"]]
    groups = {s: [r for r in triads if r["scenario"] == s] for s in SCENARIOS}
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    for b in range(n_perm):
        ordered = 0
        total = 0
        for scenario, group in groups.items():
            m = len(group)
            if m == 0:
                continue
            S = np.array([r["tau_S"] for r in group])
            Q = np.array([r["tau_Q"] for r in group])
            T = np.array([r["tau_T"] for r in group])
            if m > 1:
                S = S[rng.permutation(m)]
                Q = Q[rng.permutation(m)]
            ordered += int(np.sum((S < Q) & (Q < T)))
            total += m
        null[b] = ordered / total if total else np.nan
    return null


def summarize(rows, raw_rows, n_perm: int):
    triads = [r for r in rows if r["complete"]]
    n = len(triads)
    k = sum(r["ordered"] for r in triads)
    omega = k / n if n else float("nan")
    ci = wilson(k, n)

    null = stratified_event_time_null(rows, n_perm=n_perm)
    valid = null[np.isfinite(null)]
    null_median = float(np.median(valid))
    p = float((1 + np.sum(valid >= omega)) / (1 + len(valid))) if n else float("nan")
    delta = omega - null_median if n else float("nan")

    raw_triads = [r for r in raw_rows if r["complete"]]
    rn = len(raw_triads)
    rk = sum(r["ordered"] for r in raw_triads)
    raw_omega = rk / rn if rn else float("nan")

    gates = {
        "B1_n_complete_ge_25": n >= 25,
        "B2_omega_c_ge_0.70": bool(n and omega >= 0.70),
        "B3_wilson_LCI_gt_0.50": bool(n and ci[0] > 0.50),
        "B4_matched_timing_null": bool(n and p < 0.01 and delta >= 0.10),
    }
    if all(gates.values()):
        verdict = "Conditional-order hypothesis supported in targeted regimes"
    elif not gates["B1_n_complete_ge_25"]:
        verdict = "Inconclusive: insufficient complete triads"
    elif not gates["B2_omega_c_ge_0.70"] or not gates["B3_wilson_LCI_gt_0.50"]:
        verdict = "Conditional-order hypothesis not supported"
    else:
        verdict = "Partial/conditional evidence only"

    scenario = {}
    for s in SCENARIOS:
        rr = [r for r in rows if r["scenario"] == s]
        cc = [r for r in rr if r["complete"]]
        oo = sum(r["ordered"] for r in cc)
        scenario[s] = {
            "n": len(rr),
            "transformation_detected": sum(r["tau_T"] is not None for r in rr),
            "complete_triads": len(cc),
            "ordered": oo,
            "omega_c": oo / len(cc) if cc else None,
        }

    return {
        "n_runs": len(rows),
        "n_complete_triads": n,
        "ordered_triads": k,
        "omega_c": omega,
        "wilson95": ci,
        "event_time_null_median": null_median,
        "event_time_null_p": p,
        "delta_vs_null": delta,
        "gates": gates,
        "verdict": verdict,
        "scenario_results": scenario,
        "raw_x_audit": {
            "n_runs": len(raw_rows),
            "complete_triads": rn,
            "ordered": rk,
            "omega_c": raw_omega,
            "wilson95": wilson(rk, rn),
        },
    }, null


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds-per-scenario", type=int, default=300)
    ap.add_argument("--raw-audit-seeds", type=int, default=100)
    ap.add_argument("--permutations", type=int, default=10000)
    ap.add_argument("--outdir", default="phase1b/results/confirmatory")
    args = ap.parse_args()

    rows = [run_one(s, i, False) for s in SCENARIOS for i in range(args.seeds_per_scenario)]
    raw_rows = [run_one(s, i, True) for s in SCENARIOS for i in range(args.raw_audit_seeds)]
    summary, null = summarize(rows, raw_rows, args.permutations)

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "summary_recomputed.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with (out / "runs.csv").open("w", encoding="utf-8") as f:
        cols = ["scenario", "index", "seed", "raw_permuted", "tc", "tc2", "tau_S", "tau_Q", "tau_T", "complete", "ordered"]
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join("" if r[c] is None else str(r[c]) for c in cols) + "\n")
    np.savetxt(out / "event_time_null.csv", null, delimiter=",")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
