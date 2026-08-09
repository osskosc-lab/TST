import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase1"))

from tst_phase1.config import CFG
from tst_phase1.generator import generate_series

LAMBDAS = np.array([0.90, 0.94, 0.97, 0.985, 0.995], dtype=float)
ARMS = ((1, 1), (1, 0), (0, 1), (0, 0))
RIDGE = 1.0
EDGE_THRESHOLD = 0.12
EVIDENCE_PRIOR_DECAY = 0.97
EVAL_H = 200
MANIP_H = 50
CONF_SEED_BASE = 60_000_000


def seed_for(scenario, index):
    return CONF_SEED_BASE + int(scenario[1:]) * 1_000_000 + index


def graph_from_w(W):
    g = np.abs(W) >= EDGE_THRESHOLD
    np.fill_diagonal(g, False)
    return g


def graph_distance(a, b):
    u = np.logical_or(a, b).sum()
    return 0.0 if u == 0 else float(np.logical_xor(a, b).sum() / u)


def entropy(p):
    return float(-np.sum(p * np.log(p + 1e-300)))


def softmax(z):
    z = z - np.max(z)
    e = np.exp(np.clip(z, -700, 0))
    return e / e.sum()


def initialize_candidates(x):
    d = CFG.n_nodes
    t0 = CFG.analysis_start
    X = x[:t0]
    Y = x[1:t0 + 1]
    C = X.T @ X + RIDGE * np.eye(d)
    P0 = np.linalg.inv(C)
    W0 = Y.T @ X @ P0
    np.fill_diagonal(W0, 0.0)
    return np.repeat(W0[None, :, :], len(LAMBDAS), axis=0), np.repeat(P0[None, :, :], len(LAMBDAS), axis=0)


def update_rls(W, P, xt, yt):
    for k, lam in enumerate(LAMBDAS):
        Px = P[k] @ xt
        gain = Px / max(lam + float(xt @ Px), 1e-12)
        err = yt - W[k] @ xt
        W[k] = W[k] + err[:, None] * gain[None, :]
        P[k] = (P[k] - np.outer(gain, xt @ P[k])) / lam
        np.fill_diagonal(W[k], 0.0)


def target_graph(truth, scenario):
    if scenario == "S0":
        return graph_from_w(truth["W0"])
    return graph_from_w(truth["W1"])


def recovery_latency(distances, threshold=0.25, persistence=20):
    if len(distances) < persistence:
        return None
    x = np.asarray(distances) <= threshold
    conv = np.convolve(x.astype(int), np.ones(persistence, dtype=int), mode="valid")
    hit = np.flatnonzero(conv >= persistence)
    return int(hit[0] + 1) if hit.size else None


def run_environment(scenario, index, gamma, clip_sq):
    seed = seed_for(scenario, index)
    x, truth = generate_series(scenario, seed, CFG)
    tc = int(truth["tc"])
    target = target_graph(truth, scenario)
    W, P = initialize_candidates(x)

    priors = {a: np.ones(len(LAMBDAS)) / len(LAMBDAS) for a in ARMS}
    dists = {a: [] for a in ARMS}
    entropies = {a: [] for a in ARMS}
    clip_reductions = []

    eval_start = tc + 1
    eval_end = min(tc + EVAL_H, CFG.T - 1)
    manip_end = min(tc + MANIP_H, CFG.T - 1)

    for t in range(CFG.analysis_start, CFG.T):
        xt, yt = x[t], x[t + 1]
        preds = np.einsum("kij,j->ki", W, xt)
        err = yt[None, :] - preds
        sq = (err * err) / (CFG.sigma ** 2)
        full_cost = np.mean(sq, axis=1)
        clipped_cost = np.mean(np.minimum(sq, clip_sq), axis=1) if clip_sq is not None else full_cost
        cand_graphs = np.abs(W) >= EDGE_THRESHOLD
        for k in range(len(LAMBDAS)):
            np.fill_diagonal(cand_graphs[k], False)

        if eval_start <= t <= manip_end:
            denom = np.maximum(full_cost, 1e-12)
            clip_reductions.append(float(np.mean((full_cost - clipped_cost) / denom)))

        for s_full, q_keep in ARMS:
            cost = full_cost if s_full else clipped_cost
            post = softmax(EVIDENCE_PRIOR_DECAY * np.log(priors[(s_full, q_keep)] + 1e-300) - 0.5 * cost)
            vote = np.tensordot(post, cand_graphs.astype(float), axes=(0, 0))
            action_graph = vote >= 0.5
            np.fill_diagonal(action_graph, False)
            if eval_start <= t <= eval_end:
                dists[(s_full, q_keep)].append(graph_distance(action_graph, target))
            if eval_start <= t <= manip_end:
                entropies[(s_full, q_keep)].append(entropy(post))

            if q_keep or gamma is None:
                nxt = post
            else:
                nxt = post ** gamma
                nxt /= nxt.sum()
            priors[(s_full, q_keep)] = nxt

        update_rls(W, P, xt, yt)
        if t > eval_end and t > manip_end:
            break

    rows = []
    for s_full, q_keep in ARMS:
        dd = dists[(s_full, q_keep)]
        lat = recovery_latency(dd)
        rows.append({
            "scenario": scenario,
            "index": index,
            "seed": seed,
            "tc": tc,
            "shadow_full": s_full,
            "seeking_keep": q_keep,
            "gamma": gamma if gamma is not None else 1.0,
            "clip_sq": clip_sq if clip_sq is not None else 999.0,
            "auge": float(np.mean(dd)),
            "recovery_success": lat is not None,
            "recovery_latency": lat,
            "mean_entropy_50": float(np.mean(entropies[(s_full, q_keep)])),
            "clip_reduction_50": float(np.mean(clip_reductions)),
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True, choices=["S0", "S2", "S5", "S7"])
    ap.add_argument("--seeds", type=int, required=True)
    ap.add_argument("--calibration", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cal = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
    gamma = cal.get("selected_gamma")
    clip_sq = cal.get("selected_clip_sq")
    rows = []
    for i in range(args.seeds):
        rows.extend(run_environment(args.scenario, i, gamma, clip_sq))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["scenario", "index", "seed", "tc", "shadow_full", "seeking_keep", "gamma", "clip_sq", "auge", "recovery_success", "recovery_latency", "mean_entropy_50", "clip_reduction_50"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({"scenario": args.scenario, "seeds": args.seeds, "arm_rows": len(rows), "gamma": gamma, "clip_sq": clip_sq}, indent=2))


if __name__ == "__main__":
    main()
