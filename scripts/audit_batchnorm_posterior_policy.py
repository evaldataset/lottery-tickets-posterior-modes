#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "batchnorm_posterior_policy_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "batchnorm_posterior_policy_audit.md"


POLICIES = [
    {
        "path": "src/lottery/sgld.py",
        "family": "SGLD",
        "policy": "train_mode_stateful",
        "expected": ["model.train()", "state_to_cpu(model)"],
        "risk": "sgld_updates_batchnorm_buffers_during_sampling",
    },
    {
        "path": "src/lottery/sghmc.py",
        "family": "SGHMC",
        "policy": "train_mode_stateful",
        "expected": ["model.train()", "state_to_cpu(model)"],
        "risk": "sghmc_updates_batchnorm_buffers_during_sampling",
    },
    {
        "path": "src/lottery/cyclical_sgld.py",
        "family": "cyclical SGLD",
        "policy": "train_mode_stateful",
        "expected": ["model.train()", "state_to_cpu(model)"],
        "risk": "cyclical_sgld_updates_batchnorm_buffers_during_sampling",
    },
    {
        "path": "src/lottery/swag.py",
        "family": "SWAG",
        "policy": "train_mode_snapshot",
        "expected": ["model.train()", "state_to_cpu(model)"],
        "risk": "swag_snapshots_include_training_mode_batchnorm_buffers",
    },
    {
        "path": "src/lottery/diag_laplace.py",
        "family": "diagonal Laplace",
        "policy": "train_mode_fisher",
        "expected": ["model.train()", "state_to_cpu(model)"],
        "risk": "diag_laplace_fisher_uses_training_mode_batchnorm",
    },
    {
        "path": "src/lottery/hmc.py",
        "family": "full HMC",
        "policy": "train_mode_stateful",
        "expected": ["model.train()", "state_to_cpu(model)"],
        "risk": "full_hmc_updates_batchnorm_buffers_during_sampling",
    },
    {
        "path": "src/lottery/lowrank_laplace.py",
        "family": "low-rank Laplace",
        "policy": "configurable_batchnorm_mode_default_eval",
        "expected": ['batchnorm_mode: str = "eval"', "_set_batchnorm_mode"],
        "risk": "",
    },
    {
        "path": "src/lottery/subspace_hmc.py",
        "family": "subspace HMC",
        "policy": "configurable_batchnorm_mode_default_eval",
        "expected": ['batchnorm_mode: str = "eval"', "_set_batchnorm_mode"],
        "risk": "",
    },
    {
        "path": "src/lottery/block_laplace.py",
        "family": "block/joint Laplace",
        "policy": "eval_mode_curvature",
        "expected": ["model.eval()", "state_to_cpu(model)"],
        "risk": "",
    },
    {
        "path": "src/lottery/full_laplace.py",
        "family": "full Laplace",
        "policy": "eval_mode_curvature",
        "expected": ["model.eval()", "state_to_cpu(model)"],
        "risk": "",
    },
    {
        "path": "src/lottery/head_laplace.py",
        "family": "head Laplace",
        "policy": "eval_mode_curvature",
        "expected": ["model.eval()", "state_to_cpu(model)"],
        "risk": "",
    },
    {
        "path": "src/lottery/kfac_laplace.py",
        "family": "KFAC Laplace",
        "policy": "eval_mode_curvature",
        "expected": ["model.eval()", "state_to_cpu(model)"],
        "risk": "",
    },
]

SCRIPT_POLICIES = [
    {
        "path": "scripts/run_mode_ticket_distribution_probe.py",
        "expected": ['"--lowrank-laplace-batchnorm-mode"', "default=\"eval\""],
        "meaning": "direct LowRank Laplace runs expose a BN mode knob defaulting to eval.",
    },
    {
        "path": "scripts/run_mode_ticket_distribution_probe.py",
        "expected": [
            '"--posterior-bn-policy"',
            '"freeze"',
            '"recalibrate"',
            '"dense_buffers"',
        ],
        "meaning": (
            "direct SGLD/SGHMC/cyclical-SGLD runs expose freeze, "
            "recalibration, and dense-buffer BatchNorm ablation knobs."
        ),
    },
    {
        "path": "scripts/run_sgld_movement_grid.py",
        "expected": ['"--lowrank-laplace-batchnorm-mode"', "default=\"eval\""],
        "meaning": "movement LowRank Laplace runs expose a BN mode knob defaulting to eval.",
    },
    {
        "path": "scripts/run_subspace_hmc_probe.py",
        "expected": ['"--hmc-batchnorm-mode"', "default=\"eval\""],
        "meaning": "subspace-HMC runs expose a BN mode knob defaulting to eval.",
    },
]


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def check_policy(row: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / str(row["path"])
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = [snippet for snippet in row["expected"] if snippet not in text]
    return {
        **row,
        "exists": path.exists(),
        "missing_expected_snippets": missing,
        "policy_detected": path.exists() and not missing,
    }


def build_audit() -> dict[str, Any]:
    model_text = (ROOT / "src" / "lottery" / "models.py").read_text(encoding="utf-8")
    rows = [check_policy(row) for row in POLICIES]
    script_rows = [check_policy(row) for row in SCRIPT_POLICIES]
    missing = [
        f"{row['path']}::{snippet}"
        for row in rows + script_rows
        for snippet in row["missing_expected_snippets"]
    ]
    open_risk_flags = [
        str(row["risk"])
        for row in rows
        if row.get("risk") and row.get("policy_detected")
    ]
    risk_flags: list[str] = []
    if missing:
        risk_flags.append("batchnorm_policy_expected_snippet_missing")
    if "nn.BatchNorm2d" not in model_text:
        risk_flags.append("resnet_batchnorm_modules_not_detected")
    return {
        "batchnorm_policy_audit_ready": not risk_flags,
        "batchnorm_module_occurrences_in_models_py": model_text.count("nn.BatchNorm2d"),
        "rows": rows,
        "script_rows": script_rows,
        "open_risk_flags": open_risk_flags,
        "risk_flags": risk_flags,
        "interpretation": {
            "resnet_uses_batchnorm": "nn.BatchNorm2d" in model_text,
            "train_mode_posterior_samplers_are_documented_open_risk": bool(open_risk_flags),
            "lowrank_and_subspace_paths_have_eval_default_knob": all(
                row["policy_detected"]
                for row in script_rows
                if "LowRank Laplace" in row["meaning"]
                or "subspace-HMC" in row["meaning"]
            ),
            "direct_sgld_family_bn_ablation_knobs_available": any(
                row["policy_detected"]
                and "freeze, recalibration, and dense-buffer" in row["meaning"]
                for row in script_rows
            ),
            "exact_laplace_paths_use_eval_mode": all(
                row["policy_detected"]
                for row in rows
                if row["policy"] == "eval_mode_curvature"
            ),
        },
        "recommended_next_experiments": [
            "Run selected CIFAR SGLD/cSGLD rows with --posterior-bn-policy freeze.",
            "Run selected CIFAR SGLD/cSGLD rows with --posterior-bn-policy recalibrate.",
            "Run selected CIFAR rows with --posterior-bn-policy dense_buffers to bound buffer-only effects.",
        ],
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["batchnorm_policy_audit_ready"] else "not ready"
    lines = [
        "# BatchNorm Posterior Policy Audit",
        "",
        "This generated audit records how posterior and covariance code paths",
        "handle BatchNorm-equipped CIFAR ResNets. It is a policy audit, not a",
        "replacement for the recommended BatchNorm ablation experiments.",
        "",
        f"Current status: {status}.",
        "",
        "## Summary",
        "",
        f"- BatchNorm module occurrences in `src/lottery/models.py`: {payload['batchnorm_module_occurrences_in_models_py']}",
        "- Train-mode stochastic samplers remain an open implementation risk",
        "  because saved `state_dict`s include BatchNorm buffers.",
        "- Direct SGLD/SGHMC/cyclical-SGLD probes now expose BatchNorm",
        "  freeze/recalibrate/dense-buffer ablation knobs, but the reruns",
        "  have not been observed yet.",
        "- Low-rank Laplace and subspace-HMC paths expose eval-default BatchNorm",
        "  mode knobs.",
        "- Exact Laplace curvature paths audited here use eval mode.",
        "",
        "## Posterior/Covariance Code Paths",
        "",
        "| Family | File | Policy | Detected | Open risk | Missing snippets |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in payload["rows"]:
        missing = ", ".join(row["missing_expected_snippets"]) or "none"
        risk = row.get("risk") or "none"
        lines.append(
            f"| {row['family']} | `{row['path']}` | {row['policy']} | "
            f"{row['policy_detected']} | {risk} | {missing} |"
        )
    lines.extend(
        [
            "",
            "## Orchestration Knobs",
            "",
            "| File | Detected | Meaning | Missing snippets |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in payload["script_rows"]:
        missing = ", ".join(row["missing_expected_snippets"]) or "none"
        lines.append(
            f"| `{row['path']}` | {row['policy_detected']} | "
            f"{row['meaning']} | {missing} |"
        )
    lines.extend(["", "## Open Risk Flags", ""])
    if payload["open_risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["open_risk_flags"])
    else:
        lines.append("- none")
    lines.extend(["", "## Recommended Next Experiments", ""])
    lines.extend(f"- {item}" for item in payload["recommended_next_experiments"])
    lines.extend(["", "## Audit Risk Flags", ""])
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This file is generated by `scripts/audit_batchnorm_posterior_policy.py`.",
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
                "batchnorm_policy_audit_ready": payload["batchnorm_policy_audit_ready"],
                "open_risk_flags": payload["open_risk_flags"],
                "risk_flags": payload["risk_flags"],
                "out_json": relpath(DEFAULT_OUT_JSON),
                "out_md": relpath(DEFAULT_OUT_MD),
            }
        )
    )


if __name__ == "__main__":
    main()
