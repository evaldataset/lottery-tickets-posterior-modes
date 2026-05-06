# Remaining Experiment Queue

This generated queue converts the remaining scientific-protocol blockers
into exact rerun commands, expected evidence, and paper actions. It is
an execution plan, not completed experiment evidence.

Queue status: ready.
Plan JSON: `runs/validation_bn_rerun_plan.json`.
Top audit JSON: `runs/top_conference_completion_audit.json`.

## Group Summary

| Category | Entries | Observed | Open blockers |
| --- | ---: | ---: | --- |
| locked_final_test | 1 | 1 | none |
| batchnorm_policy_ablation | 6 | 6 | none |
| saved_artifact_seed_level_reruns | 3 | 3 | none |

## Queue Entries

### locked_final_test_sgld_full_cifar

- Category: `locked_final_test`
- Priority: `P0`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `sampler_default`
- Saves mask artifacts: `False`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry locked_final_test_sgld_full_cifar --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry locked_final_test_sgld_full_cifar --python .venv/bin/python
```

Acceptance criteria:
- metrics.json exists under the locked run root
- config.evaluation_split is test
- selection_protocol links to the validation-selected run and summary
- summary CSV/MD contains the expected three comparison rows
- scripts/audit_locked_final_test_protocol.py has no risk flags

Paper action:

- Use the locked test row as the final unbiased SGLD estimate only after the validation-selected source and locked summary artifacts pass.

### bn_freeze_sgld_full_cifar

- Category: `batchnorm_policy_ablation`
- Priority: `P1`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `freeze`
- Saves mask artifacts: `False`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_freeze_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_freeze_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_freeze_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_freeze_sgld_full_cifar --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_freeze_sgld_full_cifar --python .venv/bin/python
```

Acceptance criteria:
- all six SGLD/cSGLD BN policy rows have fresh metrics
- summaries are regenerated from those run roots
- validation_bn_rerun_plan marks the rows observed
- paper limitations reflect any policy-sensitive result

Paper action:

- If freeze/recalibrate/dense-buffer rows agree with the default, move the BatchNorm caveat to a sensitivity appendix; otherwise scope CIFAR posterior conclusions to the observed BN policy.

### bn_recalibrate_sgld_full_cifar

- Category: `batchnorm_policy_ablation`
- Priority: `P1`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `recalibrate`
- Saves mask artifacts: `False`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_recalibrate_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_recalibrate_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_recalibrate_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_recalibrate_sgld_full_cifar --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_recalibrate_sgld_full_cifar --python .venv/bin/python
```

Acceptance criteria:
- all six SGLD/cSGLD BN policy rows have fresh metrics
- summaries are regenerated from those run roots
- validation_bn_rerun_plan marks the rows observed
- paper limitations reflect any policy-sensitive result

Paper action:

- If freeze/recalibrate/dense-buffer rows agree with the default, move the BatchNorm caveat to a sensitivity appendix; otherwise scope CIFAR posterior conclusions to the observed BN policy.

### bn_dense_buffers_sgld_full_cifar

- Category: `batchnorm_policy_ablation`
- Priority: `P1`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `dense_buffers`
- Saves mask artifacts: `False`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_dense_buffers_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_dense_buffers_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_dense_buffers_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_dense_buffers_sgld_full_cifar --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_dense_buffers_sgld_full_cifar --python .venv/bin/python
```

Acceptance criteria:
- all six SGLD/cSGLD BN policy rows have fresh metrics
- summaries are regenerated from those run roots
- validation_bn_rerun_plan marks the rows observed
- paper limitations reflect any policy-sensitive result

Paper action:

- If freeze/recalibrate/dense-buffer rows agree with the default, move the BatchNorm caveat to a sensitivity appendix; otherwise scope CIFAR posterior conclusions to the observed BN policy.

### bn_freeze_csgld_full_cifar

- Category: `batchnorm_policy_ablation`
- Priority: `P1`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `freeze`
- Saves mask artifacts: `False`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_freeze_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_freeze_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_freeze_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_freeze_csgld_full_cifar --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_freeze_csgld_full_cifar --python .venv/bin/python
```

Acceptance criteria:
- all six SGLD/cSGLD BN policy rows have fresh metrics
- summaries are regenerated from those run roots
- validation_bn_rerun_plan marks the rows observed
- paper limitations reflect any policy-sensitive result

Paper action:

- If freeze/recalibrate/dense-buffer rows agree with the default, move the BatchNorm caveat to a sensitivity appendix; otherwise scope CIFAR posterior conclusions to the observed BN policy.

### bn_recalibrate_csgld_full_cifar

- Category: `batchnorm_policy_ablation`
- Priority: `P1`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `recalibrate`
- Saves mask artifacts: `False`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_recalibrate_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_recalibrate_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_recalibrate_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_recalibrate_csgld_full_cifar --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_recalibrate_csgld_full_cifar --python .venv/bin/python
```

Acceptance criteria:
- all six SGLD/cSGLD BN policy rows have fresh metrics
- summaries are regenerated from those run roots
- validation_bn_rerun_plan marks the rows observed
- paper limitations reflect any policy-sensitive result

Paper action:

- If freeze/recalibrate/dense-buffer rows agree with the default, move the BatchNorm caveat to a sensitivity appendix; otherwise scope CIFAR posterior conclusions to the observed BN policy.

### bn_dense_buffers_csgld_full_cifar

- Category: `batchnorm_policy_ablation`
- Priority: `P1`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `dense_buffers`
- Saves mask artifacts: `False`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_dense_buffers_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_dense_buffers_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_dense_buffers_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_dense_buffers_csgld_full_cifar --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry bn_dense_buffers_csgld_full_cifar --python .venv/bin/python
```

Acceptance criteria:
- all six SGLD/cSGLD BN policy rows have fresh metrics
- summaries are regenerated from those run roots
- validation_bn_rerun_plan marks the rows observed
- paper limitations reflect any policy-sensitive result

Paper action:

- If freeze/recalibrate/dense-buffer rows agree with the default, move the BatchNorm caveat to a sensitivity appendix; otherwise scope CIFAR posterior conclusions to the observed BN policy.

### saved_artifacts_csgld_multichain

- Category: `saved_artifact_seed_level_reruns`
- Priority: `P1`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `sampler_default`
- Saves mask artifacts: `True`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_multichain_saved_artifacts_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_multichain_saved_artifacts_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_multichain_saved_artifacts_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry saved_artifacts_csgld_multichain --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry saved_artifacts_csgld_multichain --python .venv/bin/python
```

Acceptance criteria:
- each row writes mask_artifacts.npz
- summaries are regenerated from those run roots
- seed-level paired audit includes the new saved-artifact rows
- paper text no longer relies on pooled p-values for those rows

Paper action:

- Promote cSGLD/LowRank128/JointDiag direct rows from pooled sample-level diagnostics to seed-level evidence only after saved mask artifacts and paired seed-level audits exist.

### saved_artifacts_lowrank128

- Category: `saved_artifact_seed_level_reruns`
- Priority: `P1`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `sampler_default`
- Saves mask artifacts: `True`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_saved_artifacts_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_saved_artifacts_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_saved_artifacts_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry saved_artifacts_lowrank128 --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry saved_artifacts_lowrank128 --python .venv/bin/python
```

Acceptance criteria:
- each row writes mask_artifacts.npz
- summaries are regenerated from those run roots
- seed-level paired audit includes the new saved-artifact rows
- paper text no longer relies on pooled p-values for those rows

Paper action:

- Promote cSGLD/LowRank128/JointDiag direct rows from pooled sample-level diagnostics to seed-level evidence only after saved mask artifacts and paired seed-level audits exist.

### saved_artifacts_jointdiag

- Category: `saved_artifact_seed_level_reruns`
- Priority: `P1`
- Observed: `True`
- Evaluation split: `test`
- BatchNorm policy: `sampler_default`
- Saves mask artifacts: `True`
- Run root: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_saved_artifacts_r5_p0p3`
- Summary MD: `docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_saved_artifacts_r5_p0p3.md`
- Summary CSV: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_saved_artifacts_r5_p0p3_summary.csv`
- Blocking open flags: none

Preflight:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry saved_artifacts_jointdiag --python .venv/bin/python --preflight-only
```

Run wrapper:

```bash
.venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py --entry saved_artifacts_jointdiag --python .venv/bin/python
```

Acceptance criteria:
- each row writes mask_artifacts.npz
- summaries are regenerated from those run roots
- seed-level paired audit includes the new saved-artifact rows
- paper text no longer relies on pooled p-values for those rows

Paper action:

- Promote cSGLD/LowRank128/JointDiag direct rows from pooled sample-level diagnostics to seed-level evidence only after saved mask artifacts and paired seed-level audits exist.

## Post-Run Refresh

```bash
.venv/bin/python scripts/build_validation_bn_rerun_plan.py
.venv/bin/python scripts/audit_locked_final_test_protocol.py
.venv/bin/python scripts/audit_direct_mode_ticket_seed_level_artifacts.py
.venv/bin/python scripts/audit_batchnorm_posterior_policy.py
.venv/bin/python scripts/build_paper_claim_ledger.py
.venv/bin/python scripts/build_top_conference_completion_audit.py
.venv/bin/python scripts/verify_research_artifacts.py
```

## Risk Flags

- none

## Open Risk Flags

- none

This file is generated by `scripts/build_remaining_experiment_queue.py`.
