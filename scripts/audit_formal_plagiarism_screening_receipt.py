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
DEFAULT_RUNBOOK = ROOT / "runs" / "formal_plagiarism_screening_runbook.json"
DEFAULT_RECEIPT = ROOT / "docs" / "formal_plagiarism_screening_receipt.json"
DEFAULT_OUT_JSON = ROOT / "runs" / "formal_plagiarism_screening_receipt_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "formal_plagiarism_screening_receipt_audit.md"
EXPECTED_SCHEMA_VERSION = "formal_plagiarism_screening_receipt_v1"

PLACEHOLDER_VALUES = {
    "",
    "tbd",
    "todo",
    "none",
    "n/a",
    "na",
    "unknown",
    "placeholder",
    "fill me",
    "fill-me",
}

BOOL_TRUE_FIELDS = {
    "external_corpus_searched",
    "material_matches_reviewed",
    "self_overlap_or_prior_version_reviewed",
    "pass",
}

LIST_FIELDS = {"top_matched_sources", "excluded_sources_or_filters"}
PERCENT_FIELDS = {"total_similarity_percent", "max_single_source_similarity_percent"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runbook", type=Path, default=DEFAULT_RUNBOOK)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero unless a valid external screening receipt is present.",
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
    return json.loads(path.read_text(encoding="utf-8"))


def meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in PLACEHOLDER_VALUES
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    if isinstance(value, bool):
        return True
    if isinstance(value, list):
        return True
    if isinstance(value, dict):
        return bool(value)
    return bool(value)


def percent_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        try:
            numeric = float(value.strip().rstrip("%"))
        except ValueError:
            return None
    else:
        return None
    if 0.0 <= numeric <= 100.0:
        return numeric
    return None


def date_like(value: Any) -> bool:
    if not isinstance(value, str) or not meaningful(value):
        return False
    raw = value.strip()
    candidates = [raw]
    if raw.endswith("Z"):
        candidates.append(raw[:-1] + "+00:00")
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed > datetime.now(timezone.utc).replace(microsecond=0):
            return False
        return True
    return False


def field_status(field: str, receipt: dict[str, Any]) -> dict[str, Any]:
    present = field in receipt
    value = receipt.get(field)
    valid = present and meaningful(value)
    reason = "ok" if valid else "missing_or_placeholder"
    if present and field == "schema_version":
        valid = value == EXPECTED_SCHEMA_VERSION
        reason = "ok" if valid else "schema_version_mismatch"
    elif present and field in BOOL_TRUE_FIELDS:
        valid = value is True
        reason = "ok" if valid else "must_be_true"
    elif present and field in LIST_FIELDS:
        valid = isinstance(value, list)
        reason = "ok" if valid else "must_be_list"
    elif present and field in PERCENT_FIELDS:
        valid = percent_value(value) is not None
        reason = "ok" if valid else "must_be_percent_0_to_100"
    elif present and field == "screened_file_sha256":
        valid = isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
        reason = "ok" if valid else "must_be_lowercase_sha256"
    elif present and field == "screened_date_utc":
        valid = date_like(value)
        reason = "ok" if valid else "must_be_past_iso_datetime"
    return {
        "field": field,
        "present": present,
        "valid": valid,
        "reason": reason,
    }


def screening_scope(runbook: dict[str, Any]) -> list[dict[str, Any]]:
    targets = runbook.get("screening_scope", [])
    if not isinstance(targets, list):
        return []
    clean_targets = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        rel = str(target.get("path", ""))
        path = ROOT / rel
        record = {
            "role": str(target.get("role", "")),
            "path": rel,
            "exists": path.exists(),
            "runbook_sha256": str(target.get("sha256", "")),
            "current_sha256": sha256(path) if path.exists() else "",
        }
        record["current_hash_matches_runbook"] = (
            record["exists"] is True
            and bool(record["runbook_sha256"])
            and record["runbook_sha256"] == record["current_sha256"]
        )
        clean_targets.append(record)
    return clean_targets


def validate_receipt(
    receipt: dict[str, Any],
    runbook: dict[str, Any],
    targets: list[dict[str, Any]],
) -> dict[str, Any]:
    required_fields = runbook.get("required_external_screening_receipt_fields", [])
    if not isinstance(required_fields, list):
        required_fields = []
    required_fields = [str(field) for field in required_fields]
    field_statuses = [field_status(field, receipt) for field in required_fields]
    open_risk_flags: list[str] = []
    invalid_fields = [
        status["field"] for status in field_statuses if status.get("valid") is not True
    ]
    if invalid_fields:
        open_risk_flags.append("formal_plagiarism_receipt_schema_invalid")

    screened_path = str(receipt.get("screened_file_path", "")).strip()
    screened_sha = str(receipt.get("screened_file_sha256", "")).strip()
    target_by_path = {str(target["path"]): target for target in targets}
    matching_targets = [
        target for target in targets if target.get("current_sha256") == screened_sha
    ]
    matched_target = target_by_path.get(screened_path)
    hash_validation: dict[str, Any] = {
        "screened_file_path": screened_path,
        "screened_file_sha256": screened_sha,
        "screened_path_in_scope": screened_path in target_by_path,
        "screened_sha256_matches_current_scope": bool(matching_targets),
        "matched_role": matching_targets[0]["role"] if matching_targets else "",
        "matched_path": matching_targets[0]["path"] if matching_targets else "",
        "path_and_hash_match_same_target": bool(
            matched_target and matched_target.get("current_sha256") == screened_sha
        ),
    }
    hash_validation["stale"] = not hash_validation["path_and_hash_match_same_target"]
    if not hash_validation["screened_path_in_scope"]:
        open_risk_flags.append("formal_plagiarism_receipt_screened_path_not_in_scope")
    if not hash_validation["screened_sha256_matches_current_scope"]:
        open_risk_flags.append("formal_plagiarism_receipt_file_hash_not_current")
    if (
        hash_validation["screened_path_in_scope"]
        and hash_validation["screened_sha256_matches_current_scope"]
        and not hash_validation["path_and_hash_match_same_target"]
    ):
        open_risk_flags.append("formal_plagiarism_receipt_path_hash_mismatch")

    tool_name = str(receipt.get("screening_tool_or_vendor", "")).strip().lower()
    local_only_names = {
        "local manuscript originality audit",
        "reference integrity audit",
        "manual grep",
    }
    tool_is_external = meaningful(tool_name) and tool_name not in local_only_names
    if not tool_is_external:
        open_risk_flags.append("formal_plagiarism_receipt_not_external_tool")

    top_sources_valid = True
    top_sources = receipt.get("top_matched_sources", [])
    if isinstance(top_sources, list):
        for source in top_sources:
            if not isinstance(source, dict):
                top_sources_valid = False
                break
            if "similarity_percent" in source and percent_value(
                source.get("similarity_percent")
            ) is None:
                top_sources_valid = False
                break
    else:
        top_sources_valid = False
    if not top_sources_valid:
        open_risk_flags.append("formal_plagiarism_receipt_top_sources_invalid")

    formal_screening_completed = bool(
        not open_risk_flags
        and receipt.get("pass") is True
        and hash_validation["path_and_hash_match_same_target"]
    )
    if not formal_screening_completed:
        open_risk_flags.append("formal_external_plagiarism_database_screen_not_performed")

    return {
        "required_fields": required_fields,
        "field_statuses": field_statuses,
        "invalid_fields": invalid_fields,
        "hash_validation": hash_validation,
        "tool_is_external": tool_is_external,
        "top_sources_valid": top_sources_valid,
        "formal_screening_completed": formal_screening_completed,
        "open_risk_flags": list(dict.fromkeys(open_risk_flags)),
    }


def build_payload(runbook_path: Path, receipt_path: Path) -> dict[str, Any]:
    risk_flags: list[str] = []
    if not runbook_path.exists():
        risk_flags.append("formal_plagiarism_runbook_missing")
        runbook: dict[str, Any] = {}
    else:
        runbook = load_json(runbook_path)
        if runbook.get("formal_plagiarism_screening_runbook_ready") is not True:
            risk_flags.append("formal_plagiarism_runbook_not_ready")
    targets = screening_scope(runbook)
    if len(targets) < 4 or any(
        target.get("current_hash_matches_runbook") is not True for target in targets
    ):
        risk_flags.append("formal_plagiarism_screening_scope_not_current")

    receipt_observed = receipt_path.exists()
    if not receipt_observed:
        required_fields = runbook.get("required_external_screening_receipt_fields", [])
        if not isinstance(required_fields, list):
            required_fields = []
        return {
            "formal_plagiarism_screening_receipt_audit_ready": not risk_flags,
            "formal_screening_completed": False,
            "receipt_observed": False,
            "receipt_path": relpath(receipt_path),
            "runbook": relpath(runbook_path),
            "schema_version_expected": EXPECTED_SCHEMA_VERSION,
            "accepted_screening_targets": targets,
            "required_fields": [str(field) for field in required_fields],
            "field_statuses": [],
            "invalid_fields": [],
            "hash_validation": {},
            "risk_flags": risk_flags,
            "open_risk_flags": [
                "formal_external_plagiarism_database_screen_not_performed"
            ],
            "interpretation": {
                "receipt_intake_gate_only": True,
                "missing_receipt_is_external_blocker_not_local_script_failure": True,
                "local_originality_audits_do_not_close_formal_screening": True,
            },
        }

    try:
        receipt = load_json(receipt_path)
    except (OSError, json.JSONDecodeError):
        receipt = {}
        risk_flags.append("formal_plagiarism_receipt_json_unreadable")
    if not isinstance(receipt, dict):
        receipt = {}
        risk_flags.append("formal_plagiarism_receipt_not_object")

    validation = validate_receipt(receipt, runbook, targets)
    return {
        "formal_plagiarism_screening_receipt_audit_ready": not risk_flags,
        "formal_screening_completed": bool(
            not risk_flags and validation["formal_screening_completed"]
        ),
        "receipt_observed": True,
        "receipt_path": relpath(receipt_path),
        "runbook": relpath(runbook_path),
        "schema_version_expected": EXPECTED_SCHEMA_VERSION,
        "accepted_screening_targets": targets,
        "required_fields": validation["required_fields"],
        "field_statuses": validation["field_statuses"],
        "invalid_fields": validation["invalid_fields"],
        "hash_validation": validation["hash_validation"],
        "tool_is_external": validation["tool_is_external"],
        "top_sources_valid": validation["top_sources_valid"],
        "risk_flags": risk_flags,
        "open_risk_flags": validation["open_risk_flags"] if not risk_flags else [],
        "interpretation": {
            "receipt_intake_gate_only": True,
            "missing_receipt_is_external_blocker_not_local_script_failure": True,
            "local_originality_audits_do_not_close_formal_screening": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = (
        "complete" if payload["formal_screening_completed"] else "not complete"
    )
    lines = [
        "# Formal Plagiarism Screening Receipt Audit",
        "",
        "This generated audit validates the intake shape for an external",
        "plagiarism/originality-screening receipt. It does not perform corpus",
        "matching and does not certify originality without a valid external",
        "receipt.",
        "",
        f"Audit ready: `{payload['formal_plagiarism_screening_receipt_audit_ready']}`.",
        f"Receipt observed: `{payload['receipt_observed']}`.",
        f"Formal screening status: {status}.",
        f"Formal screening completed: {payload['formal_screening_completed']}.",
        f"Receipt path: `{payload['receipt_path']}`.",
        f"Runbook: `{payload['runbook']}`.",
        f"Expected schema version: `{payload['schema_version_expected']}`.",
        "",
        "## Accepted Screening Targets",
        "",
        "| Role | Path | Current SHA256 | Current |",
        "| --- | --- | --- | ---: |",
    ]
    for target in payload["accepted_screening_targets"]:
        lines.append(
            "| {role} | `{path}` | `{sha}` | {current} |".format(
                role=target.get("role", ""),
                path=target.get("path", ""),
                sha=target.get("current_sha256", ""),
                current=target.get("current_hash_matches_runbook", False),
            )
        )
    lines.extend(["", "## Required Fields", ""])
    lines.extend(f"- `{field}`" for field in payload["required_fields"])
    if payload["field_statuses"]:
        lines.extend(
            [
                "",
                "## Field Validation",
                "",
                "| Field | Present | Valid | Reason |",
                "| --- | ---: | ---: | --- |",
            ]
        )
        for status_row in payload["field_statuses"]:
            lines.append(
                "| {field} | {present} | {valid} | {reason} |".format(
                    field=status_row.get("field", ""),
                    present=status_row.get("present", False),
                    valid=status_row.get("valid", False),
                    reason=status_row.get("reason", ""),
                )
            )
    if payload["hash_validation"]:
        hv = payload["hash_validation"]
        lines.extend(
            [
                "",
                "## Hash Validation",
                "",
                f"- Screened file path: `{hv.get('screened_file_path', '')}`",
                f"- Screened file SHA256: `{hv.get('screened_file_sha256', '')}`",
                f"- Screened path in scope: `{hv.get('screened_path_in_scope')}`",
                f"- SHA256 matches current scope: `{hv.get('screened_sha256_matches_current_scope')}`",
                f"- Path and hash match same target: `{hv.get('path_and_hash_match_same_target')}`",
                f"- Stale: `{hv.get('stale')}`",
            ]
        )
    lines.extend(["", "## Risk Flags", ""])
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(["", "## Open Risk Flags", ""])
    if payload["open_risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Closure Procedure",
            "",
            "Create `docs/formal_plagiarism_screening_receipt.json` from the",
            "runbook template only after an external iThenticate, Turnitin,",
            "venue-side, or institutional corpus-matching report has been",
            "reviewed. Then run:",
            "",
            "```bash",
            "python scripts/audit_formal_plagiarism_screening_receipt.py --strict",
            "```",
            "",
            "The receipt is stale if the screened file SHA256 does not match one",
            "of the current screening targets above.",
            "",
            "This file is generated by `scripts/audit_formal_plagiarism_screening_receipt.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_payload(args.runbook, args.receipt)
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "formal_plagiarism_screening_receipt_audit_ready": payload[
                    "formal_plagiarism_screening_receipt_audit_ready"
                ],
                "formal_screening_completed": payload["formal_screening_completed"],
                "receipt_observed": payload["receipt_observed"],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if args.strict and payload["formal_screening_completed"] is not True:
        sys.exit(1)


if __name__ == "__main__":
    main()
