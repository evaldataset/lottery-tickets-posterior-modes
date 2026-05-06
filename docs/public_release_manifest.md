# Public Release Manifest

Date: 2026-05-06

This manifest defines the minimum local package needed to inspect the
paper, regenerate generated statistics from included run artifacts,
and verify the core claims. The full per-file SHA256 inventory is in
`runs/public_release_manifest.json`.

`docs/external_validation_receipts.json` is intentionally excluded:
it is a mutable post-release registry for public URLs, source commits,
CI runs, and GPU logs.

Total files: 2164
Total bytes: 371.8 MiB

## Category Summary

| Category | Files | Bytes |
| --- | ---: | ---: |
| ci | 1 | 1.4 KiB |
| docs | 266 | 1.3 MiB |
| paper | 11 | 1.4 MiB |
| paper-figures | 6 | 220.4 KiB |
| paper-tables | 1 | 31.8 KiB |
| root | 12 | 181.1 KiB |
| run-artifacts | 1726 | 366.0 MiB |
| scripts | 117 | 2.5 MiB |
| source | 24 | 139.2 KiB |

## Required Artifacts

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| .dockerignore | 391 | `dc31f24c9cb52a69d1aefc300d7fcb8b9d7e2768a160b38c2f372ab23a56abc4` |
| .github/workflows/check.yml | 1389 | `edacf5072e2bcd6998a0fa51a39b592e4166159c9ba6f16c6838bf3b551db6b3` |
| .gitignore | 175 | `472922ca7d9d71ec20d0083d5632066849555d76d60fcb2b8f9a0f72b4ed6ca9` |
| Dockerfile | 1293 | `0841b7b00b5e269d6e7bef5a5cc346b144138efa94f14d20cc8ae5d55f0b0105` |
| Dockerfile.gpu | 1672 | `c1b9fa5354b4d085ef3dd4cdda9033b770ee769c2a09c07940af0e9cd0b336ec` |
| LICENSE | 1074 | `1d0dde41ece0f9620937f1a81a67e295ace0eae180c009d862006e8f3b288458` |
| Makefile | 26571 | `b5b62052b923c086cf1b6d29475353c0d792316e2f0c1c627c6c80e500f2863f` |
| README.md | 133614 | `55af3f5e2f455cc21fc47ad50189925dc28b77f7fc18ea4d76759cd1c6e46215` |
| requirements-ci.txt | 82 | `ce5460165123c8f91ea7ba49296c66d53ae24b04b4ffd638184b4022616001e2` |
| requirements-gpu-lock.txt | 374 | `5d80d0caa3599bd900afdf0ea77837391f349553df4d1751720752980a2ddab2` |
| requirements-lock.txt | 425 | `373f546c4fefb1ca56a6cd1b92a3fc68689a0196aa993a4bc401e5166b8ae8f3` |
| docs/container_lock.md | 4010 | `d43baf5c9146deeab44ce695cc00cb25629a5fdf1ee0bc349d7d39381323290a` |
| docs/gpu_training_container.md | 3735 | `c232d741514c6f7852f71a565850aad5b5e523fbe1ae458fc1871c98f48678e8` |
| docs/local_gpu_container_validation.md | 892 | `1a0756be81b5e4b677f76bf11ba45cc33adab9fb8efcfa9b4373856a7a0bdd08` |
| docs/compute_resource_accounting.md | 5661 | `9e11c26e55eea6f6de347cdd3e60af83abd305b301943c0bf2cd6f188f18d9ad` |
| docs/asset_license_inventory.md | 5606 | `85d1899b4c49210925592193f43e094419f17cc075dce2213b9dc4ae13c54bbd` |
| docs/new_asset_inventory.md | 5131 | `b542416e55a37fb1d990c7171dd11c31a2cfa7590a3e83d1ec3eb0e578398494` |
| docs/cifar10_resnet20_full_covariance_feasibility.md | 3098 | `4ed64e4c5cf5aaba16ccb217e8bfba2587f4ef7d7bdf42c5ad2ce38a4a6e9e15` |
| docs/digits_fullnet_laplace_tiny_r2_p0p3.md | 1318 | `aef18d08ffa61da26be8dc3d761e0ff0fd5844a68cbb57a68363de80aedde0e5` |
| docs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke.md | 1154 | `a1e0dc159eec46d8da8b69836d4c5849079711c3f5026810142061c0031cb212` |
| docs/linear_connectivity_barrier_audit.md | 1751 | `b264dc04e46c82ed4072dc1e2c8c0d20e838f17c29fa1ac0ec7ca052f425e78c` |
| docs/posterior_covariance_robustness_audit.md | 3904 | `37790b1a3f600b945b20f560491d7445c339b845124c125b577f63d493327362` |
| docs/cifar10_resnet20_long30_rewind1_lowrank_laplace_movement_selected_r5_p0p3.md | 1293 | `7305cde802d613561340a00c6be5a457fa1cbc6dab2a9350b41f3ca3723b0792` |
| docs/cifar10_resnet20_long30_rewind1_lowrank32_laplace_movement_selected_r5_p0p3.md | 1293 | `f977cee93ab8b479945c648c29bd3a0fec2167841570f872541e5dfb4da77295` |
| docs/cifar10_resnet20_long30_rewind1_lowrank64_laplace_movement_selected_r5_p0p3.md | 1292 | `1d3d0994d444a477d778bb2404c4f5df3ce96732a251cab7463c7b85d2ff93b9` |
| docs/cifar10_resnet20_long30_rewind1_lowrank128_laplace_movement_selected_r5_p0p3.md | 824 | `4de29cb678af6b604d3c5d255834e5803aa97fe04baf26a6202bd66fbac07cfe` |
| docs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_selected_r5_p0p3.md | 1086 | `1874665908f405a1846764746e0e8551e064f90f539c563363bdc74fc607cc75` |
| docs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_max10k_selected_r5_p0p3.md | 1088 | `1965e84f22637256cd7d2fd868c2bd080e27531fc5018355d3ec227f5698e854` |
| docs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max10k_selected_r5_p0p3.md | 1194 | `a83c298ef34a6eb0fdb2bd8e62c50d1067cb071b0fd62a6ff3d7b05f33404ff6` |
| docs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max20k_selected_r5_p0p3.md | 1194 | `e970b9864259330f8bae509aab27dff99fb5378cc7a50826a1cad35cc911db1a` |
| docs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max40k_stream_selected_r5_p0p3.md | 1194 | `60eec9801289ee82c77cba6bae603b05ee195d1d4e21e5f0f3516d830c1dc4ef` |
| docs/cifar10_resnet20_long30_rewind1_hessian32_subspace_hmc_selected_r5_p0p3.md | 857 | `0ae7dc6358f66ce19506ba4ed22563de8805469230b78320960edd62bba33a0c` |
| docs/cifar10_resnet20_long30_rewind1_hard_concrete_selected_r5_p0p3.md | 587 | `f7a4cef2df0708bf95ea1408c805b3c34f97e65f112120b7b7782528aaf15546` |
| docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_weight_aligned_r5_p0p3.md | 3367 | `ddef34956dd52eab6f8a245e78763cc49ec4cd8d9214238d78dd6bd578eec31c` |
| docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_independent_multichain_r5_p0p3.md | 2722 | `974fab23451c502712161a64d62ad3738790cae5c02e5c7c462c9e37e45c6584` |
| docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_r5_p0p3.md | 2702 | `d156f190b4a11bbb877f2882890d2f6d7ac385a62a8bc1a644bf90335f1e8274` |
| docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_r5_p0p3.md | 2716 | `c23a31470f25da234a0c0e019b54bcc75b1f500d04673397db0f784317d8a07c` |
| docs/fake_cifar10_mode_ticket_mask_artifact_smoke.md | 4274 | `2652c88771a9d46551b85e760269554c0bd633b365443689380fefe92aafc505` |
| docs/fake_cifar10_mode_ticket_mask_artifact_posthoc_audit.md | 3698 | `96ab348b821e6edff5c80718a8634c6c6bda4ba4226219fbff0f2c7bfdb8b316` |
| docs/mode_ticket_artifact_storage_budget.md | 2913 | `0ad534be0a775f5a9ac6a1fc27214d3d270ce649a480de3cb716bb7313f951e2` |
| docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3.md | 3397 | `7a1341135bd6d4f64261380eb33acb4c3337ea4504814b399ee25c8155256583` |
| docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.md | 3486 | `ff41f6eb74fdc44f5f685c890c470fe189504b7d504d621ce20d15ecde85b199` |
| docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_global_channel_audit.md | 2021 | `02605047cff6d6498627fd2d02ac027fa8aaab0f25b6875c9042633bc17c30a2` |
| docs/resnet_channel_permutation_exhaustive_feasibility_audit.md | 2516 | `bc2c7f5e20f3a156fe4a8cad1eaa2f45632f3b87e64f55e4bdeaa5603c3f86dd` |
| docs/cifar10_resnet20_long30_rewind1_residual_imp_process_stratified_exclusion_r5_p0p3.md | 1572 | `e9a55cd09442206adb386711642169a56ea98c4d6404d63858fc732f22e1ee6f` |
| docs/cifar10_resnet20_long30_rewind1_residual_imp_process_projection_r5_p0p3.md | 1506 | `49244555b681c1c77cde204cc1165f33a791019e2c99cebd820ba62b9d70426b` |
| docs/cifar10_resnet20_long30_rewind1_residual_imp_process_posterior_projection_r5_p0p3.md | 1516 | `725c1ad0bc3d08e6e1bb4c04ec6c9a03609f3e746f6777940fa5cfc21196fad5` |
| docs/cifar10_resnet20_long30_rewind1_residual_imp_process_learned_subspace_r5_p0p3.md | 1523 | `49434006a530b741a3f1d5acce90f841afa7134cd889eebe9650dc258794903d` |
| docs/environment_lock.json | 527 | `db878e1df83ae080000ef95618cd98c41ebe8db397b02f6439b69949af4adba1` |
| docs/mode_ticket_alignment_artifact_audit.md | 4154 | `d8a28aa378d015e1464ebf46f2d38a5e5dd518a68088e9421a63401f507646d7` |
| docs/paper_claim_ledger.md | 20142 | `ac28cb977be48e6757766862b24144235f1e581880f99e35146a018e45f23966` |
| docs/paper_submission_shape_audit.md | 2004 | `2d71b48a70e583b3091b816e64d68704854984b3165a4e251c82e79498b2e6a7` |
| docs/submission_pdf_shape_audit.md | 669 | `ca931055579743d248eedfb1e8c813d42fae507ef5d67e3397bd5d039f48f26c` |
| docs/venue_submission_compliance_audit.md | 2844 | `302a05fd03e3df60a80d2f66e70131461dbbf9c1d6a090afb9e2207f0e3a221e` |
| docs/iclr_submission_readiness_audit.md | 4825 | `adad02d0cc965d8dfc17cb7bb0060f5f8b6f7876fec6460b947f83bea326c368` |
| docs/ethics_statement_audit.md | 775 | `d4d03b4f54b98cac8d0f13cf69a18df735a41a89ed6a7153f6915286d5f8fe5e` |
| docs/llm_usage_disclosure_audit.md | 755 | `62ac048c8a22d950538f64025b2fdc97303634653ab5e90caf9b823a07909bfe` |
| docs/iclr_policy_watch_audit.md | 2477 | `2f7092aa4038f31703d8c99f0247c7298190c2f1e70664ed6d375327865753a6` |
| docs/iclr_openreview_packet.md | 5103 | `ba402ee14f257450d6e8f9df3b20161fa2410e40d2e733e24c057df30bbec220` |
| docs/iclr_human_confirmation_template.md | 3390 | `bf4c17faf330a52a2d692bd7b74a77e48e1f7024c9b81814c9ecd1be73b31dd6` |
| docs/iclr_human_confirmation_receipt_audit.md | 1122 | `f1e4e6aaf89ed67a592091296fe4497689af659a16a967a714d5dfccf8916629` |
| docs/venue_strategy_matrix.md | 13827 | `140a2bdcc9c5f8e381521a9e12ec40810bd62a2e02909f9e65b866b0142d0f67` |
| docs/formal_plagiarism_screening_runbook.md | 3110 | `ae0def01bed4ed87e145bf6921122b13a92f310716e316be16defc5bf518d4ff` |
| docs/reviewer_objection_matrix.md | 8569 | `d0d2ab684cd47132bb7af1c444f16723e69ca8835dbcd1257fb46017609f1496` |
| docs/proposal_to_artifact_audit.md | 5750 | `757d0e3c9e2ea9b68dd0a4f1860833fb4f7d9cfe02858f7f685a737476ee8df4` |
| docs/reproducibility_manifest.md | 27465 | `4d5abf09595d36811701baec811d3f2433bbff73ee909dd3a3dbba42fb41378c` |
| docs/unit_smoke_tests.md | 815 | `98070d38285e28f1713e4fb933f013f73f56826ee326b109be525124102969f5` |
| docs/submission_readiness_audit.md | 64957 | `c58b2fa42f22701baeaf046a4561dba247e44f320ae0b1fbc954711ee94ea602` |
| docs/thread_goal_completion_audit.md | 39809 | `3654ec0edd817725e1ade96ac1603bbb5936e24ff99b4975b56b31354c26940e` |
| docs/paper_asset_freshness_audit.md | 2692 | `625d07f923a62f0d815d49c1168bb50396ca783a481c133469b3598feb64e23d` |
| docs/remaining_experiment_queue.md | 14627 | `c172cd0ee973ef8d9369d9f052beef4e983f18d6756d1b0ef4b2c40f51f1c941` |
| docs/remaining_experiment_preflight_audit.md | 2135 | `13d5c59390120cfa628bc98f7ffa4d6626c8175f5072ac02d0135f9b3289ff6e` |
| docs/open_blocker_claim_scope_audit.md | 2543 | `582a61782e330827e56cd506ba94845b9369449eefd46643ee04ae32ef5fd0d4` |
| runs/mode_ticket_alignment_artifact_audit.json | 18515 | `e55ddc90158cad4fe2bb8384449111496d6fe7f720b3627300f5283c5f4c708b` |
| runs/fake_cifar10_mode_ticket_mask_artifact_posthoc_audit.json | 29829 | `7a9baf91f9a82b1990d41ec35c1e93c3502e0c33a545f758f4b74f8e6674036e` |
| runs/mode_ticket_artifact_storage_budget.json | 6129 | `cc35a0c9784a8af76b818febd23da3ab962bfff2c8b341f078a4a0ab78399389` |
| runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.json | 24797 | `5294c38de9f07ca0be70d513605085c7fd29a0047f00081d3cc01ad2c7336648` |
| runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_global_channel_audit.json | 46706 | `0bc66a5e667eb6e38a8f0e2575d2b689f1ee501ac3a2d83641b6fc5684404d88` |
| runs/resnet_channel_permutation_exhaustive_feasibility_audit.json | 9264 | `81d5c927e6c15be48dbc85d222d669019c578cbe6968235b73550a09320005ce` |
| runs/paper_submission_shape_audit.json | 2837 | `fc6d6f4ba0835a25414db6eebaac299646d3e1e7c5b5c87fa0f0bf3fb2b63315` |
| runs/submission_pdf_shape_audit.json | 322 | `6562b87700615a589bb0f00cdef8aa69a98eabe9d4028869ab6ad4a9e41e39c6` |
| runs/venue_submission_compliance_audit.json | 2821 | `e485520b76b78f72ac781c7e98da79c75aaf3e850ab9ff10407da90273674fd9` |
| runs/iclr_submission_readiness_audit.json | 4106 | `e0b8c3f99df33355c1b9157c694c38ce2026c8b22ef8dfde14052634d8fef6f2` |
| runs/ethics_statement_audit.json | 1097 | `aae72e440e67fc5ebaa9bc328cc9d2348ff95323aab52581e533ac03c04b39eb` |
| runs/llm_usage_disclosure_audit.json | 1053 | `85e953436d4fcb859ee69cd8d1af9c9bbedc9bd0cfe746a6c3bece64ef8ffcd9` |
| runs/iclr_policy_watch_audit.json | 2969 | `2c0d1c3d1981618ac3f624235d7af43ac6b3e39fe0e7f4ae06c4730e98c0ca04` |
| runs/iclr_openreview_packet.json | 8515 | `3e7a4fb1e31834a60a21432a58a9b229ecceb68c960b4055cc86303d51e9ff3d` |
| runs/iclr_human_confirmation_template.json | 3776 | `f15e4a643674e6e0af61ad2fe216d1d81278164193b54b3a4889777c76560f96` |
| runs/iclr_human_confirmation_receipt_audit.json | 1908 | `42913b011837f24f0624e130b4096fee6158bfe57c3e719b445bf62a32a69d6d` |
| runs/venue_strategy_matrix.json | 25982 | `e4e46d5aebad87496423b110f11fb8f83be128d1ef687a55daa04cca1265a9dc` |
| runs/formal_plagiarism_screening_runbook.json | 3787 | `2403493887d96786d452e9f9980f55bd9fc302c4c15e6908ea30beb9aeca6227` |
| runs/unit_smoke_tests.json | 904 | `e271b33cb9fb0263b9105ffc73cbca6243475ed48aacd92a7216e5d6843642a5` |
| runs/local_gpu_container_validation.json | 1851 | `0800c51acaa9f00a0c42b41c0d280bda29f61c7415e1eee7d314d7e308cac673` |
| runs/reviewer_objection_matrix.json | 10421 | `d832da98c1e9aaadfe0711edc6fa3d57b9ba87759cfbd37d7ba78dc7371e5b6c` |
| runs/proposal_to_artifact_audit_2026-05-12.json | 8297 | `1853b38e57f0eada283ba5da8cdd2e16cad5e16d474b987abd6bcdc3d23c92a6` |
| runs/paper_stats.json | 1768945 | `982a927407be2bccabb8fa826c4586181927210b8497d964b493aaf8a9243c3b` |
| runs/paper_asset_freshness_audit.json | 23637 | `6a626f05ccf1b43ba80288bcfa4acc474c6520bdc3e2e99cc0af7c35da871e9b` |
| runs/remaining_experiment_queue.json | 30240 | `f98dd2014e9e616ba62632e35570fbe9725188efb49e96dff813fbae14f90122` |
| runs/remaining_experiment_preflight_audit.json | 18500 | `9b3a989ca07041e397185e2ec1adadcd83a4c37a91d5f3290d3912ff11c89265` |
| runs/open_blocker_claim_scope_audit.json | 7164 | `ac9091e081260d67715a45398fb64870b75c3afc5643359eba93987cfb2dc493` |
| paper/main.tex | 52312 | `55a12edc5427b5704ed3398137ca99c45947fc4956040093595338848176c486` |
| paper/refs.bib | 5639 | `2ca52c6d19659b7397109579dabfa21fa5536a83b80d6d8f907a15342f82fc1e` |
| paper/main.pdf | 415361 | `374e28e23c49df59f8a2398447ea8a720ef376128842a3fb958420a44a6ef178` |
| paper/main_submission.pdf | 320599 | `814a982a9e58d71248eabdf2a3532e87b2985569f79bb606564770ab7a7a540f` |
| paper/neurips_2026.sty | 13462 | `0c1ad36961fcd9198dcc2558cf2793e1df39973bde8264fd701f5e7970672757` |
| paper/neurips_checklist.tex | 6682 | `2b955470cf337a5bffb4867dca725917d97de78193bcb113837090c1993db217` |
| paper/neurips_submission.pdf | 331773 | `ec3b5f5c161d81a8c202d6598b845add63e8b018409531494139cabbcff193c0` |
| paper/iclr2026_conference.sty | 9025 | `a4852f68e080d6c5245057ca2039100b409e31727898aa93c03d78ddb84374a3` |
| paper/iclr2026_conference.bst | 26973 | `2d67552db7ed38ccfccb5957b52f95656e25c249724761d3cf5f7922ad1844c5` |
| paper/iclr_submission.pdf | 263029 | `6e45581ead217996a5a9893c91a7c68243d1fcc8e71fe52c6e56a7430a340703` |
| paper/tables/statistical_summary.tex | 32518 | `03125756250f7b1c6f37ae63493c591b34bfe4a005099926032cbcb3eba3cb49` |
| scripts/audit_mode_ticket_alignment_artifacts.py | 21120 | `075c8aeab29ca7b9b25c20b5643220085296c32a764b26a022d097591e3d939a` |
| scripts/audit_mask_artifact_posthoc_matching.py | 35055 | `3cbde03a342226555cb151803616b095640637923f72dadbfb0a9c0f47d7e52f` |
| scripts/audit_full_data_channel_permutation_matching.py | 25065 | `c5a8e9e1b2ee8652cefa5f008d1791742060c492d4fb43a4a010910dcb81337e` |
| scripts/audit_exhaustive_channel_permutation_feasibility.py | 16690 | `9b1d6ecb539b8b5d3f284a6b65e5d8a5bd453b98c083e8fc8a7f8c93881ddd48` |
| scripts/audit_mode_ticket_artifact_storage_budget.py | 11903 | `9715e298f946c568ec604d57f8bc8452ac6cbe5f52c6162e83b849b26596e7c0` |
| scripts/run_digits_fullnet_laplace_probe.py | 13450 | `32c58313f97bda606e99e98cfb7a90e0d307bbacc35d3980e8f7388044675779` |
| scripts/summarize_fullnet_laplace_probe.py | 8794 | `58419e9bb6358248d56a63ec197f381f6179441ec97b490efb494d8093069cde` |
| scripts/audit_linear_connectivity_barriers.py | 13607 | `bd7fa09e0777b18c1e3bc239323d74dd106f0641516a62f839387364d3e5b204` |
| scripts/audit_posterior_covariance_robustness.py | 22604 | `58a8d434fa3de340f6c884c4ff613dd6b5d203954537fc57db201787ad287e1e` |
| src/lottery/full_laplace.py | 7391 | `66228aea0415e59ba3d6565d70df79c57bb4c1926eadd3906187b157dc968bcc` |
| scripts/build_paper_claim_ledger.py | 76466 | `65be03802234f166586d81d630bc09eec1be08447502ee758937c5b29ea41384` |
| scripts/run_unit_smoke_tests.py | 8624 | `c9b34c9db4ac42958606e08caa92a4a6ecd79da0344fa27db5cfcd63f8afd6d7` |
| scripts/audit_paper_submission_shape.py | 12278 | `87846587fad6cb4129e6116114969e20cfbef6d15c183c20fe1d25a7ba63387c` |
| scripts/audit_submission_pdf_shape.py | 4342 | `5df3b27c78aa6c89dc7cedd78e980fda9a571ea865832f334f0a97fa6b2abd4c` |
| scripts/audit_paper_asset_freshness.py | 14374 | `6401305a20c736370e4d2e497d4f0656abee819c180d6d049cbea27023a6cd75` |
| scripts/build_remaining_experiment_queue.py | 15096 | `4e3bd5f1a528ab04e3b740259817c01abffdaa878249ea82097c54033fc54624` |
| scripts/audit_remaining_experiment_preflight.py | 17814 | `95a65532a11e2da56bd73eae06d2ba794304b9d1c6e3a2ab6180c6d8362b25df` |
| scripts/audit_open_blocker_claim_scope.py | 11873 | `581330fb993f6d451f8daa2fcf07e89e433c9d74f0dddeeeb3268eeb99cf5f06` |
| scripts/audit_venue_submission_compliance.py | 27902 | `3e3d74b3d9ff447aad9c5c4e805d3e394f8f5ab4395f4822f709b42eece8cc1a` |
| scripts/audit_iclr_submission_readiness.py | 23186 | `35ebecba300483f40ab9be82e013f0f8bde3286d4a3426a6615bf22280c5157b` |
| scripts/audit_ethics_statement.py | 6658 | `faeed021a42a023a0cc7df727e7db91912f93f4513c1e8c8d14b83020a5431b6` |
| scripts/audit_llm_usage_disclosure.py | 6629 | `091a6b3ee306ae8e70c8dd174239cd3bb868d4b9d58803a15c72d48d42cab724` |
| scripts/build_iclr_policy_watch_audit.py | 13892 | `850225a16a3ab87bcbf08c5a83af6ceb6f4486fe8202af788531a5fa637e0188` |
| scripts/build_iclr_openreview_packet.py | 13701 | `92ca4a1458013a90c1dd2b0cb161647a758d544ae7b2c947f759120fa5a204f4` |
| scripts/build_iclr_human_confirmation_template.py | 10183 | `f724b739c20c459eeba3a868627645b8556937adbc5392254ea85ce0110b054a` |
| scripts/audit_iclr_human_confirmation_receipt.py | 14718 | `af6180939a7bc0432fe3b2b20709d86c5d99a014133956f878203fee21b614e8` |
| scripts/build_venue_strategy_matrix.py | 34423 | `30a752b4aa1333e2d46d1d2028c5300786d81ffc2f16ce9150d8c6cabbbda51f` |
| scripts/build_formal_plagiarism_screening_runbook.py | 9771 | `c1e4a1ae9345ee7c8e679cda2f693781ae021ab50f70e8e9966e7e8aefe39fe1` |
| scripts/build_reviewer_objection_matrix.py | 26995 | `d68cdea6cef0fbdde3bc8279b21fd5ee5678976001f96ef9f6662d7fc15c3497` |
| scripts/build_proposal_to_artifact_audit.py | 24839 | `13fdcb7600ef8f92475702dd9fae960a2fd2547b591c98d22172ebfbcdc14438` |
| scripts/audit_external_validation_readiness.py | 27645 | `a8a0b7f0be2cced985be7f5992d2f6ba163d58e0b362b27857e2098bbf6c8e22` |
| scripts/build_external_validation_receipt_template.py | 12065 | `d20183b1b4ea2ca7defbf85363fcff6dd0803830c55562762e218641fb16212d` |
| scripts/update_external_validation_receipts.py | 10049 | `b882a7c845989650f45046eed4c285eb7eff5391390759498ea3f380e4d81b65` |
| scripts/build_external_validation_runbook.py | 15566 | `701d9325d9f0a6024b540b092a5c4d8cda1c8f7af1065c490371825b4fc4a8cd` |
| scripts/build_submission_handoff.py | 17359 | `f07ef996de9c375cf3b9a1ab84a7ce3b65229cb1c4f9d52e6035d9c1bb7d960e` |
| scripts/stage_public_repository_snapshot.py | 15679 | `0b8d0b13db2a26cb217738b32a42331acef52128900c269a97f893749f939afd` |
| scripts/smoke_public_repository_snapshot.py | 7076 | `3f19ea04e3b9b38dda07ce28034306e18908adf10ced4c62d30a2e3c9423b974` |
| scripts/verify_source_repository_snapshot.py | 13383 | `b6afcdd60315bafdf54ee38bb8e6b07bd1f08cea2c6215a67deca8cb05f16250` |
| scripts/audit_release_anonymization.py | 8042 | `42b06f7cd849c903df3ff6b2baf1c9a23c936c2b3f5b348feb417e923ea53b72` |
| scripts/build_public_release_archive.py | 11544 | `e285b16871910a68ec77fc34e54310677e8a5a6358805ba4608f3932c5584e0f` |
| scripts/smoke_public_release_archive.py | 9254 | `c480f1a9c7972c5005719b585bf5e4ae99c79c5c0d1f8b92da5db04cb611ccaf` |
| scripts/check_gpu_training_environment.py | 6063 | `9c507fc918e7c0038eb9af292aab42b25a2f627d1b2bc75612537a65610cb35c` |
| scripts/run_gpu_container_env_check.py | 2418 | `877136f81b1b6904b903f8de748a5bdca787cb38285831a4cb28b2865209d5a3` |
| scripts/build_local_gpu_container_validation.py | 6908 | `c9f6b2be14bb088dfaa620b65381c58c0cb3fd7f5f6668ffa7b66adbc2e7613b` |
| scripts/build_external_gpu_container_receipt.py | 14857 | `2dfa3286f1c0d5bbb1ccff817ad4868a73aa3802d153923255586b4180c68b76` |
| runs/cifar10_resnet20_full_covariance_feasibility.json | 6084 | `ef572b0733d9e6299bd8ea12146921b710e71c6c7f49e5183652708b40a3a1ac` |
| runs/digits_fullnet_laplace_tiny_r2_p0p3_summary.csv | 5704 | `25c9daa9df2b9446e47bffb38dd32ba9b7e51f073e6c5367191a03d721da6af6` |
| runs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke_summary.csv | 3679 | `6bdb5373f5fe0163c0647b38e6c00b136f8eb4c24497915c833339a7dd07f045` |
| runs/linear_connectivity_barrier_audit.csv | 9146 | `7d89083538c34e68d53eb54136c302992f7fa3f08474cd869a5f62fe02fa45d3` |
| runs/linear_connectivity_barrier_audit.json | 22718 | `07cde4f12d0b89412bf848106bd38aef8274ff009674f907dd905ff42fa8ab5a` |
| runs/posterior_covariance_robustness_audit.csv | 4264 | `8722067be7b082994abd8e63c3e6c5366d596972652a8350cfc944ceb77aa2a9` |
| runs/posterior_covariance_robustness_audit.json | 10394 | `60ac7cb413ca8d8cc593e0f60e3dc97ea2421af47dcac54682f74bdcf69a1734` |
| runs/cifar10_resnet20_long30_rewind1_lowrank_laplace_movement_selected_r5_p0p3_summary.csv | 3504 | `7ee0c848ca08059fe0e39e8b34fe6b19a3a3ffea9c9708eaf9df76e3cd1518f8` |
| runs/cifar10_resnet20_long30_rewind1_lowrank32_laplace_movement_selected_r5_p0p3_summary.csv | 3586 | `ae4be8214e2731f58a3c297d16e0431a09579dea8b1044133a2ca0e04330eb2f` |
| runs/cifar10_resnet20_long30_rewind1_lowrank64_laplace_movement_selected_r5_p0p3_summary.csv | 3560 | `e99758687b18659981c66eb35a216db48cd68e43e35c62fd578cba4840c5f587` |
| runs/cifar10_resnet20_long30_rewind1_lowrank128_laplace_movement_selected_r5_p0p3_summary.csv | 1643 | `3c2e0e5ed4e347784d26194c44dd37d990fc28329ea06dc7a544d4d508afc8b6` |
| runs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_selected_r5_p0p3_summary.csv | 2397 | `2a1e21c17b55e72b41589a47026f0f893eeb847f0c203e1bb412ce455cac6659` |
| runs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_max10k_selected_r5_p0p3_summary.csv | 2384 | `68fe14d9524410a63a1c64b5fc42a6d5b8767fbce572ba0800c4177c6135b23c` |
| runs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max10k_selected_r5_p0p3_summary.csv | 2392 | `fdcd9ba3865d14a5fca8d65be1d9d32ee24374a21fd2348ccf17b7e65a6a38cd` |
| runs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max20k_selected_r5_p0p3_summary.csv | 2403 | `66696179a81b9ddeb06ed10738e868b1ff54a89bf55a7de00c0ea0a93fb25db9` |
| runs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max40k_stream_selected_r5_p0p3_summary.csv | 2417 | `4ee97f479d458cc83b59758045fa86b68d4a4b58aa936cc3a3f6cf7edfd4bc91` |
| runs/cifar10_resnet20_long30_rewind1_hessian32_subspace_hmc_selected_r5_p0p3_summary.csv | 2172 | `cd8b0ccbf311533cd4f497ea61ccd35b665cc26c6a01e7f55baf6c55b5be8742` |
| runs/cifar10_resnet20_long30_rewind1_hard_concrete_selected_r5_p0p3_summary.csv | 2023 | `fa1e0f2e4a3a3dd531abb2f485541c81f8dcea193051d7e427499612bca3162b` |
| runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_weight_aligned_r5_p0p3_summary.csv | 2844 | `b0fe9556e52aef131a9dbb9a69c096a3022aeaf468c50654e1bad6901c14b8bc` |
| runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_independent_multichain_r5_p0p3_summary.csv | 1727 | `e1225b193eed60c474e768a560fbbb721f76eb82afbe101d4b18f0344dec7103` |
| runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_r5_p0p3_summary.csv | 1714 | `a6d1420d879f2d79cf7bf5b72a1333a15a58651ef912c89f3b8a4d2b86b246fa` |
| runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_r5_p0p3_summary.csv | 1748 | `de7cf26011b8f73b4b8f94f2eed2f8344d573c1fc5704fb3b24d7aa415edb776` |
| runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3_summary.csv | 2947 | `1761472b8ad898d2006c5f0effa4dac2c3e245104e680c3723946e7b22cd3d78` |
| runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3/20260506_230706/metrics.json | 80728 | `462d02873f9da2d697ceda64253f1f6e4234d4ebcc5b94448982c183a27750af` |
| runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3/20260506_230706/mask_artifacts.npz | 118946673 | `0918c8795ccc01f5896ac1b0ba6c181a415fef31a805990bbfd6fb81061a7843` |
| runs/fake_cifar10_mode_ticket_mask_artifact_smoke_summary.csv | 2724 | `1b242a8d392bdcdf1b0b3e4520b916385251ad5f180824ecc5fd1ecb9af1b507` |
| runs/cifar10_resnet20_long30_rewind1_residual_imp_process_stratified_exclusion_r5_p0p3_summary.csv | 3935 | `725da163f9a3048aa03982c6431294b90bee762ceda614ade5fe53ea54b43711` |
| runs/cifar10_resnet20_long30_rewind1_residual_imp_process_projection_r5_p0p3_summary.csv | 3873 | `4b29c114215fb1e258dcb284de9e3de39031bf61202d28f38a2c161642e42dde` |
| runs/cifar10_resnet20_long30_rewind1_residual_imp_process_posterior_projection_r5_p0p3_summary.csv | 3896 | `339e324e6ed8231cf6ee4f6fba3b3b809bdee9863117a89019a5db032e27bb5f` |
| runs/cifar10_resnet20_long30_rewind1_residual_imp_process_learned_subspace_r5_p0p3_summary.csv | 3930 | `7eed5700c5cd83e43776d062a7be4f43bf4dfe1a040ef4c60602e23dc23b0824` |

## Verification

```bash
make check
make paper-check
make paper-neurips-check
make paper-iclr-check
```

This file is generated by `scripts/build_release_manifest.py`.
