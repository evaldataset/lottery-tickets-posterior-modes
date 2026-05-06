# Venue Strategy Matrix

Audit date: `2026-05-13`.
Source observation mode: `recorded_live_probe`.
Source probe: `docs/venue_source_probe.md`.

This generated matrix records the venue triage for the current paper. It is
a submission-planning artifact, not a final submission-readiness gate.

## Decision

- Primary target: `TMLR (rolling)`
- First backup: `ICLR 2027`
- Second backup: `AISTATS 2027`
- Emergency fallback: `ICDM 2026`
- Do not chase fast deadlines: `CIKM 2026`, `EMNLP 2026`
- Rationale: The current contribution is a controlled negative-result audit with a positive trajectory/process account, a Proposition, a locked final-test confirmation, and a reusable posterior-vs-IMP audit framework. TMLR's correctness-only acceptance criterion (novelty is explicitly not a rejection ground) and absence of a page limit accommodate this evidence density without forced scope cuts, and the local TMLR packet is already prepared, leaving only author OpenReview/COI inputs. ICLR 2027 remains a high-visibility backup once the official 2027 CFP is observed.

## Ranking

| Rank | Venue | Score | Recommendation | Deadline | Deadline status | Scope fit |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | `TMLR (rolling)` | 96 | primary target | rolling submission; no fixed deadline | rolling_submission_no_fixed_deadline | excellent |
| 2 | `ICLR 2027` | 88 | high-visibility backup | September 2026 expected from ICLR 2026 pattern | official_iclr_2027_cfp_not_observed; 2026 official pattern only | excellent |
| 3 | `AISTATS 2027` | 86 | statistics-audience backup | October 2026 expected from AISTATS 2026 pattern | official_2027_cfp_not_observed; 2026 official pattern only | strong |
| 4 | `AAAI 2027` | 78 | broad-AI backup | late July to early August 2026 per user-provided schedule; official CFP not verified here | user_supplied_deadline; official_aaai_2027_cfp_not_observed | moderate_to_strong |
| 5 | `ICDM 2026` | 64 | emergency fallback only | June 6, 2026 | official deadline observed | moderate |
| 6 | `CIKM 2026` | 53 | do not target unless rescoping radically | May 16, 2026 abstract; May 23, 2026 full paper | official deadline observed | weak_to_moderate |
| 7 | `BIGDATA 2026` | 49 | low-priority fallback | August 21, 2026 | official deadline observed | weak_to_moderate |
| 8 | `WSDM 2027` | 43 | do not target | August 11, 2026 per user-provided schedule; official 2027 CFP not verified here | user_supplied_deadline; 2027 official CFP not observed | weak |
| 9 | `EMNLP 2026` | 40 | do not target | May 25, 2026 ARR deadline | official deadline observed | weak |
| 10 | `WWW 2027` | 34 | do not target | November 2026 per user-provided schedule; official 2027 CFP not verified here | user_supplied_deadline; 2027 official CFP not observed | poor |
| 11 | `ICDE 2027` | 30 | do not target | June 11, 2026 first round; November 11, 2026 second round | official deadline observed | poor |

## Venue Notes

### TMLR (rolling)

- Why it fits or fails: TMLR's correctness-only acceptance criterion is the natural fit for a controlled negative-result audit. No page limit accommodates the operational gate, twelve-posterior-approximation harness, theory Proposition, locked final-test confirmation, and reusable audit framework as first-class contributions. Rolling decisions remove deadline-driven scope cuts and let the manuscript ship at full evidence density. The local TMLR packet (paste payload, snapshot, operator handoff bundle, final-gate audit) is already prepared; only author OpenReview profile, COI, and ethics confirmations remain.
- Required reframing: Foreground the operational support-equivalence gate, the trajectory/process positive account, and the audit framework as three first-class contributions, with the negative empirical result as the central evidence rather than the sole contribution.
- Main risk: Author OpenReview profile, COI/ethics/LLM/funding confirmations, and the external CUDA-host GPU-container receipt remain outstanding; these are blocking for submission but do not require any further empirical work.
- Source URLs:
  - https://www.jmlr.org/tmlr/
  - https://www.jmlr.org/tmlr/editorial-policies.html

### ICLR 2027

- Why it fits or fails: Core ML audience for posterior approximations, Bayesian deep learning, optimization, representation learning, pruning, and empirical negative results.
- Required reframing: Keep the paper framed as a falsifiable support-equivalence audit, not as a universal Bayesian-pruning impossibility claim.
- Main risk: Official 2027 CFP/author guide not observed; locked final-test, BN ablation, formal screening, and external validation remain open.
- Source URLs:
  - https://iclr.cc/Conferences/2027/CallForPapers
  - https://iclr.cc/Conferences/2027/AuthorGuide
  - https://iclr.cc/Conferences/2026/CallForPapers

### AISTATS 2027

- Why it fits or fails: Bayesian posterior support, approximation diagnostics, and statistical audit framing are natural for the AI/statistics audience.
- Required reframing: Move statistical reliability, hierarchical/seed-level tests, and posterior-support diagnostics to the foreground.
- Main risk: Current paper reads more like pruning/representation-learning than statistics unless the test design and uncertainty analysis are emphasized.
- Source URLs:
  - https://virtual.aistats.org/Conferences/2026/CallForPapers

### AAAI 2027

- Why it fits or fails: Broad AI venue can absorb pruning, Bayesian learning, and empirical methodology if the contribution is made concise and general.
- Required reframing: Compress the argument around one clear reviewer-facing contribution and keep artifact details in supplementary material.
- Main risk: Shorter main-paper format and broad reviewer pool increase the risk of 'incremental negative result' reviews.
- Source URLs:
  - https://aaai.org/conference/aaai/aaai-26/main-technical-track-call/

### ICDM 2026

- Why it fits or fails: Machine learning and deep learning are in scope, but the paper is not primarily a data-mining algorithm or application paper.
- Required reframing: Present the work as a reproducible data-mining/ML evaluation protocol for sparse neural model discovery.
- Main risk: Less natural audience than ICLR/AISTATS; deadline leaves limited time to close locked final-test and BN risks.
- Source URLs:
  - https://www3.cs.stonybrook.edu/~icdm2026/
  - https://www3.cs.stonybrook.edu/~icdm2026/dates/list.htm

### CIKM 2026

- Why it fits or fails: CIKM covers AI/data science, but its core identity is information retrieval, knowledge management, and databases.
- Required reframing: Would need a data/knowledge discovery angle that the current paper does not naturally have.
- Main risk: Deadline is too close for the current unresolved top-tier blockers.
- Source URLs:
  - https://cikm2026.diag.uniroma1.it/full-research-papers/

### BIGDATA 2026

- Why it fits or fails: The venue emphasizes big-data foundations, infrastructure, 5V data challenges, and applications; this paper is a model-analysis study.
- Required reframing: Would need a scalability or big-data systems angle rather than only CIFAR/MNIST posterior diagnostics.
- Main risk: Scope mismatch and lower strategic value for the current contribution.
- Source URLs:
  - https://bigdataieee.org/BigData2026/calls/papers/

### WSDM 2027

- Why it fits or fails: WSDM is search and web data mining; the paper has no web/search task.
- Required reframing: Would need a web-scale search, recommendation, or social/web mining problem, which would be a different paper.
- Main risk: High desk-review or reviewer-fit risk from scope mismatch.
- Source URLs:
  - https://www.wsdm-conference.org/calls.php

### EMNLP 2026

- Why it fits or fails: The paper has no NLP task, language data, or language-model result.
- Required reframing: Would require new NLP experiments and a language-model interpretation angle, not just a style conversion.
- Main risk: Scope mismatch plus very short deadline.
- Source URLs:
  - https://2026.emnlp.org/calls/main_conference_papers/

### WWW 2027

- Why it fits or fails: The Web Conference requires explicit relevance to Web systems or Web-related scientific questions; this paper is general ML.
- Required reframing: Would require a real Web problem and new evidence.
- Main risk: Likely out of scope without major new Web-centered experiments.
- Source URLs:
  - https://thewebconf.org/
  - https://www2026.thewebconf.org/calls/research-tracks.html

### ICDE 2027

- Why it fits or fails: ICDE is a data-engineering venue; prior ICDE guidance flags pure ML without data-management aspects as out of scope.
- Required reframing: Would require data management, scalability, or system contribution.
- Main risk: Strong scope mismatch.
- Source URLs:
  - https://icde2027.github.io/cf-research-papers.html

## Official Source Observations

### TMLR (rolling)

- Deadline status: rolling_submission_no_fixed_deadline
- Observation: TMLR uses rolling submission with a published editorial policy. Acceptance criterion is explicitly limited to correctness and support for claims; novelty/significance is not a rejection ground.
- Sources:
  - https://www.jmlr.org/tmlr/
  - https://www.jmlr.org/tmlr/editorial-policies.html

### ICLR 2027

- Deadline status: official_iclr_2027_cfp_not_observed; 2026 official pattern only
- Observation: Official 2027 CFP/Author Guide URLs are not observed; 2026 CFP is the only recorded official policy proxy.
- Sources:
  - https://iclr.cc/Conferences/2027/CallForPapers
  - https://iclr.cc/Conferences/2027/AuthorGuide
  - https://iclr.cc/Conferences/2026/CallForPapers

### AISTATS 2027

- Deadline status: official_2027_cfp_not_observed; 2026 official pattern only
- Observation: Official AISTATS 2027 CFP is not observed. Official AISTATS 2026 CFP lists abstract September 25, 2025 AOE and full paper October 2, 2025 AOE, so October 2026 remains a pattern-based estimate.
- Sources:
  - https://virtual.aistats.org/Conferences/2026/CallForPapers

### AAAI 2027

- Deadline status: user_supplied_deadline; official_aaai_2027_cfp_not_observed
- Observation: Official AAAI 2027 CFP is not observed. Official AAAI-26 main technical track lists July 25, 2025 abstract and August 1, 2025 full-paper deadlines, supporting only a pattern-based 2027 estimate.
- Sources:
  - https://aaai.org/conference/aaai/aaai-26/main-technical-track-call/

### ICDM 2026

- Deadline status: official deadline observed
- Observation: Official IEEE ICDM 2026 research-track and dates pages list June 6, 2026 as the full-paper submission deadline.
- Sources:
  - https://www3.cs.stonybrook.edu/~icdm2026/
  - https://www3.cs.stonybrook.edu/~icdm2026/dates/list.htm

### CIKM 2026

- Deadline status: official deadline observed
- Observation: Official CIKM 2026 full-research page lists May 16, 2026 abstract deadline and May 23, 2026 full-paper deadline.
- Sources:
  - https://cikm2026.diag.uniroma1.it/full-research-papers/

### BIGDATA 2026

- Deadline status: official deadline observed
- Observation: Official IEEE BigData 2026 CFP lists August 21, 2026 as the full paper submission deadline and Dec 14-17, 2026 in Phoenix.
- Sources:
  - https://bigdataieee.org/BigData2026/calls/papers/

### WSDM 2027

- Deadline status: user_supplied_deadline; 2027 official CFP not observed
- Observation: Official WSDM site currently exposes a call for WSDM 2027 host bids in Asia/Oceania, not a 2027 paper CFP. The August 11, 2026 paper deadline remains user-supplied and unverified.
- Sources:
  - https://www.wsdm-conference.org/calls.php

### EMNLP 2026

- Deadline status: official deadline observed
- Observation: Official EMNLP 2026 main conference CFP lists May 25, 2026 as the ARR submission deadline and August 2, 2026 as the EMNLP commitment deadline.
- Sources:
  - https://2026.emnlp.org/calls/main_conference_papers/

### WWW 2027

- Deadline status: user_supplied_deadline; 2027 official CFP not observed
- Observation: Official TheWebConf series page lists The ACM Web Conference 2027 in Dublin with date TBD. A 2027 research-track CFP is not observed; November 2026 remains a user-supplied estimate.
- Sources:
  - https://thewebconf.org/
  - https://www2026.thewebconf.org/calls/research-tracks.html

### ICDE 2027

- Deadline status: official deadline observed
- Observation: Official IEEE ICDE 2027 research-track CFP lists two submission rounds: June 11, 2026 and November 11, 2026.
- Sources:
  - https://icde2027.github.io/cf-research-papers.html

## Open Risks

- iclr_2027_official_cfp_not_observed
- iclr_2027_official_author_guide_not_observed
- aistats_2027_official_cfp_not_observed
- aaai_2027_official_cfp_not_observed
- wsdm_2027_official_cfp_not_observed
- www_2027_official_cfp_not_observed
- iclr_openreview_author_profile_and_coi_not_recorded
- iclr_openreview_submission_receipt_not_observed
- iclr_code_of_ethics_author_acknowledgement_not_recorded
- llm_usage_disclosure_author_confirmation_not_recorded
- public_release_archive_smoke_not_ready
- public_release_upload_not_verified
- public_repository_state_not_verified
- external_ci_run_not_observed
- external_gpu_container_run_not_observed
- formal_external_plagiarism_database_screen_not_performed

## Required Before Primary Submission

- run the locked final-test row from the validation-selected config
- run full-CIFAR BatchNorm posterior-policy ablations
- complete seed-level saved-artifact coverage for remaining direct rows or downscope the pooled statistics
- complete formal external plagiarism/corpus screening
- record final author OpenReview/COI/ethics/LLM confirmations
- collect public release, public repository, external CI, and external CUDA/GPU receipts
- submit the prepared TMLR packet via OpenReview after recording author OpenReview profile, COI, and ethics confirmations

This file is generated by `scripts/build_venue_strategy_matrix.py`.
