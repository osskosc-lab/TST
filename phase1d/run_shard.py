import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase1"))

from tst_phase1.config import CFG
from tst_phase1.generator import generate_series

LAMBDAS = np.array([0.90, 0.94, 0.97, 0.985, 0.995], dtype=float)
ARMS = ((1, 1), (1, 0), (0, 1), (0, 0))  # Shadow full?, Seeking retained?
SEED_BASE = 40_000_000
RIDGE = 1.0
EDGE_THRESHOLD = 0.12
EVIDENCE_PRIOR_DECAY = 0.97
SEEK_GAMMA = 4.0
CLIP_SQ = 4.0
EVAL_H = 200
MANIP_H = 50


def seed_for(scenario: str, index: int) -> int:
    sid = int(scenario[1:])
    return SEED_BASE + sid * 1_000_000 + index


def graph_from_w(W: np.ndarray) -> np.ndarray:
    g = np.abs(W) >= EDGE_THRESHOLD
    np.fill_diagonal(g, False)
    return g


def graph_distance(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    if union == 0:
        return 0.0
    return float(np.logical_xor(a, b).sum() / union)


def entropy(p: np.ndarray) -> float:
    return float(-np.sum(p * np.log(p + 1e-300)))


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - np.max(z)
    e = np.exp(np.clip(z, -700, 0))
    return e / e.sum()


def initialize_candidates(x: np.ndarray):
    d = CFG.n_nodes
    t0 = CFG.analysis_start
    X = x[:t0]
    Y = x[1:t0 + 1]
    C = X.T @ X + RIDGE * np.eye(d)
    P0 = np.linalg.inv(C)
    W0 = Y.T @ X @ P0
    np.fill_diagonal(W0, 0.0)
    W = np.repeat(W0[None, :, :], len(LAMBDAS), axis=0)
    P = np.repeat(P0[None, :, :], len(LAMBDAS), axis=0)
    return W, P


def update_rls(W: np.ndarray, P: np.ndarray, xt: np.ndarray, yt: np.ndarray):
    for k, lam in enumerate(LAMBDAS):
        Px = P[k] @ xt
        denom = lam + float(xt @ Px)
        gain = Px / max(denom, 1e-12)
        err = yt - W[k] @ xt
        W[k] = W[k] + err[:, None] * gain[None, :]
        P[k] = (P[k] - np.outer(gain, xt @ P[k])) / lam
        np.fill_diagonal(W[k], 0.0)


def true_target_graph(truth: dict, scenario: str) -> np.ndarray:
    if scenario in ("S0",):
        return graph_from_w(truth["W0"])
    # S2 has identical topology despite weight change; W1 is appropriate.
    return graph_from_w(truth["W1"])


def first_recovery_latency(distances: list[float], threshold: float = 0.25, persistence: int = 20):
    if len(distances) < persistence:
        return None
    mask = np.asarray(distances) <= threshold
    conv = np.convolve(mask.astype(int), np.ones(persistence, dtype=int), mode="valid")
    hit = np.flatnonzero(conv >= persistence)
    return int(hit[0] + 1) if hit.size else None


def run_environment(scenario: str, index: int):
    seed = seed_for(scenario, index)
    x, truth = generate_series(scenario, seed, CFG)
    tc = int(truth["tc"])
    target = true_target_graph(truth, scenario)
    W, P = initialize_candidates(x)

    priors = {(s, q): np.ones(len(LAMBDAS)) / len(LAMBDAS) for s, q in ARMS}
    dists = {(s, q): [] for s, q in ARMS}
    mses = {(s, q): [] for s, q in ARMS}
    entropies = {(s, q): [] for s, q in ARMS}
    clip_reductions = []

    eval_start = tc + 1
    eval_end = min(tc + EVAL_H, CFG.T - 1)
    manip_end = min(tc + MANIP_H, CFG.T - 1)

    for t in range(CFG.analysis_start, CFG.T):
        xt = x[t]
        yt = x[t + 1]
        preds = np.einsum("kij,j->ki", W, xt)
        err = yt[None, :] - preds
        sq = (err * err) / (CFG.sigma ** 2)
        full_cost = np.mean(sq, axis=1)
        clamp_cost = np.mean(np.minimum(sq, CLIP_SQ), axis=1)
        cand_graphs = np.abs(W) >= EDGE_THRESHOLD
        for k in range(len(LAMBDAS)):
            np.fill_diagonal(cand_graphs[k], False)

        if eval_start <= t <= manip_end:
            denom = np.maximum(full_cost, 1e-12)
            clip_reductions.append(float(np.mean((full_cost - clamp_cost) / denom)))

        for s_full, q_keep in ARMS:
            cost = full_cost if s_full else clamp_cost
            ll = -0.5 * cost
            prior = priors[(s_full, q_keep)]
            log_score = EVIDENCE_PRIOR_DECAY * np.log(prior + 1e-300) + ll
            post = softmax(log_score)

            # Action uses current posterior. Q- then sharpens this posterior before
            # it becomes the next prior, suppressing persistence of uncertainty.
            vote = np.tensordot(post, cand_graphs.astype(float), axes=(0, 0))
            action_graph = vote >= 0.5
            np.fill_diagonal(action_graph, False)
            pred_mix = np.tensordot(post, preds, axes=(0, 0))

            if eval_start <= t <= eval_end:
                dists[(s_full, q_keep)].append(graph_distance(action_graph, target))
                mses[(s_full, q_keep)].append(float(np.mean((yt - pred_mix) ** 2)))
            if eval_start <= t <= manip_end:
                entropies[(s_full, q_keep)].append(entropy(post))

            if q_keep:
                next_prior = post
            else:
                next_prior = post ** SEEK_GAMMA
                next_prior /= next_prior.sum()
            priors[(s_full, q_keep)] = next_prior

        update_rls(W, P, xt, yt)

        if t > eval_end and t > manip_end:
            break

    rows = []
    for s_full, q_keep in ARMS:
        key = (s_full, q_keep)
        dd = dists[key]
        latency = first_recovery_latency(dd)
        rows.append({
            "scenario": scenario,
            "index": index,
            "seed": seed,
            "tc": tc,
            "shadow_full": s_full,
            "seeking_keep": q_keep,
            "auge": float(np.mean(dd)) if dd else None,
            "recovery_success": latency is not None,
            "recovery_latency": latency,
            "predictive_mse": float(np.mean(mses[key])) if mses[key] else None,
            "mean_entropy_50": float(np.mean(entropies[key])) if entropies[key] else None,
            "clip_reduction_50": float(np.mean(clip_reductions)) if clip_reductions else None,
            "n_eval": len(dd),
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True, choices=["S0", "S2", "S5", "S7"])
    ap.add_argument("--seeds", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(args.seeds):
        rows.extend(run_environment(args.scenario, i))

    fields = [
        "scenario", "index", "seed", "tc", "shadow_full", "seeking_keep",
        "auge", "recovery_success", "recovery_latency", "predictive_mse",
        "mean_entropy_50", "clip_reduction_50", "n_eval"
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(json.dumps({"scenario": args.scenario, "environments": args.seeds, "arm_rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
