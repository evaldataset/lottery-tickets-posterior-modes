PYTHON ?= .venv/bin/python
CONTAINER_IMAGE ?= lottery-artifact:2026-05-06
GPU_CONTAINER_IMAGE ?= lottery-training-gpu:2026-05-06
VALIDATION_BN_ENTRY ?= locked_final_test_sgld_full_cifar

.PHONY: check ci-check source-repository-check unit-smoke-tests stats claim-ledger mode-ticket-alignment-audit mask-artifact-posthoc-audit full-mask-artifact-posthoc-audit full-channel-permutation-audit exhaustive-channel-feasibility-audit direct-mode-ticket-seed-audit batchnorm-policy-audit validation-test-policy-audit validation-bn-rerun-plan remaining-experiment-queue remaining-experiment-preflight remaining-experiment-preflight-live validation-bn-rerun-preflight validation-bn-rerun-entry locked-final-test-preflight locked-final-test-run locked-final-test-protocol-audit validation-bn-smoke-audit reference-integrity-audit manuscript-originality-audit formal-plagiarism-screening-runbook formal-plagiarism-screening-receipt-audit formal-plagiarism-screening-strict ethics-statement-audit llm-usage-disclosure-audit iclr-policy-watch-audit iclr-policy-watch-live iclr-openreview-packet iclr-human-confirmation-template iclr-human-confirmation-receipt-audit iclr-human-confirmation-strict venue-strategy-matrix venue-source-probe-live proposal-to-artifact-audit top-conference-completion-audit open-blocker-claim-scope-audit digits-fullnet-laplace-summary fake-resnet-fullnet-laplace-summary linear-connectivity-audit posterior-covariance-robustness-audit familywise-null-audit tost-equivalence-audit gw-mask-metric-audit topk-tracking-bound-audit paper-asset-freshness-audit paper-pdf-freshness-audit tmlr-packet-freshness-audit verify-readonly reviewer-objection-matrix paper-shape-audit submission-pdf-audit venue-submission-audit iclr-submission-readiness external-validation-claim-audit mode-ticket-artifact-budget release-anonymization-audit release-archive release-archive-smoke public-repository-snapshot external-validation-receipt-template external-validation-readiness external-validation-strict reproduce-minimal verify env-check gpu-env-check local-gpu-container-validation external-gpu-container-receipt release-manifest figures paper paper-submission paper-neurips paper-iclr paper-check paper-submission-check paper-neurips-check paper-iclr-check paper-existing paper-existing-submission paper-existing-neurips paper-existing-iclr paper-existing-check paper-existing-submission-check paper-existing-neurips-check paper-existing-iclr-check container-build container-check gpu-container-build gpu-container-env-check clean

check:
	$(PYTHON) -m py_compile src/lottery/*.py scripts/*.py
	$(PYTHON) scripts/run_unit_smoke_tests.py
	$(PYTHON) scripts/check_environment_lock.py
	$(PYTHON) scripts/audit_full_covariance_feasibility.py
	$(PYTHON) scripts/build_paper_stats.py
	$(PYTHON) scripts/build_paper_figures.py
	$(PYTHON) scripts/audit_paper_asset_freshness.py
	$(PYTHON) scripts/audit_mode_ticket_alignment_artifacts.py
	$(PYTHON) scripts/audit_mask_artifact_posthoc_matching.py
	$(PYTHON) scripts/audit_mask_artifact_posthoc_matching.py --artifact runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3/20260506_230706/mask_artifacts.npz --out-json runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.json --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.md --max-channel-pair-count 1
	$(PYTHON) scripts/audit_full_data_channel_permutation_matching.py
	$(PYTHON) scripts/audit_exhaustive_channel_permutation_feasibility.py
	$(PYTHON) scripts/audit_direct_mode_ticket_seed_level_artifacts.py
	$(PYTHON) scripts/audit_batchnorm_posterior_policy.py
	$(PYTHON) scripts/audit_validation_test_usage_policy.py
	$(PYTHON) scripts/build_validation_bn_rerun_plan.py
	$(PYTHON) scripts/build_remaining_experiment_queue.py
	$(PYTHON) scripts/audit_remaining_experiment_preflight.py
	$(PYTHON) scripts/audit_locked_final_test_protocol.py
	$(PYTHON) scripts/audit_validation_bn_smoke.py
	$(PYTHON) scripts/audit_reference_integrity.py
	$(PYTHON) scripts/audit_manuscript_originality.py
	$(PYTHON) scripts/build_formal_plagiarism_screening_runbook.py
	$(PYTHON) scripts/audit_formal_plagiarism_screening_receipt.py
	$(PYTHON) scripts/audit_ethics_statement.py
	$(PYTHON) scripts/audit_llm_usage_disclosure.py
	$(PYTHON) scripts/summarize_fullnet_laplace_probe.py --run-root runs/digits_fullnet_laplace_tiny_r2_p0p3 --out-csv runs/digits_fullnet_laplace_tiny_r2_p0p3_summary.csv --out-md docs/digits_fullnet_laplace_tiny_r2_p0p3.md
	$(PYTHON) scripts/summarize_fullnet_laplace_probe.py --run-root runs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke --out-csv runs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke_summary.csv --out-md docs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke.md
	$(PYTHON) scripts/audit_linear_connectivity_barriers.py
	$(PYTHON) scripts/audit_posterior_covariance_robustness.py
	$(PYTHON) scripts/audit_familywise_null.py
	$(PYTHON) scripts/run_tost_equivalence_reanalysis.py
	$(PYTHON) scripts/audit_gw_mask_metric.py
	$(PYTHON) scripts/audit_topk_tracking_bound.py
	$(PYTHON) scripts/build_reviewer_objection_matrix.py
	$(PYTHON) scripts/audit_paper_submission_shape.py
	$(PYTHON) scripts/audit_submission_pdf_shape.py
	$(PYTHON) scripts/build_iclr_policy_watch_audit.py
	$(PYTHON) scripts/build_iclr_openreview_packet.py
	$(PYTHON) scripts/build_iclr_human_confirmation_template.py
	$(PYTHON) scripts/audit_iclr_human_confirmation_receipt.py
	$(PYTHON) scripts/audit_iclr_submission_readiness.py
	$(PYTHON) scripts/build_venue_strategy_matrix.py
	$(PYTHON) scripts/build_proposal_to_artifact_audit.py
	$(PYTHON) scripts/audit_mode_ticket_artifact_storage_budget.py
	$(PYTHON) scripts/build_paper_claim_ledger.py
	$(PYTHON) scripts/audit_external_validation_readiness.py
	$(PYTHON) scripts/audit_venue_submission_compliance.py
	$(PYTHON) scripts/build_submission_handoff.py
	$(PYTHON) scripts/audit_open_blocker_claim_scope.py
	$(PYTHON) scripts/build_release_manifest.py
	$(PYTHON) scripts/audit_release_anonymization.py
	$(PYTHON) scripts/build_public_release_archive.py
	$(PYTHON) scripts/smoke_public_release_archive.py
	$(PYTHON) scripts/stage_public_repository_snapshot.py
	$(PYTHON) scripts/smoke_public_repository_snapshot.py
	$(PYTHON) scripts/audit_external_validation_readiness.py
	$(PYTHON) scripts/build_external_validation_receipt_template.py
	$(PYTHON) scripts/build_external_validation_runbook.py
	$(PYTHON) scripts/audit_venue_submission_compliance.py
	$(PYTHON) scripts/build_submission_handoff.py
	$(PYTHON) scripts/audit_external_validation_claims.py
	$(PYTHON) scripts/build_top_conference_completion_audit.py
	$(PYTHON) scripts/verify_research_artifacts.py

ci-check:
	$(PYTHON) -m py_compile src/lottery/*.py scripts/*.py
	$(PYTHON) scripts/run_unit_smoke_tests.py
	$(PYTHON) scripts/build_paper_stats.py
	$(PYTHON) scripts/build_paper_figures.py
	$(PYTHON) scripts/audit_paper_asset_freshness.py
	$(PYTHON) scripts/audit_mode_ticket_alignment_artifacts.py
	$(PYTHON) scripts/audit_mask_artifact_posthoc_matching.py
	$(PYTHON) scripts/audit_mask_artifact_posthoc_matching.py --artifact runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3/20260506_230706/mask_artifacts.npz --out-json runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.json --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.md --max-channel-pair-count 1
	$(PYTHON) scripts/audit_full_data_channel_permutation_matching.py
	$(PYTHON) scripts/audit_exhaustive_channel_permutation_feasibility.py
	$(PYTHON) scripts/audit_direct_mode_ticket_seed_level_artifacts.py
	$(PYTHON) scripts/audit_batchnorm_posterior_policy.py
	$(PYTHON) scripts/audit_validation_test_usage_policy.py
	$(PYTHON) scripts/build_validation_bn_rerun_plan.py
	$(PYTHON) scripts/build_remaining_experiment_queue.py
	$(PYTHON) scripts/audit_remaining_experiment_preflight.py
	$(PYTHON) scripts/audit_locked_final_test_protocol.py
	$(PYTHON) scripts/audit_validation_bn_smoke.py
	$(PYTHON) scripts/audit_reference_integrity.py
	$(PYTHON) scripts/audit_manuscript_originality.py
	$(PYTHON) scripts/build_formal_plagiarism_screening_runbook.py
	$(PYTHON) scripts/audit_formal_plagiarism_screening_receipt.py
	$(PYTHON) scripts/audit_ethics_statement.py
	$(PYTHON) scripts/audit_llm_usage_disclosure.py
	$(PYTHON) scripts/summarize_fullnet_laplace_probe.py --run-root runs/digits_fullnet_laplace_tiny_r2_p0p3 --out-csv runs/digits_fullnet_laplace_tiny_r2_p0p3_summary.csv --out-md docs/digits_fullnet_laplace_tiny_r2_p0p3.md
	$(PYTHON) scripts/summarize_fullnet_laplace_probe.py --run-root runs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke --out-csv runs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke_summary.csv --out-md docs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke.md
	$(PYTHON) scripts/audit_linear_connectivity_barriers.py
	$(PYTHON) scripts/audit_posterior_covariance_robustness.py
	$(PYTHON) scripts/audit_familywise_null.py
	$(PYTHON) scripts/run_tost_equivalence_reanalysis.py
	$(PYTHON) scripts/audit_gw_mask_metric.py
	$(PYTHON) scripts/audit_topk_tracking_bound.py
	$(PYTHON) scripts/build_reviewer_objection_matrix.py
	$(PYTHON) scripts/audit_paper_submission_shape.py
	$(PYTHON) scripts/audit_submission_pdf_shape.py
	$(PYTHON) scripts/build_iclr_policy_watch_audit.py
	$(PYTHON) scripts/build_iclr_openreview_packet.py
	$(PYTHON) scripts/build_iclr_human_confirmation_template.py
	$(PYTHON) scripts/audit_iclr_human_confirmation_receipt.py
	$(PYTHON) scripts/audit_iclr_submission_readiness.py
	$(PYTHON) scripts/build_venue_strategy_matrix.py
	$(PYTHON) scripts/build_proposal_to_artifact_audit.py
	$(PYTHON) scripts/audit_mode_ticket_artifact_storage_budget.py
	$(PYTHON) scripts/build_paper_claim_ledger.py
	$(PYTHON) scripts/audit_external_validation_readiness.py
	$(PYTHON) scripts/audit_venue_submission_compliance.py
	$(PYTHON) scripts/build_submission_handoff.py
	$(PYTHON) scripts/audit_open_blocker_claim_scope.py
	$(PYTHON) scripts/build_release_manifest.py
	$(PYTHON) scripts/audit_release_anonymization.py
	$(PYTHON) scripts/build_public_release_archive.py
	$(PYTHON) scripts/smoke_public_release_archive.py
	$(PYTHON) scripts/stage_public_repository_snapshot.py
	$(PYTHON) scripts/smoke_public_repository_snapshot.py
	$(PYTHON) scripts/audit_external_validation_readiness.py
	$(PYTHON) scripts/build_external_validation_receipt_template.py
	$(PYTHON) scripts/build_external_validation_runbook.py
	$(PYTHON) scripts/audit_venue_submission_compliance.py
	$(PYTHON) scripts/build_submission_handoff.py
	$(PYTHON) scripts/audit_external_validation_claims.py
	$(PYTHON) scripts/build_top_conference_completion_audit.py
	$(PYTHON) scripts/verify_research_artifacts.py --release-package-mode

source-repository-check:
	$(PYTHON) -m py_compile src/lottery/*.py scripts/*.py
	$(PYTHON) scripts/run_unit_smoke_tests.py
	$(PYTHON) scripts/verify_source_repository_snapshot.py
	$(MAKE) paper-existing-check PYTHON=$(PYTHON)

unit-smoke-tests:
	$(PYTHON) scripts/run_unit_smoke_tests.py

stats:
	$(PYTHON) scripts/build_paper_stats.py

claim-ledger: stats mode-ticket-alignment-audit mask-artifact-posthoc-audit full-mask-artifact-posthoc-audit full-channel-permutation-audit exhaustive-channel-feasibility-audit direct-mode-ticket-seed-audit batchnorm-policy-audit validation-test-policy-audit validation-bn-rerun-plan locked-final-test-protocol-audit validation-bn-smoke-audit reference-integrity-audit manuscript-originality-audit formal-plagiarism-screening-runbook formal-plagiarism-screening-receipt-audit ethics-statement-audit llm-usage-disclosure-audit digits-fullnet-laplace-summary fake-resnet-fullnet-laplace-summary linear-connectivity-audit posterior-covariance-robustness-audit mode-ticket-artifact-budget
	$(PYTHON) scripts/build_paper_claim_ledger.py

mode-ticket-alignment-audit: stats
	$(PYTHON) scripts/audit_mode_ticket_alignment_artifacts.py

mask-artifact-posthoc-audit:
	$(PYTHON) scripts/audit_mask_artifact_posthoc_matching.py

full-mask-artifact-posthoc-audit:
	$(PYTHON) scripts/audit_mask_artifact_posthoc_matching.py --artifact runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3/20260506_230706/mask_artifacts.npz --out-json runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.json --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.md --max-channel-pair-count 1

full-channel-permutation-audit:
	$(PYTHON) scripts/audit_full_data_channel_permutation_matching.py

exhaustive-channel-feasibility-audit:
	$(PYTHON) scripts/audit_exhaustive_channel_permutation_feasibility.py

direct-mode-ticket-seed-audit: stats
	$(PYTHON) scripts/audit_direct_mode_ticket_seed_level_artifacts.py

batchnorm-policy-audit:
	$(PYTHON) scripts/audit_batchnorm_posterior_policy.py

validation-test-policy-audit:
	$(PYTHON) scripts/audit_validation_test_usage_policy.py

validation-bn-rerun-plan:
	$(PYTHON) scripts/build_validation_bn_rerun_plan.py

remaining-experiment-queue: validation-bn-rerun-plan locked-final-test-protocol-audit
	$(PYTHON) scripts/build_remaining_experiment_queue.py

remaining-experiment-preflight: remaining-experiment-queue
	$(PYTHON) scripts/audit_remaining_experiment_preflight.py

remaining-experiment-preflight-live: remaining-experiment-queue
	$(PYTHON) scripts/audit_remaining_experiment_preflight.py --live-gpu-probe

validation-bn-rerun-preflight:
	$(PYTHON) scripts/run_validation_bn_rerun_plan_entry.py --entry $(VALIDATION_BN_ENTRY) --python $(PYTHON) --preflight-only

validation-bn-rerun-entry:
	$(PYTHON) scripts/run_validation_bn_rerun_plan_entry.py --entry $(VALIDATION_BN_ENTRY) --python $(PYTHON)

locked-final-test-preflight:
	$(PYTHON) scripts/run_validation_bn_rerun_plan_entry.py --entry locked_final_test_sgld_full_cifar --python $(PYTHON) --preflight-only

locked-final-test-run:
	$(PYTHON) scripts/run_validation_bn_rerun_plan_entry.py --entry locked_final_test_sgld_full_cifar --python $(PYTHON)

locked-final-test-protocol-audit:
	$(PYTHON) scripts/audit_locked_final_test_protocol.py

validation-bn-smoke-audit:
	$(PYTHON) scripts/audit_validation_bn_smoke.py

reference-integrity-audit:
	$(PYTHON) scripts/audit_reference_integrity.py

manuscript-originality-audit:
	$(PYTHON) scripts/audit_manuscript_originality.py

formal-plagiarism-screening-runbook:
	$(PYTHON) scripts/build_formal_plagiarism_screening_runbook.py

formal-plagiarism-screening-receipt-audit: formal-plagiarism-screening-runbook
	$(PYTHON) scripts/audit_formal_plagiarism_screening_receipt.py

formal-plagiarism-screening-strict: formal-plagiarism-screening-runbook
	$(PYTHON) scripts/audit_formal_plagiarism_screening_receipt.py --strict

ethics-statement-audit:
	$(PYTHON) scripts/audit_ethics_statement.py

llm-usage-disclosure-audit:
	$(PYTHON) scripts/audit_llm_usage_disclosure.py

iclr-policy-watch-audit:
	$(PYTHON) scripts/build_iclr_policy_watch_audit.py

iclr-policy-watch-live:
	$(PYTHON) scripts/build_iclr_policy_watch_audit.py --live-probe

iclr-openreview-packet:
	$(PYTHON) scripts/build_iclr_openreview_packet.py

iclr-human-confirmation-template:
	$(PYTHON) scripts/build_iclr_human_confirmation_template.py

iclr-human-confirmation-receipt-audit: iclr-human-confirmation-template
	$(PYTHON) scripts/audit_iclr_human_confirmation_receipt.py

iclr-human-confirmation-strict: iclr-human-confirmation-template
	$(PYTHON) scripts/audit_iclr_human_confirmation_receipt.py --strict

digits-fullnet-laplace-summary:
	$(PYTHON) scripts/summarize_fullnet_laplace_probe.py --run-root runs/digits_fullnet_laplace_tiny_r2_p0p3 --out-csv runs/digits_fullnet_laplace_tiny_r2_p0p3_summary.csv --out-md docs/digits_fullnet_laplace_tiny_r2_p0p3.md

fake-resnet-fullnet-laplace-summary:
	$(PYTHON) scripts/summarize_fullnet_laplace_probe.py --run-root runs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke --out-csv runs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke_summary.csv --out-md docs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke.md

linear-connectivity-audit:
	$(PYTHON) scripts/audit_linear_connectivity_barriers.py

posterior-covariance-robustness-audit:
	$(PYTHON) scripts/audit_posterior_covariance_robustness.py

familywise-null-audit:
	$(PYTHON) scripts/audit_familywise_null.py

tost-equivalence-audit:
	$(PYTHON) scripts/run_tost_equivalence_reanalysis.py

gw-mask-metric-audit:
	$(PYTHON) scripts/audit_gw_mask_metric.py

topk-tracking-bound-audit:
	$(PYTHON) scripts/audit_topk_tracking_bound.py

reviewer-objection-matrix: stats full-channel-permutation-audit exhaustive-channel-feasibility-audit linear-connectivity-audit posterior-covariance-robustness-audit
	$(PYTHON) scripts/audit_full_covariance_feasibility.py
	$(PYTHON) scripts/build_reviewer_objection_matrix.py

paper-shape-audit: reviewer-objection-matrix
	$(PYTHON) scripts/audit_paper_submission_shape.py

submission-pdf-audit:
	$(PYTHON) scripts/audit_submission_pdf_shape.py

venue-submission-audit:
	$(PYTHON) scripts/audit_venue_submission_compliance.py

iclr-submission-readiness: iclr-policy-watch-audit iclr-openreview-packet iclr-human-confirmation-receipt-audit formal-plagiarism-screening-receipt-audit
	$(PYTHON) scripts/audit_iclr_submission_readiness.py

venue-strategy-matrix: iclr-submission-readiness
	$(PYTHON) scripts/build_venue_strategy_matrix.py

venue-source-probe-live:
	$(PYTHON) scripts/build_venue_strategy_matrix.py --live-probe

proposal-to-artifact-audit: venue-strategy-matrix
	$(PYTHON) scripts/build_proposal_to_artifact_audit.py

top-conference-completion-audit: proposal-to-artifact-audit external-validation-readiness external-validation-claim-audit
	$(PYTHON) scripts/build_top_conference_completion_audit.py

open-blocker-claim-scope-audit: top-conference-completion-audit
	$(PYTHON) scripts/audit_open_blocker_claim_scope.py

external-validation-claim-audit:
	$(PYTHON) scripts/audit_external_validation_claims.py

mode-ticket-artifact-budget:
	$(PYTHON) scripts/audit_mode_ticket_artifact_storage_budget.py

env-check:
	$(PYTHON) scripts/check_environment_lock.py

gpu-env-check:
	$(PYTHON) scripts/check_gpu_training_environment.py

local-gpu-container-validation:
	$(PYTHON) scripts/build_local_gpu_container_validation.py

external-gpu-container-receipt:
	$(PYTHON) scripts/build_external_gpu_container_receipt.py

release-manifest:
	$(PYTHON) scripts/build_release_manifest.py

release-anonymization-audit: release-manifest
	$(PYTHON) scripts/audit_release_anonymization.py

release-archive: release-anonymization-audit
	$(PYTHON) scripts/build_public_release_archive.py

release-archive-smoke: release-archive
	$(PYTHON) scripts/smoke_public_release_archive.py

public-repository-snapshot: release-archive-smoke
	$(PYTHON) scripts/stage_public_repository_snapshot.py
	$(PYTHON) scripts/smoke_public_repository_snapshot.py

external-validation-receipt-template: public-repository-snapshot
	$(PYTHON) scripts/audit_external_validation_readiness.py
	$(PYTHON) scripts/build_external_validation_receipt_template.py

external-validation-readiness: external-validation-receipt-template venue-strategy-matrix
	$(PYTHON) scripts/build_external_validation_runbook.py
	$(PYTHON) scripts/build_submission_handoff.py
	$(PYTHON) scripts/audit_external_validation_claims.py

external-validation-strict: public-repository-snapshot
	$(PYTHON) scripts/audit_external_validation_readiness.py --strict

reproduce-minimal:
	$(MAKE) figures PYTHON=$(PYTHON)
	$(MAKE) paper-existing-check PYTHON=$(PYTHON)
	$(MAKE) check PYTHON=$(PYTHON)

verify: stats paper-asset-freshness-audit paper-pdf-freshness-audit tmlr-packet-freshness-audit claim-ledger mode-ticket-alignment-audit mask-artifact-posthoc-audit reviewer-objection-matrix paper-shape-audit submission-pdf-audit venue-submission-audit iclr-submission-readiness venue-strategy-matrix proposal-to-artifact-audit external-validation-claim-audit mode-ticket-artifact-budget external-validation-readiness open-blocker-claim-scope-audit
	$(PYTHON) scripts/verify_research_artifacts.py

figures: stats
	$(PYTHON) scripts/build_paper_figures.py

paper-asset-freshness-audit: figures
	$(PYTHON) scripts/audit_paper_asset_freshness.py

paper-pdf-freshness-audit:
	$(PYTHON) scripts/audit_paper_pdf_freshness.py

tmlr-packet-freshness-audit:
	$(PYTHON) scripts/audit_tmlr_packet_freshness.py

verify-readonly:
	# Read-only consistency gate. Unlike `make verify` or `make check`, this
	# target does NOT regenerate any artifact; it only re-runs the
	# verify_research_artifacts.py end-gate over whatever is already on
	# disk. A reviewer can run this safely against a pristine working tree.
	$(PYTHON) scripts/verify_research_artifacts.py

paper: figures
	cd paper && pdflatex -interaction=nonstopmode main
	cd paper && bibtex main
	cd paper && pdflatex -interaction=nonstopmode main
	cd paper && pdflatex -interaction=nonstopmode main

paper-submission: figures
	cd paper && pdflatex -interaction=nonstopmode -jobname=main_submission '\def\LOTTERYMAINONLY{1}\input{main.tex}'
	cd paper && bibtex main_submission
	cd paper && pdflatex -interaction=nonstopmode -jobname=main_submission '\def\LOTTERYMAINONLY{1}\input{main.tex}'
	cd paper && pdflatex -interaction=nonstopmode -jobname=main_submission '\def\LOTTERYMAINONLY{1}\input{main.tex}'

paper-neurips: figures
	cd paper && pdflatex -interaction=nonstopmode -jobname=neurips_submission '\def\LOTTERYNEURIPS{1}\input{main.tex}'
	cd paper && bibtex neurips_submission
	cd paper && pdflatex -interaction=nonstopmode -jobname=neurips_submission '\def\LOTTERYNEURIPS{1}\input{main.tex}'
	cd paper && pdflatex -interaction=nonstopmode -jobname=neurips_submission '\def\LOTTERYNEURIPS{1}\input{main.tex}'

paper-iclr: figures
	cd paper && pdflatex -interaction=nonstopmode -jobname=iclr_submission '\def\LOTTERYICLR{1}\def\LOTTERYMAINONLY{1}\input{main.tex}'
	cd paper && bibtex iclr_submission
	cd paper && pdflatex -interaction=nonstopmode -jobname=iclr_submission '\def\LOTTERYICLR{1}\def\LOTTERYMAINONLY{1}\input{main.tex}'
	cd paper && pdflatex -interaction=nonstopmode -jobname=iclr_submission '\def\LOTTERYICLR{1}\def\LOTTERYMAINONLY{1}\input{main.tex}'

paper-check: paper paper-submission-check paper-neurips-check paper-iclr-check
	@cd paper && if grep -nE "Warning|Undefined|undefined|Overfull|Underfull|Rerun|Missing \\$$|Extra \\}" main.log | grep -v "Package: rerunfilecheck"; then exit 1; fi

paper-submission-check: paper-submission
	@cd paper && if grep -nE "Warning|Undefined|undefined|Overfull|Underfull|Rerun|Missing \\$$|Extra \\}" main_submission.log | grep -v "Package: rerunfilecheck"; then exit 1; fi

paper-neurips-check: paper-neurips
	@cd paper && if grep -nE "Warning|Undefined|undefined|Overfull|Rerun|Missing \\$$|Extra \\}" neurips_submission.log | grep -v "Package: rerunfilecheck"; then exit 1; fi

paper-iclr-check: paper-iclr
	@cd paper && if grep -nE "Warning|Undefined|undefined|Overfull|Rerun|Missing \\$$|Extra \\}" iclr_submission.log | grep -v "Package: rerunfilecheck"; then exit 1; fi

paper-existing:
	cd paper && pdflatex -interaction=nonstopmode main
	cd paper && bibtex main
	cd paper && pdflatex -interaction=nonstopmode main
	cd paper && pdflatex -interaction=nonstopmode main

paper-existing-submission:
	cd paper && pdflatex -interaction=nonstopmode -jobname=main_submission '\def\LOTTERYMAINONLY{1}\input{main.tex}'
	cd paper && bibtex main_submission
	cd paper && pdflatex -interaction=nonstopmode -jobname=main_submission '\def\LOTTERYMAINONLY{1}\input{main.tex}'
	cd paper && pdflatex -interaction=nonstopmode -jobname=main_submission '\def\LOTTERYMAINONLY{1}\input{main.tex}'

paper-existing-neurips:
	cd paper && pdflatex -interaction=nonstopmode -jobname=neurips_submission '\def\LOTTERYNEURIPS{1}\input{main.tex}'
	cd paper && bibtex neurips_submission
	cd paper && pdflatex -interaction=nonstopmode -jobname=neurips_submission '\def\LOTTERYNEURIPS{1}\input{main.tex}'
	cd paper && pdflatex -interaction=nonstopmode -jobname=neurips_submission '\def\LOTTERYNEURIPS{1}\input{main.tex}'

paper-existing-iclr:
	cd paper && pdflatex -interaction=nonstopmode -jobname=iclr_submission '\def\LOTTERYICLR{1}\def\LOTTERYMAINONLY{1}\input{main.tex}'
	cd paper && bibtex iclr_submission
	cd paper && pdflatex -interaction=nonstopmode -jobname=iclr_submission '\def\LOTTERYICLR{1}\def\LOTTERYMAINONLY{1}\input{main.tex}'
	cd paper && pdflatex -interaction=nonstopmode -jobname=iclr_submission '\def\LOTTERYICLR{1}\def\LOTTERYMAINONLY{1}\input{main.tex}'

paper-existing-check: paper-existing paper-existing-submission-check paper-existing-neurips-check paper-existing-iclr-check
	@cd paper && if grep -nE "Warning|Undefined|undefined|Overfull|Underfull|Rerun|Missing \\$$|Extra \\}" main.log | grep -v "Package: rerunfilecheck"; then exit 1; fi

paper-existing-submission-check: paper-existing-submission
	@cd paper && if grep -nE "Warning|Undefined|undefined|Overfull|Underfull|Rerun|Missing \\$$|Extra \\}" main_submission.log | grep -v "Package: rerunfilecheck"; then exit 1; fi

paper-existing-neurips-check: paper-existing-neurips
	@cd paper && if grep -nE "Warning|Undefined|undefined|Overfull|Rerun|Missing \\$$|Extra \\}" neurips_submission.log | grep -v "Package: rerunfilecheck"; then exit 1; fi

paper-existing-iclr-check: paper-existing-iclr
	@cd paper && if grep -nE "Warning|Undefined|undefined|Overfull|Rerun|Missing \\$$|Extra \\}" iclr_submission.log | grep -v "Package: rerunfilecheck"; then exit 1; fi

container-build:
	docker build -t $(CONTAINER_IMAGE) .

container-check:
	docker run --rm $(CONTAINER_IMAGE)

gpu-container-build:
	docker build -f Dockerfile.gpu -t $(GPU_CONTAINER_IMAGE) .

gpu-container-env-check:
	$(PYTHON) scripts/run_gpu_container_env_check.py --image $(GPU_CONTAINER_IMAGE)

clean:
	rm -rf src/lottery/__pycache__ scripts/__pycache__
	rm -f paper/main.aux paper/main.bbl paper/main.blg paper/main.log paper/main.out
	rm -f paper/main_submission.aux paper/main_submission.bbl paper/main_submission.blg paper/main_submission.log paper/main_submission.out
	rm -f paper/neurips_submission.aux paper/neurips_submission.bbl paper/neurips_submission.blg paper/neurips_submission.log paper/neurips_submission.out
	rm -f paper/iclr_submission.aux paper/iclr_submission.bbl paper/iclr_submission.blg paper/iclr_submission.log paper/iclr_submission.out
