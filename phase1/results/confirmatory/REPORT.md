# TST Phase 1 — Confirmatory Falsification Report

## Verdict

\[
\boxed{\text{Core temporal hypothesis falsified}}
\]

The preregistered strong claim was that detected structural Transformation should ordinarily be preceded by `Shadow → Seeking → Transformation` in that order.

In 500 confirmatory runs, 78 runs produced a detected Transformation. Only 5 satisfied the complete preregistered order:

\[
\Omega=\frac{5}{78}=0.0641.
\]

This is far below the G1 support threshold of 0.70.

## Gate table

| Gate | Criterion | Result | PASS/FAIL |
|---|---|---:|---|
| G1 | \(\Omega\ge0.70\) | 0.0641 | **FAIL** |
| G2 | BCa lower bound of \(\Delta\Omega>0.10\) | 0.0256 | **FAIL** |
| G3 | S0 and S1 FPR both <5% | S0=0%, S1=6% | **FAIL** |
| G4 | S2 parameter-only misdetection <10% | 0% | **PASS** |
| G5 | \(\Delta AUC_{S+Q}\ge0.03\) | +0.1306 | **PASS** |

**Passed: 2/5.**

## Primary statistics

- Transformation-detected trials: 78 / 500
- correct `S→Q→T`: 5 / 78
- \(\Omega\): 0.0641
- block-permutation median \(\Omega_{null}\): 0.0000
- \(\Delta\Omega\): 0.0641
- 95% BCa CI for \(\Delta\Omega\): [0.0256, 0.1410]
- null 2.5–97.5% range: [0.0000, 0.0128]

## Negative controls

- S0 stable: Transformation FPR = 0/50 = 0%
- S1 noise-only: Transformation FPR = 3/50 = 6% — just above the preregistered 5% ceiling
- S2 weight-only: Transformation misdetection = 0/50 = 0%
- S8 ambiguity control: Seeking detected in 50/50 while Transformation detected in 0/50

S2 is especially important: the topology detector did not simply relabel parameter adaptation as structural change.

## Seeking still carries predictive information

For whether Transformation occurs within the next 20 steps:

- AUC using Shadow only: 0.5238
- AUC using Shadow + Seeking: 0.6544
- \(\Delta AUC\): +0.1306

Thus the confirmatory experiment rejects **Seeking as a mandatory phase in a universal three-stage chain**, while still finding that Seeking contributes predictive information in this synthetic learner.

## What actually happened in Transformation trials

Among the 78 Transformation-detected runs:

- 35 had neither Shadow nor Seeking event
- 27 had Seeking but no Shadow
- 10 had Shadow but no Seeking
- only 6 had both Shadow and Seeking

Among those 6 rare complete triads, 5 followed `S→Q→T` and 1 followed `Q→S→T`.

That suggests a weaker hypothesis for a later preregistration: **conditional on all three events occurring, their order may often be TST-like**, but the complete triad is not a necessary path to Transformation in Phase 1. This conditional observation is post-hoc and must not be counted as Phase 1 support.

## Scenario-level Transformation detection

| Scenario | Transformation detection | Omega |
|---|---:|---:|
| S0 | 0/50 | — |
| S1 | 3/50 | 0.000 |
| S2 | 0/50 | — |
| S3 | 0/50 | — |
| S4 | 1/50 | 0.000 |
| S5 | 19/50 | 0.000 |
| S6 | 3/50 | 0.000 |
| S7 | 48/50 | 0.104 |
| S8 | 0/50 | — |
| S9 | 4/50 | 0.000 |

## Methodological caveat

The executed 1,000-replicate block null permuted the measured `S`, `Q`, and `DG` series in 20-step blocks rather than re-running the entire learner on raw-`X` block permutations. See `IMPLEMENTATION_LOCK.md`.

Because G1 fails by a very large margin, the core Phase 1 verdict does not depend on this G2 implementation detail.

## Interpretation

The experiment does **not** show that Shadow, Seeking, or Transformation are useless concepts. It shows something narrower and scientifically useful:

> In this independent synthetic dynamic-network learner, `Shadow → Seeking → Transformation` did not behave as a universal mandatory temporal chain.

The strongest surviving result is a weaker one: Seeking adds predictive information, and the TST order appears in most of the very small subset where all three events are present. That is a candidate for a new, explicitly weaker Phase 1b hypothesis—not a rescue of the failed Phase 1 claim.
