# TST Phase 1e — Selective Causal Intervention Preregistration v1.0

## Purpose

Phase 1d produced two unresolved findings:

1. the Shadow intervention was too weak to satisfy its manipulation gate;
2. the Seeking intervention produced a large structural-adaptation effect but also strongly destabilized stable and weight-only controls.

Phase 1e therefore tests whether **negative-control-safe** manipulations of residual evidence (Shadow-like mechanism) and hypothesis diversity (Seeking-like mechanism) still have a selective causal effect on structural adaptation.

This is not an attempt to restore the rejected universal `Shadow -> Seeking -> Transformation` cycle. The learner remains a generic online structural model ensemble and does not encode TST phase order.

---

## Stage A — calibration on negative controls only

Calibration uses seeds that are disjoint from every confirmatory seed.

Scenarios:
- S0 stable: 60 calibration seeds
- S2 weight-only: 60 calibration seeds

### Seeking candidate interventions

Posterior persistence sharpening:

- gamma = 1.10
- gamma = 1.25
- gamma = 1.50
- gamma = 2.00

For each gamma, compare Q- against Q+ while Shadow is held full.

A gamma is **safe** only if both conditions hold:

1. entropy reduction over the first 50 post-change steps >= 0.10;
2. mean AUGE increase versus Q+ <= 0.05 in S0 and <= 0.05 in S2.

Selection rule: choose the **largest safe gamma**. If no gamma is safe, Seeking confirmatory testing stops and the Phase 1e Seeking result is `no safe intervention found`.

### Shadow candidate interventions

Standardized squared-innovation clipping thresholds:

- clip_sq = 3.0
- clip_sq = 2.5
- clip_sq = 2.0
- clip_sq = 1.5

For each threshold, compare S- against S+ while Seeking is retained.

A threshold is **safe and adequate** only if:

1. mean residual-evidence reduction over the first 50 post-change steps >= 0.20;
2. mean AUGE increase versus S+ <= 0.05 in S0 and <= 0.05 in S2.

Selection rule: choose the **largest clip threshold** satisfying both conditions (the mildest adequate intervention). If none qualifies, Shadow confirmatory testing stops and the Phase 1e Shadow result is `no safe adequate intervention found`.

Calibration statistics are not used for confirmatory effect estimation.

---

## Stage B — locked confirmatory paired 2x2 factorial

Once calibration chooses gamma and clip_sq, those values are frozen.

Confirmatory seeds are disjoint from calibration and Phase 1d.

Structural scenarios:
- S5 direction reversal: 300 seeds
- S7 abrupt large structural change: 300 seeds

Holdout negative controls:
- S0 stable: 100 seeds
- S2 weight-only: 100 seeds

Each environment seed is evaluated under all four paired arms:

- S+Q+ : full residual evidence + normal posterior diversity
- S+Q- : full residual evidence + calibrated Seeking suppression
- S-Q+ : calibrated Shadow suppression + normal posterior diversity
- S-Q- : both calibrated interventions

All four arms share identical raw observations and identical candidate RLS parameter trajectories. Interventions affect only evidence weighting and posterior-diversity propagation.

Total confirmatory scale if both manipulations calibrate:

- 800 environments x 4 arms = 3,200 learner-arm runs.

---

## Primary outcome

AUGE: mean normalized Jaccard graph error over the first 200 post-change steps.

Lower is better.

For each mechanism, define the paired removal effect as:

`ATE = AUGE(mechanism suppressed) - AUGE(mechanism retained)`

averaged over the other factorial dimension.

Positive ATE means removing the mechanism worsens adaptation.

---

## Selectivity estimand

To distinguish structural adaptation from generic learner damage, define:

`DID = ATE_structural - ATE_controls`

where structural pools S5 and S7, and controls pool S0 and S2.

A positive DID means the intervention harms structural-change adaptation more than it harms non-structural operation.

---

## Uncertainty

Use paired environment-level BCa bootstrap with 4,000 replicates for:

- structural pooled ATE;
- control pooled ATE;
- DID;
- factorial interaction.

No arm-level unpaired bootstrap is permitted.

---

## Seeking confirmatory gates

Seeking is supported as a **selective causal mechanism** only if all gates pass:

- EQ1 calibration found a safe gamma;
- EQ2 holdout control pooled ATE <= 0.05 and neither S0 nor S2 mean increase exceeds 0.05;
- EQ3 structural pooled ATE >= 0.03;
- EQ4 95% BCa lower bound for structural ATE > 0.01;
- EQ5 structural ATE is positive in both S5 and S7;
- EQ6 DID >= 0.02 and 95% BCa lower bound for DID > 0.

If EQ1 fails: `no safe Seeking intervention found`.
If EQ2 fails: `Seeking intervention remains nonspecific`.
Otherwise failure of EQ3-EQ6: `Seeking selective causal relevance not supported`.

---

## Shadow confirmatory gates

Shadow is supported as a **selective causal mechanism** only if all gates pass:

- ES1 calibration found a safe adequate clip threshold;
- ES2 holdout control pooled ATE <= 0.05 and neither S0 nor S2 mean increase exceeds 0.05;
- ES3 structural pooled ATE >= 0.03;
- ES4 95% BCa lower bound for structural ATE > 0.01;
- ES5 structural ATE is positive in both S5 and S7;
- ES6 DID >= 0.02 and 95% BCa lower bound for DID > 0.

If ES1 fails: `no safe adequate Shadow intervention found`.
If ES2 fails: `Shadow intervention remains nonspecific`.
Otherwise failure of ES3-ES6: `Shadow selective causal relevance not supported`.

---

## Interpretation firewall

A positive result supports only the operational mechanisms tested here:

- residual-evidence retention as a Shadow-like mechanism;
- maintained model-hypothesis diversity as a Seeking-like mechanism.

It does not establish:

- a universal TST cycle;
- a mandatory temporal order;
- psychological or social causation outside this synthetic learner;
- ontological status for Shadow or Seeking.

All wording must remain bounded to the simulated online structural-learning system.