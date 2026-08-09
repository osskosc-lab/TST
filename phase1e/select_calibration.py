import argparse
import csv
import json
from pathlib import Path

import numpy as np

GAMMAS = [1.10, 1.25, 1.50, 2.00]
CLIPS = [3.0, 2.5, 2.0, 1.5]


def load_rows(indir: Path):
    rows = []
    for p in sorted(indir.glob("*.csv")):
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r["candidate"] = float(r["candidate"])
                r["auge_increase"] = float(r["auge_increase"])
                r["manipulation"] = float(r["manipulation"])
                rows.append(r)
    return rows


def candidate_summary(rows, mechanism, candidate):
    rr = [r for r in rows if r["mechanism"] == mechanism and abs(r["candidate"] - candidate) < 1e-12]
    out = {"candidate": candidate, "n": len(rr), "manipulation": float(np.mean([r["manipulation"] for r in rr]))}
    for scenario in ("S0", "S2"):
        ss = [r for r in rr if r["scenario"] == scenario]
        out[f"{scenario}_auge_increase"] = float(np.mean([r["auge_increase"] for r in ss]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = load_rows(Path(args.indir))
    q = [candidate_summary(rows, "Q", g) for g in GAMMAS]
    s = [candidate_summary(rows, "S", c) for c in CLIPS]

    for x in q:
        x["safe"] = bool(x["manipulation"] >= 0.10 and x["S0_auge_increase"] <= 0.05 and x["S2_auge_increase"] <= 0.05)
    for x in s:
        x["safe_adequate"] = bool(x["manipulation"] >= 0.20 and x["S0_auge_increase"] <= 0.05 and x["S2_auge_increase"] <= 0.05)

    safe_q = [x for x in q if x["safe"]]
    selected_gamma = max((x["candidate"] for x in safe_q), default=None)

    # CLIPS are listed mildest -> strongest; choose largest threshold among qualifying candidates.
    safe_s = [x for x in s if x["safe_adequate"]]
    selected_clip = max((x["candidate"] for x in safe_s), default=None)

    result = {
        "calibration_seed_family": "50M disjoint",
        "n_rows": len(rows),
        "seeking_candidates": q,
        "shadow_candidates": s,
        "selected_gamma": selected_gamma,
        "selected_clip_sq": selected_clip,
        "seeking_calibration_pass": selected_gamma is not None,
        "shadow_calibration_pass": selected_clip is not None,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
