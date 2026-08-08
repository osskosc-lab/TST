import argparse
import csv
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy.stats import chi2_contingency
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase1"))

from tst_phase1.config import CFG
from tst_phase1.generator import (
    add_edges,
    delete_edges,
    edge_set,
    reweight_same_topology,
    reverse_edges,
    sample_base_W,
)
from tst_phase1.learner import run_learner

STRUCTURAL = (
    "R1_reverse25",
    "R2_reverse50",
    "R3_mixed_abrupt",
    "R4_mixed_gradual",
    "R5_add_heavy",
    "R6_delete_heavy",
    "R7_recurrent_mixed",
)
CONTROLS = ("C0_stable", "C1_weight_only")
ALL_REGIMES = STRUCTURAL + CONTROLS
PATHS = ("T_ONLY", "S_ONLY", "Q_ONLY", "S_Q_T", "Q_S_T")
SEED_BASE = 30_000_000


def seed_for(regime: str, index: int) -> int:
    rid = ALL_REGIMES.index(regime)
    return SEED_BASE + rid * 1_000_000 + index


def edge_descriptors(W0: np.ndarray, W1: np.ndarray):
    e0, e1 = edge_set(W0), edge_set(W1)
    n0 = max(len(e0), 1)
    added = len(e1 - e0) / n0
    deleted = len(e0 - e1) / n0
    reversed_count = sum(1 for i, j in e0 if (i, j) not in e1 and (j, i) in e1)
    reversed_frac = reversed_count / n0
    union = len(e0 | e1)
    true_edit = len(e0 ^ e1) / union if union else 0.0
    return true_edit, added, deleted, reversed_frac


def make_regime(regime: str, rng: np.random.Generator):
    W0 = sample_base_W(rng, CFG)
    n0 = len(edge_set(W0))
    W1, W2 = W0.copy(), None
    gradual = 0
    recurrent = 0

    if regime == "C0_stable":
        pass
    elif regime == "C1_weight_only":
        W1 = reweight_same_topology(W0, rng)
    elif regime == "R1_reverse25":
        W1 = reverse_edges(W0, rng, max(15, int(math.ceil(0.25 * n0))))
    elif regime == "R2_reverse50":
        W1 = reverse_edges(W0, rng, max(25, int(math.ceil(0.50 * n0))))
    elif regime == "R3_mixed_abrupt":
        W1 = delete_edges(W0, rng, max(20, int(math.ceil(0.35 * n0))))
        W1 = add_edges(W1, rng, max(28, int(math.ceil(0.50 * n0))))
    elif regime == "R4_mixed_gradual":
        W1 = delete_edges(W0, rng, max(20, int(math.ceil(0.35 * n0))))
        W1 = add_edges(W1, rng, max(28, int(math.ceil(0.50 * n0))))
        gradual = 1
    elif regime == "R5_add_heavy":
        W1 = add_edges(W0, rng, max(30, int(math.ceil(0.55 * n0))))
    elif regime == "R6_delete_heavy":
        W1 = delete_edges(W0, rng, max(28, int(math.ceil(0.50 * n0))))
    elif regime == "R7_recurrent_mixed":
        W1 = delete_edges(W0, rng, max(18, int(math.ceil(0.32 * n0))))
        W1 = add_edges(W1, rng, max(26, int(math.ceil(0.46 * n0))))
        n1 = len(edge_set(W1))
        W2 = delete_edges(W1, rng, max(20, int(math.ceil(0.35 * n1))))
        W2 = add_edges(W2, rng, max(24, int(math.ceil(0.42 * n1))))
        recurrent = 1
    else:
        raise ValueError(regime)

    desc = edge_descriptors(W0, W1)
    return W0, W1, W2, desc, gradual, recurrent


def generate_regime_series(regime: str, seed: int):
    rng = np.random.default_rng(seed)
    W0, W1, W2, desc, gradual, recurrent = make_regime(regime, rng)
    tc = int(rng.integers(CFG.tc_low, CFG.tc_high + 1))
    tc2 = min(tc + 250, CFG.T - 100) if recurrent else None
    x = np.zeros((CFG.T + 1, CFG.n_nodes), dtype=float)
    x[0] = rng.normal(0, CFG.sigma, size=CFG.n_nodes)
    transition = 120

    for t in range(CFG.T):
        if regime == "C0_stable":
            Wt = W0
        elif recurrent and tc2 is not None and t >= tc2:
            Wt = W2
        elif gradual and tc <= t < tc + transition:
            a = (t - tc + 1) / transition
            Wt = (1 - a) * W0 + a * W1
        elif t >= tc:
            Wt = W1
        else:
            Wt = W0
        x[t + 1] = Wt @ x[t] + rng.normal(0, CFG.sigma, size=CFG.n_nodes)

    return x, tc, tc2, desc, gradual, recurrent


def classify_path(ts, tq, tt):
    if tt is None:
        return None
    pre_s = ts is not None and ts < tt
    pre_q = tq is not None and tq < tt
    if not pre_s and not pre_q:
        return "T_ONLY"
    if pre_s and not pre_q:
        return "S_ONLY"
    if pre_q and not pre_s:
        return "Q_ONLY"
    if ts < tq < tt:
        return "S_Q_T"
    return "Q_S_T"


def run_one(regime: str, index: int):
    seed = seed_for(regime, index)
    x, tc, tc2, desc, gradual, recurrent = generate_regime_series(regime, seed)
    out = run_learner(x, CFG)
    ts, tq, tt = out["tau_S"], out["tau_Q"], out["tau_T"]
    true_edit, add_frac, delete_frac, reverse_frac = desc
    path = classify_path(ts, tq, tt)
    complete = ts is not None and tq is not None and tt is not None
    return {
        "regime": regime,
        "index": index,
        "seed": seed,
        "structural": regime in STRUCTURAL,
        "tc": tc,
        "tc2": tc2,
        "tau_S": ts,
        "tau_Q": tq,
        "tau_T": tt,
        "pathway": path,
        "complete": complete,
        "ordered_complete": bool(complete and ts < tq < tt),
        "true_edit": true_edit,
        "add_frac": add_frac,
        "delete_frac": delete_frac,
        "reverse_frac": reverse_frac,
        "gradual": gradual,
        "recurrent": recurrent,
    }


def _worker(args):
    return run_one(*args)


def cramers_v_from_codes(r, c, nr, nc):
    table = np.bincount(r * nc + c, minlength=nr * nc).reshape(nr, nc)
    n = table.sum()
    if n == 0:
        return float("nan"), table
    row = table.sum(axis=1, keepdims=True)
    col = table.sum(axis=0, keepdims=True)
    expected = row @ col / n
    mask = expected > 0
    chi2 = np.sum(((table - expected) ** 2 / np.where(mask, expected, 1))[mask])
    denom = n * max(min(nr - 1, nc - 1), 1)
    return float(np.sqrt(chi2 / denom)), table


def permutation_v(reg_codes, path_codes, nr, nc, n_perm, seed=20260808):
    rng = np.random.default_rng(seed)
    obs, table = cramers_v_from_codes(reg_codes, path_codes, nr, nc)
    null = np.empty(n_perm, dtype=float)
    for i in range(n_perm):
        rp = rng.permutation(reg_codes)
        null[i], _ = cramers_v_from_codes(rp, path_codes, nr, nc)
    p = (1 + np.sum(null >= obs)) / (1 + n_perm)
    return obs, table, null, float(p)


def feature_matrix(rows):
    return np.asarray([
        [r["true_edit"], r["add_frac"], r["delete_frac"], r["reverse_frac"], r["gradual"], r["recurrent"]]
        for r in rows
    ], dtype=float)


def aligned_proba(model, X, classes):
    raw = model.predict_proba(X)
    out = np.full((len(X), len(classes)), 1e-12, dtype=float)
    pos = {c: i for i, c in enumerate(classes)}
    for j, c in enumerate(model.classes_):
        if c in pos:
            out[:, pos[c]] = raw[:, j]
    out /= out.sum(axis=1, keepdims=True)
    return out


def frequency_proba(y_train, n_test, classes):
    counts = np.asarray([np.sum(y_train == c) for c in classes], dtype=float) + 1e-9
    p = counts / counts.sum()
    return np.tile(p, (n_test, 1))


def cv_logloss_gain(rows):
    y = np.asarray([r["pathway"] for r in rows], dtype=object)
    X = feature_matrix(rows)
    classes = np.asarray(sorted(set(y.tolist())), dtype=object)
    counts = {c: int(np.sum(y == c)) for c in classes}
    if len(classes) < 2 or min(counts.values()) < 5:
        return {"gain": None, "model_logloss": None, "baseline_logloss": None, "class_counts": counts}
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=20260808)
    model_losses, base_losses, ns = [], [], []
    for tr, te in skf.split(X, y):
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
        model.fit(X[tr], y[tr])
        pm = aligned_proba(model, X[te], classes)
        pb = frequency_proba(y[tr], len(te), classes)
        model_losses.append(log_loss(y[te], pm, labels=classes))
        base_losses.append(log_loss(y[te], pb, labels=classes))
        ns.append(len(te))
    ml = float(np.average(model_losses, weights=ns))
    bl = float(np.average(base_losses, weights=ns))
    return {"gain": float(1 - ml / bl), "model_logloss": ml, "baseline_logloss": bl, "class_counts": counts}


def loro_gain(rows):
    classes = np.asarray(sorted(set(r["pathway"] for r in rows)), dtype=object)
    results = {}
    for held in STRUCTURAL:
        train = [r for r in rows if r["regime"] != held]
        test = [r for r in rows if r["regime"] == held]
        if not train or not test or len(set(r["pathway"] for r in train)) < 2:
            results[held] = None
            continue
        Xtr, Xte = feature_matrix(train), feature_matrix(test)
        ytr = np.asarray([r["pathway"] for r in train], dtype=object)
        yte = np.asarray([r["pathway"] for r in test], dtype=object)
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
        model.fit(Xtr, ytr)
        pm = aligned_proba(model, Xte, classes)
        pb = frequency_proba(ytr, len(test), classes)
        ml = log_loss(yte, pm, labels=classes)
        bl = log_loss(yte, pb, labels=classes)
        results[held] = float(1 - ml / bl)
    valid = [v for v in results.values() if v is not None and np.isfinite(v)]
    return {
        "by_regime": results,
        "median_gain": float(np.median(valid)) if valid else None,
        "positive_regimes": int(sum(v > 0 for v in valid)),
        "n_valid": len(valid),
    }


def summarize(rows, n_perm):
    structural = [r for r in rows if r["structural"]]
    trows = [r for r in structural if r["tau_T"] is not None]
    reg_index = {r: i for i, r in enumerate(STRUCTURAL)}
    observed_paths = [p for p in PATHS if any(r["pathway"] == p for r in trows)]
    path_index = {p: i for i, p in enumerate(observed_paths)}
    reg_codes = np.asarray([reg_index[r["regime"]] for r in trows], dtype=int)
    path_codes = np.asarray([path_index[r["pathway"]] for r in trows], dtype=int)
    V, table, null, p = permutation_v(reg_codes, path_codes, len(STRUCTURAL), len(observed_paths), n_perm)
    cv = cv_logloss_gain(trows)
    loro = loro_gain(trows)

    regime_results = {}
    adequate = 0
    for reg in STRUCTURAL:
        rr = [r for r in structural if r["regime"] == reg]
        tr = [r for r in rr if r["tau_T"] is not None]
        cc = [r for r in tr if r["complete"]]
        oo = sum(r["ordered_complete"] for r in cc)
        counts = {p: sum(r["pathway"] == p for r in tr) for p in PATHS}
        if len(tr) >= 50:
            adequate += 1
        regime_results[reg] = {
            "n": len(rr), "T_detected": len(tr), "T_rate": len(tr) / len(rr),
            "pathway_counts": counts,
            "complete_triads": len(cc),
            "complete_order_rate": oo / len(cc) if cc else None,
            "mean_descriptors": {
                "true_edit": float(np.mean([r["true_edit"] for r in rr])),
                "add_frac": float(np.mean([r["add_frac"] for r in rr])),
                "delete_frac": float(np.mean([r["delete_frac"] for r in rr])),
                "reverse_frac": float(np.mean([r["reverse_frac"] for r in rr])),
            },
        }

    control_rates = {}
    for reg in CONTROLS:
        rr = [r for r in rows if r["regime"] == reg]
        control_rates[reg] = sum(r["tau_T"] is not None for r in rr) / len(rr)
    audit = control_rates["C0_stable"] < 0.05 and control_rates["C1_weight_only"] < 0.10

    c1 = len(trows) >= 500 and adequate >= 5
    c2 = V >= 0.20 and p < 0.001 and V > float(np.quantile(null, 0.99))
    c3 = cv["gain"] is not None and cv["gain"] >= 0.05
    c4 = loro["median_gain"] is not None and loro["median_gain"] > 0 and loro["positive_regimes"] >= 5
    gates = {"C1_measurement_adequacy": c1, "C2_pathway_heterogeneity": c2, "C3_heldout_prediction": c3, "C4_regime_transfer": c4}
    passes = sum(gates.values())
    if not audit:
        verdict = "Measurement-invalid"
    elif (not c2) or (not c3):
        verdict = "Regime-conditioned pathway hypothesis not supported"
    elif passes == 4:
        verdict = "Strong support for a regime-conditioned pathway model"
    elif passes == 3:
        verdict = "Conditional support for a regime-conditioned pathway model"
    else:
        verdict = "Regime-conditioned pathway hypothesis not supported"

    return {
        "n_runs": len(rows),
        "n_structural_runs": len(structural),
        "n_structural_T_detected": len(trows),
        "adequate_regimes_ge50_T": adequate,
        "observed_pathways": observed_paths,
        "cramers_v": V,
        "permutation_p": p,
        "permutation_v_q99": float(np.quantile(null, 0.99)),
        "cv_logloss": cv,
        "leave_one_regime_out": loro,
        "control_T_rates": control_rates,
        "detector_audit_pass": audit,
        "gates": gates,
        "pass_count": passes,
        "verdict": verdict,
        "regime_results": regime_results,
        "contingency_table": table.tolist(),
    }, null


def make_report(s):
    lines = [
        "# TST Phase 1c — Confirmatory Regime-Conditioned Pathway Report", "",
        f"**Verdict: {s['verdict']}**", "",
        f"Runs: {s['n_runs']} (structural {s['n_structural_runs']}); structural Transformation detections: {s['n_structural_T_detected']}.", "",
        "## Gate table", "",
    ]
    for k, v in s["gates"].items():
        lines.append(f"- {k}: **{'PASS' if v else 'FAIL'}**")
    lines += ["", f"Detector audit: **{'PASS' if s['detector_audit_pass'] else 'FAIL'}**", "",
              "## Primary statistics", "",
              f"- Cramer's V: {s['cramers_v']:.4f}",
              f"- 10,000-permutation p: {s['permutation_p']:.6g}",
              f"- permutation V 99th percentile: {s['permutation_v_q99']:.4f}",
              f"- 5-fold log-loss gain: {s['cv_logloss']['gain']}",
              f"- leave-one-regime-out median gain: {s['leave_one_regime_out']['median_gain']}",
              f"- leave-one-regime-out positive regimes: {s['leave_one_regime_out']['positive_regimes']}/{s['leave_one_regime_out']['n_valid']}", "",
              "## Interpretation", "",
              "Phase 1c tests a mixture-of-pathways formulation rather than a universal TST cycle. A positive result requires both measurable regime/pathway heterogeneity and out-of-sample predictive value from preregistered structural descriptors. Descriptive differences alone are not sufficient.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--structural-seeds", type=int, default=200)
    ap.add_argument("--control-seeds", type=int, default=100)
    ap.add_argument("--permutations", type=int, default=10000)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--outdir", default="phase1c/results/confirmatory")
    args = ap.parse_args()

    tasks = [(r, i) for r in STRUCTURAL for i in range(args.structural_seeds)] + [(r, i) for r in CONTROLS for i in range(args.control_seeds)]
    if args.jobs > 1:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            rows = list(ex.map(_worker, tasks, chunksize=max(1, len(tasks) // (args.jobs * 8))))
    else:
        rows = [_worker(t) for t in tasks]

    summary, null = summarize(rows, args.permutations)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with (out / "REPORT.md").open("w", encoding="utf-8") as f:
        f.write(make_report(summary))
    cols = list(rows[0].keys())
    with (out / "runs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)
    np.savetxt(out / "cramers_v_null.csv", null, delimiter=",")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
