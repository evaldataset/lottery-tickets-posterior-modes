#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import build_tmlr_external_cuda_validator_request as request_builder


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-05-08"
DEFAULT_BUNDLE = ROOT / "runs" / "external_cuda_handoff_r18_bundle.tar.gz"
DEFAULT_SIDECAR = ROOT / "runs" / "external_cuda_handoff_r18_bundle.tar.gz.sha256"
DEFAULT_OUT_JSON = ROOT / "runs" / f"external_cuda_handoff_bundle_verification_{DATE}.json"
DEFAULT_OUT_MD = ROOT / "runs" / f"external_cuda_handoff_bundle_verification_{DATE}.md"
LOCAL_OPERATOR_NOTE = ROOT / "runs" / f"external_cuda_issue_followup_comment_{DATE}.md"
OPERATOR_BUNDLE_COPY = (
    ROOT
    / "dist"
    / f"tmlr_operator_handoff_{DATE}"
    / "cuda"
    / "external_cuda_handoff_r18_bundle.tar.gz"
)
OPERATOR_SIDECAR_COPY = OPERATOR_BUNDLE_COPY.with_suffix(
    OPERATOR_BUNDLE_COPY.suffix + ".sha256"
)

EXPECTED_MEMBERS = [
    "apply_external_gpu_receipt_r18.py",
    "external_cuda_github_self_hosted_workflow_r18.yml",
    "external_cuda_handoff_r18.commands.sh",
    "external_cuda_handoff_r18.md",
    "external_cuda_host_selection_2026-05-07.md",
    "external_cuda_vm_preflight_ubuntu.sh",
]

REQUIRED_SNIPPETS = {
    "external_cuda_handoff_r18.commands.sh": [
        request_builder.REPO_URL,
        request_builder.COMMIT,
        "make gpu-container-build",
        "docker image inspect lottery-training-gpu:2026-05-06",
        "make gpu-container-env-check",
        "scripts/build_external_gpu_container_receipt.py",
        "--expected-commit",
        "--evidence-url",
    ],
    "external_cuda_vm_preflight_ubuntu.sh": [
        "nvidia-smi",
        "docker version",
        "docker run --rm --gpus all",
        "nvidia/cuda:13.0.1-base-ubuntu24.04",
    ],
    "apply_external_gpu_receipt_r18.py": [
        "external_gpu_container",
        "external_gpu_container_receipt.json",
        "update_external_validation_receipts.py",
    ],
    "external_cuda_github_self_hosted_workflow_r18.yml": [
        "self-hosted",
        "gpu-container-build",
        "gpu-container-env-check",
        "build_external_gpu_container_receipt.py",
    ],
    "external_cuda_handoff_r18.md": [
        request_builder.RELEASE_TAG,
        request_builder.COMMIT,
        "make gpu-container-build",
        "make gpu-container-env-check",
        "build_external_gpu_container_receipt.py",
    ],
    "external_cuda_host_selection_2026-05-07.md": [
        "independent",
        "NVIDIA",
        "Docker",
    ],
}

FORBIDDEN_MEMBER_SNIPPETS = [
    ".git/",
    "tmlr_human_unblock_reply",
    "tmlr_openreview_submission_receipt",
    "external_gpu_container_receipt.json",
]

PUBLIC_OPERATOR_NOTE_SNIPPETS = [
    "./external_cuda_handoff_r18.commands.sh",
    request_builder.ISSUE_URL,
    "runs/external_gpu_container_receipt.json",
    "docs/external_gpu_container_receipt.md",
    "receipt_candidate.external_gpu_container.commit",
    "receipt_candidate.external_gpu_container.image_digest",
    "This receipt is only for independent CUDA/Docker reproducibility.",
    "Why the external Docker receipt is still needed:",
    "local CPU CI cannot exercise CUDA, NVIDIA Container Toolkit, or host-driver",
    "depends on this workstation's local state",
    "frozen r18 public release can rebuild and run on a separate CUDA host",
    "strict external-GPU validation",
    "external_gpu_container_host_validation_ready: true",
    "receipt_candidate.external_gpu_container.status: observed",
    "receipt_candidate.external_gpu_container.passed: true",
    f"receipt_candidate.external_gpu_container.commit: {request_builder.COMMIT}",
    "risk_flags: []",
]

LOCAL_OPERATOR_NOTE_SNIPPETS = [
    "Additional operator note for the `--evidence-url` argument",
    "external CUDA Docker requirement",
    "The receipt builder can run without an evidence URL",
    "This receipt is only for independent CUDA/Docker reproducibility.",
    "It is not a request for additional scientific experiments.",
    *PUBLIC_OPERATOR_NOTE_SNIPPETS,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the external CUDA handoff tarball used by the independent "
            "GPU Docker validator request."
        )
    )
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument(
        "--check-urls",
        action="store_true",
        help="Download the public release tarball and sidecar and verify their hashes.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if not ready.")
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sidecar(path: Path) -> tuple[str, str]:
    if not path.is_file():
        return "", ""
    text = path.read_text(encoding="utf-8").strip()
    parts = text.split()
    if not parts:
        return "", text
    return parts[0], text


def command_result(command: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout.strip()[-1000:],
        "stderr_tail": proc.stderr.strip()[-1000:],
    }


def fetch_github_api_json(
    url: str,
    *,
    urlopen: Any | None = None,
    run_command: Any | None = None,
) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    opener = urlopen or urllib.request.urlopen
    runner = run_command or subprocess.run
    try:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "lottery-tmlr-external-cuda-handoff-verifier",
            },
        )
        with opener(request, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else {}, findings
    except (json.JSONDecodeError, urllib.error.URLError, TimeoutError) as exc:
        findings.append(f"urllib:{exc}")

    gh_result = runner(
        ["gh", "api", url],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if gh_result.returncode != 0:
        findings.append(f"gh_api:{gh_result.stderr.strip()[-500:]}")
        return {}, findings
    try:
        payload = json.loads(gh_result.stdout)
    except json.JSONDecodeError as exc:
        findings.append(f"gh_api_json:{exc}")
        return {}, findings
    return payload if isinstance(payload, dict) else {}, findings


class _FixtureResponse:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def __enter__(self) -> "_FixtureResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.data


def verify_github_api_fetcher() -> tuple[list[str], list[dict[str, Any]]]:
    findings: list[str] = []
    cases: list[dict[str, Any]] = []
    url = "https://api.github.com/repos/example/project/issues/comments/1"

    def record_case(
        name: str,
        payload: dict[str, Any],
        fetch_findings: list[str],
        passed: bool,
    ) -> None:
        cases.append(
            {
                "name": name,
                "passed": passed,
                "payload_body": str(payload.get("body", "")),
                "findings": fetch_findings,
            }
        )
        if not passed:
            findings.append(f"github_api_fetcher_case_failed:{name}")

    def unused_runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("gh api fallback should not run")

    direct_payload, direct_findings = fetch_github_api_json(
        url,
        urlopen=lambda *args, **kwargs: _FixtureResponse(b'{"body":"urllib ok"}'),
        run_command=unused_runner,
    )
    record_case(
        "urllib_success",
        direct_payload,
        direct_findings,
        direct_payload.get("body") == "urllib ok" and direct_findings == [],
    )

    def failing_urlopen(*args: object, **kwargs: object) -> _FixtureResponse:
        raise urllib.error.URLError("fixture rate limit")

    fallback_payload, fallback_findings = fetch_github_api_json(
        url,
        urlopen=failing_urlopen,
        run_command=lambda *args, **kwargs: subprocess.CompletedProcess(
            args=list(args),
            returncode=0,
            stdout='{"body":"gh api ok"}',
            stderr="",
        ),
    )
    record_case(
        "urllib_failure_gh_api_success",
        fallback_payload,
        fallback_findings,
        fallback_payload.get("body") == "gh api ok"
        and any(item.startswith("urllib:") for item in fallback_findings)
        and not any(item.startswith("gh_api") for item in fallback_findings),
    )

    failed_payload, failed_findings = fetch_github_api_json(
        url,
        urlopen=failing_urlopen,
        run_command=lambda *args, **kwargs: subprocess.CompletedProcess(
            args=list(args),
            returncode=1,
            stdout="",
            stderr="fixture gh api failure",
        ),
    )
    record_case(
        "urllib_failure_gh_api_failure",
        failed_payload,
        failed_findings,
        failed_payload == {}
        and any(item.startswith("urllib:") for item in failed_findings)
        and any(item.startswith("gh_api:") for item in failed_findings),
    )

    return findings, cases


def tar_members(path: Path) -> tuple[list[str], list[str]]:
    findings: list[str] = []
    members: list[str] = []
    if not path.is_file():
        return members, ["bundle_missing"]
    try:
        with tarfile.open(path, "r:gz") as tf:
            for member in tf.getmembers():
                name = member.name
                members.append(name)
                if name.startswith("/") or ".." in Path(name).parts:
                    findings.append(f"unsafe_member_path:{name}")
                if not member.isfile():
                    findings.append(f"non_file_member:{name}")
    except tarfile.TarError as exc:
        findings.append(f"tar_read_error:{exc}")
    return sorted(members), findings


def verify_extracted(bundle: Path) -> tuple[list[str], dict[str, Any]]:
    findings: list[str] = []
    commands: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="external_cuda_handoff_") as tmp:
        tmpdir = Path(tmp)
        try:
            with tarfile.open(bundle, "r:gz") as tf:
                tf.extractall(tmpdir, filter="data")
        except (tarfile.TarError, TypeError) as exc:
            return [f"extract_error:{exc}"], commands

        for script in [
            "external_cuda_handoff_r18.commands.sh",
            "external_cuda_vm_preflight_ubuntu.sh",
        ]:
            result = command_result(["bash", "-n", script], tmpdir)
            commands[f"bash_n:{script}"] = result
            if result["exit_code"] != 0:
                findings.append(f"bash_syntax:{script}")

        try:
            py_compile.compile(
                str(tmpdir / "apply_external_gpu_receipt_r18.py"),
                doraise=True,
            )
        except (py_compile.PyCompileError, OSError) as exc:
            findings.append(f"python_compile:apply_external_gpu_receipt_r18.py:{exc}")

        for member, snippets in REQUIRED_SNIPPETS.items():
            path = tmpdir / member
            if not path.is_file():
                findings.append(f"extracted_member_missing:{member}")
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for snippet in snippets:
                if snippet not in text:
                    findings.append(f"missing_snippet:{member}:{snippet}")
    return findings, commands


def verify_public_urls() -> tuple[list[str], dict[str, Any]]:
    findings: list[str] = []
    details: dict[str, Any] = {
        "handoff_url": request_builder.HANDOFF_URL,
        "handoff_sha_url": request_builder.HANDOFF_SHA_URL,
        "checked": True,
    }
    try:
        with urllib.request.urlopen(request_builder.HANDOFF_SHA_URL, timeout=30) as resp:
            sidecar_text = resp.read(10_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        findings.append(f"public_sidecar_fetch_error:{exc}")
        sidecar_text = ""
    details["public_sidecar_text"] = sidecar_text.strip()
    if request_builder.HANDOFF_SHA256 not in sidecar_text:
        findings.append("public_sidecar_expected_sha_missing")

    try:
        with urllib.request.urlopen(request_builder.HANDOFF_URL, timeout=60) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        findings.append(f"public_bundle_fetch_error:{exc}")
        data = b""
    if data:
        digest = hashlib.sha256(data).hexdigest()
        details["public_bundle_sha256"] = digest
        details["public_bundle_bytes"] = len(data)
        if digest != request_builder.HANDOFF_SHA256:
            findings.append("public_bundle_sha256_mismatch")

    comment_id = request_builder.OPERATOR_NOTE_URL.rsplit("#issuecomment-", 1)[-1]
    comment_api_url = (
        "https://api.github.com/repos/evaldataset/"
        "lottery-ticket-bayesian-modes-artifact/issues/comments/"
        f"{comment_id}"
    )
    details["operator_note_url"] = request_builder.OPERATOR_NOTE_URL
    details["operator_note_api_url"] = comment_api_url
    comment_payload, comment_fetch_findings = fetch_github_api_json(comment_api_url)
    details["operator_note_fetch_diagnostics"] = comment_fetch_findings
    details["operator_note_fetch_findings"] = [] if comment_payload else comment_fetch_findings
    if not comment_payload:
        findings.append(
            "public_operator_note_fetch_error:"
            + ";".join(comment_fetch_findings or ["empty_payload"])
        )
    comment_body = str(comment_payload.get("body", ""))
    details["operator_note_comment_id"] = comment_id
    details["operator_note_updated_at"] = str(comment_payload.get("updated_at", ""))
    details["operator_note_missing_snippets"] = [
        snippet for snippet in PUBLIC_OPERATOR_NOTE_SNIPPETS if snippet not in comment_body
    ]
    if details["operator_note_missing_snippets"]:
        findings.append("public_operator_note_missing_required_snippets")
    return findings, details


def verify_local_operator_note() -> tuple[list[str], dict[str, Any]]:
    details: dict[str, Any] = {
        "path": rel(LOCAL_OPERATOR_NOTE),
        "present": LOCAL_OPERATOR_NOTE.is_file(),
        "missing_snippets": [],
    }
    findings: list[str] = []
    if not LOCAL_OPERATOR_NOTE.is_file():
        return ["local_operator_note_missing"], details
    text = LOCAL_OPERATOR_NOTE.read_text(encoding="utf-8")
    details["sha256"] = sha256(LOCAL_OPERATOR_NOTE)
    details["missing_snippets"] = [
        snippet for snippet in LOCAL_OPERATOR_NOTE_SNIPPETS if snippet not in text
    ]
    if details["missing_snippets"]:
        findings.append("local_operator_note_missing_required_snippets")
    return findings, details


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    bundle = args.bundle
    sidecar = args.sidecar
    expected_sidecar_sha, sidecar_text = read_sidecar(sidecar)
    bundle_sha = sha256(bundle) if bundle.is_file() else ""
    members, tar_findings = tar_members(bundle)
    missing_members = sorted(set(EXPECTED_MEMBERS) - set(members))
    extra_members = sorted(set(members) - set(EXPECTED_MEMBERS))
    forbidden_members = [
        member
        for member in members
        for snippet in FORBIDDEN_MEMBER_SNIPPETS
        if snippet in member
    ]
    extracted_findings, command_checks = (
        verify_extracted(bundle) if bundle.is_file() else (["bundle_missing"], {})
    )
    local_operator_note_findings, local_operator_note_details = verify_local_operator_note()
    github_api_fetcher_findings, github_api_fetcher_cases = verify_github_api_fetcher()

    operator_findings: list[str] = []
    operator_bundle_sha = sha256(OPERATOR_BUNDLE_COPY) if OPERATOR_BUNDLE_COPY.is_file() else ""
    operator_sidecar_sha, operator_sidecar_text = read_sidecar(OPERATOR_SIDECAR_COPY)
    if not OPERATOR_BUNDLE_COPY.is_file():
        operator_findings.append("operator_bundle_copy_missing")
    elif operator_bundle_sha != bundle_sha:
        operator_findings.append("operator_bundle_copy_hash_mismatch")
    if not OPERATOR_SIDECAR_COPY.is_file():
        operator_findings.append("operator_sidecar_copy_missing")
    elif operator_sidecar_text != sidecar_text:
        operator_findings.append("operator_sidecar_copy_text_mismatch")

    public_url_findings: list[str] = []
    public_url_details: dict[str, Any] = {"checked": False}
    if args.check_urls:
        public_url_findings, public_url_details = verify_public_urls()

    sidecar_findings: list[str] = []
    if not sidecar.is_file():
        sidecar_findings.append("sidecar_missing")
    if expected_sidecar_sha != request_builder.HANDOFF_SHA256:
        sidecar_findings.append("sidecar_expected_sha_mismatch")
    if bundle_sha != request_builder.HANDOFF_SHA256:
        sidecar_findings.append("bundle_sha_mismatch")
    if expected_sidecar_sha and expected_sidecar_sha != bundle_sha:
        sidecar_findings.append("sidecar_bundle_sha_mismatch")
    if "external_cuda_handoff_r18_bundle.tar.gz" not in sidecar_text:
        sidecar_findings.append("sidecar_filename_missing")

    blockers: list[str] = []
    if not bundle.is_file():
        blockers.append("external_cuda_handoff_bundle_missing")
    if sidecar_findings:
        blockers.append("external_cuda_handoff_sidecar_invalid")
    if tar_findings:
        blockers.append("external_cuda_handoff_tar_invalid")
    if missing_members:
        blockers.append("external_cuda_handoff_members_missing")
    if extra_members:
        blockers.append("external_cuda_handoff_extra_members_present")
    if forbidden_members:
        blockers.append("external_cuda_handoff_forbidden_members_present")
    if extracted_findings:
        blockers.append("external_cuda_handoff_extracted_checks_failed")
    if local_operator_note_findings:
        blockers.append("external_cuda_handoff_local_operator_note_invalid")
    if operator_findings:
        blockers.append("external_cuda_handoff_operator_copy_invalid")
    if public_url_findings:
        blockers.append("external_cuda_handoff_public_urls_invalid")
    if github_api_fetcher_findings:
        blockers.append("external_cuda_handoff_github_api_fetcher_invalid")

    return {
        "external_cuda_handoff_bundle_verified": not blockers,
        "bundle": rel(bundle),
        "sidecar": rel(sidecar),
        "bundle_sha256": bundle_sha,
        "expected_sha256": request_builder.HANDOFF_SHA256,
        "sidecar_sha256": expected_sidecar_sha,
        "sidecar_text": sidecar_text,
        "expected_members": EXPECTED_MEMBERS,
        "members": members,
        "missing_members": missing_members,
        "extra_members": extra_members,
        "forbidden_members": forbidden_members,
        "sidecar_findings": sidecar_findings,
        "tar_findings": tar_findings,
        "extracted_findings": extracted_findings,
        "local_operator_note_findings": local_operator_note_findings,
        "local_operator_note_details": local_operator_note_details,
        "operator_findings": operator_findings,
        "operator_bundle": rel(OPERATOR_BUNDLE_COPY),
        "operator_bundle_sha256": operator_bundle_sha,
        "operator_sidecar": rel(OPERATOR_SIDECAR_COPY),
        "operator_sidecar_sha256": operator_sidecar_sha,
        "public_url_findings": public_url_findings,
        "public_url_details": public_url_details,
        "github_api_fetcher_findings": github_api_fetcher_findings,
        "github_api_fetcher_cases": github_api_fetcher_cases,
        "command_checks": command_checks,
        "blockers": blockers,
        "check_urls": args.check_urls,
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# External CUDA Handoff Bundle Verification",
        "",
        f"Verified: {payload['external_cuda_handoff_bundle_verified']}.",
        f"Bundle: `{payload['bundle']}`.",
        f"Bundle SHA256: `{payload['bundle_sha256']}`.",
        f"Expected SHA256: `{payload['expected_sha256']}`.",
        f"Sidecar: `{payload['sidecar']}`.",
        f"Operator copy: `{payload['operator_bundle']}`.",
        f"Check public URLs: {payload['check_urls']}.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["none"])
    for title, key in [
        ("Missing Members", "missing_members"),
        ("Extra Members", "extra_members"),
        ("Forbidden Members", "forbidden_members"),
        ("Sidecar Findings", "sidecar_findings"),
        ("Tar Findings", "tar_findings"),
        ("Extracted Findings", "extracted_findings"),
        ("Local Operator Note Findings", "local_operator_note_findings"),
        ("Operator Copy Findings", "operator_findings"),
        ("Public URL Findings", "public_url_findings"),
        ("GitHub API Fetcher Findings", "github_api_fetcher_findings"),
    ]:
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {item}" for item in payload[key] or ["none"])
    lines.extend(
        [
            "",
            "## GitHub API Fetcher Cases",
            "",
            "| Case | Passed | Findings |",
            "| --- | --- | --- |",
        ]
    )
    for case in payload["github_api_fetcher_cases"]:
        findings = "; ".join(case["findings"]) if case["findings"] else "none"
        lines.append(f"| {case['name']} | {case['passed']} | {findings} |")
    lines.extend(["", "## Members", ""])
    lines.extend(f"- `{item}`" for item in payload["members"] or ["none"])
    lines.extend(
        [
            "",
            "This file is generated by `scripts/verify_external_cuda_handoff_bundle.py`.",
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
                "external_cuda_handoff_bundle_verified": payload[
                    "external_cuda_handoff_bundle_verified"
                ],
                "blockers": payload["blockers"],
                "bundle_sha256": payload["bundle_sha256"],
                "out_json": rel(args.out_json),
                "out_md": rel(args.out_md),
            }
        )
    )
    if args.strict and not payload["external_cuda_handoff_bundle_verified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
