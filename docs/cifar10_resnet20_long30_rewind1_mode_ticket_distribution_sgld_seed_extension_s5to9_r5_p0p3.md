# Mode/Ticket Distribution Probe

This is a direct check of the proposal-level equivalence criteria.
Posterior samples are converted to magnitude masks at the
matched IMP sparsity; posterior modes are mean-shift representatives
in PCA-reduced parameter space. Function-space similarity is measured
as linear CKA over held-out validation logits and final hidden activations.

- Run: `runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_sgld_seed_extension_s5to9_r5_p0p3/20260610_214505`
- Dataset/model: `cifar10` / `resnet20`
- Seeds: `[5, 6, 7, 8, 9]`; data seed `0`
- Evaluation split: `val`; validation fraction `0.1`; subset strategy `seeded`
- Posterior sampler: `sgld` with 10 samples per chain, 1 chain(s) per seed from `dense` starts
- Posterior clusters: 1 (largest fraction 1.0000)
- Posterior basin entropy: 0.0000 nats; normalized 0.0000; effective clusters 1.0000
- Chain-start clusters: 1 (largest fraction 1.0000)
- Posterior-to-chain-start Hamming mean: 0.0518; sample accuracy mean 0.8717; chain-start accuracy mean 0.8798

| Comparison | n left | n tickets | KS p | MMD | SW2 | Hamming overlap | Logit CKA | Act. CKA | H-cost | Act. H-cost | Threshold pass count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| chain_start_magnitude_vs_tickets | 5 | 5 | 0.0000 | 0.9408 | 0.0819 | 0.0000 | 0.9377 | 0.9190 | 0.0623 | 0.0810 | 4/6 |
| posterior_samples_vs_tickets | 50 | 5 | 0.0000 | 1.2512 | 0.0739 | 0.0000 | 0.9334 | 0.9128 | 0.0666 | 0.0872 | 4/6 |
| posterior_modes_vs_tickets | 1 | 5 | 0.0413 | 1.7336 | 0.0817 | nan | 0.9308 | 0.9114 | 0.0692 | 0.0886 | 4/6 |

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
- Activation comparison uses final hidden-feature linear CKA on the held-out validation split.
- Basin entropy is computed over the parameter-PCA mean-shift clusters used by each row.
