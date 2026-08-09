# TST Phase 1e — Selective Causal Intervention Report

## Verdict

- **Shadow: selective causal relevance not supported**
- **Seeking: no safe intervention found**

Phase 1e was designed to resolve the two confounds left by Phase 1d: insufficient Shadow manipulation and nonspecific destabilization under aggressive Seeking suppression.

## Stage A — negative-control calibration

Calibration used disjoint S0/S2 seeds only.

### Seeking

Even the mildest preregistered posterior-sharpening intervention, `gamma=1.10`, reduced posterior entropy by 91.21% but increased AUGE by:

- S0 stable: +0.05028
- S2 weight-only: +0.05391

Both exceed the fixed safety ceiling of +0.05. Stronger gamma values were substantially more damaging. Therefore **no Seeking intervention qualified as safe**, and no confirmatory causal credit is permitted.

### Shadow

`clip_sq=3.0` was the mildest adequate safe intervention:

- residual-evidence reduction: 21.95%
- S0 AUGE increase: +0.01027
- S2 AUGE increase: +0.01556

It therefore passed calibration and was frozen before confirmatory testing.

## Stage B — confirmatory experiment

New disjoint confirmatory seeds:

- S5: 300
- S7: 300
- S0 holdout control: 100
- S2 holdout control: 100

Total learner-arm rows: **3,200**.

### Shadow manipulation

The frozen `clip_sq=3.0` intervention reduced residual evidence by **23.49%** in the structural confirmatory sample, confirming that the manipulation remained adequate out of calibration.

### Structural Shadow effect

Pooled S5/S7 removal effect on post-change AUGE:

- ATE: **+0.014169**
- 95% BCa: **[+0.013037, +0.015421]**

Scenario effects:

- S5: +0.015332
- S7: +0.013006

The effect is precise and positive in both structural scenarios.

### Holdout-control Shadow effect

Pooled S0/S2 effect:

- ATE: **+0.011429**
- 95% BCa: **[+0.009221, +0.013877]**

By scenario:

- S0: +0.012670
- S2: +0.010188

Thus most of the observed structural effect is also present when no structural adaptation is required.

### Selectivity

Difference-in-differences:

`DID = structural ATE - control ATE`

- DID: **+0.002740**
- 95% BCa: **[+0.000010, +0.005271]**

The excess structural effect is statistically positive but far below the preregistered practical threshold of +0.02.

## Gates

### Shadow

- ES1 safe adequate calibration: **PASS**
- ES2 holdout controls safe: **PASS**
- ES3 structural ATE >=0.03: **FAIL**
- ES4 structural BCa lower bound >0.01: **PASS**
- ES5 positive in S5 and S7: **PASS**
- ES6 DID >=0.02 and BCa lower bound >0: **FAIL**

Result: **4/6 gates passed**, but both effect-size gates failed.

### Seeking

- EQ1 safe calibration: **FAIL**

Because no safe intervention existed in the preregistered candidate set, the confirmatory Q arms were effectively identical. Their zero effect is therefore **not a falsification of Seeking**; it is a stopped causal test.

## Interpretation

Phase 1e provides a sharper result than Phase 1d.

1. Residual-evidence retention has a small, reproducible functional effect on this learner.
2. That effect is not sufficiently selective to structural transformation: most of it also appears in stable/weight-only operation.
3. Therefore the tested Shadow-like mechanism does not meet the preregistered standard for a strong transformation-specific causal role.
4. Posterior sharpening remains unsuitable as a clean Seeking intervention because even mild recursive sharpening collapses uncertainty and begins to damage control performance.

The strongest defensible conclusion is:

> In this synthetic online structural learner, residual-evidence retention contributes weakly to general estimation quality but is not established as a transformation-specific causal mechanism. Maintaining hypothesis diversity may be important, but the current posterior-sharpening intervention cannot isolate that role without nonspecific damage.

## Reproducibility

- GitHub Actions run: `31293715389`
- confirmatory artifact: `tst-phase1e-confirmatory`
- artifact ID: `9032275851`
- calibration and confirmatory seeds are disjoint
- final confirmatory statistics were computed only after fixed calibration and merging all confirmatory shards
