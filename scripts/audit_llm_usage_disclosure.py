#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "llm_usage_disclosure_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "llm_usage_disclosure_audit.md"

REQUIRED_SOURCE_PHRASES = [
    r"\section*{LLM Usage Disclosure}",
    "LLM-based coding and writing assistants",
    "audit and runbook scripts",
    "reproducibility and submission-checklist documentation",
    "not used as authors",
    "not treated as sources of scientific evidence",
    "reviewed and accepted by the human authors",
]

REQUIRED_PDF_PHRASES = [
    "LLM-based coding and writing assistants",
    "not used as authors",
    "not treated as sources of scientific evidence",
    "reviewed and accepted by the human authors",
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


def normalize_text(text: str) -> str:
    # ICLR's style emits line numbers in pdftotext output and may hyphenate
    # line-wrapped words. Remove those artifacts before phrase matching.
    text = text.replace("-\n", "")
    text = " ".join(text.split())
    text = " ".join(part for part in text.split() if not part.isdigit())
    return " ".join(text.split())


def build_audit(paper: Path, iclr_pdf: Path) -> dict[str, Any]:
    source = paper.read_text(encoding="utf-8") if paper.exists() else ""
    normalized_source = normalize_text(source)
    rendered = pdf_text(iclr_pdf)
    missing_source = []
    for phrase in REQUIRED_SOURCE_PHRASES:
        if phrase.startswith("\\"):
            present = phrase in source
        else:
            present = phrase in normalized_source
        if not present:
            missing_source.append(phrase)
    missing_pdf = [phrase for phrase in REQUIRED_PDF_PHRASES if phrase not in rendered]
    risk_flags = []
    if missing_source:
        risk_flags.append("llm_usage_disclosure_missing_from_source")
    if missing_pdf:
        risk_flags.append("llm_usage_disclosure_missing_from_iclr_pdf")
    return {
        "llm_usage_disclosure_audit_ready": not risk_flags,
        "paper_source": relpath(paper),
        "iclr_submission_pdf": relpath(iclr_pdf),
        "required_source_phrases": REQUIRED_SOURCE_PHRASES,
        "required_pdf_phrases": REQUIRED_PDF_PHRASES,
        "missing_source_phrases": missing_source,
        "missing_pdf_phrases": missing_pdf,
        "risk_flags": risk_flags,
        "open_risk_flags": [
            "llm_usage_disclosure_author_confirmation_not_recorded",
        ],
        "interpretation": {
            "iclr_style_disclosure_section_present": not missing_source and not missing_pdf,
            "does_not_replace_author_confirmation": True,
            "must_refresh_after_official_iclr_2027_policy_posts": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["llm_usage_disclosure_audit_ready"] else "not ready"
    lines = [
        "# LLM Usage Disclosure Audit",
        "",
        "This generated audit checks that the ICLR-style paper source and PDF",
        "contain a separate LLM usage disclosure. It does not replace final",
        "human author confirmation of the exact disclosure wording.",
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
            "The disclosure section is present in the generated ICLR PDF, but the",
            "human authors still need to confirm that it precisely matches their",
            "actual LLM use before submission.",
            "",
            "This file is generated by `scripts/audit_llm_usage_disclosure.py`.",
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
                "llm_usage_disclosure_audit_ready": payload[
                    "llm_usage_disclosure_audit_ready"
                ],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if not payload["llm_usage_disclosure_audit_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
