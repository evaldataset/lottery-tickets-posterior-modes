#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "formal_plagiarism_screening_runbook.json"
DEFAULT_OUT_MD = ROOT / "docs" / "formal_plagiarism_screening_runbook.md"

DEFAULT_TARGETS = [
    ("primary_iclr_submission_pdf", ROOT / "paper" / "iclr_submission.pdf"),
    ("main_submission_pdf", ROOT / "paper" / "main_submission.pdf"),
    ("paper_source_tex", ROOT / "paper" / "main.tex"),
    ("bibliography_source_bib", ROOT / "paper" / "refs.bib"),
]

REQUIRED_RECEIPT_FIELDS = [
    "schema_version",
    "screening_tool_or_vendor",
    "screening_report_id_or_url",
    "screening_report_export_sha256_or_private_location",
    "screened_file_path",
    "screened_file_sha256",
    "screened_date_utc",
    "operator",
    "screening_database_or_corpus",
    "external_corpus_searched",
    "total_similarity_percent",
    "max_single_source_similarity_percent",
    "top_matched_sources",
    "excluded_sources_or_filters",
    "human_review_disposition",
    "material_matches_reviewed",
    "self_overlap_or_prior_version_reviewed",
    "pass",
    "notes",
]


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(role: str, path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "role": role,
        "path": relpath(path),
        "exists": path.exists(),
    }
    if path.exists():
        record.update(
            {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return record


def build_payload() -> dict[str, Any]:
    targets = [file_record(role, path) for role, path in DEFAULT_TARGETS]
    missing_targets = [target["path"] for target in targets if target["exists"] is not True]
    risk_flags = []
    if missing_targets:
        risk_flags.append("formal_plagiarism_screening_target_missing")
    return {
        "formal_plagiarism_screening_runbook_ready": not risk_flags,
        "formal_screening_completed": False,
        "receipt_intake_audit": {
            "receipt_path": "docs/formal_plagiarism_screening_receipt.json",
            "audit_json": "runs/formal_plagiarism_screening_receipt_audit.json",
            "audit_md": "docs/formal_plagiarism_screening_receipt_audit.md",
            "strict_command": (
                "python scripts/audit_formal_plagiarism_screening_receipt.py --strict"
            ),
        },
        "screening_scope": targets,
        "acceptable_external_tools": [
            "iThenticate",
            "Turnitin",
            "venue-side corpus matching report",
            "institutional plagiarism/originality screening service",
        ],
        "required_external_screening_receipt_fields": REQUIRED_RECEIPT_FIELDS,
        "receipt_template": {
            "schema_version": "formal_plagiarism_screening_receipt_v1",
            "screening_tool_or_vendor": "",
            "screening_report_id_or_url": "",
            "screening_report_export_sha256_or_private_location": "",
            "screened_file_path": "",
            "screened_file_sha256": "",
            "screened_date_utc": "",
            "operator": "",
            "screening_database_or_corpus": "",
            "external_corpus_searched": False,
            "total_similarity_percent": None,
            "max_single_source_similarity_percent": None,
            "top_matched_sources": [],
            "excluded_sources_or_filters": [],
            "human_review_disposition": "",
            "material_matches_reviewed": False,
            "self_overlap_or_prior_version_reviewed": False,
            "pass": False,
            "notes": "",
        },
        "receipt_acceptance_policy": {
            "screened_file_sha256_must_match_scope": True,
            "tool_must_search_external_corpus": True,
            "human_review_required_for_each_material_match": True,
            "material_matches_review_must_be_recorded": True,
            "self_overlap_or_prior_version_review_must_be_recorded": True,
            "receipt_intake_audit_required": True,
            "numeric_similarity_threshold_is_institution_or_venue_dependent": True,
            "do_not_mark_complete_from_local_duplicate_sentence_audit_only": True,
        },
        "risk_flags": risk_flags,
        "open_risk_flags": [
            "formal_external_plagiarism_database_screen_not_performed",
        ],
        "interpretation": {
            "runbook_only": True,
            "formal_external_screening_still_required": True,
            "local_reference_integrity_audit_is_not_formal_detector": True,
            "local_manuscript_originality_audit_is_not_formal_detector": True,
            "no_similarity_result_recorded": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["formal_plagiarism_screening_runbook_ready"] else "not ready"
    lines = [
        "# Formal Plagiarism Screening Runbook",
        "",
        "This generated runbook fixes the exact manuscript files and receipt",
        "fields required for a formal external plagiarism/originality screen.",
        "It does not certify that screening has been completed.",
        "",
        f"Runbook status: {status}.",
        f"Formal screening completed: `{payload['formal_screening_completed']}`.",
        "",
        "## Screening Scope",
        "",
        "| Role | Path | Exists | Bytes | SHA256 |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for target in payload["screening_scope"]:
        lines.append(
            "| {role} | `{path}` | {exists} | {bytes} | `{sha256}` |".format(
                role=target["role"],
                path=target["path"],
                exists=target["exists"],
                bytes=target.get("bytes", "missing"),
                sha256=target.get("sha256", "missing"),
            )
        )
    lines.extend(
        [
            "",
            "## Receipt Intake Audit",
            "",
            f"- Receipt path: `{payload['receipt_intake_audit']['receipt_path']}`",
            f"- Audit JSON: `{payload['receipt_intake_audit']['audit_json']}`",
            f"- Audit Markdown: `{payload['receipt_intake_audit']['audit_md']}`",
            f"- Strict command: `{payload['receipt_intake_audit']['strict_command']}`",
            "",
            "## Acceptable External Tools",
            "",
        ]
    )
    lines.extend(f"- {tool}" for tool in payload["acceptable_external_tools"])
    lines.extend(
        [
            "",
            "## Required Receipt Fields",
            "",
        ]
    )
    lines.extend(
        f"- `{field}`" for field in payload["required_external_screening_receipt_fields"]
    )
    lines.extend(
        [
            "",
            "## Receipt Acceptance Policy",
            "",
        ]
    )
    for key, value in payload["receipt_acceptance_policy"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Risk Flags", ""])
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(["", "## Open Risk Flags", ""])
    lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Local reference-integrity and manuscript-originality audits are not",
            "formal plagiarism detectors. They reduce hallucinated-reference and",
            "obvious duplicate-prose risk, but they do not replace iThenticate,",
            "Turnitin, venue-side corpus matching, or institutional corpus search.",
            "",
            "The open risk `formal_external_plagiarism_database_screen_not_performed`",
            "must stay open until an external report is reviewed and the screened",
            "file SHA256 matches one of the files above.",
            "",
            "This file is generated by `scripts/build_formal_plagiarism_screening_runbook.py`.",
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
                "formal_plagiarism_screening_runbook_ready": payload[
                    "formal_plagiarism_screening_runbook_ready"
                ],
                "formal_screening_completed": payload["formal_screening_completed"],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )


if __name__ == "__main__":
    main()
