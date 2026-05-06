#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from audit_paper_submission_shape import ROOT, pdf_page_count


DEFAULT_OUT_JSON = ROOT / "runs" / "iclr_openreview_packet.json"
DEFAULT_OUT_MD = ROOT / "docs" / "iclr_openreview_packet.md"
DEFAULT_PRIMARY_PDF = ROOT / "paper" / "iclr_submission.pdf"
DEFAULT_ARTIFACT_ARCHIVE = ROOT / "dist" / "lottery_artifact_public_release_2026-05-06.tar.gz"

KEYWORDS = [
    "lottery ticket hypothesis",
    "Bayesian deep learning",
    "posterior modes",
    "network pruning",
    "SGLD",
    "Laplace approximation",
    "model sparsity",
    "reproducibility",
]

SUBJECT_AREAS = [
    "Deep learning",
    "Bayesian methods",
    "Optimization",
    "Generalization",
]

REQUIRED_HUMAN_FIELDS = [
    "author_names",
    "author_emails",
    "author_affiliations",
    "author_openreview_profiles",
    "author_conflicts_of_interest",
    "author_order_confirmed",
    "submission_agreement_confirmed",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", type=Path, default=ROOT / "paper" / "main.tex")
    parser.add_argument("--primary-pdf", type=Path, default=DEFAULT_PRIMARY_PDF)
    parser.add_argument("--main-pdf", type=Path, default=ROOT / "paper" / "main_submission.pdf")
    parser.add_argument("--full-pdf", type=Path, default=ROOT / "paper" / "main.pdf")
    parser.add_argument("--refs", type=Path, default=ROOT / "paper" / "refs.bib")
    parser.add_argument("--artifact-archive", type=Path, default=DEFAULT_ARTIFACT_ARCHIVE)
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


def tex_block(text: str, command: str) -> str:
    match = re.search(rf"\\{command}\s*\{{", text)
    if not match:
        return ""
    start = match.end()
    depth = 1
    index = start
    while index < len(text):
        char = text[index]
        previous = text[index - 1] if index > 0 else ""
        if char == "{" and previous != "\\":
            depth += 1
        elif char == "}" and previous != "\\":
            depth -= 1
            if depth == 0:
                return text[start:index]
        index += 1
    return ""


def normalize_tex_text(text: str) -> str:
    replacements = {
        r"\\": " ",
        r"\%": "%",
        r"\_": "_",
        r"\&": "&",
        "~": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", text))


def paper_metadata(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    title = normalize_tex_text(tex_block(text, "title"))
    abstract_match = re.search(
        r"\\begin\{abstract\}(?P<body>.*?)\\end\{abstract\}",
        text,
        flags=re.DOTALL,
    )
    abstract = normalize_tex_text(abstract_match.group("body") if abstract_match else "")
    return {
        "title": title,
        "abstract": abstract,
        "abstract_words": word_count(abstract),
        "anonymous_author_field": normalize_tex_text(tex_block(text, "author")),
    }


def pdf_metadata(path: Path) -> dict[str, Any]:
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo is None or not path.exists():
        return {"pdfinfo_available": pdfinfo is not None, "author": "", "raw": {}}
    completed = subprocess.run(
        [pdfinfo, str(path)],
        check=False,
        text=True,
        capture_output=True,
    )
    raw: dict[str, str] = {}
    if completed.returncode == 0:
        for line in completed.stdout.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            raw[key.strip()] = value.strip()
    return {
        "pdfinfo_available": True,
        "author": raw.get("Author", ""),
        "title": raw.get("Title", ""),
        "raw": raw,
    }


def file_record(role: str, path: Path, *, include_hash: bool = True) -> dict[str, Any]:
    record: dict[str, Any] = {
        "role": role,
        "path": relpath(path),
        "exists": path.exists(),
    }
    if path.exists():
        record["bytes"] = path.stat().st_size
        if include_hash:
            record["sha256"] = sha256(path)
    return record


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    metadata = paper_metadata(args.paper)
    primary_pdf = file_record("primary_iclr_submission_pdf", args.primary_pdf)
    main_pdf = file_record("main_only_submission_pdf", args.main_pdf)
    full_pdf = file_record("appendix_inclusive_reference_pdf", args.full_pdf)
    paper_source = file_record("paper_source_tex", args.paper)
    refs = file_record("bibliography_source_bib", args.refs)
    artifact = file_record(
        "optional_supplementary_artifact_archive",
        args.artifact_archive,
        include_hash=False,
    )
    primary_pdf["page_count"] = pdf_page_count(args.primary_pdf)
    primary_pdf["pdf_metadata"] = pdf_metadata(args.primary_pdf)

    upload_files = [primary_pdf, main_pdf, full_pdf, paper_source, refs, artifact]
    risk_flags: list[str] = []
    if not metadata["title"]:
        risk_flags.append("openreview_packet_title_missing")
    if not metadata["abstract"]:
        risk_flags.append("openreview_packet_abstract_missing")
    if int(metadata["abstract_words"]) > 250:
        risk_flags.append("openreview_packet_abstract_over_250_words")
    if metadata["anonymous_author_field"] != "Anonymous":
        risk_flags.append("openreview_packet_paper_author_not_anonymous")
    if primary_pdf.get("exists") is not True:
        risk_flags.append("openreview_packet_primary_pdf_missing")
    if primary_pdf.get("page_count") is None:
        risk_flags.append("openreview_packet_primary_pdf_page_count_unavailable")
    pdf_author = str(primary_pdf.get("pdf_metadata", {}).get("author", "")).strip()
    if pdf_author and pdf_author.lower() != "anonymous":
        risk_flags.append("openreview_packet_primary_pdf_author_metadata_not_anonymous")
    if artifact.get("exists") is not True:
        risk_flags.append("openreview_packet_supplement_artifact_missing")

    paste_payload = {
        "title": metadata["title"],
        "abstract": metadata["abstract"],
        "keywords": KEYWORDS,
        "subject_areas": SUBJECT_AREAS,
        "paper_pdf": primary_pdf["path"],
        "supplementary_material": artifact["path"],
        "ethics_statement": (
            "This work uses standard public benchmark datasets and does not "
            "introduce human subjects data, private personal data, surveillance "
            "data, or safety-critical deployment claims. The main risk is "
            "scientific overclaiming, which is mitigated by scoped claims, "
            "explicit limitations, and reproducible artifacts."
        ),
        "llm_usage_disclosure": (
            "LLM-based coding and writing assistants were used for audit/runbook "
            "scripts, reproducibility documentation, stale-claim checks, and "
            "manuscript/code-edit suggestions; they were not authors or sources "
            "of scientific evidence, and all final claims, references, code, and "
            "text were human-reviewed."
        ),
        "author_field_in_pdf": metadata["anonymous_author_field"],
        "external_urls_for_initial_submission": [],
        "public_artifact_links_for_initial_submission": [],
    }
    open_risk_flags = [
        "iclr_2027_official_cfp_not_observed",
        "iclr_openreview_author_profile_and_coi_not_recorded",
        "iclr_openreview_submission_receipt_not_observed",
    ]
    return {
        "iclr_openreview_packet_ready": not risk_flags,
        "ready_to_submit": False,
        "provisional_primary_venue": "ICLR 2027",
        "official_2027_cfp_observed": False,
        "metadata": metadata,
        "paste_payload": paste_payload,
        "upload_files": upload_files,
        "required_human_fields": REQUIRED_HUMAN_FIELDS,
        "double_blind_policy": {
            "paper_author_field_must_be_anonymous": True,
            "omit_public_artifact_urls_from_initial_submission": True,
            "artifact_archive_must_remain_anonymous": True,
            "human_author_identity_fields_not_stored_in_this_public_packet": True,
        },
        "risk_flags": risk_flags,
        "open_risk_flags": open_risk_flags,
        "interpretation": {
            "local_openreview_packet_prepared": not risk_flags,
            "not_a_final_openreview_submission_receipt": True,
            "must_update_after_official_2027_cfp": True,
            "must_record_human_author_profile_and_conflict_fields": True,
            "must_not_claim_ready_to_submit_until_open_risks_close": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    metadata = payload["metadata"]
    paste = payload["paste_payload"]
    status = "ready" if payload["iclr_openreview_packet_ready"] else "not ready"
    lines = [
        "# ICLR OpenReview Packet",
        "",
        "This generated packet collects the provisional ICLR OpenReview form",
        "fields and upload targets. It is a local packet, not a submission",
        "receipt, and it must be checked again after the official ICLR 2027 CFP",
        "and OpenReview form are available.",
        "",
        f"Packet status: {status}.",
        f"Ready to submit: `{payload['ready_to_submit']}`.",
        f"Official ICLR 2027 CFP observed: `{payload['official_2027_cfp_observed']}`.",
        "",
        "## Paste Payload",
        "",
        f"Title: {paste['title']}",
        "",
        f"Keywords: {', '.join(paste['keywords'])}",
        "",
        f"Subject areas: {', '.join(paste['subject_areas'])}",
        "",
        f"Abstract words: {metadata['abstract_words']}",
        "",
        "Ethics statement:",
        "",
        paste["ethics_statement"],
        "",
        "LLM usage disclosure:",
        "",
        paste["llm_usage_disclosure"],
        "",
        "Abstract:",
        "",
        paste["abstract"],
        "",
        "## Upload Files",
        "",
        "| Role | Path | Exists | Bytes | SHA256 | Pages |",
        "| --- | --- | ---: | ---: | --- | ---: |",
    ]
    for item in payload["upload_files"]:
        lines.append(
            "| {role} | `{path}` | {exists} | {bytes} | `{sha}` | {pages} |".format(
                role=item["role"],
                path=item["path"],
                exists=item["exists"],
                bytes=item.get("bytes", "missing"),
                sha=item.get("sha256", "not-recorded"),
                pages=item.get("page_count", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Required Human Fields",
            "",
        ]
    )
    lines.extend(f"- `{field}`" for field in payload["required_human_fields"])
    lines.extend(["", "## Double-Blind Policy", ""])
    for key, value in payload["double_blind_policy"].items():
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
            "## Do Not Paste Or Upload",
            "",
            "- Do not paste public repository, archive, CI, or GPU-log URLs into the",
            "  initial double-blind submission form unless the official venue form",
            "  explicitly requests them.",
            "- Do not upload author-identifying notes, receipts, or local handoff",
            "  files as supplementary material.",
            "",
            "This file is generated by `scripts/build_iclr_openreview_packet.py`.",
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
                "iclr_openreview_packet_ready": payload["iclr_openreview_packet_ready"],
                "ready_to_submit": payload["ready_to_submit"],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if not payload["iclr_openreview_packet_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
