#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from audit_paper_submission_shape import ROOT, pdf_page_count
from audit_venue_submission_compliance import (
    abstract_text,
    document_class,
    find_reference_start_page,
    latex_group,
    page_texts,
    word_count,
)


DEFAULT_OUT_JSON = ROOT / "runs" / "iclr_submission_readiness_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "iclr_submission_readiness_audit.md"

PROVISIONAL_PRIMARY_VENUE = "ICLR 2027"
FALLBACK_VENUES = ["AISTATS 2027", "AAAI 2027", "ICDM 2026"]
REFERENCE_POLICY = {
    "basis": "ICLR 2026 author guide and call-for-papers pattern",
    "official_2027_cfp_observed": False,
    "source_urls": [
        "https://iclr.cc/Conferences/2026/CallForPapers",
        "https://iclr.cc/Conferences/2026/AuthorGuide",
        "https://github.com/ICLR/Master-Template/raw/master/iclr2026.zip",
    ],
    "provisional_assumptions": [
        "double-blind submission",
        "10-page main-text budget before references",
        "references do not count toward the page limit",
        "supplementary material is allowed but reviewers are not required to read it",
        "reproducibility statement is strongly encouraged",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-tex", type=Path, default=ROOT / "paper" / "main.tex")
    parser.add_argument(
        "--main-submission-pdf",
        type=Path,
        default=ROOT / "paper" / "main_submission.pdf",
    )
    parser.add_argument("--max-main-pages", type=int, default=10)
    parser.add_argument("--max-abstract-words", type=int, default=250)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    return parser.parse_args()


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else {}


def contains_reproducibility_statement(text: str) -> bool:
    return bool(re.search(r"\\section\*?\{Reproducibility", text, flags=re.I)) or (
        "Reproducibility Statement" in text
    )


def add_if_present(target: list[str], source: dict[str, Any], key: str) -> None:
    for flag in source.get(key, []):
        if isinstance(flag, str) and flag not in target:
            target.append(flag)


def find_iclr_reference_start_page(pages: list[str]) -> int | None:
    generic_match = find_reference_start_page(pages)
    if generic_match is not None:
        return generic_match
    for page_num, text in enumerate(pages, start=1):
        compact = re.sub(r"[^A-Za-z]", "", text).lower()
        if "references" in compact:
            return page_num
    return None


def build_audit(
    *,
    paper_tex: Path,
    main_submission_pdf: Path,
    max_main_pages: int,
    max_abstract_words: int,
) -> dict[str, Any]:
    text = paper_tex.read_text(encoding="utf-8") if paper_tex.exists() else ""
    makefile_text = (ROOT / "Makefile").read_text(encoding="utf-8")
    title = latex_group(text, "title")
    author = latex_group(text, "author")
    abstract = abstract_text(text)
    abstract_words = word_count(abstract)
    page_count = pdf_page_count(main_submission_pdf)
    pages = page_texts(main_submission_pdf, page_count)
    reference_start_page = find_reference_start_page(pages)
    content_pages_before_references = (
        reference_start_page - 1 if reference_start_page is not None else page_count
    )
    iclr_pdf = ROOT / "paper" / "iclr_submission.pdf"
    iclr_page_count = pdf_page_count(iclr_pdf)
    iclr_pages = page_texts(iclr_pdf, iclr_page_count)
    iclr_reference_start_page = find_iclr_reference_start_page(iclr_pages)
    iclr_content_pages_before_references = (
        iclr_reference_start_page - 1
        if iclr_reference_start_page is not None
        else iclr_page_count
    )
    plagiarism_runbook = load_optional_json(
        ROOT / "runs" / "formal_plagiarism_screening_runbook.json"
    )
    plagiarism_receipt_audit = load_optional_json(
        ROOT / "runs" / "formal_plagiarism_screening_receipt_audit.json"
    )
    openreview_packet = load_optional_json(ROOT / "runs" / "iclr_openreview_packet.json")
    policy_watch = load_optional_json(ROOT / "runs" / "iclr_policy_watch_audit.json")
    policy_source_probe = load_optional_json(ROOT / "runs" / "iclr_policy_source_probe.json")
    llm_disclosure = load_optional_json(ROOT / "runs" / "llm_usage_disclosure_audit.json")
    ethics = load_optional_json(ROOT / "runs" / "ethics_statement_audit.json")
    human_confirmations = load_optional_json(
        ROOT / "runs" / "iclr_human_confirmation_template.json"
    )
    human_confirmation_receipt = load_optional_json(
        ROOT / "runs" / "iclr_human_confirmation_receipt_audit.json"
    )

    checks = {
        "paper_tex_exists": paper_tex.exists(),
        "document_class_article": document_class(text) == "article",
        "anonymous_author": author.strip() == "Anonymous",
        "title_present": bool(title),
        "abstract_present": bool(abstract),
        "abstract_within_250_words": abstract_words <= max_abstract_words,
        "main_submission_pdf_exists": main_submission_pdf.exists(),
        "main_submission_pdf_page_count_available": page_count is not None,
        "references_heading_found": reference_start_page is not None,
        "main_text_pages_before_references_within_budget": (
            content_pages_before_references is not None
            and content_pages_before_references <= max_main_pages
        ),
        "main_only_source_flag_wired": "LOTTERYMAINONLY" in text,
        "claim_ledger_present": (ROOT / "docs" / "paper_claim_ledger.md").exists(),
        "reproducibility_manifest_present": (
            ROOT / "docs" / "reproducibility_manifest.md"
        ).exists(),
        "release_manifest_present": (ROOT / "docs" / "public_release_manifest.md").exists(),
        "artifact_verifier_present": (
            ROOT / "scripts" / "verify_research_artifacts.py"
        ).exists(),
        "formal_reproducibility_statement_present": contains_reproducibility_statement(text),
        "ethics_statement_present": (
            (ROOT / "docs" / "ethics_statement_audit.md").exists()
            and ethics.get("ethics_statement_audit_ready") is True
        ),
        "llm_usage_disclosure_present": (
            (ROOT / "docs" / "llm_usage_disclosure_audit.md").exists()
            and llm_disclosure.get("llm_usage_disclosure_audit_ready") is True
        ),
        "iclr_policy_watch_present": (
            (ROOT / "docs" / "iclr_policy_watch_audit.md").exists()
            and policy_watch.get("iclr_policy_watch_audit_ready") is True
        ),
        "iclr_policy_source_probe_present": (
            (ROOT / "docs" / "iclr_policy_source_probe.md").exists()
            and policy_source_probe.get("iclr_policy_source_probe_ready") is True
        ),
        "iclr_policy_watch_uses_recorded_live_probe": (
            policy_watch.get("source_observation_mode")
            in {"live_probe", "recorded_live_probe"}
            and policy_watch.get("official_source_observations")
            == policy_source_probe.get("official_source_observations")
        ),
        "iclr_2026_policy_proxy_sources_observed": (
            policy_watch.get("proxy_policy_facts", {}).get("proxy_year") == "ICLR 2026"
            and policy_watch.get("proxy_policy_facts", {}).get("proxy_only_not_2027_policy")
            is True
        ),
        "formal_plagiarism_screening_runbook_present": (
            (ROOT / "docs" / "formal_plagiarism_screening_runbook.md").exists()
            and plagiarism_runbook.get("formal_plagiarism_screening_runbook_ready") is True
        ),
        "formal_plagiarism_receipt_fields_declared": (
            len(plagiarism_runbook.get("required_external_screening_receipt_fields", [])) >= 10
        ),
        "formal_plagiarism_receipt_intake_audit_present": (
            (ROOT / "docs" / "formal_plagiarism_screening_receipt_audit.md").exists()
            and plagiarism_receipt_audit.get(
                "formal_plagiarism_screening_receipt_audit_ready"
            )
            is True
        ),
        "iclr_openreview_packet_present": (
            (ROOT / "docs" / "iclr_openreview_packet.md").exists()
            and openreview_packet.get("iclr_openreview_packet_ready") is True
        ),
        "iclr_openreview_paste_payload_declared": (
            bool(openreview_packet.get("paste_payload", {}).get("title"))
            and bool(openreview_packet.get("paste_payload", {}).get("abstract"))
            and bool(openreview_packet.get("paste_payload", {}).get("paper_pdf"))
        ),
        "iclr_human_confirmation_template_present": (
            (ROOT / "docs" / "iclr_human_confirmation_template.md").exists()
            and human_confirmations.get("iclr_human_confirmation_template_ready") is True
        ),
        "iclr_human_confirmation_receipt_audit_present": (
            (ROOT / "docs" / "iclr_human_confirmation_receipt_audit.md").exists()
            and human_confirmation_receipt.get(
                "iclr_human_confirmation_receipt_audit_ready"
            )
            is True
        ),
        "iclr_style_file_present": (ROOT / "paper" / "iclr2026_conference.sty").exists(),
        "iclr_bibliography_style_present": (
            ROOT / "paper" / "iclr2026_conference.bst"
        ).exists(),
        "iclr_source_flag_wired": "LOTTERYICLR" in text,
        "iclr_make_target_present": "paper-existing-iclr" in makefile_text
        and "paper-iclr" in makefile_text,
        "iclr_submission_pdf_exists": iclr_pdf.exists(),
        "iclr_submission_pdf_page_count_available": iclr_page_count is not None,
        "iclr_references_heading_found": iclr_reference_start_page is not None,
        "iclr_main_text_pages_before_references_within_budget": (
            iclr_content_pages_before_references is not None
            and iclr_content_pages_before_references <= max_main_pages
        ),
    }

    risk_flags: list[str] = []
    for key in [
        "paper_tex_exists",
        "anonymous_author",
        "title_present",
        "abstract_present",
        "abstract_within_250_words",
        "main_submission_pdf_exists",
        "main_submission_pdf_page_count_available",
        "references_heading_found",
        "main_text_pages_before_references_within_budget",
        "main_only_source_flag_wired",
        "claim_ledger_present",
        "reproducibility_manifest_present",
        "artifact_verifier_present",
        "ethics_statement_present",
        "llm_usage_disclosure_present",
        "iclr_policy_watch_present",
        "iclr_policy_source_probe_present",
        "iclr_policy_watch_uses_recorded_live_probe",
        "iclr_2026_policy_proxy_sources_observed",
        "formal_plagiarism_screening_runbook_present",
        "formal_plagiarism_receipt_fields_declared",
        "formal_plagiarism_receipt_intake_audit_present",
        "iclr_openreview_packet_present",
        "iclr_openreview_paste_payload_declared",
        "iclr_human_confirmation_template_present",
        "iclr_human_confirmation_receipt_audit_present",
    ]:
        if checks.get(key) is not True:
            risk_flags.append(f"{key}_failed")

    open_risk_flags = [
    ]
    add_if_present(open_risk_flags, policy_watch, "open_risk_flags")
    if openreview_packet.get("iclr_openreview_packet_ready") is True:
        add_if_present(open_risk_flags, openreview_packet, "open_risk_flags")
    else:
        open_risk_flags.append("iclr_openreview_packet_not_prepared")
    add_if_present(open_risk_flags, human_confirmations, "open_risk_flags")
    add_if_present(open_risk_flags, human_confirmation_receipt, "open_risk_flags")
    iclr_style_checks = [
        "iclr_style_file_present",
        "iclr_bibliography_style_present",
        "iclr_source_flag_wired",
        "iclr_make_target_present",
    ]
    if any(checks.get(key) is not True for key in iclr_style_checks):
        open_risk_flags.append("iclr_style_binding_not_implemented")
    if not checks["iclr_submission_pdf_exists"]:
        open_risk_flags.append("iclr_style_pdf_not_built")
    elif (
        checks["iclr_submission_pdf_page_count_available"] is not True
        or checks["iclr_references_heading_found"] is not True
        or checks["iclr_main_text_pages_before_references_within_budget"] is not True
    ):
        open_risk_flags.append("iclr_style_pdf_shape_not_verified")
    if checks["formal_reproducibility_statement_present"] is not True:
        open_risk_flags.append("formal_iclr_reproducibility_statement_not_in_main_text")

    locked_protocol = load_optional_json(ROOT / "runs" / "locked_final_test_protocol_audit.json")
    add_if_present(open_risk_flags, locked_protocol, "open_risk_flags")
    validation_policy = load_optional_json(ROOT / "runs" / "validation_test_usage_policy_audit.json")
    add_if_present(open_risk_flags, validation_policy, "open_risk_flags")
    bn_smoke = load_optional_json(ROOT / "runs" / "validation_bn_smoke_audit.json")
    add_if_present(open_risk_flags, bn_smoke, "open_risk_flags")
    add_if_present(open_risk_flags, ethics, "open_risk_flags")
    add_if_present(open_risk_flags, llm_disclosure, "open_risk_flags")
    direct_seed = load_optional_json(ROOT / "runs" / "direct_mode_ticket_seed_level_audit.json")
    if direct_seed.get("direct_seed_level_audit_ready") is True:
        # Drop the "other direct rows incomplete" risk once the validation_bn
        # rerun plan reports that every saved_artifacts_* entry (the rerun
        # queue that fills the other direct rows) has been observed.
        plan_payload = load_optional_json(
            ROOT / "runs" / "validation_bn_rerun_plan.json"
        )
        saved_entries = [
            entry
            for entry in plan_payload.get("entries", [])
            if isinstance(entry, dict)
            and str(entry.get("name", "")).startswith("saved_artifacts_")
        ]
        saved_complete = bool(saved_entries) and all(
            entry.get("observed") for entry in saved_entries
        )
        if not saved_complete:
            open_risk_flags.append(
                "seed_level_saved_artifacts_incomplete_for_other_direct_rows"
            )
    external = load_optional_json(ROOT / "runs" / "external_validation_readiness_audit.json")
    add_if_present(open_risk_flags, external, "risk_flags")
    originality = load_optional_json(ROOT / "runs" / "manuscript_originality_audit.json")
    add_if_present(open_risk_flags, originality, "open_risk_flags")
    add_if_present(open_risk_flags, plagiarism_runbook, "open_risk_flags")
    add_if_present(open_risk_flags, plagiarism_receipt_audit, "open_risk_flags")

    unique_open_flags = list(dict.fromkeys(open_risk_flags))

    return {
        "iclr_submission_readiness_audit_ready": not risk_flags,
        "provisional_primary_venue": PROVISIONAL_PRIMARY_VENUE,
        "fallback_venues": FALLBACK_VENUES,
        "reference_policy": REFERENCE_POLICY,
        "paper_tex": relpath(paper_tex),
        "main_submission_pdf": relpath(main_submission_pdf),
        "checks": checks,
        "title": title,
        "abstract_word_count": abstract_words,
        "max_abstract_words": max_abstract_words,
        "pdf_page_count": page_count,
        "reference_start_page": reference_start_page,
        "content_pages_before_references": content_pages_before_references,
        "iclr_submission_pdf": relpath(iclr_pdf),
        "iclr_pdf_page_count": iclr_page_count,
        "iclr_reference_start_page": iclr_reference_start_page,
        "iclr_content_pages_before_references": iclr_content_pages_before_references,
        "max_main_pages_before_references": max_main_pages,
        "risk_flags": risk_flags,
        "open_risk_flags": unique_open_flags,
        "provisional_strategy_ready": not risk_flags,
        "iclr_submission_ready": not risk_flags and not unique_open_flags,
        "interpretation": {
            "recommended_primary_target": PROVISIONAL_PRIMARY_VENUE,
            "not_a_final_submission_gate": True,
            "local_shape_is_compatible_with_iclr_page_budget": (
                checks["main_text_pages_before_references_within_budget"] is True
            ),
            "provisional_iclr_style_build_available": (
                checks["iclr_style_file_present"] is True
                and checks["iclr_bibliography_style_present"] is True
                and checks["iclr_submission_pdf_exists"] is True
                and checks["iclr_main_text_pages_before_references_within_budget"] is True
            ),
            "must_not_claim_iclr_ready_until_open_risks_close": True,
            "venue_specific_reformatting_still_required": False,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["provisional_strategy_ready"] else "not ready"
    submission_status = "ready" if payload["iclr_submission_ready"] else "not ready"
    lines = [
        "# ICLR Submission Readiness Audit",
        "",
        "This generated audit records the provisional ICLR target strategy after",
        "venue triage. It uses the ICLR 2026 author-guide pattern as a temporary",
        "policy proxy because the official ICLR 2027 call has not been observed in",
        "this repository. This is not a final OpenReview submission gate.",
        "",
        f"Provisional strategy status: {status}.",
        f"Final ICLR submission status: {submission_status}.",
        f"Recommended primary target: `{payload['provisional_primary_venue']}`.",
        f"Fallback venues: {', '.join(f'`{venue}`' for venue in payload['fallback_venues'])}.",
        "",
        "## Policy Basis",
        "",
        f"- Basis: {payload['reference_policy']['basis']}",
        f"- Official 2027 CFP observed: `{payload['reference_policy']['official_2027_cfp_observed']}`",
        "- Scope marker: official 2027 CFP 미관측; author/COI and submission receipt confirmation remain open until the human confirmation receipt passes.",
        "- Source URLs:",
    ]
    lines.extend(f"  - {url}" for url in payload["reference_policy"]["source_urls"])
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Paper source | `{payload['paper_tex']}` |",
        f"| Main submission PDF | `{payload['main_submission_pdf']}` |",
        f"| ICLR-style submission PDF | `{payload['iclr_submission_pdf']}` |",
        f"| Abstract words | {payload['abstract_word_count']} |",
        f"| Abstract word budget | {payload['max_abstract_words']} |",
        f"| PDF pages | {payload['pdf_page_count']} |",
        f"| References start page | {payload['reference_start_page']} |",
        f"| Content pages before references | {payload['content_pages_before_references']} |",
        f"| ICLR-style PDF pages | {payload['iclr_pdf_page_count']} |",
        f"| ICLR-style references start page | {payload['iclr_reference_start_page']} |",
        f"| ICLR-style content pages before references | {payload['iclr_content_pages_before_references']} |",
        f"| Provisional main-page budget | {payload['max_main_pages_before_references']} |",
            "",
            "## Checks",
            "",
            "| Check | Pass |",
            "| --- | ---: |",
        ]
    )
    for key, value in sorted(payload["checks"].items()):
        lines.append(f"| {key} | {value} |")
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
            "## Recommended Action",
            "",
            "Use ICLR 2027 as the primary target only after the locked final-test row,",
            "full-CIFAR BatchNorm posterior-policy ablations, direct-row seed-level",
            "artifact coverage, ethics/LLM author confirmations, formal",
            "plagiarism screening, and external validation receipts are closed.",
            "Do not treat the packet as final while author/COI fields or the",
            "OpenReview submission receipt are absent.",
            "Until then, keep the paper wording scoped as an empirical negative",
            "result under tested posterior approximations.",
            f"The ethics statement audit is `docs/ethics_statement_audit.md`.",
            f"The LLM usage disclosure audit is `docs/llm_usage_disclosure_audit.md`.",
            f"The ICLR policy watch is `docs/iclr_policy_watch_audit.md`.",
            f"The provisional OpenReview packet is `docs/iclr_openreview_packet.md`.",
            f"The human confirmation template is `docs/iclr_human_confirmation_template.md`.",
            f"The human confirmation receipt audit is `docs/iclr_human_confirmation_receipt_audit.md`.",
            f"The formal screening runbook is `docs/formal_plagiarism_screening_runbook.md`.",
            f"The formal screening receipt intake audit is `docs/formal_plagiarism_screening_receipt_audit.md`.",
            "",
            "This file is generated by `scripts/audit_iclr_submission_readiness.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_audit(
        paper_tex=args.paper_tex,
        main_submission_pdf=args.main_submission_pdf,
        max_main_pages=args.max_main_pages,
        max_abstract_words=args.max_abstract_words,
    )
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "iclr_submission_readiness_audit_ready": payload[
                    "iclr_submission_readiness_audit_ready"
                ],
                "provisional_strategy_ready": payload["provisional_strategy_ready"],
                "iclr_submission_ready": payload["iclr_submission_ready"],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )


if __name__ == "__main__":
    main()
