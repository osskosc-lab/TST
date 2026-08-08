from dataclasses import dataclass
from typing import Tuple

SCENARIOS=[f"S{i}" for i in range(10)]

@dataclass(frozen=True)
class Config:
    n_nodes: int = 20
    edge_density: float = 0.15
    T: int = 1000
    sigma: float = 0.30
    tc_low: int = 350
    tc_high: int = 650
    baseline_start: int = 200
    baseline_end: int = 300
    analysis_start: int = 300
    shadow_z_threshold: float = 2.0
    shadow_persistence: int = 3
    seeking_persistence: int = 3
    graph_lag: int = 80
    graph_distance_threshold: float = 0.20
    transformation_persistence: int = 10
    graph_edge_threshold: float = 0.12
    graph_smoothing: float = 0.90
    graph_consensus_threshold: float = 0.80
    graph_add_support: float = 0.80
    graph_drop_support: float = 0.20
    graph_vote_persistence: int = 3
    topology_forgetting: float = 0.995
    topology_init_threshold: float = 0.12
    topology_add_threshold: float = 0.16
    topology_drop_threshold: float = 0.08
    topology_update_interval: int = 10
    learner_warmup: int = 150
    candidate_windows: Tuple[int, ...] = (60, 100, 160, 250, 400)
    candidate_update_interval: int = 10
    learner_ridge_alpha: float = 1.0
    model_evidence_window: int = 30
    horizon_auc: int = 20
    block_size: int = 20
    n_permutations: int = 1000
    n_bootstrap: int = 2000
    confirmatory_seeds: int = 50
    calibration_seeds: int = 10
    stress_seeds: int = 100

CFG = Config()
