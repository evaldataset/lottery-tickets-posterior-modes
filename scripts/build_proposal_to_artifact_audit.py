#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "proposal_to_artifact_audit_2026-05-12.json"
DEFAULT_OUT_MD = ROOT / "docs" / "proposal_to_artifact_audit.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Map the original lottery-ticket/Bayesian-mode proposal to the "
            "current evidence, paper claims, and remaining top-conference gaps."
        )
    )
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def finite(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    if not finite(value):
        return "n/a"
    number = float(value)
    if abs(number) < 0.001 and number != 0.0:
        return f"{number:.2e}"
    return f"{number:.{digits}f}"


def require(condition: bool, findings: list[str], message: str) -> None:
    if not condition:
        findings.append(message)


def first_row(rows: list[dict[str, Any]], **criteria: Any) -> dict[str, Any]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    raise KeyError(f"missing row with criteria: {criteria}")


def stat_mean(row: dict[str, Any], metric: str) -> float:
    value = row.get(metric, {}).get("mean")
    if not finite(value):
        raise ValueError(f"non-finite metric {metric}: {row}")
    return float(value)


def row_payload(
    rows: list[dict[str, Any]],
    *,
    proposal_item: str,
    current_resolution: str,
    status: str,
    evidence: list[str],
    key_numbers: str,
    remaining_gap: str,
) -> None:
    rows.append(
        {
            "proposal_item": proposal_item,
            "current_resolution": current_resolution,
            "status": status,
            "evidence": evidence,
            "key_numbers": key_numbers,
            "remaining_gap": remaining_gap,
        }
    )


def build_payload() -> dict[str, Any]:
    findings: list[str] = []
    proposal_path = ROOT / "proposal_A3_lottery_ticket_bayesian_modes.md"
    roadmap_path = ROOT / "docs" / "research_roadmap.md"
    paper_path = ROOT / "paper" / "main_tmlr.tex"
    if not paper_path.is_file():
        paper_path = ROOT / "paper" / "main.tex"
    stats_path = ROOT / "runs" / "paper_stats.json"
    claim_ledger_path = ROOT / "docs" / "paper_claim_ledger.md"
    posterior_cov_path = ROOT / "runs" / "posterior_covariance_robustness_audit.json"
    alignment_path = ROOT / "runs" / "mode_ticket_alignment_artifact_audit.json"
    channel_path = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_global_channel_audit.json"
    )
    exhaustive_path = ROOT / "runs" / "resnet_channel_permutation_exhaustive_feasibility_audit.json"
    handoff_path = ROOT / "runs" / "submission_handoff.json"
    external_readiness_path = ROOT / "runs" / "external_validation_readiness_audit.json"
    iclr_readiness_path = ROOT / "runs" / "iclr_submission_readiness_audit.json"
    venue_strategy_path = ROOT / "runs" / "venue_strategy_matrix.json"

    required_files = [
        proposal_path,
        roadmap_path,
        paper_path,
        stats_path,
        claim_ledger_path,
        posterior_cov_path,
        alignment_path,
        channel_path,
        exhaustive_path,
        handoff_path,
        external_readiness_path,
        iclr_readiness_path,
        venue_strategy_path,
    ]
    for path in required_files:
        require(path.is_file(), findings, f"missing_required_file:{rel(path)}")

    proposal_text = read_text(proposal_path)
    roadmap_text = read_text(roadmap_path)
    paper_text = read_text(paper_path)
    stats = load_json(stats_path)
    posterior_cov = load_json(posterior_cov_path)
    alignment = load_json(alignment_path)
    channel = load_json(channel_path)
    exhaustive = load_json(exhaustive_path)
    handoff = load_json(handoff_path)
    external_readiness = load_json(external_readiness_path)
    iclr_readiness = load_json(iclr_readiness_path)
    venue_strategy = load_json(venue_strategy_path)

    proposal_snippets = [
        "Lottery Ticket",
        "Bayesian",
        "SGLD",
        "cyclical SGLD",
        "HMC",
        "KS test",
        "MMD",
        "2-Wasserstein",
        "Variational Pruning",
        "calibration",
    ]
    missing_proposal_snippets = [
        snippet for snippet in proposal_snippets if snippet not in proposal_text
    ]
    require(
        not missing_proposal_snippets,
        findings,
        f"proposal_missing_expected_snippets:{missing_proposal_snippets}",
    )
    require(
        "Source proposal: `proposal_A3_lottery_ticket_bayesian_modes.md`"
        in roadmap_text,
        findings,
        "roadmap_does_not_reference_source_proposal",
    )
    require(
        "Winning Tickets Are Not Posterior Modes" in paper_text,
        findings,
        "paper_title_does_not_reflect_negative_reframe",
    )

    mode_rows = stats.get("mode_distribution_equivalence", [])
    random_rows = [row for row in mode_rows if row.get("comparison") == "posterior-random"]
    random_wins = [
        row for row in random_rows if row.get("verdict") == "posterior separates from random"
    ]
    chain_rows = [row for row in mode_rows if row.get("comparison") == "posterior-chain"]
    chain_wins = [row for row in chain_rows if float(row.get("delta_mean", 0.0)) > 0.005]
    rewind_rows = [row for row in mode_rows if row.get("comparison") == "posterior-rewind"]
    rewind_beats = [row for row in rewind_rows if float(row.get("delta_mean", 0.0)) < -0.005]
    require(len(random_rows) == 59 and len(random_wins) == 58, findings, "mode_random_counts_changed")
    require(len(chain_rows) == 59 and not chain_wins, findings, "mode_chain_control_counts_changed")
    require(len(rewind_rows) == 57 and len(rewind_beats) == 55, findings, "mode_rewind_counts_changed")

    direct_rows = stats.get("direct_mode_ticket_distribution", [])
    direct_sample_criteria = [
        ("CIFAR full ResNet", "posterior_samples_vs_tickets"),
        ("CIFAR full aligned", "activation_aligned_posterior_samples_vs_tickets"),
        ("CIFAR full weight-aligned", "weight_aligned_posterior_samples_vs_tickets"),
        ("CIFAR full cSGLD multi-chain", "posterior_samples_vs_tickets"),
        ("CIFAR full cSGLD independent", "posterior_samples_vs_tickets"),
        ("CIFAR full LowRank128Lap", "posterior_samples_vs_tickets"),
        ("CIFAR full JointDiagLap270k", "posterior_samples_vs_tickets"),
    ]
    direct_sample_rows = [
        first_row(direct_rows, setting=setting, comparison=comparison)
        for setting, comparison in direct_sample_criteria
    ]
    one_cluster_count = sum(
        1 for row in direct_sample_rows if int(float(row.get("posterior_num_clusters", -1))) == 1
    )
    failing_layer_ks = sum(
        1 for row in direct_sample_rows if float(row.get("layer_ks_pvalue", 1.0)) < 0.001
    )
    failing_hamming = sum(
        1
        for row in direct_sample_rows
        if row.get("hamming_overlap") is not None
        and float(row.get("hamming_overlap", 1.0)) < 0.70
    )
    lowrank_row = first_row(
        direct_rows,
        setting="CIFAR full LowRank128Lap",
        comparison="posterior_samples_vs_tickets",
    )
    jointdiag_row = first_row(
        direct_rows,
        setting="CIFAR full JointDiagLap270k",
        comparison="posterior_samples_vs_tickets",
    )
    require(one_cluster_count == 7, findings, "direct_rows_do_not_all_collapse_to_one_cluster")
    require(failing_layer_ks == 7, findings, "direct_rows_do_not_all_fail_layer_ks")
    require(failing_hamming == 6, findings, "direct_hamming_failure_count_changed")

    variational_rows = stats.get("variational_pruning", [])
    var_digits = first_row(variational_rows, source="variational_prune")
    imp_digits = first_row(variational_rows, source="imp")
    calibration_rows = stats.get("calibration_ood", [])
    var_cifar = first_row(calibration_rows, source="variational_prune")
    imp_cifar = first_row(calibration_rows, source="imp")
    require(stat_mean(var_digits, "accuracy_minus_imp") < 0.0, findings, "digits_variational_not_below_imp")
    require(stat_mean(var_cifar, "id_accuracy") < stat_mean(imp_cifar, "id_accuracy"), findings, "cifar_variational_not_below_imp_accuracy")
    require(stat_mean(var_cifar, "ood_msp_auroc") < stat_mean(imp_cifar, "ood_msp_auroc"), findings, "cifar_variational_not_below_imp_auroc")

    learned_rows = stats.get("trajectory_mask_training", [])
    learned_sources = ["gem_miner", "variational_prune", "hard_concrete"]
    learned = {source: first_row(learned_rows, source=source) for source in learned_sources}
    imp_learned = first_row(learned_rows, source="imp")
    require(
        all(stat_mean(row, "source_to_imp") < 0.10 for row in learned.values()),
        findings,
        "learned_mask_support_not_random_scale",
    )
    require(
        all(stat_mean(row, "trained_accuracy") < stat_mean(imp_learned, "trained_accuracy") for row in learned.values()),
        findings,
        "learned_mask_accuracy_not_below_imp",
    )

    movement_samplers = sorted({row.get("sampler") for row in stats.get("movement", [])})
    required_samplers = {
        "SGLD",
        "SGHMC",
        "cSGLD",
        "SWAG20",
        "DiagLap",
        "KFACLap",
        "LowRankLap",
        "LowRank32Lap",
        "LowRank64Lap",
        "LowRank128Lap",
    }
    require(required_samplers.issubset(set(movement_samplers)), findings, "posterior_sampler_coverage_missing")
    require(bool(stats.get("subspace_hmc")), findings, "subspace_hmc_section_empty")
    cov_checks = posterior_cov.get("interpretation_checks", {})
    require(cov_checks.get("posterior_covariance_robustness_ready") is True, findings, "posterior_covariance_audit_not_ready")
    require(cov_checks.get("dense_full_covariance_infeasible") is True, findings, "dense_full_covariance_not_bounded")

    alignment_overall = alignment.get("overall", {})
    channel_overall = channel.get("overall", {})
    exhaustive_overall = exhaustive.get("overall", {})
    require(alignment_overall.get("any_direct_equivalence_pass") is False, findings, "alignment_audit_equivalence_passed_unexpectedly")
    require(channel_overall.get("global_channel_coordinate_descent_supported") is True, findings, "global_channel_audit_not_supported")
    require(exhaustive_overall.get("stage1_coordinate_descent_all_exact") is True, findings, "stage1_exact_audit_not_exact")
    require(exhaustive_overall.get("full_exhaustive_channel_permutation_supported") is False, findings, "full_exhaustive_channel_unexpectedly_supported")

    metric_keys = {
        "layer_ks_pvalue",
        "layer_mmd_rbf",
        "layer_sliced_wasserstein",
        "hamming_overlap",
        "hungarian_cost",
        "logit_cka_hungarian_mean",
        "activation_cka_hungarian_mean",
        "posterior_cluster_entropy_nats",
    }
    require(metric_keys.issubset(set(direct_sample_rows[0])), findings, "direct_probe_metrics_missing")
    venue_decision = venue_strategy.get("decision", {})
    require(venue_strategy.get("venue_strategy_matrix_ready") is True, findings, "venue_strategy_matrix_not_ready")
    require(venue_decision.get("primary_target") == "TMLR (rolling)", findings, "venue_strategy_primary_not_tmlr")
    require(venue_decision.get("first_backup") == "ICLR 2027", findings, "venue_strategy_backup_not_iclr")

    rows: list[dict[str, Any]] = []
    row_payload(
        rows,
        proposal_item="Source proposal and thesis reframing",
        current_resolution=(
            "The positive 1:1 mode-ticket thesis has been reframed as a scoped "
            "negative support-equivalence paper."
        ),
        status="covered_negative_reframe",
        evidence=[rel(proposal_path), rel(roadmap_path), rel(paper_path)],
        key_numbers="paper title and roadmap both state the negative posterior-mode resolution",
        remaining_gap="Venue editing can tighten wording, but the claim direction is settled in the current draft.",
    )
    row_payload(
        rows,
        proposal_item="H1: lottery tickets correspond one-to-one to posterior modes",
        current_resolution="Falsified under the current support-distribution and direct mode/ticket tests.",
        status="falsified_current_artifacts",
        evidence=[rel(stats_path), rel(claim_ledger_path)],
        key_numbers=(
            f"posterior>random {len(random_wins)}/{len(random_rows)}; "
            f"posterior>chain by >0.005 {len(chain_wins)}/{len(chain_rows)}; "
            f"rewind>posterior by >0.005 {len(rewind_beats)}/{len(rewind_rows)}; "
            f"direct CIFAR sample rows one-cluster {one_cluster_count}/7, "
            f"layer-KS failures {failing_layer_ks}/7, hamming failures {failing_hamming}/7"
        ),
        remaining_gap="Exact dense full-covariance CIFAR posterior evidence is infeasible locally and remains bounded rather than closed.",
    )
    row_payload(
        rows,
        proposal_item="H2: posterior mode count determines ticket diversity",
        current_resolution=(
            "Unsupported: full-data direct posterior rows collapse to one posterior basin while IMP keeps seed-level ticket diversity."
        ),
        status="unsupported_current_artifacts",
        evidence=[rel(stats_path), rel(roadmap_path)],
        key_numbers=(
            f"direct sample rows with one posterior cluster {one_cluster_count}/7; "
            f"LowRank128Lap p={fmt(lowrank_row['layer_ks_pvalue'])}, "
            f"hamming={fmt(lowrank_row['hamming_overlap'])}; "
            f"JointDiag270k p={fmt(jointdiag_row['layer_ks_pvalue'])}, "
            f"hamming={fmt(jointdiag_row['hamming_overlap'])}"
        ),
        remaining_gap="A different exact posterior method could be proposed, but current covariance-fidelity trend does not point toward rescue.",
    )
    row_payload(
        rows,
        proposal_item="H3: variational mode-finding pruning should match accuracy and improve calibration",
        current_resolution=(
            "Partially implemented and negative for the paper claim: variational pruning can lower ECE but loses accuracy, Brier, OOD AUROC, and ticket support."
        ),
        status="covered_negative",
        evidence=[rel(stats_path), rel(claim_ledger_path)],
        key_numbers=(
            f"digits variational accuracy-IMP {fmt(stat_mean(var_digits, 'accuracy_minus_imp'))}; "
            f"digits support-to-IMP {fmt(stat_mean(var_digits, 'source_to_imp'))}; "
            f"CIFAR variational acc/AUROC {fmt(stat_mean(var_cifar, 'id_accuracy'))}/"
            f"{fmt(stat_mean(var_cifar, 'ood_msp_auroc'))} vs IMP "
            f"{fmt(stat_mean(imp_cifar, 'id_accuracy'))}/{fmt(stat_mean(imp_cifar, 'ood_msp_auroc'))}"
        ),
        remaining_gap="Do not expand into a broad pruning benchmark unless reviewers ask; the current baseline is enough for the scoped negative claim.",
    )
    row_payload(
        rows,
        proposal_item="H4: random-weight networks as prior mode finding",
        current_resolution=(
            "Bounded by learned-mask controls rather than developed into a separate Ramanujan-style study."
        ),
        status="bounded_negative",
        evidence=[rel(stats_path), rel(roadmap_path)],
        key_numbers=(
            "full-data learned-mask support-to-IMP: "
            + ", ".join(
                f"{source}={fmt(stat_mean(learned[source], 'source_to_imp'))}"
                for source in learned_sources
            )
            + f"; IMP accuracy {fmt(stat_mean(imp_learned, 'trained_accuracy'))}"
        ),
        remaining_gap="A full random-weight-network replication is de-scoped; the submitted paper should state this as out of scope.",
    )
    row_payload(
        rows,
        proposal_item="Posterior sampler and covariance-fidelity ladder",
        current_resolution=(
            "Covered across stochastic samplers, SWAG, Laplace variants, subspace HMC, and covariance-fidelity audits."
        ),
        status="covered_with_bounded_limitation",
        evidence=[rel(stats_path), rel(posterior_cov_path)],
        key_numbers=(
            f"movement samplers={', '.join(movement_samplers)}; "
            f"covariance movement rows={cov_checks.get('movement_row_count')}; "
            f"direct rows={cov_checks.get('direct_row_count')}; "
            f"dense full covariance memory={fmt(posterior_cov.get('dense_feasibility', {}).get('dense_precision_float64_gib'))} GiB"
        ),
        remaining_gap="Literal dense full-covariance CIFAR posterior is outside the single-workstation memory budget.",
    )
    row_payload(
        rows,
        proposal_item="Proposal metrics: KS, MMD, Wasserstein, Hamming, CKA, Hungarian, basin entropy",
        current_resolution="Implemented in direct mode/ticket distribution probes and summarized into paper statistics.",
        status="covered",
        evidence=[rel(stats_path), "scripts/run_mode_ticket_distribution_probe.py"],
        key_numbers="required direct metric keys present in the current CIFAR direct rows",
        remaining_gap="Metric interpretation should remain explicit: function-space CKA alone is not enough for H1.",
    )
    row_payload(
        rows,
        proposal_item="Permutation and alignment risk",
        current_resolution=(
            "First-order activation/weight alignment is negative; saved-artifact record matching and global channel audits bound the post-hoc issue."
        ),
        status="bounded_open_limitation",
        evidence=[rel(alignment_path), rel(channel_path), rel(exhaustive_path)],
        key_numbers=(
            f"aligned rows fail layer-KS={alignment_overall.get('aligned_rows_all_fail_layer_ks')}; "
            f"global channel supported={channel_overall.get('global_channel_coordinate_descent_supported')}; "
            f"stage-1 exact assignments={exhaustive_overall.get('stage1_exact_permutation_count')}; "
            f"full search log10 assignments={fmt(exhaustive_overall.get('full_log10_permutation_count'), 1)}"
        ),
        remaining_gap="Exhaustive full-data graph/channel search is infeasible and unimplemented.",
    )
    row_payload(
        rows,
        proposal_item="Top-conference venue targeting",
        current_resolution=(
            "Venue triage is now explicit: TMLR (rolling) is the primary "
            "target with a fully prepared local packet, ICLR 2027 and AISTATS "
            "2027 are high-visibility backups, and faster CIKM/EMNLP deadlines "
            "are rejected unless the paper is substantially rescoped."
        ),
        status="venue_target_selected",
        evidence=[rel(venue_strategy_path), rel(iclr_readiness_path), rel(handoff_path)],
        key_numbers=(
            f"primary={venue_decision.get('primary_target')}; "
            f"backup1={venue_decision.get('first_backup')}; "
            f"backup2={venue_decision.get('second_backup')}"
        ),
        remaining_gap=(
            "Author OpenReview/COI/ethics confirmations and the external "
            "CUDA-host GPU-container receipt must still be recorded before "
            "TMLR upload; official ICLR 2027 CFP/Author Guide observation "
            "remains the backup-venue blocker."
        ),
    )
    row_payload(
        rows,
        proposal_item="Submission and reproducibility state",
        current_resolution=(
            "Local TMLR and ICLR-style manuscript packets, OpenReview paste packets, anonymous archive, source snapshot, locked final-test, full-CIFAR BN policy ablations, saved-artifact reruns, and the TinyCNN architecture-generality cell are ready; remaining blockers are author OpenReview profile/COI/ethics/LLM confirmations, formal external plagiarism screening, and public release/CI/GPU receipts (all external/author actions)."
        ),
        status="external_blocked",
        evidence=[
            rel(handoff_path),
            rel(external_readiness_path),
            rel(iclr_readiness_path),
            rel(venue_strategy_path),
        ],
        key_numbers=(
            f"venue={handoff.get('metadata', {}).get('venue')}; "
            f"submission_handoff_ready={handoff.get('submission_handoff_ready')}; "
            f"iclr_submission_ready={iclr_readiness.get('iclr_submission_ready')}; "
            f"top_conference_release_ready={external_readiness.get('top_conference_release_ready')}"
        ),
        remaining_gap=", ".join(
            str(item)
            for item in [
                *iclr_readiness.get("open_risk_flags", []),
                *external_readiness.get("risk_flags", []),
            ]
        ),
    )

    open_rows = [
        row
        for row in rows
        if row["status"] in {"bounded_open_limitation", "external_blocked", "covered_with_bounded_limitation"}
    ]
    return {
        "proposal_to_artifact_audit_verified": not findings,
        "goal_complete": (
            iclr_readiness.get("iclr_submission_ready") is True
            and external_readiness.get("top_conference_release_ready") is True
        ),
        "source_proposal": rel(proposal_path),
        "paper": rel(paper_path),
        "row_count": len(rows),
        "open_or_bounded_row_count": len(open_rows),
        "findings": findings,
        "rows": rows,
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Proposal To Artifact Audit",
        "",
        "This audit maps `proposal_A3_lottery_ticket_bayesian_modes.md` to the current evidence and submission state.",
        "",
        f"- Verified: {payload['proposal_to_artifact_audit_verified']}",
        f"- Goal complete: {payload['goal_complete']}",
        f"- Rows: {payload['row_count']}",
        f"- Open or bounded rows: {payload['open_or_bounded_row_count']}",
        "",
        "## Rows",
        "",
        "| Proposal item | Status | Current resolution | Key numbers | Remaining gap |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| "
            + " | ".join(
                str(row[key]).replace("\n", " ")
                for key in [
                    "proposal_item",
                    "status",
                    "current_resolution",
                    "key_numbers",
                    "remaining_gap",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Findings", ""])
    lines.extend(f"- {item}" for item in payload["findings"] or ["none"])
    lines.extend(["", "This file is generated by `scripts/build_proposal_to_artifact_audit.py`."])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_payload()
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "proposal_to_artifact_audit_verified": payload[
                    "proposal_to_artifact_audit_verified"
                ],
                "goal_complete": payload["goal_complete"],
                "row_count": payload["row_count"],
                "open_or_bounded_row_count": payload["open_or_bounded_row_count"],
                "findings": payload["findings"],
                "out_json": rel(args.out_json),
                "out_md": rel(args.out_md),
            },
            ensure_ascii=False,
        )
    )
    if args.strict and not payload["proposal_to_artifact_audit_verified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
