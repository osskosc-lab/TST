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
GAMMAS = (1.10, 1.25, 1.50, 2.00)
CLIPS = (3.0, 2.5, 2.0, 1.5)
RIDGE = 1.0
EDGE_THRESHOLD = 0.12
EVIDENCE_PRIOR_DECAY = 0.97
EVAL_H = 200
MANIP_H = 50
CAL_SEED_BASE = 50_000_000


def seed_for(scenario: str, index: int) -> int:
    sid = int(scenario[1:])
    return CAL_SEED_BASE + sid * 1_000_000 + index


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
    W = np.repeat(W0[None, :, :], len(LAMBDAS), axis=0)
    P = np.repeat(P0[None, :, :], len(LAMBDAS), axis=0)
    return W, P


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


def run_environment(scenario: str, index: int):
    seed = seed_for(scenario, index)
    x, truth = generate_series(scenario, seed, CFG)
    tc = int(truth["tc"])
    target = target_graph(truth, scenario)
    W, P = initialize_candidates(x)

    # independent posterior states for the baseline and every intervention candidate
    priors_q = {1.0: np.ones(len(LAMBDAS)) / len(LAMBDAS)}
    for g in GAMMAS:
        priors_q[g] = np.ones(len(LAMBDAS)) / len(LAMBDAS)
    priors_s = {"full": np.ones(len(LAMBDAS)) / len(LAMBDAS)}
    for c in CLIPS:
        priors_s[c] = np.ones(len(LAMBDAS)) / len(LAMBDAS)

    dists_q = {k: [] for k in priors_q}
    ents_q = {k: [] for k in priors_q}
    dists_s = {k: [] for k in priors_s}
    clip_red = {c: [] for c in CLIPS}

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
        cand_graphs = np.abs(W) >= EDGE_THRESHOLD
        for k in range(len(LAMBDAS)):
            np.fill_diagonal(cand_graphs[k], False)

        # Seeking candidate family: full residual evidence, varying posterior persistence sharpening.
        for g in priors_q:
            prior = priors_q[g]
            post = softmax(EVIDENCE_PRIOR_DECAY * np.log(prior + 1e-300) - 0.5 * full_cost)
            vote = np.tensordot(post, cand_graphs.astype(float), axes=(0, 0))
            action_graph = vote >= 0.5
            np.fill_diagonal(action_graph, False)
            if eval_start <= t <= eval_end:
                dists_q[g].append(graph_distance(action_graph, target))
            if eval_start <= t <= manip_end:
                ents_q[g].append(entropy(post))
            next_prior = post if g == 1.0 else post ** g
            next_prior /= next_prior.sum()
            priors_q[g] = next_prior

        # Shadow candidate family: normal posterior diversity, varying residual clipping.
        for c in priors_s:
            if c == "full":
                cost = full_cost
            else:
                clipped = np.mean(np.minimum(sq, float(c)), axis=1)
                cost = clipped
                if eval_start <= t <= manip_end:
                    denom = np.maximum(full_cost, 1e-12)
                    clip_red[c].append(float(np.mean((full_cost - clipped) / denom)))
            prior = priors_s[c]
            post = softmax(EVIDENCE_PRIOR_DECAY * np.log(prior + 1e-300) - 0.5 * cost)
            vote = np.tensordot(post, cand_graphs.astype(float), axes=(0, 0))
            action_graph = vote >= 0.5
            np.fill_diagonal(action_graph, False)
            if eval_start <= t <= eval_end:
                dists_s[c].append(graph_distance(action_graph, target))
            priors_s[c] = post

        update_rls(W, P, xt, yt)
        if t > eval_end and t > manip_end:
            break

    rows = []
    base_q_auge = float(np.mean(dists_q[1.0]))
    base_q_ent = float(np.mean(ents_q[1.0]))
    for g in GAMMAS:
        ent = float(np.mean(ents_q[g]))
        rows.append({
            "scenario": scenario,
            "index": index,
            "seed": seed,
            "mechanism": "Q",
            "candidate": g,
            "base_auge": base_q_auge,
            "candidate_auge": float(np.mean(dists_q[g])),
            "auge_increase": float(np.mean(dists_q[g])) - base_q_auge,
            "manipulation": 1.0 - ent / max(base_q_ent, 1e-12),
        })

    base_s_auge = float(np.mean(dists_s["full"]))
    for c in CLIPS:
        rows.append({
            "scenario": scenario,
            "index": index,
            "seed": seed,
            "mechanism": "S",
            "candidate": c,
            "base_auge": base_s_auge,
            "candidate_auge": float(np.mean(dists_s[c])),
            "auge_increase": float(np.mean(dists_s[c])) - base_s_auge,
            "manipulation": float(np.mean(clip_red[c])) if clip_red[c] else 0.0,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True, choices=["S0", "S2"])
    ap.add_argument("--seeds", type=int, default=60)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    for i in range(args.seeds):
        rows.extend(run_environment(args.scenario, i))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["scenario", "index", "seed", "mechanism", "candidate", "base_auge", "candidate_auge", "auge_increase", "manipulation"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({"scenario": args.scenario, "seeds": args.seeds, "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
