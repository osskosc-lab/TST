import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from .config import CFG, SCENARIOS
from .learner import run_one
from .analysis import summarize, save_outputs

def _worker_run_one(args):
    sc, i, offset = args
    return run_one(sc, i, CFG, seed_offset=offset)

def run_experiment(mode: str, seeds_per_scenario: int, n_perm: int, outdir: Path, jobs: int = 1, seed_start: int = 0):
    rows, series = [], []
    offset = {"calibration": 0, "confirmatory": 1000, "stress": 10000}.get(mode, 0)
    tasks = [(sc, seed_start + i, offset) for sc in SCENARIOS for i in range(seeds_per_scenario)]
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for r,z in ex.map(_worker_run_one, tasks, chunksize=max(1, len(tasks)//(jobs*4))):
                rows.append(r); series.append(z)
    else:
        for args in tasks:
            r,z = _worker_run_one(args)
            rows.append(r); series.append(z)
    summary, null = summarize(rows, series, CFG, n_perm=n_perm)
    summary["mode"] = mode
    summary["seeds_per_scenario"] = seeds_per_scenario
    summary["n_runs"] = len(rows)
    summary["permutations"] = n_perm
    save_outputs(rows, series, summary, null, outdir, CFG)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["calibration","confirmatory","stress"], default="confirmatory")
    ap.add_argument("--seeds-per-scenario", type=int, default=None)
    ap.add_argument("--permutations", type=int, default=None)
    ap.add_argument("--outdir", default="phase1/results/confirmatory")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--seed-start", type=int, default=0)
    args = ap.parse_args()
    default_seeds = {"calibration": CFG.calibration_seeds, "confirmatory": CFG.confirmatory_seeds, "stress": CFG.stress_seeds}[args.mode]
    seeds = args.seeds_per_scenario or default_seeds
    perms = args.permutations if args.permutations is not None else (CFG.n_permutations if args.mode == "confirmatory" else 100)
    run_experiment(args.mode, seeds, perms, Path(args.outdir), jobs=max(1,args.jobs), seed_start=max(0,args.seed_start))

if __name__ == "__main__":
    main()
