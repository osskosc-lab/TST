# TST Phase 1c — Confirmatory Regime-Conditioned Pathway Report

## Verdict

**Regime-conditioned pathway hypothesis not supported.**

Phase 1c tested whether Transformation is better represented as a mixture of measurable pathways whose probabilities depend predictably on the structural transformation regime.

The Phase 1 Shadow / Seeking / Transformation detector was kept unchanged.

## Confirmatory dataset

- total runs: 1,600
- structural runs: 1,400
- structural Transformation detections: 1,086
- all 7 structural regimes produced at least 50 detected Transformations
- negative controls: 100 stable + 100 weight-only

## Gate result

| Gate | Criterion | Result | Decision |
|---|---|---:|---|
| C1 | >=500 structural T detections and >=5/7 regimes with >=50 | 1,086; 7/7 | PASS |
| C2 | Cramér's V >=0.20, permutation p<0.001, above null q99 | V=0.1318; p=9.999e-05; q99=0.0997 | FAIL |
| C3 | 5-fold log-loss gain >=0.05 | 0.01227 | FAIL |
| C4 | LORO median gain >0 and >=5/7 positive | median=0.00491; 4/7 positive | FAIL |

Passed: **1/4**.

Detector audit passed:

- stable Transformation FPR: 0%
- weight-only Transformation misdetection: 0%

## Main finding

The pathway distribution was **not random with respect to regime**. The observed Cramér's V of 0.1318 exceeded the 99th percentile of the 10,000-permutation null (0.0997), with empirical p approximately 0.0001.

However, the effect size was below the preregistered minimum V=0.20. More importantly, preregistered structural descriptors improved 5-fold held-out pathway log loss by only 1.23%, far below the required 5%.

Thus the data show **weak but statistically detectable heterogeneity**, not a useful regime-conditioned predictive pathway law.

## Pathway counts

Across 1,086 structural Transformation detections:

- T_ONLY: 415
- S_ONLY: 103
- Q_ONLY: 439
- S_Q_T: 91
- Q_S_T: 38

The dominant routes were therefore `T_ONLY` and `Q_ONLY`, not the complete TST triad.

## Regime-level results

### R1 reverse 25%

- T detected: 79/200 = 39.5%
- complete triads: 10
- S→Q→T among complete triads: 30.0%

### R2 reverse 50%

- T detected: 200/200 = 100%
- complete triads: 50
- S→Q→T among complete triads: 70.0%

### R3 mixed abrupt

- T detected: 188/200 = 94.0%
- complete triads: 26
- S→Q→T among complete triads: 69.2%

### R4 mixed gradual

- T detected: 187/200 = 93.5%
- complete triads: 17
- S→Q→T among complete triads: 70.6%

### R5 add-heavy

- T detected: 66/200 = 33.0%
- complete triads: 9
- S→Q→T among complete triads: 55.6%

### R6 delete-heavy

- T detected: 170/200 = 85.0%
- complete triads: 5
- S→Q→T among complete triads: 40.0%

### R7 recurrent mixed

- T detected: 196/200 = 98.0%
- complete triads: 55
- S→Q→T among complete triads: 29.1%

## Out-of-sample prediction

Five-fold multinomial prediction from preregistered generator-side descriptors produced:

- model log loss: 1.26656
- frequency-baseline log loss: 1.28229
- normalized gain: **1.23%**

This is statistically compatible with small structural differences but does not meet the preregistered requirement for practically meaningful pathway prediction.

Leave-one-regime-out gains were:

- reverse25: +0.0126
- reverse50: +0.0288
- mixed abrupt: +0.0056
- mixed gradual: -0.0118
- add-heavy: -0.0208
- delete-heavy: +0.0049
- recurrent mixed: -0.0015

Median gain was +0.0049, with only 4/7 regimes positive. Therefore the pathway model did not transfer reliably to an unseen transformation regime.

## Interpretation

Phase 1c narrows TST further.

The results do **not** support:

> each transformation regime has a strong, predictably different TST pathway law.

What remains supported at a weaker descriptive level is:

> pathway frequencies vary somewhat across structural changes, and those differences are unlikely to be pure sampling noise.

But the variation is too weak and too poorly generalizable to justify a predictive regime-conditioned pathway theory under the preregistered standard.

Across Phase 1 → 1b → 1c, the evidence now points away from a universal or strongly regime-determined `Shadow → Seeking → Transformation` mechanism. The more defensible role for TST at this stage is as a descriptive decomposition of transformation dynamics, unless a new independent mechanism can predict when Shadow and Seeking will become causally relevant rather than merely co-occur.

## Reproducibility

GitHub Actions confirmatory workflow run: `31248767753`.

Result artifact: `tst-phase1c-confirmatory`, artifact ID `9019336723`.
