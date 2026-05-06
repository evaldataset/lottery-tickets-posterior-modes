#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "venue_strategy_matrix.json"
DEFAULT_OUT_MD = ROOT / "docs" / "venue_strategy_matrix.md"
DEFAULT_SOURCE_PROBE_JSON = ROOT / "runs" / "venue_source_probe.json"
DEFAULT_SOURCE_PROBE_MD = ROOT / "docs" / "venue_source_probe.md"
AUDIT_DATE = date(2026, 5, 13)

OFFICIAL_SOURCE_TARGETS = [
    {
        "role": "iclr_2027_cfp_candidate",
        "venue": "ICLR 2027",
        "url": "https://iclr.cc/Conferences/2027/CallForPapers",
        "expected_http_status_until_posted": 404,
        "expected_keywords": [],
    },
    {
        "role": "iclr_2026_cfp_proxy",
        "venue": "ICLR 2027",
        "url": "https://iclr.cc/Conferences/2026/CallForPapers",
        "expected_http_status": 200,
        "expected_keywords": ["Call for Papers", "Final decisions"],
    },
    {
        "role": "aistats_2026_cfp_proxy",
        "venue": "AISTATS 2027",
        "url": "https://virtual.aistats.org/Conferences/2026/CallForPapers",
        "expected_http_status": 200,
        "expected_keywords": [
            "September 25, 2025",
            "October 2, 2025",
        ],
    },
    {
        "role": "aaai_26_main_track_proxy",
        "venue": "AAAI 2027",
        "url": "https://aaai.org/conference/aaai/aaai-26/main-technical-track-call/",
        "expected_http_status": 200,
        "expected_keywords": [
            "July 25, 2025",
            "August 1, 2025",
            "Full papers due",
        ],
    },
    {
        "role": "icdm_2026_research_track",
        "venue": "ICDM 2026",
        "url": "https://www3.cs.stonybrook.edu/~icdm2026/dates/list.htm",
        "expected_http_status": 200,
        "expected_keywords": ["Full Paper Submission", "June 06, 2026"],
    },
    {
        "role": "cikm_2026_full_research",
        "venue": "CIKM 2026",
        "url": "https://cikm2026.diag.uniroma1.it/full-research-papers/",
        "expected_http_status": 200,
        "expected_keywords": [
            "May 16, 2026",
            "May 23, 2026",
            "Full Paper Submission Deadline",
        ],
    },
    {
        "role": "bigdata_2026_cfp",
        "venue": "BIGDATA 2026",
        "url": "https://bigdataieee.org/BigData2026/calls/papers/",
        "expected_http_status": 200,
        "expected_keywords": ["Aug. 21, 2026", "Phoenix, AZ"],
    },
    {
        "role": "wsdm_2027_host_bid_page",
        "venue": "WSDM 2027",
        "url": "https://www.wsdm-conference.org/calls.php",
        "expected_http_status": 200,
        "expected_keywords": ["Call for Bids to Host WSDM 2027", "Asia or Oceania"],
    },
    {
        "role": "emnlp_2026_main_cfp",
        "venue": "EMNLP 2026",
        "url": "https://2026.emnlp.org/calls/main_conference_papers/",
        "expected_http_status": 200,
        "expected_keywords": ["ARR submission deadline", "May 25, 2026"],
    },
    {
        "role": "webconf_series_2027_listing",
        "venue": "WWW 2027",
        "url": "https://thewebconf.org/",
        "expected_http_status": 200,
        "expected_keywords": ["The ACM Web Conference 2027", "Date TBD"],
    },
    {
        "role": "icde_2027_research_track",
        "venue": "ICDE 2027",
        "url": "https://icde2027.github.io/cf-research-papers.html",
        "expected_http_status": 200,
        "expected_keywords": [
            "ICDE 2027 Call for Research Papers",
            "June 11, 2026",
            "November 11, 2026",
        ],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", type=Path, default=ROOT / "paper" / "main.tex")
    parser.add_argument(
        "--iclr-readiness",
        type=Path,
        default=ROOT / "runs" / "iclr_submission_readiness_audit.json",
    )
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--source-probe-json", type=Path, default=DEFAULT_SOURCE_PROBE_JSON)
    parser.add_argument("--source-probe-md", type=Path, default=DEFAULT_SOURCE_PROBE_MD)
    parser.add_argument(
        "--live-probe",
        action="store_true",
        help="Probe official venue source URLs and persist a source-probe receipt.",
    )
    parser.add_argument("--probe-timeout", type=float, default=15.0)
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
    text = text.replace(r"\\", " ")
    text = text.replace(r"\_", "_").replace(r"\&", "&")
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def days_until(deadline: str | None) -> int | None:
    if not deadline:
        return None
    return (date.fromisoformat(deadline) - AUDIT_DATE).days


def probe_official_sources(timeout: float) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for row in OFFICIAL_SOURCE_TARGETS:
        request = Request(row["url"], headers={"User-Agent": "Mozilla/5.0 research-audit"})
        http_status: int | None = None
        final_url = row["url"]
        probe_error = None
        body_text = ""
        try:
            with urlopen(request, timeout=timeout) as response:
                http_status = int(response.status)
                final_url = response.geturl()
                body_text = response.read(300_000).decode("utf-8", errors="ignore")
        except HTTPError as exc:
            http_status = int(exc.code)
            final_url = exc.geturl()
            try:
                body_text = exc.read(300_000).decode("utf-8", errors="ignore")
            except Exception:
                body_text = ""
        except URLError as exc:
            probe_error = str(exc.reason)
        expected_keywords = [str(item) for item in row.get("expected_keywords", [])]
        keyword_hits = {
            keyword: keyword.lower() in body_text.lower() for keyword in expected_keywords
        }
        expected_status = row.get("expected_http_status")
        expected_status_until_posted = row.get("expected_http_status_until_posted")
        status_matches = (
            http_status == expected_status
            if expected_status is not None
            else http_status == expected_status_until_posted
            if expected_status_until_posted is not None
            else http_status is not None
        )
        expected_keywords_found = all(keyword_hits.values()) if keyword_hits else True
        source_probe_ok = bool(status_matches and expected_keywords_found and probe_error is None)
        observations.append(
            {
                "role": row["role"],
                "venue": row["venue"],
                "url": row["url"],
                "observed_http_status": http_status,
                "observed_final_url": final_url,
                "expected_http_status": expected_status,
                "expected_http_status_until_posted": expected_status_until_posted,
                "keyword_hits": keyword_hits,
                "source_probe_ok": source_probe_ok,
                "official_source_observed": bool(
                    http_status == 200 and expected_keywords_found and probe_error is None
                ),
                "probe_error": probe_error,
                "observation_source": "live_probe",
            }
        )
    return observations


def write_source_probe(
    *,
    observations: list[dict[str, Any]],
    out_json: Path,
    out_md: Path,
) -> None:
    probe = {
        "venue_source_probe_ready": all(row.get("source_probe_ok") is True for row in observations),
        "observed_date": AUDIT_DATE.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "official_source_observations": observations,
        "target_count": len(observations),
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(probe, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Venue Source Probe",
        "",
        f"Observed date: `{probe['observed_date']}`.",
        f"Probe ready: `{probe['venue_source_probe_ready']}`.",
        "",
        "| Venue | Role | URL | HTTP status | Probe OK | Official source observed | Error |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in observations:
        lines.append(
            "| {venue} | {role} | {url} | {status} | {ok} | {observed} | {error} |".format(
                venue=row["venue"],
                role=row["role"],
                url=row["url"],
                status=row.get("observed_http_status"),
                ok=row.get("source_probe_ok"),
                observed=row.get("official_source_observed"),
                error=row.get("probe_error") or "",
            )
        )
    lines.extend(
        [
            "",
            "This file is generated by `scripts/build_venue_strategy_matrix.py --live-probe`.",
        ]
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_source_probe(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "static_snapshot"
    payload = load_optional_json(path)
    observations = payload.get("official_source_observations", [])
    if not isinstance(observations, list) or not observations:
        return [], "static_snapshot"
    return observations, "recorded_live_probe"


def venue_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "venue": "TMLR (rolling)",
            "rank": 1,
            "recommendation": "primary target",
            "score": 96,
            "deadline": "rolling submission; no fixed deadline",
            "deadline_iso": None,
            "deadline_status": "rolling_submission_no_fixed_deadline",
            "source_urls": [
                "https://www.jmlr.org/tmlr/",
                "https://www.jmlr.org/tmlr/editorial-policies.html",
            ],
            "source_observation": (
                "TMLR uses rolling submission with a published editorial policy. "
                "Acceptance criterion is explicitly limited to correctness and "
                "support for claims; novelty/significance is not a rejection ground."
            ),
            "scope_fit": "excellent",
            "why_fit": (
                "TMLR's correctness-only acceptance criterion is the natural fit for "
                "a controlled negative-result audit. No page limit accommodates the "
                "operational gate, twelve-posterior-approximation harness, theory "
                "Proposition, locked final-test confirmation, and reusable audit "
                "framework as first-class contributions. Rolling decisions remove "
                "deadline-driven scope cuts and let the manuscript ship at full "
                "evidence density. The local TMLR packet (paste payload, snapshot, "
                "operator handoff bundle, final-gate audit) is already prepared; "
                "only author OpenReview profile, COI, and ethics confirmations "
                "remain."
            ),
            "required_reframing": (
                "Foreground the operational support-equivalence gate, the "
                "trajectory/process positive account, and the audit framework as "
                "three first-class contributions, with the negative empirical "
                "result as the central evidence rather than the sole contribution."
            ),
            "main_risk": (
                "Author OpenReview profile, COI/ethics/LLM/funding confirmations, "
                "and the external CUDA-host GPU-container receipt remain "
                "outstanding; these are blocking for submission but do not require "
                "any further empirical work."
            ),
        },
        {
            "venue": "ICLR 2027",
            "rank": 2,
            "recommendation": "high-visibility backup",
            "score": 88,
            "deadline": "September 2026 expected from ICLR 2026 pattern",
            "deadline_iso": None,
            "deadline_status": "official_iclr_2027_cfp_not_observed; 2026 official pattern only",
            "source_urls": [
                "https://iclr.cc/Conferences/2027/CallForPapers",
                "https://iclr.cc/Conferences/2027/AuthorGuide",
                "https://iclr.cc/Conferences/2026/CallForPapers",
            ],
            "source_observation": (
                "Official 2027 CFP/Author Guide URLs are not observed; 2026 CFP is "
                "the only recorded official policy proxy."
            ),
            "scope_fit": "excellent",
            "why_fit": (
                "Core ML audience for posterior approximations, Bayesian deep learning, "
                "optimization, representation learning, pruning, and empirical negative results."
            ),
            "required_reframing": (
                "Keep the paper framed as a falsifiable support-equivalence audit, not "
                "as a universal Bayesian-pruning impossibility claim."
            ),
            "main_risk": (
                "Official 2027 CFP/author guide not observed; locked final-test, BN "
                "ablation, formal screening, and external validation remain open."
            ),
        },
        {
            "venue": "AISTATS 2027",
            "rank": 3,
            "recommendation": "statistics-audience backup",
            "score": 86,
            "deadline": "October 2026 expected from AISTATS 2026 pattern",
            "deadline_iso": None,
            "deadline_status": "official_2027_cfp_not_observed; 2026 official pattern only",
            "source_urls": [
                "https://virtual.aistats.org/Conferences/2026/CallForPapers",
            ],
            "source_observation": (
                "Official AISTATS 2027 CFP is not observed. Official AISTATS 2026 "
                "CFP lists abstract September 25, 2025 AOE and full paper October "
                "2, 2025 AOE, so October 2026 remains a pattern-based estimate."
            ),
            "scope_fit": "strong",
            "why_fit": (
                "Bayesian posterior support, approximation diagnostics, and statistical "
                "audit framing are natural for the AI/statistics audience."
            ),
            "required_reframing": (
                "Move statistical reliability, hierarchical/seed-level tests, and "
                "posterior-support diagnostics to the foreground."
            ),
            "main_risk": (
                "Current paper reads more like pruning/representation-learning than "
                "statistics unless the test design and uncertainty analysis are emphasized."
            ),
        },
        {
            "venue": "AAAI 2027",
            "rank": 4,
            "recommendation": "broad-AI backup",
            "score": 78,
            "deadline": "late July to early August 2026 per user-provided schedule; official CFP not verified here",
            "deadline_iso": None,
            "deadline_status": "user_supplied_deadline; official_aaai_2027_cfp_not_observed",
            "source_urls": [
                "https://aaai.org/conference/aaai/aaai-26/main-technical-track-call/",
            ],
            "source_observation": (
                "Official AAAI 2027 CFP is not observed. Official AAAI-26 main "
                "technical track lists July 25, 2025 abstract and August 1, 2025 "
                "full-paper deadlines, supporting only a pattern-based 2027 estimate."
            ),
            "scope_fit": "moderate_to_strong",
            "why_fit": (
                "Broad AI venue can absorb pruning, Bayesian learning, and empirical "
                "methodology if the contribution is made concise and general."
            ),
            "required_reframing": (
                "Compress the argument around one clear reviewer-facing contribution "
                "and keep artifact details in supplementary material."
            ),
            "main_risk": (
                "Shorter main-paper format and broad reviewer pool increase the risk "
                "of 'incremental negative result' reviews."
            ),
        },
        {
            "venue": "ICDM 2026",
            "rank": 5,
            "recommendation": "emergency fallback only",
            "score": 64,
            "deadline": "June 6, 2026",
            "deadline_iso": "2026-06-06",
            "deadline_status": "official deadline observed",
            "source_urls": [
                "https://www3.cs.stonybrook.edu/~icdm2026/",
                "https://www3.cs.stonybrook.edu/~icdm2026/dates/list.htm",
            ],
            "source_observation": (
                "Official IEEE ICDM 2026 research-track and dates pages list June "
                "6, 2026 as the full-paper submission deadline."
            ),
            "scope_fit": "moderate",
            "why_fit": (
                "Machine learning and deep learning are in scope, but the paper is not "
                "primarily a data-mining algorithm or application paper."
            ),
            "required_reframing": (
                "Present the work as a reproducible data-mining/ML evaluation protocol "
                "for sparse neural model discovery."
            ),
            "main_risk": (
                "Less natural audience than ICLR/AISTATS; deadline leaves limited time "
                "to close locked final-test and BN risks."
            ),
        },
        {
            "venue": "CIKM 2026",
            "rank": 6,
            "recommendation": "do not target unless rescoping radically",
            "score": 53,
            "deadline": "May 16, 2026 abstract; May 23, 2026 full paper",
            "deadline_iso": "2026-05-23",
            "deadline_status": "official deadline observed",
            "source_urls": ["https://cikm2026.diag.uniroma1.it/full-research-papers/"],
            "source_observation": (
                "Official CIKM 2026 full-research page lists May 16, 2026 abstract "
                "deadline and May 23, 2026 full-paper deadline."
            ),
            "scope_fit": "weak_to_moderate",
            "why_fit": (
                "CIKM covers AI/data science, but its core identity is information "
                "retrieval, knowledge management, and databases."
            ),
            "required_reframing": (
                "Would need a data/knowledge discovery angle that the current paper "
                "does not naturally have."
            ),
            "main_risk": "Deadline is too close for the current unresolved top-tier blockers.",
        },
        {
            "venue": "BIGDATA 2026",
            "rank": 7,
            "recommendation": "low-priority fallback",
            "score": 49,
            "deadline": "August 21, 2026",
            "deadline_iso": "2026-08-21",
            "deadline_status": "official deadline observed",
            "source_urls": ["https://bigdataieee.org/BigData2026/calls/papers/"],
            "source_observation": (
                "Official IEEE BigData 2026 CFP lists August 21, 2026 as the full "
                "paper submission deadline and Dec 14-17, 2026 in Phoenix."
            ),
            "scope_fit": "weak_to_moderate",
            "why_fit": (
                "The venue emphasizes big-data foundations, infrastructure, 5V data "
                "challenges, and applications; this paper is a model-analysis study."
            ),
            "required_reframing": (
                "Would need a scalability or big-data systems angle rather than only "
                "CIFAR/MNIST posterior diagnostics."
            ),
            "main_risk": "Scope mismatch and lower strategic value for the current contribution.",
        },
        {
            "venue": "WSDM 2027",
            "rank": 8,
            "recommendation": "do not target",
            "score": 43,
            "deadline": "August 11, 2026 per user-provided schedule; official 2027 CFP not verified here",
            "deadline_iso": "2026-08-11",
            "deadline_status": "user_supplied_deadline; 2027 official CFP not observed",
            "source_urls": ["https://www.wsdm-conference.org/calls.php"],
            "source_observation": (
                "Official WSDM site currently exposes a call for WSDM 2027 host "
                "bids in Asia/Oceania, not a 2027 paper CFP. The August 11, 2026 "
                "paper deadline remains user-supplied and unverified."
            ),
            "scope_fit": "weak",
            "why_fit": "WSDM is search and web data mining; the paper has no web/search task.",
            "required_reframing": (
                "Would need a web-scale search, recommendation, or social/web mining "
                "problem, which would be a different paper."
            ),
            "main_risk": "High desk-review or reviewer-fit risk from scope mismatch.",
        },
        {
            "venue": "EMNLP 2026",
            "rank": 9,
            "recommendation": "do not target",
            "score": 40,
            "deadline": "May 25, 2026 ARR deadline",
            "deadline_iso": "2026-05-25",
            "deadline_status": "official deadline observed",
            "source_urls": ["https://2026.emnlp.org/calls/main_conference_papers/"],
            "source_observation": (
                "Official EMNLP 2026 main conference CFP lists May 25, 2026 as the "
                "ARR submission deadline and August 2, 2026 as the EMNLP commitment deadline."
            ),
            "scope_fit": "weak",
            "why_fit": "The paper has no NLP task, language data, or language-model result.",
            "required_reframing": (
                "Would require new NLP experiments and a language-model interpretation "
                "angle, not just a style conversion."
            ),
            "main_risk": "Scope mismatch plus very short deadline.",
        },
        {
            "venue": "WWW 2027",
            "rank": 10,
            "recommendation": "do not target",
            "score": 34,
            "deadline": "November 2026 per user-provided schedule; official 2027 CFP not verified here",
            "deadline_iso": None,
            "deadline_status": "user_supplied_deadline; 2027 official CFP not observed",
            "source_urls": [
                "https://thewebconf.org/",
                "https://www2026.thewebconf.org/calls/research-tracks.html",
            ],
            "source_observation": (
                "Official TheWebConf series page lists The ACM Web Conference 2027 "
                "in Dublin with date TBD. A 2027 research-track CFP is not observed; "
                "November 2026 remains a user-supplied estimate."
            ),
            "scope_fit": "poor",
            "why_fit": (
                "The Web Conference requires explicit relevance to Web systems or "
                "Web-related scientific questions; this paper is general ML."
            ),
            "required_reframing": "Would require a real Web problem and new evidence.",
            "main_risk": "Likely out of scope without major new Web-centered experiments.",
        },
        {
            "venue": "ICDE 2027",
            "rank": 11,
            "recommendation": "do not target",
            "score": 30,
            "deadline": "June 11, 2026 first round; November 11, 2026 second round",
            "deadline_iso": "2026-06-11",
            "deadline_status": "official deadline observed",
            "source_urls": ["https://icde2027.github.io/cf-research-papers.html"],
            "source_observation": (
                "Official IEEE ICDE 2027 research-track CFP lists two submission "
                "rounds: June 11, 2026 and November 11, 2026."
            ),
            "scope_fit": "poor",
            "why_fit": (
                "ICDE is a data-engineering venue; prior ICDE guidance flags pure ML "
                "without data-management aspects as out of scope."
            ),
            "required_reframing": "Would require data management, scalability, or system contribution.",
            "main_risk": "Strong scope mismatch.",
        },
    ]
    for row in rows:
        row["days_until_exact_deadline"] = days_until(row.get("deadline_iso"))
    return rows


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    paper_text = args.paper.read_text(encoding="utf-8") if args.paper.exists() else ""
    iclr = load_optional_json(args.iclr_readiness)
    if args.live_probe:
        source_observations = probe_official_sources(args.probe_timeout)
        source_observation_mode = "live_probe"
        write_source_probe(
            observations=source_observations,
            out_json=args.source_probe_json,
            out_md=args.source_probe_md,
        )
    else:
        source_observations, source_observation_mode = load_source_probe(
            args.source_probe_json
        )
    rows = venue_rows()
    primary = rows[0]
    risk_flags: list[str] = []
    if primary["venue"] != "TMLR (rolling)":
        risk_flags.append("primary_venue_not_tmlr_rolling")
    if rows[1]["venue"] != "ICLR 2027":
        risk_flags.append("first_backup_not_iclr_2027")
    if not args.paper.exists():
        risk_flags.append("paper_source_missing")
    # ICLR readiness still reports ICLR 2027 as its provisional target venue
    # (it audits the ICLR-style submission packet), which is unchanged. The
    # TMLR-primary strategy makes ICLR a high-visibility backup, not a
    # replacement target.
    if iclr.get("provisional_primary_venue") not in (None, "ICLR 2027"):
        risk_flags.append("iclr_readiness_disagrees_with_venue_strategy")

    open_risk_flags = [
        "iclr_2027_official_cfp_not_observed",
        "iclr_2027_official_author_guide_not_observed",
        "aistats_2027_official_cfp_not_observed",
        "aaai_2027_official_cfp_not_observed",
        "wsdm_2027_official_cfp_not_observed",
        "www_2027_official_cfp_not_observed",
    ]
    for flag in iclr.get("open_risk_flags", []):
        if isinstance(flag, str) and flag not in open_risk_flags:
            open_risk_flags.append(flag)

    return {
        "venue_strategy_matrix_ready": not risk_flags,
        "not_a_final_submission_gate": True,
        "audit_date": AUDIT_DATE.isoformat(),
        "source_observation_mode": source_observation_mode,
        "source_probe_json": relpath(args.source_probe_json),
        "source_probe_md": relpath(args.source_probe_md),
        "paper": {
            "source": relpath(args.paper),
            "title": normalize_tex_text(tex_block(paper_text, "title")),
        },
        "decision": {
            "primary_target": "TMLR (rolling)",
            "first_backup": "ICLR 2027",
            "second_backup": "AISTATS 2027",
            "emergency_fallback": "ICDM 2026",
            "do_not_chase_fast_deadlines": ["CIKM 2026", "EMNLP 2026"],
            "rationale": (
                "The current contribution is a controlled negative-result audit "
                "with a positive trajectory/process account, a Proposition, a "
                "locked final-test confirmation, and a reusable posterior-vs-IMP "
                "audit framework. TMLR's correctness-only acceptance criterion "
                "(novelty is explicitly not a rejection ground) and absence of a "
                "page limit accommodate this evidence density without forced "
                "scope cuts, and the local TMLR packet is already prepared, "
                "leaving only author OpenReview/COI inputs. ICLR 2027 remains a "
                "high-visibility backup once the official 2027 CFP is observed."
            ),
        },
        "source_probe_observations": source_observations,
        "rows": rows,
        "official_source_summary": [
            {
                "venue": row["venue"],
                "deadline_status": row["deadline_status"],
                "source_observation": row["source_observation"],
                "source_urls": row["source_urls"],
            }
            for row in rows
        ],
        "risk_flags": risk_flags,
        "open_risk_flags": list(dict.fromkeys(open_risk_flags)),
        "required_before_primary_submission": [
            "run the locked final-test row from the validation-selected config",
            "run full-CIFAR BatchNorm posterior-policy ablations",
            "complete seed-level saved-artifact coverage for remaining direct rows or downscope the pooled statistics",
            "complete formal external plagiarism/corpus screening",
            "record final author OpenReview/COI/ethics/LLM confirmations",
            "collect public release, public repository, external CI, and external CUDA/GPU receipts",
            "submit the prepared TMLR packet via OpenReview after recording author OpenReview profile, COI, and ethics confirmations",
        ],
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    decision = payload["decision"]
    lines = [
        "# Venue Strategy Matrix",
        "",
        f"Audit date: `{payload['audit_date']}`.",
        f"Source observation mode: `{payload['source_observation_mode']}`.",
        f"Source probe: `{payload['source_probe_md']}`.",
        "",
        "This generated matrix records the venue triage for the current paper. It is",
        "a submission-planning artifact, not a final submission-readiness gate.",
        "",
        "## Decision",
        "",
        f"- Primary target: `{decision['primary_target']}`",
        f"- First backup: `{decision['first_backup']}`",
        f"- Second backup: `{decision['second_backup']}`",
        f"- Emergency fallback: `{decision['emergency_fallback']}`",
        f"- Do not chase fast deadlines: {', '.join(f'`{v}`' for v in decision['do_not_chase_fast_deadlines'])}",
        f"- Rationale: {decision['rationale']}",
        "",
        "## Ranking",
        "",
        "| Rank | Venue | Score | Recommendation | Deadline | Deadline status | Scope fit |",
        "| ---: | --- | ---: | --- | --- | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| {rank} | `{venue}` | {score} | {recommendation} | {deadline} | {deadline_status} | {scope_fit} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Venue Notes",
            "",
        ]
    )
    for row in payload["rows"]:
        lines.extend(
            [
                f"### {row['venue']}",
                "",
                f"- Why it fits or fails: {row['why_fit']}",
                f"- Required reframing: {row['required_reframing']}",
                f"- Main risk: {row['main_risk']}",
                "- Source URLs:",
            ]
        )
        lines.extend(f"  - {url}" for url in row["source_urls"])
        lines.append("")
    lines.extend(["## Official Source Observations", ""])
    for row in payload["official_source_summary"]:
        lines.extend(
            [
                f"### {row['venue']}",
                "",
                f"- Deadline status: {row['deadline_status']}",
                f"- Observation: {row['source_observation']}",
                "- Sources:",
            ]
        )
        lines.extend(f"  - {url}" for url in row["source_urls"])
        lines.append("")
    lines.extend(["## Open Risks", ""])
    if payload["open_risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Required Before Primary Submission",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["required_before_primary_submission"])
    lines.extend(
        [
            "",
            "This file is generated by `scripts/build_venue_strategy_matrix.py`.",
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
                "venue_strategy_matrix_ready": payload["venue_strategy_matrix_ready"],
                "primary_target": payload["decision"]["primary_target"],
                "first_backup": payload["decision"]["first_backup"],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if not payload["venue_strategy_matrix_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
