# TST Phase 1 — 動的ネットワーク反証実験・事前登録プロトコル v1.0

## Confirmatory claim

Phase 1 tests one strong temporal claim only:

\[
H_{\mathrm{TST}}:\quad \tau_S < \tau_Q < \tau_T
\]

That is, before a structural transformation, a measurable increase in Shadow must precede a measurable Seeking state, which must precede Transformation. Failure is evidence against the **strong mandatory temporal-order hypothesis**, not against every descriptive use of TST.

## System and generator

\[
G_t=(V,E_t,W_t,X_t),\qquad X_{t+1}=W^{(r_t)}X_t+\epsilon_t,
\quad \epsilon_t\sim\mathcal N(0,\sigma^2I).
\]

The learner is not told the change point or the new structure. TST labels are never used as update rules.

Fixed main conditions:

- nodes: \(|V|=20\)
- edge density: \(\rho=0.15\)
- length: \(T=1000\)
- change point: \(t_c\sim U(350,650)\)
- noise: \(\sigma=0.30\)
- confirmatory seeds: 50 per scenario = 500 runs
- calibration seeds: 10 per scenario, excluded from hypothesis testing
- stress seeds: 100 per scenario, only after confirmatory lock

## Operational definitions

### Shadow

\[
e_t=-\log p(X_t\mid G_{t-1}),\qquad
S_t=\frac{e_t-\mu_{base}}{\sigma_{base}}.
\]

Shadow fires at the first time \(S_t>2\) for 3 consecutive steps. That time is \(\tau_S\). Graph distance is never used to compute Shadow.

### Seeking

For candidate models \(M_1,\ldots,M_K\) with online posterior weights,

\[
Q_t=-\sum_k p(M_k\mid D_{1:t})\log p(M_k\mid D_{1:t}).
\]

Seeking fires when \(Q_t\) exceeds the baseline 95th percentile for 3 consecutive steps. That time is \(\tau_Q\).

### Transformation

For the learner's estimated graph \(\hat G_t\),

\[
D_G(t)=D(\hat G_t,\hat G_{t-L}).
\]

Transformation fires when normalized graph distance is at least 0.20 and remains so for at least 10 steps. That time is \(\tau_T\). Prediction improvement alone is not Transformation.

## Scenarios

| ID | Condition | Role |
|---|---|---|
| S0 | completely stable | negative control |
| S1 | noise increase only | Shadow false-positive audit |
| S2 | weight-only change | parameter-learning control |
| S3 | edge addition | Transformation |
| S4 | edge deletion | Transformation |
| S5 | edge-direction reversal | strong Transformation |
| S6 | gradual structural change | gradual case |
| S7 | abrupt large structural change | abrupt case |
| S8 | ambiguity / Seeking increase without intended structural change | Seeking false-positive audit |
| S9 | multiple structural changes | recurrent-cycle case |

## Primary metric

Among trials in which Transformation is detected,

\[
I_i=\mathbf 1(\tau_S<\tau_Q<\tau_T),\qquad
\Omega=\frac{1}{N}\sum_i I_i.
\]

## Null baseline

20-step block permutation, 1,000 replicates, preserving within-block temporal dependence while disrupting cross-phase temporal alignment. See `IMPLEMENTATION_LOCK.md` for the exact computational realization.

## Gates

- **G1**: \(\Omega\ge0.70\)
- **G2**: lower 95% BCa bound of \(\Delta\Omega=\Omega-\mathrm{median}(\Omega_{null})\) is \(>0.10\)
- **G3**: Transformation FPR in both S0 and S1 is \(<0.05\)
- **G4**: S2 weight-only Transformation misdetection is \(<0.10\)
- **G5**: \(\Delta AUC=AUC_{S+Q}-AUC_S\ge0.03\), predicting Transformation within \(H=20\)

Decision rule:

- 5/5: Strong preliminary support
- 4/5: Conditional support
- 3/5 or fewer: Not supported
- **If G1 or G2 fails: Core temporal hypothesis falsified**

## Statistical plan

- BCa bootstrap: 2,000 resamples
- secondary multiple comparisons: Benjamini–Hochberg, \(q=0.05\), when inferential p-values are reported
- confirmatory results are immutable after execution

## Interpretation boundary

Even a positive result would only show that an independent dynamic-network learner exhibits the preregistered temporal ordering under these synthetic conditions. It would not prove TST as a universal theory.
