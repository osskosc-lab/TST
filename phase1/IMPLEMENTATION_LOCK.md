# TST Phase 1 — Implementation Lock

This file records implementation choices that were not fully specified by the preregistration. They were fixed before the 500-run confirmatory dataset was analyzed.

## TST-agnostic learner

The learner never reads `S`, `Q`, `DG`, TST phase labels, or gate outcomes when updating its models.

### Seeking / predictive ensemble

Five rolling ridge VAR(1) candidate models use memory windows `60, 100, 160, 250, 400` steps. They are refit every 10 steps with ridge coefficient 1.0. Model posterior evidence is based on the most recent 30 predictive log-likelihoods. Seeking is Shannon entropy over the candidate posterior.

### Shadow likelihood

Shadow uses the ensemble mixture predictive likelihood, normalized per node, then standardized against the pre-change baseline interval `t=200..299`.

### Topology learner

Topology is estimated independently from Shadow and Seeking using a long-memory multivariate recursive least-squares model initialized on the known stable calibration span `t=0..299`.

- forgetting factor: 0.995
- initial edge magnitude threshold: 0.12
- edge-add threshold: 0.16
- edge-drop threshold: 0.08
- topology decision interval: 10 steps
- add/drop evidence persistence: 3 topology updates
- graph lag L: 80 steps

For fixed labeled directed nodes, normalized graph edit distance is implemented as Jaccard edge-set distance:

\[
D_G(A,B)=\frac{|E_A\triangle E_B|}{|E_A\cup E_B|}.
\]

## Calibration rule

Calibration was used only to eliminate measurement artifacts such as startup convergence being misclassified as Transformation. The final locked topology detector produced, on a separate negative-control audit before confirmatory analysis:

- S0 Transformation FPR: 0/50
- S1 Transformation FPR: 1/50
- S2 Transformation FPR: 0/50

No confirmatory threshold was changed after that lock.

## Confirmatory execution

The 50 seeds per scenario were computed in two deterministic batches (`0–24` and `25–49`) only to satisfy execution limits. All confirmatory statistics were computed after merging all 500 runs.

## Block-permutation implementation note

The executed 1,000-replicate null independently block-permutes the measured phase series `S_t`, `Q_t`, and `DG_t` in 20-step blocks, preserving each marginal block autocorrelation while breaking cross-phase temporal alignment.

This is computationally distinct from re-running the entire online learner on 500 × 1,000 raw-`X` block permutations. Therefore G2 should be read as the preregistered temporal-order null implemented at the measured-series level. A fully raw-series permutation audit would be a stricter follow-up.

This distinction does not affect the G1 result, which by itself triggers the preregistered core falsification rule.
