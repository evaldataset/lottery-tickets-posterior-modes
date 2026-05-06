#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE_JSON = ROOT / "runs" / "remaining_experiment_queue.json"
DEFAULT_OUT_JSON = ROOT / "runs" / "remaining_experiment_preflight_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "remaining_experiment_preflight_audit.md"

EXPECTED_NAMES = [
    "locked_final_test_sgld_full_cifar",
    "bn_freeze_sgld_full_cifar",
    "bn_recalibrate_sgld_full_cifar",
    "bn_dense_buffers_sgld_full_cifar",
    "bn_freeze_csgld_full_cifar",
    "bn_recalibrate_csgld_full_cifar",
    "bn_dense_buffers_csgld_full_cifar",
    "saved_artifacts_csgld_multichain",
    "saved_artifacts_lowrank128",
    "saved_artifacts_jointdiag",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-json", type=Path, default=DEFAULT_QUEUE_JSON)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument(
        "--live-gpu-probe",
        action="store_true",
        help="Record sanitized nvidia-smi occupancy without starting training.",
    )
    return parser.parse_args()


def relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def split_env_command(command: str) -> tuple[dict[str, str], list[str]]:
    tokens = shlex.split(command)
    env: dict[str, str] = {}
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        key, value = tokens.pop(0).split("=", 1)
        env[key] = value
    return env, tokens


def script_path(argv: list[str]) -> str | None:
    if len(argv) >= 2 and argv[1].endswith(".py"):
        return argv[1]
    return None


def receipt_paths(name: str) -> tuple[str, str]:
    return (
        f"runs/validation_bn_plan_entry_{name}_receipt.json",
        f"docs/validation_bn_plan_entry_{name}_receipt.md",
    )


def load_receipt_summary(path: str) -> dict[str, Any] | None:
    full = ROOT / path
    if not full.exists():
        return None
    payload = load_json(full)
    if not isinstance(payload, dict):
        return None
    return {
        "path": path,
        "entry": payload.get("entry"),
        "status": payload.get("status"),
        "preflight_only": payload.get("preflight_only"),
        "ready": payload.get("validation_bn_plan_entry_receipt_ready"),
        "risk_flags": payload.get("risk_flags", []),
        "warning_flags": payload.get("warning_flags", []),
    }


def split_csv_line(line: str) -> list[str]:
    return [part.strip() for part in line.split(",")]


def query_gpu_inventory() -> tuple[dict[str, str], list[dict[str, str]], str | None]:
    if shutil.which("nvidia-smi") is None:
        return {}, [], "nvidia_smi_not_found"
    gpu_query = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader,nounits"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if gpu_query.returncode != 0:
        return {}, [], "nvidia_smi_gpu_query_failed"
    index_to_uuid: dict[str, str] = {}
    for line in gpu_query.stdout.splitlines():
        if not line.strip():
            continue
        parts = split_csv_line(line)
        if len(parts) >= 2:
            index_to_uuid[parts[0]] = parts[1]
    apps_query = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if apps_query.returncode != 0:
        return index_to_uuid, [], "nvidia_smi_compute_apps_query_failed"
    processes: list[dict[str, str]] = []
    for line in apps_query.stdout.splitlines():
        if not line.strip():
            continue
        parts = split_csv_line(line)
        if len(parts) >= 4:
            processes.append(
                {
                    "gpu_uuid": parts[0],
                    "pid": parts[1],
                    "process_name": parts[2],
                    "used_memory_mb": parts[3],
                }
            )
    return index_to_uuid, processes, None


def selected_gpu_uuids(visible: str, index_to_uuid: dict[str, str]) -> tuple[set[str], list[str]]:
    tokens = [token.strip() for token in visible.split(",") if token.strip()]
    if not tokens or tokens == ["-1"]:
        return set(), []
    if any(token.lower() == "all" for token in tokens):
        return set(index_to_uuid.values()), tokens
    selected: set[str] = set()
    unresolved: list[str] = []
    for token in tokens:
        if token in index_to_uuid:
            selected.add(index_to_uuid[token])
        elif token.startswith("GPU-"):
            selected.add(token)
        else:
            unresolved.append(token)
    return selected, unresolved


def redact_gpu_probe(
    index_to_uuid: dict[str, str],
    processes: list[dict[str, str]],
    selected_visible_devices: list[str],
) -> dict[str, Any]:
    selected_uuids: set[str] = set()
    unresolved: list[str] = []
    for visible in selected_visible_devices:
        selected, unresolved_for_visible = selected_gpu_uuids(visible, index_to_uuid)
        selected_uuids.update(selected)
        unresolved.extend(unresolved_for_visible)
    uuid_set = set(index_to_uuid.values()) | {str(p.get("gpu_uuid")) for p in processes}
    uuid_map = {uuid: f"GPU-REDACTED-{idx}" for idx, uuid in enumerate(sorted(uuid_set)) if uuid}
    blocking = [p for p in processes if p.get("gpu_uuid") in selected_uuids]
    def redact_process(process: dict[str, str]) -> dict[str, str]:
        redacted = dict(process)
        if redacted.get("gpu_uuid"):
            redacted["gpu_uuid"] = uuid_map.get(str(redacted["gpu_uuid"]), "GPU-REDACTED")
        return redacted
    return {
        "selected_visible_devices": selected_visible_devices,
        "selected_gpu_uuids": [uuid_map.get(uuid, "GPU-REDACTED") for uuid in sorted(selected_uuids)],
        "unresolved_visible_devices": unresolved,
        "blocking_process_count": len(blocking),
        "blocking_processes": [redact_process(p) for p in blocking],
        "all_compute_process_count": len(processes),
        "all_compute_processes": [redact_process(p) for p in processes],
        "hardware_identifiers_redacted": True,
    }


def build_entry(row: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    name = str(row.get("name", ""))
    main_command = str(row.get("main_command", ""))
    summarize_command = str(row.get("summarize_command", ""))
    findings: list[str] = []
    main_env, main_argv = split_env_command(main_command) if main_command else ({}, [])
    summary_env, summary_argv = split_env_command(summarize_command) if summarize_command else ({}, [])
    main_script = script_path(main_argv)
    summary_script = script_path(summary_argv)
    if not main_command:
        findings.append("main_command_missing")
    if not summarize_command:
        findings.append("summarize_command_missing")
    if not main_argv:
        findings.append("main_argv_empty")
    if not summary_argv:
        findings.append("summary_argv_empty")
    if main_script is None or not (ROOT / main_script).exists():
        findings.append("main_script_missing")
    if summary_script is None or not (ROOT / summary_script).exists():
        findings.append("summary_script_missing")
    if str(row.get("run_root", "")) not in main_command:
        findings.append("run_root_not_in_main_command")
    if str(row.get("summary_md", "")) not in summarize_command:
        findings.append("summary_md_not_in_summarize_command")
    if str(row.get("summary_csv", "")) not in summarize_command:
        findings.append("summary_csv_not_in_summarize_command")
    if row.get("preflight_command") and "--preflight-only" not in str(row.get("preflight_command")):
        findings.append("queue_preflight_command_not_preflight_only")
    if row.get("run_wrapper_command") and "--preflight-only" in str(row.get("run_wrapper_command")):
        findings.append("queue_run_wrapper_command_is_preflight_only")
    expected_receipt_json, expected_receipt_md = receipt_paths(name)
    receipt_summary = load_receipt_summary(expected_receipt_json)
    if receipt_summary and receipt_summary.get("entry") != name:
        findings.append("existing_receipt_entry_mismatch")
    requires_gpu = bool(main_env.get("CUDA_VISIBLE_DEVICES") not in (None, "", "-1"))
    return (
        {
            "name": name,
            "category": row.get("category"),
            "observed": bool(row.get("observed")),
            "requires_gpu": requires_gpu,
            "cuda_visible_devices": main_env.get("CUDA_VISIBLE_DEVICES"),
            "main_script": main_script,
            "main_script_exists": bool(main_script and (ROOT / main_script).exists()),
            "summary_script": summary_script,
            "summary_script_exists": bool(summary_script and (ROOT / summary_script).exists()),
            "run_root": row.get("run_root"),
            "summary_md": row.get("summary_md"),
            "summary_csv": row.get("summary_csv"),
            "preflight_command": row.get("preflight_command"),
            "run_wrapper_command": row.get("run_wrapper_command"),
            "expected_receipt_json": expected_receipt_json,
            "expected_receipt_md": expected_receipt_md,
            "existing_receipt": receipt_summary,
            "command_shape_ready": not findings,
            "training_started_by_this_audit": False,
            "validation_findings": findings,
        },
        [f"{name}:{finding}" for finding in findings],
    )


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    queue = load_json(args.queue_json)
    risk_flags: list[str] = []
    if queue.get("remaining_experiment_queue_ready") is not True:
        risk_flags.append("remaining_experiment_queue_not_ready")
    rows = queue.get("entries", [])
    by_name = {str(row.get("name")): row for row in rows if isinstance(row, dict)}
    if set(by_name) != set(EXPECTED_NAMES):
        missing = sorted(set(EXPECTED_NAMES) - set(by_name))
        extra = sorted(set(by_name) - set(EXPECTED_NAMES))
        risk_flags.extend(f"missing_entry:{name}" for name in missing)
        risk_flags.extend(f"unexpected_entry:{name}" for name in extra)
    entries: list[dict[str, Any]] = []
    selected_visible_devices: list[str] = []
    for name in EXPECTED_NAMES:
        if name not in by_name:
            continue
        entry, findings = build_entry(by_name[name])
        entries.append(entry)
        risk_flags.extend(findings)
        if entry.get("cuda_visible_devices"):
            selected_visible_devices.append(str(entry["cuda_visible_devices"]))

    live_gpu_probe: dict[str, Any] = {
        "performed": bool(args.live_gpu_probe),
        "training_started": False,
        "query_error": None,
        "status": "not_requested",
    }
    if args.live_gpu_probe:
        index_to_uuid, processes, query_error = query_gpu_inventory()
        live_gpu_probe["query_error"] = query_error
        if query_error is None:
            live_gpu_probe.update(redact_gpu_probe(index_to_uuid, processes, selected_visible_devices))
            live_gpu_probe["status"] = (
                "selected_gpu_busy"
                if int(live_gpu_probe.get("blocking_process_count", 0)) > 0
                else "selected_gpu_available"
            )
        else:
            live_gpu_probe["status"] = "gpu_inventory_unavailable"

    open_risk_flags = list(dict.fromkeys(str(flag) for flag in queue.get("open_risk_flags", [])))
    return {
        "remaining_experiment_preflight_audit_ready": not risk_flags,
        "not_completed_experiment_evidence": True,
        "audit_is_non_executing": True,
        "queue_json": relpath(args.queue_json),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expected_entry_count": len(EXPECTED_NAMES),
        "entry_count": len(entries),
        "command_shape_ready_count": sum(1 for entry in entries if entry["command_shape_ready"]),
        "observed_entry_count": sum(1 for entry in entries if entry["observed"]),
        "gpu_required_entry_count": sum(1 for entry in entries if entry["requires_gpu"]),
        "entries": entries,
        "live_gpu_probe": live_gpu_probe,
        "risk_flags": risk_flags,
        "open_risk_flags": open_risk_flags,
        "interpretation": {
            "all_commands_parsed_without_starting_training": not risk_flags,
            "queue_still_requires_gpu_reruns": True,
            "absence_of_live_gpu_probe_does_not_close_or_create_scientific_blockers": not args.live_gpu_probe,
            "busy_gpu_blocks_execution_but_not_static_preflight": bool(
                live_gpu_probe.get("status") == "selected_gpu_busy"
            ),
        },
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Remaining Experiment Preflight Audit",
        "",
        f"Ready: `{payload['remaining_experiment_preflight_audit_ready']}`.",
        f"Non-executing audit: `{payload['audit_is_non_executing']}`.",
        f"Completed experiment evidence: `{not payload['not_completed_experiment_evidence']}`.",
        f"Queue JSON: `{payload['queue_json']}`.",
        "",
        "This audit parses the queued training and summary commands without starting",
        "training. It is an operational preflight record, not evidence that the",
        "locked final-test, BatchNorm ablations, or saved-artifact reruns completed.",
        "",
        "## Summary",
        "",
        f"- Expected entries: `{payload['expected_entry_count']}`",
        f"- Entries observed in queue: `{payload['entry_count']}`",
        f"- Command-shape ready entries: `{payload['command_shape_ready_count']}`",
        f"- Already completed entries: `{payload['observed_entry_count']}`",
        f"- GPU-required entries: `{payload['gpu_required_entry_count']}`",
        f"- Live GPU probe status: `{payload['live_gpu_probe']['status']}`",
        "",
        "## Entries",
        "",
        "| Entry | Category | Observed | CUDA | Command shape | Existing receipt |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for entry in payload["entries"]:
        receipt = entry.get("existing_receipt") or {}
        receipt_text = receipt.get("status", "not observed") if isinstance(receipt, dict) else "not observed"
        lines.append(
            "| {name} | {category} | {observed} | `{cuda}` | {ready} | {receipt} |".format(
                name=entry["name"],
                category=entry.get("category"),
                observed=entry.get("observed"),
                cuda=entry.get("cuda_visible_devices"),
                ready=entry.get("command_shape_ready"),
                receipt=receipt_text,
            )
        )
    lines.extend(["", "## Live GPU Probe", ""])
    gpu = payload["live_gpu_probe"]
    for key in [
        "performed",
        "status",
        "query_error",
        "selected_visible_devices",
        "blocking_process_count",
        "all_compute_process_count",
        "hardware_identifiers_redacted",
    ]:
        if key in gpu:
            lines.append(f"- {key}: `{gpu.get(key)}`")
    if gpu.get("blocking_processes"):
        lines.extend(["", "Blocking process details are sanitized:", ""])
        for process in gpu["blocking_processes"]:
            lines.append(f"- `{process}`")
    lines.extend(["", "## Open Scientific Risks", ""])
    lines.extend(f"- `{flag}`" for flag in payload["open_risk_flags"])
    if payload["risk_flags"]:
        lines.extend(["", "## Risk Flags", ""])
        lines.extend(f"- `{flag}`" for flag in payload["risk_flags"])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This audit verifies command shape and expected receipts only.",
            "- It does not reduce the locked final-test, BatchNorm, or saved-artifact blockers.",
            "- Run the entry-specific wrapper commands after the selected GPU is available.",
            "",
            "This file is generated by `scripts/audit_remaining_experiment_preflight.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    write_json(args.out_json, payload)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "remaining_experiment_preflight_audit_ready": payload[
                    "remaining_experiment_preflight_audit_ready"
                ],
                "entry_count": payload["entry_count"],
                "command_shape_ready_count": payload["command_shape_ready_count"],
                "live_gpu_probe_status": payload["live_gpu_probe"]["status"],
                "risk_flags": payload["risk_flags"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
