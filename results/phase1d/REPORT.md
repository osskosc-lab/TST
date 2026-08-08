# TST Phase 1d — Shadow / Seeking Causal Intervention Report

## Executive verdict

Phase 1d does **not** yet establish clean causal roles for both Shadow and Seeking.

- **Shadow:** inconclusive. The preregistered manipulation-strength check failed, and the estimated effect was small and compatible with zero.
- **Seeking:** the preregistered primary causal gates all passed, with a large paired effect, but the intervention also strongly degraded stable and weight-only negative controls. Therefore the Seeking result is **not mechanism-specific enough to count as a clean TST causal confirmation**.

The scientifically conservative interpretation is:

> Preserving model uncertainty is strongly associated with better structural adaptation in this learner, but the Q− intervention was too globally destabilizing to identify a specific causal role for Seeking. Shadow remains unresolved because its intervention was too weak.

## Design

The experiment used a paired 2×2 factorial intervention. Every environment seed was evaluated under the same four arms and the same raw observations:

- S+Q+: full residual evidence + normal hypothesis diversity
- S+Q−: full residual evidence + posterior sharpening (`gamma=4`)
- S−Q+: clipped residual evidence + normal diversity
- S−Q−: both interventions

All five candidate RLS learners received identical raw observations in every arm. Only evidence processing and posterior propagation differed.

Primary structural environments:

- S5 direction reversal: 200 seeds
- S7 abrupt large mixed change: 200 seeds

Negative controls:

- S0 stable: 100 seeds
- S2 weight-only: 100 seeds

Total: 600 environments × 4 arms = **2,400 learner-arm runs**.

## Manipulation checks

### Shadow manipulation

Preregistered requirement: at least 20% reduction in residual-evidence contribution.

Observed:

`15.79%`

**FAIL.**

Therefore the Shadow null cannot be treated as a valid strong causal falsification; the intervention did not move the intended mechanism enough.

### Seeking manipulation

Mean posterior entropy:

- Q+: `0.8301`
- Q−: approximately `0`

Entropy reduction: essentially `100%`.

**PASS.**

## Primary causal effects

Primary outcome: AUGE, mean Jaccard graph error over the first 200 post-change steps. Positive ATE means removing the mechanism worsened adaptation.

### Shadow

`ATE_S = +0.00609`

95% BCa CI:

`[-0.00200, +0.01442]`

Scenario estimates:

- S5: `+0.00215`
- S7: `+0.01003`

Gate results:

- DS1 manipulation: FAIL
- DS2 ATE >= 0.03: FAIL
- DS3 BCa lower bound > 0.01: FAIL
- DS4 positive in both scenarios: PASS

**Verdict: Shadow manipulation invalid / causal relevance unresolved.**

### Seeking

`ATE_Q = +0.20345`

95% BCa CI:

`[+0.18312, +0.22261]`

Scenario estimates:

- S5: `+0.24255`
- S7: `+0.16435`

Gate results:

- DQ1 manipulation: PASS
- DQ2 ATE >= 0.03: PASS
- DQ3 BCa lower bound > 0.01: PASS
- DQ4 positive in both scenarios: PASS

**Raw primary-gate verdict: Seeking causal relevance supported.**

However, this must be qualified by the negative-control audit below.

## Recovery success

Recovery success rates across structural environments:

- S+Q+: `39.25%`
- S+Q−: `18.50%`
- S−Q+: `36.50%`
- S−Q−: `18.25%`

Suppressing hypothesis diversity approximately halved recovery success.

## Interaction

Factorial interaction:

`-0.000043`

95% BCa CI:

`[-0.01667, +0.01691]`

There is no evidence that the Shadow and Seeking interventions synergize in this design.

## Negative-control audit

The preregistration required intervention-induced drift to remain <=0.10 relative to S+Q+.

### S0 stable

Baseline S+Q+ AUGE: `0.0512`.

Arm increases relative to baseline:

- S+Q−: `+0.4043`
- S−Q+: `+0.0055`
- S−Q−: `+0.3991`

### S2 weight-only

Baseline S+Q+ AUGE: `0.0537`.

Arm increases relative to baseline:

- S+Q−: `+0.3107`
- S−Q+: `+0.0043`
- S−Q−: `+0.2973`

**Negative-control audit: FAIL.**

The failure is driven almost entirely by Q− posterior collapse. The Shadow intervention by itself does not destabilize controls.

## Interpretation

The Seeking manipulation produced a very large and statistically precise structural-adaptation effect, but it also severely damaged performance when no structural adaptation was required. Thus the intervention is not selective: aggressively collapsing model uncertainty appears to be globally harmful to this ensemble learner.

Therefore Phase 1d supports the weaker statement:

> Maintaining multiple live model hypotheses is functionally important for this online structural learner.

But it does **not** yet justify the stronger TST-specific statement:

> Seeking, as a distinct causal phase of transformation, has been experimentally established.

Likewise, Shadow cannot be declared irrelevant because its preregistered intervention failed the manipulation-strength check.

## What Phase 1d changes in the TST research program

Across Phase 1 → 1b → 1c, the universal temporal-cycle interpretation weakened. Phase 1d provides the first strong functional signal, but it points toward **model diversity / uncertainty preservation** rather than the original three-stage sequence.

The next clean experiment should use:

1. a milder, non-destabilizing Seeking intervention calibrated only on S0/S2 negative controls, then frozen before structural testing; and
2. a stronger Shadow intervention that demonstrably moves residual-evidence use by >=20% without destabilizing controls.

Only then can the causal roles of the two mechanisms be separated from generic learner damage.

## Reproducibility

- GitHub Actions run: `31252223338`
- confirmatory artifact ID: `9020353104`
- branch: `agent/tst-phase1d-causal-intervention`
- PR: #4
