#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "top_conference_completion_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "top_conference_completion_audit.md"

INPUTS = {
    "submission_handoff": ROOT / "runs" / "submission_handoff.json",
    "iclr_readiness": ROOT / "runs" / "iclr_submission_readiness_audit.json",
    "paper_asset_freshness": ROOT / "runs" / "paper_asset_freshness_audit.json",
    "venue_strategy": ROOT / "runs" / "venue_strategy_matrix.json",
    "external_validation": ROOT / "runs" / "external_validation_readiness_audit.json",
    "public_archive": ROOT / "runs" / "public_release_archive_audit.json",
    "public_repository_snapshot": ROOT / "runs" / "public_repository_snapshot_audit.json",
    "locked_final_test": ROOT / "runs" / "locked_final_test_protocol_audit.json",
    "validation_bn_rerun_plan": ROOT / "runs" / "validation_bn_rerun_plan.json",
    "remaining_experiment_preflight": ROOT / "runs" / "remaining_experiment_preflight_audit.json",
    "validation_bn_smoke": ROOT / "runs" / "validation_bn_smoke_audit.json",
    "reference_integrity": ROOT / "runs" / "reference_integrity_audit.json",
    "manuscript_originality": ROOT / "runs" / "manuscript_originality_audit.json",
    "formal_plagiarism": ROOT / "runs" / "formal_plagiarism_screening_runbook.json",
    "formal_plagiarism_receipt": ROOT
    / "runs"
    / "formal_plagiarism_screening_receipt_audit.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    return parser.parse_args()


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json_or_empty(path: Path, risk_flags: list[str]) -> dict[str, Any]:
    if not path.exists():
        risk_flags.append(f"missing_input:{relpath(path)}")
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError:
        risk_flags.append(f"invalid_json:{relpath(path)}")
        return {}
    if not isinstance(payload, dict):
        risk_flags.append(f"non_object_json:{relpath(path)}")
        return {}
    return payload


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def open_flags(*payloads: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    for payload in payloads:
        for key in ["open_risk_flags", "risk_flags"]:
            values = payload.get(key, [])
            if isinstance(values, list):
                flags.extend(str(value) for value in values)
    return unique(flags)


def status(complete: bool, blocked: bool = False) -> str:
    if complete:
        return "complete"
    if blocked:
        return "blocked"
    return "partial"


def build_payload() -> dict[str, Any]:
    risk_flags: list[str] = []
    data = {name: load_json_or_empty(path, risk_flags) for name, path in INPUTS.items()}

    handoff = data["submission_handoff"]
    iclr = data["iclr_readiness"]
    paper_asset_freshness = data["paper_asset_freshness"]
    venue = data["venue_strategy"]
    external = data["external_validation"]
    archive = data["public_archive"]
    snapshot = data["public_repository_snapshot"]
    locked = data["locked_final_test"]
    rerun_plan = data["validation_bn_rerun_plan"]
    remaining_preflight = data["remaining_experiment_preflight"]
    bn_smoke = data["validation_bn_smoke"]
    reference = data["reference_integrity"]
    originality = data["manuscript_originality"]
    plagiarism = data["formal_plagiarism"]
    plagiarism_receipt = data["formal_plagiarism_receipt"]

    archive_sha = str(archive.get("archive_sha256", ""))
    source_commit = str(snapshot.get("git", {}).get("commit", ""))
    handoff_supplement = handoff.get("supplement_files", {})
    if isinstance(handoff_supplement, dict):
        if archive_sha and handoff_supplement.get("artifact_archive_sha256") != archive_sha:
            risk_flags.append("submission_handoff_archive_sha_mismatch")
        if source_commit and handoff_supplement.get("source_repository_snapshot_commit") != source_commit:
            risk_flags.append("submission_handoff_source_commit_mismatch")

    local_paper_packet_ready = bool(
        handoff.get("submission_handoff_ready") is True
        and iclr.get("iclr_submission_readiness_audit_ready") is True
        and iclr.get("provisional_strategy_ready") is True
        and paper_asset_freshness.get("paper_asset_freshness_audit_ready") is True
    )
    final_iclr_ready = iclr.get("iclr_submission_ready") is True
    venue_strategy_ready = venue.get("venue_strategy_matrix_ready") is True
    local_release_ready = bool(
        archive.get("archive_ready") is True
        and snapshot.get("public_repository_snapshot_ready") is True
        and external.get("local", {}).get("local_artifact_release_ready") is True
        and external.get("clean_repository_ready") is True
    )
    strict_external_ready = external.get("top_conference_release_ready") is True
    locked_final_ready = not locked.get("open_risk_flags") and locked.get(
        "locked_final_test_protocol_audit_ready"
    ) is True
    bn_full_cifar_ready = "full_cifar_bn_ablation_rerun_not_observed" not in set(
        str(flag) for flag in bn_smoke.get("open_risk_flags", [])
    )
    saved_artifact_reruns_ready = int(rerun_plan.get("observed_entry_count", 0)) >= int(
        rerun_plan.get("entry_count", 1)
    )
    remaining_preflight_ready = (
        remaining_preflight.get("remaining_experiment_preflight_audit_ready") is True
    )
    formal_screening_ready = plagiarism_receipt.get("formal_screening_completed") is True
    local_reference_screen_ready = bool(
        reference.get("reference_integrity_audit_ready") is True
        and originality.get("manuscript_originality_audit_ready") is True
    )

    deliverables = [
        {
            "deliverable": "Venue strategy",
            "required_evidence": "Primary and backup venue rationale generated from current submission audits.",
            "evidence": [
                "docs/venue_strategy_matrix.md",
                "runs/venue_strategy_matrix.json",
            ],
            "status": status(venue_strategy_ready),
            "blocking_gaps": []
            if venue_strategy_ready
            else ["venue_strategy_matrix_not_ready"],
        },
        {
            "deliverable": "Local paper packet",
            "required_evidence": "Compilable ICLR-style PDF, OpenReview packet, handoff metadata, ethics and LLM disclosures.",
            "evidence": [
                "paper/iclr_submission.pdf",
                "docs/iclr_openreview_packet.md",
                "docs/submission_handoff.md",
                "docs/paper_asset_freshness_audit.md",
                "docs/ethics_statement_audit.md",
                "docs/llm_usage_disclosure_audit.md",
            ],
            "status": status(local_paper_packet_ready),
            "blocking_gaps": []
            if local_paper_packet_ready
            else open_flags(paper_asset_freshness)
            or ["local_paper_packet_not_ready"],
        },
        {
            "deliverable": "Final venue submission gate",
            "required_evidence": "Official ICLR 2027 policy, author/COI confirmations, and OpenReview submission receipt.",
            "evidence": [
                "docs/iclr_policy_watch_audit.md",
                "docs/iclr_human_confirmation_template.md",
                "docs/iclr_human_confirmation_receipt_audit.md",
                "docs/iclr_submission_readiness_audit.md",
            ],
            "status": status(final_iclr_ready, blocked=True),
            "blocking_gaps": [
                flag
                for flag in iclr.get("open_risk_flags", [])
                if str(flag).startswith("iclr_")
                or str(flag).startswith("llm_usage")
            ],
        },
        {
            "deliverable": "Scientific protocol hardening",
            "required_evidence": "Locked final-test metrics, full-CIFAR BN ablations, and saved-artifact reruns for direct rows.",
            "evidence": [
                "docs/locked_final_test_protocol_audit.md",
                "docs/validation_bn_rerun_plan.md",
                "docs/remaining_experiment_queue.md",
                "docs/remaining_experiment_preflight_audit.md",
                "docs/validation_bn_smoke_audit.md",
            ],
            "status": status(
                locked_final_ready
                and bn_full_cifar_ready
                and saved_artifact_reruns_ready
                and remaining_preflight_ready,
                blocked=True,
            ),
            "blocking_gaps": unique(
                [
                    *[str(flag) for flag in locked.get("open_risk_flags", [])],
                    *[str(flag) for flag in bn_smoke.get("open_risk_flags", [])],
                    *[str(flag) for flag in rerun_plan.get("open_risk_flags", [])],
                    *[str(flag) for flag in remaining_preflight.get("risk_flags", [])],
                ]
            ),
        },
        {
            "deliverable": "Local reproducibility package",
            "required_evidence": "Anonymous archive, source-only repository snapshot, environment/container checks, and local smoke verification.",
            "evidence": [
                "docs/public_release_archive_audit.md",
                "docs/public_release_archive_smoke.md",
                "docs/public_repository_snapshot_audit.md",
                "docs/local_gpu_container_validation.md",
            ],
            "status": status(local_release_ready),
            "blocking_gaps": []
            if local_release_ready
            else ["local_release_or_source_snapshot_not_ready"],
        },
        {
            "deliverable": "Strict external validation",
            "required_evidence": "Public archive URL, public source repo, public CI, and independent external CUDA/GPU-container receipts for the current SHA/commit.",
            "evidence": [
                "docs/external_validation_readiness_audit.md",
                "docs/external_validation_receipt_template.md",
                "docs/external_validation_runbook.md",
            ],
            "status": status(strict_external_ready, blocked=True),
            "blocking_gaps": [str(flag) for flag in external.get("risk_flags", [])],
        },
        {
            "deliverable": "Originality and reference integrity",
            "required_evidence": "Local manuscript/reference audits plus formal external plagiarism-screening receipt.",
            "evidence": [
                "docs/reference_integrity_audit.md",
                "docs/manuscript_originality_audit.md",
                "docs/formal_plagiarism_screening_runbook.md",
                "docs/formal_plagiarism_screening_receipt_audit.md",
            ],
            "status": status(
                local_reference_screen_ready and formal_screening_ready,
                blocked=not formal_screening_ready,
            ),
            "blocking_gaps": []
            if formal_screening_ready
            else open_flags(plagiarism, plagiarism_receipt),
        },
    ]

    checklist = [
        {
            "explicit_requirement": "top conference level paper",
            "evidence": [
                "paper/iclr_submission.pdf",
                "runs/iclr_submission_readiness_audit.json",
                "runs/submission_handoff.json",
                "runs/paper_asset_freshness_audit.json",
            ],
            "coverage": "partial",
            "uncovered": [
                "official ICLR 2027 CFP not observed",
                "OpenReview author/COI/submission receipts absent",
            ],
        },
        {
            "explicit_requirement": "research results strong enough for review",
            "evidence": [
                "docs/paper_claim_ledger.md",
                "docs/reviewer_objection_matrix.md",
                "runs/paper_stats.json",
                "docs/validation_bn_rerun_plan.md",
            ],
            "coverage": "partial",
            "uncovered": [
                "locked final-test metrics",
                "full-CIFAR BatchNorm posterior-policy ablation",
                "seed-level saved artifacts for remaining direct rows",
            ],
        },
        {
            "explicit_requirement": "reproducible code and artifact",
            "evidence": [
                "runs/public_release_archive_audit.json",
                "runs/public_release_archive_smoke.json",
                "runs/public_repository_snapshot_audit.json",
                "runs/external_validation_readiness_audit.json",
            ],
            "coverage": "partial",
            "uncovered": [
                "public release upload receipt",
                "public repository receipt",
                "external CI receipt",
                "external GPU-container receipt",
            ],
        },
        {
            "explicit_requirement": "plagiarism, hallucinated reference, and logic risk checked",
            "evidence": [
                "runs/reference_integrity_audit.json",
                "runs/manuscript_originality_audit.json",
                "runs/formal_plagiarism_screening_runbook.json",
                "runs/formal_plagiarism_screening_receipt_audit.json",
            ],
            "coverage": "partial",
            "uncovered": ["formal external corpus-screening receipt"],
        },
        {
            "explicit_requirement": "completion audit before goal closure",
            "evidence": [
                "runs/top_conference_completion_audit.json",
                "docs/top_conference_completion_audit.md",
            ],
            "coverage": "covered",
            "uncovered": [],
        },
    ]

    open_blockers = unique(
        [
            *open_flags(
                iclr,
                paper_asset_freshness,
                venue,
                external,
                locked,
                bn_smoke,
                rerun_plan,
                plagiarism,
                plagiarism_receipt,
            ),
            *[gap for item in deliverables for gap in item.get("blocking_gaps", [])],
        ]
    )
    top_conference_goal_complete = bool(
        not risk_flags
        and all(item["status"] == "complete" for item in deliverables)
        and not open_blockers
    )

    return {
        "top_conference_completion_audit_ready": not risk_flags,
        "top_conference_goal_complete": top_conference_goal_complete,
        "must_not_mark_goal_complete": not top_conference_goal_complete,
        "risk_flags": risk_flags,
        "open_blockers": open_blockers,
        "objective_restatement": (
            "Produce a defensible top-conference submission package for the "
            "lottery-ticket Bayesian-modes research topic, including the paper, "
            "evidence, reproducibility artifact, venue handoff, and reviewer-risk "
            "closure gates."
        ),
        "current_authoritative_facts": {
            "primary_venue": "TMLR (rolling)",
            "first_backup": "ICLR 2027",
            "second_backup": "AISTATS 2027",
            "primary_submission_pdf": "paper/main_submission.pdf",
            "artifact_archive_sha256": archive_sha,
            "source_repository_snapshot_commit": source_commit,
            "external_validation_ready": external.get("external_validation_ready") is True,
            "top_conference_release_ready": strict_external_ready,
        },
        "deliverables": deliverables,
        "prompt_to_artifact_checklist": checklist,
        "input_artifacts": {name: relpath(path) for name, path in INPUTS.items()},
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def join_list(items: list[Any]) -> str:
    return "<br>".join(f"`{item}`" for item in items) if items else "none"


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    facts = payload["current_authoritative_facts"]
    status_text = "complete" if payload["top_conference_goal_complete"] else "not complete"
    lines = [
        "# Top-Conference Completion Audit",
        "",
        "This generated audit maps the active research objective to concrete",
        "paper, experiment, reproducibility, venue, and external-validation",
        "evidence. It is an operator gate, not a public release artifact.",
        "",
        f"Goal status: {status_text}.",
        f"Audit ready: {payload['top_conference_completion_audit_ready']}.",
        f"Must not mark goal complete: {payload['must_not_mark_goal_complete']}.",
        "",
        "## Objective Restatement",
        "",
        payload["objective_restatement"],
        "",
        "## Authoritative Facts",
        "",
        "| Fact | Value |",
        "| --- | --- |",
        f"| Primary venue | `{facts['primary_venue']}` |",
        f"| First backup | `{facts['first_backup']}` |",
        f"| Second backup | `{facts['second_backup']}` |",
        f"| Primary submission PDF | `{facts['primary_submission_pdf']}` |",
        f"| Artifact archive SHA256 | `{facts['artifact_archive_sha256']}` |",
        f"| Source snapshot commit | `{facts['source_repository_snapshot_commit']}` |",
        f"| External validation ready | {facts['external_validation_ready']} |",
        f"| Top-conference release ready | {facts['top_conference_release_ready']} |",
        "",
        "## Success Criteria",
        "",
        "| Deliverable | Status | Evidence | Blocking gaps |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["deliverables"]:
        lines.append(
            f"| {item['deliverable']} | {item['status']} | "
            f"{join_list(item['evidence'])} | {join_list(item['blocking_gaps'])} |"
        )
    lines.extend(
        [
            "",
            "## Prompt-To-Artifact Checklist",
            "",
            "| Explicit requirement | Coverage | Evidence | Uncovered requirement |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in payload["prompt_to_artifact_checklist"]:
        lines.append(
            f"| {item['explicit_requirement']} | {item['coverage']} | "
            f"{join_list(item['evidence'])} | {join_list(item['uncovered'])} |"
        )
    lines.extend(["", "## Open Blockers", ""])
    if payload["open_blockers"]:
        lines.extend(f"- {flag}" for flag in payload["open_blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Completion Decision", ""])
    if payload["top_conference_goal_complete"]:
        lines.append("The objective is complete and can be marked complete.")
    else:
        lines.append(
            "Do not mark the active goal complete. The local ICLR-oriented packet "
            "is substantial, but final venue submission, locked final-test, "
            "full-CIFAR BatchNorm ablation, strict external validation, and formal "
            "external plagiarism-screening evidence remain incomplete."
        )
    lines.extend(
        [
            "",
            "This file is generated by `scripts/build_top_conference_completion_audit.py`.",
        ]
    )
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
                "top_conference_completion_audit_ready": payload[
                    "top_conference_completion_audit_ready"
                ],
                "top_conference_goal_complete": payload["top_conference_goal_complete"],
                "open_blocker_count": len(payload["open_blockers"]),
                "risk_flags": payload["risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if not payload["top_conference_completion_audit_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
