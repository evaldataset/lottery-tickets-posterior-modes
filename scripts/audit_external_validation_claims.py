#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_READINESS = ROOT / "runs" / "external_validation_readiness_audit.json"
DEFAULT_OUT_JSON = ROOT / "runs" / "external_validation_claim_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "external_validation_claim_audit.md"

SCAN_PATHS = [
    ROOT / "README.md",
    ROOT / "paper" / "main.tex",
    ROOT / "docs",
]

FORBIDDEN_WHEN_NOT_READY = [
    (
        "observed_public_release_source_ci",
        re.compile(r"observed public release/source/CI receipts", re.IGNORECASE),
    ),
    (
        "public_archive_source_ci_observed",
        re.compile(
            r"public archive,\s*public source repository,\s*and\s*external CI receipts are observed",
            re.IGNORECASE,
        ),
    ),
    (
        "public_archive_source_ci_filled",
        re.compile(
            r"public archive,\s*public source repository,\s*public CI,\s*and local GPU-container receipts are filled",
            re.IGNORECASE,
        ),
    ),
    (
        "public_release_source_ci_filled",
        re.compile(
            r"public release archive,\s*public source repository,\s*external CI,\s*and local GPU-container receipts are filled",
            re.IGNORECASE,
        ),
    ),
    (
        "public_ci_observed_green",
        re.compile(r"public (?:GitHub Actions|CI) run is observed green", re.IGNORECASE),
    ),
    (
        "public_release_source_ci_gates_ready",
        re.compile(r"public release/public source/public CI gates are ready", re.IGNORECASE),
    ),
    (
        "first_three_receipts_observed",
        re.compile(r"first three are observed in the receipt registry", re.IGNORECASE),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness-json", type=Path, default=DEFAULT_READINESS)
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


def iter_scan_files() -> list[Path]:
    files: list[Path] = []
    for path in SCAN_PATHS:
        if path.is_file():
            files.append(path)
            continue
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.md") if p.is_file()))
    return sorted(set(files))


def context_for(text: str, start: int, end: int, radius: int = 90) -> str:
    snippet = text[max(0, start - radius) : min(len(text), end + radius)]
    return " ".join(snippet.split())


def build_audit(readiness_json: Path) -> dict[str, Any]:
    readiness = load_json(readiness_json)
    external_ready = readiness.get("external_validation_ready") is True
    top_conference_ready = readiness.get("top_conference_release_ready") is True
    readiness_flags = sorted(str(flag) for flag in readiness.get("risk_flags", []))

    findings: list[dict[str, Any]] = []
    if not external_ready:
        for path in iter_scan_files():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for rule_id, pattern in FORBIDDEN_WHEN_NOT_READY:
                for match in pattern.finditer(text):
                    findings.append(
                        {
                            "rule": rule_id,
                            "path": relpath(path),
                            "context": context_for(text, match.start(), match.end()),
                        }
                    )

    risk_flags = []
    if findings:
        risk_flags.append("stale_external_validation_positive_claims")

    return {
        "external_validation_claim_audit_ready": not risk_flags,
        "readiness_json": relpath(readiness_json),
        "external_validation_ready": external_ready,
        "top_conference_release_ready": top_conference_ready,
        "readiness_risk_flags": readiness_flags,
        "scanned_file_count": len(iter_scan_files()),
        "forbidden_rule_count": len(FORBIDDEN_WHEN_NOT_READY),
        "findings": findings,
        "risk_flags": risk_flags,
        "open_risk_flags": [] if external_ready else readiness_flags,
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# External Validation Claim Audit",
        "",
        "This generated audit prevents stale prose from claiming completed public",
        "external validation while the strict external-validation readiness gate is",
        "still open.",
        "",
        f"External validation ready: {payload['external_validation_ready']}.",
        f"Top-conference release ready: {payload['top_conference_release_ready']}.",
        f"Claim audit ready: {payload['external_validation_claim_audit_ready']}.",
        "",
        "## Readiness Risk Flags",
        "",
    ]
    risk_flags = payload["readiness_risk_flags"]
    if risk_flags:
        lines.extend(f"- {flag}" for flag in risk_flags)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Stale Positive Claim Findings",
            "",
        ]
    )
    findings = payload["findings"]
    if findings:
        lines.append("| Rule | Path | Context |")
        lines.append("| --- | --- | --- |")
        for finding in findings:
            context = str(finding["context"]).replace("|", "\\|")
            lines.append(f"| {finding['rule']} | `{finding['path']}` | {context} |")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This file is generated by `scripts/audit_external_validation_claims.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_audit(args.readiness_json)
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "external_validation_claim_audit_ready": payload[
                    "external_validation_claim_audit_ready"
                ],
                "risk_flags": payload["risk_flags"],
                "finding_count": len(payload["findings"]),
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if payload["risk_flags"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
