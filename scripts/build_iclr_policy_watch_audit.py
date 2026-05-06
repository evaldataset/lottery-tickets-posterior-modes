#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "iclr_policy_watch_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "iclr_policy_watch_audit.md"
DEFAULT_SOURCE_PROBE_JSON = ROOT / "runs" / "iclr_policy_source_probe.json"
DEFAULT_SOURCE_PROBE_MD = ROOT / "docs" / "iclr_policy_source_probe.md"

OFFICIAL_SOURCE_TARGETS = [
    {
        "role": "official_2027_call_for_papers_candidate",
        "url": "https://iclr.cc/Conferences/2027/CallForPapers",
    },
    {
        "role": "official_2027_author_guide_candidate",
        "url": "https://iclr.cc/Conferences/2027/AuthorGuide",
    },
    {
        "role": "official_2026_call_for_papers_proxy",
        "url": "https://iclr.cc/Conferences/2026/CallForPapers",
    },
    {
        "role": "official_2026_author_guide_proxy",
        "url": "https://iclr.cc/Conferences/2026/AuthorGuide",
    },
]

STATIC_SOURCE_OBSERVATIONS = [
    {
        **row,
        "observed_http_status": 404 if "2027" in row["role"] else 200,
        "observed": "2026" in row["role"],
        "observation_source": "static_snapshot",
    }
    for row in OFFICIAL_SOURCE_TARGETS
]

EXPECTED_LIVE_STATUSES = [
    {
        "role": "official_2027_call_for_papers_candidate",
        "url": "https://iclr.cc/Conferences/2027/CallForPapers",
        "expected_http_status_until_posted": 404,
    },
    {
        "role": "official_2027_author_guide_candidate",
        "url": "https://iclr.cc/Conferences/2027/AuthorGuide",
        "expected_http_status_until_posted": 404,
    },
    {
        "role": "official_2026_call_for_papers_proxy",
        "url": "https://iclr.cc/Conferences/2026/CallForPapers",
        "observed_http_status": 200,
    },
    {
        "role": "official_2026_author_guide_proxy",
        "url": "https://iclr.cc/Conferences/2026/AuthorGuide",
        "observed_http_status": 200,
    },
]

PROXY_POLICY_FACTS = {
    "proxy_year": "ICLR 2026",
    "proxy_only_not_2027_policy": True,
    "abstract_deadline": "September 19, 2025 AOE",
    "full_paper_deadline": "September 24, 2025 11:59pm AOE",
    "submission_system": "OpenReview",
    "double_blind": True,
    "main_text_page_limit_at_submission": 9,
    "references_excluded_from_page_limit": True,
    "appendix_allowed_but_review_optional": True,
    "all_authors_need_openreview_profiles": True,
    "new_authors_not_allowed_after_abstract_deadline": True,
    "paper_must_be_anonymous": True,
    "llm_usage_disclosure_required_when_significant": True,
    "llms_not_eligible_for_authorship": True,
    "authors_responsible_for_llm_generated_content": True,
    "code_of_ethics_acknowledgement_required": True,
    "reproducibility_statement_strongly_encouraged": True,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--source-probe-json", type=Path, default=DEFAULT_SOURCE_PROBE_JSON)
    parser.add_argument("--source-probe-md", type=Path, default=DEFAULT_SOURCE_PROBE_MD)
    parser.add_argument(
        "--live-probe",
        action="store_true",
        help="Probe official ICLR policy URLs and persist a source-probe receipt.",
    )
    parser.add_argument("--probe-timeout", type=float, default=15.0)
    parser.add_argument("--observed-date", default="2026-05-13")
    return parser.parse_args()


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def probe_official_sources(timeout: float) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for row in OFFICIAL_SOURCE_TARGETS:
        request = Request(
            row["url"],
            headers={"User-Agent": "Mozilla/5.0 research-audit"},
        )
        observed_http_status: int | None = None
        final_url = row["url"]
        probe_error = None
        try:
            with urlopen(request, timeout=timeout) as response:
                observed_http_status = int(response.status)
                final_url = response.geturl()
        except HTTPError as exc:
            observed_http_status = int(exc.code)
            final_url = exc.geturl()
        except URLError as exc:
            probe_error = str(exc.reason)
        observed = observed_http_status == 200 and probe_error is None
        observations.append(
            {
                **row,
                "observed_http_status": observed_http_status,
                "observed_final_url": final_url,
                "observed": observed,
                "probe_error": probe_error,
                "observation_source": "live_probe",
            }
        )
    return observations


def write_source_probe(
    *,
    observations: list[dict[str, Any]],
    observed_date: str,
    out_json: Path,
    out_md: Path,
) -> None:
    probe = {
        "iclr_policy_source_probe_ready": all(
            row.get("observed_http_status") is not None for row in observations
        ),
        "observed_date": observed_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "official_source_observations": observations,
        "expected_live_statuses": EXPECTED_LIVE_STATUSES,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(probe, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# ICLR Policy Source Probe",
        "",
        f"Observed date: `{observed_date}`.",
        f"Probe ready: `{probe['iclr_policy_source_probe_ready']}`.",
        "",
        "| Role | URL | HTTP status | Final URL | Observed | Error |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in observations:
        lines.append(
            "| {role} | {url} | {status} | {final_url} | {observed} | {error} |".format(
                role=row["role"],
                url=row["url"],
                status=row.get("observed_http_status"),
                final_url=row.get("observed_final_url", row["url"]),
                observed=row.get("observed"),
                error=row.get("probe_error") or "",
            )
        )
    lines.extend(
        [
            "",
            "This file is generated by `scripts/build_iclr_policy_watch_audit.py --live-probe`.",
        ]
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_source_observations(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return STATIC_SOURCE_OBSERVATIONS, "static_snapshot"
    payload = json.loads(path.read_text(encoding="utf-8"))
    observations = payload.get("official_source_observations")
    if not isinstance(observations, list) or not observations:
        return STATIC_SOURCE_OBSERVATIONS, "static_snapshot"
    return observations, "recorded_live_probe"


def build_payload(
    *,
    observed_date: str,
    observations: list[dict[str, Any]],
    source_observation_mode: str,
    source_probe_json: Path,
    source_probe_md: Path,
) -> dict[str, Any]:
    official_2027_cfp_observed = any(
        row["role"] == "official_2027_call_for_papers_candidate" and row["observed"]
        for row in observations
    )
    official_2027_author_guide_observed = any(
        row["role"] == "official_2027_author_guide_candidate" and row["observed"]
        for row in observations
    )
    proxy_sources_ready = all(
        row["observed"]
        for row in observations
        if str(row["role"]).startswith("official_2026_")
    )
    risk_flags = []
    if not proxy_sources_ready:
        risk_flags.append("iclr_2026_policy_proxy_sources_not_observed")
    open_risk_flags = []
    if not official_2027_cfp_observed:
        open_risk_flags.append("iclr_2027_official_cfp_not_observed")
    if not official_2027_author_guide_observed:
        open_risk_flags.append("iclr_2027_official_author_guide_not_observed")
    return {
        "iclr_policy_watch_audit_ready": not risk_flags,
        "observed_date": observed_date,
        "source_observation_mode": source_observation_mode,
        "source_probe_json": relpath(source_probe_json),
        "source_probe_md": relpath(source_probe_md),
        "official_2027_cfp_observed": official_2027_cfp_observed,
        "official_2027_author_guide_observed": official_2027_author_guide_observed,
        "official_source_observations": observations,
        "proxy_policy_facts": PROXY_POLICY_FACTS,
        "risk_flags": risk_flags,
        "open_risk_flags": open_risk_flags,
        "interpretation": {
            "official_2027_policy_not_confirmed": not official_2027_cfp_observed,
            "uses_2026_policy_as_provisional_proxy": proxy_sources_ready,
            "uses_recorded_live_probe": source_observation_mode
            in {"live_probe", "recorded_live_probe"},
            "must_refresh_after_iclr_2027_cfp_posts": True,
            "must_not_claim_final_iclr_2027_compliance_yet": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["iclr_policy_watch_audit_ready"] else "not ready"
    lines = [
        "# ICLR Policy Watch Audit",
        "",
        "This generated audit records the current official ICLR policy-observation",
        "state used by the provisional ICLR 2027 submission path. It is not a",
        "final ICLR 2027 compliance certificate.",
        "",
        f"Audit status: {status}.",
        f"Observed date: `{payload['observed_date']}`.",
        f"Source observation mode: `{payload['source_observation_mode']}`.",
        f"Source probe JSON: `{payload['source_probe_json']}`.",
        f"Official ICLR 2027 CFP observed: `{payload['official_2027_cfp_observed']}`.",
        f"Official ICLR 2027 author guide observed: `{payload['official_2027_author_guide_observed']}`.",
        "",
        "## Official Source Observations",
        "",
        "| Role | URL | HTTP status | Final URL | Observed | Source |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in payload["official_source_observations"]:
        lines.append(
            "| {role} | {url} | {status} | {final_url} | {observed} | {source} |".format(
                role=row["role"],
                url=row["url"],
                status=row.get("observed_http_status"),
                final_url=row.get("observed_final_url", row["url"]),
                observed=row.get("observed"),
                source=row.get("observation_source", payload["source_observation_mode"]),
            )
        )
    lines.extend(["", "## Provisional 2026 Proxy Facts", ""])
    facts = payload["proxy_policy_facts"]
    for key, value in facts.items():
        lines.append(f"- `{key}`: `{value}`")
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
            "## Interpretation",
            "",
            "The repository can use the ICLR 2026 CFP and Author Guide only as a",
            "provisional policy proxy. The official ICLR 2027 CFP and Author Guide",
            "must be checked again before final submission.",
            "",
            "This file is generated by `scripts/build_iclr_policy_watch_audit.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    source_observation_mode = "static_snapshot"
    if args.live_probe:
        observations = probe_official_sources(args.probe_timeout)
        source_observation_mode = "live_probe"
        write_source_probe(
            observations=observations,
            observed_date=args.observed_date,
            out_json=args.source_probe_json,
            out_md=args.source_probe_md,
        )
    else:
        observations, source_observation_mode = load_source_observations(
            args.source_probe_json
        )
    payload = build_payload(
        observed_date=args.observed_date,
        observations=observations,
        source_observation_mode=source_observation_mode,
        source_probe_json=args.source_probe_json,
        source_probe_md=args.source_probe_md,
    )
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "iclr_policy_watch_audit_ready": payload["iclr_policy_watch_audit_ready"],
                "official_2027_cfp_observed": payload["official_2027_cfp_observed"],
                "official_2027_author_guide_observed": payload[
                    "official_2027_author_guide_observed"
                ],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )
    if not payload["iclr_policy_watch_audit_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
