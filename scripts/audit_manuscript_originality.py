#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "main.tex"
DEFAULT_OUT_JSON = ROOT / "runs" / "manuscript_originality_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "manuscript_originality_audit.md"

PLACEHOLDER_PATTERNS = [
    ("todo_marker", re.compile(r"\bTODO\b", re.IGNORECASE)),
    ("citation_needed", re.compile(r"citation needed", re.IGNORECASE)),
    ("placeholder_text", re.compile(r"\bplaceholder\b", re.IGNORECASE)),
    ("copied_text_marker", re.compile(r"\bcopied from\b", re.IGNORECASE)),
]

REQUIRED_SCOPE_PHRASES = [
    "under the posterior families and CIFAR-10/MNIST/Fashion-MNIST settings tested here",
    "controlled negative result under the posterior approximations we can currently test",
    "not as a theorem about all Bayesian neural-network posteriors",
    "Pooled direct mode/ticket p-values over posterior samples are descriptive",
    "locked final test rerun is still required",
    "BatchNorm buffers in sampled state dictionaries",
    "exact dense full-network CIFAR posterior remains absent",
]

FORBIDDEN_OVERCLAIM_PATTERNS = [
    ("sota_claim", re.compile(r"\bSOTA\b|state-of-the-art", re.IGNORECASE)),
    ("proof_claim", re.compile(r"\bprove(?:s|d)? that\b", re.IGNORECASE)),
    (
        "universal_bayesian_claim",
        re.compile(r"\bfor all Bayesian neural-network posteriors\b", re.IGNORECASE),
    ),
    (
        "external_validation_overclaim",
        re.compile(r"\bexternally validated\b", re.IGNORECASE),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", type=Path, default=PAPER)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    return parser.parse_args()


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def strip_environment(text: str, env: str) -> str:
    pattern = re.compile(
        rf"\\begin\{{{re.escape(env)}\}}.*?\\end\{{{re.escape(env)}\}}",
        re.DOTALL,
    )
    return pattern.sub(" ", text)


def strip_latex_to_prose(tex: str) -> str:
    for env in [
        "table",
        "tabular",
        "figure",
        "equation",
        "align",
        "quote",
        "verbatim",
    ]:
        tex = strip_environment(tex, env)
    tex = re.sub(r"%.*", " ", tex)
    tex = re.sub(r"\\cite[a-zA-Z*]*\{[^}]*\}", " CITATION ", tex)
    tex = re.sub(r"\\ref\{[^}]*\}", " REF ", tex)
    tex = re.sub(r"\\[a-zA-Z*]+(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", r" \1 ", tex)
    tex = re.sub(r"[$_^{}\\]", " ", tex)
    tex = re.sub(r"\s+", " ", tex)
    return tex.strip()


def sentence_split(prose: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", prose)
    sentences: list[str] = []
    for part in parts:
        sentence = " ".join(part.split()).strip()
        if not sentence:
            continue
        if len(sentence.split()) >= 14:
            sentences.append(sentence)
    return sentences


def normalize_sentence(sentence: str) -> str:
    lowered = sentence.lower()
    lowered = re.sub(r"[^a-z0-9%.\- ]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def find_duplicate_sentences(sentences: list[str]) -> list[dict[str, Any]]:
    normalized = [normalize_sentence(sentence) for sentence in sentences]
    counts = Counter(normalized)
    duplicates = []
    for norm, count in sorted(counts.items()):
        if count <= 1:
            continue
        if len(norm.split()) < 18:
            continue
        examples = [s for s, n in zip(sentences, normalized) if n == norm][:2]
        duplicates.append({"count": count, "sentence": examples[0]})
    return duplicates


def find_repeated_long_ngrams(sentences: list[str], n: int = 18) -> list[dict[str, Any]]:
    ngrams: Counter[str] = Counter()
    for sentence in sentences:
        words = normalize_sentence(sentence).split()
        for i in range(0, max(0, len(words) - n + 1)):
            ngram = " ".join(words[i : i + n])
            if "citation" in ngram:
                continue
            ngrams[ngram] += 1
    repeated = [
        {"count": count, "ngram": ngram}
        for ngram, count in ngrams.items()
        if count >= 3
    ]
    repeated.sort(key=lambda row: (-int(row["count"]), str(row["ngram"])))
    return repeated[:20]


def find_placeholders(tex: str) -> list[dict[str, str]]:
    findings = []
    for rule, pattern in PLACEHOLDER_PATTERNS:
        for match in pattern.finditer(tex):
            start = max(0, match.start() - 80)
            end = min(len(tex), match.end() + 80)
            findings.append(
                {
                    "rule": rule,
                    "context": " ".join(tex[start:end].split()),
                }
            )
    return findings


def related_work_citation_coverage(tex: str) -> dict[str, Any]:
    match = re.search(
        r"\\section\{Related Work\}(.*?)(?:\\section\{|\\subsection\{)",
        tex,
        flags=re.DOTALL,
    )
    if not match:
        return {
            "section_present": False,
            "paragraph_count": 0,
            "paragraphs_without_citation": [],
        }
    body = match.group(1)
    paragraphs = [
        " ".join(paragraph.split())
        for paragraph in re.split(r"\n\s*\n", body)
        if paragraph.strip()
    ]
    uncited = []
    for idx, paragraph in enumerate(paragraphs, start=1):
        prose = strip_latex_to_prose(paragraph)
        if len(prose.split()) < 20:
            continue
        if not re.search(r"\\cite[a-zA-Z*]*\{[^}]+\}", paragraph):
            if re.match(r"\s*Our contribution\b", prose):
                continue
            uncited.append({"paragraph": idx, "text": prose[:240]})
    return {
        "section_present": True,
        "paragraph_count": len(paragraphs),
        "paragraphs_without_citation": uncited,
    }


def _locked_final_test_observed() -> bool:
    """Mirror of the verifier helper: True iff locked-final-test row recorded."""
    p = ROOT / "runs" / "locked_final_test_protocol_audit.json"
    if not p.exists():
        return False
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    interpretation = data.get("interpretation", {}) if isinstance(data, dict) else {}
    return interpretation.get("locked_final_test_observed") is True


def required_scope_phrases() -> list[str]:
    """Return the active required-scope phrases for the current observation state.

    Once the locked final-test rerun is observed the "still required" caveat is no longer the correct wording; the paper
    must instead describe the completed rerun. The audit therefore swaps the required phrase in lock-step with the
    source-of-truth audit.
    """
    phrases = list(REQUIRED_SCOPE_PHRASES)
    if _locked_final_test_observed():
        phrases = [
            "locked final-test rerun has been completed"
            if phrase == "locked final test rerun is still required"
            else phrase
            for phrase in phrases
        ]
    return phrases


def find_claim_scope_findings(tex: str) -> dict[str, Any]:
    normalized = " ".join(tex.split())
    required = []
    for phrase in required_scope_phrases():
        required.append({"phrase": phrase, "present": phrase in normalized})
    forbidden = []
    for rule, pattern in FORBIDDEN_OVERCLAIM_PATTERNS:
        for match in pattern.finditer(tex):
            start = max(0, match.start() - 120)
            end = min(len(tex), match.end() + 120)
            forbidden.append(
                {
                    "rule": rule,
                    "context": " ".join(tex[start:end].split()),
                }
            )
    return {
        "required_scope_phrases": required,
        "forbidden_overclaim_findings": forbidden,
    }


def build_audit(paper: Path) -> dict[str, Any]:
    tex = paper.read_text(encoding="utf-8")
    prose = strip_latex_to_prose(tex)
    sentences = sentence_split(prose)
    duplicate_sentences = find_duplicate_sentences(sentences)
    repeated_ngrams = find_repeated_long_ngrams(sentences)
    placeholders = find_placeholders(tex)
    related_work = related_work_citation_coverage(tex)
    claim_scope = find_claim_scope_findings(tex)

    risk_flags = []
    if placeholders:
        risk_flags.append("placeholder_or_copy_marker_in_manuscript")
    if duplicate_sentences:
        risk_flags.append("duplicate_long_prose_sentences")
    if repeated_ngrams:
        risk_flags.append("repeated_long_prose_ngrams")
    if not related_work.get("section_present"):
        risk_flags.append("related_work_section_missing")
    if related_work.get("paragraphs_without_citation"):
        risk_flags.append("related_work_paragraph_without_citation")
    if any(not row["present"] for row in claim_scope["required_scope_phrases"]):
        risk_flags.append("required_claim_scope_phrase_missing")
    if claim_scope["forbidden_overclaim_findings"]:
        risk_flags.append("forbidden_overclaim_phrase_in_manuscript")

    return {
        "manuscript_originality_audit_ready": not risk_flags,
        "paper": relpath(paper),
        "sentence_count": len(sentences),
        "placeholder_findings": placeholders,
        "duplicate_sentence_findings": duplicate_sentences,
        "repeated_ngram_findings": repeated_ngrams,
        "related_work_citation_coverage": related_work,
        "claim_scope_audit": claim_scope,
        "risk_flags": risk_flags,
        "open_risk_flags": ["formal_external_plagiarism_database_screen_not_performed"],
        "interpretation": {
            "local_prose_screen_only": True,
            "not_a_formal_plagiarism_detector": True,
            "formal_external_screening_still_required": True,
            "claim_scope_overclaim_guard_enabled": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Manuscript Originality Audit",
        "",
        "This generated audit is a local prose screen for obvious originality",
        "risks in `paper/main.tex`. It is not a formal plagiarism detector and",
        "does not replace iThenticate, Turnitin, or venue-side corpus matching.",
        "",
        f"Audit ready: {payload['manuscript_originality_audit_ready']}.",
        f"Paper: `{payload['paper']}`.",
        f"Long prose sentences scanned: {payload['sentence_count']}.",
        "",
        "## Risk Flags",
        "",
    ]
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(["", "## Open Risk Flags", ""])
    lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    lines.extend(["", "## Placeholder/Copy Markers", ""])
    if payload["placeholder_findings"]:
        lines.append("| Rule | Context |")
        lines.append("| --- | --- |")
        for finding in payload["placeholder_findings"]:
            context = str(finding["context"]).replace("|", "\\|")
            lines.append(f"| {finding['rule']} | {context} |")
    else:
        lines.append("- none")
    lines.extend(["", "## Duplicate Long Sentences", ""])
    if payload["duplicate_sentence_findings"]:
        lines.append("| Count | Sentence |")
        lines.append("| ---: | --- |")
        for finding in payload["duplicate_sentence_findings"]:
            sentence = str(finding["sentence"]).replace("|", "\\|")
            lines.append(f"| {finding['count']} | {sentence} |")
    else:
        lines.append("- none")
    lines.extend(["", "## Repeated Long N-Grams", ""])
    if payload["repeated_ngram_findings"]:
        lines.append("| Count | N-gram |")
        lines.append("| ---: | --- |")
        for finding in payload["repeated_ngram_findings"]:
            ngram = str(finding["ngram"]).replace("|", "\\|")
            lines.append(f"| {finding['count']} | {ngram} |")
    else:
        lines.append("- none")
    related = payload["related_work_citation_coverage"]
    lines.extend(
        [
            "",
            "## Related Work Citation Coverage",
            "",
            f"- Section present: {related['section_present']}",
            f"- Paragraphs scanned: {related['paragraph_count']}",
        ]
    )
    uncited = related["paragraphs_without_citation"]
    if uncited:
        lines.append("- Paragraphs without citation:")
        for row in uncited:
            lines.append(f"  - paragraph {row['paragraph']}: {row['text']}")
    else:
        lines.append("- Paragraphs without citation: none")
    claim_scope = payload["claim_scope_audit"]
    lines.extend(
        [
            "",
            "## Claim Scope Guard",
            "",
            "Required scoped-claim phrases:",
            "",
            "| Present | Phrase |",
            "| ---: | --- |",
        ]
    )
    for row in claim_scope["required_scope_phrases"]:
        phrase = str(row["phrase"]).replace("|", "\\|")
        lines.append(f"| {row['present']} | {phrase} |")
    lines.extend(["", "Forbidden overclaim findings:", ""])
    if claim_scope["forbidden_overclaim_findings"]:
        lines.append("| Rule | Context |")
        lines.append("| --- | --- |")
        for finding in claim_scope["forbidden_overclaim_findings"]:
            context = str(finding["context"]).replace("|", "\\|")
            lines.append(f"| {finding['rule']} | {context} |")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This file is generated by `scripts/audit_manuscript_originality.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_audit(args.paper)
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "manuscript_originality_audit_ready": payload[
                    "manuscript_originality_audit_ready"
                ],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if payload["risk_flags"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
