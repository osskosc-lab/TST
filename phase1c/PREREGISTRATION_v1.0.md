# TST Phase 1c — Regime-Conditioned Pathway Experiment / Preregistration v1.0

## Background

Phase 1 rejected the strong mandatory chain `Shadow → Seeking → Transformation`. Phase 1b then rejected the weaker claim that, conditional on all three events occurring, at least 70% of complete triads follow that order. Phase 1b nevertheless found significant enrichment above a matched timing null and substantial regime heterogeneity.

Phase 1c does **not** rescue either failed claim. It tests a different hypothesis: structural transformation may be a **mixture of pathways whose probabilities depend on the transformation regime**.

## Confirmatory claim

For a transformation-detected run, define the pre-Transformation pathway category:

- `T_ONLY`: neither Shadow nor Seeking fires before Transformation
- `S_ONLY`: Shadow but not Seeking fires before Transformation
- `Q_ONLY`: Seeking but not Shadow fires before Transformation
- `S_Q_T`: both fire before Transformation and `tau_S < tau_Q < tau_T`
- `Q_S_T`: both fire before Transformation but the TST order is not satisfied (`tau_Q <= tau_S < tau_T`)

Let `Y` be this pathway category and `Z` the structural transformation regime / preregistered ground-truth change descriptors.

The Phase 1c hypothesis is:

\[
H_{1c}:\quad P(Y\mid Z) \neq P(Y),
\]

with the stronger operational requirement that regime information provides non-trivial **out-of-sample predictive value** for pathway class.

## Measurement lock

All Phase 1 Shadow, Seeking, and Transformation definitions, thresholds, persistence rules, rolling candidate models, RLS topology learner, and baseline windows are inherited unchanged from Phase 1. Phase 1c code may not alter them.

## Structural regimes

Each structural regime uses 200 new deterministic seeds.

1. `R1_reverse25`: reverse approximately 25% of baseline directed edges
2. `R2_reverse50`: reverse approximately 50% of baseline directed edges
3. `R3_mixed_abrupt`: large abrupt mixed delete/add rewiring
4. `R4_mixed_gradual`: the same class of large mixed rewiring introduced gradually over 120 steps
5. `R5_add_heavy`: large edge-addition-dominant abrupt change
6. `R6_delete_heavy`: large edge-deletion-dominant abrupt change
7. `R7_recurrent_mixed`: two large mixed structural changes separated in time

Negative controls use 100 new seeds each:

- `C0_stable`: no change
- `C1_weight_only`: weight re-estimation without topology change

Total confirmatory dataset: **1,600 runs**.

The learner is not told the regime name, change point, or pathway target.

## Ground-truth regime descriptors

The predictive model may use only preregistered generator-side structural descriptors:

- normalized true graph edit distance between baseline and first changed graph
- added-edge fraction
- deleted-edge fraction
- reversed-edge fraction
- gradual indicator
- recurrent indicator

It may not use Shadow, Seeking, Transformation event times, pathway labels, or post-hoc tuned features as predictors.

## Primary analysis population

The primary pathway analysis includes only **structural-regime runs in which Transformation is detected**. Negative controls are used only for detector-audit gates.

## Primary statistics

### 1. Regime × pathway heterogeneity

Construct the contingency table of structural regime by pathway category. Compute Cramér's V. A 10,000-replicate permutation null shuffles regime labels while preserving pathway marginals.

### 2. Out-of-sample descriptor prediction

Fit a multinomial L2-regularized logistic regression using the six preregistered structural descriptors. Evaluate with 5-fold stratified cross-validation.

Primary predictive metric:

\[
G_{LL}=1-\frac{\mathrm{LogLoss}_{model}}{\mathrm{LogLoss}_{frequency\ baseline}}.
\]

The frequency baseline is estimated from each training fold only.

### 3. Leave-one-regime-out generalization

For each structural regime, train on all other regimes and evaluate descriptor-model log loss on the held-out regime against a training-frequency baseline. Record the fraction of regimes with positive log-loss gain and the median gain.

## Gates

- **C1 — measurement adequacy:** at least 500 structural Transformation detections in total, and at least 50 detections in at least 5 of 7 structural regimes.
- **C2 — pathway heterogeneity:** Cramér's `V >= 0.20`, permutation `p < 0.001`, and observed V exceeds the 99th percentile of the permutation null.
- **C3 — held-out prediction:** 5-fold `G_LL >= 0.05`.
- **C4 — regime transfer:** leave-one-regime-out median `G_LL > 0` and at least 5/7 held-out regimes show positive gain.

Detector audit (required validity condition, not a pathway-support gate):

- `C0_stable` Transformation FPR < 0.05
- `C1_weight_only` Transformation misdetection < 0.10

## Decision rule

- 4/4 gates + detector audit pass: **Strong support for a regime-conditioned pathway model**
- 3/4 gates + detector audit pass: **Conditional support**
- 2/4 or fewer: **Regime-conditioned pathway hypothesis not supported**
- If C2 or C3 fails, the central predictive pathway claim is considered failed even if descriptive heterogeneity is present.
- If the detector audit fails, the experiment is **measurement-invalid** and no pathway conclusion is drawn.

## Secondary analyses

Report, without changing the confirmatory decision:

- pathway probabilities by regime
- Transformation detection rate by regime
- complete-triad rate and conditional `S→Q→T` rate by regime
- multinomial coefficients for the six preregistered descriptors

## Interpretation boundary

A positive result would not re-establish a universal TST cycle. It would support only the narrower claim that independent structural transformation can follow multiple measurable pathways and that the mixture weights depend predictably on the kind of structural change.