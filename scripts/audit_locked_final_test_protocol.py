#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "runs" / "validation_bn_rerun_plan.json"
DEFAULT_OUT_JSON = ROOT / "runs" / "locked_final_test_protocol_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "locked_final_test_protocol_audit.md"

VALIDATION_ENTRY = "validation_select_sgld_full_cifar"
LOCKED_ENTRY = "locked_final_test_sgld_full_cifar"
EXPECTED_SELECTION_RUN = (
    "runs/"
    "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3"
)
EXPECTED_SELECTION_SUMMARY = (
    "docs/"
    "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3.md"
)
EXPECTED_COMPARISONS = [
    "chain_start_magnitude_vs_tickets",
    "posterior_samples_vs_tickets",
    "posterior_modes_vs_tickets",
]
SUMMARY_REQUIRED_COLUMNS = [
    "run",
    "dataset",
    "model",
    "posterior_sampler",
    "comparison",
]

LOCKED_CONFIG_KEYS = [
    "dataset",
    "model",
    "seeds",
    "data_seed",
    "validation_fraction",
    "subset_strategy",
    "epochs",
    "rewind_epochs",
    "imp_rounds",
    "prune_fraction",
    "posterior_sampler",
    "posterior_sampler_config",
    "samples_per_chain",
    "posterior_chains",
    "posterior_chain_init",
    "samples_per_seed",
    "alignment_method",
    "alignment_batches",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-json", type=Path, default=DEFAULT_PLAN)
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


def latest_metrics(run_root: Path) -> tuple[Path | None, dict[str, Any] | None]:
    metrics_paths = sorted(run_root.glob("*/metrics.json"))
    if not metrics_paths:
        return None, None
    path = metrics_paths[-1]
    return path, load_json(path)


def plan_path(entry: dict[str, Any] | None, key: str) -> Path | None:
    if entry is None:
        return None
    value = entry.get(key)
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def entry_by_name(plan: dict[str, Any], name: str) -> dict[str, Any] | None:
    for entry in plan.get("entries", []):
        if isinstance(entry, dict) and entry.get("name") == name:
            return entry
    return None


def compare_locked_config(
    validation_metrics: dict[str, Any] | None,
    locked_metrics: dict[str, Any] | None,
) -> list[str]:
    if validation_metrics is None or locked_metrics is None:
        return []
    validation_config = validation_metrics.get("config", {})
    locked_config = locked_metrics.get("config", {})
    mismatches = []
    for key in LOCKED_CONFIG_KEYS:
        if validation_config.get(key) != locked_config.get(key):
            mismatches.append(key)
    return mismatches


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def audit_summary_artifacts(
    *,
    entry: dict[str, Any] | None,
    metrics_path: Path | None,
    expected_split: str,
    expected_sampler: str,
    require: bool,
) -> dict[str, Any]:
    csv_path = plan_path(entry, "summary_csv")
    md_path = plan_path(entry, "summary_md")
    result: dict[str, Any] = {
        "required": require,
        "summary_csv": relpath(csv_path) if csv_path else None,
        "summary_md": relpath(md_path) if md_path else None,
        "csv_exists": bool(csv_path and csv_path.exists()),
        "md_exists": bool(md_path and md_path.exists()),
        "csv_row_count": 0,
        "csv_expected_comparisons_present": False,
        "csv_required_columns_present": False,
        "csv_sampler_matches": False,
        "csv_run_matches_latest_metrics": False,
        "md_split_matches": False,
        "md_sampler_matches": False,
        "md_run_matches_latest_metrics": False,
    }
    if csv_path and csv_path.exists():
        rows = read_csv_rows(csv_path)
        result["csv_row_count"] = len(rows)
        columns = set(rows[0].keys()) if rows else set()
        result["csv_required_columns_present"] = set(SUMMARY_REQUIRED_COLUMNS).issubset(
            columns
        )
        comparisons = {row.get("comparison") for row in rows}
        result["csv_expected_comparisons_present"] = set(EXPECTED_COMPARISONS).issubset(
            comparisons
        )
        result["csv_sampler_matches"] = bool(rows) and all(
            row.get("posterior_sampler") == expected_sampler for row in rows
        )
        if metrics_path is not None:
            expected_run = relpath(metrics_path.parent)
            result["csv_run_matches_latest_metrics"] = bool(rows) and all(
                row.get("run") == expected_run for row in rows
            )
    if md_path and md_path.exists():
        text = " ".join(md_path.read_text(encoding="utf-8").split())
        result["md_split_matches"] = f"Evaluation split: `{expected_split}`" in text
        result["md_sampler_matches"] = f"Posterior sampler: `{expected_sampler}`" in text
        if metrics_path is not None:
            result["md_run_matches_latest_metrics"] = (
                f"Run: `{relpath(metrics_path.parent)}`" in text
            )
    return result


def required_summary_failures(label: str, summary: dict[str, Any]) -> list[str]:
    failures = []
    if not summary.get("required"):
        return failures
    for key in [
        "csv_exists",
        "md_exists",
        "csv_required_columns_present",
        "csv_expected_comparisons_present",
        "csv_sampler_matches",
        "csv_run_matches_latest_metrics",
        "md_split_matches",
        "md_sampler_matches",
        "md_run_matches_latest_metrics",
    ]:
        if summary.get(key) is not True:
            failures.append(f"{label}_{key}_failed")
    if summary.get("csv_row_count", 0) < len(EXPECTED_COMPARISONS):
        failures.append(f"{label}_csv_row_count_too_small")
    return failures


def build_audit(plan_json: Path) -> dict[str, Any]:
    plan = load_json(plan_json)
    validation_entry = entry_by_name(plan, VALIDATION_ENTRY)
    locked_entry = entry_by_name(plan, LOCKED_ENTRY)

    risk_flags: list[str] = []
    open_risk_flags: list[str] = []
    checks: dict[str, bool] = {}
    paths: dict[str, str | None] = {}
    summary_checks: dict[str, dict[str, Any]] = {}

    if validation_entry is None:
        risk_flags.append("validation_selection_plan_entry_missing")
    if locked_entry is None:
        risk_flags.append("locked_final_test_plan_entry_missing")

    validation_metrics_path: Path | None = None
    locked_metrics_path: Path | None = None
    validation_metrics: dict[str, Any] | None = None
    locked_metrics: dict[str, Any] | None = None

    if validation_entry is not None:
        validation_root = ROOT / str(validation_entry.get("run_root", ""))
        validation_metrics_path, validation_metrics = latest_metrics(validation_root)
        paths["validation_run_root"] = relpath(validation_root)
        paths["validation_metrics"] = (
            relpath(validation_metrics_path) if validation_metrics_path else None
        )
        paths["validation_summary_csv"] = relpath(plan_path(validation_entry, "summary_csv"))
        paths["validation_summary_md"] = relpath(plan_path(validation_entry, "summary_md"))
        checks["validation_entry_observed"] = bool(validation_entry.get("observed"))
        checks["validation_metrics_present"] = validation_metrics is not None
        summary_checks["validation"] = audit_summary_artifacts(
            entry=validation_entry,
            metrics_path=validation_metrics_path,
            expected_split="val",
            expected_sampler="sgld",
            require=True,
        )
        if validation_metrics is None:
            risk_flags.append("validation_selection_metrics_missing")
        else:
            config = validation_metrics.get("config", {})
            checks["validation_evaluation_split_val"] = (
                config.get("evaluation_split") == "val"
            )
            checks["validation_fraction_0p1"] = config.get("validation_fraction") == 0.1
            checks["validation_subset_seeded"] = config.get("subset_strategy") == "seeded"
            checks["validation_sampler_sgld"] = config.get("posterior_sampler") == "sgld"
            for name in [
                "validation_evaluation_split_val",
                "validation_fraction_0p1",
                "validation_subset_seeded",
                "validation_sampler_sgld",
            ]:
                if checks.get(name) is not True:
                    risk_flags.append(name.replace("validation_", "validation_config_not_"))
        risk_flags.extend(
            required_summary_failures("validation_summary", summary_checks["validation"])
        )

    if locked_entry is not None:
        locked_root = ROOT / str(locked_entry.get("run_root", ""))
        locked_metrics_path, locked_metrics = latest_metrics(locked_root)
        paths["locked_run_root"] = relpath(locked_root)
        paths["locked_metrics"] = relpath(locked_metrics_path) if locked_metrics_path else None
        paths["locked_summary_csv"] = relpath(plan_path(locked_entry, "summary_csv"))
        paths["locked_summary_md"] = str(locked_entry.get("summary_md"))
        checks["locked_entry_observed"] = bool(locked_entry.get("observed"))
        checks["locked_metrics_present"] = locked_metrics is not None
        summary_checks["locked"] = audit_summary_artifacts(
            entry=locked_entry,
            metrics_path=locked_metrics_path,
            expected_split="test",
            expected_sampler="sgld",
            require=locked_metrics is not None,
        )
        checks["locked_command_has_selection_source_run"] = (
            "--selection-source-run" in str(locked_entry.get("command", ""))
        )
        checks["locked_command_has_selection_source_summary"] = (
            "--selection-source-summary" in str(locked_entry.get("command", ""))
        )
        if locked_metrics is None:
            open_risk_flags.append("locked_final_test_metrics_not_observed")
        else:
            config = locked_metrics.get("config", {})
            selection = locked_metrics.get("selection_protocol", {})
            checks["locked_evaluation_split_test"] = config.get("evaluation_split") == "test"
            checks["locked_after_validation_selection"] = (
                selection.get("locked_after_validation_selection") is True
            )
            checks["locked_selection_source_run_matches"] = (
                selection.get("selection_source_run") == EXPECTED_SELECTION_RUN
            )
            checks["locked_selection_source_summary_matches"] = (
                selection.get("selection_source_summary") == EXPECTED_SELECTION_SUMMARY
            )
            checks["locked_selection_source_run_exists"] = (
                selection.get("selection_source_run_exists") is True
            )
            checks["locked_selection_source_summary_exists"] = (
                selection.get("selection_source_summary_exists") is True
            )
            for name in [
                "locked_evaluation_split_test",
                "locked_after_validation_selection",
                "locked_selection_source_run_matches",
                "locked_selection_source_summary_matches",
                "locked_selection_source_run_exists",
                "locked_selection_source_summary_exists",
            ]:
                if checks.get(name) is not True:
                    risk_flags.append(f"{name}_failed")
            risk_flags.extend(
                required_summary_failures("locked_summary", summary_checks["locked"])
            )
        for name in [
            "locked_command_has_selection_source_run",
            "locked_command_has_selection_source_summary",
        ]:
            if checks.get(name) is not True:
                risk_flags.append(f"{name}_failed")

    config_mismatches = compare_locked_config(validation_metrics, locked_metrics)
    if config_mismatches:
        risk_flags.append("locked_final_test_config_mismatch_with_validation_selection")

    return {
        "locked_final_test_protocol_audit_ready": not risk_flags,
        "plan_json": relpath(plan_json),
        "validation_entry": VALIDATION_ENTRY,
        "locked_entry": LOCKED_ENTRY,
        "checks": checks,
        "paths": paths,
        "summary_expected_comparisons": EXPECTED_COMPARISONS,
        "summary_required_columns": SUMMARY_REQUIRED_COLUMNS,
        "summary_checks": summary_checks,
        "config_comparison_keys": LOCKED_CONFIG_KEYS,
        "config_mismatches": config_mismatches,
        "risk_flags": risk_flags,
        "open_risk_flags": open_risk_flags,
        "interpretation": {
            "validation_selection_observed": checks.get("validation_metrics_present") is True,
            "locked_final_test_observed": checks.get("locked_metrics_present") is True,
            "missing_locked_final_test_is_open_blocker_not_a_protocol_mismatch": (
                "locked_final_test_metrics_not_observed" in open_risk_flags
            ),
            "locked_final_test_must_match_validation_config_except_split": True,
            "validation_summary_artifacts_observed": not required_summary_failures(
                "validation_summary", summary_checks.get("validation", {})
            ),
            "future_locked_summary_required_when_metrics_observed": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["locked_final_test_protocol_audit_ready"] else "not ready"
    lines = [
        "# Locked Final-Test Protocol Audit",
        "",
        "This generated audit checks that the held-out validation-selected CIFAR",
        "SGLD direct row and the future locked final-test row are linked by an",
        "explicit selection source and by matching config keys except for the",
        "evaluation split.",
        "",
        f"Audit status: {status}.",
        f"Validation entry: `{payload['validation_entry']}`.",
        f"Locked final-test entry: `{payload['locked_entry']}`.",
        "",
        "## Paths",
        "",
    ]
    for key, value in payload["paths"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks", "", "| Check | Pass |", "| --- | ---: |"])
    for key, value in sorted(payload["checks"].items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Summary Artifact Checks", ""])
    lines.append(
        "The validation summary is required now. The locked summary is required "
        "as soon as locked metrics are observed."
    )
    lines.extend(["", "| Entry | Check | Value |", "| --- | --- | ---: |"])
    for entry_label, summary in sorted(payload["summary_checks"].items()):
        for key, value in sorted(summary.items()):
            lines.append(f"| {entry_label} | {key} | `{value}` |")
    lines.extend(["", "## Config Mismatches", ""])
    if payload["config_mismatches"]:
        lines.extend(f"- {key}" for key in payload["config_mismatches"])
    else:
        lines.append("- none")
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
            "This file is generated by `scripts/audit_locked_final_test_protocol.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_audit(args.plan_json)
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "locked_final_test_protocol_audit_ready": payload[
                    "locked_final_test_protocol_audit_ready"
                ],
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
