#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "runs" / "validation_bn_rerun_plan.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one generated validation/BatchNorm rerun-plan entry."
    )
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--entry", help="Entry name from validation_bn_rerun_plan.json.")
    parser.add_argument("--list", action="store_true", help="List available entries and exit.")
    parser.add_argument(
        "--python",
        default=None,
        help="Replace the Python executable in generated commands, e.g. .venv/bin/python.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Override CUDA_VISIBLE_DEVICES for the main command.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running.")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run only the selected-GPU occupancy preflight and write a receipt.",
    )
    parser.add_argument("--skip-main", action="store_true", help="Only run summary/audit steps.")
    parser.add_argument("--skip-summary", action="store_true", help="Only run the main command.")
    parser.add_argument(
        "--allow-busy-gpu",
        action="store_true",
        help="Run even if nvidia-smi reports another compute process on the selected GPU.",
    )
    parser.add_argument(
        "--skip-gpu-preflight",
        action="store_true",
        help="Skip the selected-GPU occupancy check before running the main command.",
    )
    parser.add_argument(
        "--skip-refresh-audits",
        action="store_true",
        help="Do not refresh plan/protocol audits after a successful run.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help="Output JSON receipt path. Defaults to runs/validation_bn_plan_entry_<entry>_receipt.json.",
    )
    parser.add_argument(
        "--receipt-md",
        type=Path,
        default=None,
        help="Output Markdown receipt path. Defaults to docs/validation_bn_plan_entry_<entry>_receipt.md.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def local_path_for_receipt(path: str) -> str:
    candidate = Path(path)
    for variant in [candidate, candidate.absolute()]:
        try:
            return str(variant.relative_to(ROOT))
        except ValueError:
            continue
    return candidate.name


def split_env_command(command: str, python_override: str | None) -> tuple[dict[str, str], list[str]]:
    tokens = shlex.split(command)
    env: dict[str, str] = {}
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        key, value = tokens.pop(0).split("=", 1)
        env[key] = value
    if python_override and tokens and tokens[0] in {".venv/bin/python", "python", "python3"}:
        tokens[0] = python_override
    if not tokens:
        raise ValueError(f"empty command after parsing environment assignments: {command!r}")
    return env, tokens


def command_record(
    label: str,
    command: str,
    python_override: str | None,
    device_override: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    env_updates, argv = split_env_command(command, python_override)
    if device_override is not None:
        env_updates["CUDA_VISIBLE_DEVICES"] = device_override
    return {
        "label": label,
        "command": command,
        "argv": argv,
        "env_updates": env_updates,
        "dry_run": dry_run,
        "returncode": None,
        "started_at": None,
        "ended_at": None,
        "wall_clock_seconds": None,
    }


def run_record(record: dict[str, Any]) -> int:
    record["started_at"] = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in record["env_updates"].items()})
    result = subprocess.run(record["argv"], cwd=ROOT, env=env, check=False)
    record["returncode"] = result.returncode
    record["ended_at"] = datetime.now(timezone.utc).isoformat()
    record["wall_clock_seconds"] = round(time.monotonic() - start, 3)
    return result.returncode


def display_command(record: dict[str, Any]) -> str:
    env_tokens = [f"{key}={value}" for key, value in record["env_updates"].items()]
    return shlex.join(env_tokens + list(record["argv"]))


def split_csv_line(line: str) -> list[str]:
    return [part.strip() for part in line.split(",")]


def query_gpu_inventory() -> tuple[dict[str, str], list[dict[str, Any]], str | None]:
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
    processes: list[dict[str, Any]] = []
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


def sanitize_gpu_preflight_for_receipt(gpu_check: dict[str, Any]) -> dict[str, Any]:
    sanitized = json.loads(json.dumps(gpu_check))
    uuids = set(sanitized.get("selected_gpu_uuids", []))
    for key in ["blocking_processes", "all_compute_processes"]:
        for process in sanitized.get(key, []):
            uuid = process.get("gpu_uuid")
            if uuid:
                uuids.add(str(uuid))
    uuid_map = {
        uuid: f"GPU-REDACTED-{idx}"
        for idx, uuid in enumerate(sorted(uuids))
    }
    if "selected_gpu_uuids" in sanitized:
        sanitized["selected_gpu_uuids"] = [
            uuid_map.get(uuid, "GPU-REDACTED") for uuid in sanitized["selected_gpu_uuids"]
        ]
    for key in ["blocking_processes", "all_compute_processes"]:
        for process in sanitized.get(key, []):
            uuid = process.get("gpu_uuid")
            if uuid:
                process["gpu_uuid"] = uuid_map.get(str(uuid), "GPU-REDACTED")
    sanitized["hardware_identifiers_redacted"] = bool(uuid_map)
    return sanitized


def gpu_preflight(
    records: list[dict[str, Any]],
    *,
    allow_busy_gpu: bool,
    skip_gpu_preflight: bool,
) -> dict[str, Any]:
    main_records = [record for record in records if record["label"] == "main"]
    visible_values = [
        str(record["env_updates"].get("CUDA_VISIBLE_DEVICES", ""))
        for record in main_records
        if "CUDA_VISIBLE_DEVICES" in record["env_updates"]
    ]
    visible_values = [value for value in visible_values if value and value != "-1"]
    if not visible_values:
        return {
            "required": False,
            "skipped": False,
            "risk_flags": [],
            "warning_flags": [],
            "selected_visible_devices": [],
            "blocking_processes": [],
        }
    if skip_gpu_preflight:
        return {
            "required": True,
            "skipped": True,
            "risk_flags": [],
            "warning_flags": ["gpu_preflight_skipped"],
            "selected_visible_devices": visible_values,
            "blocking_processes": [],
        }

    index_to_uuid, processes, query_error = query_gpu_inventory()
    if query_error is not None:
        return {
            "required": True,
            "skipped": False,
            "risk_flags": [query_error],
            "warning_flags": [],
            "selected_visible_devices": visible_values,
            "blocking_processes": [],
        }

    selected: set[str] = set()
    unresolved: list[str] = []
    for visible in visible_values:
        selected_for_value, unresolved_for_value = selected_gpu_uuids(visible, index_to_uuid)
        selected.update(selected_for_value)
        unresolved.extend(unresolved_for_value)
    if unresolved:
        return {
            "required": True,
            "skipped": False,
            "risk_flags": ["gpu_preflight_unresolved_visible_device"],
            "warning_flags": [],
            "selected_visible_devices": visible_values,
            "unresolved_visible_devices": unresolved,
            "blocking_processes": [],
        }

    blocking = [process for process in processes if process.get("gpu_uuid") in selected]
    risk_flags: list[str] = []
    warning_flags: list[str] = []
    if blocking:
        if allow_busy_gpu:
            warning_flags.append("selected_gpu_busy_allowed")
        else:
            risk_flags.append("selected_gpu_busy")
    return {
        "required": True,
        "skipped": False,
        "risk_flags": risk_flags,
        "warning_flags": warning_flags,
        "selected_visible_devices": visible_values,
        "selected_gpu_uuids": sorted(selected),
        "blocking_processes": blocking,
        "all_compute_processes": processes,
    }


def find_entry(plan: dict[str, Any], name: str) -> dict[str, Any]:
    for entry in plan.get("entries", []):
        if entry.get("name") == name:
            return entry
    available = ", ".join(str(entry.get("name")) for entry in plan.get("entries", []))
    raise SystemExit(f"unknown entry {name!r}; available entries: {available}")


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Validation/BatchNorm Rerun Receipt: {payload['entry']}",
        "",
        f"- Ready: `{payload['validation_bn_plan_entry_receipt_ready']}`",
        f"- Status: `{payload['status']}`",
        f"- Preflight only: `{payload['preflight_only']}`",
        f"- Entry observed before run: `{payload['entry_observed_before']}`",
        f"- Entry observed after refresh: `{payload.get('entry_observed_after_refresh')}`",
        f"- Receipt JSON: `{payload['receipt_json']}`",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Host: `{payload['host']}`",
        "",
        "## GPU Preflight",
        "",
        f"- Required: `{payload['gpu_preflight']['required']}`",
        f"- Skipped: `{payload['gpu_preflight']['skipped']}`",
        f"- Selected visible devices: `{payload['gpu_preflight'].get('selected_visible_devices', [])}`",
        f"- Blocking processes: `{payload['gpu_preflight'].get('blocking_processes', [])}`",
        "",
        "## Commands",
        "",
    ]
    for record in payload["commands"]:
        lines.extend(
            [
                f"### {record['label']}",
                "",
                f"- Return code: `{record['returncode']}`",
                f"- Wall clock seconds: `{record['wall_clock_seconds']}`",
                f"- Env updates: `{record['env_updates']}`",
                "",
                "```bash",
                display_command(record),
                "```",
                "",
            ]
        )
    if payload["risk_flags"]:
        lines.extend(["## Risk Flags", "", *[f"- {flag}" for flag in payload["risk_flags"]], ""])
    if payload["warning_flags"]:
        lines.extend(
            ["## Warning Flags", "", *[f"- {flag}" for flag in payload["warning_flags"]], ""]
        )
    lines.append("This file is generated by `scripts/run_validation_bn_rerun_plan_entry.py`.")
    return "\n".join(lines) + "\n"


def refresh_audits(python_executable: str | None) -> list[dict[str, Any]]:
    py = python_executable or ".venv/bin/python"
    refresh_commands = [
        f"{py} scripts/build_validation_bn_rerun_plan.py",
        f"{py} scripts/audit_locked_final_test_protocol.py",
        f"{py} scripts/audit_validation_test_usage_policy.py",
    ]
    records = [
        command_record(f"refresh_{idx}", command, None, None, False)
        for idx, command in enumerate(refresh_commands, start=1)
    ]
    for record in records:
        code = run_record(record)
        if code != 0:
            break
    return records


def build_receipt_payload(
    *,
    entry_name: str,
    entry: dict[str, Any],
    refreshed_entry: dict[str, Any],
    records: list[dict[str, Any]],
    gpu_check: dict[str, Any],
    risk_flags: list[str],
    warning_flags: list[str],
    receipt: Path,
    receipt_md: Path,
    preflight_only: bool,
    status: str,
) -> dict[str, Any]:
    ready = not risk_flags
    python_executable = local_path_for_receipt(sys.executable)
    return {
        "validation_bn_plan_entry_receipt_ready": ready,
        "entry": entry_name,
        "status": status,
        "preflight_only": preflight_only,
        "entry_observed_before": bool(entry.get("observed")),
        "entry_observed_after_refresh": bool(refreshed_entry.get("observed")),
        "priority": entry.get("priority"),
        "purpose": entry.get("purpose"),
        "criticism_addressed": entry.get("criticism_addressed"),
        "evaluation_split": entry.get("evaluation_split"),
        "posterior_bn_policy": entry.get("posterior_bn_policy"),
        "run_root": entry.get("run_root"),
        "summary_md": entry.get("summary_md"),
        "summary_csv": entry.get("summary_csv"),
        "receipt_json": rel(receipt),
        "receipt_md": rel(receipt_md),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": "local_hostname_redacted",
        "host_redacted": True,
        "platform": platform.platform(),
        "python_executable": python_executable,
        "commands": records,
        "would_run": records if preflight_only else [],
        "gpu_preflight": sanitize_gpu_preflight_for_receipt(gpu_check),
        "risk_flags": risk_flags,
        "warning_flags": warning_flags,
    }


def write_receipt(receipt: Path, receipt_md: Path, payload: dict[str, Any]) -> None:
    write_json(receipt, payload)
    receipt_md.parent.mkdir(parents=True, exist_ok=True)
    receipt_md.write_text(build_markdown(payload), encoding="utf-8")


def main() -> int:
    args = parse_args()
    plan = load_json(args.plan)
    entries = plan.get("entries", [])
    if args.list:
        for entry in entries:
            print(
                "\t".join(
                    [
                        str(entry.get("name")),
                        str(entry.get("priority")),
                        str(entry.get("evaluation_split")),
                        str(entry.get("posterior_bn_policy")),
                        str(entry.get("observed")),
                    ]
                )
            )
        return 0
    if not args.entry:
        raise SystemExit("--entry is required unless --list is used")

    entry = find_entry(plan, args.entry)
    receipt = args.receipt or ROOT / "runs" / f"validation_bn_plan_entry_{args.entry}_receipt.json"
    receipt_md = args.receipt_md or ROOT / "docs" / f"validation_bn_plan_entry_{args.entry}_receipt.md"

    records: list[dict[str, Any]] = []
    if not args.skip_main:
        records.append(
            command_record(
                "main",
                str(entry["command"]),
                args.python,
                args.device,
                args.dry_run,
            )
        )
    if not args.skip_summary:
        records.append(
            command_record(
                "summary",
                str(entry["summarize_command"]),
                args.python,
                None,
                args.dry_run,
            )
        )

    if args.dry_run:
        for record in records:
            print(display_command(record))
        return 0

    gpu_check = gpu_preflight(
        records,
        allow_busy_gpu=args.allow_busy_gpu,
        skip_gpu_preflight=args.skip_gpu_preflight,
    )
    risk_flags: list[str] = list(gpu_check["risk_flags"])
    warning_flags: list[str] = list(gpu_check["warning_flags"])
    if args.preflight_only:
        status = "preflight_ready" if not risk_flags else "blocked_by_gpu_preflight"
        payload = build_receipt_payload(
            entry_name=args.entry,
            entry=entry,
            refreshed_entry=entry,
            records=records,
            gpu_check=gpu_check,
            risk_flags=risk_flags,
            warning_flags=warning_flags,
            receipt=receipt,
            receipt_md=receipt_md,
            preflight_only=True,
            status=status,
        )
        write_receipt(receipt, receipt_md, payload)
        print(
            json.dumps(
                {
                    "validation_bn_plan_entry_receipt_ready": not risk_flags,
                    "entry": args.entry,
                    "status": status,
                    "risk_flags": risk_flags,
                    "warning_flags": warning_flags,
                    "selected_visible_devices": gpu_check.get("selected_visible_devices", []),
                    "blocking_processes": gpu_check.get("blocking_processes", []),
                    "receipt": rel(receipt),
                    "receipt_md": rel(receipt_md),
                },
                sort_keys=True,
            )
        )
        return 0 if not risk_flags else 1
    if not risk_flags:
        for record in records:
            code = run_record(record)
            if code != 0:
                risk_flags.append(f"{record['label']}_command_failed")
                break

    refresh_records: list[dict[str, Any]] = []
    if not risk_flags and not args.skip_refresh_audits:
        refresh_records = refresh_audits(args.python)
        records.extend(refresh_records)
        if any(record["returncode"] != 0 for record in refresh_records):
            risk_flags.append("refresh_audit_failed")

    refreshed_plan = load_json(args.plan) if args.plan.exists() else plan
    refreshed_entry = find_entry(refreshed_plan, args.entry)
    ready = not risk_flags
    status = "completed" if ready else "blocked_or_failed"
    payload = build_receipt_payload(
        entry_name=args.entry,
        entry=entry,
        refreshed_entry=refreshed_entry,
        records=records,
        gpu_check=gpu_check,
        risk_flags=risk_flags,
        warning_flags=warning_flags,
        receipt=receipt,
        receipt_md=receipt_md,
        preflight_only=False,
        status=status,
    )
    write_receipt(receipt, receipt_md, payload)
    print(
        json.dumps(
            {
                "validation_bn_plan_entry_receipt_ready": ready,
                "entry": args.entry,
                "risk_flags": risk_flags,
                "warning_flags": warning_flags,
                "receipt": rel(receipt),
                "receipt_md": rel(receipt_md),
            },
            sort_keys=True,
        )
    )
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
