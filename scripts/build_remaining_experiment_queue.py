#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "runs" / "validation_bn_rerun_plan.json"
DEFAULT_TOP_AUDIT = ROOT / "runs" / "top_conference_completion_audit.json"
DEFAULT_OUT_JSON = ROOT / "runs" / "remaining_experiment_queue.json"
DEFAULT_OUT_MD = ROOT / "docs" / "remaining_experiment_queue.md"

LOCKED_ENTRIES = ["locked_final_test_sgld_full_cifar"]
BN_ENTRIES = [
    "bn_freeze_sgld_full_cifar",
    "bn_recalibrate_sgld_full_cifar",
    "bn_dense_buffers_sgld_full_cifar",
    "bn_freeze_csgld_full_cifar",
    "bn_recalibrate_csgld_full_cifar",
    "bn_dense_buffers_csgld_full_cifar",
]
SAVED_ARTIFACT_ENTRIES = [
    "saved_artifacts_csgld_multichain",
    "saved_artifacts_lowrank128",
    "saved_artifacts_jointdiag",
]

GROUPS = {
    "locked_final_test": {
        "entries": LOCKED_ENTRIES,
        "blockers": [
            "locked_final_test_metrics_not_observed",
            "locked_final_test_rerun_not_observed",
        ],
        "paper_action": (
            "Use the locked test row as the final unbiased SGLD estimate only "
            "after the validation-selected source and locked summary artifacts pass."
        ),
        "acceptance_criteria": [
            "metrics.json exists under the locked run root",
            "config.evaluation_split is test",
            "selection_protocol links to the validation-selected run and summary",
            "summary CSV/MD contains the expected three comparison rows",
            "scripts/audit_locked_final_test_protocol.py has no risk flags",
        ],
    },
    "batchnorm_policy_ablation": {
        "entries": BN_ENTRIES,
        "blockers": [
            "full_cifar_bn_ablation_rerun_not_observed",
            "bn_policy_cifar_ablation_not_observed",
        ],
        "paper_action": (
            "If freeze/recalibrate/dense-buffer rows agree with the default, "
            "move the BatchNorm caveat to a sensitivity appendix; otherwise "
            "scope CIFAR posterior conclusions to the observed BN policy."
        ),
        "acceptance_criteria": [
            "all six SGLD/cSGLD BN policy rows have fresh metrics",
            "summaries are regenerated from those run roots",
            "validation_bn_rerun_plan marks the rows observed",
            "paper limitations reflect any policy-sensitive result",
        ],
    },
    "saved_artifact_seed_level_reruns": {
        "entries": SAVED_ARTIFACT_ENTRIES,
        "blockers": [
            "seed_level_saved_artifacts_incomplete_for_other_direct_rows",
            "seed_level_saved_artifact_reruns_not_observed",
        ],
        "paper_action": (
            "Promote cSGLD/LowRank128/JointDiag direct rows from pooled "
            "sample-level diagnostics to seed-level evidence only after saved "
            "mask artifacts and paired seed-level audits exist."
        ),
        "acceptance_criteria": [
            "each row writes mask_artifacts.npz",
            "summaries are regenerated from those run roots",
            "seed-level paired audit includes the new saved-artifact rows",
            "paper text no longer relies on pooled p-values for those rows",
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-json", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--top-audit-json", type=Path, default=DEFAULT_TOP_AUDIT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    return parser.parse_args()


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json(path)
    return payload if isinstance(payload, dict) else {}


def entry_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("name")): entry
        for entry in plan.get("entries", [])
        if isinstance(entry, dict) and entry.get("name")
    }


def preflight_command(entry_name: str) -> str:
    return (
        ".venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py "
        f"--entry {entry_name} --python .venv/bin/python --preflight-only"
    )


def run_command(entry_name: str) -> str:
    return (
        ".venv/bin/python scripts/run_validation_bn_rerun_plan_entry.py "
        f"--entry {entry_name} --python .venv/bin/python"
    )


def classify_entry(name: str) -> str:
    if name in LOCKED_ENTRIES:
        return "locked_final_test"
    if name in BN_ENTRIES:
        return "batchnorm_policy_ablation"
    if name in SAVED_ARTIFACT_ENTRIES:
        return "saved_artifact_seed_level_reruns"
    return "unknown"


def validate_entry(name: str, entry: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    command = str(entry.get("command", ""))
    summarize = str(entry.get("summarize_command", ""))
    if not command:
        findings.append(f"{name}_main_command_missing")
    if not summarize:
        findings.append(f"{name}_summarize_command_missing")
    if not entry.get("run_root"):
        findings.append(f"{name}_run_root_missing")
    if not entry.get("summary_md") or not entry.get("summary_csv"):
        findings.append(f"{name}_summary_target_missing")
    if name in LOCKED_ENTRIES:
        for token in [
            "--evaluation-split test",
            "--selection-source-run",
            "--selection-source-summary",
        ]:
            if token not in command:
                findings.append(f"{name}_command_missing_{token.strip('-').replace(' ', '_')}")
    if name in BN_ENTRIES:
        policy = str(entry.get("posterior_bn_policy", ""))
        if policy not in {"freeze", "recalibrate", "dense_buffers"}:
            findings.append(f"{name}_unexpected_bn_policy")
        if f"--posterior-bn-policy {policy}" not in command:
            findings.append(f"{name}_command_missing_posterior_bn_policy")
    if name in SAVED_ARTIFACT_ENTRIES:
        if entry.get("saves_mask_artifacts") is not True:
            findings.append(f"{name}_plan_not_marked_saves_mask_artifacts")
        if "--save-mask-artifacts" not in command:
            findings.append(f"{name}_command_missing_save_mask_artifacts")
    return findings


def build_queue(plan_json: Path, top_audit_json: Path) -> dict[str, Any]:
    plan = load_json(plan_json)
    top = load_json_or_empty(top_audit_json)
    entries = entry_map(plan)
    open_blockers = set(str(flag) for flag in top.get("open_blockers", []))
    risk_flags: list[str] = []
    queue_entries: list[dict[str, Any]] = []

    expected_names = LOCKED_ENTRIES + BN_ENTRIES + SAVED_ARTIFACT_ENTRIES
    missing_entries = [name for name in expected_names if name not in entries]
    if missing_entries:
        risk_flags.extend(f"{name}_missing_from_validation_bn_plan" for name in missing_entries)

    for name in expected_names:
        entry = entries.get(name)
        if entry is None:
            continue
        category = classify_entry(name)
        group = GROUPS[category]
        findings = validate_entry(name, entry)
        risk_flags.extend(findings)
        queue_entries.append(
            {
                "name": name,
                "category": category,
                "priority": entry.get("priority"),
                "observed": bool(entry.get("observed")),
                "evaluation_split": entry.get("evaluation_split"),
                "posterior_bn_policy": entry.get("posterior_bn_policy"),
                "saves_mask_artifacts": bool(entry.get("saves_mask_artifacts")),
                "run_root": entry.get("run_root"),
                "summary_md": entry.get("summary_md"),
                "summary_csv": entry.get("summary_csv"),
                "main_command": entry.get("command"),
                "summarize_command": entry.get("summarize_command"),
                "preflight_command": preflight_command(name),
                "run_wrapper_command": run_command(name),
                "blocking_open_flags": [
                    flag for flag in group["blockers"] if flag in open_blockers
                ],
                "acceptance_criteria": group["acceptance_criteria"],
                "paper_action": group["paper_action"],
                "validation_findings": findings,
            }
        )

    group_summaries = []
    for category, group in GROUPS.items():
        names = set(group["entries"])
        rows = [row for row in queue_entries if row["name"] in names]
        if rows and any(not row["observed"] for row in rows):
            open_blockers.update(str(flag) for flag in group["blockers"])
        group_summaries.append(
            {
                "category": category,
                "entry_count": len(rows),
                "observed_count": sum(1 for row in rows if row["observed"]),
                "open_blockers": [
                    flag for flag in group["blockers"] if flag in open_blockers
                ],
                "paper_action": group["paper_action"],
            }
        )

    return {
        "remaining_experiment_queue_ready": not risk_flags,
        "plan_json": relpath(plan_json),
        "top_audit_json": relpath(top_audit_json),
        "expected_entry_count": len(expected_names),
        "queue_entry_count": len(queue_entries),
        "group_summaries": group_summaries,
        "entries": queue_entries,
        "post_run_refresh_commands": [
            ".venv/bin/python scripts/build_validation_bn_rerun_plan.py",
            ".venv/bin/python scripts/audit_locked_final_test_protocol.py",
            ".venv/bin/python scripts/audit_direct_mode_ticket_seed_level_artifacts.py",
            ".venv/bin/python scripts/audit_batchnorm_posterior_policy.py",
            ".venv/bin/python scripts/build_paper_claim_ledger.py",
            ".venv/bin/python scripts/build_top_conference_completion_audit.py",
            ".venv/bin/python scripts/verify_research_artifacts.py",
        ],
        "risk_flags": risk_flags,
        "open_risk_flags": sorted(
            flag
            for group in GROUPS.values()
            for flag in group["blockers"]
            if flag in open_blockers
        ),
        "interpretation": {
            "queue_is_execution_plan_not_completed_evidence": True,
            "gpu_reruns_still_required": any(
                not row["observed"] for row in queue_entries
            ),
            "paper_claims_must_remain_scoped_until_queue_observed": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["remaining_experiment_queue_ready"] else "not ready"
    lines = [
        "# Remaining Experiment Queue",
        "",
        "This generated queue converts the remaining scientific-protocol blockers",
        "into exact rerun commands, expected evidence, and paper actions. It is",
        "an execution plan, not completed experiment evidence.",
        "",
        f"Queue status: {status}.",
        f"Plan JSON: `{payload['plan_json']}`.",
        f"Top audit JSON: `{payload['top_audit_json']}`.",
        "",
        "## Group Summary",
        "",
        "| Category | Entries | Observed | Open blockers |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in payload["group_summaries"]:
        blockers = ", ".join(f"`{flag}`" for flag in row["open_blockers"]) or "none"
        lines.append(
            f"| {row['category']} | {row['entry_count']} | "
            f"{row['observed_count']} | {blockers} |"
        )
    lines.extend(["", "## Queue Entries", ""])
    for row in payload["entries"]:
        blockers = ", ".join(f"`{flag}`" for flag in row["blocking_open_flags"]) or "none"
        lines.extend(
            [
                f"### {row['name']}",
                "",
                f"- Category: `{row['category']}`",
                f"- Priority: `{row['priority']}`",
                f"- Observed: `{row['observed']}`",
                f"- Evaluation split: `{row['evaluation_split']}`",
                f"- BatchNorm policy: `{row['posterior_bn_policy']}`",
                f"- Saves mask artifacts: `{row['saves_mask_artifacts']}`",
                f"- Run root: `{row['run_root']}`",
                f"- Summary MD: `{row['summary_md']}`",
                f"- Summary CSV: `{row['summary_csv']}`",
                f"- Blocking open flags: {blockers}",
                "",
                "Preflight:",
                "",
                "```bash",
                str(row["preflight_command"]),
                "```",
                "",
                "Run wrapper:",
                "",
                "```bash",
                str(row["run_wrapper_command"]),
                "```",
                "",
                "Acceptance criteria:",
            ]
        )
        lines.extend(f"- {item}" for item in row["acceptance_criteria"])
        lines.extend(["", "Paper action:", "", f"- {row['paper_action']}", ""])
    lines.extend(["## Post-Run Refresh", "", "```bash"])
    lines.extend(payload["post_run_refresh_commands"])
    lines.extend(["```", "", "## Risk Flags", ""])
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
            "This file is generated by `scripts/build_remaining_experiment_queue.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_queue(args.plan_json, args.top_audit_json)
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "remaining_experiment_queue_ready": payload[
                    "remaining_experiment_queue_ready"
                ],
                "queue_entry_count": payload["queue_entry_count"],
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
