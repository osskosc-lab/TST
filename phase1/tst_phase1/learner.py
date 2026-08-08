import math
import numpy as np
from scipy.special import logsumexp
from .config import Config
from .generator import generate_series

def jaccard_graph_distance(A: np.ndarray, B: np.ndarray) -> float:
    a = A.astype(bool)
    b = B.astype(bool)
    union = np.logical_or(a, b).sum()
    if union == 0:
        return 0.0
    diff = np.logical_xor(a, b).sum()
    return float(diff / union)

def first_persistent(mask: np.ndarray, n: int, start: int) -> int | None:
    if n <= 1:
        inds = np.flatnonzero(mask[start:])
        return int(start + inds[0]) if inds.size else None
    m = mask.astype(np.int8)
    conv = np.convolve(m, np.ones(n, dtype=np.int8), mode="valid")
    inds = np.flatnonzero((conv >= n) & (np.arange(conv.size) >= start))
    return int(inds[0]) if inds.size else None

def run_learner(x: np.ndarray, cfg: Config):
    d = cfg.n_nodes
    windows = np.asarray(cfg.candidate_windows, dtype=int)
    K = len(windows)
    diag_mask = ~np.eye(d, dtype=bool)
    sigma2 = cfg.sigma ** 2
    xx = np.einsum("ti,tj->tij", x[:-1], x[:-1])
    yx = np.einsum("ti,tj->tij", x[1:], x[:-1])
    cum_xx = np.concatenate([np.zeros((1,d,d)), np.cumsum(xx, axis=0)], axis=0)
    cum_yx = np.concatenate([np.zeros((1,d,d)), np.cumsum(yx, axis=0)], axis=0)
    W = np.zeros((K, d, d), dtype=float)
    q = np.zeros(cfg.T, dtype=float)
    nll = np.full(cfg.T, np.nan, dtype=float)
    evidence = np.zeros(K, dtype=float)
    ll_queue: list[np.ndarray] = []

    def refit_candidates(t: int) -> None:
        nonlocal W
        Cxxs, Cyxs, valid = [], [], []
        I = np.eye(d)
        for k, win in enumerate(windows):
            lo = max(0, t - int(win))
            if t - lo < d + 5:
                continue
            Cxxs.append(cum_xx[t] - cum_xx[lo] + cfg.learner_ridge_alpha * I)
            Cyxs.append(cum_yx[t] - cum_yx[lo])
            valid.append(k)
        if valid:
            Cxxs = np.stack(Cxxs)
            Cyxs = np.stack(Cyxs)
            invs = np.linalg.inv(Cxxs)
            Wks = np.einsum("kij,kjl->kil", Cyxs, invs)
            for a,k in enumerate(valid):
                W[k] = Wks[a]
                np.fill_diagonal(W[k], 0.0)

    refit_candidates(cfg.learner_warmup)
    C0 = cum_xx[cfg.analysis_start] + cfg.learner_ridge_alpha * np.eye(d)
    Ptop = np.linalg.inv(C0)
    Wtop = cum_yx[cfg.analysis_start] @ Ptop
    np.fill_diagonal(Wtop, 0.0)
    graph = (np.abs(Wtop) >= cfg.topology_init_threshold) & diag_mask
    add_count = np.zeros((d, d), dtype=np.int16)
    drop_count = np.zeros((d, d), dtype=np.int16)
    graph_hist = np.zeros((cfg.T, d, d), dtype=bool)
    graph_hist[:cfg.analysis_start] = graph
    dg = np.zeros(cfg.T, dtype=float)

    for t in range(cfg.T):
        if t >= cfg.learner_warmup:
            if t % cfg.candidate_update_interval == 0:
                refit_candidates(t)
            xt = x[t]
            yt = x[t+1]
            pred = np.einsum("kij,j->ki", W, xt)
            err = yt[None, :] - pred
            ll = -0.5 * np.sum((err * err) / sigma2 + math.log(2*math.pi*sigma2), axis=1)
            p_prev = np.exp(evidence - logsumexp(evidence))
            nll[t] = -float(logsumexp(np.log(p_prev + 1e-300) + ll)) / d
            ll_queue.append(ll.copy())
            evidence += ll
            if len(ll_queue) > cfg.model_evidence_window:
                evidence -= ll_queue.pop(0)
            p = np.exp(evidence - logsumexp(evidence))
            q[t] = -float(np.sum(p * np.log(p + 1e-300)))

        if t >= cfg.analysis_start:
            xt = x[t]
            yt = x[t+1]
            Px = Ptop @ xt
            denom = cfg.topology_forgetting + float(xt @ Px)
            gain = Px / max(denom, 1e-12)
            terr = yt - Wtop @ xt
            Wtop = Wtop + terr[:, None] * gain[None, :]
            Ptop = (Ptop - np.outer(gain, xt @ Ptop)) / cfg.topology_forgetting
            np.fill_diagonal(Wtop, 0.0)
            if t % cfg.topology_update_interval == 0:
                mag = np.abs(Wtop)
                add_ev = (mag >= cfg.topology_add_threshold) & (~graph) & diag_mask
                drop_ev = (mag <= cfg.topology_drop_threshold) & graph & diag_mask
                add_count = np.where(add_ev, add_count + 1, 0)
                drop_count = np.where(drop_ev, drop_count + 1, 0)
                graph = graph | (add_count >= cfg.graph_vote_persistence)
                graph = graph & ~(drop_count >= cfg.graph_vote_persistence)
                graph &= diag_mask
            graph_hist[t] = graph
            if t >= cfg.graph_lag:
                dg[t] = jaccard_graph_distance(graph_hist[t], graph_hist[t-cfg.graph_lag])
        elif t >= cfg.analysis_start - cfg.graph_lag:
            graph_hist[t] = graph

    b = slice(cfg.baseline_start, cfg.baseline_end)
    mu = float(np.nanmean(nll[b]))
    sd = float(np.nanstd(nll[b], ddof=1))
    if not np.isfinite(sd) or sd < 1e-9:
        sd = 1.0
    s_z = (nll - mu) / sd
    q_thr = float(np.quantile(q[b], 0.95))
    tau_s = first_persistent(s_z > cfg.shadow_z_threshold, cfg.shadow_persistence, cfg.analysis_start)
    tau_q = first_persistent(q > q_thr, cfg.seeking_persistence, cfg.analysis_start)
    tau_t = first_persistent(dg >= cfg.graph_distance_threshold, cfg.transformation_persistence, cfg.analysis_start)
    return {"S": s_z, "Q": q, "DG": dg, "q_thr": q_thr, "tau_S": tau_s, "tau_Q": tau_q, "tau_T": tau_t}

def run_one(scenario: str, seed_index: int, cfg: Config, seed_offset: int = 0):
    sid = int(scenario[1:])
    seed = 10_000_000 + sid * 100_000 + seed_offset + seed_index
    x, truth = generate_series(scenario, seed, cfg)
    out = run_learner(x, cfg)
    ts, tq, tt = out["tau_S"], out["tau_Q"], out["tau_T"]
    ordered = bool(tt is not None and ts is not None and tq is not None and ts < tq < tt)
    row = {"scenario": scenario, "seed_index": seed_index, "seed": seed, "tc": truth["tc"], "tc2": truth["tc2"], "tau_S": ts, "tau_Q": tq, "tau_T": tt, "ordered": ordered}
    return row, out
