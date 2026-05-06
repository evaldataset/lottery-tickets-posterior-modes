#!/usr/bin/env python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "validation_test_usage_policy_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "validation_test_usage_policy_audit.md"
VALIDATION_SELECTED_RUN_ROOT = (
    ROOT
    / "runs"
    / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3"
)
VALIDATION_SELECTED_SUMMARY_MD = (
    ROOT
    / "docs"
    / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3.md"
)
LOCKED_FINAL_TEST_RUN_ROOT = (
    ROOT
    / "runs"
    / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3"
)
LOCKED_FINAL_TEST_SUMMARY_MD = (
    ROOT
    / "docs"
    / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3.md"
)


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def line_hits(path: Path, patterns: list[str]) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    hits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if any(pattern in line for pattern in patterns):
            hits.append({"line": lineno, "text": line.strip()[:180]})
    return hits


def build_audit() -> dict[str, Any]:
    data_path = ROOT / "src" / "lottery" / "data.py"
    data_text = data_path.read_text(encoding="utf-8")
    run_scripts = sorted((ROOT / "scripts").glob("run_*.py"))

    test_usage_rows: list[dict[str, Any]] = []
    for path in run_scripts:
        script_text = path.read_text(encoding="utf-8")
        hits = line_hits(
            path,
            [
                "test_loader",
                "bundle.test_loader",
                "evaluate(",
                "logits_matrix(",
                "feature_matrix(",
            ],
        )
        test_hits = [
            hit
            for hit in hits
            if "test_loader" in hit["text"] or "bundle.test_loader" in hit["text"]
        ]
        if test_hits:
            validation_split_supported = (
                "--validation-fraction" in script_text
                and "--evaluation-split" in script_text
                and "val_loader" in script_text
            )
            test_usage_rows.append(
                {
                    "path": relpath(path),
                    "test_loader_hit_count": len(test_hits),
                    "validation_split_supported": validation_split_supported,
                    "first_hits": test_hits[:8],
                }
            )
    validation_configurable_rows = [
        row for row in test_usage_rows if row["validation_split_supported"]
    ]
    validation_unsupported_rows = [
        row for row in test_usage_rows if not row["validation_split_supported"]
    ]

    val_terms = ["val_loader", "validation_loader", "validation_split", "validation_fraction"]
    dataset_has_validation_loader = any(term in data_text for term in val_terms)
    bundle_match = re.search(
        r"class DatasetBundle:\n(?P<body>.*?)(?=\n\n)",
        data_text,
        flags=re.S,
    )
    dataset_bundle_fields = (
        re.findall(
            r"^\s+([a-zA-Z_][a-zA-Z0-9_]*):",
            bundle_match.group("body"),
            flags=re.M,
        )
        if bundle_match
        else []
    )
    first_subset_option_available = all(
        snippet in data_text
        for snippet in [
            'if strategy == "first":',
            "return list(range(count))",
        ]
    )
    first_n_subset_default_detected = 'subset_strategy: str = "first"' in data_text
    subset_default_rows: list[dict[str, Any]] = []
    for path in run_scripts:
        hits = line_hits(path, ['--subset-strategy", choices=["first", "seeded"], default="first"'])
        if hits:
            subset_default_rows.append(
                {
                    "path": relpath(path),
                    "first_default_hit_count": len(hits),
                    "first_hits": hits[:4],
                }
            )
    if subset_default_rows:
        first_n_subset_default_detected = True
    seeded_subset_option_detected = '"seeded"' in data_text and "torch.randperm" in data_text
    digits_scaler_fit_on_train = "scaler.fit_transform(x_train)" in data_text and (
        "scaler.transform(x_test)" in data_text
    )
    validation_selected_observed = (
        VALIDATION_SELECTED_SUMMARY_MD.exists()
        and any(VALIDATION_SELECTED_RUN_ROOT.glob("*/metrics.json"))
    )
    locked_final_test_observed = (
        LOCKED_FINAL_TEST_SUMMARY_MD.exists()
        and any(LOCKED_FINAL_TEST_RUN_ROOT.glob("*/metrics.json"))
    )

    open_risk_flags: list[str] = []
    warning_flags: list[str] = []
    if not dataset_has_validation_loader:
        open_risk_flags.append("dataset_bundle_has_no_validation_loader")
    elif not validation_selected_observed:
        open_risk_flags.append("validation_loader_available_but_publishable_rerun_missing")
    if test_usage_rows and validation_unsupported_rows:
        open_risk_flags.append("experiment_scripts_repeatedly_use_test_loader")
    elif test_usage_rows:
        warning_flags.append("test_loader_eval_paths_retained_but_validation_configurable")
    if validation_unsupported_rows:
        open_risk_flags.append("test_loader_scripts_without_validation_split_support")
    if first_n_subset_default_detected:
        open_risk_flags.append("torchvision_first_n_subset_default_still_available")
    if not locked_final_test_observed:
        open_risk_flags.append("locked_final_test_rerun_not_observed")

    risk_flags: list[str] = []
    if not data_path.exists():
        risk_flags.append("data_module_missing")
    if not run_scripts:
        risk_flags.append("run_scripts_missing")
    if not digits_scaler_fit_on_train:
        risk_flags.append("digits_scaler_train_only_fit_not_detected")

    return {
        "validation_test_usage_policy_audit_ready": not risk_flags,
        "data_module": relpath(data_path),
        "dataset_bundle_fields": dataset_bundle_fields,
        "dataset_has_validation_loader": dataset_has_validation_loader,
        "digits_scaler_fit_on_train_only_detected": digits_scaler_fit_on_train,
        "torchvision_first_n_subset_detected": first_n_subset_default_detected,
        "torchvision_first_subset_option_available": first_subset_option_available,
        "first_subset_default_rows": subset_default_rows,
        "torchvision_seeded_subset_option_detected": seeded_subset_option_detected,
        "run_script_count": len(run_scripts),
        "test_loader_script_count": len(test_usage_rows),
        "validation_configurable_test_loader_script_count": len(
            validation_configurable_rows
        ),
        "validation_unsupported_test_loader_script_count": len(
            validation_unsupported_rows
        ),
        "test_loader_usage_rows": test_usage_rows,
        "validation_unsupported_test_loader_usage_rows": validation_unsupported_rows,
        "validation_selected_cifar_rerun_observed": validation_selected_observed,
        "locked_final_test_rerun_observed": locked_final_test_observed,
        "validation_selected_summary_md": relpath(VALIDATION_SELECTED_SUMMARY_MD),
        "locked_final_test_summary_md": relpath(LOCKED_FINAL_TEST_SUMMARY_MD),
        "open_risk_flags": open_risk_flags,
        "warning_flags": warning_flags,
        "risk_flags": risk_flags,
        "interpretation": {
            "no_data_leakage_seen_in_digits_scaler": digits_scaler_fit_on_train,
            "validation_loader_supported_by_shared_bundle": dataset_has_validation_loader,
            "validation_selected_cifar_rerun_observed": validation_selected_observed,
            "locked_final_test_rerun_still_required": not locked_final_test_observed,
            "test_metrics_are_diagnostic_until_locked_final_test": bool(test_usage_rows)
            and not locked_final_test_observed,
            "some_test_loader_scripts_support_validation_split": bool(
                validation_configurable_rows
            ),
            "some_test_loader_scripts_still_lack_validation_split": bool(
                validation_unsupported_rows
            ),
            "seeded_subset_option_available_for_publishable_subset_rows": (
                seeded_subset_option_detected
            ),
            "first_n_subset_is_legacy_explicit_only": (
                first_subset_option_available and not first_n_subset_default_detected
            ),
            "all_test_loader_scripts_are_validation_configurable": (
                bool(test_usage_rows) and not validation_unsupported_rows
            ),
        },
        "recommended_next_steps": [
            "Use DatasetBundle.val_loader with --evaluation-split val for hyperparameter/model-selection diagnostics.",
            "Keep paper-supporting scripts validation-configurable when adding new evaluation paths.",
            "Run the locked final-test SGLD row once after validation selection and keep validation/test rows separate in paper tables.",
            "Mark existing test-reported sweep rows as falsification diagnostics rather than unbiased benchmark estimates.",
            "Keep --subset-strategy first as an explicit legacy/debug option only; default publishable subset evidence should remain seeded.",
        ],
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["validation_test_usage_policy_audit_ready"] else "not ready"
    lines = [
        "# Validation/Test Usage Policy Audit",
        "",
        "This generated audit records the current selection/evaluation split",
        "policy. It is intended to keep test-set peeking risk visible until",
        "key rows are rerun with validation-selected locked configurations.",
        "",
        f"Current status: {status}.",
        "",
        "## Summary",
        "",
        f"- Dataset module: `{payload['data_module']}`",
        f"- DatasetBundle fields: {', '.join(payload['dataset_bundle_fields'])}",
        f"- Shared validation loader present: `{payload['dataset_has_validation_loader']}`",
        f"- Digits scaler fit only on train split detected: `{payload['digits_scaler_fit_on_train_only_detected']}`",
        f"- Torchvision first-N subset default detected: `{payload['torchvision_first_n_subset_detected']}`",
        f"- Torchvision first-N subset option available for legacy/debug use: `{payload['torchvision_first_subset_option_available']}`",
        f"- Torchvision seeded subset option detected: `{payload['torchvision_seeded_subset_option_detected']}`",
        f"- Run scripts scanned: {payload['run_script_count']}",
        f"- Run scripts with test-loader usage: {payload['test_loader_script_count']}",
        "- Test-loader scripts with validation/evaluation split support: "
        f"{payload['validation_configurable_test_loader_script_count']}",
        "- Test-loader scripts still lacking validation/evaluation split support: "
        f"{payload['validation_unsupported_test_loader_script_count']}",
        f"- Validation-selected CIFAR SGLD rerun observed: `{payload['validation_selected_cifar_rerun_observed']}`",
        f"- Locked final-test SGLD rerun observed: `{payload['locked_final_test_rerun_observed']}`",
        "",
        "## Open Risk Flags",
        "",
    ]
    if payload["open_risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    else:
        lines.append("- none")

    lines.extend(["", "## Warning Flags", ""])
    if payload["warning_flags"]:
        lines.extend(f"- {flag}" for flag in payload["warning_flags"])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Scripts Using Test Loader",
            "",
            "| Script | Hits | Validation split support | First evidence lines |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for row in payload["test_loader_usage_rows"]:
        evidence = "<br>".join(
            f"L{hit['line']}: `{hit['text']}`" for hit in row["first_hits"]
        )
        lines.append(
            f"| `{row['path']}` | {row['test_loader_hit_count']} | "
            f"{row['validation_split_supported']} | {evidence} |"
        )
    if not payload["test_loader_usage_rows"]:
        lines.append("| none | 0 | False | none |")

    lines.extend(
        [
            "",
            "## Scripts With First-N Subset Default",
            "",
            "| Script | Hits | First evidence lines |",
            "| --- | ---: | --- |",
        ]
    )
    for row in payload["first_subset_default_rows"]:
        evidence = "<br>".join(
            f"L{hit['line']}: `{hit['text']}`" for hit in row["first_hits"]
        )
        lines.append(
            f"| `{row['path']}` | {row['first_default_hit_count']} | {evidence} |"
        )
    if not payload["first_subset_default_rows"]:
        lines.append("| none | 0 | none |")

    lines.extend(["", "## Recommended Next Steps", ""])
    lines.extend(f"- {step}" for step in payload["recommended_next_steps"])
    lines.extend(["", "## Audit Risk Flags", ""])
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This file is generated by `scripts/audit_validation_test_usage_policy.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_audit()
    write_json(payload, DEFAULT_OUT_JSON)
    write_markdown(payload, DEFAULT_OUT_MD)
    print(
        json.dumps(
            {
                "validation_test_usage_policy_audit_ready": payload[
                    "validation_test_usage_policy_audit_ready"
                ],
                "test_loader_script_count": payload["test_loader_script_count"],
                "open_risk_flags": payload["open_risk_flags"],
                "risk_flags": payload["risk_flags"],
                "out_json": relpath(DEFAULT_OUT_JSON),
                "out_md": relpath(DEFAULT_OUT_MD),
            }
        )
    )


if __name__ == "__main__":
    main()
