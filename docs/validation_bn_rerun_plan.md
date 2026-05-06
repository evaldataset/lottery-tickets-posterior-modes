# Validation and BatchNorm Rerun Plan

This generated plan fixes the commands needed to close the remaining
validation/test protocol, BatchNorm policy, and direct-row seed-level
artifact blockers. It is a command plan, not evidence that the GPU
reruns have completed.

Current status: ready.

## Summary

- Plan entries: 11
- Observed entries: 11
- Open risk flags: none

## Commands

### P0 validation_select_sgld_full_cifar

- Purpose: Select/report diagnostics on a held-out validation split before final test reporting.
- Criticism addressed: test-set peeking during direct mode/ticket row selection
- Evaluation split: `val`
- BN policy: `sampler_default`
- Saves mask/state artifacts: `False`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split val --posterior-sampler sgld --samples 10 --sgld-steps 200 --sgld-burn-in 50 --sgld-sample-every 10 --sgld-lr 1e-6 --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3_summary.csv
```

### P0 locked_final_test_sgld_full_cifar

- Purpose: Evaluate the locked SGLD direct row on the test split once after validation selection.
- Criticism addressed: unbiased final test estimate missing after validation selection
- Evaluation split: `test`
- BN policy: `sampler_default`
- Saves mask/state artifacts: `False`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler sgld --samples 10 --sgld-steps 200 --sgld-burn-in 50 --sgld-sample-every 10 --sgld-lr 1e-6 --selection-source-run runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3 --selection-source-summary docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3.md --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3_summary.csv
```

### P1 bn_freeze_sgld_full_cifar

- Purpose: Bound whether sgld direct failure is a BatchNorm-buffer artifact.
- Criticism addressed: posterior sampler implementation may drive the result through BN running buffers
- Evaluation split: `test`
- BN policy: `freeze`
- Saves mask/state artifacts: `False`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler sgld --samples 10 --sgld-steps 200 --sgld-burn-in 50 --sgld-sample-every 10 --sgld-lr 1e-6 --posterior-bn-policy freeze --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_freeze_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_freeze_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_freeze_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_freeze_r5_p0p3_summary.csv
```

### P1 bn_recalibrate_sgld_full_cifar

- Purpose: Bound whether sgld direct failure is a BatchNorm-buffer artifact.
- Criticism addressed: posterior sampler implementation may drive the result through BN running buffers
- Evaluation split: `test`
- BN policy: `recalibrate`
- Saves mask/state artifacts: `False`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler sgld --samples 10 --sgld-steps 200 --sgld-burn-in 50 --sgld-sample-every 10 --sgld-lr 1e-6 --posterior-bn-policy recalibrate --bn-recalibration-batches 20 --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_recalibrate_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_recalibrate_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_recalibrate_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_recalibrate_r5_p0p3_summary.csv
```

### P1 bn_dense_buffers_sgld_full_cifar

- Purpose: Bound whether sgld direct failure is a BatchNorm-buffer artifact.
- Criticism addressed: posterior sampler implementation may drive the result through BN running buffers
- Evaluation split: `test`
- BN policy: `dense_buffers`
- Saves mask/state artifacts: `False`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler sgld --samples 10 --sgld-steps 200 --sgld-burn-in 50 --sgld-sample-every 10 --sgld-lr 1e-6 --posterior-bn-policy dense_buffers --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_dense_buffers_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_dense_buffers_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_dense_buffers_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_bn_dense_buffers_r5_p0p3_summary.csv
```

### P1 bn_freeze_csgld_full_cifar

- Purpose: Bound whether csgld direct failure is a BatchNorm-buffer artifact.
- Criticism addressed: posterior sampler implementation may drive the result through BN running buffers
- Evaluation split: `test`
- BN policy: `freeze`
- Saves mask/state artifacts: `False`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler cyclical-sgld --samples 5 --posterior-chains 3 --posterior-chain-init dense --sgld-steps 400 --sgld-burn-in 50 --sgld-sample-every 10 --sgld-lr 1e-6 --sgld-likelihood-scale mean --csgld-cycle-length 50 --csgld-sample-phase-start 0.5 --posterior-bn-policy freeze --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_freeze_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_freeze_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_freeze_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_freeze_r5_p0p3_summary.csv
```

### P1 bn_recalibrate_csgld_full_cifar

- Purpose: Bound whether csgld direct failure is a BatchNorm-buffer artifact.
- Criticism addressed: posterior sampler implementation may drive the result through BN running buffers
- Evaluation split: `test`
- BN policy: `recalibrate`
- Saves mask/state artifacts: `False`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler cyclical-sgld --samples 5 --posterior-chains 3 --posterior-chain-init dense --sgld-steps 400 --sgld-burn-in 50 --sgld-sample-every 10 --sgld-lr 1e-6 --sgld-likelihood-scale mean --csgld-cycle-length 50 --csgld-sample-phase-start 0.5 --posterior-bn-policy recalibrate --bn-recalibration-batches 20 --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_recalibrate_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_recalibrate_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_recalibrate_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_recalibrate_r5_p0p3_summary.csv
```

### P1 bn_dense_buffers_csgld_full_cifar

- Purpose: Bound whether csgld direct failure is a BatchNorm-buffer artifact.
- Criticism addressed: posterior sampler implementation may drive the result through BN running buffers
- Evaluation split: `test`
- BN policy: `dense_buffers`
- Saves mask/state artifacts: `False`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler cyclical-sgld --samples 5 --posterior-chains 3 --posterior-chain-init dense --sgld-steps 400 --sgld-burn-in 50 --sgld-sample-every 10 --sgld-lr 1e-6 --sgld-likelihood-scale mean --csgld-cycle-length 50 --csgld-sample-phase-start 0.5 --posterior-bn-policy dense_buffers --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_dense_buffers_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_dense_buffers_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_dense_buffers_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_bn_dense_buffers_r5_p0p3_summary.csv
```

### P1 saved_artifacts_csgld_multichain

- Purpose: Save raw masks/states so direct distribution rows can be audited at seed level.
- Criticism addressed: pooled direct-row p-values are descriptive without saved per-seed artifacts
- Evaluation split: `test`
- BN policy: `sampler_default`
- Saves mask/state artifacts: `True`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler cyclical-sgld --samples 5 --posterior-chains 3 --posterior-chain-init dense --sgld-steps 400 --sgld-burn-in 50 --sgld-sample-every 10 --sgld-lr 1e-6 --sgld-likelihood-scale mean --csgld-cycle-length 50 --csgld-sample-phase-start 0.5 --save-mask-artifacts --save-state-artifacts --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_multichain_saved_artifacts_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_multichain_saved_artifacts_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_multichain_saved_artifacts_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_multichain_saved_artifacts_r5_p0p3_summary.csv
```

### P1 saved_artifacts_lowrank128

- Purpose: Save raw masks/states so direct distribution rows can be audited at seed level.
- Criticism addressed: pooled direct-row p-values are descriptive without saved per-seed artifacts
- Evaluation split: `test`
- BN policy: `sampler_default`
- Saves mask/state artifacts: `True`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler lowrank-laplace --samples 10 --lowrank-laplace-scale 1e-2 --lowrank-laplace-rank 128 --lowrank-laplace-power-iterations 1 --lowrank-laplace-oversample 32 --lowrank-laplace-fisher-batches 20 --lowrank-laplace-hessian-batches 2 --lowrank-laplace-prior-precision 1e-2 --lowrank-laplace-damping 1e-6 --lowrank-laplace-batchnorm-mode eval --save-mask-artifacts --save-state-artifacts --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_saved_artifacts_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_saved_artifacts_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_saved_artifacts_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_saved_artifacts_r5_p0p3_summary.csv
```

### P1 saved_artifacts_jointdiag

- Purpose: Save raw masks/states so direct distribution rows can be audited at seed level.
- Criticism addressed: pooled direct-row p-values are descriptive without saved per-seed artifacts
- Evaluation split: `test`
- BN policy: `sampler_default`
- Saves mask/state artifacts: `True`
- Observed: `True`

```bash
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_mode_ticket_distribution_probe.py --dataset cifar10 --model resnet20 --resnet-width 16 --seeds 0,1,2,3,4 --epochs 30 --rewind-epochs 1 --imp-rounds 5 --imp-epochs 30 --imp-final-epochs 30 --prune-fraction 0.30 --batch-size 512 --lr 0.1 --lr-schedule cosine --weight-decay 5e-4 --augment --cluster-pca-dim 20 --sliced-projections 128 --validation-fraction 0.1 --subset-strategy seeded --evaluation-split test --posterior-sampler jointdiag-laplace --samples 5 --jointdiag-laplace-scale 1e-6 --jointdiag-laplace-prior-precision 1e-2 --jointdiag-laplace-damping 1e-5 --jointdiag-laplace-hessian-batches 1 --jointdiag-laplace-max-parameters 40000 --save-mask-artifacts --save-state-artifacts --out-dir runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_saved_artifacts_r5_p0p3
.venv/bin/python scripts/summarize_mode_ticket_distribution_probe.py --run-root runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_saved_artifacts_r5_p0p3 --out-md docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_saved_artifacts_r5_p0p3.md --out-csv runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_saved_artifacts_r5_p0p3_summary.csv
```

## Audit Risk Flags

- none

This file is generated by `scripts/build_validation_bn_rerun_plan.py`.
