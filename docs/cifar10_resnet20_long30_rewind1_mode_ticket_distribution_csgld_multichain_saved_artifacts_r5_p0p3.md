# Mode/Ticket Distribution Probe

This is a direct check of the proposal-level equivalence criteria.
Posterior samples are converted to magnitude masks at the
matched IMP sparsity; posterior modes are mean-shift representatives
in PCA-reduced parameter space. Function-space similarity is measured
as linear CKA over held-out test logits and final hidden activations.

- Run: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_multichain_saved_artifacts_r5_p0p3/20260518_072346`
- Dataset/model: `cifar10` / `resnet20`
- Seeds: `[0, 1, 2, 3, 4]`; data seed `0`
- Evaluation split: `test`; validation fraction `0.1`; subset strategy `seeded`
- Posterior sampler: `cyclical-sgld` with 5 samples per chain, 3 chain(s) per seed from `dense` starts
- Posterior clusters: 1 (largest fraction 1.0000)
- Posterior basin entropy: 0.0000 nats; normalized 0.0000; effective clusters 1.0000
- Chain-start clusters: 1 (largest fraction 1.0000)
- Posterior-to-chain-start Hamming mean: 0.0445; sample accuracy mean 0.8721; chain-start accuracy mean 0.8808

| Comparison | n left | n tickets | KS p | MMD | SW2 | Hamming overlap | Logit CKA | Act. CKA | H-cost | Act. H-cost | Threshold pass count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| chain_start_magnitude_vs_tickets | 15 | 5 | 0.0000 | 1.6308 | 0.0756 | 0.0000 | 0.9386 | 0.9217 | 0.0614 | 0.0783 | 4/6 |
| posterior_samples_vs_tickets | 75 | 5 | 0.0000 | 1.4781 | 0.0704 | 0.0000 | 0.9349 | 0.9161 | 0.0651 | 0.0839 | 4/6 |
| posterior_modes_vs_tickets | 1 | 5 | 0.0413 | 1.7402 | 0.0784 | nan | 0.9326 | 0.9158 | 0.0674 | 0.0842 | 4/6 |

Interpretation:

- `posterior_samples_vs_tickets` tests the raw posterior sample-induced
  mask distribution against IMP tickets.
- `posterior_modes_vs_tickets` first collapses posterior samples to
  mean-shift mode representatives, then compares those representatives
  with IMP tickets.
- `*_aligned_*` rows first map ResNet masks into the first
  seed dense-model channel frame using the configured channel-alignment
  method, then repeat the same distribution checks.
- Passing the logit/activation CKA and Hungarian thresholds alone is
  not enough for H1; the proposal also requires mask-distribution agreement. Low
  Hamming-overlap or low KS support therefore counts against the
  strong one-to-one mode/ticket equivalence claim.

Caveats:
- Posterior modes are mean-shift representatives in raw parameter PCA space.
- Chain-start rows use magnitude masks from the dense state that initialized each posterior chain.
- No channel permutation alignment is applied here.
- Activation comparison uses final hidden-feature linear CKA on the held-out test split.
- Basin entropy is computed over the parameter-PCA mean-shift clusters used by each row.
