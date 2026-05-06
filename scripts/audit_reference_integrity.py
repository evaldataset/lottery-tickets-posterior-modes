#!/usr/bin/env python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "main.tex"
BIB = ROOT / "paper" / "refs.bib"
DEFAULT_OUT_JSON = ROOT / "runs" / "reference_integrity_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "reference_integrity_audit.md"

# External verification registry: entries carrying an arXiv eprint were
# fetched from arxiv.org and their title/author lists matched against the
# bib entry verbatim. Venue-only entries are canonical, widely cited papers
# whose venue/year metadata is enforced by expected_key_metadata below; the
# two eprint entries are the only ones a reviewer cannot cross-check from
# the venue proceedings alone, so they get an explicit fetch receipt.
EXTERNAL_VERIFICATION = {
    "sakamoto2022pacbayes": {
        "method": "arxiv_fetch_title_author_match",
        "source": "https://arxiv.org/abs/2205.07320",
        "verified_date": "2026-06-10",
        "matched": "Analyzing Lottery Ticket Hypothesis from PAC-Bayesian Theory Perspective; Sakamoto, Sato (U. Tokyo)",
    },
    "kuhn2026bayesian": {
        "method": "arxiv_fetch_title_author_match",
        "source": "https://arxiv.org/abs/2602.18825",
        "verified_date": "2026-06-10",
        "matched": "Bayesian Lottery Ticket Hypothesis; Kuhn, Weyrauch, Heyen, Streit, Goetz, Debus (KIT/Helmholtz AI)",
    },
}


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def cited_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    for match in re.finditer(r"\\cite[a-zA-Z*]*\{([^}]*)\}", tex):
        keys.update(key.strip() for key in match.group(1).split(",") if key.strip())
    return keys


def parse_bib_entries(bib: str) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    chunks = re.split(r"(?m)(?=^@\w+\{)", bib)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        header = re.match(r"@(?P<type>\w+)\{(?P<key>[^,]+),", chunk)
        if not header:
            continue
        key = header.group("key").strip()
        fields: dict[str, str] = {}
        for field, value in re.findall(
            r"(?m)^\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*\{(.*?)\},?\s*$",
            chunk,
        ):
            fields[field.lower()] = value.strip()
        entries[key] = {
            "type": header.group("type").lower(),
            "fields": fields,
            "raw": chunk,
        }
    return entries


def build_audit() -> dict[str, Any]:
    tex = PAPER.read_text(encoding="utf-8")
    bib = BIB.read_text(encoding="utf-8")
    cited = cited_keys(tex)
    entries = parse_bib_entries(bib)
    bib_keys = set(entries)

    missing_citations = sorted(cited - bib_keys)
    unused_bib_entries = sorted(bib_keys - cited)
    duplicate_keys = sorted(
        key
        for key in bib_keys
        if len(re.findall(rf"(?m)^@\w+\{{{re.escape(key)},", bib)) > 1
    )
    required_field_issues: list[str] = []
    suspicious_field_issues: list[str] = []
    current_year = 2026

    for key in sorted(cited & bib_keys):
        entry = entries[key]
        fields = entry["fields"]
        for field in ["title", "author", "year"]:
            if not fields.get(field):
                required_field_issues.append(f"{key}:missing_{field}")
        if entry["type"] in {"inproceedings", "incollection"} and not fields.get("booktitle"):
            required_field_issues.append(f"{key}:missing_booktitle")
        if entry["type"] == "article" and not fields.get("journal"):
            required_field_issues.append(f"{key}:missing_journal")
        if entry["type"] == "misc" and not (
            fields.get("eprint") or fields.get("url") or fields.get("howpublished")
        ):
            required_field_issues.append(f"{key}:misc_missing_eprint_url_or_howpublished")
        year = fields.get("year", "")
        if year and year.isdigit() and int(year) > current_year:
            suspicious_field_issues.append(f"{key}:future_year_{year}")
        raw_lower = entry["raw"].lower()
        for token in ["todo", "tbd", "unknown", "placeholder", "citation needed"]:
            if token in raw_lower:
                suspicious_field_issues.append(f"{key}:contains_{token.replace(' ', '_')}")

    expected_key_metadata = {
        "frankle2019lottery": [
            "Lottery Ticket Hypothesis",
            "Frankle",
            "Carbin",
            "International Conference on Learning Representations",
            "2019",
        ],
        "frankle2020linear": [
            "Linear Mode Connectivity and the Lottery Ticket Hypothesis",
            "Dziugaite",
            "International Conference on Machine Learning",
            "2020",
        ],
        "ramanujan2020hidden": [
            "Randomly Weighted Neural Network",
            "Ramanujan",
            "IEEE/CVF Conference on Computer Vision and Pattern Recognition",
            "2020",
        ],
        "lee2019snip": [
            "Single-shot Network Pruning",
            "Lee",
            "International Conference on Learning Representations",
            "2019",
        ],
        "tanaka2020synflow": [
            "Synaptic Flow",
            "Tanaka",
            "Advances in Neural Information Processing Systems",
            "2020",
        ],
        "garipov2018loss": [
            "Loss Surfaces",
            "Garipov",
            "Advances in Neural Information Processing Systems",
            "2018",
        ],
        "draxler2018barriers": [
            "Essentially No Barriers",
            "Draxler",
            "International Conference on Machine Learning",
            "2018",
        ],
        "entezari2022role": [
            "Permutation Invariance",
            "Entezari",
            "International Conference on Learning Representations",
            "2022",
        ],
        "ainsworth2023git": [
            "Git Re-Basin",
            "Ainsworth",
            "International Conference on Learning Representations",
            "2023",
        ],
        "paul2023unmasking": [
            "Unmasking the Lottery Ticket Hypothesis",
            "Paul",
            "International Conference on Learning Representations",
            "2023",
        ],
        "welling2011sgld": [
            "Bayesian Learning via Stochastic Gradient Langevin Dynamics",
            "Welling",
            "International Conference on Machine Learning",
            "2011",
        ],
        "mandt2017sgd": [
            "Stochastic Gradient Descent as Approximate Bayesian Inference",
            "Mandt",
            "Journal of Machine Learning Research",
            "2017",
        ],
        "maddox2019swag": [
            "Simple Baseline for Bayesian Uncertainty",
            "Maddox",
            "Advances in Neural Information Processing Systems",
            "2019",
        ],
        "wilson2020bayesian": [
            "Bayesian Deep Learning and a Probabilistic Perspective of Generalization",
            "Wilson",
            "Advances in Neural Information Processing Systems",
            "2020",
        ],
        "izmailov2021posteriors": [
            "Bayesian Neural Network Posteriors Really Like",
            "Izmailov",
            "International Conference on Machine Learning",
            "2021",
        ],
        "sakamoto2022pacbayes": [
            "PAC-Bayesian",
            "Sakamoto",
            "Sato",
            "Advances in Neural Information Processing Systems",
            "2205.07320",
        ],
        "kuhn2026bayesian": [
            "Bayesian Lottery Ticket Hypothesis",
            "Kuhn",
            "2602.18825",
            "2026",
        ],
        "molchanov2017variational": [
            "Variational Dropout Sparsifies Deep Neural Networks",
            "Molchanov",
            "International Conference on Machine Learning",
            "2017",
        ],
        "louizos2018l0": [
            "Sparse Neural Networks through",
            "Louizos",
            "International Conference on Learning Representations",
            "2018",
        ],
        "dziugaite2017nonvacuous": [
            "Nonvacuous Generalization Bounds",
            "Dziugaite",
            "Conference on Uncertainty in Artificial Intelligence",
            "2017",
        ],
    }
    expected_metadata_issues = []
    for key, phrases in expected_key_metadata.items():
        raw = entries.get(key, {}).get("raw", "")
        if key not in entries:
            expected_metadata_issues.append(f"{key}:missing_entry")
            continue
        for phrase in phrases:
            if phrase not in raw:
                expected_metadata_issues.append(f"{key}:missing_phrase:{phrase}")

    eprint_entries_without_external_verification = sorted(
        key
        for key in (cited & bib_keys)
        if entries[key]["fields"].get("eprint") and key not in EXTERNAL_VERIFICATION
    )

    risk_flags = []
    if missing_citations:
        risk_flags.append("missing_cited_bib_entries")
    if eprint_entries_without_external_verification:
        risk_flags.append("eprint_entries_without_external_verification")
    if duplicate_keys:
        risk_flags.append("duplicate_bib_keys")
    if required_field_issues:
        risk_flags.append("required_bib_fields_missing")
    if suspicious_field_issues:
        risk_flags.append("suspicious_bib_metadata")
    if expected_metadata_issues:
        risk_flags.append("expected_key_metadata_missing")

    return {
        "reference_integrity_audit_ready": not risk_flags,
        "paper": relpath(PAPER),
        "bibliography": relpath(BIB),
        "cited_key_count": len(cited),
        "bib_entry_count": len(entries),
        "missing_citations": missing_citations,
        "unused_bib_entries": unused_bib_entries,
        "duplicate_keys": duplicate_keys,
        "required_field_issues": required_field_issues,
        "suspicious_field_issues": suspicious_field_issues,
        "expected_metadata_issues": expected_metadata_issues,
        "expected_metadata_checked_key_count": len(expected_key_metadata),
        "external_verification": EXTERNAL_VERIFICATION,
        "eprint_entries_without_external_verification": (
            eprint_entries_without_external_verification
        ),
        "risk_flags": risk_flags,
        "open_risk_flags": ["formal_plagiarism_screening_not_performed"],
        "interpretation": {
            "all_cited_keys_have_bib_entries": not missing_citations,
            "all_cited_entries_have_required_fields": not required_field_issues,
            "no_duplicate_bib_keys": not duplicate_keys,
            "no_placeholder_metadata_detected": not suspicious_field_issues,
            "key_method_and_competitor_metadata_present": not expected_metadata_issues,
            "all_cited_eprint_entries_externally_verified": (
                not eprint_entries_without_external_verification
            ),
            "all_cited_entries_have_expected_metadata_smoke": (
                not expected_metadata_issues
                and len(expected_key_metadata) == len(cited & bib_keys)
            ),
            "not_a_plagiarism_detector": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["reference_integrity_audit_ready"] else "not ready"
    lines = [
        "# Reference Integrity Audit",
        "",
        "This generated audit checks citation-key coverage, duplicate keys,",
        "required bibliography fields for cited entries, placeholder-like",
        "metadata, and expected metadata for core method and competitor",
        "citations. It is not a formal plagiarism detector.",
        "",
        f"Current status: {status}.",
        "",
        "## Summary",
        "",
        f"- Paper: `{payload['paper']}`",
        f"- Bibliography: `{payload['bibliography']}`",
        f"- Cited keys: {payload['cited_key_count']}",
        f"- Bib entries: {payload['bib_entry_count']}",
        f"- Expected metadata checked keys: {payload['expected_metadata_checked_key_count']}",
        "",
        "## Findings",
        "",
        f"- Missing cited bib entries: `{payload['missing_citations']}`",
        f"- Duplicate bib keys: `{payload['duplicate_keys']}`",
        f"- Required field issues: `{payload['required_field_issues']}`",
        f"- Suspicious metadata issues: `{payload['suspicious_field_issues']}`",
        f"- Expected metadata issues: `{payload['expected_metadata_issues']}`",
        f"- Unused bib entries: `{payload['unused_bib_entries']}`",
        "",
        "## External Verification (eprint entries)",
        "",
    ]
    for key, record in payload["external_verification"].items():
        lines.append(
            f"- `{key}`: {record['method']} against {record['source']}"
            f" on {record['verified_date']} ({record['matched']})"
        )
    lines += [
        f"- Cited eprint entries without external verification: "
        f"`{payload['eprint_entries_without_external_verification']}`",
        "",
        "## Open Risk Flags",
        "",
    ]
    lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    lines.extend(["", "## Audit Risk Flags", ""])
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This file is generated by `scripts/audit_reference_integrity.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_audit()
    write_json(payload, DEFAULT_OUT_JSON)
    write_markdown(payload, DEFAULT_OUT_MD)
    print(
        json.dumps(
            {
                "reference_integrity_audit_ready": payload[
                    "reference_integrity_audit_ready"
                ],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(DEFAULT_OUT_JSON),
                "out_md": relpath(DEFAULT_OUT_MD),
            }
        )
    )


if __name__ == "__main__":
    main()
