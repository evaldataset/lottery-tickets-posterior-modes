# Mode/Ticket Distribution Probe

This is a direct check of the proposal-level equivalence criteria.
Posterior samples are converted to magnitude masks at the
matched IMP sparsity; posterior modes are mean-shift representatives
in PCA-reduced parameter space. Function-space similarity is measured
as linear CKA over held-out test logits and final hidden activations.

- Run: `runs/cifar100_resnet20_long30_rewind1_mode_ticket_distribution_sgld_r5_p0p3/20260524_225916`
- Dataset/model: `cifar100` / `resnet20`
- Seeds: `[0, 1, 2, 3, 4]`; data seed `0`
- Evaluation split: `test`; validation fraction `0.0`; subset strategy `seeded`
- Posterior sampler: `sgld` with 10 samples per chain, 1 chain(s) per seed from `dense` starts
- Posterior clusters: 1 (largest fraction 1.0000)
- Posterior basin entropy: 0.0000 nats; normalized 0.0000; effective clusters 1.0000
- Chain-start clusters: 1 (largest fraction 1.0000)
- Posterior-to-chain-start Hamming mean: 0.0367; sample accuracy mean 0.6169; chain-start accuracy mean 0.6296

| Comparison | n left | n tickets | KS p | MMD | SW2 | Hamming overlap | Logit CKA | Act. CKA | H-cost | Act. H-cost | Threshold pass count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| chain_start_magnitude_vs_tickets | 5 | 5 | 0.0009 | 0.9061 | 0.0513 | 1.0000 | 0.8913 | 0.8442 | 0.1087 | 0.1558 | 4/6 |
| posterior_samples_vs_tickets | 50 | 5 | 0.0000 | 1.1576 | 0.0491 | 0.8163 | 0.8858 | 0.8375 | 0.1142 | 0.1625 | 4/6 |
| posterior_modes_vs_tickets | 1 | 5 | 0.1153 | 1.4767 | 0.0473 | nan | 0.8833 | 0.8327 | 0.1167 | 0.1673 | 4/6 |

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
