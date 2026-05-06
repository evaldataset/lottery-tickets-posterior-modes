#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "runs" / "iclr_human_confirmation_template.json"
DEFAULT_RECEIPT = ROOT / "docs" / "iclr_human_confirmation_receipt.json"
DEFAULT_OUT_JSON = ROOT / "runs" / "iclr_human_confirmation_receipt_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "iclr_human_confirmation_receipt_audit.md"
EXPECTED_SCHEMA_VERSION = "iclr_human_confirmation_receipt_v1"

TRUE_FIELDS = {
    "author_order_confirmed",
    "all_authors_have_openreview_profiles",
    "conflicts_recorded_in_openreview",
    "reciprocal_reviewing_policy_reviewed",
    "code_of_ethics_acknowledged_by_all_authors",
    "ethics_statement_confirmed_by_all_authors",
    "llm_usage_disclosure_confirmed_by_all_authors",
    "no_human_subjects_private_or_surveillance_data_confirmed",
    "submission_agreement_confirmed",
}
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
PLACEHOLDERS = {"", "tbd", "todo", "none", "n/a", "na", "unknown", "placeholder"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero unless all private human confirmations are present.",
    )
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


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else {}


def meaningful(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in PLACEHOLDERS


def iso_datetime_with_timezone(value: Any) -> bool:
    if not meaningful(value):
        return False
    raw = str(value).strip()
    candidates = [raw, raw[:-1] + "+00:00"] if raw.endswith("Z") else [raw]
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return False
        return parsed <= datetime.now(timezone.utc)
    return False


def list_status(receipt: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "author_names",
        "author_emails",
        "author_affiliations",
        "author_openreview_profile_urls",
    ]
    counts = {
        field: len(receipt.get(field, [])) if isinstance(receipt.get(field), list) else 0
        for field in fields
    }
    nonempty = all(counts[field] > 0 for field in fields)
    same_length = len(set(counts.values())) == 1 and nonempty
    profile_urls_valid = False
    profiles = receipt.get("author_openreview_profile_urls", [])
    if isinstance(profiles, list) and profiles:
        profile_urls_valid = all(
            isinstance(item, str)
            and item.startswith("https://openreview.net/profile?id=")
            for item in profiles
        )
    return {
        "author_count": counts["author_names"],
        "email_count": counts["author_emails"],
        "affiliation_count": counts["author_affiliations"],
        "openreview_profile_count": counts["author_openreview_profile_urls"],
        "author_lists_nonempty": nonempty,
        "author_lists_same_length": same_length,
        "openreview_profile_urls_shape_valid": profile_urls_valid,
    }


def build_payload(template_path: Path, receipt_path: Path) -> dict[str, Any]:
    risk_flags: list[str] = []
    if not template_path.exists():
        risk_flags.append("iclr_human_confirmation_template_missing")
        template: dict[str, Any] = {}
    else:
        template = load_json(template_path)
        if template.get("iclr_human_confirmation_template_ready") is not True:
            risk_flags.append("iclr_human_confirmation_template_not_ready")

    primary_pdf = ROOT / "paper" / "iclr_submission.pdf"
    expected_pdf_sha = sha256(primary_pdf) if primary_pdf.exists() else ""
    required_fields = [
        "schema_version",
        *[str(field) for field in template.get("required_confirmation_fields", [])],
    ]

    if not receipt_path.exists():
        return {
            "iclr_human_confirmation_receipt_audit_ready": not risk_flags,
            "confirmations_completed": False,
            "receipt_observed": False,
            "receipt_path": relpath(receipt_path),
            "template": relpath(template_path),
            "expected_schema_version": EXPECTED_SCHEMA_VERSION,
            "expected_pdf_sha256": expected_pdf_sha,
            "required_fields": required_fields,
            "field_statuses": [],
            "private_field_status": {},
            "risk_flags": risk_flags,
            "open_risk_flags": [
                "iclr_openreview_author_profile_and_coi_not_recorded",
                "iclr_code_of_ethics_author_acknowledgement_not_recorded",
                "llm_usage_disclosure_author_confirmation_not_recorded",
                "iclr_openreview_submission_receipt_not_observed",
            ],
            "privacy": {
                "does_not_echo_private_values": True,
                "private_fields": sorted(PRIVATE_FIELDS),
            },
        }

    try:
        receipt = load_json(receipt_path)
    except (OSError, json.JSONDecodeError):
        receipt = {}
        risk_flags.append("iclr_human_confirmation_receipt_unreadable")

    field_statuses: list[dict[str, Any]] = []
    missing_or_invalid: list[str] = []
    for field in required_fields:
        present = field in receipt
        valid = present
        reason = "ok"
        if field == "schema_version":
            valid = receipt.get(field) == EXPECTED_SCHEMA_VERSION
            reason = "ok" if valid else "schema_version_mismatch"
        elif field in TRUE_FIELDS:
            valid = receipt.get(field) is True
            reason = "ok" if valid else "must_be_true"
        elif field in {"screened_pdf_sha256_confirmed", "submitted_pdf_sha256_confirmed"}:
            valid = receipt.get(field) == expected_pdf_sha and bool(expected_pdf_sha)
            reason = "ok" if valid else "pdf_sha256_mismatch"
        elif field == "submitted_at_iso8601_with_timezone":
            valid = iso_datetime_with_timezone(receipt.get(field))
            reason = "ok" if valid else "must_be_past_iso_datetime_with_timezone"
        elif field == "openreview_submission_forum_url":
            value = str(receipt.get(field, "")).strip()
            valid = value.startswith("https://openreview.net/forum?id=")
            reason = "ok" if valid else "must_be_openreview_forum_url"
        elif field == "openreview_submission_id":
            valid = meaningful(receipt.get(field))
            reason = "ok" if valid else "missing_or_placeholder"
        elif field == "confirmation_email_or_receipt_path":
            valid = meaningful(receipt.get(field))
            reason = "ok" if valid else "missing_or_placeholder"
        elif field in {
            "author_names",
            "author_emails",
            "author_affiliations",
            "author_openreview_profile_urls",
        }:
            valid = isinstance(receipt.get(field), list) and bool(receipt.get(field))
            reason = "ok" if valid else "must_be_nonempty_list"
        if not valid:
            missing_or_invalid.append(field)
        field_statuses.append(
            {
                "field": field,
                "present": present,
                "valid": valid,
                "reason": reason,
                "private": field in PRIVATE_FIELDS,
            }
        )

    private_status = list_status(receipt)
    open_flags: list[str] = []
    if (
        not private_status["author_lists_nonempty"]
        or not private_status["author_lists_same_length"]
        or not private_status["openreview_profile_urls_shape_valid"]
        or receipt.get("all_authors_have_openreview_profiles") is not True
        or receipt.get("conflicts_recorded_in_openreview") is not True
    ):
        open_flags.append("iclr_openreview_author_profile_and_coi_not_recorded")
    if receipt.get("code_of_ethics_acknowledged_by_all_authors") is not True:
        open_flags.append("iclr_code_of_ethics_author_acknowledgement_not_recorded")
    if receipt.get("llm_usage_disclosure_confirmed_by_all_authors") is not True:
        open_flags.append("llm_usage_disclosure_author_confirmation_not_recorded")
    forum_url = str(receipt.get("openreview_submission_forum_url", "")).strip()
    if (
        not forum_url.startswith("https://openreview.net/forum?id=")
        or not meaningful(receipt.get("openreview_submission_id"))
        or not iso_datetime_with_timezone(receipt.get("submitted_at_iso8601_with_timezone"))
        or receipt.get("submitted_pdf_sha256_confirmed") != expected_pdf_sha
    ):
        open_flags.append("iclr_openreview_submission_receipt_not_observed")
    if missing_or_invalid:
        open_flags.append("iclr_human_confirmation_receipt_incomplete")

    completed = bool(not risk_flags and not open_flags)
    return {
        "iclr_human_confirmation_receipt_audit_ready": not risk_flags,
        "confirmations_completed": completed,
        "receipt_observed": True,
        "receipt_path": relpath(receipt_path),
        "template": relpath(template_path),
        "expected_schema_version": EXPECTED_SCHEMA_VERSION,
        "expected_pdf_sha256": expected_pdf_sha,
        "required_fields": required_fields,
        "field_statuses": field_statuses,
        "invalid_fields": missing_or_invalid,
        "private_field_status": private_status,
        "risk_flags": risk_flags,
        "open_risk_flags": list(dict.fromkeys(open_flags)),
        "privacy": {
            "does_not_echo_private_values": True,
            "private_fields": sorted(PRIVATE_FIELDS),
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "complete" if payload["confirmations_completed"] else "not complete"
    lines = [
        "# ICLR Human Confirmation Receipt Audit",
        "",
        "This generated audit validates a private ICLR human-confirmation",
        "receipt without echoing author names, emails, affiliations, OpenReview",
        "profile URLs, COI details, or confirmation paths.",
        "",
        f"Audit ready: `{payload['iclr_human_confirmation_receipt_audit_ready']}`.",
        f"Receipt observed: `{payload['receipt_observed']}`.",
        f"Confirmation status: {status}.",
        f"Receipt path: `{payload['receipt_path']}`.",
        f"Expected schema version: `{payload['expected_schema_version']}`.",
        f"Expected PDF SHA256: `{payload['expected_pdf_sha256']}`.",
        "",
        "## Private Field Status",
        "",
    ]
    private_status = payload.get("private_field_status", {})
    if private_status:
        lines.extend(
            [
                f"- Author count: `{private_status.get('author_count')}`",
                f"- Email count: `{private_status.get('email_count')}`",
                f"- Affiliation count: `{private_status.get('affiliation_count')}`",
                f"- OpenReview profile count: `{private_status.get('openreview_profile_count')}`",
                f"- Author lists same length: `{private_status.get('author_lists_same_length')}`",
                f"- OpenReview profile URL shape valid: `{private_status.get('openreview_profile_urls_shape_valid')}`",
            ]
        )
    else:
        lines.append("- no private receipt observed")
    lines.extend(["", "## Field Validation", ""])
    if payload["field_statuses"]:
        lines.extend(["| Field | Present | Valid | Private | Reason |", "| --- | ---: | ---: | ---: | --- |"])
        for row in payload["field_statuses"]:
            lines.append(
                f"| `{row['field']}` | {row['present']} | {row['valid']} | {row['private']} | {row['reason']} |"
            )
    else:
        lines.append("- no receipt fields observed")
    lines.extend(["", "## Open Risk Flags", ""])
    if payload["open_risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Privacy",
            "",
            "- This audit intentionally records only counts, booleans, and expected hashes.",
            "- Do not commit `docs/iclr_human_confirmation_receipt.json` to the public release.",
            "",
            "This file is generated by `scripts/audit_iclr_human_confirmation_receipt.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_payload(args.template, args.receipt)
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "iclr_human_confirmation_receipt_audit_ready": payload[
                    "iclr_human_confirmation_receipt_audit_ready"
                ],
                "confirmations_completed": payload["confirmations_completed"],
                "receipt_observed": payload["receipt_observed"],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if args.strict and payload["confirmations_completed"] is not True:
        sys.exit(1)


if __name__ == "__main__":
    main()
