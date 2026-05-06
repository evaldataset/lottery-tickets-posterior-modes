#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "runs" / "fake_cifar10_validation_bn_policy_smoke"
SUMMARY_CSV = ROOT / "runs" / "fake_cifar10_validation_bn_policy_smoke_summary.csv"
SUMMARY_MD = ROOT / "docs" / "fake_cifar10_validation_bn_policy_smoke.md"
FULL_VALIDATION_SUMMARY_MD = (
    ROOT
    / "docs"
    / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3.md"
)
FULL_VALIDATION_SUMMARY_CSV = (
    ROOT
    / "runs"
    / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3_summary.csv"
)
FULL_VALIDATION_RUN_ROOT = (
    ROOT
    / "runs"
    / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3"
)
DEFAULT_OUT_JSON = ROOT / "runs" / "validation_bn_smoke_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "validation_bn_smoke_audit.md"


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def latest_metrics_path() -> Path | None:
    paths = sorted(RUN_ROOT.glob("*/metrics.json"))
    return paths[-1] if paths else None


def build_audit() -> dict[str, Any]:
    metrics_path = latest_metrics_path()
    risk_flags: list[str] = []
    full_validation_observed = (
        FULL_VALIDATION_SUMMARY_MD.exists()
        and FULL_VALIDATION_SUMMARY_CSV.exists()
        and any(FULL_VALIDATION_RUN_ROOT.glob("*/metrics.json"))
    )
    # Drop full_cifar_bn_ablation_rerun_not_observed once the validation_bn
    # rerun plan reports that every bn_* entry has been observed. The plan
    # JSON is the single source-of-truth for full-CIFAR BN observation, so
    # this audit must mirror that state rather than hardcode the flag.
    bn_plan_path = ROOT / "runs" / "validation_bn_rerun_plan.json"
    bn_full_cifar_ablation_observed = False
    if bn_plan_path.exists():
        try:
            with bn_plan_path.open(encoding="utf-8") as f:
                plan_payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            plan_payload = {}
        bn_entries = [
            entry
            for entry in plan_payload.get("entries", [])
            if isinstance(entry, dict)
            and str(entry.get("name", "")).startswith("bn_")
        ]
        bn_full_cifar_ablation_observed = bool(bn_entries) and all(
            entry.get("observed") for entry in bn_entries
        )
    open_risk_flags: list[str] = []
    if not bn_full_cifar_ablation_observed:
        open_risk_flags.append("full_cifar_bn_ablation_rerun_not_observed")
    if not full_validation_observed:
        open_risk_flags.insert(0, "full_cifar_validation_selected_rerun_not_observed")
    metrics: dict[str, Any] = {}
    config: dict[str, Any] = {}
    mask_artifact_path: Path | None = None

    if metrics_path is None:
        risk_flags.append("validation_bn_smoke_metrics_missing")
    else:
        metrics = load_json(metrics_path)
        config = dict(metrics.get("config", {}))
        artifact = metrics.get("mask_artifacts", {}) or {}
        if artifact.get("path"):
            mask_artifact_path = ROOT / str(artifact["path"])

    checks = {
        "run_root_exists": RUN_ROOT.exists(),
        "metrics_present": metrics_path is not None,
        "summary_csv_present": SUMMARY_CSV.exists(),
        "summary_md_present": SUMMARY_MD.exists(),
        "dataset_fake_cifar": config.get("dataset") == "fake-cifar10",
        "model_resnet20": config.get("model") == "resnet20",
        "validation_fraction_positive": float(config.get("validation_fraction", 0.0) or 0.0)
        > 0.0,
        "evaluation_split_val": config.get("evaluation_split") == "val",
        "subset_strategy_seeded": config.get("subset_strategy") == "seeded",
        "posterior_bn_policy_recalibrate": (
            config.get("posterior_sampler_config", {}).get("posterior_bn_policy")
            == "recalibrate"
        ),
        "bn_recalibration_batches_recorded": (
            config.get("posterior_sampler_config", {}).get("bn_recalibration_batches")
            == 1
        ),
        "reference_val_size_positive": int(config.get("reference_val_size", 0) or 0) > 0,
        "mask_artifact_present": mask_artifact_path is not None
        and mask_artifact_path.exists(),
        "smoke_uses_mask_artifact_schema": bool(
            (metrics.get("mask_artifacts", {}) or {}).get("schema_version") == 1
        ),
    }
    for name, passed in checks.items():
        if not passed:
            risk_flags.append(f"{name}_failed")

    if SUMMARY_MD.exists():
        summary_text = SUMMARY_MD.read_text(encoding="utf-8")
        for phrase, flag in [
            ("held-out validation logits", "summary_validation_wording_missing"),
            ("Evaluation split: `val`", "summary_eval_split_missing"),
            ("subset strategy `seeded`", "summary_subset_strategy_missing"),
        ]:
            if phrase not in summary_text:
                risk_flags.append(flag)
    else:
        risk_flags.append("summary_markdown_missing")

    return {
        "validation_bn_smoke_ready": not risk_flags,
        "run_root": relpath(RUN_ROOT),
        "latest_metrics": relpath(metrics_path) if metrics_path else None,
        "summary_csv": relpath(SUMMARY_CSV),
        "summary_md": relpath(SUMMARY_MD),
        "mask_artifact": relpath(mask_artifact_path) if mask_artifact_path else None,
        "checks": checks,
        "config": {
            key: config.get(key)
            for key in [
                "dataset",
                "model",
                "validation_fraction",
                "evaluation_split",
                "subset_strategy",
                "reference_train_size",
                "reference_val_size",
                "reference_test_size",
            ]
        },
        "posterior_sampler_config": config.get("posterior_sampler_config", {}),
        "open_risk_flags": open_risk_flags,
        "risk_flags": risk_flags,
        "interpretation": {
            "validation_split_path_smoked": checks["evaluation_split_val"]
            and checks["reference_val_size_positive"],
            "batchnorm_recalibration_path_smoked": checks[
                "posterior_bn_policy_recalibrate"
            ],
            "seeded_subset_path_smoked": checks["subset_strategy_seeded"],
            "mask_artifact_path_smoked": checks["mask_artifact_present"],
            "full_cifar_validation_selected_rerun_observed": full_validation_observed,
            "full_cifar_reruns_still_required": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["validation_bn_smoke_ready"] else "not ready"
    lines = [
        "# Validation/BatchNorm Smoke Audit",
        "",
        "This generated audit checks the small fake-CIFAR ResNet smoke that",
        "exercises the new validation split, seeded subset, BatchNorm",
        "recalibration, and mask-artifact paths. It does not replace the",
        "required full CIFAR reruns.",
        "",
        f"Current status: {status}.",
        "",
        "## Inputs",
        "",
        f"- Run root: `{payload['run_root']}`",
        f"- Latest metrics: `{payload['latest_metrics']}`",
        f"- Summary CSV: `{payload['summary_csv']}`",
        f"- Summary Markdown: `{payload['summary_md']}`",
        f"- Mask artifact: `{payload['mask_artifact']}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- {name}: `{passed}`" for name, passed in payload["checks"].items()
    )
    lines.extend(
        [
            "",
            "## Full CIFAR Follow-up",
            "",
            "- validation-selected SGLD rerun observed: "
            f"`{payload['interpretation']['full_cifar_validation_selected_rerun_observed']}`",
            "- further full CIFAR reruns still required: "
            f"`{payload['interpretation']['full_cifar_reruns_still_required']}`",
        ]
    )
    lines.extend(["", "## Open Risk Flags", ""])
    lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    lines.extend(["", "## Audit Risk Flags", ""])
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This file is generated by `scripts/audit_validation_bn_smoke.py`.",
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
                "validation_bn_smoke_ready": payload["validation_bn_smoke_ready"],
                "risk_flags": payload["risk_flags"],
                "open_risk_flags": payload["open_risk_flags"],
                "latest_metrics": payload["latest_metrics"],
                "out_json": relpath(DEFAULT_OUT_JSON),
                "out_md": relpath(DEFAULT_OUT_MD),
            }
        )
    )


if __name__ == "__main__":
    main()
