# Validation/Test Usage Policy Audit

This generated audit records the current selection/evaluation split
policy. It is intended to keep test-set peeking risk visible until
key rows are rerun with validation-selected locked configurations.

Current status: ready.

## Summary

- Dataset module: `src/lottery/data.py`
- DatasetBundle fields: train_loader, test_loader, input_dim, input_shape, num_classes, train_size, test_size, val_loader, val_size
- Shared validation loader present: `True`
- Digits scaler fit only on train split detected: `True`
- Torchvision first-N subset default detected: `False`
- Torchvision first-N subset option available for legacy/debug use: `True`
- Torchvision seeded subset option detected: `True`
- Run scripts scanned: 30
- Run scripts with test-loader usage: 20
- Test-loader scripts with validation/evaluation split support: 20
- Test-loader scripts still lacking validation/evaluation split support: 0
- Validation-selected CIFAR SGLD rerun observed: `True`
- Locked final-test SGLD rerun observed: `True`

## Open Risk Flags

- none

## Warning Flags

- test_loader_eval_paths_retained_but_validation_configurable

## Scripts Using Test Loader

| Script | Hits | Validation split support | First evidence lines |
| --- | ---: | ---: | --- |
| `scripts/run_block_laplace_probe.py` | 2 | True | L318: `eval_loader = bundle.test_loader`<br>L383: `test_loader=eval_loader,` |
| `scripts/run_calibration_ood_probe.py` | 3 | True | L169: `).test_loader`<br>L429: `eval_loader = bundle.test_loader`<br>L473: `test_loader=eval_loader,` |
| `scripts/run_cifar_baseline.py` | 1 | True | L86: `eval_loader = bundle.test_loader` |
| `scripts/run_digits_fullnet_laplace_probe.py` | 4 | True | L86: `test_loader,`<br>L91: `return evaluate(model, test_loader, device), predictions(model, test_loader, device)`<br>L123: `eval_loader = bundle.test_loader`<br>L188: `test_loader=eval_loader,` |
| `scripts/run_digits_hmc_baseline.py` | 2 | True | L73: `eval_loader = bundle.test_loader`<br>L104: `test_loader=eval_loader,` |
| `scripts/run_digits_pilot.py` | 2 | True | L162: `eval_loader = bundle.test_loader`<br>L226: `test_loader=eval_loader,` |
| `scripts/run_head_laplace_probe.py` | 2 | True | L125: `eval_loader = bundle.test_loader`<br>L190: `test_loader=eval_loader,` |
| `scripts/run_mode_ticket_distribution_probe.py` | 2 | True | L342: `return bundle.test_loader`<br>L1768: `test_loader=eval_loader,` |
| `scripts/run_residual_anatomy_probe.py` | 5 | True | L137: `test_loader: torch.utils.data.DataLoader,`<br>L174: `metrics = evaluate(model, test_loader, device)`<br>L191: `final_metrics = evaluate(final_model, test_loader, device)`<br>L604: `eval_loader = bundle.test_loader`<br>L683: `test_loader=eval_loader,` |
| `scripts/run_residual_base_compatibility_probe.py` | 1 | True | L417: `test_loader=artifact.eval_loader,` |
| `scripts/run_residual_cross_seed_transfer_probe.py` | 3 | True | L213: `eval_loader = bundle.test_loader`<br>L275: `test_loader=eval_loader,`<br>L530: `test_loader=target.eval_loader,` |
| `scripts/run_residual_direct_transfer_probe.py` | 1 | True | L535: `test_loader=target.eval_loader,` |
| `scripts/run_residual_imp_process_probe.py` | 6 | True | L217: `test_loader: torch.utils.data.DataLoader,`<br>L257: `metrics = evaluate(model, test_loader, device)`<br>L274: `final_metrics = evaluate(final_model, test_loader, device)`<br>L687: `eval_loader = bundle.test_loader`<br>L743: `test_loader=eval_loader,`<br>L838: `test_loader=eval_loader,` |
| `scripts/run_residual_predictor_mask_probe.py` | 5 | True | L212: `test_loader: torch.utils.data.DataLoader,`<br>L232: `metrics = evaluate(model, test_loader, device)`<br>L592: `eval_loader = bundle.test_loader`<br>L673: `test_loader=eval_loader,`<br>L745: `test_loader=eval_loader,` |
| `scripts/run_residual_stratified_control_probe.py` | 3 | True | L363: `eval_loader = bundle.test_loader`<br>L419: `test_loader=eval_loader,`<br>L477: `test_loader=eval_loader,` |
| `scripts/run_sgld_movement_grid.py` | 2 | True | L189: `eval_loader = bundle.test_loader`<br>L254: `test_loader=eval_loader,` |
| `scripts/run_subspace_hmc_probe.py` | 5 | True | L168: `test_loader: torch.utils.data.DataLoader,`<br>L201: `metrics[0] = evaluate(model, test_loader, device)`<br>L208: `metrics[epoch] = evaluate(model, test_loader, device)`<br>L378: `eval_loader = train_bundle.test_loader`<br>L476: `test_loader=eval_loader,` |
| `scripts/run_trajectory_mask_training_probe.py` | 10 | True | L211: `test_loader: torch.utils.data.DataLoader,`<br>L231: `metrics = evaluate(model, test_loader, device)`<br>L232: `metrics.update(calibration_metrics(model, test_loader, device))`<br>L284: `test_loader: torch.utils.data.DataLoader,`<br>L290: `metrics = evaluate(model, test_loader, device)`<br>L291: `metrics.update(calibration_metrics(model, test_loader, device))`<br>L346: `eval_loader = bundle.test_loader`<br>L426: `test_loader=eval_loader,` |
| `scripts/run_trajectory_probe.py` | 2 | True | L296: `eval_loader = bundle.test_loader`<br>L375: `test_loader=eval_loader,` |
| `scripts/run_trajectory_residual_probe.py` | 5 | True | L191: `test_loader: torch.utils.data.DataLoader,`<br>L211: `metrics = evaluate(model, test_loader, device)`<br>L434: `eval_loader = bundle.test_loader`<br>L517: `test_loader=eval_loader,`<br>L582: `test_loader=eval_loader,` |

## Scripts With First-N Subset Default

| Script | Hits | First evidence lines |
| --- | ---: | --- |
| none | 0 | none |

## Recommended Next Steps

- Use DatasetBundle.val_loader with --evaluation-split val for hyperparameter/model-selection diagnostics.
- Keep paper-supporting scripts validation-configurable when adding new evaluation paths.
- Run the locked final-test SGLD row once after validation selection and keep validation/test rows separate in paper tables.
- Mark existing test-reported sweep rows as falsification diagnostics rather than unbiased benchmark estimates.
- Keep --subset-strategy first as an explicit legacy/debug option only; default publishable subset evidence should remain seeded.

## Audit Risk Flags

- none

This file is generated by `scripts/audit_validation_test_usage_policy.py`.
