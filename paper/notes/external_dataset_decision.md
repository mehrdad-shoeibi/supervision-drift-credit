# External Dataset Decision for Current Paper Version

**Date:** 2026-06-07
**Type:** Methodological decision note (not an analysis stage).

## Decision

- We will **not** add a completely new second dataset to the current paper version.
- The current locked Stage 3–7 analysis and the final multi-signal synthesis remain
  **unchanged**.
- **No** Stage 8 external robustness analysis is added at this time.
- The current empirical scope remains **one public LendingClub lending dataset**.

## Rationale

- A second dataset could improve external breadth/generalizability **in principle**.
- However, adding one *after* the current synthesis is locked would need to be
  treated as a **fully pre-registered external robustness phase**, not as a post-hoc
  search for stronger or cleaner results (no dataset shopping).
- A valid second-dataset phase would require **locking eligibility criteria** and a
  **prior commitment to report the result** regardless of whether it is clean,
  mixed, unfavorable, or hard to interpret.
- It would also require repeating the diagnostic discipline at a comparable level of
  rigor:
  - data verification;
  - primary transfer analysis;
  - oracle-gap analysis;
  - calibration analysis;
  - feature–label stability;
  - positive-control sensitivity;
  - band notes;
  - external synthesis.
- Under the current timeline, a rushed second dataset would create **asymmetric
  risk**: modest upside if it is clean, but substantial downside if it is messy,
  underpowered, under-specified, or less rigorously analyzed than the current work.
- The decision is therefore based on **methodological integrity, asymmetric risk, a
  limited timeline, and preserving the locked analysis** — not on any expectation
  about whether a second dataset's results would be favorable. The most
  scientifically defensible choice for the current version is to preserve the locked
  analysis and focus on writing it clearly.

## Current study strength

The current study is **not** a shallow single split. Within one public LendingClub
lending dataset it includes:

- temporal transfer;
- cross-segment transfer;
- primary transfer performance;
- oracle-gap diagnostic;
- calibration diagnostic;
- feature–label stability diagnostic;
- synthetic positive-control sensitivity curve;
- locked final multi-signal synthesis.

- The contribution is the **locked diagnostic protocol and cautious evidence
  synthesis**.
- The paper should be framed as a **deeply analyzed, pre-registered diagnostic case
  study based on one public LendingClub lending dataset**.
- This internal diagnostic depth **strengthens** the study but does **not** remove
  the limitation of external breadth/generalizability. Internal diagnostic depth and
  external generalizability are **distinct dimensions**.

## Limitation to report

- The current study uses **one public LendingClub lending dataset**.
- This limits **external breadth/generalizability**.
- This should be acknowledged transparently in the paper's **Limitations** section.
- We should **not** overclaim broad generality across all tabular risk domains.
- Internal diagnostic depth does **not** eliminate the need for external replication.

Candidate limitation sentence for the paper:

> "Although this study is based on a single public LendingClub lending dataset, it
> evaluates the diagnostic protocol across multiple pre-specified transfer settings
> and complementary evidence layers, including temporal transfer, cross-segment
> transfer, oracle-gap diagnostics, calibration analysis, marginal feature-label
> stability, and a synthetic positive-control sensitivity curve. This internal
> diagnostic depth does not eliminate the need for external replication, and
> evaluation on additional datasets remains an important direction for future work."

## Future work

- **External replication on additional datasets is important future work.**
- If pursued later, it should be handled as a **separate pre-registered external
  robustness phase**.
- The dataset should be selected by **pre-specified eligibility criteria**, not by
  favorable outcomes.
- Any later external dataset should be **reported regardless** of whether results are
  clean, mixed, unfavorable, or hard to interpret.
- Optional internal robustness checks within the **same** LendingClub dataset (e.g.
  additional vintages or segments) may be considered **only if separately locked and
  clearly labeled**, and are **not** part of the current locked analysis (they must
  not reopen the current synthesis).

## Claims not made

- We do **not** claim that external replication is unnecessary.
- We do **not** claim that one public LendingClub lending dataset proves broad
  generality.
- We do **not** claim that a second dataset would be invalid in principle.
- We do **not** claim that the current limitation disappears because the internal
  analysis is deep.
- We do **not** claim that internal diagnostic depth replaces external validation.
- We do **not** reopen the locked Stage 3–7 synthesis.
- We do **not** add or imply a Stage 8 result.
- We do **not** imply that multiple independent datasets were analyzed.
