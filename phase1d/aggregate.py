import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import bootstrap

STRUCTURAL = ("S5", "S7")
CONTROLS = ("S0", "S2")


def read_rows(indir: Path):
    rows = []
    for p in sorted(indir.glob("*.csv")):
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "scenario": r["scenario"],
                    "index": int(r["index"]),
                    "seed": int(r["seed"]),
                    "tc": int(r["tc"]),
                    "shadow_full": int(r["shadow_full"]),
                    "seeking_keep": int(r["seeking_keep"]),
                    "auge": float(r["auge"]),
                    "recovery_success": r["recovery_success"] == "True",
                    "recovery_latency": None if r["recovery_latency"] in ("", "None") else int(r["recovery_latency"]),
                    "predictive_mse": float(r["predictive_mse"]),
                    "mean_entropy_50": float(r["mean_entropy_50"]),
                    "clip_reduction_50": float(r["clip_reduction_50"]),
                })
    return rows


def grouped(rows):
    g = {}
    for r in rows:
        g.setdefault((r["scenario"], r["index"]), {})[(r["shadow_full"], r["seeking_keep"])] = r
    return g


def bca_mean_ci(values, seed=20260808):
    x = np.asarray(values, dtype=float)
    if len(x) < 3:
        return [float("nan"), float("nan")]
    res = bootstrap((x,), np.mean, confidence_level=0.95, n_resamples=5000,
                    method="BCa", random_state=np.random.default_rng(seed), vectorized=False)
    return [float(res.confidence_interval.low), float(res.confidence_interval.high)]


def effect_arrays(rows, scenarios):
    g = grouped([r for r in rows if r["scenario"] in scenarios])
    e_s, e_q, e_int = [], [], []
    by_scenario = {s: {"shadow": [], "seeking": [], "interaction": []} for s in scenarios}
    success = {"pp": [], "p0": [], "0p": [], "00": []}
    for (scenario, idx), arms in sorted(g.items()):
        if len(arms) != 4:
            continue
        ypp = arms[(1,1)]["auge"]
        yp0 = arms[(1,0)]["auge"]
        y0p = arms[(0,1)]["auge"]
        y00 = arms[(0,0)]["auge"]
        es = 0.5 * ((y0p-ypp) + (y00-yp0))
        eq = 0.5 * ((yp0-ypp) + (y00-y0p))
        eint = (y00-yp0) - (y0p-ypp)
        e_s.append(es); e_q.append(eq); e_int.append(eint)
        by_scenario[scenario]["shadow"].append(es)
        by_scenario[scenario]["seeking"].append(eq)
        by_scenario[scenario]["interaction"].append(eint)
        success["pp"].append(int(arms[(1,1)]["recovery_success"]))
        success["p0"].append(int(arms[(1,0)]["recovery_success"]))
        success["0p"].append(int(arms[(0,1)]["recovery_success"]))
        success["00"].append(int(arms[(0,0)]["recovery_success"]))
    return e_s, e_q, e_int, by_scenario, success


def mean_or_nan(x):
    return float(np.mean(x)) if x else float("nan")


def summarize(rows):
    structural_rows = [r for r in rows if r["scenario"] in STRUCTURAL]
    e_s, e_q, e_int, by_scenario, success = effect_arrays(rows, STRUCTURAL)

    shadow_ate = mean_or_nan(e_s)
    seeking_ate = mean_or_nan(e_q)
    interaction = mean_or_nan(e_int)
    shadow_ci = bca_mean_ci(e_s, 20260808)
    seeking_ci = bca_mean_ci(e_q, 20260809)
    interaction_ci = bca_mean_ci(e_int, 20260810)

    # Manipulation check M1: one value per environment, because clipping is candidate-level
    # and does not depend on the intervention arm once the raw candidate trajectories are fixed.
    g = grouped(structural_rows)
    clip_per_env = []
    for arms in g.values():
        if (1,1) in arms:
            clip_per_env.append(arms[(1,1)]["clip_reduction_50"])
    m1 = mean_or_nan(clip_per_env)

    ent_qplus = [r["mean_entropy_50"] for r in structural_rows if r["seeking_keep"] == 1]
    ent_qminus = [r["mean_entropy_50"] for r in structural_rows if r["seeking_keep"] == 0]
    h_plus = mean_or_nan(ent_qplus)
    h_minus = mean_or_nan(ent_qminus)
    m2 = 1.0 - h_minus / h_plus if h_plus > 0 else float("nan")

    scenario_effects = {}
    for s in STRUCTURAL:
        es = by_scenario[s]["shadow"]
        eq = by_scenario[s]["seeking"]
        scenario_effects[s] = {
            "n_environments": len(es),
            "shadow_ate": mean_or_nan(es),
            "shadow_ci95": bca_mean_ci(es, 100 + int(s[1:])),
            "seeking_ate": mean_or_nan(eq),
            "seeking_ci95": bca_mean_ci(eq, 200 + int(s[1:])),
            "interaction": mean_or_nan(by_scenario[s]["interaction"]),
        }

    shadow_sign_both = all(scenario_effects[s]["shadow_ate"] > 0 for s in STRUCTURAL)
    seeking_sign_both = all(scenario_effects[s]["seeking_ate"] > 0 for s in STRUCTURAL)

    shadow_gates = {
        "DS1_manipulation": bool(m1 >= 0.20),
        "DS2_ATE_ge_0.03": bool(shadow_ate >= 0.03),
        "DS3_BCa_LCI_gt_0.01": bool(shadow_ci[0] > 0.01),
        "DS4_positive_both_scenarios": bool(shadow_sign_both),
    }
    seeking_gates = {
        "DQ1_manipulation": bool(m2 >= 0.30),
        "DQ2_ATE_ge_0.03": bool(seeking_ate >= 0.03),
        "DQ3_BCa_LCI_gt_0.01": bool(seeking_ci[0] > 0.01),
        "DQ4_positive_both_scenarios": bool(seeking_sign_both),
    }

    # Controls: compare each arm to S+Q+ within environment on graph error.
    control = {}
    audit_pass = True
    cg = grouped([r for r in rows if r["scenario"] in CONTROLS])
    for s in CONTROLS:
        diffs = {(1,0): [], (0,1): [], (0,0): []}
        base_vals = []
        for (sc, idx), arms in cg.items():
            if sc != s or len(arms) != 4:
                continue
            base = arms[(1,1)]["auge"]
            base_vals.append(base)
            for a in diffs:
                diffs[a].append(arms[a]["auge"] - base)
        mean_diffs = {f"S{a[0]}Q{a[1]}": mean_or_nan(v) for a,v in diffs.items()}
        max_increase = max([0.0] + list(mean_diffs.values()))
        control[s] = {"base_auge": mean_or_nan(base_vals), "mean_arm_minus_base": mean_diffs, "max_increase": max_increase}
        audit_pass = audit_pass and max_increase <= 0.10

    if all(shadow_gates.values()):
        shadow_verdict = "Shadow causal relevance supported"
    elif shadow_gates["DS1_manipulation"] and (abs(shadow_ate) < 0.01 or shadow_ci[0] <= 0 <= shadow_ci[1]):
        shadow_verdict = "Strong Shadow causal claim falsified"
    elif not shadow_gates["DS1_manipulation"]:
        shadow_verdict = "Shadow manipulation invalid"
    else:
        shadow_verdict = "Shadow causal relevance not supported"

    if all(seeking_gates.values()):
        seeking_verdict = "Seeking causal relevance supported"
    elif seeking_gates["DQ1_manipulation"] and (abs(seeking_ate) < 0.01 or seeking_ci[0] <= 0 <= seeking_ci[1]):
        seeking_verdict = "Strong Seeking causal claim falsified"
    elif not seeking_gates["DQ1_manipulation"]:
        seeking_verdict = "Seeking manipulation invalid"
    else:
        seeking_verdict = "Seeking causal relevance not supported"

    recovery_rates = {k: mean_or_nan(v) for k,v in success.items()}

    return {
        "n_arm_rows": len(rows),
        "n_structural_environments": len(e_s),
        "manipulation": {
            "shadow_clip_reduction": m1,
            "seeking_entropy_qplus": h_plus,
            "seeking_entropy_qminus": h_minus,
            "seeking_entropy_reduction": m2,
        },
        "primary": {
            "shadow_ate": shadow_ate,
            "shadow_bca95": shadow_ci,
            "seeking_ate": seeking_ate,
            "seeking_bca95": seeking_ci,
            "interaction": interaction,
            "interaction_bca95": interaction_ci,
        },
        "scenario_effects": scenario_effects,
        "shadow_gates": shadow_gates,
        "seeking_gates": seeking_gates,
        "shadow_verdict": shadow_verdict,
        "seeking_verdict": seeking_verdict,
        "negative_control_audit_pass": bool(audit_pass),
        "controls": control,
        "recovery_success_rates": recovery_rates,
    }


def write_report(summary, path: Path):
    p = summary["primary"]
    m = summary["manipulation"]
    lines = [
        "# TST Phase 1d — Shadow / Seeking Causal Intervention Report",
        "",
        f"**Shadow verdict: {summary['shadow_verdict']}**",
        f"**Seeking verdict: {summary['seeking_verdict']}**",
        "",
        f"Paired structural environments: {summary['n_structural_environments']}",
        f"Negative-control audit: {'PASS' if summary['negative_control_audit_pass'] else 'FAIL'}",
        "",
        "## Manipulation checks",
        "",
        f"- Shadow clipping reduction: {m['shadow_clip_reduction']:.4f}",
        f"- Seeking entropy Q+: {m['seeking_entropy_qplus']:.4f}",
        f"- Seeking entropy Q-: {m['seeking_entropy_qminus']:.4f}",
        f"- Seeking entropy reduction: {m['seeking_entropy_reduction']:.4f}",
        "",
        "## Primary causal effects on AUGE (positive = mechanism removal worsens adaptation)",
        "",
        f"- Shadow ATE: {p['shadow_ate']:.6f}, 95% BCa [{p['shadow_bca95'][0]:.6f}, {p['shadow_bca95'][1]:.6f}]",
        f"- Seeking ATE: {p['seeking_ate']:.6f}, 95% BCa [{p['seeking_bca95'][0]:.6f}, {p['seeking_bca95'][1]:.6f}]",
        f"- Interaction: {p['interaction']:.6f}, 95% BCa [{p['interaction_bca95'][0]:.6f}, {p['interaction_bca95'][1]:.6f}]",
        "",
        "## Gates",
        "",
    ]
    for k,v in summary["shadow_gates"].items():
        lines.append(f"- {k}: **{'PASS' if v else 'FAIL'}**")
    for k,v in summary["seeking_gates"].items():
        lines.append(f"- {k}: **{'PASS' if v else 'FAIL'}**")
    lines += ["", "## Scenario effects", ""]
    for s,d in summary["scenario_effects"].items():
        lines.append(f"- {s}: Shadow ATE={d['shadow_ate']:.6f}; Seeking ATE={d['seeking_ate']:.6f}; interaction={d['interaction']:.6f}")
    lines += ["", "## Recovery success rates", ""]
    for k,v in summary["recovery_success_rates"].items():
        lines.append(f"- {k}: {v:.4f}")
    lines += ["", "## Interpretation", "", "This experiment changes generic residual-evidence processing and hypothesis diversity while all candidate RLS models receive identical raw observations. A positive causal result therefore applies to these operationalized adaptive-learning mechanisms, not to the original TST cycle as a universal law."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    rows = read_rows(Path(args.indir))
    summary = summarize(rows)
    out = Path(args.outdir); out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(summary, out / "REPORT.md")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
