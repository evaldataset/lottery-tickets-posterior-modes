#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOP_AUDIT = ROOT / "runs" / "top_conference_completion_audit.json"
DEFAULT_OUT_JSON = ROOT / "runs" / "open_blocker_claim_scope_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "open_blocker_claim_scope_audit.md"

SCAN_PATHS = [
    ROOT / "paper" / "main.tex",
    ROOT / "docs" / "iclr_submission_readiness_audit.md",
    ROOT / "docs" / "venue_strategy_matrix.md",
    ROOT / "docs" / "locked_final_test_protocol_audit.md",
    ROOT / "docs" / "remaining_experiment_queue.md",
    ROOT / "docs" / "remaining_experiment_preflight_audit.md",
    ROOT / "docs" / "external_validation_readiness_audit.md",
    ROOT / "docs" / "formal_plagiarism_screening_receipt_audit.md",
    ROOT / "docs" / "manuscript_originality_audit.md",
    ROOT / "docs" / "reviewer_objection_matrix.md",
]

GROUPS = [
    {
        "group": "final_venue_submission",
        "blockers": [
            "iclr_2027_official_cfp_not_observed",
            "iclr_2027_official_author_guide_not_observed",
            "iclr_openreview_author_profile_and_coi_not_recorded",
            "iclr_openreview_submission_receipt_not_observed",
            "iclr_code_of_ethics_author_acknowledgement_not_recorded",
            "llm_usage_disclosure_author_confirmation_not_recorded",
        ],
        "required_phrases": [
            "official ICLR 2027 call has not been observed",
            "official 2027 CFP 미관측",
            "author/COI",
            "ethics/LLM author confirmations",
        ],
        "mitigation_type": "operator_submission_gate",
    },
    {
        "group": "locked_final_test",
        "blockers": [
            "locked_final_test_metrics_not_observed",
            "locked_final_test_rerun_not_observed",
        ],
        "required_phrases": [
            "locked final test rerun is still required",
            "diagnostic falsification evidence rather than final model-selection evidence",
            "locked_final_test_sgld_full_cifar",
        ],
        "mitigation_type": "paper_limitation_and_run_queue",
    },
    {
        "group": "batchnorm_policy_ablation",
        "blockers": [
            "full_cifar_bn_ablation_rerun_not_observed",
            "bn_policy_cifar_ablation_not_observed",
        ],
        "required_phrases": [
            "BatchNorm buffers in sampled state dictionaries",
            "full CIFAR sensitivity runs remain to be completed",
            "bn_recalibrate_csgld_full_cifar",
        ],
        "mitigation_type": "paper_limitation_and_run_queue",
    },
    {
        "group": "saved_artifact_seed_level_reruns",
        "blockers": [
            "seed_level_saved_artifacts_incomplete_for_other_direct_rows",
            "seed_level_saved_artifact_reruns_not_observed",
        ],
        "required_phrases": [
            "Pooled direct mode/ticket p-values over posterior samples are descriptive",
            "saved-mask reruns",
            "saved_artifacts_jointdiag",
        ],
        "mitigation_type": "paper_limitation_and_run_queue",
    },
    {
        "group": "strict_external_validation",
        "blockers": [
            "public_release_upload_not_verified",
            "public_repository_state_not_verified",
            "external_ci_run_not_observed",
            "external_gpu_container_run_not_observed",
        ],
        "required_phrases": [
            "lacks public archive, public repository, external CI, and external GPU-run receipts",
            "public_release_upload_not_verified",
            "external_gpu_container_run_not_observed",
        ],
        "mitigation_type": "paper_reproducibility_caveat_and_external_runbook",
    },
    {
        "group": "formal_external_screening",
        "blockers": ["formal_external_plagiarism_database_screen_not_performed"],
        "required_phrases": [
            "not a formal plagiarism detector",
            "formal_external_plagiarism_database_screen_not_performed",
            "Formal screening completed: False",
        ],
        "mitigation_type": "operator_screening_gate",
    },
    {
        "group": "backup_venue_cfp_watch",
        "blockers": [
            "aistats_2027_official_cfp_not_observed",
            "aaai_2027_official_cfp_not_observed",
            "wsdm_2027_official_cfp_not_observed",
            "www_2027_official_cfp_not_observed",
        ],
        "required_phrases": [
            "Official AISTATS 2027 CFP is not observed",
            "Official AAAI 2027 CFP is not observed",
            "not a 2027 paper CFP",
            "A 2027 research-track CFP is not observed",
        ],
        "mitigation_type": "venue_watch_gate",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-audit-json", type=Path, default=DEFAULT_TOP_AUDIT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    return parser.parse_args()


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def read_scan_texts() -> tuple[str, list[str], list[str]]:
    texts: list[str] = []
    present: list[str] = []
    missing: list[str] = []
    for path in SCAN_PATHS:
        if not path.exists():
            missing.append(relpath(path))
            continue
        texts.append(path.read_text(encoding="utf-8"))
        present.append(relpath(path))
    return "\n".join(texts), present, missing


def build_payload(top_audit_json: Path) -> dict[str, Any]:
    top = load_json(top_audit_json)
    open_blockers = [str(flag) for flag in top.get("open_blockers", [])]
    open_set = set(open_blockers)
    scan_text, scanned_paths, missing_scan_paths = read_scan_texts()
    normalized = " ".join(scan_text.split())
    group_rows: list[dict[str, Any]] = []
    risk_flags: list[str] = []
    grouped_blockers: set[str] = set()

    for group in GROUPS:
        blockers = [flag for flag in group["blockers"] if flag in open_set]
        grouped_blockers.update(str(flag) for flag in group["blockers"])
        active = bool(blockers)
        phrase_checks = [
            {"phrase": phrase, "present": phrase in normalized}
            for phrase in group["required_phrases"]
        ]
        missing_phrases = [
            check["phrase"] for check in phrase_checks if active and not check["present"]
        ]
        if missing_phrases:
            risk_flags.append(f"{group['group']}_scope_mitigation_missing")
        group_rows.append(
            {
                "group": group["group"],
                "mitigation_type": group["mitigation_type"],
                "active": active,
                "open_blockers": blockers,
                "required_phrase_checks": phrase_checks,
                "missing_required_phrases": missing_phrases,
                "mitigation_documented": active and not missing_phrases,
            }
        )

    ungrouped_open_blockers = sorted(open_set - grouped_blockers)
    if ungrouped_open_blockers:
        risk_flags.append("ungrouped_open_blockers")
    if missing_scan_paths:
        risk_flags.append("scope_scan_paths_missing")

    return {
        "open_blocker_claim_scope_audit_ready": not risk_flags,
        "not_blocker_closure_evidence": True,
        "top_audit_json": relpath(top_audit_json),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_conference_goal_complete": bool(top.get("top_conference_goal_complete")),
        "open_blocker_count": len(open_blockers),
        "scanned_paths": scanned_paths,
        "missing_scan_paths": missing_scan_paths,
        "groups": group_rows,
        "ungrouped_open_blockers": ungrouped_open_blockers,
        "risk_flags": risk_flags,
        "open_risk_flags": open_blockers,
        "interpretation": {
            "all_open_blockers_have_scope_mitigation": not risk_flags,
            "paper_or_operator_docs_keep_claims_scoped": not risk_flags,
            "audit_does_not_reduce_scientific_or_external_blockers": True,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Open Blocker Claim-Scope Audit",
        "",
        f"Ready: `{payload['open_blocker_claim_scope_audit_ready']}`.",
        f"Not blocker closure evidence: `{payload['not_blocker_closure_evidence']}`.",
        f"Top audit: `{payload['top_audit_json']}`.",
        f"Open blocker count: `{payload['open_blocker_count']}`.",
        "",
        "This audit checks whether each still-open submission blocker is explicitly",
        "reflected in the paper limitations or operator-facing submission docs. It",
        "does not claim that any blocker is closed.",
        "",
        "## Group Coverage",
        "",
        "| Group | Active | Mitigation type | Documented | Open blockers | Missing phrases |",
        "| --- | ---: | --- | ---: | --- | --- |",
    ]
    for row in payload["groups"]:
        blockers = "<br>".join(f"`{flag}`" for flag in row["open_blockers"]) or "none"
        missing = "<br>".join(f"`{phrase}`" for phrase in row["missing_required_phrases"]) or "none"
        lines.append(
            "| {group} | {active} | {mitigation_type} | {documented} | {blockers} | {missing} |".format(
                group=row["group"],
                active=row["active"],
                mitigation_type=row["mitigation_type"],
                documented=row["mitigation_documented"],
                blockers=blockers,
                missing=missing,
            )
        )
    lines.extend(["", "## Scanned Paths", ""])
    lines.extend(f"- `{path}`" for path in payload["scanned_paths"])
    if payload["ungrouped_open_blockers"]:
        lines.extend(["", "## Ungrouped Open Blockers", ""])
        lines.extend(f"- `{flag}`" for flag in payload["ungrouped_open_blockers"])
    if payload["risk_flags"]:
        lines.extend(["", "## Risk Flags", ""])
        lines.extend(f"- `{flag}`" for flag in payload["risk_flags"])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Active blockers remain active until the required experiment, receipt, or venue event is actually observed.",
            "- This gate only prevents stale or overconfident prose from drifting away from the blocker ledger.",
            "",
            "This file is generated by `scripts/audit_open_blocker_claim_scope.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_payload(args.top_audit_json)
    write_json(args.out_json, payload)
    write_markdown(args.out_md, payload)
    print(
        json.dumps(
            {
                "open_blocker_claim_scope_audit_ready": payload[
                    "open_blocker_claim_scope_audit_ready"
                ],
                "open_blocker_count": payload["open_blocker_count"],
                "risk_flags": payload["risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            },
            sort_keys=True,
        )
    )
    if payload["risk_flags"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
