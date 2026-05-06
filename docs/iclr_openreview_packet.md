# ICLR OpenReview Packet

This generated packet collects the provisional ICLR OpenReview form
fields and upload targets. It is a local packet, not a submission
receipt, and it must be checked again after the official ICLR 2027 CFP
and OpenReview form are available.

Packet status: ready.
Ready to submit: `False`.
Official ICLR 2027 CFP observed: `False`.

## Paste Payload

Title: Winning Tickets Are Not Posterior Modes: Evidence from Posterior Support and Magnitude Controls

Keywords: lottery ticket hypothesis, Bayesian deep learning, posterior modes, network pruning, SGLD, Laplace approximation, model sparsity, reproducibility

Subject areas: Deep learning, Bayesian methods, Optimization, Generalization

Abstract words: 242

Ethics statement:

This work uses standard public benchmark datasets and does not introduce human subjects data, private personal data, surveillance data, or safety-critical deployment claims. The main risk is scientific overclaiming, which is mitigated by scoped claims, explicit limitations, and reproducible artifacts.

LLM usage disclosure:

LLM-based coding and writing assistants were used for audit/runbook scripts, reproducibility documentation, stale-claim checks, and manuscript/code-edit suggestions; they were not authors or sources of scientific evidence, and all final claims, references, code, and text were human-reviewed.

Abstract:

The lottery ticket hypothesis suggests that dense neural networks contain sparse subnetworks that can be trained in isolation when rewound to their original initialization. A tempting Bayesian interpretation is that these tickets correspond to posterior modes, or to posterior-basin supports. We turn this interpretation into a pre-specified, falsifiable test: posterior-induced masks must match IMP tickets better than local magnitude, dense-trajectory, and pruning-process controls, not merely better than uniform random masks. Across five-seed MNIST and Fashion-MNIST sparsity sweeps and a CIFAR-10 ResNet-20 epoch-1 rewind setting, fourteen posterior approximations---SGLD, SGHMC, cyclical and parallel-tempered SGLD, SWAG, the Laplace family up to joint-group full covariance, subspace HMC, and deep ensembles---fail this stronger criterion. Posterior supports often beat random masks, but they remain tied to chain-start magnitude, dominated by dense magnitude, or closer to rewind controls than to IMP. Support-equivalence is graded rather than binary: only a rank-128 Hessian-plus-diagonal Laplace crosses the mask-overlap threshold, and even it fails the layer-sparsity and basin-count gates, so a posterior account survives on one axis at one fidelity. We then give a positive account of what winning tickets are: trajectory and pruning-process objects. Dense-trajectory magnitude explains most of the fixed-mask training gap and a process-selected IMP-only residual explains the rest, with an extensive battery of process controls failing to substitute for it. This account is consistent with axial-subspace views of IMP and inconsistent with a posterior-mode view. Exact dense full-network full-covariance CIFAR posterior baselines remain an open limitation.

## Upload Files

| Role | Path | Exists | Bytes | SHA256 | Pages |
| --- | --- | ---: | ---: | --- | ---: |
| primary_iclr_submission_pdf | `paper/iclr_submission.pdf` | True | 255181 | `14f026795cbd89c1b133bbe7ab76c27607c8f561e8ffda5c297408a93cb7ff88` | 12 |
| main_only_submission_pdf | `paper/main_submission.pdf` | True | 337435 | `064230d4ea08d15050cda5b4656148691987ca00e7d25c90fc6304e5625df8e1` |  |
| appendix_inclusive_reference_pdf | `paper/main.pdf` | True | 440736 | `8e9177bdb97dedca4ee600b2da440b4e2e0293154058ef3c5ad90a561fa61455` |  |
| paper_source_tex | `paper/main.tex` | True | 50592 | `c964c268d88f316119768a06bcc0a23b43b165072de9b0d9683f059a486327ea` |  |
| bibliography_source_bib | `paper/refs.bib` | True | 5639 | `2ca52c6d19659b7397109579dabfa21fa5536a83b80d6d8f907a15342f82fc1e` |  |
| optional_supplementary_artifact_archive | `dist/lottery_artifact_public_release_2026-05-06.tar.gz` | True | 372574021 | `not-recorded` |  |

## Required Human Fields

- `author_names`
- `author_emails`
- `author_affiliations`
- `author_openreview_profiles`
- `author_conflicts_of_interest`
- `author_order_confirmed`
- `submission_agreement_confirmed`

## Double-Blind Policy

- `paper_author_field_must_be_anonymous`: `True`
- `omit_public_artifact_urls_from_initial_submission`: `True`
- `artifact_archive_must_remain_anonymous`: `True`
- `human_author_identity_fields_not_stored_in_this_public_packet`: `True`

## Risk Flags

- none

## Open Risk Flags

- iclr_2027_official_cfp_not_observed
- iclr_openreview_author_profile_and_coi_not_recorded
- iclr_openreview_submission_receipt_not_observed

## Do Not Paste Or Upload

- Do not paste public repository, archive, CI, or GPU-log URLs into the
  initial double-blind submission form unless the official venue form
  explicitly requests them.
- Do not upload author-identifying notes, receipts, or local handoff
  files as supplementary material.

This file is generated by `scripts/build_iclr_openreview_packet.py`.
