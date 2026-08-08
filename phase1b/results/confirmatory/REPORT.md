# TST Phase 1b — Conditional Temporal Order Confirmatory Report

## Verdict

\[
\boxed{\text{Conditional-order hypothesis not supported}}
\]

Phase 1b tested a weaker follow-up to the rejected Phase 1 mandatory-chain claim. The new question was:

> If Shadow, Seeking, and Transformation all occur in the same run, is their order strongly biased toward `Shadow → Seeking → Transformation`?

The preregistered effect-size target was `Omega_c >= 0.70`.

## Confirmatory result

900 new runs were executed across S5, S7, and S9, 300 seeds per scenario. The Phase 1 detector and all thresholds were kept unchanged.

Complete triads occurred in 62/900 runs. Of those 62 runs, 35 followed the complete TST order:

\[
\Omega_c=\frac{35}{62}=0.5645.
\]

The 95% Wilson interval was:

\[
[0.4409,\;0.6806].
\]

Therefore the preregistered 0.70 effect-size threshold was not reached, and the lower confidence bound did not exceed 0.50.

## Gate table

| Gate | Criterion | Result | PASS/FAIL |
|---|---|---:|---|
| B1 | complete triads >=25 | 62 | **PASS** |
| B2 | `Omega_c >=0.70` | 0.5645 | **FAIL** |
| B3 | 95% Wilson lower bound >0.50 | 0.4409 | **FAIL** |
| B4 | matched timing null: p<0.01 and delta>=0.10 | p<0.0001, delta=+0.2097 | **PASS** |

Because B2 and B3 failed, the conditional-order hypothesis is not supported under the preregistered rule.

## Important surviving signal: order is not random

Although the strong 0.70 claim failed, the observed order was not explained by marginal event timing alone.

A scenario-stratified event-time permutation null was built by independently shuffling `tau_S` and `tau_Q` among complete-triad runs while keeping `tau_T` fixed. Across 10,000 permutations:

- observed `Omega_c`: 0.5645
- null median: 0.3548
- null 95th percentile: 0.4355
- observed minus null median: +0.2097
- empirical p-value: <0.0001

Thus complete triads show a statistically detectable TST-order enrichment, but not one strong enough to justify the preregistered `>=0.70` claim.

## Scenario heterogeneity

| Scenario | T detected | Complete triads | Ordered | Omega_c |
|---|---:|---:|---:|---:|
| S5 direction reversal | 122/300 | 11 | 9 | 0.8182 |
| S7 abrupt large change | 277/300 | 48 | 24 | 0.5000 |
| S9 recurrent change | 31/300 | 3 | 2 | 0.6667 |

The pooled result is dominated by S7 because it contributes 48/62 complete triads. In S7 the conditional order rate is exactly 0.50, despite a matched-null median of 0.3333. S5 shows a much stronger point estimate (0.8182), but only 11 complete triads, so its uncertainty remains large.

This heterogeneity is important. It argues against treating `S→Q→T` as one fixed sequence that applies equally across types of structural change.

## Raw-X block-permutation audit

A stricter audit was run on the first 100 seeds of each scenario, 300 paired runs total. The stable baseline was preserved, while the post-baseline raw multivariate X series was permuted in 20-step blocks and the entire learner was rerun.

Raw-X permutation results:

- complete triads: 12/300
- ordered triads: 3/12
- conditional order: `Omega_c = 0.25`
- 95% Wilson interval: [0.0889, 0.5323]

For the same 300 original runs, 19 runs contained a correctly ordered complete triad; after raw-X permutation only 3 did. Paired discordances were 17 original-only versus 1 raw-only, giving an exact McNemar p-value of approximately 0.000145.

This means the observed TST-like sequence depends on genuine temporal organization in the raw series. It is not produced equally often after destroying long-range block order.

## Interpretation

Phase 1b rejects the strong conditional statement:

\[
P(S<Q<T\mid S,Q,T\text{ all occur})\ge0.70.
\]

But it also rejects the opposite simplistic interpretation that the order is purely accidental. The data support a narrower statement:

> When all three independently measured events co-occur, `S→Q→T` occurs more often than expected from matched event-time marginals and is weakened by raw-X temporal permutation, but the strength of that bias depends strongly on the transformation regime.

The current evidence therefore suggests that TST's temporal cycle is better treated as a **regime-dependent pathway** than as a universal or strongly dominant sequence.

## Implication for the next experiment

The next scientifically useful step should not tighten thresholds until the target passes. It should explain the scenario heterogeneity.

A Phase 1c candidate is to test whether structural-change geometry moderates the sequence:

\[
P(S<Q<T\mid C,\;Z_{\text{change}}),
\]

where `Z_change` describes transformation type and severity independently of Shadow and Seeking. The key question becomes whether direction reversal, abrupt rewiring, gradual rewiring, and recurrent rewiring occupy different transformation pathways.

That would shift TST from a single mandatory cycle toward a falsifiable **mixture-of-pathways theory of transformation**.
