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

Abstract words: 238

Ethics statement:

This work uses standard public benchmark datasets and does not introduce human subjects data, private personal data, surveillance data, or safety-critical deployment claims. The main risk is scientific overclaiming, which is mitigated by scoped claims, explicit limitations, and reproducible artifacts.

LLM usage disclosure:

LLM-based coding and writing assistants were used for audit/runbook scripts, reproducibility documentation, stale-claim checks, and manuscript/code-edit suggestions; they were not authors or sources of scientific evidence, and all final claims, references, code, and text were human-reviewed.

Abstract:

The lottery ticket hypothesis suggests that dense neural networks contain sparse subnetworks that can be trained in isolation when rewound to their original initialization. A tempting Bayesian interpretation is that these tickets correspond to posterior modes, or to posterior-basin supports. We turn this interpretation into a pre-specified, falsifiable test: posterior-induced masks must match IMP tickets better than local magnitude, dense-trajectory, and pruning-process controls, not merely better than uniform random masks. Across five-seed MNIST and Fashion-MNIST sparsity sweeps and a CIFAR-10 ResNet-20 epoch-1 rewind setting, twelve posterior approximations---SGLD, SGHMC, cyclical SGLD, SWAG, the Laplace family up to joint-group full covariance, and subspace HMC---fail this stronger criterion. Posterior supports often beat random masks, but they remain tied to chain-start magnitude, dominated by dense magnitude, or closer to rewind controls than to IMP. Support-equivalence is graded rather than binary: only a rank-128 Hessian-plus-diagonal Laplace crosses the mask-overlap threshold, and even it fails the layer-sparsity and basin-count gates, so a posterior account survives on one axis at one fidelity. We then give a positive account of what winning tickets are: trajectory and pruning-process objects. Dense-trajectory magnitude explains most of the fixed-mask training gap and a process-selected IMP-only residual explains the rest, with an extensive battery of process controls failing to substitute for it. This account is consistent with axial-subspace views of IMP and inconsistent with a posterior-mode view. Exact dense full-network full-covariance CIFAR posterior baselines remain an open limitation.

## Upload Files

| Role | Path | Exists | Bytes | SHA256 | Pages |
| --- | --- | ---: | ---: | --- | ---: |
| primary_iclr_submission_pdf | `paper/iclr_submission.pdf` | True | 263029 | `6e45581ead217996a5a9893c91a7c68243d1fcc8e71fe52c6e56a7430a340703` | 12 |
| main_only_submission_pdf | `paper/main_submission.pdf` | True | 320599 | `814a982a9e58d71248eabdf2a3532e87b2985569f79bb606564770ab7a7a540f` |  |
| appendix_inclusive_reference_pdf | `paper/main.pdf` | True | 415361 | `374e28e23c49df59f8a2398447ea8a720ef376128842a3fb958420a44a6ef178` |  |
| paper_source_tex | `paper/main.tex` | True | 52312 | `55a12edc5427b5704ed3398137ca99c45947fc4956040093595338848176c486` |  |
| bibliography_source_bib | `paper/refs.bib` | True | 5639 | `2ca52c6d19659b7397109579dabfa21fa5536a83b80d6d8f907a15342f82fc1e` |  |
| optional_supplementary_artifact_archive | `dist/lottery_artifact_public_release_2026-05-06.tar.gz` | True | 372494867 | `not-recorded` |  |

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
