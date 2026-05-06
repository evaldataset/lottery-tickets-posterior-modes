#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPLY_HELPER = ROOT / "runs" / "apply_external_gpu_receipt_r18.py"
ISSUE_POLLER = ROOT / "scripts" / "poll_external_cuda_issue_receipt.py"
UPDATE_HELPER = ROOT / "scripts" / "update_external_validation_receipts.py"
DEFAULT_RECEIPTS = ROOT / "docs" / "external_validation_receipts.json"
DEFAULT_TEMPLATE = ROOT / "runs" / "external_validation_receipt_template.json"
DEFAULT_OUT_JSON = ROOT / "runs" / "external_gpu_receipt_intake_verification_2026-05-08.json"
DEFAULT_OUT_MD = ROOT / "runs" / "external_gpu_receipt_intake_verification_2026-05-08.md"
FALLBACK_EXPECTED_COMMIT = "20db0bf4917736fdb59390f33cdbf371bc41da7e"
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
VALID_DIGEST = "sha256:" + "a" * 64
VALID_URL = "https://github.com/evaldataset/lottery-ticket-bayesian-modes-artifact/issues/1"


def load_expected_commit(template_path: Path = DEFAULT_TEMPLATE) -> str:
    if not template_path.is_file():
        return FALLBACK_EXPECTED_COMMIT
    try:
        payload = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return FALLBACK_EXPECTED_COMMIT
    if not isinstance(payload, dict):
        return FALLBACK_EXPECTED_COMMIT
    receipts = payload.get("receipt_template", {}).get("receipts", {})
    receipt_commit = str(receipts.get("external_gpu_container", {}).get("commit", "")).strip()
    if HEX40_RE.fullmatch(receipt_commit):
        return receipt_commit
    local_facts_commit = str(
        payload.get("local_facts", {}).get("source_repository_commit", "")
    ).strip()
    if HEX40_RE.fullmatch(local_facts_commit):
        return local_facts_commit
    return FALLBACK_EXPECTED_COMMIT


EXPECTED_COMMIT = load_expected_commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that the external CUDA receipt intake helper accepts and rejects fixtures correctly."
    )
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if any intake case fails.")
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def receipt_payload(
    *,
    host_ready: bool = True,
    risk_flags: list[str] | None = None,
    status: str = "observed",
    passed: bool = True,
    commit: str = EXPECTED_COMMIT,
    digest: str = VALID_DIGEST,
    url: str = VALID_URL,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "external_gpu_container_host_validation_ready": host_ready,
        "risk_flags": risk_flags or [],
        "receipt_candidate": {
            "external_gpu_container": {
                "status": status,
                "url": url,
                "commit": commit,
                "image_digest": digest,
                "passed": passed,
            }
        },
    }


def run_case(name: str, payload: dict[str, Any], expect_ready: bool, tmpdir: Path) -> dict[str, Any]:
    receipt_path = tmpdir / f"{name}.json"
    receipt_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    command = [
        sys.executable,
        str(APPLY_HELPER),
        "--receipt-json",
        str(receipt_path),
    ]
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    stdout = proc.stdout.strip()
    summary: dict[str, Any] = {}
    if stdout:
        first_line = stdout.splitlines()[0]
        try:
            summary = json.loads(first_line)
        except json.JSONDecodeError:
            summary = {"parse_error": first_line}
    ready = bool(summary.get("external_gpu_receipt_apply_ready") is True and proc.returncode == 0)
    return {
        "name": name,
        "expect_ready": expect_ready,
        "ready": ready,
        "passed": ready is expect_ready,
        "returncode": proc.returncode,
        "risk_flags": summary.get("risk_flags", []),
        "candidate_commit": summary.get("candidate_commit", ""),
        "candidate_image_digest": summary.get("candidate_image_digest", ""),
        "evidence_url": summary.get("evidence_url", ""),
        "stderr_tail": proc.stderr.strip()[-1000:],
    }


def issue_payload(body: str) -> dict[str, Any]:
    return {
        "state": "OPEN",
        "updatedAt": "2026-05-08T00:00:00Z",
        "url": VALID_URL,
        "comments": [
            {
                "author": {"login": "external-validator"},
                "body": body,
                "createdAt": "2026-05-08T00:00:00Z",
                "url": VALID_URL + "#issuecomment-fixture",
            }
        ],
    }


def generated_markdown_receipt(*, risk_flags: list[str] | None = None) -> str:
    risks = risk_flags or []
    risk_lines = "\n".join(f"- {risk}" for risk in risks) if risks else "- none"
    host_status = "not ready" if risks else "ready"
    return "\n".join(
        [
            "# External GPU Container Receipt",
            "",
            "This generated receipt records an independent CUDA-host validation of",
            "the GPU training Docker image. Upload this JSON or Markdown file and",
            "use the uploaded URL in `docs/external_validation_receipts.json`.",
            "",
            f"Host validation status: {host_status}.",
            "Receipt-registry update status: ready.",
            "",
            "## Source",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Expected commit | `{EXPECTED_COMMIT}` |",
            f"| Observed commit | `{EXPECTED_COMMIT}` |",
            f"| Evidence URL | `{VALID_URL}` |",
            "",
            "## Image",
            "",
            "| Field | Value |",
            "| --- | --- |",
            "| Image | `lottery-training-gpu:2026-05-06` |",
            f"| Image ID | `{VALID_DIGEST}` |",
            "| Size bytes | 123456 |",
            "",
            "## Runtime Check",
            "",
            "| Field | Value |",
            "| --- | --- |",
            "| Command mode | `docker` |",
            "| Fallback used | False |",
            "| Return code | 0 |",
            "| Package lock | `requirements-gpu-lock.txt` |",
            "| Torch CUDA version | `13.0` |",
            "| CUDA available | True |",
            "| CUDA device | `fixture-gpu` |",
            "| CUDA device count | 1 |",
            "| CUDA matmul sum | 4096.0 |",
            "",
            "## Risk Flags",
            "",
            risk_lines,
            "",
            "## Warning Flags",
            "",
            "- none",
            "",
            "This file is generated by `scripts/build_external_gpu_container_receipt.py`.",
        ]
    )


def run_issue_poll_case(
    name: str,
    payload: dict[str, Any],
    expect_poll_ready: bool,
    tmpdir: Path,
    linked_receipt_fixtures: dict[str, str] | None = None,
    *,
    check_urls: bool = False,
    expect_operator_note_count: int | None = None,
) -> dict[str, Any]:
    issue_path = tmpdir / f"{name}_issue.json"
    out_json = tmpdir / f"{name}_poll.json"
    out_md = tmpdir / f"{name}_poll.md"
    linked_fixtures_path = tmpdir / f"{name}_linked_receipts.json"
    issue_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    command = [
        sys.executable,
        str(ISSUE_POLLER),
        "--issue-json",
        str(issue_path),
        "--out-json",
        str(out_json),
        "--out-md",
        str(out_md),
    ]
    if linked_receipt_fixtures is not None:
        linked_fixtures_path.write_text(
            json.dumps(linked_receipt_fixtures, indent=2) + "\n",
            encoding="utf-8",
        )
        command.extend(["--linked-receipt-fixtures", str(linked_fixtures_path)])
    if check_urls:
        command.append("--check-urls")
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    poll_payload: dict[str, Any] = {}
    if out_json.is_file():
        try:
            candidate = json.loads(out_json.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                poll_payload = candidate
        except json.JSONDecodeError:
            poll_payload = {}
    poll_ready = poll_payload.get("external_cuda_issue_receipt_poll_ready") is True
    operator_note_count = poll_payload.get("operator_note_comment_count")
    operator_note_ready = (
        True
        if expect_operator_note_count is None
        else operator_note_count == expect_operator_note_count
    )
    expected_operator_note_without_receipt = (
        True
        if expect_operator_note_count and not expect_poll_ready
        else False
    )
    operator_note_without_receipt_ready = (
        poll_payload.get("operator_note_without_receipt")
        is expected_operator_note_without_receipt
    )
    return {
        "name": name,
        "expect_ready": expect_poll_ready,
        "ready": poll_ready,
        "passed": bool(
            proc.returncode == 0
            and poll_ready is expect_poll_ready
            and operator_note_ready
            and operator_note_without_receipt_ready
        ),
        "returncode": proc.returncode,
        "risk_flags": [],
        "candidate_commit": (
            (poll_payload.get("selected_candidate") or {})
            .get("apply_result", {})
            .get("summary", {})
            .get("candidate_commit", "")
        ),
        "candidate_image_digest": (
            (poll_payload.get("selected_candidate") or {})
            .get("apply_result", {})
            .get("summary", {})
            .get("candidate_image_digest", "")
        ),
        "evidence_url": (
            (poll_payload.get("selected_candidate") or {})
            .get("apply_result", {})
            .get("summary", {})
            .get("evidence_url", "")
        ),
        "comment_count": poll_payload.get("comment_count"),
        "candidate_count": poll_payload.get("candidate_count"),
        "valid_candidate_count": poll_payload.get("valid_candidate_count"),
        "linked_receipt_count": poll_payload.get("linked_receipt_count"),
        "linked_receipt_fetch_error_count": poll_payload.get(
            "linked_receipt_fetch_error_count"
        ),
        "operator_note_comment_count": operator_note_count,
        "expected_operator_note_comment_count": expect_operator_note_count,
        "operator_note_without_receipt": poll_payload.get(
            "operator_note_without_receipt"
        ),
        "expected_operator_note_without_receipt": expected_operator_note_without_receipt,
        "operator_note_urls": poll_payload.get("operator_note_comment_urls", []),
        "check_urls": poll_payload.get("check_urls"),
        "stderr_tail": proc.stderr.strip()[-1000:],
    }


def run_registry_update_case(
    name: str,
    update_args: list[str],
    expect_ready: bool,
    tmpdir: Path,
    *,
    expect_written: bool = False,
) -> dict[str, Any]:
    receipts_path = tmpdir / f"{name}_receipts.json"
    receipts_path.write_text(DEFAULT_RECEIPTS.read_text(encoding="utf-8"), encoding="utf-8")
    command = [
        sys.executable,
        str(UPDATE_HELPER),
        "--receipts",
        str(receipts_path),
        "--template",
        str(DEFAULT_TEMPLATE),
        *update_args,
    ]
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    stdout = proc.stdout.strip()
    summary: dict[str, Any] = {}
    if stdout:
        try:
            summary = json.loads(stdout.splitlines()[0])
        except json.JSONDecodeError:
            summary = {"parse_error": stdout.splitlines()[0]}
    ready = bool(summary.get("receipt_update_ready") is True and proc.returncode == 0)
    registry_row: dict[str, Any] = {}
    registry_write_verified = not expect_written
    if receipts_path.is_file():
        try:
            registry = json.loads(receipts_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            registry = {}
        candidate = registry.get("receipts", {}).get("external_gpu_container", {})
        if isinstance(candidate, dict):
            registry_row = candidate
            if expect_written:
                registry_write_verified = bool(
                    candidate.get("status") == "observed"
                    and candidate.get("url") == VALID_URL
                    and candidate.get("commit") == EXPECTED_COMMIT
                    and candidate.get("image_digest") == VALID_DIGEST
                    and candidate.get("passed") is True
                )
    return {
        "name": name,
        "expect_ready": expect_ready,
        "ready": ready,
        "passed": bool((ready is expect_ready) and registry_write_verified),
        "returncode": proc.returncode,
        "risk_flags": summary.get("risk_flags", []),
        "candidate_commit": registry_row.get("commit", ""),
        "candidate_image_digest": registry_row.get("image_digest", ""),
        "evidence_url": registry_row.get("url", ""),
        "updated_receipts": summary.get("updated_receipts", []),
        "registry_write_verified": registry_write_verified,
        "stderr_tail": proc.stderr.strip()[-1000:],
    }


def build_payload() -> dict[str, Any]:
    valid_receipt_comment = "```json\n" + json.dumps(receipt_payload(), indent=2) + "\n```"
    linked_json_url = "https://example.test/external_gpu_container_receipt.json"
    linked_md_url = "https://example.test/external_gpu_container_receipt.md"
    linked_error_url = "https://example.test/external_gpu_container_receipt_fetch_error.json"
    cases = [
        ("valid_receipt", receipt_payload(), True),
        (
            "wrong_commit",
            receipt_payload(commit="0" * 40),
            False,
        ),
        (
            "bad_digest",
            receipt_payload(digest="sha256:not-a-digest"),
            False,
        ),
        (
            "risk_flags_present",
            receipt_payload(risk_flags=["cuda_not_available"]),
            False,
        ),
        (
            "host_not_ready",
            receipt_payload(host_ready=False),
            False,
        ),
        (
            "not_passed",
            receipt_payload(passed=False),
            False,
        ),
        (
            "missing_url",
            receipt_payload(url=""),
            False,
        ),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        results = [run_case(name, payload, expect_ready, tmpdir) for name, payload, expect_ready in cases]
        results.extend(
            [
                run_issue_poll_case(
                    "issue_poller_ignores_operator_note_without_receipt",
                    issue_payload(
                        "\n".join(
                            [
                                "Additional operator note for the `--evidence-url` argument",
                                "external CUDA Docker requirement",
                                "runs/external_gpu_container_receipt.json",
                                "docs/external_gpu_container_receipt.md",
                                "receipt_candidate.external_gpu_container.commit",
                                "receipt_candidate.external_gpu_container.image_digest",
                                "This receipt is only for independent CUDA/Docker reproducibility.",
                            ]
                        )
                    ),
                    False,
                    tmpdir,
                    check_urls=True,
                    expect_operator_note_count=1,
                ),
                run_issue_poll_case(
                    "issue_poller_accepts_fenced_receipt_json",
                    issue_payload(valid_receipt_comment),
                    True,
                    tmpdir,
                ),
                run_issue_poll_case(
                    "issue_poller_accepts_generated_markdown_receipt",
                    issue_payload(generated_markdown_receipt()),
                    True,
                    tmpdir,
                ),
                run_issue_poll_case(
                    "issue_poller_rejects_generated_markdown_with_risk_flags",
                    issue_payload(
                        generated_markdown_receipt(risk_flags=["cuda_not_available"])
                    ),
                    False,
                    tmpdir,
                ),
                run_issue_poll_case(
                    "issue_poller_accepts_linked_receipt_json",
                    issue_payload(f"[receipt]({linked_json_url})"),
                    True,
                    tmpdir,
                    linked_receipt_fixtures={
                        linked_json_url: json.dumps(receipt_payload(), indent=2)
                    },
                ),
                run_issue_poll_case(
                    "issue_poller_accepts_linked_generated_markdown_receipt",
                    issue_payload(f"[external_gpu_container_receipt.md]({linked_md_url})"),
                    True,
                    tmpdir,
                    linked_receipt_fixtures={linked_md_url: generated_markdown_receipt()},
                ),
                run_issue_poll_case(
                    "issue_poller_records_linked_receipt_fetch_error",
                    issue_payload(f"[external_gpu_container_receipt.json]({linked_error_url})"),
                    False,
                    tmpdir,
                    linked_receipt_fixtures={
                        linked_error_url: "__ERROR__:fixture_fetch_error"
                    },
                ),
                run_registry_update_case(
                    "registry_writer_updates_temp_external_gpu_receipt",
                    [
                        "--write",
                        "--external-gpu-url",
                        VALID_URL,
                        "--external-gpu-image-digest",
                        VALID_DIGEST,
                        "--external-gpu-passed",
                    ],
                    True,
                    tmpdir,
                    expect_written=True,
                ),
                run_registry_update_case(
                    "registry_writer_rejects_placeholder_external_gpu_url",
                    [
                        "--external-gpu-url",
                        "http://127.0.0.1/external_gpu_container_receipt.json",
                        "--external-gpu-image-digest",
                        VALID_DIGEST,
                        "--external-gpu-passed",
                    ],
                    False,
                    tmpdir,
                ),
            ]
        )
    return {
        "external_gpu_receipt_intake_verified": all(result["passed"] for result in results),
        "apply_helper": rel(APPLY_HELPER),
        "issue_poller": rel(ISSUE_POLLER),
        "update_helper": rel(UPDATE_HELPER),
        "expected_commit": EXPECTED_COMMIT,
        "case_count": len(results),
        "cases": results,
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# External GPU Receipt Intake Verification",
        "",
        f"Verified: {payload['external_gpu_receipt_intake_verified']}.",
        f"Apply helper: `{payload['apply_helper']}`.",
        f"Issue poller: `{payload['issue_poller']}`.",
        f"Update helper: `{payload['update_helper']}`.",
        f"Expected commit: `{payload['expected_commit']}`.",
        "",
        "| Case | Expected ready | Actual ready | Passed | Risk flags |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for case in payload["cases"]:
        risks = ", ".join(case["risk_flags"]) if case["risk_flags"] else "none"
        lines.append(
            f"| {case['name']} | {case['expect_ready']} | {case['ready']} | {case['passed']} | {risks} |"
        )
    lines.extend(
        [
            "",
            "This verifier uses temporary local fixtures only; it does not mark the",
            "external CUDA receipt as observed. A real independent CUDA-host receipt",
            "is still required before strict artifact readiness can pass.",
            "",
            "This file is generated by `scripts/verify_external_gpu_receipt_intake.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_payload()
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "external_gpu_receipt_intake_verified": payload[
                    "external_gpu_receipt_intake_verified"
                ],
                "case_count": payload["case_count"],
                "out_json": rel(args.out_json),
                "out_md": rel(args.out_md),
            }
        )
    )
    if args.strict and not payload["external_gpu_receipt_intake_verified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
