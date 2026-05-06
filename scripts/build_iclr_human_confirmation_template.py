#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "iclr_human_confirmation_template.json"
DEFAULT_OUT_MD = ROOT / "docs" / "iclr_human_confirmation_template.md"

REQUIRED_CONFIRMATION_FIELDS = [
    "author_names",
    "author_emails",
    "author_affiliations",
    "author_openreview_profile_urls",
    "author_order_confirmed",
    "all_authors_have_openreview_profiles",
    "conflicts_recorded_in_openreview",
    "reciprocal_reviewing_policy_reviewed",
    "code_of_ethics_acknowledged_by_all_authors",
    "ethics_statement_confirmed_by_all_authors",
    "llm_usage_disclosure_confirmed_by_all_authors",
    "no_human_subjects_private_or_surveillance_data_confirmed",
    "submission_agreement_confirmed",
    "screened_pdf_sha256_confirmed",
    "submitted_pdf_sha256_confirmed",
    "openreview_submission_forum_url",
    "openreview_submission_id",
    "submitted_at_iso8601_with_timezone",
    "confirmation_email_or_receipt_path",
]

PRIVATE_FIELDS = {
    "author_names",
    "author_emails",
    "author_affiliations",
    "author_openreview_profile_urls",
    "conflicts_recorded_in_openreview",
    "openreview_submission_forum_url",
    "openreview_submission_id",
    "confirmation_email_or_receipt_path",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--openreview-packet",
        type=Path,
        default=ROOT / "runs" / "iclr_openreview_packet.json",
    )
    parser.add_argument(
        "--policy-watch",
        type=Path,
        default=ROOT / "runs" / "iclr_policy_watch_audit.json",
    )
    parser.add_argument(
        "--ethics-audit",
        type=Path,
        default=ROOT / "runs" / "ethics_statement_audit.json",
    )
    parser.add_argument(
        "--llm-audit",
        type=Path,
        default=ROOT / "runs" / "llm_usage_disclosure_audit.json",
    )
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


def empty_template(openreview_packet: dict[str, Any]) -> dict[str, Any]:
    upload_files = {
        str(item.get("path")): item
        for item in openreview_packet.get("upload_files", [])
        if isinstance(item, dict)
    }
    primary_pdf = upload_files.get("paper/iclr_submission.pdf", {})
    return {
        "author_names": [],
        "author_emails": [],
        "author_affiliations": [],
        "author_openreview_profile_urls": [],
        "author_order_confirmed": False,
        "all_authors_have_openreview_profiles": False,
        "conflicts_recorded_in_openreview": False,
        "reciprocal_reviewing_policy_reviewed": False,
        "code_of_ethics_acknowledged_by_all_authors": False,
        "ethics_statement_confirmed_by_all_authors": False,
        "llm_usage_disclosure_confirmed_by_all_authors": False,
        "no_human_subjects_private_or_surveillance_data_confirmed": False,
        "submission_agreement_confirmed": False,
        "screened_pdf_sha256_confirmed": "",
        "submitted_pdf_sha256_confirmed": str(primary_pdf.get("sha256", "")),
        "openreview_submission_forum_url": "",
        "openreview_submission_id": "",
        "submitted_at_iso8601_with_timezone": "",
        "confirmation_email_or_receipt_path": "",
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    openreview_packet = load_json(args.openreview_packet)
    policy_watch = load_json(args.policy_watch)
    ethics = load_json(args.ethics_audit)
    llm = load_json(args.llm_audit)

    risk_flags: list[str] = []
    if openreview_packet.get("iclr_openreview_packet_ready") is not True:
        risk_flags.append("iclr_openreview_packet_not_ready")
    if policy_watch.get("iclr_policy_watch_audit_ready") is not True:
        risk_flags.append("iclr_policy_watch_not_ready")
    if ethics.get("ethics_statement_audit_ready") is not True:
        risk_flags.append("ethics_statement_audit_not_ready")
    if llm.get("llm_usage_disclosure_audit_ready") is not True:
        risk_flags.append("llm_usage_disclosure_audit_not_ready")

    template = empty_template(openreview_packet)
    missing_template_fields = [
        field for field in REQUIRED_CONFIRMATION_FIELDS if field not in template
    ]
    if missing_template_fields:
        risk_flags.append("iclr_human_confirmation_template_fields_missing")

    return {
        "iclr_human_confirmation_template_ready": not risk_flags,
        "confirmations_completed": False,
        "risk_flags": risk_flags,
        "open_risk_flags": [
            "iclr_openreview_author_profile_and_coi_not_recorded",
            "iclr_code_of_ethics_author_acknowledgement_not_recorded",
            "llm_usage_disclosure_author_confirmation_not_recorded",
            "iclr_openreview_submission_receipt_not_observed",
        ],
        "inputs": {
            "openreview_packet": relpath(args.openreview_packet),
            "policy_watch": relpath(args.policy_watch),
            "ethics_audit": relpath(args.ethics_audit),
            "llm_audit": relpath(args.llm_audit),
        },
        "receipt_intake_audit": {
            "receipt_path": "docs/iclr_human_confirmation_receipt.json",
            "audit_json": "runs/iclr_human_confirmation_receipt_audit.json",
            "audit_md": "docs/iclr_human_confirmation_receipt_audit.md",
            "strict_command": (
                "python scripts/audit_iclr_human_confirmation_receipt.py --strict"
            ),
            "schema_version": "iclr_human_confirmation_receipt_v1",
        },
        "required_confirmation_fields": REQUIRED_CONFIRMATION_FIELDS,
        "private_fields_not_for_public_release": sorted(PRIVATE_FIELDS),
        "confirmation_template": template,
        "operator_instructions": [
            "Copy the confirmation_template into a private local receipt file before final submission.",
            "Do not commit author emails, OpenReview profile URLs, COI details, or confirmation email paths to the public release.",
            "After submission, record the OpenReview forum URL, submission id, timestamp, and confirmation evidence privately.",
            "Keep ready_to_submit false until all human confirmation booleans are true and the official ICLR 2027 policy has been rechecked.",
        ],
        "interpretation": {
            "template_only": True,
            "does_not_record_private_author_information": True,
            "does_not_replace_openreview_submission_receipt": True,
            "human_confirmations_still_required": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["iclr_human_confirmation_template_ready"] else "not ready"
    lines = [
        "# ICLR Human Confirmation Template",
        "",
        "This generated template lists the human-only ICLR submission confirmations",
        "that cannot be completed by the artifact verifier. It is intentionally",
        "blank and should not contain private author details in the public release.",
        "",
        f"Template status: {status}.",
        f"Confirmations completed: `{payload['confirmations_completed']}`.",
        "",
        "## Required Confirmation Fields",
        "",
    ]
    lines.extend(f"- `{field}`" for field in payload["required_confirmation_fields"])
    lines.extend(["", "## Private Fields Not For Public Release", ""])
    lines.extend(f"- `{field}`" for field in payload["private_fields_not_for_public_release"])
    lines.extend(["", "## Open Risk Flags", ""])
    lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    lines.extend(["", "## Operator Instructions", ""])
    lines.extend(f"- {item}" for item in payload["operator_instructions"])
    lines.extend(
        [
            "",
            "## Receipt Intake Audit",
            "",
            f"- Receipt path: `{payload['receipt_intake_audit']['receipt_path']}`",
            f"- Audit JSON: `{payload['receipt_intake_audit']['audit_json']}`",
            f"- Audit Markdown: `{payload['receipt_intake_audit']['audit_md']}`",
            f"- Strict command: `{payload['receipt_intake_audit']['strict_command']}`",
            f"- Schema version: `{payload['receipt_intake_audit']['schema_version']}`",
        ]
    )
    lines.extend(
        [
            "",
            "## Template JSON",
            "",
            "```json",
            json.dumps(payload["confirmation_template"], indent=2),
            "```",
            "",
            "This file is generated by `scripts/build_iclr_human_confirmation_template.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "iclr_human_confirmation_template_ready": payload[
                    "iclr_human_confirmation_template_ready"
                ],
                "confirmations_completed": payload["confirmations_completed"],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if not payload["iclr_human_confirmation_template_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
