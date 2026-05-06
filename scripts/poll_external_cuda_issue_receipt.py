#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "evaldataset/lottery-ticket-bayesian-modes-artifact"
DEFAULT_ISSUE = "1"
DEFAULT_OUT_JSON = ROOT / "runs" / "external_cuda_issue_receipt_poll_2026-05-08.json"
DEFAULT_OUT_MD = ROOT / "runs" / "external_cuda_issue_receipt_poll_2026-05-08.md"
APPLY_HELPER = ROOT / "runs" / "apply_external_gpu_receipt_r18.py"
JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)
URL_RE = re.compile(r"^(https?://|doi:|10\.)", re.IGNORECASE)
COMMENT_LINK_RE = re.compile(
    r"\[(?P<label>[^\]]{1,240})\]\((?P<md_url>https?://[^)\s]+)\)"
    r"|(?P<bare_url>https?://[^\s<>)]+)",
    re.IGNORECASE,
)
RECEIPT_LINK_MARKERS = (
    "external_gpu_container_receipt",
    "external_gpu_receipt",
    "external_cuda_receipt",
)
OPERATOR_NOTE_MARKERS = (
    "Additional operator note",
    "--evidence-url",
    "runs/external_gpu_container_receipt.json",
    "docs/external_gpu_container_receipt.md",
    "receipt_candidate.external_gpu_container.commit",
    "receipt_candidate.external_gpu_container.image_digest",
    "independent CUDA/Docker reproducibility",
)
MAX_LINKED_RECEIPT_BYTES = 1_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Poll the public r18 CUDA validation issue for an external GPU "
            "container receipt JSON and dry-run or apply it through the local "
            "receipt helper."
        )
    )
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--issue", default=DEFAULT_ISSUE)
    parser.add_argument(
        "--issue-json",
        type=Path,
        default=None,
        help="Read a saved gh issue-view JSON payload instead of calling gh; used by fixture tests.",
    )
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument(
        "--linked-receipt-fixtures",
        type=Path,
        default=None,
        help=(
            "Optional JSON object mapping linked receipt URLs to text content; "
            "used by fixture tests instead of live HTTP fetches."
        ),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply the first valid external CUDA receipt to docs/external_validation_receipts.json.",
    )
    parser.add_argument(
        "--check-urls",
        action="store_true",
        help=(
            "Accepted for compatibility with the TMLR closure/final-gate "
            "commands. Live issue polling and linked receipt fetches are "
            "already URL-backed; this flag does not change fixture behavior."
        ),
    )
    parser.add_argument(
        "--require-found",
        action="store_true",
        help="Exit nonzero if no valid external CUDA receipt is found.",
    )
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def run_gh_issue_view(repo: str, issue: str) -> tuple[dict[str, Any], str]:
    command = [
        "gh",
        "issue",
        "view",
        issue,
        "--repo",
        repo,
        "--json",
        "state,updatedAt,url,comments",
    ]
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return {}, proc.stderr.strip() or proc.stdout.strip()
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {}, f"gh output was not JSON: {exc}"
    return payload if isinstance(payload, dict) else {}, ""


def load_linked_receipt_fixtures(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def raw_json_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    payloads: list[dict[str, Any]] = []

    def append_unique(candidate: Any) -> None:
        if not isinstance(candidate, dict):
            return
        key = json.dumps(candidate, sort_keys=True, separators=(",", ":"))
        if key in seen:
            return
        seen.add(key)
        payloads.append(candidate)

    seen: set[str] = set()
    for match in JSON_FENCE_RE.finditer(text):
        try:
            candidate = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        append_unique(candidate)
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        append_unique(candidate)
    return payloads


def has_external_gpu_candidate(payload: dict[str, Any]) -> bool:
    candidate = payload.get("receipt_candidate", {}).get("external_gpu_container", {})
    return isinstance(candidate, dict) and bool(candidate)


def clean_markdown_value(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def markdown_table_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        columns = [column.strip() for column in stripped.strip("|").split("|")]
        if len(columns) < 2:
            continue
        field, value = columns[0], columns[1]
        if not field or set(field) <= {"-", ":"} or field.lower() == "field":
            continue
        fields[field.lower()] = clean_markdown_value(value)
    return fields


def markdown_section_list(text: str, heading: str) -> list[str]:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return []
    values: list[str] = []
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        value = clean_markdown_value(stripped[1:])
        if value and value.lower() != "none":
            values.append(value)
    return values


def generated_markdown_receipt_payload(text: str) -> dict[str, Any] | None:
    if "# External GPU Container Receipt" not in text:
        return None
    status_match = re.search(
        r"^Host validation status:\s*(?P<status>ready|not ready)\.",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    fields = markdown_table_fields(text)
    observed_commit = fields.get("observed commit", "")
    image_digest = fields.get("image id", "")
    evidence_url = fields.get("evidence url", "")
    if evidence_url.startswith("<") or evidence_url.endswith(">"):
        evidence_url = ""
    risk_flags = markdown_section_list(text, "Risk Flags")
    if not status_match or not observed_commit or not image_digest:
        return None
    host_ready = status_match.group("status").lower() == "ready" and not risk_flags
    return {
        "schema_version": 1,
        "external_gpu_container_host_validation_ready": host_ready,
        "risk_flags": risk_flags,
        "receipt_candidate": {
            "external_gpu_container": {
                "status": "observed" if URL_RE.search(evidence_url) else "pending",
                "url": evidence_url,
                "commit": observed_commit,
                "image_digest": image_digest,
                "passed": host_ready,
                "notes": (
                    "Synthesized from generated Markdown receipt by "
                    "scripts/poll_external_cuda_issue_receipt.py."
                ),
            }
        },
    }


def receipt_payloads_from_comment(text: str) -> list[tuple[str, dict[str, Any]]]:
    payloads: list[tuple[str, dict[str, Any]]] = []
    for payload in raw_json_objects(text):
        payloads.append(("json", payload))
    markdown_payload = generated_markdown_receipt_payload(text)
    if markdown_payload is not None:
        payloads.append(("generated_markdown", markdown_payload))
    return payloads


def receipt_links_from_comment(text: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for match in COMMENT_LINK_RE.finditer(text):
        label = match.group("label") or ""
        url = (match.group("md_url") or match.group("bare_url") or "").rstrip(".,;")
        haystack = f"{label} {url}".lower()
        if not any(marker in haystack for marker in RECEIPT_LINK_MARKERS):
            continue
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


def is_operator_note_comment(text: str) -> bool:
    return all(marker in text for marker in OPERATOR_NOTE_MARKERS)


def fetch_linked_receipt_text(url: str, fixtures: dict[str, str]) -> tuple[str, str]:
    if url in fixtures:
        fixture = fixtures[url]
        if fixture.startswith("__ERROR__:"):
            return "", fixture.removeprefix("__ERROR__:").strip() or "fixture_fetch_error"
        return fixture, ""
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/markdown,text/plain,*/*",
            "User-Agent": "lottery-external-cuda-receipt-poller",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_LINKED_RECEIPT_BYTES:
                    return "", "linked_receipt_too_large"
                chunks.append(chunk)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return "", str(exc)
    raw = b"".join(chunks)
    try:
        return raw.decode("utf-8"), ""
    except UnicodeDecodeError as exc:
        return "", f"linked_receipt_not_utf8:{exc}"


def apply_receipt_candidate(payload: dict[str, Any], *, write: bool, evidence_url: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        receipt_path = Path(tmp) / "external_gpu_receipt_candidate.json"
        receipt_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        command = [
            sys.executable,
            str(APPLY_HELPER),
            "--receipt-json",
            str(receipt_path),
        ]
        if evidence_url:
            command.extend(["--evidence-url", evidence_url])
        if write:
            command.append("--write")
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    summary: dict[str, Any] = {}
    if proc.stdout.strip():
        try:
            candidate_summary = json.loads(proc.stdout.splitlines()[0])
            if isinstance(candidate_summary, dict):
                summary = candidate_summary
        except json.JSONDecodeError:
            summary = {"parse_error": proc.stdout.splitlines()[0]}
    return {
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout.strip()[-1000:],
        "stderr_tail": proc.stderr.strip()[-1000:],
        "summary": summary,
        "ready": bool(
            proc.returncode == 0 and summary.get("external_gpu_receipt_apply_ready") is True
        ),
    }


def load_issue_payload(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    if args.issue_json is None:
        return run_gh_issue_view(args.repo, args.issue)
    try:
        payload = json.loads(args.issue_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"issue-json could not be read: {exc}"
    return payload if isinstance(payload, dict) else {}, ""


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    issue_payload, gh_error = load_issue_payload(args)
    linked_receipt_fixtures = load_linked_receipt_fixtures(args.linked_receipt_fixtures)
    comments = issue_payload.get("comments", []) if isinstance(issue_payload, dict) else []
    if not isinstance(comments, list):
        comments = []

    candidates: list[dict[str, Any]] = []
    linked_receipts: list[dict[str, Any]] = []
    operator_note_comments: list[dict[str, str]] = []
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = str(comment.get("body", ""))
        if is_operator_note_comment(body):
            operator_note_comments.append(
                {
                    "comment_url": str(comment.get("url", "")),
                    "comment_author": str(comment.get("author", {}).get("login", "")),
                    "created_at": str(comment.get("createdAt", "")),
                }
            )
        source_texts: list[tuple[str, str, str]] = [("comment", "", body)]
        for link_url in receipt_links_from_comment(body):
            linked_text, fetch_error = fetch_linked_receipt_text(
                link_url,
                linked_receipt_fixtures,
            )
            linked_receipts.append(
                {
                    "comment_url": str(comment.get("url", "")),
                    "url": link_url,
                    "fetched": bool(linked_text and not fetch_error),
                    "fetch_error": fetch_error,
                }
            )
            if linked_text and not fetch_error:
                source_texts.append(("linked", link_url, linked_text))
        for source_kind, source_url, source_text in source_texts:
            for source_format, payload in receipt_payloads_from_comment(source_text):
                if not has_external_gpu_candidate(payload):
                    continue
                result = apply_receipt_candidate(
                    payload,
                    write=args.write,
                    evidence_url=source_url or str(comment.get("url", "")).strip(),
                )
                candidates.append(
                    {
                        "comment_url": str(comment.get("url", "")),
                        "comment_author": comment.get("author", {}).get("login", ""),
                        "created_at": comment.get("createdAt", ""),
                        "source_kind": source_kind,
                        "source_url": source_url,
                        "source_format": source_format,
                        "apply_result": result,
                    }
                )

    valid = [candidate for candidate in candidates if candidate["apply_result"]["ready"]]
    operator_note_without_receipt = bool(operator_note_comments and not valid)
    return {
        "external_cuda_issue_receipt_poll_ready": bool(valid),
        "write": args.write,
        "check_urls": args.check_urls,
        "repo": args.repo,
        "issue": args.issue,
        "issue_url": issue_payload.get("url", ""),
        "issue_state": issue_payload.get("state", ""),
        "issue_updated_at": issue_payload.get("updatedAt", ""),
        "gh_error": gh_error,
        "comment_count": len(comments),
        "candidate_count": len(candidates),
        "valid_candidate_count": len(valid),
        "linked_receipt_count": len(linked_receipts),
        "linked_receipt_fetch_error_count": len(
            [item for item in linked_receipts if item.get("fetch_error")]
        ),
        "linked_receipts": linked_receipts,
        "operator_note_comment_count": len(operator_note_comments),
        "operator_note_comment_urls": [
            item["comment_url"] for item in operator_note_comments if item.get("comment_url")
        ],
        "operator_note_comments": operator_note_comments,
        "operator_note_without_receipt": operator_note_without_receipt,
        "selected_candidate": valid[0] if valid else None,
        "candidates": candidates,
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# External CUDA Issue Receipt Poll",
        "",
        f"Ready: {payload['external_cuda_issue_receipt_poll_ready']}.",
        f"Write mode: {payload['write']}.",
        f"Check URLs mode: {payload['check_urls']}.",
        f"Issue: `{payload['issue_url']}`.",
        f"Issue state: `{payload['issue_state']}`.",
        f"Issue updated at: `{payload['issue_updated_at']}`.",
        f"Comments scanned: {payload['comment_count']}.",
        f"Operator-note comments: {payload['operator_note_comment_count']}.",
        f"Operator note without receipt: {payload['operator_note_without_receipt']}.",
        f"Linked receipt URLs scanned: {payload['linked_receipt_count']}.",
        f"Linked receipt fetch errors: {payload['linked_receipt_fetch_error_count']}.",
        f"Receipt candidates found: {payload['candidate_count']}.",
        f"Valid candidates: {payload['valid_candidate_count']}.",
        "",
        "## Selected Candidate",
        "",
    ]
    selected = payload.get("selected_candidate")
    if selected:
        summary = selected["apply_result"]["summary"]
        lines.extend(
            [
                f"- Comment URL: `{selected['comment_url']}`",
                f"- Source kind: `{selected.get('source_kind', '')}`",
                f"- Source URL: `{selected.get('source_url', '')}`",
                f"- Source format: `{selected.get('source_format', '')}`",
                f"- Commit: `{summary.get('candidate_commit', '')}`",
                f"- Image digest: `{summary.get('candidate_image_digest', '')}`",
                f"- Evidence URL: `{summary.get('evidence_url', '')}`",
            ]
        )
    else:
        lines.append("- none")
    if payload.get("gh_error"):
        lines.extend(["", "## GitHub Error", "", "```text", payload["gh_error"], "```"])
    lines.extend(["", "## Operator Notes", ""])
    if payload.get("operator_note_comments"):
        for item in payload["operator_note_comments"]:
            lines.append(f"- `{item.get('comment_url', '')}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This poller accepts comments containing either a receipt JSON with",
            "`receipt_candidate.external_gpu_container` or the generated",
            "`docs/external_gpu_container_receipt.md` Markdown content. It also",
            "fetches linked receipt-looking JSON/Markdown files when their URL",
            "or link label names an external GPU/CUDA receipt.",
            "Operator-note comments without a receipt are ignored.",
            "",
            "This file is generated by `scripts/poll_external_cuda_issue_receipt.py`.",
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
                "external_cuda_issue_receipt_poll_ready": payload[
                    "external_cuda_issue_receipt_poll_ready"
                ],
                "comment_count": payload["comment_count"],
                "candidate_count": payload["candidate_count"],
                "valid_candidate_count": payload["valid_candidate_count"],
                "linked_receipt_count": payload["linked_receipt_count"],
                "linked_receipt_fetch_error_count": payload[
                    "linked_receipt_fetch_error_count"
                ],
                "operator_note_comment_count": payload["operator_note_comment_count"],
                "operator_note_without_receipt": payload[
                    "operator_note_without_receipt"
                ],
                "out_json": rel(args.out_json),
                "out_md": rel(args.out_md),
            }
        )
    )
    if args.require_found and not payload["external_cuda_issue_receipt_poll_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
