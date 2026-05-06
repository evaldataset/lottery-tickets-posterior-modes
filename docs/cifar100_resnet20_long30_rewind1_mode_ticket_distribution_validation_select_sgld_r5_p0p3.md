# Mode/Ticket Distribution Probe

This is a direct check of the proposal-level equivalence criteria.
Posterior samples are converted to magnitude masks at the
matched IMP sparsity; posterior modes are mean-shift representatives
in PCA-reduced parameter space. Function-space similarity is measured
as linear CKA over held-out validation logits and final hidden activations.

- Run: `runs/cifar100_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3/20260610_174216`
- Dataset/model: `cifar100` / `resnet20`
- Seeds: `[0, 1, 2, 3, 4]`; data seed `0`
- Evaluation split: `val`; validation fraction `0.1`; subset strategy `seeded`
- Posterior sampler: `sgld` with 10 samples per chain, 1 chain(s) per seed from `dense` starts
- Posterior clusters: 1 (largest fraction 1.0000)
- Posterior basin entropy: 0.0000 nats; normalized 0.0000; effective clusters 1.0000
- Chain-start clusters: 1 (largest fraction 1.0000)
- Posterior-to-chain-start Hamming mean: 0.0418; sample accuracy mean 0.5819; chain-start accuracy mean 0.5927

| Comparison | n left | n tickets | KS p | MMD | SW2 | Hamming overlap | Logit CKA | Act. CKA | H-cost | Act. H-cost | Threshold pass count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| chain_start_magnitude_vs_tickets | 5 | 5 | 0.0002 | 0.8826 | 0.0696 | 0.0000 | 0.8884 | 0.8459 | 0.1116 | 0.1541 | 3/6 |
| posterior_samples_vs_tickets | 50 | 5 | 0.0000 | 1.5268 | 0.0655 | 0.0000 | 0.8834 | 0.8402 | 0.1166 | 0.1598 | 3/6 |
| posterior_modes_vs_tickets | 1 | 5 | 0.0413 | 1.7199 | 0.0743 | nan | 0.8816 | 0.8369 | 0.1184 | 0.1631 | 3/6 |

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
