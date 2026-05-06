#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "ethics_statement_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "ethics_statement_audit.md"

REQUIRED_SOURCE_PHRASES = [
    r"\section*{Ethics Statement}",
    "standard public benchmark datasets",
    "does not introduce human subjects data",
    "private personal data",
    "surveillance data",
    "safety-critical deployment claims",
    "scientific overclaiming",
    "controlled empirical result",
    "Code of Ethics",
]

REQUIRED_PDF_PHRASES = [
    "standard public benchmark datasets",
    "human subjects data",
    "private personal data",
    "scientific overclaiming",
    "controlled empirical result",
    "Code of Ethics",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", type=Path, default=ROOT / "paper" / "main.tex")
    parser.add_argument("--iclr-pdf", type=Path, default=ROOT / "paper" / "iclr_submission.pdf")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    return parser.parse_args()


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_text(text: str) -> str:
    text = re.sub(r"-\s*\d+\s*", "", text)
    text = text.replace("-\n", "")
    text = " ".join(text.split())
    text = " ".join(part for part in text.split() if not part.isdigit())
    return " ".join(text.split())


def pdf_text(path: Path) -> str:
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None or not path.exists():
        return ""
    completed = subprocess.run(
        [pdftotext, "-layout", str(path), "-"],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return ""
    return normalize_text(completed.stdout)


def build_audit(paper: Path, iclr_pdf: Path) -> dict[str, Any]:
    source = paper.read_text(encoding="utf-8") if paper.exists() else ""
    normalized_source = normalize_text(source)
    rendered = pdf_text(iclr_pdf)
    missing_source = []
    for phrase in REQUIRED_SOURCE_PHRASES:
        haystack = source if phrase.startswith("\\") else normalized_source
        if phrase not in haystack:
            missing_source.append(phrase)
    missing_pdf = [phrase for phrase in REQUIRED_PDF_PHRASES if phrase not in rendered]
    risk_flags = []
    if missing_source:
        risk_flags.append("ethics_statement_missing_from_source")
    if missing_pdf:
        risk_flags.append("ethics_statement_missing_from_iclr_pdf")
    return {
        "ethics_statement_audit_ready": not risk_flags,
        "paper_source": relpath(paper),
        "iclr_submission_pdf": relpath(iclr_pdf),
        "required_source_phrases": REQUIRED_SOURCE_PHRASES,
        "required_pdf_phrases": REQUIRED_PDF_PHRASES,
        "missing_source_phrases": missing_source,
        "missing_pdf_phrases": missing_pdf,
        "risk_flags": risk_flags,
        "open_risk_flags": [
            "iclr_code_of_ethics_author_acknowledgement_not_recorded",
        ],
        "interpretation": {
            "ethics_statement_present_in_iclr_pdf": not missing_source and not missing_pdf,
            "no_human_subjects_or_private_data_claimed": (
                "human subjects data" in normalized_source
                and "private personal data" in normalized_source
            ),
            "overclaiming_risk_scoped": "scientific overclaiming" in normalized_source,
            "does_not_replace_final_iclr_author_acknowledgement": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["ethics_statement_audit_ready"] else "not ready"
    lines = [
        "# Ethics Statement Audit",
        "",
        "This generated audit checks that the ICLR-style paper source and PDF",
        "include a concise ethics statement. It does not replace the final",
        "ICLR Code of Ethics acknowledgement by the human authors.",
        "",
        f"Audit status: {status}.",
        f"Paper source: `{payload['paper_source']}`.",
        f"ICLR submission PDF: `{payload['iclr_submission_pdf']}`.",
        "",
        "## Missing Source Phrases",
        "",
    ]
    if payload["missing_source_phrases"]:
        lines.extend(f"- `{phrase}`" for phrase in payload["missing_source_phrases"])
    else:
        lines.append("- none")
    lines.extend(["", "## Missing PDF Phrases", ""])
    if payload["missing_pdf_phrases"]:
        lines.extend(f"- `{phrase}`" for phrase in payload["missing_pdf_phrases"])
    else:
        lines.append("- none")
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
            "The ethics statement is present in the generated ICLR PDF, but final",
            "submission still requires the authors to acknowledge and comply with",
            "the applicable ICLR Code of Ethics in the submission system.",
            "",
            "This file is generated by `scripts/audit_ethics_statement.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_audit(args.paper, args.iclr_pdf)
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "ethics_statement_audit_ready": payload["ethics_statement_audit_ready"],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if not payload["ethics_statement_audit_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
