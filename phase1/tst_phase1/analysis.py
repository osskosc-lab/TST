import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Tuple
import numpy as np
from scipy.stats import bootstrap
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from .config import Config, SCENARIOS

def omega_from_rows(rows: List[dict]) -> Tuple[float, int]:
    vals = [int(r["ordered"]) for r in rows if r["tau_T"] is not None]
    if not vals:
        return float("nan"), 0
    return float(np.mean(vals)), len(vals)

def permutation_null(series: List[dict], cfg: Config, n_perm: int, rng: np.random.Generator) -> np.ndarray:
    start = cfg.analysis_start
    L = cfg.T - start
    nblocks = L // cfg.block_size
    Luse = nblocks * cfg.block_size
    R = len(series)
    S = np.stack([z["S"][start:start+Luse] for z in series]).reshape(R, nblocks, cfg.block_size)
    Q = np.stack([z["Q"][start:start+Luse] for z in series]).reshape(R, nblocks, cfg.block_size)
    D = np.stack([z["DG"][start:start+Luse] for z in series]).reshape(R, nblocks, cfg.block_size)
    qthr = np.asarray([z["q_thr"] for z in series])
    out = np.empty(n_perm, dtype=float)
    row_idx = np.arange(R)[:, None]
    def first_run(mask: np.ndarray, n: int):
        if n == 1:
            anyv = mask.any(axis=1)
            idx = np.argmax(mask, axis=1)
        else:
            view = np.lib.stride_tricks.sliding_window_view(mask, n, axis=1)
            hit = view.all(axis=2)
            anyv = hit.any(axis=1)
            idx = np.argmax(hit, axis=1)
        return np.where(anyv, idx + start, -1)
    for b in range(n_perm):
        pS = np.argsort(rng.random((R, nblocks)), axis=1)
        pQ = np.argsort(rng.random((R, nblocks)), axis=1)
        pD = np.argsort(rng.random((R, nblocks)), axis=1)
        s = S[row_idx, pS].reshape(R, Luse)
        q = Q[row_idx, pQ].reshape(R, Luse)
        d = D[row_idx, pD].reshape(R, Luse)
        ts = first_run(s > cfg.shadow_z_threshold, cfg.shadow_persistence)
        tq = first_run(q > qthr[:, None], cfg.seeking_persistence)
        tt = first_run(d >= cfg.graph_distance_threshold, cfg.transformation_persistence)
        valid = tt >= 0
        if valid.any():
            ordered = valid & (ts >= 0) & (tq >= 0) & (ts < tq) & (tq < tt)
            out[b] = ordered[valid].mean()
        else:
            out[b] = np.nan
    return out

def bca_ci_omega(rows: List[dict], null_median: float, cfg: Config):
    vals = np.asarray([int(r["ordered"]) for r in rows if r["tau_T"] is not None], dtype=float)
    if len(vals) < 3:
        return (float("nan"), float("nan"))
    res = bootstrap((vals,), np.mean, confidence_level=0.95, n_resamples=cfg.n_bootstrap,
                    method="BCa", random_state=np.random.default_rng(20260808), vectorized=False)
    return float(res.confidence_interval.low - null_median), float(res.confidence_interval.high - null_median)

def _fast_logistic_fit_predict(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray) -> np.ndarray:
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0)
    sd[sd < 1e-12] = 1.0
    A = (Xtr - mu) / sd
    B = (Xte - mu) / sd
    Z = np.column_stack([np.ones(len(A)), A])
    Zt = np.column_stack([np.ones(len(B)), B])
    n1 = max(int(ytr.sum()), 1); n0 = max(len(ytr)-n1, 1)
    sw = np.where(ytr == 1, len(ytr)/(2*n1), len(ytr)/(2*n0)).astype(float)
    beta = np.zeros(Z.shape[1], dtype=float)
    for _ in range(20):
        eta = np.clip(Z @ beta, -30, 30)
        pr = 1.0/(1.0 + np.exp(-eta))
        g = Z.T @ (sw * (pr - ytr))
        v = sw * pr * (1-pr)
        H = Z.T @ (Z * v[:,None])
        H.flat[::H.shape[0]+1] += 1e-6
        step = np.linalg.solve(H, g)
        beta -= step
        if np.max(np.abs(step)) < 1e-8:
            break
    return 1.0/(1.0 + np.exp(-np.clip(Zt @ beta, -30, 30)))

def auc_delta(rows: List[dict], series: List[dict], cfg: Config):
    X1s=[]; X2s=[]; ys=[]; gs=[]
    times = np.arange(cfg.analysis_start, cfg.T - cfg.horizon_auc)
    for g,(r,z) in enumerate(zip(rows,series)):
        X1s.append(z["S"][times,None])
        X2s.append(np.column_stack([z["S"][times], z["Q"][times]]))
        tt = r["tau_T"]
        yy = np.zeros(len(times), dtype=np.int8)
        if tt is not None:
            yy[(times < tt) & (tt <= times + cfg.horizon_auc)] = 1
        ys.append(yy); gs.append(np.full(len(times),g,dtype=int))
    X1=np.vstack(X1s); X2=np.vstack(X2s); y=np.concatenate(ys); groups=np.concatenate(gs)
    if y.sum()==0 or y.sum()==len(y):
        return {"auc_S":float("nan"),"auc_SQ":float("nan"),"delta_auc":float("nan"),"positives":int(y.sum())}
    pred1=np.full(len(y),np.nan); pred2=np.full(len(y),np.nan)
    gkf=GroupKFold(n_splits=5)
    for tr,te in gkf.split(X1,y,groups):
        if len(np.unique(y[tr]))<2:
            continue
        pred1[te]=_fast_logistic_fit_predict(X1[tr],y[tr],X1[te])
        pred2[te]=_fast_logistic_fit_predict(X2[tr],y[tr],X2[te])
    good=np.isfinite(pred1)&np.isfinite(pred2)
    auc1=float(roc_auc_score(y[good],pred1[good])); auc2=float(roc_auc_score(y[good],pred2[good]))
    return {"auc_S":auc1,"auc_SQ":auc2,"delta_auc":auc2-auc1,"positives":int(y.sum())}

def summarize(rows: List[dict], series: List[dict], cfg: Config, n_perm: int):
    omega, nT = omega_from_rows(rows)
    rng = np.random.default_rng(20260808)
    null = permutation_null(series, cfg, n_perm=n_perm, rng=rng)
    null_valid = null[np.isfinite(null)]
    null_med = float(np.median(null_valid)) if len(null_valid) else float("nan")
    delta = float(omega - null_med) if np.isfinite(omega) and np.isfinite(null_med) else float("nan")
    ci_delta = bca_ci_omega(rows, null_med, cfg)
    fprs = {}
    for sc in ["S0", "S1", "S2"]:
        rr = [r for r in rows if r["scenario"] == sc]
        fprs[sc] = float(np.mean([r["tau_T"] is not None for r in rr])) if rr else float("nan")
    auc = auc_delta(rows, series, cfg)
    gates = {
        "G1_omega_ge_0.70": bool(np.isfinite(omega) and omega >= 0.70),
        "G2_deltaOmega_BCa_LCI_gt_0.10": bool(np.isfinite(ci_delta[0]) and ci_delta[0] > 0.10),
        "G3_S0_S1_FPR_lt_0.05": bool(fprs["S0"] < 0.05 and fprs["S1"] < 0.05),
        "G4_S2_parameter_only_FPR_lt_0.10": bool(fprs["S2"] < 0.10),
        "G5_deltaAUC_ge_0.03": bool(np.isfinite(auc["delta_auc"]) and auc["delta_auc"] >= 0.03),
    }
    pass_count = sum(gates.values())
    if not gates["G1_omega_ge_0.70"] or not gates["G2_deltaOmega_BCa_LCI_gt_0.10"]:
        verdict = "Core temporal hypothesis falsified"
    elif pass_count == 5:
        verdict = "Strong preliminary support"
    elif pass_count == 4:
        verdict = "Conditional support"
    else:
        verdict = "Not supported"
    scenario_summary = {}
    for sc in SCENARIOS:
        rr = [r for r in rows if r["scenario"] == sc]
        om, nt = omega_from_rows(rr)
        scenario_summary[sc] = {
            "n": len(rr), "transformation_detected": nt,
            "T_detection_rate": nt/len(rr) if rr else float("nan"),
            "omega": om,
            "S_detect_rate": float(np.mean([r["tau_S"] is not None for r in rr])) if rr else float("nan"),
            "Q_detect_rate": float(np.mean([r["tau_Q"] is not None for r in rr])) if rr else float("nan"),
        }
    return {
        "omega": omega,
        "n_transformation_trials": nT,
        "null_median": null_med,
        "delta_omega": delta,
        "delta_omega_bca95": [ci_delta[0], ci_delta[1]],
        "fpr": fprs,
        "auc": auc,
        "gates": gates,
        "pass_count": pass_count,
        "verdict": verdict,
        "scenario_summary": scenario_summary,
        "null_quantiles": {"q025": float(np.quantile(null_valid, .025)), "q975": float(np.quantile(null_valid, .975))} if len(null_valid) else {},
    }, null

def save_outputs(rows, series, summary, null, outdir: Path, cfg: Config):
    outdir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(outdir / "series.npz",
        S=np.stack([z["S"] for z in series]),
        Q=np.stack([z["Q"] for z in series]),
        DG=np.stack([z["DG"] for z in series]),
        q_thr=np.asarray([z["q_thr"] for z in series], dtype=float))
    with (outdir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with (outdir / "config.json").open("w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, indent=2, ensure_ascii=False)
    with (outdir / "runs.csv").open("w", encoding="utf-8") as f:
        cols = ["scenario","seed_index","seed","tc","tc2","tau_S","tau_Q","tau_T","ordered"]
        f.write(",".join(cols)+"\n")
        for r in rows:
            f.write(",".join("" if r[c] is None else str(r[c]) for c in cols)+"\n")
    np.savetxt(outdir / "omega_null.csv", null, delimiter=",")
    window = np.arange(-100, 51)
    synced = {k: [] for k in ["S","Q","DG"]}
    for r,z in zip(rows,series):
        tt = r["tau_T"]
        if tt is None or tt-100 < 0 or tt+50 >= cfg.T:
            continue
        for k in synced:
            synced[k].append(z[k][tt-100:tt+51])
    with (outdir / "event_sync.csv").open("w", encoding="utf-8") as f:
        f.write("relative_t,mean_S,mean_Q,mean_DG\n")
        means = {k: (np.mean(v,axis=0) if v else np.full(len(window),np.nan)) for k,v in synced.items()}
        for i,t in enumerate(window):
            f.write(f"{t},{means['S'][i]},{means['Q'][i]},{means['DG'][i]}\n")
