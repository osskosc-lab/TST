# TST Phase 1b — Conditional Temporal Order Falsification Protocol v1.0

## Rationale

Phase 1 rejected the strong mandatory-chain claim because only 5/78 detected Transformations followed `Shadow → Seeking → Transformation` (`Omega=0.0641`). However, among the six runs in which all three events occurred, five followed the TST order. Phase 1b tests that weaker claim as a new preregistered hypothesis rather than treating it as a rescue of Phase 1.

## Confirmatory hypothesis

Condition on runs in which all three events are detected:

\[
C=\{\tau_S,\tau_Q,\tau_T\text{ all finite}\}.
\]

The primary quantity is

\[
\Omega_c=P(\tau_S<\tau_Q<\tau_T\mid C).
\]

The confirmatory claim is that complete triads show a strong TST-order bias:

\[
H_{1b}:\Omega_c\ge 0.70.
\]

This is explicitly weaker than the Phase 1 claim. It says nothing about Transformation runs that lack Shadow or Seeking.

## Locked measurement system

All Phase 1 measurement definitions and thresholds remain unchanged:

- Shadow: standardized predictive surprisal, `S>2` for 3 consecutive steps.
- Seeking: candidate-model posterior entropy above the baseline 95th percentile for 3 consecutive steps.
- Transformation: normalized graph distance `DG>=0.20` persisting for at least 10 steps.
- topology learner, candidate windows, baseline interval, graph lag, and all other detector parameters are inherited unchanged from Phase 1.

No Phase 1b result may be used to retune those values.

## Confirmatory scenarios and sample size

Main scenarios are the Phase 1 transformation-capable structural regimes:

- S5: edge-direction reversal
- S7: abrupt large structural change
- S9: recurrent structural change

Each receives 300 new seeds, for 900 confirmatory runs total. Seeds are disjoint from Phase 1.

The targeted regime is declared up front: Phase 1b does not claim generality to stable, noise-only, or weak-change regimes.

## Primary gates

A complete triad is a run in which Shadow, Seeking, and Transformation are all detected.

- **B1 — information gate:** at least 25 complete triads.
- **B2 — effect-size gate:** `Omega_c >= 0.70`.
- **B3 — uncertainty gate:** lower bound of the 95% Wilson interval for `Omega_c` is `>0.50`.
- **B4 — matched timing null:** within each scenario, independently permute `tau_S` and `tau_Q` across complete-triad runs while leaving `tau_T` fixed. Use 10,000 permutations. Require both `p<0.01` and `Omega_c - median(Omega_null) >= 0.10`.

Decision rule:

- all 4 gates pass: **Conditional-order hypothesis supported in targeted regimes**
- B1 fails: **Inconclusive — insufficient complete triads**
- B2 or B3 fails: **Conditional-order hypothesis not supported**
- otherwise: **Partial/conditional evidence only**

## Raw-X block-permutation audit

As a stricter stress test, run one deterministic 20-step block permutation of the post-baseline raw multivariate `X` series for the first 100 seeds of each scenario (300 runs total), rerun the complete learner, and recompute complete-triad frequency and conditional order.

This audit is reported separately from the four confirmatory gates because raw-X permutation can change both event incidence and event timing.

## Interpretation boundary

A positive Phase 1b result would not restore the rejected Phase 1 mandatory-chain hypothesis. It would support only a conditional statement: when the three independently measured events co-occur in the targeted structural regimes, their order is strongly biased toward `S→Q→T`.
