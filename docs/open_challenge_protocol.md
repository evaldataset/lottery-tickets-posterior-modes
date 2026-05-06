# Open Posterior-vs-IMP Challenge Protocol

This hand-written protocol document defines a standing, adversarial-collaboration
style challenge built on the released audit framework. It exists so that the
paper's negative claim is structurally falsifiable by third parties after
publication, not only by the authors.

## Motivation

The paper rejects the weak posterior-mode hypothesis (WPMH) under the twelve
posterior approximation configurations the authors could test. The strongest
possible defense of a negative result is to let proponents of the hypothesis
choose their own best posterior construction and run it under the identical
pre-specified contract. This protocol makes that concrete.

## Challenge contract

1. **Fixed gate.** The operational support-equivalence gate is the one shipped
   in `scripts/run_mode_ticket_distribution_probe.py` at the released commit:
   the same six axes (layer-sparsity KS, Hamming-overlap, logit CKA, Hungarian
   cost, activation CKA, activation Hungarian cost), the same thresholds, and
   the same five-seed / matched-sparsity protocol. Challengers do not get to
   move the gate; the authors do not get to move it either.
2. **Free posterior.** A challenger may submit _any_ posterior approximation
   or sampling procedure over the released training setup (CIFAR-10
   ResNet-20, epoch-1 rewind, the pinned environment lock), including
   multimodal families (deep ensembles, tempered MCMC, normalizing-flow
   posteriors) and trajectory-conditioned constructions, provided:
    - posterior samples are produced by code runnable under
      `requirements-gpu-lock.txt` or an equivalent pinned container;
    - sample accuracy stays within 2 percentage points of the dense baseline
      (the validity criterion that excludes degenerate samplers, the same one
      that excludes the frozen-BN vanilla SGLD row);
    - the submission declares its configuration _before_ seeing per-seed gate
      outputs (selection on the gate is the failure mode the locked-test
      protocol exists to prevent).
3. **Success criterion.** A submission supports WPMH if and only if it passes
   the full joint gate (all six axes) on the five-seed direct probe _and_
   its posterior-minus-chain-start support gap exceeds the materiality margin
   (+0.005 Jaccard) under the seed-level paired audit
   (`scripts/audit_direct_mode_ticket_seed_level_artifacts.py`). Single-axis
   passes are recorded but do not count, consistent with the family-wise
   audit (`docs/familywise_null_audit.md`).
4. **Reporting.** The authors commit to acknowledging any gate-passing
   submission as a refutation of the paper's negative claim in a public
   erratum or follow-up, and to recording all submissions (pass or fail) in
   a public registry file in the released repository.

## Submission mechanics

- Open an issue on the public repository (or contact the authors during
  anonymous review via the OpenReview forum) with: the sampler code or
  container reference, the declared configuration, and the per-seed
  `metrics.json` outputs of the unmodified probe script.
- The authors re-run the probe on the declared configuration with the
  released harness on pinned seeds 0--4 and publish the gate outputs.
- Compute responsibility lies with the challenger for exploratory sweeps;
  the authors re-run only the single declared configuration.

## Status

- Registry: no external submissions yet (protocol published with the paper).
- This document is hand-written policy, not generated output; the audit
  framework files it references are generated and verified by `make check`.
