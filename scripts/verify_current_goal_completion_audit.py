#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-05-08"
AUDIT_MD = ROOT / "runs" / "current_goal_completion_audit_2026-05-07.md"
CHECKLIST_MD = ROOT / "runs" / f"tmlr_submission_checklist_{DATE}.md"
FINAL_GATE_JSON = ROOT / "runs" / f"tmlr_final_gate_{DATE}.json"
FINAL_GATE_CONTRACT_JSON = ROOT / "runs" / f"tmlr_final_gate_contract_{DATE}.json"
SYNC_JSON = ROOT / "runs" / f"tmlr_submission_snapshot_sync_{DATE}.json"
SNAPSHOT_INTEGRITY_JSON = (
    ROOT / "runs" / f"tmlr_submission_snapshot_integrity_{DATE}.json"
)
SNAPSHOT_DIR = ROOT / "dist" / f"lottery_tmlr_submission_snapshot_{DATE}"
OPERATOR_BUNDLE_JSON = ROOT / "runs" / f"tmlr_operator_handoff_bundle_{DATE}.json"
OPERATOR_BUNDLE_VERIFICATION_JSON = (
    ROOT / "runs" / f"tmlr_operator_handoff_bundle_verification_{DATE}.json"
)
ACTIVE_HANDOFF_JSON = ROOT / "runs" / f"tmlr_active_blocker_handoff_{DATE}.json"
ACTIVE_HANDOFF_VERIFICATION_JSON = (
    ROOT / "runs" / f"tmlr_active_blocker_handoff_verification_{DATE}.json"
)
ACTIVE_MONITOR_JSON = ROOT / "runs" / f"tmlr_active_blocker_monitor_{DATE}.json"
CLOSURE_WORKFLOW_JSON = (
    ROOT / "runs" / f"tmlr_active_blocker_closure_workflow_{DATE}.json"
)
CLOSURE_WORKFLOW_VERIFICATION_JSON = (
    ROOT / "runs" / f"tmlr_active_blocker_closure_workflow_verification_{DATE}.json"
)
EXTERNAL_CUDA_HANDOFF_JSON = (
    ROOT / "runs" / f"external_cuda_handoff_bundle_verification_{DATE}.json"
)
SUBMISSION_PACKET_JSON = ROOT / "runs" / f"tmlr_submission_packet_preflight_{DATE}.json"
OPENREVIEW_PASTE_PAYLOAD_JSON = (
    ROOT / "runs" / f"tmlr_openreview_paste_payload_{DATE}.json"
)
OPENREVIEW_PASTE_PAYLOAD_MD = (
    ROOT / "runs" / f"tmlr_openreview_paste_payload_{DATE}.md"
)
OPENREVIEW_FORM_PACKET_MD = ROOT / "runs" / f"tmlr_openreview_form_packet_{DATE}.md"
CUDA_ISSUE_POLL_JSON = ROOT / "runs" / f"external_cuda_issue_receipt_poll_{DATE}.json"
HUMAN_REPLY_JSON = ROOT / "runs" / f"tmlr_human_unblock_reply_{DATE}.json"
SUBMISSION_RECEIPT_JSON = (
    ROOT / "runs" / f"tmlr_openreview_submission_receipt_{DATE}.json"
)
AUTHOR_INPUTS_JSON = ROOT / "runs" / f"tmlr_external_author_inputs_template_{DATE}.json"
AUTHOR_INPUTS_STATUS_MD = ROOT / "runs" / f"tmlr_external_author_inputs_status_{DATE}.md"
PUBLIC_REPO = ROOT / "dist" / "lottery_public_repository_snapshot"
DEFAULT_OUT_JSON = (
    ROOT / "runs" / f"current_goal_completion_audit_verification_{DATE}.json"
)
DEFAULT_OUT_MD = (
    ROOT / "runs" / f"current_goal_completion_audit_verification_{DATE}.md"
)

EXPECTED_BLOCKERS = [
    "author_openreview_profiles_and_conflicts_not_recorded_locally",
    "funding_competing_interest_irb_llm_answers_not_recorded_locally",
    "tmlr_openreview_submission_receipt_missing",
    "public_release_upload_not_verified",
    "public_repository_state_not_verified",
    "external_ci_run_not_observed",
    "external_gpu_container_run_not_observed",
]
EXPECTED_CLOSURE_STAGE_ORDER = [
    "ready_to_submit",
    "post_submit",
    "strict_artifact",
    "goal",
]
EXPECTED_ACTIVE_HANDOFF_REQUIRED_SNIPPETS = 69
EXPECTED_ACTIVE_MONITOR_NEXT_ACTION_LABELS = [
    "create_human_reply",
    "fill_human_reply_required_policy_fields",
    "record_submission_receipt_json",
    "upload_current_public_release",
    "publish_current_source_snapshot",
    "record_external_ci_run",
    "obtain_external_cuda_receipt",
]
EXPECTED_ACTIVE_MONITOR_NEXT_ACTION_GATES = [
    "ready_to_submit",
    "ready_to_submit",
    "post_submit",
    "strict_artifact",
    "strict_artifact",
    "strict_artifact",
    "strict_artifact",
]
EXPECTED_PACKET_READY_TO_SUBMIT_BLOCKERS = EXPECTED_BLOCKERS[:2]
EXPECTED_PACKET_EXTERNAL_BLOCKERS = EXPECTED_BLOCKERS[:3]
EXPECTED_PACKET_SUBMISSION_RECORD_BLOCKERS = [
    "tmlr_openreview_submission_receipt_missing",
]
EXPECTED_PACKET_RECEIPT_FINDINGS = [
    "submission_receipt.author_inputs_status_not_ready_for_tmlr_preflight",
    "submission_receipt.tmlr_openreview_forum_url",
    "submission_receipt.tmlr_submission_id",
    "submission_receipt.submitted_at_iso8601_with_timezone",
    "submission_receipt.confirmation_email_or_receipt_path",
]
EXPECTED_EXTERNAL_CUDA_ISSUE_STATE = "OPEN"
EXPECTED_PASTE_READY_FIELDS = [
    "title",
    "abstract",
    "short_summary",
    "keywords",
    "artifact_code_statement",
    "broader_impact_ethics_statement",
]
EXPECTED_PASTE_READY_FIELD_GUARDRAILS = {
    "title": {"max_chars": 180, "min_words": 4},
    "abstract": {"max_words": 250, "min_words": 100},
    "short_summary": {"max_words": 50, "max_chars": 400},
    "keywords": {"min_count": 3, "max_count": 8, "max_keyword_chars": 64},
    "artifact_code_statement": {"max_words": 140},
    "broader_impact_ethics_statement": {"max_words": 180},
}
EXPECTED_PASTE_AUTHOR_SIDE_FIELDS_REQUIRED = [
    "author list and order",
    "active OpenReview profiles",
    "conflict metadata",
    "action-editor conflict screening",
    "funding statement",
    "competing-interest statement",
    "human-subjects/IRB confirmation",
    "originality and no-parallel-archival-review confirmation",
    "CC BY 4.0 confirmation",
    "TMLR OpenReview receipt after submission",
]
EXPECTED_PASTE_MD_SNIPPETS = [
    "Source form packet: `runs/tmlr_openreview_form_packet_2026-05-08.md`",
    "Ready fields pass: True.",
    "Draft candidates are intentionally withheld from this paste payload until",
    "Withheld candidate count: 8.",
    "8 conflict-screen findings withheld from this paste view.",
    "Use the local author-input template and action-editor recommendation record to resolve them.",
]
FORBIDDEN_PASTE_READY_FIELD_SNIPPETS = [
    "github.com/evaldataset",
    "openreview.net/forum",
    "arxiv.org",
    "author@",
    "/home/",
    "Projects/Lottery",
    "suan" + "lab",
    "OPENAI_API_KEY",
    "sk-",
    "AWS_SECRET",
    "AWS_ACCESS_KEY",
]

AUDIT_REQUIRED_SNIPPETS = [
    "Objective:",
    "Concrete success criteria:",
    "## Completion Decision",
    "Not complete.",
    "## Prompt-To-Artifact Checklist",
    "## Blocking Requirements",
    "top conf에 제출할 수준의 논문과 연구 성과가 나올 수 있도록",
    "The aggregate final gate therefore still reports `goal_complete: false`.",
    "final aggregate gate reports submission completion and strict artifact",
    "author_openreview_profiles_and_conflicts_not_recorded_locally",
    "funding_competing_interest_irb_llm_answers_not_recorded_locally",
    "tmlr_openreview_submission_receipt_missing",
    "external_gpu_container_run_not_observed",
    "45 required targets, 69 required README snippets",
    "external CUDA GitHub API fetcher case count 3 with no findings",
    "public URL findings now track the pending public handoff re-upload, while operator-note fetch and GitHub API fetcher findings remain clear over 3",
    "local operator-note content snippets",
    "post-validator CUDA issue poll/apply commands with `--check-urls --require-found`",
    "ready issue-receipt apply command's `--write --check-urls --require-found` requirement",
    "gate-ordered closure stages",
    "ready-to-submit, post-submit, strict-artifact, and goal stages",
    "scripts/verify_tmlr_final_gate_contract.py --strict",
    "tmlr_final_gate_contract_verified: true",
    "active-blocker handoff verifier `true` over 69 required Markdown snippets",
    "current `runs/tmlr_submission_snapshot_integrity_2026-05-08.json`",
    "snapshot_ready, blockers, upload parity, record parity, record count, and sidecars",
    "active monitor current human-reply, submission-receipt, external-CUDA issue-candidate, and next-action state",
    "direct file and issue-poll checks for absent human reply, absent OpenReview receipt, and zero valid external-CUDA candidates",
    "direct author-input template/status checks for unfilled OpenReview profile, conflict, funding, IRB, license, LLM, and receipt fields",
    "direct submission-packet detail checks for exact ready blockers, receipt findings, residual limitations, upload targets, request snippets, and external-CUDA overclaim count",
    "direct OpenReview paste-payload checks for ready fields, guardrails, withheld action-editor candidates, and author-side-only fields",
    "direct active-monitor issue metadata checks for URL-backed external-CUDA polling, open issue state, updated timestamp, and empty GitHub error",
    "direct public external-CUDA operator-note checks for posted validator instructions and issue-comment URL preservation",
    "direct external-CUDA operator-note-without-receipt checks for posted instructions with zero valid receipt candidates",
    "with 47 required snippets each and no missing snippets",
    "checked with 26 required snippets and no missing snippets",
    "scripts/verify_current_goal_completion_audit.py --strict",
    "current_goal_completion_audit_verified: true",
    "Only after the TMLR final gate reports `submission_complete: true`",
]

CHECKLIST_REQUIRED_SNIPPETS = [
    "Operator handoff bundle",
    "45 required targets, 69 README snippets",
    "external CUDA GitHub API fetcher case count 3 with zero findings",
    "gate-ordered closure stages",
    "Final gate contract",
    "checks 69 required Markdown snippets",
    "Human-unblock request pointers",
    "current-goal audit directly checks the current snapshot-integrity report",
    "active monitor current human-reply, submission-receipt, external-CUDA issue-candidate, and next-action state",
    "direct file and issue-poll checks for absent human reply, absent OpenReview receipt, and zero valid external-CUDA candidates",
    "direct author-input template/status checks for unfilled OpenReview profile, conflict, funding, IRB, license, LLM, and receipt fields",
    "direct submission-packet detail checks for exact ready blockers, receipt findings, residual limitations, upload targets, request snippets, and external-CUDA overclaim count",
    "direct OpenReview paste-payload checks for ready fields, guardrails, withheld action-editor candidates, and author-side-only fields",
    "direct active-monitor issue metadata checks for URL-backed external-CUDA polling, open issue state, updated timestamp, and empty GitHub error",
    "direct public external-CUDA operator-note checks for posted validator instructions and issue-comment URL preservation",
    "direct external-CUDA operator-note-without-receipt checks for posted instructions with zero valid receipt candidates",
    "47 required snippets each",
    "does not replace the missing author/OpenReview receipt or external CUDA receipt",
]

STALE_STRINGS = [
    "9d1b7fa07165b3775fd2d7aa9b53414396547db5e8379703662f2728864ccdd3",
    "83ec4fdc4796ee2c6a13482b8df4aa7afc8397f6fc58455e8bc7c99c1f0008a1",
    "f3f9d2e5204118fe8978188da34f0e072a702e89c83bf6b9758659cc5299e690",
    "3143d78b7a9282485e92967d848637b38f9bdca790988d5ebd6036d23b1f6b45",
    "7079eb17ea939012c5776f51d1f8c27fe091d90e2f0d94e8d09eeabf9ff47b3a",
    "38 required targets, 39 required README snippets",
    "38 required targets, 39 README snippets",
    "39 required targets, 40 required README snippets",
    "39 required targets, 40 README snippets",
    "39 required targets, 43 required README snippets",
    "39 required targets, 43 README snippets",
    "operator handoff 39-target/43-README-snippet coverage",
    "39 required targets, 49 required README snippets",
    "39 required targets, 49 README snippets",
    "43 required targets, 56 required README snippets",
    "43 required targets, 56 README snippets",
    "operator handoff 43-target/56-README-snippet coverage",
    "43 required targets, 62 required README snippets",
    "43 required targets, 62 README snippets",
    "operator handoff 43-target/62-README-snippet coverage",
    "45 required targets, 66 required README snippets",
    "45 required targets, 66 README snippets",
    "66 required Markdown snippets",
    "38 required targets, 37 required README snippets",
    "38 required targets, 37 README snippets",
    "37 required targets, 36 required README snippets",
    "37 required targets, 36 README snippets",
    "37 required targets, 32 required README snippets",
    "37 required targets, 32 README snippets",
    "post-validator CUDA issue poll/apply commands with `--check-urls`",
    "ready issue-receipt apply command's `--write --check-urls` requirement",
    "55 required Markdown snippets",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that the current goal completion audit reflects the current "
            "TMLR final gate, snapshot sync, operator handoff, and external-CUDA "
            "handoff evidence instead of stale proxy signals."
        )
    )
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if not verified.")
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def command_result(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout.strip()[-1000:],
        "stderr_tail": proc.stderr.strip()[-1000:],
    }


def list_nonempty_locks() -> list[str]:
    runs = ROOT / "runs"
    if not runs.is_dir():
        return ["runs_missing"]
    return sorted(
        rel(path)
        for path in runs.glob("*.lock")
        if path.is_file() and path.stat().st_size > 0
    )


def exact_blockers(value: Any) -> bool:
    return [str(item) for item in value or []] == EXPECTED_BLOCKERS


def snapshot_manifest_sha(payload: dict[str, Any]) -> str:
    manifest = payload.get("manifest", {})
    if isinstance(manifest, dict):
        return str(manifest.get("sha256", ""))
    return str(payload.get("manifest_sha256", ""))


def copied_snapshot_record_matches(source: Path, record_name: str) -> bool:
    target = SNAPSHOT_DIR / "records" / record_name
    if not source.is_file() or not target.is_file():
        return False
    return source.read_bytes() == target.read_bytes()


def sidecars_ok(value: Any) -> bool:
    if not isinstance(value, dict) or not value:
        return False
    return all(isinstance(item, dict) and item.get("ok") is True for item in value.values())


def candidate_names_from_conflict_findings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        text = str(item)
        if "]." not in text or "." not in text:
            continue
        name = text.split("].", 1)[1].rsplit(".", 1)[0].strip()
        if name and name not in names:
            names.append(name)
    return names


def paste_metric_guardrail_findings(metrics: Any) -> list[str]:
    if not isinstance(metrics, dict):
        return ["ready_field_metrics"]
    findings: list[str] = []
    for field, rules in EXPECTED_PASTE_READY_FIELD_GUARDRAILS.items():
        values = metrics.get(field, {})
        if not isinstance(values, dict):
            findings.append(f"{field}.missing_metrics")
            continue
        chars = int(values.get("chars") or 0)
        words = int(values.get("words") or 0)
        line_count = int(values.get("line_count") or 0)
        if line_count < 1:
            findings.append(f"{field}.line_count")
        if chars < 1:
            findings.append(f"{field}.chars")
        if words < 1:
            findings.append(f"{field}.words")
        if "max_chars" in rules and chars > int(rules["max_chars"]):
            findings.append(f"{field}.max_chars")
        if "min_words" in rules and words < int(rules["min_words"]):
            findings.append(f"{field}.min_words")
        if "max_words" in rules and words > int(rules["max_words"]):
            findings.append(f"{field}.max_words")
        if field == "keywords":
            keyword_count = int(values.get("keyword_count") or 0)
            max_keyword_chars = int(values.get("max_keyword_chars") or 0)
            keywords = values.get("keywords", [])
            if not isinstance(keywords, list) or not all(str(item).strip() for item in keywords):
                findings.append("keywords.keywords")
            if keyword_count < int(rules["min_count"]):
                findings.append("keywords.min_count")
            if keyword_count > int(rules["max_count"]):
                findings.append("keywords.max_count")
            if max_keyword_chars > int(rules["max_keyword_chars"]):
                findings.append("keywords.max_keyword_chars")
    return findings


def build_payload() -> dict[str, Any]:
    audit_text = read_text(AUDIT_MD)
    checklist_text = read_text(CHECKLIST_MD)
    author_inputs_status_text = read_text(AUTHOR_INPUTS_STATUS_MD)
    paste_payload_text = read_text(OPENREVIEW_PASTE_PAYLOAD_MD)
    form_packet_text = read_text(OPENREVIEW_FORM_PACKET_MD)
    final_gate = load_json(FINAL_GATE_JSON)
    final_gate_contract = load_json(FINAL_GATE_CONTRACT_JSON)
    sync = load_json(SYNC_JSON)
    snapshot_integrity = load_json(SNAPSHOT_INTEGRITY_JSON)
    operator_bundle = load_json(OPERATOR_BUNDLE_JSON)
    operator_verification = load_json(OPERATOR_BUNDLE_VERIFICATION_JSON)
    active_handoff = load_json(ACTIVE_HANDOFF_JSON)
    active_handoff_verification = load_json(ACTIVE_HANDOFF_VERIFICATION_JSON)
    active_monitor = load_json(ACTIVE_MONITOR_JSON)
    closure_workflow = load_json(CLOSURE_WORKFLOW_JSON)
    closure_verification = load_json(CLOSURE_WORKFLOW_VERIFICATION_JSON)
    external_cuda = load_json(EXTERNAL_CUDA_HANDOFF_JSON)
    submission_packet = load_json(SUBMISSION_PACKET_JSON)
    openreview_paste_payload = load_json(OPENREVIEW_PASTE_PAYLOAD_JSON)
    issue_poll = load_json(CUDA_ISSUE_POLL_JSON)
    author_inputs = load_json(AUTHOR_INPUTS_JSON)
    upload_comparison = snapshot_integrity.get("upload_comparison", {})
    record_comparison = snapshot_integrity.get("record_comparison", {})

    public_git_status = command_result(
        ["git", "-C", str(PUBLIC_REPO), "status", "--short"]
    )

    missing_audit_snippets = [
        snippet for snippet in AUDIT_REQUIRED_SNIPPETS if snippet not in audit_text
    ]
    missing_checklist_snippets = [
        snippet for snippet in CHECKLIST_REQUIRED_SNIPPETS if snippet not in checklist_text
    ]
    stale_hits = [
        stale
        for stale in STALE_STRINGS
        if stale in audit_text or stale in checklist_text
    ]
    nonempty_locks = list_nonempty_locks()

    external_cases = external_cuda.get("github_api_fetcher_cases", [])
    active_handoff_cuda = (
        active_handoff.get("external_cuda_receipt", {}).get("handoff_bundle", {})
        if isinstance(active_handoff.get("external_cuda_receipt", {}), dict)
        else {}
    )

    findings: list[str] = []
    if missing_audit_snippets:
        findings.append("audit_missing_required_snippets")
    if missing_checklist_snippets:
        findings.append("checklist_missing_required_snippets")
    if stale_hits:
        findings.append("stale_audit_or_checklist_strings_present")
    if not copied_snapshot_record_matches(AUDIT_MD, AUDIT_MD.name):
        findings.append("snapshot_audit_record_mismatch")
    if not copied_snapshot_record_matches(CHECKLIST_MD, CHECKLIST_MD.name):
        findings.append("snapshot_checklist_record_mismatch")
    if snapshot_integrity.get("snapshot_ready") is not True:
        findings.append("snapshot_integrity.snapshot_ready")
    if snapshot_integrity.get("blockers"):
        findings.append("snapshot_integrity.blockers")
    if not isinstance(upload_comparison, dict) or upload_comparison.get("all_match") is not True:
        findings.append("snapshot_integrity.upload_comparison")
    if not isinstance(record_comparison, dict) or record_comparison.get("all_match") is not True:
        findings.append("snapshot_integrity.record_comparison")
    if record_comparison.get("expected_count") != 77:
        findings.append("snapshot_integrity.record_comparison.expected_count")
    if record_comparison.get("actual_count") != 77:
        findings.append("snapshot_integrity.record_comparison.actual_count")
    if not sidecars_ok(snapshot_integrity.get("upload_sidecars")):
        findings.append("snapshot_integrity.upload_sidecars")
    if not sidecars_ok(snapshot_integrity.get("bundle_sidecars")):
        findings.append("snapshot_integrity.bundle_sidecars")

    if final_gate.get("local_file_packet_ready") is not True:
        findings.append("final_gate.local_file_packet_ready")
    if final_gate.get("ready_to_submit") is not False:
        findings.append("final_gate.ready_to_submit")
    if final_gate.get("submission_complete") is not False:
        findings.append("final_gate.submission_complete")
    if final_gate.get("strict_artifact_ready") is not False:
        findings.append("final_gate.strict_artifact_ready")
    if final_gate.get("goal_complete") is not False:
        findings.append("final_gate.goal_complete")
    if not exact_blockers(final_gate.get("blockers", [])):
        findings.append("final_gate.blockers")
    if final_gate_contract.get("tmlr_final_gate_contract_verified") is not True:
        findings.append("final_gate_contract.verified")
    if final_gate_contract.get("findings"):
        findings.append("final_gate_contract.findings")

    if sync.get("synced") is not True:
        findings.append("sync.synced")
    if sync.get("copied_upload_count") != 4:
        findings.append("sync.copied_upload_count")
    if sync.get("copied_record_count_final") != 77:
        findings.append("sync.copied_record_count_final")
    if sync.get("snapshot_ready") is not True:
        findings.append("sync.snapshot_ready")
    if sync.get("local_file_packet_ready") is not True:
        findings.append("sync.local_file_packet_ready")
    if sync.get("ready_to_submit") is not False:
        findings.append("sync.ready_to_submit")
    if sync.get("submission_complete") is not False:
        findings.append("sync.submission_complete")
    if sync.get("strict_artifact_ready") is not False:
        findings.append("sync.strict_artifact_ready")
    if sync.get("goal_complete") is not False:
        findings.append("sync.goal_complete")
    if sync.get("failed_commands"):
        findings.append("sync.failed_commands")
    if sync.get("blocking_failed_commands"):
        findings.append("sync.blocking_failed_commands")
    if sync.get("transient_failed_commands"):
        findings.append("sync.transient_failed_commands")
    if not exact_blockers(sync.get("blockers", [])):
        findings.append("sync.blockers")
    sync_commands = sync.get("commands", {})
    sync_contract_command = (
        sync_commands.get("convergence_final_gate_contract_verification", {})
        if isinstance(sync_commands, dict)
        else {}
    )
    if sync_contract_command.get("exit_code") != 0:
        findings.append("sync.convergence_final_gate_contract_verification")
    if sync.get("manifest_sha256") != snapshot_manifest_sha(snapshot_integrity):
        findings.append("snapshot_manifest_hash_mismatch")

    if submission_packet.get("file_packet_ready") is not True:
        findings.append("submission_packet.file_packet_ready")
    if submission_packet.get("ready_to_submit") is not False:
        findings.append("submission_packet.ready_to_submit")
    if submission_packet.get("submission_complete") is not False:
        findings.append("submission_packet.submission_complete")
    if submission_packet.get("submission_recorded") is not False:
        findings.append("submission_packet.submission_recorded")
    if submission_packet.get("risk_flags") != []:
        findings.append("submission_packet.risk_flags")
    if submission_packet.get("ready_to_submit_blockers") != (
        EXPECTED_PACKET_READY_TO_SUBMIT_BLOCKERS
    ):
        findings.append("submission_packet.ready_to_submit_blockers")
    if submission_packet.get("external_blockers") != EXPECTED_PACKET_EXTERNAL_BLOCKERS:
        findings.append("submission_packet.external_blockers")
    if submission_packet.get("submission_record_blockers") != (
        EXPECTED_PACKET_SUBMISSION_RECORD_BLOCKERS
    ):
        findings.append("submission_packet.submission_record_blockers")
    if submission_packet.get("residual_limitations") != [
        "strict_external_cuda_host_gpu_container_receipt_pending"
    ]:
        findings.append("submission_packet.residual_limitations")
    packet_author_inputs = submission_packet.get("author_inputs", {})
    if not isinstance(packet_author_inputs, dict):
        findings.append("submission_packet.author_inputs")
        packet_author_inputs = {}
    else:
        if packet_author_inputs.get("authors_ready") is not False:
            findings.append("submission_packet.author_inputs.authors_ready")
        if packet_author_inputs.get("funding_irb_ready") is not False:
            findings.append("submission_packet.author_inputs.funding_irb_ready")
        if packet_author_inputs.get("submission_receipt_ready") is not False:
            findings.append("submission_packet.author_inputs.submission_receipt_ready")
        if packet_author_inputs.get("payload_status") != "template_unfilled":
            findings.append("submission_packet.author_inputs.payload_status")
        if packet_author_inputs.get("submission_receipt_findings") != (
            EXPECTED_PACKET_RECEIPT_FINDINGS
        ):
            findings.append("submission_packet.author_inputs.submission_receipt_findings")
        conflict_findings = packet_author_inputs.get(
            "action_editor_conflict_screen_findings", []
        )
        if not isinstance(conflict_findings, list) or len(conflict_findings) != 8:
            findings.append(
                "submission_packet.author_inputs.action_editor_conflict_screen_findings"
            )
    packet_upload_targets = submission_packet.get("upload_targets", {})
    if not isinstance(packet_upload_targets, dict):
        findings.append("submission_packet.upload_targets")
    else:
        for key in [
            "ready",
            "bundle_matches",
            "file_inventory_matches",
            "target_names_match",
            "target_hashes_match",
        ]:
            if packet_upload_targets.get(key) is not True:
                findings.append(f"submission_packet.upload_targets.{key}")
        if packet_upload_targets.get("blockers") != []:
            findings.append("submission_packet.upload_targets.blockers")
        if packet_upload_targets.get("expected_upload_target_file_names") != [
            "main_tmlr.pdf",
            "lottery_tmlr_supplement_source_2026-05-08.zip",
        ]:
            findings.append("submission_packet.upload_targets.expected_upload_target_file_names")
    packet_upload_readme = submission_packet.get("upload_readme", {})
    if not isinstance(packet_upload_readme, dict) or packet_upload_readme.get("ready") is not True:
        findings.append("submission_packet.upload_readme.ready")
    elif packet_upload_readme.get("required_snippet_count") != 27:
        findings.append("submission_packet.upload_readme.required_snippet_count")
    for request_key, expected_count in [
        ("human_unblock_request", 47),
        ("human_unblock_request_ko", 47),
        ("author_input_collection_request", 26),
    ]:
        request_payload = submission_packet.get(request_key, {})
        if not isinstance(request_payload, dict):
            findings.append(f"submission_packet.{request_key}")
            continue
        if request_payload.get("ready") is not True:
            findings.append(f"submission_packet.{request_key}.ready")
        if request_payload.get("required_snippet_count") != expected_count:
            findings.append(f"submission_packet.{request_key}.required_snippet_count")
        if request_payload.get("missing_required_snippets") != []:
            findings.append(f"submission_packet.{request_key}.missing_required_snippets")
    packet_external_cuda_wording = submission_packet.get("external_cuda_wording", {})
    if not isinstance(packet_external_cuda_wording, dict):
        findings.append("submission_packet.external_cuda_wording")
    else:
        if packet_external_cuda_wording.get("ready") is not True:
            findings.append("submission_packet.external_cuda_wording.ready")
        if packet_external_cuda_wording.get("pdf_required_snippet_count") != 3:
            findings.append(
                "submission_packet.external_cuda_wording.pdf_required_snippet_count"
            )
        if packet_external_cuda_wording.get("paste_required_snippet_count") != 3:
            findings.append(
                "submission_packet.external_cuda_wording.paste_required_snippet_count"
            )
        for key in [
            "missing_pdf_required_snippets",
            "missing_paste_required_snippets",
            "overclaim_findings",
        ]:
            if packet_external_cuda_wording.get(key) != []:
                findings.append(f"submission_packet.external_cuda_wording.{key}")
    for file_key in ["primary_pdf", "supplement"]:
        file_payload = submission_packet.get(file_key, {})
        if not isinstance(file_payload, dict):
            findings.append(f"submission_packet.{file_key}")
            continue
        for key in ["present", "sidecar_present", "hash_ok"]:
            if file_payload.get(key) is not True:
                findings.append(f"submission_packet.{file_key}.{key}")
    supplement_payload = submission_packet.get("supplement", {})
    if isinstance(supplement_payload, dict):
        if supplement_payload.get("under_tmlr_limit") is not True:
            findings.append("submission_packet.supplement.under_tmlr_limit")
        zip_scan = supplement_payload.get("zip_scan", {})
        if not isinstance(zip_scan, dict):
            findings.append("submission_packet.supplement.zip_scan")
        else:
            if zip_scan.get("verify_tmlr_supplement_exit") != 0:
                findings.append("submission_packet.supplement.zip_scan.verify_exit")
            for key in ["required_missing", "forbidden_paths", "text_findings"]:
                if zip_scan.get(key) != []:
                    findings.append(f"submission_packet.supplement.zip_scan.{key}")

    if not OPENREVIEW_PASTE_PAYLOAD_JSON.is_file():
        findings.append("openreview_paste_payload.json_missing")
    if not OPENREVIEW_PASTE_PAYLOAD_MD.is_file():
        findings.append("openreview_paste_payload.markdown_missing")
    if not OPENREVIEW_FORM_PACKET_MD.is_file():
        findings.append("openreview_paste_payload.form_packet_missing")
    if openreview_paste_payload.get("source_form_packet") != rel(OPENREVIEW_FORM_PACKET_MD):
        findings.append("openreview_paste_payload.source_form_packet")
    if openreview_paste_payload.get("ready_fields_pass") is not True:
        findings.append("openreview_paste_payload.ready_fields_pass")
    if openreview_paste_payload.get("missing_ready_fields") != []:
        findings.append("openreview_paste_payload.missing_ready_fields")
    if openreview_paste_payload.get("ready_field_findings") != []:
        findings.append("openreview_paste_payload.ready_field_findings")
    if openreview_paste_payload.get("ready_field_guardrail_findings") != []:
        findings.append("openreview_paste_payload.ready_field_guardrail_findings")
    if openreview_paste_payload.get("ready_field_guardrails") != (
        EXPECTED_PASTE_READY_FIELD_GUARDRAILS
    ):
        findings.append("openreview_paste_payload.ready_field_guardrails")
    paste_ready_fields = openreview_paste_payload.get("ready_fields", {})
    if not isinstance(paste_ready_fields, dict):
        findings.append("openreview_paste_payload.ready_fields")
        paste_ready_fields = {}
    elif list(paste_ready_fields) != EXPECTED_PASTE_READY_FIELDS:
        findings.append("openreview_paste_payload.ready_field_keys")
    paste_metrics = openreview_paste_payload.get("ready_field_metrics", {})
    metric_guardrail_findings = paste_metric_guardrail_findings(paste_metrics)
    if metric_guardrail_findings:
        findings.append("openreview_paste_payload.ready_field_metric_guardrails")
    ready_field_joined = "\n".join(str(paste_ready_fields.get(field, "")) for field in EXPECTED_PASTE_READY_FIELDS)
    for field in EXPECTED_PASTE_READY_FIELDS:
        value = str(paste_ready_fields.get(field, "")).strip()
        if not value:
            findings.append(f"openreview_paste_payload.ready_fields.{field}")
            continue
        if value not in form_packet_text:
            findings.append(f"openreview_paste_payload.form_packet_value:{field}")
        if value not in paste_payload_text:
            findings.append(f"openreview_paste_payload.markdown_value:{field}")
    for snippet in FORBIDDEN_PASTE_READY_FIELD_SNIPPETS:
        if snippet.lower() in ready_field_joined.lower():
            findings.append(f"openreview_paste_payload.ready_field_forbidden:{snippet}")
    for snippet in EXPECTED_PASTE_MD_SNIPPETS:
        if snippet not in paste_payload_text:
            findings.append(f"openreview_paste_payload.markdown_missing_snippet:{snippet}")
    if rel(OPENREVIEW_PASTE_PAYLOAD_MD) not in form_packet_text:
        findings.append("openreview_paste_payload.form_packet_paste_payload_pointer")
    if "Draft candidates, pending author conflict screening:" not in form_packet_text:
        findings.append("openreview_paste_payload.form_packet_action_editor_section")
    if "## Fields Requiring Author Input" not in form_packet_text:
        findings.append("openreview_paste_payload.form_packet_author_fields_section")

    paste_action_editors = openreview_paste_payload.get("action_editor_recommendations", {})
    if not isinstance(paste_action_editors, dict):
        findings.append("openreview_paste_payload.action_editor_recommendations")
        paste_action_editors = {}
    else:
        if paste_action_editors.get("paste_ready") is not False:
            findings.append("openreview_paste_payload.action_editors.paste_ready")
        if paste_action_editors.get("reason") != (
            "Author conflict screening is required before using these candidates in OpenReview."
        ):
            findings.append("openreview_paste_payload.action_editors.reason")
        if paste_action_editors.get("action_editors_file") != (
            "runs/tmlr_action_editor_recommendations_2026-05-08.json"
        ):
            findings.append("openreview_paste_payload.action_editors.action_editors_file")
        if paste_action_editors.get("candidate_source") != "action_editor_recommendations_json":
            findings.append("openreview_paste_payload.action_editors.candidate_source")
        if paste_action_editors.get("author_inputs_file") != rel(AUTHOR_INPUTS_JSON):
            findings.append("openreview_paste_payload.action_editors.author_inputs_file")
        if paste_action_editors.get("candidates_withheld_until_conflict_screen") is not True:
            findings.append("openreview_paste_payload.action_editors.candidates_withheld")
        if paste_action_editors.get("withheld_candidate_count") != 8:
            findings.append("openreview_paste_payload.action_editors.withheld_candidate_count")
        if paste_action_editors.get("primary_candidates") != []:
            findings.append("openreview_paste_payload.action_editors.primary_candidates")
        if paste_action_editors.get("alternate_candidates") != []:
            findings.append("openreview_paste_payload.action_editors.alternate_candidates")
    paste_conflict_findings = paste_action_editors.get("conflict_screen_findings", [])
    if not isinstance(paste_conflict_findings, list) or len(paste_conflict_findings) != 8:
        findings.append("openreview_paste_payload.action_editors.conflict_screen_findings")
        paste_conflict_findings = []
    elif any(".screened_by_all_authors" not in str(item) for item in paste_conflict_findings):
        findings.append("openreview_paste_payload.action_editors.conflict_screen_finding_labels")
    paste_candidate_names = candidate_names_from_conflict_findings(paste_conflict_findings)
    if len(paste_candidate_names) != 8:
        findings.append("openreview_paste_payload.action_editors.candidate_name_count")
    paste_candidate_name_leaks = sorted(
        name for name in paste_candidate_names if name and name in paste_payload_text
    )
    if paste_candidate_name_leaks:
        findings.append("openreview_paste_payload.markdown_candidate_names_leaked")
    if "Primary draft candidates:" in paste_payload_text or "Alternate draft candidates:" in paste_payload_text:
        findings.append("openreview_paste_payload.markdown_candidate_sections_visible")
    paste_author_side_fields = openreview_paste_payload.get("author_side_fields_required", [])
    if paste_author_side_fields != EXPECTED_PASTE_AUTHOR_SIDE_FIELDS_REQUIRED:
        findings.append("openreview_paste_payload.author_side_fields_required")
    for item in EXPECTED_PASTE_AUTHOR_SIDE_FIELDS_REQUIRED:
        if f"- {item}" not in paste_payload_text:
            findings.append(f"openreview_paste_payload.markdown_author_side_field:{item}")

    if operator_verification.get("tmlr_operator_handoff_bundle_verified") is not True:
        findings.append("operator_handoff_bundle.verified")
    if operator_verification.get("required_target_count") != 45:
        findings.append("operator_handoff_bundle.required_target_count")
    if operator_verification.get("required_readme_snippet_count") != 69:
        findings.append("operator_handoff_bundle.required_readme_snippet_count")
    if operator_verification.get("blockers"):
        findings.append("operator_handoff_bundle.blockers")
    if operator_bundle.get("external_cuda_handoff", {}).get(
        "github_api_fetcher_case_count"
    ) != 3:
        findings.append("operator_handoff_bundle.external_cuda_handoff.case_count")
    for key in [
        "github_api_fetcher_findings",
        "operator_note_fetch_findings",
    ]:
        if operator_bundle.get("external_cuda_handoff", {}).get(key):
            findings.append(f"operator_handoff_bundle.external_cuda_handoff.{key}")

    external_cuda_public_only_blocked = [
        str(item) for item in external_cuda.get("blockers", [])
    ] == ["external_cuda_handoff_public_urls_invalid"]
    if (
        external_cuda.get("external_cuda_handoff_bundle_verified") is not True
        and not external_cuda_public_only_blocked
    ):
        findings.append("external_cuda_handoff.verified")
    if external_cuda.get("blockers") and not external_cuda_public_only_blocked:
        findings.append("external_cuda_handoff.blockers")
    if len(external_cases) != 3:
        findings.append("external_cuda_handoff.github_api_fetcher_case_count")
    if any(not case.get("passed") for case in external_cases if isinstance(case, dict)):
        findings.append("external_cuda_handoff.github_api_fetcher_case_failed")
    if external_cuda.get("github_api_fetcher_findings"):
        findings.append("external_cuda_handoff.github_api_fetcher_findings")
    if external_cuda.get("public_url_details", {}).get("operator_note_fetch_findings"):
        findings.append("external_cuda_handoff.operator_note_fetch_findings")
    if external_cuda.get("local_operator_note_findings"):
        findings.append("external_cuda_handoff.local_operator_note_findings")
    local_operator_note_details = external_cuda.get("local_operator_note_details", {})
    if local_operator_note_details.get("present") is not True:
        findings.append("external_cuda_handoff.local_operator_note.present")
    if local_operator_note_details.get("missing_snippets"):
        findings.append("external_cuda_handoff.local_operator_note.missing_snippets")

    if active_handoff.get("current_gate", {}).get("goal_complete") is not False:
        findings.append("active_handoff.goal_complete")
    if not exact_blockers(active_handoff.get("current_gate", {}).get("blockers", [])):
        findings.append("active_handoff.blockers")
    if (
        active_handoff_verification.get("tmlr_active_blocker_handoff_verified")
        is not True
    ):
        findings.append("active_handoff_verification.verified")
    if active_handoff_verification.get("required_markdown_snippet_count") != (
        EXPECTED_ACTIVE_HANDOFF_REQUIRED_SNIPPETS
    ):
        findings.append("active_handoff_verification.required_markdown_snippet_count")
    if active_handoff_verification.get("blockers"):
        findings.append("active_handoff_verification.blockers")
    if active_handoff_cuda.get("github_api_fetcher_case_count") != 3:
        findings.append("active_handoff.github_api_fetcher_case_count")
    if active_handoff_cuda.get("github_api_fetcher_findings"):
        findings.append("active_handoff.github_api_fetcher_findings")

    if HUMAN_REPLY_JSON.is_file():
        findings.append("external_blocker_inputs.human_reply_file_present")
    if SUBMISSION_RECEIPT_JSON.is_file():
        findings.append("external_blocker_inputs.submission_receipt_file_present")
    if issue_poll.get("external_cuda_issue_receipt_poll_ready") is not False:
        findings.append("external_blocker_inputs.issue_poll_ready")
    if issue_poll.get("check_urls") is not True:
        findings.append("external_blocker_inputs.issue_poll_check_urls")
    if issue_poll.get("issue_state") != EXPECTED_EXTERNAL_CUDA_ISSUE_STATE:
        findings.append("external_blocker_inputs.issue_poll_issue_state")
    if issue_poll.get("gh_error"):
        findings.append("external_blocker_inputs.issue_poll_gh_error")
    if not issue_poll.get("issue_updated_at"):
        findings.append("external_blocker_inputs.issue_poll_issue_updated_at")
    if int(issue_poll.get("comment_count") or 0) < 1:
        findings.append("external_blocker_inputs.issue_poll_comment_count")
    if issue_poll.get("valid_candidate_count") != 0:
        findings.append("external_blocker_inputs.issue_poll_valid_candidate_count")
    if issue_poll.get("linked_receipt_fetch_error_count") != 0:
        findings.append("external_blocker_inputs.issue_poll_linked_fetch_errors")
    if int(issue_poll.get("operator_note_comment_count") or 0) < 1:
        findings.append("external_blocker_inputs.operator_note_comment_count")
    if issue_poll.get("operator_note_without_receipt") is not True:
        findings.append("external_blocker_inputs.operator_note_without_receipt")
    operator_note_urls = issue_poll.get("operator_note_comment_urls", [])
    if not isinstance(operator_note_urls, list) or not operator_note_urls:
        findings.append("external_blocker_inputs.operator_note_comment_urls")
        operator_note_urls = []
    elif not all(
        str(url).startswith(
            "https://github.com/evaldataset/lottery-ticket-bayesian-modes-artifact/issues/1#issuecomment-"
        )
        for url in operator_note_urls
    ):
        findings.append("external_blocker_inputs.operator_note_comment_url_shape")

    author_input_status_snippets = [
        "Input file status: `template_unfilled`.",
        "Ready to submit author fields: False.",
        "Submission receipt recorded: False.",
        "`authors[1].name`",
        "`author_order_confirmed`",
        "`funding_statement`",
        "`competing_interests_statement`",
        "`human_subjects_irb.confirmed_by_all_authors`",
        "`cc_by_4_0.all_authors_confirm_tmlr_submission_license`",
        "`llm_use_policy.authors_take_full_responsibility`",
        "`llm_use_policy.no_llm_listed_as_author`",
        "`submission_receipt.tmlr_openreview_forum_url`",
        "`submission_receipt.tmlr_submission_id`",
    ]
    for snippet in author_input_status_snippets:
        if snippet not in author_inputs_status_text:
            findings.append(f"author_inputs_status.missing_snippet:{snippet}")
    if author_inputs.get("status") != "template_unfilled":
        findings.append("author_inputs.status")
    authors = author_inputs.get("authors", [])
    first_author = authors[0] if isinstance(authors, list) and authors else {}
    if not isinstance(first_author, dict):
        findings.append("author_inputs.authors")
        first_author = {}
    for key in ["name", "openreview_profile_url", "current_affiliation", "email_for_submission"]:
        if str(first_author.get(key, "")):
            findings.append(f"author_inputs.authors[0].{key}")
    if first_author.get("conflicts_complete") is not False:
        findings.append("author_inputs.authors[0].conflicts_complete")
    for key in [
        "author_order_confirmed",
        "all_authors_have_active_openreview_profiles",
        "conflicts_recorded_in_openreview",
        "action_editor_conflict_screen_complete",
    ]:
        if author_inputs.get(key) is not False:
            findings.append(f"author_inputs.{key}")
    action_editor_screen = author_inputs.get("action_editor_conflict_screen", [])
    if not isinstance(action_editor_screen, list) or len(action_editor_screen) != 8:
        findings.append("author_inputs.action_editor_conflict_screen.count")
    elif any(
        not isinstance(item, dict) or item.get("screened_by_all_authors") is not False
        for item in action_editor_screen
    ):
        findings.append("author_inputs.action_editor_conflict_screen.screening_state")
    if str(author_inputs.get("funding_statement", "")):
        findings.append("author_inputs.funding_statement")
    if str(author_inputs.get("competing_interests_statement", "")):
        findings.append("author_inputs.competing_interests_statement")
    human_subjects = author_inputs.get("human_subjects_irb", {})
    if not isinstance(human_subjects, dict) or human_subjects.get("confirmed_by_all_authors") is not False:
        findings.append("author_inputs.human_subjects_irb.confirmed_by_all_authors")
    originality = author_inputs.get("originality_and_parallel_submission", {})
    if not isinstance(originality, dict):
        findings.append("author_inputs.originality_and_parallel_submission")
    else:
        for key in [
            "original_work_confirmed",
            "not_under_parallel_archival_peer_review",
        ]:
            if originality.get(key) is not False:
                findings.append(f"author_inputs.originality_and_parallel_submission.{key}")
    license_payload = author_inputs.get("cc_by_4_0", {})
    if (
        not isinstance(license_payload, dict)
        or license_payload.get("all_authors_confirm_tmlr_submission_license") is not False
    ):
        findings.append("author_inputs.cc_by_4_0.all_authors_confirm_tmlr_submission_license")
    llm_payload = author_inputs.get("llm_use_policy", {})
    if not isinstance(llm_payload, dict):
        findings.append("author_inputs.llm_use_policy")
    else:
        for key in ["authors_take_full_responsibility", "no_llm_listed_as_author"]:
            if llm_payload.get(key) is not False:
                findings.append(f"author_inputs.llm_use_policy.{key}")
    author_receipt = author_inputs.get("submission_receipt", {})
    if not isinstance(author_receipt, dict):
        findings.append("author_inputs.submission_receipt")
    else:
        for key in [
            "tmlr_openreview_forum_url",
            "tmlr_submission_id",
            "submitted_at",
            "confirmation_email_or_receipt_path",
        ]:
            if str(author_receipt.get(key, "")):
                findings.append(f"author_inputs.submission_receipt.{key}")

    if active_monitor.get("goal_complete") is not False:
        findings.append("active_monitor.goal_complete")
    if active_monitor.get("active_blocker_monitor_ready") is not False:
        findings.append("active_monitor.active_blocker_monitor_ready")
    if not exact_blockers(active_monitor.get("blockers", [])):
        findings.append("active_monitor.blockers")
    if active_monitor.get("missing_expected_blockers"):
        findings.append("active_monitor.missing_expected_blockers")
    if active_monitor.get("unexpected_blockers"):
        findings.append("active_monitor.unexpected_blockers")
    active_monitor_next_actions = active_monitor.get("next_actions", [])
    if not isinstance(active_monitor_next_actions, list):
        active_monitor_next_actions = []
        findings.append("active_monitor.next_actions")
    active_monitor_labels = [
        str(item.get("label", ""))
        for item in active_monitor_next_actions
        if isinstance(item, dict)
    ]
    active_monitor_gates = [
        str(item.get("gate", ""))
        for item in active_monitor_next_actions
        if isinstance(item, dict)
    ]
    if active_monitor_labels != EXPECTED_ACTIVE_MONITOR_NEXT_ACTION_LABELS:
        findings.append("active_monitor.next_action_labels")
    if active_monitor_gates != EXPECTED_ACTIVE_MONITOR_NEXT_ACTION_GATES:
        findings.append("active_monitor.next_action_gates")
    for item in active_monitor_next_actions:
        if not isinstance(item, dict):
            findings.append("active_monitor.next_action_not_object")
            continue
        for key in [
            "gate",
            "blocker",
            "label",
            "recipient",
            "required_input",
            "preflight_command",
            "apply_command",
            "success_evidence",
        ]:
            if not str(item.get(key, "")).strip():
                findings.append(f"active_monitor.next_action.{item.get('label', 'unknown')}.{key}")
    cuda_actions = [
        item
        for item in active_monitor_next_actions
        if isinstance(item, dict) and item.get("label") == "obtain_external_cuda_receipt"
    ]
    if len(cuda_actions) != 1:
        findings.append("active_monitor.obtain_external_cuda_receipt")
    else:
        cuda_action = cuda_actions[0]
        if "verify_external_cuda_handoff_bundle.py --check-urls --strict" not in str(
            cuda_action.get("preflight_command", "")
        ):
            findings.append("active_monitor.obtain_external_cuda_receipt.preflight_handoff")
        if "verify_tmlr_external_cuda_receipt_template.py --strict" not in str(
            cuda_action.get("preflight_command", "")
        ):
            findings.append("active_monitor.obtain_external_cuda_receipt.preflight_template")
        if "poll_external_cuda_issue_receipt.py --write --check-urls --require-found" not in str(
            cuda_action.get("apply_command", "")
        ):
            findings.append("active_monitor.obtain_external_cuda_receipt.apply_command")
        if cuda_action.get("handoff_document") != "runs/tmlr_external_cuda_validator_request_2026-05-08.md":
            findings.append("active_monitor.obtain_external_cuda_receipt.handoff_document")
    active_monitor_human = active_monitor.get("human_reply", {})
    if not isinstance(active_monitor_human, dict):
        findings.append("active_monitor.human_reply")
    else:
        if active_monitor_human.get("present") is not False:
            findings.append("active_monitor.human_reply.present")
        if active_monitor_human.get("workflow_ready") is not False:
            findings.append("active_monitor.human_reply.workflow_ready")
        if "human_unblock_reply_json_missing" not in [
            str(item) for item in active_monitor_human.get("workflow_blockers", [])
        ]:
            findings.append("active_monitor.human_reply.workflow_blockers")
    active_monitor_receipt = active_monitor.get("submission_receipt", {})
    if not isinstance(active_monitor_receipt, dict):
        findings.append("active_monitor.submission_receipt")
    else:
        if active_monitor_receipt.get("present") is not False:
            findings.append("active_monitor.submission_receipt.present")
        if active_monitor_receipt.get("workflow_ready") is not False:
            findings.append("active_monitor.submission_receipt.workflow_ready")
        receipt_blockers = [
            str(item) for item in active_monitor_receipt.get("workflow_blockers", [])
        ]
        for blocker in [
            "submission_receipt_json_missing",
            "tmlr_openreview_submission_receipt_missing",
        ]:
            if blocker not in receipt_blockers:
                findings.append(f"active_monitor.submission_receipt.workflow_blockers:{blocker}")
    active_monitor_cuda = active_monitor.get("external_cuda", {})
    if not isinstance(active_monitor_cuda, dict):
        findings.append("active_monitor.external_cuda")
    else:
        if active_monitor_cuda.get("receipt_observed") is not False:
            findings.append("active_monitor.external_cuda.receipt_observed")
        if active_monitor_cuda.get("handoff_bundle_verified") is not True:
            findings.append("active_monitor.external_cuda.handoff_bundle_verified")
        if not active_monitor_cuda.get("handoff_bundle_sha256"):
            findings.append("active_monitor.external_cuda.handoff_bundle_sha256")
        if active_monitor_cuda.get("receipt_template_present") is not True:
            findings.append("active_monitor.external_cuda.receipt_template_present")
        if active_monitor_cuda.get("receipt_template_verified") is not True:
            findings.append("active_monitor.external_cuda.receipt_template_verified")
        if active_monitor_cuda.get("receipt_template_placeholder_safe") is not True:
            findings.append("active_monitor.external_cuda.receipt_template_placeholder_safe")
        if active_monitor_cuda.get("receipt_template_apply_ready") is not False:
            findings.append("active_monitor.external_cuda.receipt_template_apply_ready")
        if active_monitor_cuda.get("issue_poll_ready") is not False:
            findings.append("active_monitor.external_cuda.issue_poll_ready")
        if active_monitor_cuda.get("issue_poll_check_urls") is not True:
            findings.append("active_monitor.external_cuda.issue_poll_check_urls")
        if active_monitor_cuda.get("issue_poll_check_urls") != issue_poll.get("check_urls"):
            findings.append("active_monitor.external_cuda.issue_poll_check_urls_mismatch")
        if active_monitor_cuda.get("issue_state") != issue_poll.get("issue_state"):
            findings.append("active_monitor.external_cuda.issue_state")
        if active_monitor_cuda.get("issue_state") != EXPECTED_EXTERNAL_CUDA_ISSUE_STATE:
            findings.append("active_monitor.external_cuda.issue_state_expected")
        if active_monitor_cuda.get("issue_url") != issue_poll.get("issue_url"):
            findings.append("active_monitor.external_cuda.issue_url")
        if active_monitor_cuda.get("issue_updated_at") != issue_poll.get("issue_updated_at"):
            findings.append("active_monitor.external_cuda.issue_updated_at")
        if not active_monitor_cuda.get("issue_updated_at"):
            findings.append("active_monitor.external_cuda.issue_updated_at_missing")
        if active_monitor_cuda.get("issue_poll_gh_error") != issue_poll.get("gh_error", ""):
            findings.append("active_monitor.external_cuda.issue_poll_gh_error_mismatch")
        if active_monitor_cuda.get("issue_poll_gh_error"):
            findings.append("active_monitor.external_cuda.issue_poll_gh_error")
        if active_monitor_cuda.get("comment_count") != issue_poll.get("comment_count"):
            findings.append("active_monitor.external_cuda.comment_count")
        if active_monitor_cuda.get("candidate_count") != issue_poll.get("candidate_count"):
            findings.append("active_monitor.external_cuda.candidate_count")
        if active_monitor_cuda.get("valid_candidate_count") != 0:
            findings.append("active_monitor.external_cuda.valid_candidate_count")
        if active_monitor_cuda.get("valid_candidate_count") != issue_poll.get(
            "valid_candidate_count"
        ):
            findings.append("active_monitor.external_cuda.valid_candidate_count_mismatch")
        if active_monitor_cuda.get("linked_receipt_count") != issue_poll.get(
            "linked_receipt_count"
        ):
            findings.append("active_monitor.external_cuda.linked_receipt_count")
        if active_monitor_cuda.get("linked_receipt_fetch_error_count") != 0:
            findings.append("active_monitor.external_cuda.linked_receipt_fetch_error_count")
        if active_monitor_cuda.get("linked_receipt_fetch_error_count") != issue_poll.get(
            "linked_receipt_fetch_error_count"
        ):
            findings.append(
                "active_monitor.external_cuda.linked_receipt_fetch_error_count_mismatch"
            )
        if active_monitor_cuda.get("operator_note_comment_count") != issue_poll.get(
            "operator_note_comment_count"
        ):
            findings.append("active_monitor.external_cuda.operator_note_comment_count")
        if active_monitor_cuda.get("operator_note_comment_urls") != issue_poll.get(
            "operator_note_comment_urls", []
        ):
            findings.append("active_monitor.external_cuda.operator_note_comment_urls")
        if int(active_monitor_cuda.get("operator_note_comment_count") or 0) < 1:
            findings.append("active_monitor.external_cuda.operator_note_comment_count_missing")
        if active_monitor_cuda.get("operator_note_without_receipt") is not True:
            findings.append("active_monitor.external_cuda.operator_note_without_receipt")
        if active_monitor_cuda.get("operator_note_without_receipt") != issue_poll.get(
            "operator_note_without_receipt"
        ):
            findings.append("active_monitor.external_cuda.operator_note_without_receipt_mismatch")

    closure_stages = (
        closure_workflow.get("closure_stages", {})
        if isinstance(closure_workflow.get("closure_stages"), dict)
        else {}
    )
    closure_commands = (
        closure_workflow.get("commands", {})
        if isinstance(closure_workflow.get("commands"), dict)
        else {}
    )
    if closure_workflow.get("stage_order") != EXPECTED_CLOSURE_STAGE_ORDER:
        findings.append("closure_workflow.stage_order")
    for index, stage_name in enumerate(EXPECTED_CLOSURE_STAGE_ORDER, start=1):
        stage = closure_stages.get(stage_name, {})
        if not isinstance(stage, dict):
            findings.append(f"closure_workflow.stage_missing:{stage_name}")
            continue
        if stage.get("order") != index:
            findings.append(f"closure_workflow.stage_order_value:{stage_name}")
        if stage.get("ready") is not False:
            findings.append(f"closure_workflow.stage_ready:{stage_name}")
    if "human_unblock_reply_json_missing" not in [
        str(item)
        for item in closure_stages.get("ready_to_submit", {}).get("blockers", [])
    ]:
        findings.append("closure_workflow.ready_to_submit.local_missing_blocker")
    if "submission_receipt_json_missing" not in [
        str(item) for item in closure_stages.get("post_submit", {}).get("blockers", [])
    ]:
        findings.append("closure_workflow.post_submit.local_missing_blocker")
    if "external_cuda_issue_receipt_candidate_missing" not in [
        str(item) for item in closure_stages.get("strict_artifact", {}).get("blockers", [])
    ]:
        findings.append("closure_workflow.strict_artifact.local_missing_blocker")
    for command_name in ["snapshot_preflight", "final_gate"]:
        command_result_payload = closure_commands.get(command_name, {})
        if not isinstance(command_result_payload, dict):
            findings.append(f"closure_workflow.command_missing:{command_name}")
        elif command_result_payload.get("exit_code") != 0:
            findings.append(f"closure_workflow.command_exit:{command_name}")
    if closure_verification.get("tmlr_active_blocker_closure_workflow_verified") is not True:
        findings.append("closure_workflow_verification.verified")
    if closure_verification.get("case_count") != 4:
        findings.append("closure_workflow_verification.case_count")
    for case in closure_verification.get("cases", []):
        if not isinstance(case, dict):
            findings.append("closure_workflow_verification.case_not_object")
            continue
        if (
            case.get("stage_order_ok") is not True
            or case.get("stage_headings_ok") is not True
            or case.get("stage_details_ok") is not True
        ):
            findings.append(f"closure_workflow_verification.stage_case:{case.get('name')}")

    if nonempty_locks:
        findings.append("nonempty_lock_files_present")
    if public_git_status["exit_code"] != 0 or public_git_status["stdout_tail"]:
        findings.append("public_repository_snapshot_dirty")

    return {
        "current_goal_completion_audit_verified": not findings,
        "findings": findings,
        "audit": rel(AUDIT_MD),
        "checklist": rel(CHECKLIST_MD),
        "snapshot": rel(SNAPSHOT_DIR),
        "snapshot_integrity": {
            "snapshot_ready": snapshot_integrity.get("snapshot_ready"),
            "blockers": snapshot_integrity.get("blockers", []),
            "upload_all_match": upload_comparison.get("all_match")
            if isinstance(upload_comparison, dict)
            else None,
            "record_all_match": record_comparison.get("all_match")
            if isinstance(record_comparison, dict)
            else None,
            "record_expected_count": record_comparison.get("expected_count")
            if isinstance(record_comparison, dict)
            else None,
            "record_actual_count": record_comparison.get("actual_count")
            if isinstance(record_comparison, dict)
            else None,
            "record_mismatches": record_comparison.get("mismatches", [])
            if isinstance(record_comparison, dict)
            else [],
        },
        "expected_blockers": EXPECTED_BLOCKERS,
        "final_gate": {
            "local_file_packet_ready": final_gate.get("local_file_packet_ready"),
            "ready_to_submit": final_gate.get("ready_to_submit"),
            "submission_complete": final_gate.get("submission_complete"),
            "strict_artifact_ready": final_gate.get("strict_artifact_ready"),
            "goal_complete": final_gate.get("goal_complete"),
            "blockers": final_gate.get("blockers", []),
        },
        "final_gate_contract": {
            "verified": final_gate_contract.get("tmlr_final_gate_contract_verified"),
            "findings": final_gate_contract.get("findings", []),
        },
        "sync": {
            "synced": sync.get("synced"),
            "manifest_sha256": sync.get("manifest_sha256"),
            "copied_upload_count": sync.get("copied_upload_count"),
            "copied_record_count_final": sync.get("copied_record_count_final"),
            "failed_commands": sync.get("failed_commands", []),
            "blocking_failed_commands": sync.get("blocking_failed_commands", []),
            "transient_failed_commands": sync.get("transient_failed_commands", []),
            "goal_complete": sync.get("goal_complete"),
            "blockers": sync.get("blockers", []),
        },
        "submission_packet": {
            "file_packet_ready": submission_packet.get("file_packet_ready"),
            "ready_to_submit": submission_packet.get("ready_to_submit"),
            "submission_recorded": submission_packet.get("submission_recorded"),
            "submission_complete": submission_packet.get("submission_complete"),
            "ready_to_submit_blockers": submission_packet.get(
                "ready_to_submit_blockers", []
            ),
            "external_blockers": submission_packet.get("external_blockers", []),
            "submission_record_blockers": submission_packet.get(
                "submission_record_blockers", []
            ),
            "residual_limitations": submission_packet.get("residual_limitations", []),
            "risk_flags": submission_packet.get("risk_flags", []),
            "author_inputs": {
                "authors_ready": packet_author_inputs.get("authors_ready"),
                "funding_irb_ready": packet_author_inputs.get("funding_irb_ready"),
                "submission_receipt_ready": packet_author_inputs.get(
                    "submission_receipt_ready"
                ),
                "submission_receipt_findings": packet_author_inputs.get(
                    "submission_receipt_findings", []
                ),
                "action_editor_conflict_screen_finding_count": len(
                    packet_author_inputs.get(
                        "action_editor_conflict_screen_findings", []
                    )
                )
                if isinstance(
                    packet_author_inputs.get(
                        "action_editor_conflict_screen_findings", []
                    ),
                    list,
                )
                else None,
            },
            "upload_targets_ready": packet_upload_targets.get("ready")
            if isinstance(packet_upload_targets, dict)
            else None,
            "upload_target_names": packet_upload_targets.get(
                "expected_upload_target_file_names", []
            )
            if isinstance(packet_upload_targets, dict)
            else [],
            "external_cuda_wording": {
                "ready": packet_external_cuda_wording.get("ready")
                if isinstance(packet_external_cuda_wording, dict)
                else None,
                "pdf_required_snippet_count": packet_external_cuda_wording.get(
                    "pdf_required_snippet_count"
                )
                if isinstance(packet_external_cuda_wording, dict)
                else None,
                "paste_required_snippet_count": packet_external_cuda_wording.get(
                    "paste_required_snippet_count"
                )
                if isinstance(packet_external_cuda_wording, dict)
                else None,
                "overclaim_count": len(
                    packet_external_cuda_wording.get("overclaim_findings", [])
                )
                if isinstance(packet_external_cuda_wording, dict)
                and isinstance(packet_external_cuda_wording.get("overclaim_findings", []), list)
                else None,
            },
        },
        "openreview_paste_payload": {
            "path": rel(OPENREVIEW_PASTE_PAYLOAD_JSON),
            "markdown": rel(OPENREVIEW_PASTE_PAYLOAD_MD),
            "source_form_packet": openreview_paste_payload.get("source_form_packet"),
            "ready_fields_pass": openreview_paste_payload.get("ready_fields_pass"),
            "ready_field_keys": list(paste_ready_fields)
            if isinstance(paste_ready_fields, dict)
            else [],
            "missing_ready_fields": openreview_paste_payload.get(
                "missing_ready_fields", []
            ),
            "ready_field_findings": openreview_paste_payload.get(
                "ready_field_findings", []
            ),
            "ready_field_guardrail_findings": openreview_paste_payload.get(
                "ready_field_guardrail_findings", []
            ),
            "metric_guardrail_findings": metric_guardrail_findings,
            "action_editor_paste_ready": paste_action_editors.get("paste_ready")
            if isinstance(paste_action_editors, dict)
            else None,
            "candidates_withheld_until_conflict_screen": paste_action_editors.get(
                "candidates_withheld_until_conflict_screen"
            )
            if isinstance(paste_action_editors, dict)
            else None,
            "withheld_candidate_count": paste_action_editors.get(
                "withheld_candidate_count"
            )
            if isinstance(paste_action_editors, dict)
            else None,
            "primary_candidate_count": len(paste_action_editors.get("primary_candidates", []))
            if isinstance(paste_action_editors, dict)
            and isinstance(paste_action_editors.get("primary_candidates", []), list)
            else None,
            "alternate_candidate_count": len(
                paste_action_editors.get("alternate_candidates", [])
            )
            if isinstance(paste_action_editors, dict)
            and isinstance(paste_action_editors.get("alternate_candidates", []), list)
            else None,
            "conflict_screen_finding_count": len(paste_conflict_findings)
            if isinstance(paste_conflict_findings, list)
            else None,
            "candidate_name_count": len(paste_candidate_names),
            "candidate_name_leak_count_in_markdown": len(paste_candidate_name_leaks),
            "author_side_fields_required": paste_author_side_fields
            if isinstance(paste_author_side_fields, list)
            else [],
        },
        "operator_handoff": {
            "verified": operator_verification.get(
                "tmlr_operator_handoff_bundle_verified"
            ),
            "bundle_zip_sha256": operator_verification.get("bundle_zip_sha256", ""),
            "required_target_count": operator_verification.get(
                "required_target_count"
            ),
            "required_readme_snippet_count": operator_verification.get(
                "required_readme_snippet_count"
            ),
            "external_cuda_handoff": operator_bundle.get("external_cuda_handoff", {}),
        },
        "external_cuda_handoff": {
            "verified": external_cuda.get("external_cuda_handoff_bundle_verified"),
            "bundle_sha256": external_cuda.get("bundle_sha256", ""),
            "github_api_fetcher_case_count": len(external_cases),
            "github_api_fetcher_findings": external_cuda.get(
                "github_api_fetcher_findings", []
            ),
            "public_url_findings": external_cuda.get("public_url_findings", []),
            "operator_note_fetch_findings": external_cuda.get(
                "public_url_details", {}
            ).get("operator_note_fetch_findings", []),
        },
        "active_handoff": {
            "verified": active_handoff_verification.get(
                "tmlr_active_blocker_handoff_verified"
            ),
            "required_markdown_snippet_count": active_handoff_verification.get(
                "required_markdown_snippet_count"
            ),
            "blockers": active_handoff_verification.get("blockers", []),
        },
        "active_monitor": {
            "ready": active_monitor.get("active_blocker_monitor_ready"),
            "goal_complete": active_monitor.get("goal_complete"),
            "blockers": active_monitor.get("blockers", []),
            "human_reply_present": active_monitor.get("human_reply", {}).get("present")
            if isinstance(active_monitor.get("human_reply", {}), dict)
            else None,
            "submission_receipt_present": active_monitor.get(
                "submission_receipt", {}
            ).get("present")
            if isinstance(active_monitor.get("submission_receipt", {}), dict)
            else None,
            "external_cuda_valid_candidate_count": active_monitor.get(
                "external_cuda", {}
            ).get("valid_candidate_count")
            if isinstance(active_monitor.get("external_cuda", {}), dict)
            else None,
            "external_cuda_issue_poll_check_urls": active_monitor.get(
                "external_cuda", {}
            ).get("issue_poll_check_urls")
            if isinstance(active_monitor.get("external_cuda", {}), dict)
            else None,
            "external_cuda_issue_state": active_monitor.get(
                "external_cuda", {}
            ).get("issue_state")
            if isinstance(active_monitor.get("external_cuda", {}), dict)
            else None,
            "external_cuda_issue_updated_at": active_monitor.get(
                "external_cuda", {}
            ).get("issue_updated_at")
            if isinstance(active_monitor.get("external_cuda", {}), dict)
            else None,
            "external_cuda_issue_poll_gh_error": active_monitor.get(
                "external_cuda", {}
            ).get("issue_poll_gh_error")
            if isinstance(active_monitor.get("external_cuda", {}), dict)
            else None,
            "external_cuda_operator_note_comment_count": active_monitor.get(
                "external_cuda", {}
            ).get("operator_note_comment_count")
            if isinstance(active_monitor.get("external_cuda", {}), dict)
            else None,
            "external_cuda_operator_note_comment_urls": active_monitor.get(
                "external_cuda", {}
            ).get("operator_note_comment_urls", [])
            if isinstance(active_monitor.get("external_cuda", {}), dict)
            else [],
            "external_cuda_operator_note_without_receipt": active_monitor.get(
                "external_cuda", {}
            ).get("operator_note_without_receipt")
            if isinstance(active_monitor.get("external_cuda", {}), dict)
            else None,
            "next_action_labels": active_monitor_labels,
            "next_action_gates": active_monitor_gates,
        },
        "external_blocker_inputs": {
            "human_reply_file_present": HUMAN_REPLY_JSON.is_file(),
            "submission_receipt_file_present": SUBMISSION_RECEIPT_JSON.is_file(),
            "issue_poll_ready": issue_poll.get("external_cuda_issue_receipt_poll_ready"),
            "issue_poll_check_urls": issue_poll.get("check_urls"),
            "issue_state": issue_poll.get("issue_state"),
            "issue_updated_at": issue_poll.get("issue_updated_at"),
            "comment_count": issue_poll.get("comment_count"),
            "candidate_count": issue_poll.get("candidate_count"),
            "valid_candidate_count": issue_poll.get("valid_candidate_count"),
            "linked_receipt_count": issue_poll.get("linked_receipt_count"),
            "linked_receipt_fetch_error_count": issue_poll.get(
                "linked_receipt_fetch_error_count"
            ),
            "operator_note_comment_count": issue_poll.get("operator_note_comment_count"),
            "operator_note_comment_urls": operator_note_urls,
            "operator_note_without_receipt": issue_poll.get(
                "operator_note_without_receipt"
            ),
            "gh_error": issue_poll.get("gh_error", ""),
        },
        "author_inputs_status": {
            "path": rel(AUTHOR_INPUTS_JSON),
            "status_report": rel(AUTHOR_INPUTS_STATUS_MD),
            "payload_status": author_inputs.get("status"),
            "author_count": len(authors) if isinstance(authors, list) else None,
            "action_editor_screen_count": len(action_editor_screen)
            if isinstance(action_editor_screen, list)
            else None,
            "author_name_present": bool(str(first_author.get("name", ""))),
            "author_openreview_present": bool(
                str(first_author.get("openreview_profile_url", ""))
            ),
            "author_conflicts_complete": first_author.get("conflicts_complete"),
            "funding_statement_present": bool(
                str(author_inputs.get("funding_statement", ""))
            ),
            "competing_interests_statement_present": bool(
                str(author_inputs.get("competing_interests_statement", ""))
            ),
            "human_subjects_confirmed_by_all_authors": human_subjects.get(
                "confirmed_by_all_authors"
            )
            if isinstance(human_subjects, dict)
            else None,
            "llm_authors_take_full_responsibility": llm_payload.get(
                "authors_take_full_responsibility"
            )
            if isinstance(llm_payload, dict)
            else None,
            "submission_receipt_forum_url_present": bool(
                str(author_receipt.get("tmlr_openreview_forum_url", ""))
            )
            if isinstance(author_receipt, dict)
            else None,
        },
        "closure_workflow": {
            "stage_order": closure_workflow.get("stage_order"),
            "stage_count": len(closure_stages),
            "snapshot_preflight_exit_code": closure_commands.get(
                "snapshot_preflight", {}
            ).get("exit_code")
            if isinstance(closure_commands.get("snapshot_preflight", {}), dict)
            else None,
            "final_gate_exit_code": closure_commands.get("final_gate", {}).get(
                "exit_code"
            )
            if isinstance(closure_commands.get("final_gate", {}), dict)
            else None,
            "verification": closure_verification.get(
                "tmlr_active_blocker_closure_workflow_verified"
            ),
            "verification_case_count": closure_verification.get("case_count"),
        },
        "missing_audit_snippets": missing_audit_snippets,
        "missing_checklist_snippets": missing_checklist_snippets,
        "stale_hits": stale_hits,
        "snapshot_record_parity": {
            "audit": copied_snapshot_record_matches(AUDIT_MD, AUDIT_MD.name),
            "checklist": copied_snapshot_record_matches(CHECKLIST_MD, CHECKLIST_MD.name),
        },
        "nonempty_lock_files": nonempty_locks,
        "public_repository_snapshot_status": public_git_status,
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Current Goal Completion Audit Verification",
        "",
        f"Verified: {payload['current_goal_completion_audit_verified']}.",
        f"Audit: `{payload['audit']}`.",
        f"Checklist: `{payload['checklist']}`.",
        f"Snapshot: `{payload['snapshot']}`.",
        f"Snapshot integrity ready: {payload['snapshot_integrity']['snapshot_ready']}.",
        f"Snapshot manifest SHA256: `{payload['sync']['manifest_sha256']}`.",
        f"Operator bundle zip SHA256: `{payload['operator_handoff']['bundle_zip_sha256']}`.",
        f"External CUDA handoff SHA256: `{payload['external_cuda_handoff']['bundle_sha256']}`.",
        "",
        "## Findings",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["findings"] or ["none"])
    lines.extend(
        [
            "",
            "## Gate State",
            "",
            f"- Local file packet ready: {payload['final_gate']['local_file_packet_ready']}",
            f"- Ready to submit: {payload['final_gate']['ready_to_submit']}",
            f"- Submission complete: {payload['final_gate']['submission_complete']}",
            f"- Strict artifact ready: {payload['final_gate']['strict_artifact_ready']}",
            f"- Goal complete: {payload['final_gate']['goal_complete']}",
            "",
            "## Submission Packet",
            "",
            f"- File packet ready: {payload['submission_packet']['file_packet_ready']}",
            f"- Ready to submit: {payload['submission_packet']['ready_to_submit']}",
            f"- Submission recorded: {payload['submission_packet']['submission_recorded']}",
            f"- Ready-to-submit blockers: {', '.join(payload['submission_packet']['ready_to_submit_blockers'])}",
            f"- External blockers: {', '.join(payload['submission_packet']['external_blockers'])}",
            f"- Residual limitations: {', '.join(payload['submission_packet']['residual_limitations'])}",
            f"- Receipt findings: {len(payload['submission_packet']['author_inputs']['submission_receipt_findings'])}",
            f"- Action-editor conflict findings: {payload['submission_packet']['author_inputs']['action_editor_conflict_screen_finding_count']}",
            f"- Upload targets ready: {payload['submission_packet']['upload_targets_ready']}",
            f"- Upload targets: {', '.join(payload['submission_packet']['upload_target_names'])}",
            f"- External CUDA wording ready: {payload['submission_packet']['external_cuda_wording']['ready']}",
            f"- External CUDA overclaim count: {payload['submission_packet']['external_cuda_wording']['overclaim_count']}",
            "",
            "## OpenReview Paste Payload",
            "",
            f"- Ready fields pass: {payload['openreview_paste_payload']['ready_fields_pass']}",
            f"- Ready field keys: {', '.join(payload['openreview_paste_payload']['ready_field_keys'])}",
            f"- Missing ready fields: {len(payload['openreview_paste_payload']['missing_ready_fields'])}",
            f"- Ready-field findings: {len(payload['openreview_paste_payload']['ready_field_findings'])}",
            f"- Ready-field guardrail findings: {len(payload['openreview_paste_payload']['ready_field_guardrail_findings'])}",
            f"- Metric guardrail findings: {len(payload['openreview_paste_payload']['metric_guardrail_findings'])}",
            f"- Action-editor paste ready: {payload['openreview_paste_payload']['action_editor_paste_ready']}",
            f"- Candidates withheld: {payload['openreview_paste_payload']['candidates_withheld_until_conflict_screen']}",
            f"- Withheld candidate count: {payload['openreview_paste_payload']['withheld_candidate_count']}",
            f"- Conflict-screen finding count: {payload['openreview_paste_payload']['conflict_screen_finding_count']}",
            f"- Candidate name leaks in Markdown: {payload['openreview_paste_payload']['candidate_name_leak_count_in_markdown']}",
            f"- Author-side-only field count: {len(payload['openreview_paste_payload']['author_side_fields_required'])}",
            "",
            "## Snapshot Integrity",
            "",
            f"- Snapshot ready: {payload['snapshot_integrity']['snapshot_ready']}",
            f"- Upload all match: {payload['snapshot_integrity']['upload_all_match']}",
            f"- Record all match: {payload['snapshot_integrity']['record_all_match']}",
            f"- Record count: {payload['snapshot_integrity']['record_actual_count']} / {payload['snapshot_integrity']['record_expected_count']}",
            f"- Record mismatches: {len(payload['snapshot_integrity']['record_mismatches'])}",
            "",
            "## Expected Active Blockers",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in payload["expected_blockers"])
    lines.extend(
        [
            "",
            "## External CUDA Handoff",
            "",
            f"- Verified: {payload['external_cuda_handoff']['verified']}",
            f"- GitHub API fetcher cases: {payload['external_cuda_handoff']['github_api_fetcher_case_count']}",
            f"- GitHub API fetcher findings: {len(payload['external_cuda_handoff']['github_api_fetcher_findings'])}",
            f"- Public URL findings: {len(payload['external_cuda_handoff']['public_url_findings'])}",
            f"- Operator-note fetch findings: {len(payload['external_cuda_handoff']['operator_note_fetch_findings'])}",
            "",
            "## Active Handoff",
            "",
            f"- Verified: {payload['active_handoff']['verified']}",
            f"- Required Markdown snippets: {payload['active_handoff']['required_markdown_snippet_count']}",
            f"- Verification blockers: {len(payload['active_handoff']['blockers'])}",
            "",
            "## Active Monitor",
            "",
            f"- Ready: {payload['active_monitor']['ready']}",
            f"- Goal complete: {payload['active_monitor']['goal_complete']}",
            f"- Human reply present: {payload['active_monitor']['human_reply_present']}",
            f"- Submission receipt present: {payload['active_monitor']['submission_receipt_present']}",
            f"- External CUDA valid candidates: {payload['active_monitor']['external_cuda_valid_candidate_count']}",
            f"- External CUDA issue poll check URLs: {payload['active_monitor']['external_cuda_issue_poll_check_urls']}",
            f"- External CUDA issue state: {payload['active_monitor']['external_cuda_issue_state']}",
            f"- External CUDA issue updated at: {payload['active_monitor']['external_cuda_issue_updated_at']}",
            f"- External CUDA issue poll GitHub error: `{payload['active_monitor']['external_cuda_issue_poll_gh_error']}`",
            f"- External CUDA operator-note comments: {payload['active_monitor']['external_cuda_operator_note_comment_count']}",
            f"- External CUDA operator note without receipt: {payload['active_monitor']['external_cuda_operator_note_without_receipt']}",
            f"- Next action labels: {', '.join(payload['active_monitor']['next_action_labels'])}",
            f"- Next action gates: {', '.join(payload['active_monitor']['next_action_gates'])}",
            "",
            "## External Blocker Inputs",
            "",
            f"- Human reply file present: {payload['external_blocker_inputs']['human_reply_file_present']}",
            f"- Submission receipt file present: {payload['external_blocker_inputs']['submission_receipt_file_present']}",
            f"- External CUDA issue poll ready: {payload['external_blocker_inputs']['issue_poll_ready']}",
            f"- External CUDA issue poll check URLs: {payload['external_blocker_inputs']['issue_poll_check_urls']}",
            f"- External CUDA issue state: {payload['external_blocker_inputs']['issue_state']}",
            f"- External CUDA issue updated at: {payload['external_blocker_inputs']['issue_updated_at']}",
            f"- External CUDA valid candidates: {payload['external_blocker_inputs']['valid_candidate_count']}",
            f"- External CUDA linked receipt fetch errors: {payload['external_blocker_inputs']['linked_receipt_fetch_error_count']}",
            f"- External CUDA operator-note comments: {payload['external_blocker_inputs']['operator_note_comment_count']}",
            f"- External CUDA operator note without receipt: {payload['external_blocker_inputs']['operator_note_without_receipt']}",
            "",
            "## Author Inputs Status",
            "",
            f"- Payload status: {payload['author_inputs_status']['payload_status']}",
            f"- Author count: {payload['author_inputs_status']['author_count']}",
            f"- Action-editor screen count: {payload['author_inputs_status']['action_editor_screen_count']}",
            f"- Author name present: {payload['author_inputs_status']['author_name_present']}",
            f"- Author OpenReview present: {payload['author_inputs_status']['author_openreview_present']}",
            f"- Author conflicts complete: {payload['author_inputs_status']['author_conflicts_complete']}",
            f"- Funding statement present: {payload['author_inputs_status']['funding_statement_present']}",
            f"- Competing interests statement present: {payload['author_inputs_status']['competing_interests_statement_present']}",
            f"- Human-subjects confirmed by all authors: {payload['author_inputs_status']['human_subjects_confirmed_by_all_authors']}",
            f"- LLM responsibility confirmed: {payload['author_inputs_status']['llm_authors_take_full_responsibility']}",
            f"- Submission receipt forum URL present: {payload['author_inputs_status']['submission_receipt_forum_url_present']}",
            "",
            "This file is generated by `scripts/verify_current_goal_completion_audit.py`.",
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
                "current_goal_completion_audit_verified": payload[
                    "current_goal_completion_audit_verified"
                ],
                "findings": payload["findings"],
                "out_json": rel(args.out_json),
                "out_md": rel(args.out_md),
            }
        )
    )
    if args.strict and not payload["current_goal_completion_audit_verified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
