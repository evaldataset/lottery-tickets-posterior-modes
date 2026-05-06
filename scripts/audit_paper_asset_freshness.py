#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "paper_asset_freshness_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "paper_asset_freshness_audit.md"

EXPECTED_FIGURE_REFS = {
    "figures/gate1_controls.pdf",
    "figures/cifar_movement.pdf",
    "figures/cifar_trajectory.pdf",
}
EXPECTED_TABLE_REFS = {"tables/statistical_summary.tex"}

GENERATED_OUTPUTS = [
    ("paper_stats_json", ROOT / "runs" / "paper_stats.json", 1000),
    ("paper_stats_markdown", ROOT / "docs" / "paper_stats.md", 1000),
    ("statistical_summary_table", ROOT / "paper" / "tables" / "statistical_summary.tex", 1000),
    ("gate1_controls_pdf", ROOT / "paper" / "figures" / "gate1_controls.pdf", 1000),
    ("gate1_controls_png", ROOT / "paper" / "figures" / "gate1_controls.png", 1000),
    ("cifar_movement_pdf", ROOT / "paper" / "figures" / "cifar_movement.pdf", 1000),
    ("cifar_movement_png", ROOT / "paper" / "figures" / "cifar_movement.png", 1000),
    ("cifar_trajectory_pdf", ROOT / "paper" / "figures" / "cifar_trajectory.pdf", 1000),
    ("cifar_trajectory_png", ROOT / "paper" / "figures" / "cifar_trajectory.png", 1000),
]

DIRECT_FIGURE_SOURCES = [
    ROOT / "runs" / "mnist_gate1_full_sweep.csv",
    ROOT / "runs" / "fashion_gate1_full_sweep.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_sgld_movement_selected_r5_p0p3_summary.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_sghmc_movement_selected_r5_p0p3_summary.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_csgld_movement_selected_r5_p0p3_summary.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_swag_movement_selected20_lr1e3_r5_p0p3_summary.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_diag_laplace_movement_selected_r5_p0p3_summary.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_kfac_laplace_movement_selected_r5_p0p3_summary.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_lowrank_laplace_movement_selected_r5_p0p3_summary.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_lowrank32_laplace_movement_selected_r5_p0p3_summary.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_trajectory_probe_r5_p0p3_v2_summary.csv",
    ROOT / "runs" / "cifar10_resnet20_long30_rewind1_trajectory_probe_r5_p0p3_v2_aggregate_summary.csv",
]

EXPECTED_TABLE_LABELS = {
    "tab:cifar-movement-stats",
    "tab:cifar-head-laplace-stats",
    "tab:cifar-block-laplace-stats",
    "tab:cifar-subspace-hmc-stats",
    "tab:mode-ticket-equivalence-audit",
    "tab:direct-mode-ticket-distribution",
    "tab:cifar-calibration-ood-stats",
    "tab:cifar-trajectory-stats",
    "tab:cifar-trajectory-mask-training",
    "tab:cifar-residual-imp-process-learned-subspace",
}

EXPECTED_STATS_SECTIONS = {
    "gate1",
    "movement",
    "head_laplace",
    "block_laplace",
    "subspace_hmc",
    "mode_distribution_equivalence",
    "direct_mode_ticket_distribution",
    "calibration_ood",
    "trajectory",
    "trajectory_mask_training",
    "residual_imp_process_learned_subspace_pairs",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    return parser.parse_args()


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def record(path: Path, role: str, min_bytes: int = 1) -> dict[str, Any]:
    out: dict[str, Any] = {
        "role": role,
        "path": relpath(path),
        "exists": path.exists(),
        "min_bytes": min_bytes,
    }
    if path.exists():
        out.update(
            {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "mtime_utc": iso_mtime(path),
                "size_ok": path.stat().st_size >= min_bytes,
            }
        )
    else:
        out["size_ok"] = False
    return out


def parse_paper_refs() -> dict[str, Any]:
    text = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    figure_refs = set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text))
    table_refs = set(re.findall(r"\\input\{(tables/[^}]+)\}", text))
    return {
        "figure_refs": sorted(figure_refs),
        "table_refs": sorted(table_refs),
        "expected_figure_refs": sorted(EXPECTED_FIGURE_REFS),
        "expected_table_refs": sorted(EXPECTED_TABLE_REFS),
        "unexpected_figure_refs": sorted(figure_refs - EXPECTED_FIGURE_REFS),
        "missing_figure_refs": sorted(EXPECTED_FIGURE_REFS - figure_refs),
        "unexpected_table_refs": sorted(table_refs - EXPECTED_TABLE_REFS),
        "missing_table_refs": sorted(EXPECTED_TABLE_REFS - table_refs),
    }


def discover_stats_sources() -> list[Path]:
    script = (ROOT / "scripts" / "build_paper_stats.py").read_text(encoding="utf-8")
    quoted = set(re.findall(r'"([^"]+)"', script))
    paths: set[Path] = set()
    for value in quoted:
        if value.endswith(".csv"):
            paths.add(ROOT / "runs" / value)
        elif value.startswith(("cifar10_", "digits_", "mnist_", "fashion_")) and "/" not in value:
            candidate = ROOT / "runs" / value
            if candidate.exists():
                paths.update(candidate.glob("**/metrics.json"))
            summary = ROOT / "runs" / f"{value}_summary.csv"
            if summary.exists():
                paths.add(summary)
    for pattern in [
        "mnist_gate1_full_*/*/metrics.json",
        "fashion_gate1_full_*/*/metrics.json",
    ]:
        paths.update((ROOT / "runs").glob(pattern))
    return sorted(paths, key=relpath)


def output_content_checks(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    checks: dict[str, Any] = {}
    if suffix == ".pdf":
        with path.open("rb") as f:
            checks["pdf_header_ok"] = f.read(4) == b"%PDF"
    elif suffix == ".png":
        with path.open("rb") as f:
            checks["png_header_ok"] = f.read(8) == b"\x89PNG\r\n\x1a\n"
    elif suffix == ".tex":
        text = path.read_text(encoding="utf-8")
        labels = set(re.findall(r"\\label\{([^}]+)\}", text))
        checks["table_label_count"] = len(labels)
        checks["missing_expected_table_labels"] = sorted(EXPECTED_TABLE_LABELS - labels)
    elif path.name == "paper_stats.json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        checks["stats_section_count"] = len(payload) if isinstance(payload, dict) else 0
        checks["missing_expected_stats_sections"] = sorted(
            EXPECTED_STATS_SECTIONS - set(payload)
        ) if isinstance(payload, dict) else sorted(EXPECTED_STATS_SECTIONS)
    return checks


def build_payload() -> dict[str, Any]:
    risk_flags: list[str] = []
    scripts = [
        ROOT / "scripts" / "build_paper_stats.py",
        ROOT / "scripts" / "build_paper_figures.py",
        ROOT / "paper" / "main.tex",
    ]
    source_paths = sorted(
        {*DIRECT_FIGURE_SOURCES, *discover_stats_sources(), *scripts},
        key=relpath,
    )
    source_records = [record(path, "source") for path in source_paths]
    output_records = []
    for role, path, min_bytes in GENERATED_OUTPUTS:
        row = record(path, role, min_bytes)
        if path.exists():
            row.update(output_content_checks(path))
        output_records.append(row)

    missing_sources = [row["path"] for row in source_records if row["exists"] is not True]
    missing_outputs = [row["path"] for row in output_records if row["exists"] is not True]
    undersized_outputs = [
        row["path"] for row in output_records if row.get("size_ok") is not True
    ]
    if missing_sources:
        risk_flags.append("paper_asset_source_missing")
    if missing_outputs:
        risk_flags.append("paper_generated_asset_missing")
    if undersized_outputs:
        risk_flags.append("paper_generated_asset_too_small")

    refs = parse_paper_refs()
    if (
        refs["unexpected_figure_refs"]
        or refs["missing_figure_refs"]
        or refs["unexpected_table_refs"]
        or refs["missing_table_refs"]
    ):
        risk_flags.append("paper_generated_asset_reference_mismatch")

    mtimes = [
        (ROOT / row["path"]).stat().st_mtime
        for row in source_records
        if row["exists"] is True
    ]
    max_source_mtime = max(mtimes) if mtimes else 0.0
    stale_outputs = []
    for row in output_records:
        if row["exists"] is True and (ROOT / row["path"]).stat().st_mtime + 1e-6 < max_source_mtime:
            stale_outputs.append(row["path"])
    if stale_outputs:
        risk_flags.append("paper_generated_asset_stale_vs_sources")

    content_failures = []
    for row in output_records:
        if row.get("pdf_header_ok") is False:
            content_failures.append(f"{row['path']}:pdf_header")
        if row.get("png_header_ok") is False:
            content_failures.append(f"{row['path']}:png_header")
        if row.get("missing_expected_table_labels"):
            content_failures.append(f"{row['path']}:table_labels")
        if row.get("missing_expected_stats_sections"):
            content_failures.append(f"{row['path']}:stats_sections")
    if content_failures:
        risk_flags.append("paper_generated_asset_content_check_failed")

    return {
        "paper_asset_freshness_audit_ready": not risk_flags,
        "risk_flags": risk_flags,
        "source_observation_mode": "static_literal_scan_plus_known_outputs",
        "source_count": len(source_records),
        "generated_output_count": len(output_records),
        "max_source_mtime_utc": (
            datetime.fromtimestamp(max_source_mtime, tz=timezone.utc).isoformat()
            if max_source_mtime
            else ""
        ),
        "stale_outputs": stale_outputs,
        "missing_sources": missing_sources,
        "missing_outputs": missing_outputs,
        "undersized_outputs": undersized_outputs,
        "content_failures": content_failures,
        "paper_references": refs,
        "sources": source_records,
        "generated_outputs": output_records,
        "interpretation": {
            "checks_paper_referenced_generated_assets": True,
            "checks_generator_source_hashes": True,
            "does_not_recompute_experiments": True,
            "does_not_replace_metric_audits": True,
        },
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["paper_asset_freshness_audit_ready"] else "not ready"
    lines = [
        "# Paper Asset Freshness Audit",
        "",
        "This generated audit checks that paper-referenced generated figures",
        "and tables exist, are nontrivial files, match the references in",
        "`paper/main.tex`, and are not older than their observed generator",
        "scripts and source summaries.",
        "",
        f"Audit status: {status}.",
        f"Source observation mode: `{payload['source_observation_mode']}`.",
        f"Source count: {payload['source_count']}.",
        f"Generated output count: {payload['generated_output_count']}.",
        f"Max source mtime UTC: `{payload['max_source_mtime_utc']}`.",
        "",
        "## Paper References",
        "",
        f"- Figure refs: {', '.join(f'`{item}`' for item in payload['paper_references']['figure_refs'])}",
        f"- Table refs: {', '.join(f'`{item}`' for item in payload['paper_references']['table_refs'])}",
        "",
        "## Generated Outputs",
        "",
        "| Role | Path | Bytes | SHA256 | mtime UTC |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in payload["generated_outputs"]:
        lines.append(
            "| {role} | `{path}` | {bytes} | `{sha}` | `{mtime}` |".format(
                role=row["role"],
                path=row["path"],
                bytes=row.get("bytes", "missing"),
                sha=row.get("sha256", "missing"),
                mtime=row.get("mtime_utc", "missing"),
            )
        )
    lines.extend(
        [
            "",
            "## Risk Flags",
            "",
        ]
    )
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Freshness Interpretation",
            "",
            "- This audit is a generated-asset consistency gate, not a substitute for experiment reruns.",
            "- It closes the local paper figure/table freshness risk for currently referenced assets.",
            "- A future edit to paper claims or source summaries must rerun `make paper-asset-freshness-audit`.",
            "",
            "This file is generated by `scripts/audit_paper_asset_freshness.py`.",
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
                "paper_asset_freshness_audit_ready": payload[
                    "paper_asset_freshness_audit_ready"
                ],
                "risk_flags": payload["risk_flags"],
                "source_count": payload["source_count"],
                "generated_output_count": payload["generated_output_count"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )


if __name__ == "__main__":
    main()
