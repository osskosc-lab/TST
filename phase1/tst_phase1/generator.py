import math
import numpy as np
from .config import Config

def spectral_stabilize(W: np.ndarray, radius: float = 0.82) -> np.ndarray:
    eig = np.linalg.eigvals(W)
    r = float(np.max(np.abs(eig))) if eig.size else 0.0
    if r > radius and r > 0:
        W = W * (radius / r)
    return W

def sample_base_W(rng: np.random.Generator, cfg: Config) -> np.ndarray:
    d = cfg.n_nodes
    W = np.zeros((d, d), dtype=float)
    candidates = [(i, j) for i in range(d) for j in range(d) if i != j]
    n_edges = int(round(cfg.edge_density * len(candidates)))
    idx = rng.choice(len(candidates), size=n_edges, replace=False)
    for k in idx:
        i, j = candidates[int(k)]
        W[i, j] = rng.choice([-1.0, 1.0]) * rng.uniform(0.18, 0.34)
    return spectral_stabilize(W)

def edge_set(W: np.ndarray, threshold: float = 1e-12) -> set[tuple[int, int]]:
    ii, jj = np.where((np.abs(W) > threshold) & (~np.eye(W.shape[0], dtype=bool)))
    return set(zip(ii.tolist(), jj.tolist()))

def add_edges(W: np.ndarray, rng: np.random.Generator, n: int) -> np.ndarray:
    W = W.copy()
    d = W.shape[0]
    existing = edge_set(W)
    avail = [(i, j) for i in range(d) for j in range(d) if i != j and (i, j) not in existing]
    n = min(n, len(avail))
    picks = rng.choice(len(avail), size=n, replace=False)
    for p in picks:
        i, j = avail[int(p)]
        W[i, j] = rng.choice([-1.0, 1.0]) * rng.uniform(0.18, 0.34)
    return spectral_stabilize(W)

def delete_edges(W: np.ndarray, rng: np.random.Generator, n: int) -> np.ndarray:
    W = W.copy()
    edges = list(edge_set(W))
    n = min(n, len(edges))
    picks = rng.choice(len(edges), size=n, replace=False)
    for p in picks:
        i, j = edges[int(p)]
        W[i, j] = 0.0
    return spectral_stabilize(W)

def reverse_edges(W: np.ndarray, rng: np.random.Generator, n: int) -> np.ndarray:
    W = W.copy()
    edges = [(i, j) for i, j in edge_set(W) if abs(W[j, i]) < 1e-12]
    n = min(n, len(edges))
    picks = rng.choice(len(edges), size=n, replace=False)
    for p in picks:
        i, j = edges[int(p)]
        val = W[i, j]
        W[i, j] = 0.0
        W[j, i] = val
    return spectral_stabilize(W)

def reweight_same_topology(W: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = W.copy()
    nz = np.abs(out) > 1e-12
    factors = rng.uniform(0.75, 1.25, size=out.shape)
    out[nz] *= factors[nz]
    return spectral_stabilize(out)

def make_structural_variant(W0: np.ndarray, scenario: str, rng: np.random.Generator):
    n0 = len(edge_set(W0))
    if scenario == "S2":
        return reweight_same_topology(W0, rng), None
    if scenario == "S3":
        return add_edges(W0, rng, max(15, int(math.ceil(0.25*n0)))), None
    if scenario == "S4":
        return delete_edges(W0, rng, max(15, int(math.ceil(0.25*n0)))), None
    if scenario == "S5":
        return reverse_edges(W0, rng, max(15, int(math.ceil(0.25*n0)))), None
    if scenario == "S6":
        W1 = delete_edges(W0, rng, 10)
        W1 = add_edges(W1, rng, 14)
        return W1, None
    if scenario == "S7":
        W1 = delete_edges(W0, rng, 20)
        W1 = add_edges(W1, rng, 28)
        return W1, None
    if scenario == "S9":
        W1 = add_edges(W0, rng, 16)
        W2 = delete_edges(W1, rng, 18)
        W2 = add_edges(W2, rng, 16)
        return W1, W2
    return W0.copy(), None

def generate_series(scenario: str, seed: int, cfg: Config):
    rng = np.random.default_rng(seed)
    W0 = sample_base_W(rng, cfg)
    W1, W2 = make_structural_variant(W0, scenario, rng)
    tc = int(rng.integers(cfg.tc_low, cfg.tc_high + 1))
    tc2 = min(tc + 250, cfg.T - 100) if scenario == "S9" else None
    x = np.zeros((cfg.T + 1, cfg.n_nodes), dtype=float)
    x[0] = rng.normal(0, cfg.sigma, size=cfg.n_nodes)
    transition = 120
    for t in range(cfg.T):
        if scenario in ("S0", "S1", "S8"):
            Wt = W0
        elif scenario == "S6" and tc <= t < tc + transition:
            a = (t - tc + 1) / transition
            Wt = (1-a)*W0 + a*W1
        elif scenario == "S9" and tc2 is not None and t >= tc2:
            Wt = W2
        elif t >= tc:
            Wt = W1
        else:
            Wt = W0
        sig = cfg.sigma
        if scenario == "S1" and tc <= t < min(tc + 100, cfg.T):
            sig = 0.60
        if scenario == "S8" and tc <= t < min(tc + 80, cfg.T):
            sig = 0.03
            if t == tc:
                x[t] *= 0.03
        x[t+1] = Wt @ x[t] + rng.normal(0, sig, size=cfg.n_nodes)
    return x, {"tc": tc, "tc2": tc2, "W0": W0, "W1": W1, "W2": W2}
