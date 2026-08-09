import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import bootstrap

STRUCTURAL = ("S5", "S7")
CONTROLS = ("S0", "S2")


def read_rows(indir):
    rows = []
    for p in sorted(Path(indir).glob("*.csv")):
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "scenario": r["scenario"],
                    "index": int(r["index"]),
                    "shadow_full": int(r["shadow_full"]),
                    "seeking_keep": int(r["seeking_keep"]),
                    "auge": float(r["auge"]),
                    "recovery_success": r["recovery_success"] == "True",
                    "mean_entropy_50": float(r["mean_entropy_50"]),
                    "clip_reduction_50": float(r["clip_reduction_50"]),
                })
    return rows


def grouped(rows):
    g = {}
    for r in rows:
        g.setdefault((r["scenario"], r["index"]), {})[(r["shadow_full"], r["seeking_keep"])] = r
    return g


def effects(rows, scenarios):
    g = grouped([r for r in rows if r["scenario"] in scenarios])
    es, eq, ei = [], [], []
    by = {s: {"shadow": [], "seeking": [], "interaction": []} for s in scenarios}
    rec = {"pp": [], "p0": [], "0p": [], "00": []}
    for (s, i), a in sorted(g.items()):
        if len(a) != 4:
            continue
        ypp, yp0, y0p, y00 = a[(1,1)]["auge"], a[(1,0)]["auge"], a[(0,1)]["auge"], a[(0,0)]["auge"]
        e_s = 0.5 * ((y0p-ypp) + (y00-yp0))
        e_q = 0.5 * ((yp0-ypp) + (y00-y0p))
        e_i = (y00-yp0) - (y0p-ypp)
        es.append(e_s); eq.append(e_q); ei.append(e_i)
        by[s]["shadow"].append(e_s); by[s]["seeking"].append(e_q); by[s]["interaction"].append(e_i)
        rec["pp"].append(int(a[(1,1)]["recovery_success"])); rec["p0"].append(int(a[(1,0)]["recovery_success"]))
        rec["0p"].append(int(a[(0,1)]["recovery_success"])); rec["00"].append(int(a[(0,0)]["recovery_success"]))
    return np.asarray(es), np.asarray(eq), np.asarray(ei), by, rec


def mean_ci(x, seed):
    x = np.asarray(x, dtype=float)
    if len(x) < 3:
        return [float("nan"), float("nan")]
    r = bootstrap((x,), np.mean, confidence_level=0.95, n_resamples=4000, method="BCa",
                  vectorized=False, random_state=np.random.default_rng(seed))
    return [float(r.confidence_interval.low), float(r.confidence_interval.high)]


def did_ci(xs, xc, seed):
    xs, xc = np.asarray(xs, dtype=float), np.asarray(xc, dtype=float)
    def stat(a, b):
        return np.mean(a) - np.mean(b)
    r = bootstrap((xs, xc), stat, paired=False, confidence_level=0.95, n_resamples=4000,
                  method="BCa", vectorized=False, random_state=np.random.default_rng(seed))
    return [float(r.confidence_interval.low), float(r.confidence_interval.high)]


def m(x):
    return float(np.mean(x)) if len(x) else float("nan")


def summarize(rows, cal):
    sS, sQ, sI, byS, recS = effects(rows, STRUCTURAL)
    cS, cQ, cI, byC, _ = effects(rows, CONTROLS)

    shadow_struct = m(sS); seek_struct = m(sQ)
    shadow_ctrl = m(cS); seek_ctrl = m(cQ)
    shadow_did = shadow_struct - shadow_ctrl
    seek_did = seek_struct - seek_ctrl

    sh_ci = mean_ci(sS, 202608091)
    sq_ci = mean_ci(sQ, 202608092)
    sc_ci = mean_ci(cS, 202608093)
    qc_ci = mean_ci(cQ, 202608094)
    sdid_ci = did_ci(sS, cS, 202608095)
    qdid_ci = did_ci(sQ, cQ, 202608096)
    int_ci = mean_ci(sI, 202608097)

    scenario_effects = {}
    for s in STRUCTURAL:
        scenario_effects[s] = {
            "shadow_ate": m(byS[s]["shadow"]),
            "seeking_ate": m(byS[s]["seeking"]),
            "interaction": m(byS[s]["interaction"]),
        }
    control_effects = {}
    for s in CONTROLS:
        control_effects[s] = {
            "shadow_ate": m(byC[s]["shadow"]),
            "seeking_ate": m(byC[s]["seeking"]),
        }

    structural_rows = [r for r in rows if r["scenario"] in STRUCTURAL]
    clip_env = []
    for arms in grouped(structural_rows).values():
        if (1,1) in arms:
            clip_env.append(arms[(1,1)]["clip_reduction_50"])
    hplus = [r["mean_entropy_50"] for r in structural_rows if r["seeking_keep"] == 1]
    hminus = [r["mean_entropy_50"] for r in structural_rows if r["seeking_keep"] == 0]
    hp, hm = m(hplus), m(hminus)
    qman = 1.0 - hm / hp if hp > 0 else float("nan")
    sman = m(clip_env)

    eq2 = seek_ctrl <= 0.05 and all(control_effects[s]["seeking_ate"] <= 0.05 for s in CONTROLS)
    es2 = shadow_ctrl <= 0.05 and all(control_effects[s]["shadow_ate"] <= 0.05 for s in CONTROLS)

    qg = {
        "EQ1_safe_calibration": bool(cal.get("seeking_calibration_pass")),
        "EQ2_holdout_controls_safe": bool(eq2),
        "EQ3_structural_ATE_ge_0.03": bool(seek_struct >= 0.03),
        "EQ4_structural_BCa_LCI_gt_0.01": bool(sq_ci[0] > 0.01),
        "EQ5_positive_S5_S7": bool(all(scenario_effects[s]["seeking_ate"] > 0 for s in STRUCTURAL)),
        "EQ6_DID_selective": bool(seek_did >= 0.02 and qdid_ci[0] > 0.0),
    }
    sg = {
        "ES1_safe_adequate_calibration": bool(cal.get("shadow_calibration_pass")),
        "ES2_holdout_controls_safe": bool(es2),
        "ES3_structural_ATE_ge_0.03": bool(shadow_struct >= 0.03),
        "ES4_structural_BCa_LCI_gt_0.01": bool(sh_ci[0] > 0.01),
        "ES5_positive_S5_S7": bool(all(scenario_effects[s]["shadow_ate"] > 0 for s in STRUCTURAL)),
        "ES6_DID_selective": bool(shadow_did >= 0.02 and sdid_ci[0] > 0.0),
    }

    if not qg["EQ1_safe_calibration"]:
        qver = "No safe Seeking intervention found"
    elif not qg["EQ2_holdout_controls_safe"]:
        qver = "Seeking intervention remains nonspecific"
    elif all(qg.values()):
        qver = "Seeking selective causal relevance supported"
    else:
        qver = "Seeking selective causal relevance not supported"

    if not sg["ES1_safe_adequate_calibration"]:
        sver = "No safe adequate Shadow intervention found"
    elif not sg["ES2_holdout_controls_safe"]:
        sver = "Shadow intervention remains nonspecific"
    elif all(sg.values()):
        sver = "Shadow selective causal relevance supported"
    else:
        sver = "Shadow selective causal relevance not supported"

    return {
        "n_arm_rows": len(rows),
        "selected_gamma": cal.get("selected_gamma"),
        "selected_clip_sq": cal.get("selected_clip_sq"),
        "confirmatory_manipulation": {"shadow_clip_reduction": sman, "seeking_entropy_qplus": hp, "seeking_entropy_qminus": hm, "seeking_entropy_reduction": qman},
        "structural": {
            "shadow_ate": shadow_struct, "shadow_bca95": sh_ci,
            "seeking_ate": seek_struct, "seeking_bca95": sq_ci,
            "interaction": m(sI), "interaction_bca95": int_ci,
        },
        "controls_pooled": {
            "shadow_ate": shadow_ctrl, "shadow_bca95": sc_ci,
            "seeking_ate": seek_ctrl, "seeking_bca95": qc_ci,
        },
        "selectivity_DID": {
            "shadow": shadow_did, "shadow_bca95": sdid_ci,
            "seeking": seek_did, "seeking_bca95": qdid_ci,
        },
        "scenario_effects": scenario_effects,
        "control_effects": control_effects,
        "shadow_gates": sg,
        "seeking_gates": qg,
        "shadow_verdict": sver,
        "seeking_verdict": qver,
        "recovery_success_structural": {k: m(v) for k,v in recS.items()},
        "calibration": cal,
    }


def report(s):
    st, ct, di = s["structural"], s["controls_pooled"], s["selectivity_DID"]
    lines = [
        "# TST Phase 1e — Selective Causal Intervention Confirmatory Report", "",
        f"**Shadow verdict: {s['shadow_verdict']}**",
        f"**Seeking verdict: {s['seeking_verdict']}**", "",
        f"Selected gamma: {s['selected_gamma']}", f"Selected clip_sq: {s['selected_clip_sq']}", "",
        "## Structural effects", "",
        f"- Shadow ATE: {st['shadow_ate']:.6f}, BCa95 [{st['shadow_bca95'][0]:.6f}, {st['shadow_bca95'][1]:.6f}]",
        f"- Seeking ATE: {st['seeking_ate']:.6f}, BCa95 [{st['seeking_bca95'][0]:.6f}, {st['seeking_bca95'][1]:.6f}]",
        "", "## Holdout-control effects", "",
        f"- Shadow pooled control ATE: {ct['shadow_ate']:.6f}",
        f"- Seeking pooled control ATE: {ct['seeking_ate']:.6f}",
        "", "## Selectivity (structural minus control)", "",
        f"- Shadow DID: {di['shadow']:.6f}, BCa95 [{di['shadow_bca95'][0]:.6f}, {di['shadow_bca95'][1]:.6f}]",
        f"- Seeking DID: {di['seeking']:.6f}, BCa95 [{di['seeking_bca95'][0]:.6f}, {di['seeking_bca95'][1]:.6f}]",
        "", "## Gates", ""
    ]
    for k,v in s["shadow_gates"].items(): lines.append(f"- {k}: **{'PASS' if v else 'FAIL'}**")
    for k,v in s["seeking_gates"].items(): lines.append(f"- {k}: **{'PASS' if v else 'FAIL'}**")
    lines += ["", "## Interpretation", "", "Phase 1e only credits a mechanism when a negative-control-safe intervention selectively impairs structural adaptation. Statistical significance without control safety or positive DID is not counted as TST-specific causal support."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", required=True)
    ap.add_argument("--calibration", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    rows = read_rows(args.indir)
    cal = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
    s = summarize(rows, cal)
    out = Path(args.outdir); out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "REPORT.md").write_text(report(s), encoding="utf-8")
    print(json.dumps(s, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
