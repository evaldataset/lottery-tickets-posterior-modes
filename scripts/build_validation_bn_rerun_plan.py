#!/usr/bin/env python
from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "validation_bn_rerun_plan.json"
DEFAULT_OUT_MD = ROOT / "docs" / "validation_bn_rerun_plan.md"
VALIDATION_SELECT_RUN = (
    "runs/"
    "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3"
)
VALIDATION_SELECT_SUMMARY = (
    "docs/"
    "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3.md"
)


BASE_DIRECT = [
    "CUDA_VISIBLE_DEVICES=0",
    ".venv/bin/python",
    "scripts/run_mode_ticket_distribution_probe.py",
    "--dataset",
    "cifar10",
    "--model",
    "resnet20",
    "--resnet-width",
    "16",
    "--seeds",
    "0,1,2,3,4",
    "--epochs",
    "30",
    "--rewind-epochs",
    "1",
    "--imp-rounds",
    "5",
    "--imp-epochs",
    "30",
    "--imp-final-epochs",
    "30",
    "--prune-fraction",
    "0.30",
    "--batch-size",
    "512",
    "--lr",
    "0.1",
    "--lr-schedule",
    "cosine",
    "--weight-decay",
    "5e-4",
    "--augment",
    "--cluster-pca-dim",
    "20",
    "--sliced-projections",
    "128",
    "--validation-fraction",
    "0.1",
    "--subset-strategy",
    "seeded",
]

SGLD = [
    "--posterior-sampler",
    "sgld",
    "--samples",
    "10",
    "--sgld-steps",
    "200",
    "--sgld-burn-in",
    "50",
    "--sgld-sample-every",
    "10",
    "--sgld-lr",
    "1e-6",
]

CSGLD = [
    "--posterior-sampler",
    "cyclical-sgld",
    "--samples",
    "5",
    "--posterior-chains",
    "3",
    "--posterior-chain-init",
    "dense",
    "--sgld-steps",
    "400",
    "--sgld-burn-in",
    "50",
    "--sgld-sample-every",
    "10",
    "--sgld-lr",
    "1e-6",
    "--sgld-likelihood-scale",
    "mean",
    "--csgld-cycle-length",
    "50",
    "--csgld-sample-phase-start",
    "0.5",
]

LOWRANK128 = [
    "--posterior-sampler",
    "lowrank-laplace",
    "--samples",
    "10",
    "--lowrank-laplace-scale",
    "1e-2",
    "--lowrank-laplace-rank",
    "128",
    "--lowrank-laplace-power-iterations",
    "1",
    "--lowrank-laplace-oversample",
    "32",
    "--lowrank-laplace-fisher-batches",
    "20",
    "--lowrank-laplace-hessian-batches",
    "2",
    "--lowrank-laplace-prior-precision",
    "1e-2",
    "--lowrank-laplace-damping",
    "1e-6",
    "--lowrank-laplace-batchnorm-mode",
    "eval",
]

JOINTDIAG = [
    "--posterior-sampler",
    "jointdiag-laplace",
    "--samples",
    "5",
    "--jointdiag-laplace-scale",
    "1e-6",
    "--jointdiag-laplace-prior-precision",
    "1e-2",
    "--jointdiag-laplace-damping",
    "1e-5",
    "--jointdiag-laplace-hessian-batches",
    "1",
    "--jointdiag-laplace-max-parameters",
    "40000",
]


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def shell_join(parts: list[str]) -> str:
    out = []
    for part in parts:
        if "=" in part and not part.startswith("--") and part.split("=", 1)[0].isidentifier():
            out.append(part)
        else:
            out.append(shlex.quote(part))
    return " ".join(out)


def run_entry(
    *,
    name: str,
    priority: str,
    purpose: str,
    criticism: str,
    sampler_args: list[str],
    evaluation_split: str,
    out_dir: str,
    bn_policy: str | None = None,
    save_artifacts: bool = False,
    expected_hours: str,
    selection_source_run: str | None = None,
    selection_source_summary: str | None = None,
) -> dict[str, Any]:
    command = [
        *BASE_DIRECT,
        "--evaluation-split",
        evaluation_split,
        *sampler_args,
    ]
    if bn_policy is not None:
        command.extend(["--posterior-bn-policy", bn_policy])
        if bn_policy == "recalibrate":
            command.extend(["--bn-recalibration-batches", "20"])
    if save_artifacts:
        command.extend(["--save-mask-artifacts", "--save-state-artifacts"])
    if selection_source_run:
        command.extend(["--selection-source-run", selection_source_run])
    if selection_source_summary:
        command.extend(["--selection-source-summary", selection_source_summary])
    command.extend(["--out-dir", out_dir])
    summarize = [
        ".venv/bin/python",
        "scripts/summarize_mode_ticket_distribution_probe.py",
        "--run-root",
        out_dir,
        "--out-md",
        f"docs/{Path(out_dir).name}.md",
        "--out-csv",
        f"runs/{Path(out_dir).name}_summary.csv",
    ]
    run_root = ROOT / out_dir
    summary_csv = ROOT / "runs" / f"{Path(out_dir).name}_summary.csv"
    summary_md = ROOT / "docs" / f"{Path(out_dir).name}.md"
    files_present = (
        run_root.exists() and summary_csv.exists() and summary_md.exists()
    )
    # Strengthen observed: not just "files exist" but "the run has actually
    # produced a complete five-seed metrics.json with a partial-seed-summary
    # status of complete". This prevents an in-flight or killed run from
    # silently counting toward observed_entry_count.
    metrics_present = False
    seed_count_match = False
    seed_status_complete = False
    if files_present:
        metrics_paths = sorted(run_root.glob("*/metrics.json"))
        if metrics_paths:
            metrics_present = True
            run_dir = metrics_paths[-1].parent
            partial = run_dir / "partial_seed_summaries.json"
            if partial.exists():
                try:
                    payload = json.loads(partial.read_text(encoding="utf-8"))
                    completed = int(payload.get("completed_seed_count", 0))
                    total = int(payload.get("total_seed_count", 0))
                    seed_count_match = (
                        completed == total and total >= 5
                    )
                    seed_status_complete = (
                        payload.get("status") == "complete"
                    )
                except (json.JSONDecodeError, ValueError):
                    pass
    observed = (
        files_present
        and metrics_present
        and seed_count_match
        # status "complete" is the strict gate; "running" with 5/5 seeds is
        # treated as incomplete because the distribution-comparison stage may
        # have been killed (cf. AUDIT.md 2026-05-27 C3 TinyCNN case).
        and seed_status_complete
    )
    return {
        "name": name,
        "priority": priority,
        "purpose": purpose,
        "criticism_addressed": criticism,
        "evaluation_split": evaluation_split,
        "posterior_bn_policy": bn_policy or "sampler_default",
        "saves_mask_artifacts": save_artifacts,
        "selection_source_run": selection_source_run,
        "selection_source_summary": selection_source_summary,
        "expected_wall_clock": expected_hours,
        "run_root": out_dir,
        "summary_csv": relpath(summary_csv),
        "summary_md": relpath(summary_md),
        "command": shell_join(command),
        "summarize_command": shell_join(summarize),
        "observation_checks": {
            "files_present": files_present,
            "metrics_json_present": metrics_present,
            "seed_count_matches": seed_count_match,
            "run_status_complete": seed_status_complete,
        },
        "observed": observed,
    }


def build_plan() -> dict[str, Any]:
    entries = [
        run_entry(
            name="validation_select_sgld_full_cifar",
            priority="P0",
            purpose="Select/report diagnostics on a held-out validation split before final test reporting.",
            criticism="test-set peeking during direct mode/ticket row selection",
            sampler_args=SGLD,
            evaluation_split="val",
            out_dir="runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_validation_select_sgld_r5_p0p3",
            expected_hours="GPU: roughly comparable to the existing full CIFAR direct SGLD row",
        ),
        run_entry(
            name="locked_final_test_sgld_full_cifar",
            priority="P0",
            purpose="Evaluate the locked SGLD direct row on the test split once after validation selection.",
            criticism="unbiased final test estimate missing after validation selection",
            sampler_args=SGLD,
            evaluation_split="test",
            out_dir="runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_locked_test_sgld_r5_p0p3",
            expected_hours="GPU: roughly comparable to the existing full CIFAR direct SGLD row",
            selection_source_run=VALIDATION_SELECT_RUN,
            selection_source_summary=VALIDATION_SELECT_SUMMARY,
        ),
    ]
    for sampler_name, sampler_args in [("sgld", SGLD), ("csgld", CSGLD)]:
        for policy in ["freeze", "recalibrate", "dense_buffers"]:
            entries.append(
                run_entry(
                    name=f"bn_{policy}_{sampler_name}_full_cifar",
                    priority="P1",
                    purpose=f"Bound whether {sampler_name} direct failure is a BatchNorm-buffer artifact.",
                    criticism="posterior sampler implementation may drive the result through BN running buffers",
                    sampler_args=sampler_args,
                    evaluation_split="test",
                    out_dir=(
                        "runs/"
                        f"cifar10_resnet20_long30_rewind1_mode_ticket_distribution_{sampler_name}_bn_{policy}_r5_p0p3"
                    ),
                    bn_policy=policy,
                    expected_hours="GPU: full CIFAR direct-row rerun",
                )
            )
    for name, sampler_args, out_dir in [
        (
            "saved_artifacts_csgld_multichain",
            CSGLD,
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_multichain_saved_artifacts_r5_p0p3",
        ),
        (
            "saved_artifacts_lowrank128",
            LOWRANK128,
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_saved_artifacts_r5_p0p3",
        ),
        (
            "saved_artifacts_jointdiag",
            JOINTDIAG,
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_saved_artifacts_r5_p0p3",
        ),
    ]:
        entries.append(
            run_entry(
                name=name,
                priority="P1",
                purpose="Save raw masks/states so direct distribution rows can be audited at seed level.",
                criticism="pooled direct-row p-values are descriptive without saved per-seed artifacts",
                sampler_args=sampler_args,
                evaluation_split="test",
                out_dir=out_dir,
                save_artifacts=True,
                expected_hours="GPU: full CIFAR direct-row rerun plus artifact storage",
            )
        )

    source = (ROOT / "scripts" / "run_mode_ticket_distribution_probe.py").read_text(
        encoding="utf-8"
    )
    required_snippets = [
        "--validation-fraction",
        "--evaluation-split",
        "--subset-strategy",
        "--posterior-bn-policy",
        "freeze",
        "recalibrate",
        "dense_buffers",
        "--save-mask-artifacts",
        "--save-state-artifacts",
    ]
    missing_snippets = [snippet for snippet in required_snippets if snippet not in source]
    observed_names = [entry["name"] for entry in entries if entry["observed"]]
    open_risk_flags = []
    if not any(entry["name"] == "validation_select_sgld_full_cifar" and entry["observed"] for entry in entries):
        open_risk_flags.append("validation_selected_cifar_rerun_not_observed")
    if not any(entry["name"].startswith("bn_") and entry["observed"] for entry in entries):
        open_risk_flags.append("bn_policy_cifar_ablation_not_observed")
    if not any(entry["name"].startswith("saved_artifacts_") and entry["observed"] for entry in entries):
        open_risk_flags.append("seed_level_saved_artifact_reruns_not_observed")
    risk_flags = []
    if missing_snippets:
        risk_flags.append("required_cli_knobs_missing")
    return {
        "validation_bn_rerun_plan_ready": not risk_flags,
        "entry_count": len(entries),
        "observed_entry_count": len(observed_names),
        "observed_entries": observed_names,
        "required_snippets": required_snippets,
        "missing_snippets": missing_snippets,
        "open_risk_flags": open_risk_flags,
        "risk_flags": risk_flags,
        "entries": entries,
        "interpretation": {
            "commands_are_locked_before_rerun": not risk_flags,
            "validation_selection_rerun_still_required": "validation_selected_cifar_rerun_not_observed"
            in open_risk_flags,
            "batchnorm_ablation_rerun_still_required": "bn_policy_cifar_ablation_not_observed"
            in open_risk_flags,
            "seed_level_artifact_rerun_still_required": "seed_level_saved_artifact_reruns_not_observed"
            in open_risk_flags,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["validation_bn_rerun_plan_ready"] else "not ready"
    lines = [
        "# Validation and BatchNorm Rerun Plan",
        "",
        "This generated plan fixes the commands needed to close the remaining",
        "validation/test protocol, BatchNorm policy, and direct-row seed-level",
        "artifact blockers. It is a command plan, not evidence that the GPU",
        "reruns have completed.",
        "",
        f"Current status: {status}.",
        "",
        "## Summary",
        "",
        f"- Plan entries: {payload['entry_count']}",
        f"- Observed entries: {payload['observed_entry_count']}",
        f"- Open risk flags: {', '.join(payload['open_risk_flags']) or 'none'}",
        "",
        "## Commands",
        "",
    ]
    for entry in payload["entries"]:
        lines.extend(
            [
                f"### {entry['priority']} {entry['name']}",
                "",
                f"- Purpose: {entry['purpose']}",
                f"- Criticism addressed: {entry['criticism_addressed']}",
                f"- Evaluation split: `{entry['evaluation_split']}`",
                f"- BN policy: `{entry['posterior_bn_policy']}`",
                f"- Saves mask/state artifacts: `{entry['saves_mask_artifacts']}`",
                f"- Observed: `{entry['observed']}`",
                "",
                "```bash",
                entry["command"],
                entry["summarize_command"],
                "```",
                "",
            ]
        )
    lines.extend(["## Audit Risk Flags", ""])
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This file is generated by `scripts/build_validation_bn_rerun_plan.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_plan()
    write_json(payload, DEFAULT_OUT_JSON)
    write_markdown(payload, DEFAULT_OUT_MD)
    print(
        json.dumps(
            {
                "validation_bn_rerun_plan_ready": payload[
                    "validation_bn_rerun_plan_ready"
                ],
                "entry_count": payload["entry_count"],
                "observed_entry_count": payload["observed_entry_count"],
                "open_risk_flags": payload["open_risk_flags"],
                "risk_flags": payload["risk_flags"],
                "out_json": relpath(DEFAULT_OUT_JSON),
                "out_md": relpath(DEFAULT_OUT_MD),
            }
        )
    )


if __name__ == "__main__":
    main()
