# TST Phase 1d — Shadow / Seeking Causal Intervention Preregistration v1.0

## Question

Phase 1–1c did not support a universal or strongly regime-predictive `Shadow → Seeking → Transformation` law. Phase 1d therefore asks a narrower causal question:

> In an adaptive structural learner that is not programmed with TST phase order, does access to large prediction-residual evidence (Shadow channel) and preservation of competing model hypotheses (Seeking channel) causally improve structural adaptation after an exogenous network change?

This experiment does **not** intervene on the measured Phase-1 `S_t` or `Q_t` labels. Those were passive observables. Instead it intervenes on two generic learning mechanisms that correspond operationally to the information carried by those observables.

## Learner

The learner maintains five parallel recursive least-squares VAR(1) models with fixed forgetting factors:

`λ = {0.90, 0.94, 0.97, 0.985, 0.995}`.

All candidate models receive exactly the same raw observations in all intervention arms. Candidate parameter trajectories are therefore shared counterfactuals; interventions only alter model-evidence processing and hypothesis weighting.

Each candidate induces an estimated directed graph by the same fixed coefficient threshold used previously (`|w_ij| >= 0.12`). No TST phase label, event order, or TST gate is used by the learner.

## Randomized 2×2 factorial intervention

For every environment seed, all four arms are evaluated on the identical generated time series.

### Factor S — residual / Shadow information channel

- **S+ (full residual evidence):** predictive likelihood uses the full standardized squared innovation.
- **S− (clamped residual evidence):** each per-node standardized squared innovation is clipped at 4.0 before entering model-evidence updates.

The RLS candidate models themselves still receive the original raw observations in both arms. Only the evidence used to decide which adaptive timescale to trust is clamped.

### Factor Q — hypothesis diversity / Seeking channel

- **Q+ (uncertainty retained):** posterior model weights are propagated normally.
- **Q− (uncertainty suppressed):** after each update, posterior weights are sharpened by power `γ=4` and renormalized before becoming the next prior.

`γ=4` is fixed before confirmatory execution. This suppresses model entropy without deleting candidate models or changing their parameter updates.

The action graph is the posterior-weighted majority graph (`sum_k p_k 1(edge_k) >= 0.5`).

## Environments

Primary structural conditions reuse the fixed Phase-1 generator without modification:

- S5: abrupt edge-direction reversal
- S7: abrupt large mixed structural change

Negative controls:

- S0: stable structure
- S2: weight-only parameter change

The primary causal estimands use S5 and S7 only. S0/S2 are measurement/safety audits and are not pooled into the primary effect.

## Sample size

- S5: 200 new environment seeds
- S7: 200 new environment seeds
- S0: 100 new environment seeds
- S2: 100 new environment seeds

Each environment is evaluated in 4 paired intervention arms.

Total learner-arm runs: `600 × 4 = 2,400`.

No Phase-1/1b/1c seed is reused.

## Primary outcome

For each structural environment, evaluate the first 200 post-change steps. Let `G*_t` be the true directed graph and `Ghat_t` the action graph.

Normalized graph error:

`D_t = |Ehat_t Δ E*_t| / |Ehat_t ∪ E*_t|`.

Primary outcome:

`AUGE = mean_{h=1..200} D_{tc+h}`.

Lower is better. For S7 this is against the post-change graph. For S5 it is against the reversed graph.

Secondary outcomes:

- graph-recovery success: `D_t <= 0.25` for 20 consecutive steps within the 200-step window
- recovery latency among successes
- mean predictive squared error over the same window
- stable/weight-only structural drift relative to the pre-change graph

## Paired causal estimands

Let `Y(s,q)` be AUGE for Shadow state `s ∈ {+,−}` and Seeking state `q ∈ {+,−}`.

Shadow availability effect:

`ATE_S = 0.5 * [(Y(-,+)-Y(+,+)) + (Y(-,-)-Y(+,-))]`.

Seeking availability effect:

`ATE_Q = 0.5 * [(Y(+,-)-Y(+,+)) + (Y(-,-)-Y(-,+))]`.

Positive values mean that removing the mechanism worsens adaptation.

Interaction:

`INT = [Y(-,-)-Y(+,-)] - [Y(-,+)-Y(+,+)]`.

All estimands are computed within environment seed before aggregation.

## Statistics

- paired bootstrap over environment seeds, B=5,000
- 95% BCa confidence intervals
- report S5, S7, and pooled estimates
- no multiplicity correction for the two preregistered primary main effects; interaction and secondary outcomes are secondary

## Manipulation checks

M1 Shadow manipulation:

The average clipped contribution to model-evidence loss under S− must be at least 20% lower than under S+ during the first 50 post-change steps.

M2 Seeking manipulation:

Mean posterior entropy under Q− must be at least 30% lower than Q+ during the first 50 post-change steps.

If either manipulation check fails, the corresponding causal null is not interpretable and is reported as manipulation-invalid.

## Primary support / falsification gates

For **Shadow causal relevance**:

- DS1: M1 passes
- DS2: pooled `ATE_S >= 0.03`
- DS3: 95% BCa lower bound of `ATE_S > 0.01`
- DS4: sign is positive in both S5 and S7

All four are required for `Shadow causal relevance supported`.

For **Seeking causal relevance**:

- DQ1: M2 passes
- DQ2: pooled `ATE_Q >= 0.03`
- DQ3: 95% BCa lower bound of `ATE_Q > 0.01`
- DQ4: sign is positive in both S5 and S7

All four are required for `Seeking causal relevance supported`.

If the manipulation passes but `|ATE| < 0.01` or the 95% CI includes zero, the corresponding strong causal claim is falsified for this learner/environment family.

## Negative-control audit

For S0 and S2, intervention arms must not create structural drift greater than 0.10 absolute Jaccard-error increase relative to the S+Q+ arm. If they do, interpretation is downgraded because the intervention may simply destabilize the learner.

## Interpretation boundary

A positive result would show that residual-sensitive evidence weighting and/or preservation of model uncertainty has a causal role in adaptation in this generic online learner. It would **not** prove the original TST cycle or establish Shadow/Seeking as universal causal entities.

A negative result would mean that, after Phase 1–1c already rejected the strong temporal claims, these operationalized mechanisms also fail to show the preregistered causal effect in this independent adaptive-learning setting.
