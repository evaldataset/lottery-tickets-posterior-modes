#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import hashlib
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-package-mode",
        action="store_true",
        help=(
            "Verify an extracted public release package. This mode skips checks "
            "for the outer release tarball and archive-smoke sidecars, which "
            "cannot be included inside the tarball without self-reference."
        ),
    )
    return parser.parse_args()


def fail(message: str) -> None:
    raise AssertionError(message)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: str, min_size: int = 1) -> None:
    full_path = ROOT / path
    if not full_path.exists():
        fail(f"missing required file: {path}")
    if full_path.stat().st_size < min_size:
        fail(f"required file is too small: {path}")


def locked_final_test_observed() -> bool:
    """True iff the locked final-test SGLD CIFAR row produced metrics.

    Sourced from locked_final_test_protocol_audit.json.interpretation. Used to gate hardcoded anti-overclaim assertions
    in this verifier: before the locked run exists, every aggregator audit MUST advertise the matching open-risk flag;
    once observed, the flag MUST be absent.
    """
    p = ROOT / "runs" / "locked_final_test_protocol_audit.json"
    if not p.exists():
        return False
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    interpretation = data.get("interpretation", {}) if isinstance(data, dict) else {}
    return interpretation.get("locked_final_test_observed") is True


def external_receipts_registry_available() -> bool:
    """True iff the mutable receipt registry is present.

    The registry is intentionally excluded from the public release archive
    (it records the archive's own SHA), so inside --release-package-mode the
    receipt-conditioned anti-overclaim assertions are skipped in both
    directions rather than evaluated against a missing file.
    """
    return (ROOT / "docs" / "external_validation_receipts.json").exists()


def external_receipt_observed(name: str) -> bool:
    """True iff docs/external_validation_receipts.json marks `name` observed.

    Mirrors locked_final_test_observed: before a receipt is recorded against the current archive SHA / source commit,
    every aggregator audit MUST advertise the matching open-risk flag; once the receipt updater has written an observed
    entry, the flag MUST be absent.
    """
    p = ROOT / "docs" / "external_validation_receipts.json"
    if not p.exists():
        return False
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    receipts = data.get("receipts", {}) if isinstance(data, dict) else {}
    entry = receipts.get(name, {}) if isinstance(receipts, dict) else {}
    return isinstance(entry, dict) and entry.get("status") == "observed"


def bn_ablation_observed() -> bool:
    """True iff every bn_* entry in validation_bn_rerun_plan.json is observed.

    Once all six full-CIFAR BN policy rows produced metrics, the source-of-truth plan drops
    `bn_policy_cifar_ablation_not_observed` / `full_cifar_bn_ablation_rerun_not_observed`. Downstream verifier rules
    must mirror that state.
    """
    p = ROOT / "runs" / "validation_bn_rerun_plan.json"
    if not p.exists():
        return False
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    bn_entries = [
        entry
        for entry in (data.get("entries") if isinstance(data, dict) else []) or []
        if isinstance(entry, dict) and str(entry.get("name", "")).startswith("bn_")
    ]
    return bool(bn_entries) and all(entry.get("observed") for entry in bn_entries)


def saved_artifact_reruns_observed() -> bool:
    """True iff every saved_artifacts_* entry in validation_bn_rerun_plan.json is observed."""
    p = ROOT / "runs" / "validation_bn_rerun_plan.json"
    if not p.exists():
        return False
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    saved_entries = [
        entry
        for entry in (data.get("entries") if isinstance(data, dict) else []) or []
        if isinstance(entry, dict)
        and str(entry.get("name", "")).startswith("saved_artifacts_")
    ]
    return bool(saved_entries) and all(entry.get("observed") for entry in saved_entries)


def finite(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def rows_matching(rows: list[dict[str, Any]], **criteria: Any) -> list[dict[str, Any]]:
    matched = []
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            matched.append(row)
    return matched


def require_stats_sections(stats: dict[str, Any]) -> None:
    required_sections = [
        "gate1",
        "movement",
        "head_laplace",
        "block_laplace",
        "subspace_hmc",
        "mode_distribution_equivalence",
        "direct_mode_ticket_distribution",
        "calibration_ood",
        "trajectory_mask_training",
        "variational_pruning",
        "trajectory_residual",
        "residual_anatomy_global",
        "residual_predictor_mask",
        "residual_cross_seed_transfer",
        "residual_direct_transfer",
        "residual_base_compatibility",
        "residual_base_ordering",
        "residual_stratified_controls",
        "residual_imp_process",
        "residual_imp_process_controls",
        "residual_imp_process_oracle_matched",
        "residual_imp_process_score_source",
        "residual_imp_process_round_exclusion",
        "residual_imp_process_layer_exclusion",
        "residual_imp_process_layer_exclusion_pairs",
        "residual_imp_process_tensor_score_exclusion",
        "residual_imp_process_tensor_score_exclusion_pairs",
        "residual_imp_process_projection",
        "residual_imp_process_projection_pairs",
        "residual_imp_process_posterior_projection",
        "residual_imp_process_posterior_projection_pairs",
        "residual_imp_process_learned_subspace",
        "residual_imp_process_learned_subspace_pairs",
    ]
    for section in required_sections:
        if section not in stats:
            fail(f"paper_stats.json missing section: {section}")
        if not stats[section]:
            fail(f"paper_stats.json section is empty: {section}")


def require_paper_asset_freshness_audit() -> None:
    json_path = ROOT / "runs" / "paper_asset_freshness_audit.json"
    doc_path = ROOT / "docs" / "paper_asset_freshness_audit.md"
    payload = load_json(json_path)
    if payload.get("paper_asset_freshness_audit_ready") is not True:
        fail(f"paper asset freshness audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"paper asset freshness audit has risk flags: {payload['risk_flags']}")
    if payload.get("source_observation_mode") != "static_literal_scan_plus_known_outputs":
        fail("paper asset freshness audit observation mode changed unexpectedly")
    if int(payload.get("source_count", 0)) < 20:
        fail("paper asset freshness audit observed too few source files")
    if int(payload.get("generated_output_count", 0)) != 9:
        fail("paper asset freshness audit should track exactly 9 generated outputs")
    refs = payload.get("paper_references", {})
    if set(refs.get("figure_refs", [])) != {
        "figures/gate1_controls.pdf",
        "figures/cifar_movement.pdf",
        "figures/cifar_trajectory.pdf",
    }:
        fail(f"paper asset freshness audit figure references changed: {refs}")
    if set(refs.get("table_refs", [])) != {"tables/statistical_summary.tex"}:
        fail(f"paper asset freshness audit table references changed: {refs}")
    for key in [
        "unexpected_figure_refs",
        "missing_figure_refs",
        "unexpected_table_refs",
        "missing_table_refs",
    ]:
        if refs.get(key) not in ([], None):
            fail(f"paper asset freshness audit has reference mismatch: {key}")
    if payload.get("stale_outputs") not in ([], None):
        fail(f"paper asset freshness audit found stale outputs: {payload['stale_outputs']}")
    if payload.get("missing_sources") not in ([], None):
        fail(f"paper asset freshness audit found missing sources: {payload['missing_sources']}")
    if payload.get("missing_outputs") not in ([], None):
        fail(f"paper asset freshness audit found missing outputs: {payload['missing_outputs']}")
    if payload.get("undersized_outputs") not in ([], None):
        fail(f"paper asset freshness audit found undersized outputs: {payload['undersized_outputs']}")
    if payload.get("content_failures") not in ([], None):
        fail(f"paper asset freshness audit found content failures: {payload['content_failures']}")
    outputs = payload.get("generated_outputs", [])
    if not isinstance(outputs, list):
        fail("paper asset freshness audit generated outputs should be a list")
    by_path = {str(row.get("path")): row for row in outputs if isinstance(row, dict)}
    for rel in [
        "runs/paper_stats.json",
        "docs/paper_stats.md",
        "paper/tables/statistical_summary.tex",
        "paper/figures/gate1_controls.pdf",
        "paper/figures/gate1_controls.png",
        "paper/figures/cifar_movement.pdf",
        "paper/figures/cifar_movement.png",
        "paper/figures/cifar_trajectory.pdf",
        "paper/figures/cifar_trajectory.png",
    ]:
        row = by_path.get(rel)
        if not isinstance(row, dict):
            fail(f"paper asset freshness audit missing output: {rel}")
        if row.get("exists") is not True or row.get("size_ok") is not True:
            fail(f"paper asset freshness audit output missing or small: {rel}")
        if row.get("sha256") != sha256(ROOT / rel):
            fail(f"paper asset freshness audit output hash mismatch: {rel}")
    if by_path["paper/tables/statistical_summary.tex"].get("table_label_count", 0) < 20:
        fail("paper asset freshness audit found too few generated table labels")
    if by_path["runs/paper_stats.json"].get("stats_section_count", 0) < 40:
        fail("paper asset freshness audit found too few stats sections")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Paper Asset Freshness Audit",
        "Source observation mode: `static_literal_scan_plus_known_outputs`",
        "generated-asset consistency gate",
        "scripts/audit_paper_asset_freshness.py",
    ]:
        if phrase not in text:
            fail(f"paper asset freshness audit markdown missing phrase: {phrase}")


def require_tmlr_packet_freshness_audit() -> None:
    json_path = ROOT / "runs" / "tmlr_packet_freshness_audit.json"
    doc_path = ROOT / "docs" / "tmlr_packet_freshness_audit.md"
    payload = load_json(json_path)
    if payload.get("tmlr_packet_freshness_audit_ready") is not True:
        fail(
            "TMLR packet freshness audit is not ready: "
            f"{payload.get('risk_flags')}"
        )
    if payload.get("risk_flags"):
        fail(
            f"TMLR packet freshness audit has blocking risk flags: "
            f"{payload['risk_flags']}"
        )
    artifacts = payload.get("artifacts", {})
    expected_artifacts = {"paste_payload", "final_gate", "submission_packet"}
    if set(artifacts.keys()) != expected_artifacts:
        fail(
            "TMLR packet freshness audit tracked artifact set drifted: "
            f"{sorted(artifacts.keys())}"
        )
    text = doc_path.read_text(encoding="utf-8")
    for phrase in [
        "TMLR Packet Freshness Audit",
        "must be rebuilt against the",
        "This file is generated by",
        "`scripts/audit_tmlr_packet_freshness.py`",
    ]:
        if phrase not in text:
            fail(
                f"TMLR packet freshness audit markdown missing phrase: {phrase}"
            )


def require_paper_pdf_freshness_audit() -> None:
    json_path = ROOT / "runs" / "paper_pdf_freshness_audit.json"
    doc_path = ROOT / "docs" / "paper_pdf_freshness_audit.md"
    payload = load_json(json_path)
    if payload.get("paper_pdf_freshness_audit_ready") is not True:
        fail(
            "paper PDF freshness audit is not ready: "
            f"{payload.get('risk_flags')}"
        )
    if payload.get("risk_flags"):
        fail(
            f"paper PDF freshness audit has risk flags: {payload['risk_flags']}"
        )
    pdfs = payload.get("pdfs", [])
    expected_paths = {
        "paper/main.pdf",
        "paper/main_submission.pdf",
        "paper/iclr_submission.pdf",
        "paper/neurips_submission.pdf",
    }
    observed_paths = {entry.get("path") for entry in pdfs}
    if observed_paths != expected_paths:
        fail(
            "paper PDF freshness audit tracked PDF set drifted: "
            f"{sorted(observed_paths)}"
        )
    for entry in pdfs:
        if entry.get("exists") is not True:
            fail(
                f"paper PDF freshness audit missing PDF: {entry.get('path')}"
            )
        if entry.get("stale_vs_source") is not False:
            fail(
                "paper PDF freshness audit reports stale PDF: "
                f"{entry.get('path')}"
            )
    text = doc_path.read_text(encoding="utf-8")
    for phrase in [
        "Paper PDF Freshness Audit",
        "This file is generated by",
        "`scripts/audit_paper_pdf_freshness.py`",
    ]:
        if phrase not in text:
            fail(f"paper PDF freshness audit markdown missing phrase: {phrase}")


def require_gate1(stats: dict[str, Any]) -> None:
    labels = {row["label"] for row in stats["gate1"]}
    required_labels = {
        "MNIST: posterior - random",
        "MNIST: posterior - chain-start",
        "MNIST: dense magnitude - posterior",
        "Fashion-MNIST: posterior - random",
        "Fashion-MNIST: posterior - chain-start",
        "Fashion-MNIST: dense magnitude - posterior",
    }
    missing = sorted(required_labels - labels)
    if missing:
        fail(f"Gate1 summary missing labels: {missing}")
    for row in stats["gate1"]:
        if row["label"].endswith("posterior - chain-start"):
            if abs(float(row["mean"])) > 0.005:
                fail(f"posterior-chain Gate1 delta is not near control: {row}")
        if row["label"].endswith("dense magnitude - posterior"):
            if float(row["mean"]) <= 0.0:
                fail(f"dense magnitude should dominate posterior masks: {row}")


def require_movement(stats: dict[str, Any]) -> None:
    rows = stats["movement"]
    lowrank_expectations = {
        "LowRankLap": (
            16,
            ROOT
            / "runs"
            / "cifar10_resnet20_long30_rewind1_lowrank_laplace_movement_selected_r5_p0p3",
        ),
        "LowRank32Lap": (
            32,
            ROOT
            / "runs"
            / "cifar10_resnet20_long30_rewind1_lowrank32_laplace_movement_selected_r5_p0p3",
        ),
        "LowRank64Lap": (
            64,
            ROOT
            / "runs"
            / "cifar10_resnet20_long30_rewind1_lowrank64_laplace_movement_selected_r5_p0p3",
        ),
        "LowRank128Lap": (
            128,
            ROOT
            / "runs"
            / "cifar10_resnet20_long30_rewind1_lowrank128_laplace_movement_selected_r5_p0p3",
        ),
    }
    for sampler in lowrank_expectations:
        lowrank_rows = [
            row
            for row in rows
            if row.get("sampler") == sampler and abs(float(row.get("scale")) - 1e-2) < 1e-12
        ]
        if not lowrank_rows:
            fail(f"{sampler} movement row at scale 1e-2 is missing")
        row = lowrank_rows[0]
        if int(row["posterior_minus_chain"]["n"]) != 5:
            fail(f"{sampler} movement row must be five-seed")
        if float(row["posterior_minus_chain"]["mean"]) >= 0.0:
            fail(f"{sampler} should not beat chain-start support")
        if float(row["post_chain"]["mean"]) >= 0.80:
            fail(f"{sampler} scale 1e-2 should move away from chain-start support")
        if float(row["sample_accuracy"]["mean"]) <= 0.87:
            fail(f"{sampler} scale 1e-2 sample accuracy is unexpectedly low")
    for sampler, (expected_rank, root) in lowrank_expectations.items():
        metrics = sorted(root.glob("*/metrics.json"))
        if len(metrics) != 5:
            fail(f"{sampler} raw metrics should contain five seeds, found {len(metrics)}")
        for path in metrics:
            payload = load_json(path)
            for row in payload.get("rows", []):
                if int(row.get("lowrank_laplace_positive_rank", 0)) != expected_rank:
                    fail(
                        f"{sampler} did not retain {expected_rank} positive directions in {path}"
                    )


def require_block_laplace(stats: dict[str, Any]) -> None:
    rows = rows_matching(
        stats["block_laplace"],
        sampler="BlockDiagLap",
        block="blockdiag:11blocks<=5000",
        scale=0.0001,
    )
    if not rows:
        fail("BlockDiagLap selected CIFAR row is missing")
    row = rows[0]
    if int(row["block_posterior_minus_chain"]["n"]) != 5:
        fail("BlockDiagLap row must be five-seed")
    if float(row["parameter_count"]["mean"]) < 22_000:
        fail("BlockDiagLap row should cover at least 22k parameters")
    if float(row["block_posterior_minus_chain"]["mean"]) >= 0.0:
        fail("BlockDiagLap block posterior should not beat chain-start support")
    if float(row["global_posterior_minus_chain"]["mean"]) >= 0.01:
        fail("BlockDiagLap global posterior gain should remain small")
    if float(row["global_rewind_minus_posterior"]["mean"]) <= 0.02:
        fail("BlockDiagLap rewind support should remain closer than posterior")
    if float(row["sample_accuracy"]["mean"]) <= 0.87:
        fail("BlockDiagLap samples should preserve useful accuracy")
    root = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_blockdiag_laplace_selected_r5_p0p3"
    )
    metrics = sorted(root.glob("*/metrics.json"))
    if len(metrics) != 5:
        fail(f"BlockDiagLap raw metrics should contain five seeds, found {len(metrics)}")
    for path in metrics:
        payload = load_json(path)
        config = payload.get("block_laplace", {})
        if not config.get("independent_block_diagonal"):
            fail(f"BlockDiagLap raw metrics missing independent blockdiag flag: {path}")
        if len(config.get("block_names", [])) != 11:
            fail(f"BlockDiagLap raw metrics should contain 11 block names: {path}")
    wider_rows = rows_matching(
        stats["block_laplace"],
        sampler="BlockDiagLap",
        block="blockdiag:16blocks<=10000",
        scale=1e-05,
    )
    if not wider_rows:
        fail("BlockDiagLap max10k CIFAR row is missing")
    row = wider_rows[0]
    if int(row["block_posterior_minus_chain"]["n"]) != 5:
        fail("BlockDiagLap max10k row must be five-seed")
    if float(row["parameter_count"]["mean"]) < 68_000:
        fail("BlockDiagLap max10k row should cover at least 68k parameters")
    if float(row["block_posterior_minus_chain"]["mean"]) >= 0.0:
        fail("BlockDiagLap max10k block posterior should not beat chain-start support")
    if float(row["global_posterior_minus_chain"]["mean"]) >= 0.005:
        fail("BlockDiagLap max10k global posterior gain should remain tiny")
    if float(row["global_rewind_minus_posterior"]["mean"]) <= 0.025:
        fail("BlockDiagLap max10k rewind support should remain closer than posterior")
    if float(row["global_post_chain"]["mean"]) >= 0.80:
        fail("BlockDiagLap max10k samples should move from chain-start support")
    if float(row["sample_accuracy"]["mean"]) <= 0.875:
        fail("BlockDiagLap max10k samples should preserve useful accuracy")
    wider_root = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_blockdiag_laplace_max10k_selected_r5_p0p3"
    )
    metrics = sorted(wider_root.glob("*/metrics.json"))
    if len(metrics) != 5:
        fail(f"BlockDiagLap max10k raw metrics should contain five seeds, found {len(metrics)}")
    for path in metrics:
        payload = load_json(path)
        config = payload.get("block_laplace", {})
        if not config.get("independent_block_diagonal"):
            fail(f"BlockDiagLap max10k raw metrics missing independent blockdiag flag: {path}")
        if int(config.get("max_parameters", 0)) != 10_000:
            fail(f"BlockDiagLap max10k raw metrics should use max_parameters=10000: {path}")
        if len(config.get("block_names", [])) != 16:
            fail(f"BlockDiagLap max10k raw metrics should contain 16 block names: {path}")
    jointdiag_rows = rows_matching(
        stats["block_laplace"],
        sampler="JointDiagLap",
        block="jointdiag:8groups<=10000",
        scale=1e-05,
    )
    if not jointdiag_rows:
        fail("JointDiagLap max10k CIFAR row is missing")
    row = jointdiag_rows[0]
    if int(row["block_posterior_minus_chain"]["n"]) != 5:
        fail("JointDiagLap max10k row must be five-seed")
    if float(row["parameter_count"]["mean"]) < 68_000:
        fail("JointDiagLap max10k row should cover at least 68k parameters")
    if float(row["block_posterior_minus_chain"]["mean"]) >= 0.0:
        fail("JointDiagLap max10k block posterior should not beat chain-start support")
    if float(row["global_posterior_minus_chain"]["mean"]) >= 0.005:
        fail("JointDiagLap max10k global posterior gain should remain tiny")
    if float(row["global_rewind_minus_posterior"]["mean"]) <= 0.025:
        fail("JointDiagLap max10k rewind support should remain closer than posterior")
    if float(row["global_post_chain"]["mean"]) >= 0.80:
        fail("JointDiagLap max10k samples should move from chain-start support")
    if float(row["sample_accuracy"]["mean"]) <= 0.875:
        fail("JointDiagLap max10k samples should preserve useful accuracy")
    jointdiag_root = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_jointdiag_laplace_max10k_selected_r5_p0p3"
    )
    metrics = sorted(jointdiag_root.glob("*/metrics.json"))
    if len(metrics) != 5:
        fail(f"JointDiagLap max10k raw metrics should contain five seeds, found {len(metrics)}")
    for path in metrics:
        payload = load_json(path)
        config = payload.get("block_laplace", {})
        if not config.get("joint_block_diagonal"):
            fail(f"JointDiagLap max10k raw metrics missing joint blockdiag flag: {path}")
        if int(config.get("max_parameters", 0)) != 10_000:
            fail(f"JointDiagLap max10k raw metrics should use max_parameters=10000: {path}")
        if len(config.get("block_names", [])) != 16:
            fail(f"JointDiagLap max10k raw metrics should contain 16 block names: {path}")
        if len(config.get("block_groups", [])) != 8:
            fail(f"JointDiagLap max10k raw metrics should contain eight joint groups: {path}")
    jointdiag20_rows = rows_matching(
        stats["block_laplace"],
        sampler="JointDiagLap",
        block="jointdiag:6groups<=20000",
        scale=3e-06,
    )
    if not jointdiag20_rows:
        fail("JointDiagLap max20k CIFAR row is missing")
    row = jointdiag20_rows[0]
    if int(row["block_posterior_minus_chain"]["n"]) != 5:
        fail("JointDiagLap max20k row must be five-seed")
    if float(row["parameter_count"]["mean"]) < 86_000:
        fail("JointDiagLap max20k row should cover at least 86k parameters")
    if float(row["block_posterior_minus_chain"]["mean"]) >= 0.0:
        fail("JointDiagLap max20k block posterior should not beat chain-start support")
    if float(row["global_posterior_minus_chain"]["mean"]) >= 0.005:
        fail("JointDiagLap max20k global posterior gain should remain tiny")
    if float(row["global_rewind_minus_posterior"]["mean"]) <= 0.025:
        fail("JointDiagLap max20k rewind support should remain closer than posterior")
    if float(row["global_post_chain"]["mean"]) >= 0.85:
        fail("JointDiagLap max20k samples should move from chain-start support")
    if float(row["sample_accuracy"]["mean"]) <= 0.875:
        fail("JointDiagLap max20k samples should preserve useful accuracy")
    jointdiag20_root = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_jointdiag_laplace_max20k_selected_r5_p0p3"
    )
    metrics = sorted(jointdiag20_root.glob("*/metrics.json"))
    if len(metrics) != 5:
        fail(f"JointDiagLap max20k raw metrics should contain five seeds, found {len(metrics)}")
    for path in metrics:
        payload = load_json(path)
        config = payload.get("block_laplace", {})
        if not config.get("joint_block_diagonal"):
            fail(f"JointDiagLap max20k raw metrics missing joint blockdiag flag: {path}")
        if int(config.get("max_parameters", 0)) != 20_000:
            fail(f"JointDiagLap max20k raw metrics should use max_parameters=20000: {path}")
        if len(config.get("block_names", [])) != 17:
            fail(f"JointDiagLap max20k raw metrics should contain 17 block names: {path}")
        if len(config.get("block_groups", [])) != 6:
            fail(f"JointDiagLap max20k raw metrics should contain six joint groups: {path}")
    jointdiag40_rows = rows_matching(
        stats["block_laplace"],
        sampler="JointDiagLap",
        block="jointdiag:8groups<=40000",
        scale=1e-06,
    )
    if not jointdiag40_rows:
        fail("JointDiagLap max40k CIFAR row is missing")
    row = jointdiag40_rows[0]
    if int(row["block_posterior_minus_chain"]["n"]) != 5:
        fail("JointDiagLap max40k row must be five-seed")
    if float(row["parameter_count"]["mean"]) < 270_000:
        fail("JointDiagLap max40k row should cover the full weight vector")
    if float(row["block_posterior_minus_chain"]["mean"]) >= 0.0:
        fail("JointDiagLap max40k block posterior should not beat chain-start support")
    if float(row["global_posterior_minus_chain"]["mean"]) >= 0.001:
        fail("JointDiagLap max40k global posterior gain should remain non-positive or tiny")
    if float(row["global_rewind_minus_posterior"]["mean"]) <= 0.03:
        fail("JointDiagLap max40k rewind support should remain closer than posterior")
    if float(row["global_post_chain"]["mean"]) >= 0.80:
        fail("JointDiagLap max40k samples should move from chain-start support")
    if float(row["sample_accuracy"]["mean"]) <= 0.875:
        fail("JointDiagLap max40k samples should preserve useful accuracy")
    jointdiag40_root = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_jointdiag_laplace_max40k_stream_selected_r5_p0p3"
    )
    metrics = sorted(jointdiag40_root.glob("*/metrics.json"))
    if len(metrics) != 5:
        fail(f"JointDiagLap max40k raw metrics should contain five seeds, found {len(metrics)}")
    for path in metrics:
        payload = load_json(path)
        config = payload.get("block_laplace", {})
        if not config.get("joint_block_diagonal"):
            fail(f"JointDiagLap max40k raw metrics missing joint blockdiag flag: {path}")
        if not config.get("stream_joint_groups"):
            fail(f"JointDiagLap max40k raw metrics should stream joint groups: {path}")
        if int(config.get("max_parameters", 0)) != 40_000:
            fail(f"JointDiagLap max40k raw metrics should use max_parameters=40000: {path}")
        if len(config.get("block_names", [])) != 22:
            fail(f"JointDiagLap max40k raw metrics should contain 22 block names: {path}")
        if len(config.get("block_groups", [])) != 8:
            fail(f"JointDiagLap max40k raw metrics should contain eight joint groups: {path}")


def require_subspace_hmc(stats: dict[str, Any]) -> None:
    rows = stats["subspace_hmc"]
    hess32_rows = [
        row
        for row in rows
        if row.get("sampler") == "Hess32SubHMC"
        and abs(float(row.get("step")) - 3e-4) < 1e-12
    ]
    if not hess32_rows:
        fail("Hess32SubHMC selected subspace-HMC row is missing")
    row = hess32_rows[0]
    for key in [
        "posterior_minus_chain",
        "rewind_minus_posterior",
        "post_chain",
        "sample_accuracy",
        "accept_rate",
        "parameter_distance",
    ]:
        if int(row[key]["n"]) != 5:
            fail(f"Hess32SubHMC {key} summary must be five-seed")
    if abs(float(row["posterior_minus_chain"]["mean"])) >= 0.001:
        fail("Hess32SubHMC should remain practically tied to chain-start support")
    if float(row["rewind_minus_posterior"]["mean"]) <= 0.02:
        fail("Hess32SubHMC rewind control should remain closer to IMP")
    if float(row["post_chain"]["mean"]) <= 0.99:
        fail("Hess32SubHMC post-chain overlap should remain near chain-start")
    if float(row["sample_accuracy"]["mean"]) <= 0.88:
        fail("Hess32SubHMC sample accuracy is unexpectedly low")
    if float(row["accept_rate"]["mean"]) <= 0.80:
        fail("Hess32SubHMC accept rate is unexpectedly low")
    if float(row["parameter_distance"]["mean"]) <= 0.005:
        fail("Hess32SubHMC parameter movement is unexpectedly small")


def require_mode_distribution_audit(stats: dict[str, Any]) -> None:
    rows = stats["mode_distribution_equivalence"]
    if len(rows) < 150:
        fail(f"mode distribution audit has too few grouped rows: {len(rows)}")
    random_rows = [row for row in rows if row["comparison"] == "posterior-random"]
    chain_rows = [row for row in rows if row["comparison"] == "posterior-chain"]
    if len(random_rows) < 40 or len(chain_rows) < 40:
        fail("mode distribution audit is missing random or chain controls")
    random_wins = [
        row
        for row in random_rows
        if str(row.get("verdict", "")) == "posterior separates from random"
    ]
    chain_wins = [row for row in chain_rows if float(row["delta_mean"]) > 0.005]
    if len(random_wins) < 40:
        fail(f"posterior-vs-random support evidence too weak: {len(random_wins)}")
    if chain_wins:
        fail(f"posterior beats chain-start by >0.005 in audit rows: {chain_wins[:3]}")


def require_direct_mode_ticket(stats: dict[str, Any]) -> None:
    rows = stats["direct_mode_ticket_distribution"]
    required_settings = {
        "Digits MLP",
        "CIFAR full ResNet",
        "CIFAR full aligned",
        "CIFAR full weight-aligned",
        "CIFAR full cSGLD multi-chain",
        "CIFAR full cSGLD independent",
        "CIFAR full LowRank128Lap",
        "CIFAR full JointDiagLap270k",
    }
    settings = {row.get("setting") for row in rows}
    missing = sorted(required_settings - settings)
    if missing:
        fail(f"direct mode/ticket table missing settings: {missing}")
    for setting in ["Digits MLP", "CIFAR full ResNet"]:
        row = rows_matching(
            rows,
            setting=setting,
            comparison="posterior_samples_vs_tickets",
        )[0]
        if int(float(row["posterior_num_clusters"])) != 1:
            fail(f"{setting} should collapse to one mean-shift cluster")
        if float(row["posterior_effective_cluster_count"]) != 1.0:
            fail(f"{setting} should have effective cluster count 1")
        if float(row["hamming_overlap"]) >= 0.70:
            fail(f"{setting} should fail Hamming-overlap threshold")
        if float(row["logit_cka_hungarian_mean"]) <= 0.85:
            fail(f"{setting} should pass logit CKA threshold")
        if setting == "CIFAR full ResNet":
            if float(row["layer_ks_pvalue"]) >= 0.001:
                fail("full CIFAR direct row should strongly fail layer KS")
            if float(row["activation_cka_hungarian_mean"]) <= 0.85:
                fail("full CIFAR direct row should pass final-hidden activation CKA")
    full_mode_row = rows_matching(
        rows,
        setting="CIFAR full ResNet",
        comparison="posterior_modes_vs_tickets",
    )[0]
    if int(float(full_mode_row["left_count"])) != 1:
        fail("full CIFAR mode row should have one representative")
    if float(full_mode_row["layer_ks_pvalue"]) >= 0.10:
        fail("full CIFAR mode row should fail the layer KS threshold")
    aligned_sample_rows = rows_matching(
        rows,
        setting="CIFAR full aligned",
        comparison="activation_aligned_posterior_samples_vs_tickets",
    )
    if not aligned_sample_rows:
        fail("aligned full CIFAR direct row is missing")
    row = aligned_sample_rows[0]
    if int(float(row["posterior_num_clusters"])) != 1:
        fail("aligned full CIFAR direct row should collapse to one cluster")
    if int(float(row["left_count"])) != 50 or int(float(row["right_count"])) != 5:
        fail("aligned full CIFAR direct row should compare 50 samples to 5 tickets")
    if float(row["layer_ks_pvalue"]) >= 0.001:
        fail("aligned full CIFAR direct row should strongly fail layer KS")
    if float(row["hamming_overlap"]) >= 0.70:
        fail("aligned full CIFAR direct row should fail Hamming-overlap threshold")
    if float(row["activation_cka_hungarian_mean"]) <= 0.85:
        fail("aligned full CIFAR direct row should pass final-hidden activation CKA")
    weight_aligned_sample_rows = rows_matching(
        rows,
        setting="CIFAR full weight-aligned",
        comparison="weight_aligned_posterior_samples_vs_tickets",
    )
    if not weight_aligned_sample_rows:
        fail("weight-aligned full CIFAR direct row is missing")
    row = weight_aligned_sample_rows[0]
    if int(float(row["posterior_num_clusters"])) != 1:
        fail("weight-aligned full CIFAR direct row should collapse to one cluster")
    if int(float(row["left_count"])) != 50 or int(float(row["right_count"])) != 5:
        fail("weight-aligned full CIFAR direct row should compare 50 samples to 5 tickets")
    if float(row["layer_ks_pvalue"]) >= 0.001:
        fail("weight-aligned full CIFAR direct row should strongly fail layer KS")
    if float(row["hamming_overlap"]) >= 0.70:
        fail("weight-aligned full CIFAR direct row should fail Hamming-overlap threshold")
    if float(row["activation_cka_hungarian_mean"]) <= 0.85:
        fail("weight-aligned full CIFAR direct row should pass final-hidden activation CKA")
    csgld_sample_rows = rows_matching(
        rows,
        setting="CIFAR full cSGLD multi-chain",
        comparison="posterior_samples_vs_tickets",
    )
    if not csgld_sample_rows:
        fail("multi-chain cSGLD full CIFAR direct row is missing")
    row = csgld_sample_rows[0]
    if int(float(row["posterior_num_clusters"])) != 1:
        fail("multi-chain cSGLD full CIFAR direct row should collapse to one cluster")
    if int(float(row["left_count"])) != 75 or int(float(row["right_count"])) != 5:
        fail("multi-chain cSGLD full CIFAR direct row should compare 75 samples to 5 tickets")
    if float(row["layer_ks_pvalue"]) >= 0.001:
        fail("multi-chain cSGLD full CIFAR direct row should strongly fail layer KS")
    if float(row["hamming_overlap"]) >= 0.70:
        fail("multi-chain cSGLD full CIFAR direct row should fail Hamming-overlap threshold")
    if float(row["activation_cka_hungarian_mean"]) <= 0.85:
        fail("multi-chain cSGLD full CIFAR direct row should pass final-hidden activation CKA")
    csgld_chain_rows = rows_matching(
        rows,
        setting="CIFAR full cSGLD multi-chain",
        comparison="chain_start_magnitude_vs_tickets",
    )
    if not csgld_chain_rows:
        fail("multi-chain cSGLD full CIFAR chain-start control row is missing")
    if int(float(csgld_chain_rows[0]["left_count"])) != 15:
        fail("multi-chain cSGLD full CIFAR should record 15 chain-start masks")
    csgld_independent_sample_rows = rows_matching(
        rows,
        setting="CIFAR full cSGLD independent",
        comparison="posterior_samples_vs_tickets",
    )
    if not csgld_independent_sample_rows:
        fail("independent-start cSGLD full CIFAR direct row is missing")
    row = csgld_independent_sample_rows[0]
    if int(float(row["posterior_num_clusters"])) != 1:
        fail("independent-start cSGLD full CIFAR direct row should collapse to one cluster")
    if int(float(row["left_count"])) != 75 or int(float(row["right_count"])) != 5:
        fail("independent-start cSGLD full CIFAR direct row should compare 75 samples to 5 tickets")
    if float(row["layer_ks_pvalue"]) >= 0.001:
        fail("independent-start cSGLD full CIFAR direct row should strongly fail layer KS")
    if float(row["hamming_overlap"]) >= 0.70:
        fail("independent-start cSGLD full CIFAR direct row should fail Hamming-overlap threshold")
    if float(row["activation_cka_hungarian_mean"]) <= 0.85:
        fail("independent-start cSGLD full CIFAR direct row should pass final-hidden activation CKA")
    csgld_independent_chain_rows = rows_matching(
        rows,
        setting="CIFAR full cSGLD independent",
        comparison="chain_start_magnitude_vs_tickets",
    )
    if not csgld_independent_chain_rows:
        fail("independent-start cSGLD full CIFAR chain-start control row is missing")
    if int(float(csgld_independent_chain_rows[0]["left_count"])) != 15:
        fail("independent-start cSGLD full CIFAR should record 15 chain-start masks")
    lowrank_sample_rows = rows_matching(
        rows,
        setting="CIFAR full LowRank128Lap",
        comparison="posterior_samples_vs_tickets",
    )
    if not lowrank_sample_rows:
        fail("LowRank128Lap full CIFAR direct row is missing")
    row = lowrank_sample_rows[0]
    if int(float(row["posterior_num_clusters"])) != 1:
        fail("LowRank128Lap full CIFAR direct row should collapse to one cluster")
    if float(row["posterior_effective_cluster_count"]) != 1.0:
        fail("LowRank128Lap full CIFAR direct row should have effective cluster count 1")
    if int(float(row["left_count"])) != 50 or int(float(row["right_count"])) != 5:
        fail("LowRank128Lap full CIFAR direct row should compare 50 samples to 5 tickets")
    if float(row["layer_ks_pvalue"]) >= 0.001:
        fail("LowRank128Lap full CIFAR direct row should still strongly fail layer KS")
    if float(row["hamming_overlap"]) <= 0.70:
        fail("LowRank128Lap full CIFAR direct row should pass Hamming-overlap threshold")
    if float(row["logit_cka_hungarian_mean"]) <= 0.85:
        fail("LowRank128Lap full CIFAR direct row should pass logit CKA")
    if float(row["activation_cka_hungarian_mean"]) <= 0.85:
        fail("LowRank128Lap full CIFAR direct row should pass final-hidden activation CKA")
    jointdiag_sample_rows = rows_matching(
        rows,
        setting="CIFAR full JointDiagLap270k",
        comparison="posterior_samples_vs_tickets",
    )
    if not jointdiag_sample_rows:
        fail("JointDiagLap270k full CIFAR direct row is missing")
    row = jointdiag_sample_rows[0]
    if int(float(row["posterior_num_clusters"])) != 1:
        fail("JointDiagLap270k full CIFAR direct row should collapse to one cluster")
    if float(row["posterior_effective_cluster_count"]) != 1.0:
        fail("JointDiagLap270k full CIFAR direct row should have effective cluster count 1")
    if int(float(row["left_count"])) != 25 or int(float(row["right_count"])) != 5:
        fail("JointDiagLap270k full CIFAR direct row should compare 25 samples to 5 tickets")
    if float(row["layer_ks_pvalue"]) >= 0.001:
        fail("JointDiagLap270k full CIFAR direct row should strongly fail layer KS")
    if float(row["hamming_overlap"]) >= 0.70:
        fail("JointDiagLap270k full CIFAR direct row should fail Hamming-overlap threshold")
    if float(row["logit_cka_hungarian_mean"]) <= 0.85:
        fail("JointDiagLap270k full CIFAR direct row should pass logit CKA")
    if float(row["activation_cka_hungarian_mean"]) <= 0.85:
        fail("JointDiagLap270k full CIFAR direct row should pass final-hidden activation CKA")
    metrics_path = ROOT / str(row["run"]) / "metrics.json"
    if not metrics_path.exists():
        fail(f"JointDiagLap270k raw metrics are missing: {metrics_path}")
    payload = load_json(metrics_path)
    config = payload.get("config", {})
    if config.get("posterior_sampler") != "jointdiag-laplace":
        fail("JointDiagLap270k direct metrics should use jointdiag-laplace sampler")
    sampler_config = config.get("posterior_sampler_config", {})
    if not sampler_config.get("stream_joint_groups"):
        fail("JointDiagLap270k direct metrics should stream joint groups")
    if int(sampler_config.get("max_parameters", 0)) != 40_000:
        fail("JointDiagLap270k direct metrics should use max_parameters=40000")
    if abs(float(sampler_config.get("scale", 0.0)) - 1e-6) > 1e-12:
        fail("JointDiagLap270k direct metrics should use scale=1e-6")
    diagnostics = payload.get("posterior_chain_diagnostics", {})
    if int(diagnostics.get("posterior_sample_count", 0)) != 25:
        fail("JointDiagLap270k direct metrics should contain 25 posterior samples")
    if float(diagnostics.get("posterior_sample_accuracy_mean", 0.0)) <= 0.875:
        fail("JointDiagLap270k direct samples should preserve useful accuracy")
    hamming = float(diagnostics.get("posterior_to_chain_start_hamming_mean", math.nan))
    if not (0.045 <= hamming <= 0.055):
        fail("JointDiagLap270k direct posterior movement should remain around 0.05 Hamming")


def require_direct_mode_ticket_seed_level_audit() -> None:
    json_path = ROOT / "runs" / "direct_mode_ticket_seed_level_audit.json"
    doc_path = ROOT / "docs" / "direct_mode_ticket_seed_level_audit.md"
    payload = load_json(json_path)
    if payload.get("direct_seed_level_audit_ready") is not True:
        fail(f"direct seed-level audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"direct seed-level audit has risk flags: {payload['risk_flags']}")
    checks = payload.get("interpretation_checks", {})
    expected_true = [
        "seed_level_artifact_available_for_saved_full_data_sgld",
        "pooled_direct_distribution_pvalues_are_descriptive",
        "raw_posterior_not_closer_than_chain_in_5_of_5_seeds",
        "activation_aligned_posterior_not_closer_than_chain_in_5_of_5_seeds",
        "other_direct_rows_require_saved_masks_for_seed_level_reanalysis",
    ]
    for key in expected_true:
        if checks.get(key) is not True:
            fail(f"direct seed-level audit interpretation check failed: {key}")
    variants = {
        str(variant.get("label")): variant
        for variant in payload.get("variants", [])
        if isinstance(variant, dict)
    }
    for label in ["raw_saved_artifact", "activation_aligned_saved_artifact"]:
        variant = variants.get(label)
        if not isinstance(variant, dict):
            fail(f"direct seed-level audit missing variant: {label}")
        if int(variant.get("seed_count", 0)) != 5:
            fail(f"direct seed-level audit variant should be five-seed: {label}")
        if int(variant.get("sample_count", 0)) < 50:
            fail(f"direct seed-level audit variant sample count too small: {label}")
        if variant.get("posterior_not_closer_than_chain_in_all_seeds") is not True:
            fail(f"posterior should not be closer than chain in all seeds: {label}")
        delta = variant.get("posterior_minus_chain_hamming", {})
        if int(delta.get("positive", 0)) != 5 or int(delta.get("negative", 0)) != 0:
            fail(f"direct seed-level audit should have 5/5 positive Hamming deltas: {label}")
        if float(delta.get("mean", 0.0)) <= 0.0:
            fail(f"direct seed-level audit Hamming delta should be positive: {label}")
    if len(payload.get("direct_rows_without_saved_masks", [])) < 5:
        fail("direct seed-level audit should record remaining direct rows without saved masks")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Direct Mode/Ticket Seed-Level Artifact Audit",
        "Pooled layer-KS p-values",
        "raw_saved_artifact",
        "activation_aligned_saved_artifact",
        "Positive values mean posterior samples are farther",
        "Direct Rows Still Requiring Saved Masks",
        "This file is generated by `scripts/audit_direct_mode_ticket_seed_level_artifacts.py`.",
    ]:
        if phrase not in text:
            fail(f"direct seed-level audit markdown missing phrase: {phrase}")


def require_batchnorm_posterior_policy_audit() -> None:
    json_path = ROOT / "runs" / "batchnorm_posterior_policy_audit.json"
    doc_path = ROOT / "docs" / "batchnorm_posterior_policy_audit.md"
    payload = load_json(json_path)
    if payload.get("batchnorm_policy_audit_ready") is not True:
        fail(f"BatchNorm posterior policy audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"BatchNorm posterior policy audit has risk flags: {payload['risk_flags']}")
    if int(payload.get("batchnorm_module_occurrences_in_models_py", 0)) < 6:
        fail("BatchNorm posterior policy audit should detect ResNet BatchNorm modules")
    checks = payload.get("interpretation", {})
    for key in [
        "resnet_uses_batchnorm",
        "train_mode_posterior_samplers_are_documented_open_risk",
        "lowrank_and_subspace_paths_have_eval_default_knob",
        "direct_sgld_family_bn_ablation_knobs_available",
        "exact_laplace_paths_use_eval_mode",
    ]:
        if checks.get(key) is not True:
            fail(f"BatchNorm posterior policy interpretation check failed: {key}")
    open_flags = set(payload.get("open_risk_flags", []))
    expected_open = {
        "sgld_updates_batchnorm_buffers_during_sampling",
        "sghmc_updates_batchnorm_buffers_during_sampling",
        "cyclical_sgld_updates_batchnorm_buffers_during_sampling",
        "swag_snapshots_include_training_mode_batchnorm_buffers",
        "diag_laplace_fisher_uses_training_mode_batchnorm",
        "full_hmc_updates_batchnorm_buffers_during_sampling",
    }
    if not expected_open.issubset(open_flags):
        fail(f"BatchNorm posterior policy audit missing open risks: {sorted(expected_open - open_flags)}")
    rows = payload.get("rows", [])
    if len(rows) < 10:
        fail("BatchNorm posterior policy audit should cover posterior/covariance families")
    if any(row.get("policy_detected") is not True for row in rows):
        fail("BatchNorm posterior policy audit failed to detect at least one policy")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "BatchNorm Posterior Policy Audit",
        "Train-mode stochastic samplers remain an open implementation risk",
        "freeze/recalibrate/dense-buffer ablation knobs",
        "sgld_updates_batchnorm_buffers_during_sampling",
        "low-rank Laplace",
        "Recommended Next Experiments",
        "This file is generated by `scripts/audit_batchnorm_posterior_policy.py`.",
    ]:
        if phrase not in text:
            fail(f"BatchNorm posterior policy audit markdown missing phrase: {phrase}")


def require_unit_smoke_tests() -> None:
    json_path = ROOT / "runs" / "unit_smoke_tests.json"
    doc_path = ROOT / "docs" / "unit_smoke_tests.md"
    payload = load_json(json_path)
    if payload.get("unit_smoke_tests_ready") is not True:
        fail(f"unit smoke tests are not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"unit smoke tests have risk flags: {payload['risk_flags']}")
    checks = {row.get("name"): row for row in payload.get("checks", [])}
    expected = {
        "seed_determinism",
        "mask_operations",
        "evaluate_weighted_average",
        "data_splits",
        "tempered_sgld",
    }
    if set(checks) != expected:
        fail(f"unit smoke tests changed coverage: {sorted(checks)}")
    for name in expected:
        if checks[name].get("passed") is not True:
            fail(f"unit smoke test failed: {name}")
        if not checks[name].get("covers"):
            fail(f"unit smoke test lacks coverage metadata: {name}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Unit Smoke Tests",
        "RNG seeding",
        "mask keep counts",
        "evaluation aggregation",
        "validation splits",
        "This file is generated by `scripts/run_unit_smoke_tests.py`.",
    ]:
        if phrase not in text:
            fail(f"unit smoke test markdown missing phrase: {phrase}")


def require_validation_test_usage_policy_audit() -> None:
    json_path = ROOT / "runs" / "validation_test_usage_policy_audit.json"
    doc_path = ROOT / "docs" / "validation_test_usage_policy_audit.md"
    payload = load_json(json_path)
    if payload.get("validation_test_usage_policy_audit_ready") is not True:
        fail(f"validation/test policy audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"validation/test policy audit has risk flags: {payload['risk_flags']}")
    if payload.get("dataset_has_validation_loader") is not True:
        fail("validation/test policy audit should record shared validation loader support")
    if payload.get("digits_scaler_fit_on_train_only_detected") is not True:
        fail("validation/test policy audit should confirm digits scaler is fit on train only")
    if payload.get("torchvision_first_n_subset_detected") is not False:
        fail("validation/test policy audit should confirm first-N torchvision subset is not the default")
    if payload.get("torchvision_first_subset_option_available") is not True:
        fail("validation/test policy audit should record first-N as an explicit legacy/debug option")
    if payload.get("torchvision_seeded_subset_option_detected") is not True:
        fail("validation/test policy audit should detect seeded torchvision subset support")
    if int(payload.get("test_loader_script_count", 0)) < 10:
        fail("validation/test policy audit should detect repeated test-loader script usage")
    if int(payload.get("validation_configurable_test_loader_script_count", 0)) < 20:
        fail("validation/test policy audit should detect all validation-configurable scripts")
    if int(payload.get("validation_unsupported_test_loader_script_count", 0)) != 0:
        fail("validation/test policy audit should have no unsupported test-loader scripts")
    configurable_paths = {
        row.get("path")
        for row in payload.get("test_loader_usage_rows", [])
        if row.get("validation_split_supported") is True
    }
    for expected_path in [
        "scripts/run_block_laplace_probe.py",
        "scripts/run_calibration_ood_probe.py",
        "scripts/run_cifar_baseline.py",
        "scripts/run_digits_fullnet_laplace_probe.py",
        "scripts/run_digits_hmc_baseline.py",
        "scripts/run_digits_pilot.py",
        "scripts/run_head_laplace_probe.py",
        "scripts/run_mode_ticket_distribution_probe.py",
        "scripts/run_residual_anatomy_probe.py",
        "scripts/run_residual_base_compatibility_probe.py",
        "scripts/run_residual_cross_seed_transfer_probe.py",
        "scripts/run_residual_direct_transfer_probe.py",
        "scripts/run_residual_imp_process_probe.py",
        "scripts/run_residual_predictor_mask_probe.py",
        "scripts/run_residual_stratified_control_probe.py",
        "scripts/run_sgld_movement_grid.py",
        "scripts/run_subspace_hmc_probe.py",
        "scripts/run_trajectory_probe.py",
        "scripts/run_trajectory_residual_probe.py",
        "scripts/run_trajectory_mask_training_probe.py",
    ]:
        if expected_path not in configurable_paths:
            fail(f"validation/test policy audit missing configurable script: {expected_path}")
    open_flags = set(payload.get("open_risk_flags", []))
    locked_observed = locked_final_test_observed()
    if locked_observed:
        if "locked_final_test_rerun_not_observed" in open_flags:
            fail("validation/test policy audit should drop locked-final-test risk after the rerun is observed")
    else:
        expected = {
            "locked_final_test_rerun_not_observed",
        }
        if not expected.issubset(open_flags):
            fail(f"validation/test policy audit missing open risks: {sorted(expected - open_flags)}")
    if "test_loader_scripts_without_validation_split_support" in open_flags:
        fail("validation/test policy audit should not keep unsupported-script risk open")
    if "experiment_scripts_repeatedly_use_test_loader" in open_flags:
        fail("validation/test policy audit should not keep configurable test-loader usage as an open risk")
    if "validation_loader_available_but_publishable_rerun_missing" in open_flags:
        fail("validation/test policy audit should now observe the validation-selected CIFAR rerun")
    warning_flags = set(payload.get("warning_flags", []))
    if "test_loader_eval_paths_retained_but_validation_configurable" not in warning_flags:
        fail("validation/test policy audit should keep validation-configurable test-loader usage as a warning")
    if payload.get("validation_selected_cifar_rerun_observed") is not True:
        fail("validation/test policy audit should record observed validation-selected CIFAR rerun")
    if locked_observed:
        if payload.get("locked_final_test_rerun_observed") is not True:
            fail("validation/test policy audit should record observed locked final-test rerun")
    else:
        if payload.get("locked_final_test_rerun_observed") is not False:
            fail("validation/test policy audit should keep locked final-test rerun open until executed")
    checks = payload.get("interpretation", {})
    always_true_keys = [
        "no_data_leakage_seen_in_digits_scaler",
        "validation_loader_supported_by_shared_bundle",
        "validation_selected_cifar_rerun_observed",
        "some_test_loader_scripts_support_validation_split",
        "seeded_subset_option_available_for_publishable_subset_rows",
        "first_n_subset_is_legacy_explicit_only",
        "all_test_loader_scripts_are_validation_configurable",
    ]
    for key in always_true_keys:
        if checks.get(key) is not True:
            fail(f"validation/test policy interpretation check failed: {key}")
    locked_dependent_keys = [
        "locked_final_test_rerun_still_required",
        "test_metrics_are_diagnostic_until_locked_final_test",
    ]
    expected_value = not locked_observed
    for key in locked_dependent_keys:
        if checks.get(key) is not expected_value:
            fail(
                "validation/test policy interpretation should record "
                f"{key}={expected_value} once locked_final_test_observed={locked_observed}"
            )
    if checks.get("some_test_loader_scripts_still_lack_validation_split") is not False:
        fail("validation/test policy interpretation should record zero unsupported scripts")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Validation/Test Usage Policy Audit",
        "test-set peeking risk",
        "Shared validation loader present: `True`",
        "Torchvision first-N subset default detected: `False`",
        "Test-loader scripts with validation/evaluation split support:",
        "Test-loader scripts with validation/evaluation split support: 20",
        "Test-loader scripts still lacking validation/evaluation split support: 0",
        "scripts/run_block_laplace_probe.py",
        "scripts/run_calibration_ood_probe.py",
        "scripts/run_cifar_baseline.py",
        "scripts/run_digits_fullnet_laplace_probe.py",
        "scripts/run_digits_hmc_baseline.py",
        "scripts/run_digits_pilot.py",
        "scripts/run_head_laplace_probe.py",
        "scripts/run_residual_anatomy_probe.py",
        "scripts/run_residual_base_compatibility_probe.py",
        "scripts/run_residual_cross_seed_transfer_probe.py",
        "scripts/run_residual_direct_transfer_probe.py",
        "scripts/run_residual_imp_process_probe.py",
        "scripts/run_residual_predictor_mask_probe.py",
        "scripts/run_residual_stratified_control_probe.py",
        "scripts/run_subspace_hmc_probe.py",
        "scripts/run_trajectory_probe.py",
        "scripts/run_trajectory_residual_probe.py",
        "Validation-selected CIFAR SGLD rerun observed: `True`",
        "test_loader_eval_paths_retained_but_validation_configurable",
        "Scripts With First-N Subset Default",
        "Run the locked final-test SGLD row once after validation selection",
        "This file is generated by `scripts/audit_validation_test_usage_policy.py`.",
    ]:
        if phrase not in text:
            fail(f"validation/test policy audit markdown missing phrase: {phrase}")


def require_validation_bn_rerun_plan() -> None:
    json_path = ROOT / "runs" / "validation_bn_rerun_plan.json"
    doc_path = ROOT / "docs" / "validation_bn_rerun_plan.md"
    payload = load_json(json_path)
    if payload.get("validation_bn_rerun_plan_ready") is not True:
        fail(f"validation/BN rerun plan is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"validation/BN rerun plan has risk flags: {payload['risk_flags']}")
    if int(payload.get("entry_count", 0)) < 10:
        fail("validation/BN rerun plan should include validation, BN, and saved-artifact rows")
    open_flags = set(payload.get("open_risk_flags", []))
    observed_entries = set(payload.get("observed_entries", []))
    bn_observed = any(name.startswith("bn_") for name in observed_entries)
    saved_observed = any(name.startswith("saved_artifacts_") for name in observed_entries)
    expected_open: set[str] = set()
    if not bn_observed:
        expected_open.add("bn_policy_cifar_ablation_not_observed")
    if not saved_observed:
        expected_open.add("seed_level_saved_artifact_reruns_not_observed")
    if not expected_open.issubset(open_flags):
        fail(f"validation/BN rerun plan missing open risks: {sorted(expected_open - open_flags)}")
    leaked_observed = set()
    if bn_observed and "bn_policy_cifar_ablation_not_observed" in open_flags:
        leaked_observed.add("bn_policy_cifar_ablation_not_observed")
    if saved_observed and "seed_level_saved_artifact_reruns_not_observed" in open_flags:
        leaked_observed.add("seed_level_saved_artifact_reruns_not_observed")
    if leaked_observed:
        fail(f"validation/BN rerun plan should drop observed-group risks: {sorted(leaked_observed)}")
    if "validation_selected_cifar_rerun_not_observed" in open_flags:
        fail("validation/BN rerun plan should now observe the validation-selected CIFAR rerun")
    if int(payload.get("observed_entry_count", 0)) < 1:
        fail("validation/BN rerun plan should observe at least the validation-selected CIFAR rerun")
    if "validation_select_sgld_full_cifar" not in observed_entries:
        fail("validation/BN rerun plan missing observed validation_select_sgld_full_cifar")
    commands = "\n".join(
        str(entry.get("command", "")) for entry in payload.get("entries", [])
    )
    for snippet in [
        "--validation-fraction 0.1",
        "--evaluation-split val",
        "--evaluation-split test",
        "--subset-strategy seeded",
        "--posterior-bn-policy freeze",
        "--posterior-bn-policy recalibrate",
        "--posterior-bn-policy dense_buffers",
        "--save-mask-artifacts",
        "--save-state-artifacts",
        "--selection-source-run",
        "--selection-source-summary",
    ]:
        if snippet not in commands:
            fail(f"validation/BN rerun plan command missing snippet: {snippet}")
    checks = payload.get("interpretation", {})
    if checks.get("commands_are_locked_before_rerun") is not True:
        fail("validation/BN rerun plan interpretation check failed: commands_are_locked_before_rerun")
    bn_expected = not bn_observed
    if checks.get("batchnorm_ablation_rerun_still_required") is not bn_expected:
        fail(
            "validation/BN rerun plan interpretation should record "
            f"batchnorm_ablation_rerun_still_required={bn_expected} once bn_observed={bn_observed}"
        )
    saved_expected = not saved_observed
    if checks.get("seed_level_artifact_rerun_still_required") is not saved_expected:
        fail(
            "validation/BN rerun plan interpretation should record "
            f"seed_level_artifact_rerun_still_required={saved_expected} once saved_observed={saved_observed}"
        )
    if checks.get("validation_selection_rerun_still_required") is not False:
        fail("validation/BN rerun plan should mark validation selection rerun as observed")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Validation and BatchNorm Rerun Plan",
        "command plan, not evidence",
        "validation_select_sgld_full_cifar",
        "bn_freeze_sgld_full_cifar",
        "saved_artifacts_lowrank128",
        "This file is generated by `scripts/build_validation_bn_rerun_plan.py`.",
    ]:
        if phrase not in text:
            fail(f"validation/BN rerun plan markdown missing phrase: {phrase}")


def require_validation_bn_rerun_runner() -> None:
    script_text = (ROOT / "scripts" / "run_validation_bn_rerun_plan_entry.py").read_text(
        encoding="utf-8"
    )
    makefile_text = (ROOT / "Makefile").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    for snippet in [
        "--preflight-only",
        "--allow-busy-gpu",
        "--skip-gpu-preflight",
        "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
        "selected_gpu_busy",
        "validation_bn_plan_entry_<entry>_receipt.json",
        "This file is generated by `scripts/run_validation_bn_rerun_plan_entry.py`.",
    ]:
        if snippet not in script_text:
            fail(f"validation/BN rerun runner missing snippet: {snippet}")
    for snippet in [
        "validation-bn-rerun-preflight",
        "validation-bn-rerun-entry",
        "locked-final-test-preflight",
        "locked-final-test-run",
        "--preflight-only",
    ]:
        if snippet not in makefile_text:
            fail(f"Makefile missing validation/BN runner target snippet: {snippet}")
    for snippet in [
        "make locked-final-test-preflight",
        "make locked-final-test-run",
        "make validation-bn-rerun-preflight",
        "make validation-bn-rerun-entry",
        "refuses to start when another",
        "selected CUDA device",
    ]:
        if snippet not in readme_text:
            fail(f"README missing validation/BN runner guidance snippet: {snippet}")


def require_remaining_experiment_queue() -> None:
    json_path = ROOT / "runs" / "remaining_experiment_queue.json"
    doc_path = ROOT / "docs" / "remaining_experiment_queue.md"
    payload = load_json(json_path)
    if payload.get("remaining_experiment_queue_ready") is not True:
        fail(f"remaining experiment queue is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"remaining experiment queue has risk flags: {payload['risk_flags']}")
    if payload.get("expected_entry_count") != 10 or payload.get("queue_entry_count") != 10:
        fail("remaining experiment queue should cover exactly the ten remaining rerun entries")
    entries = payload.get("entries", [])
    by_name = {str(row.get("name")): row for row in entries if isinstance(row, dict)}
    expected_names = {
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
    }
    if set(by_name) != expected_names:
        fail(f"remaining experiment queue entries changed: {sorted(set(by_name))}")
    for name, row in by_name.items():
        for key in [
            "run_root",
            "summary_md",
            "summary_csv",
            "main_command",
            "summarize_command",
            "preflight_command",
            "run_wrapper_command",
            "paper_action",
        ]:
            if not row.get(key):
                fail(f"remaining experiment queue entry {name} missing {key}")
        if "run_validation_bn_rerun_plan_entry.py" not in str(row.get("preflight_command")):
            fail(f"remaining experiment queue preflight command malformed for {name}")
        if "run_validation_bn_rerun_plan_entry.py" not in str(row.get("run_wrapper_command")):
            fail(f"remaining experiment queue run command malformed for {name}")
        if row.get("validation_findings") not in ([], None):
            fail(f"remaining experiment queue validation finding for {name}: {row.get('validation_findings')}")
    if "--selection-source-run" not in str(by_name["locked_final_test_sgld_full_cifar"].get("main_command")):
        fail("remaining experiment queue locked final-test command lost validation source")
    for name in [
        "bn_freeze_sgld_full_cifar",
        "bn_recalibrate_sgld_full_cifar",
        "bn_dense_buffers_sgld_full_cifar",
        "bn_freeze_csgld_full_cifar",
        "bn_recalibrate_csgld_full_cifar",
        "bn_dense_buffers_csgld_full_cifar",
    ]:
        if "--posterior-bn-policy" not in str(by_name[name].get("main_command")):
            fail(f"remaining experiment queue BN command missing policy flag: {name}")
    for name in [
        "saved_artifacts_csgld_multichain",
        "saved_artifacts_lowrank128",
        "saved_artifacts_jointdiag",
    ]:
        if by_name[name].get("saves_mask_artifacts") is not True:
            fail(f"remaining experiment queue saved-artifact row not marked as saving masks: {name}")
        if "--save-mask-artifacts" not in str(by_name[name].get("main_command")):
            fail(f"remaining experiment queue saved-artifact command missing mask save flag: {name}")
    group_names = {str(row.get("category")) for row in payload.get("group_summaries", [])}
    for category in [
        "locked_final_test",
        "batchnorm_policy_ablation",
        "saved_artifact_seed_level_reruns",
    ]:
        if category not in group_names:
            fail(f"remaining experiment queue missing group: {category}")
    open_flags = set(payload.get("open_risk_flags", []))

    def _gate_queue_flags(flags: list[str], cleared: bool, group_label: str) -> None:
        if cleared:
            leaked = [flag for flag in flags if flag in open_flags]
            if leaked:
                fail(
                    f"remaining experiment queue should drop {group_label} risks: {leaked}"
                )
        else:
            for flag in flags:
                if flag not in open_flags:
                    fail(f"remaining experiment queue missing open risk: {flag}")

    _gate_queue_flags(
        [
            "locked_final_test_metrics_not_observed",
            "locked_final_test_rerun_not_observed",
        ],
        locked_final_test_observed(),
        "locked-final-test",
    )
    _gate_queue_flags(
        [
            "full_cifar_bn_ablation_rerun_not_observed",
            "bn_policy_cifar_ablation_not_observed",
        ],
        bn_ablation_observed(),
        "BN-ablation",
    )
    _gate_queue_flags(
        [
            "seed_level_saved_artifacts_incomplete_for_other_direct_rows",
            "seed_level_saved_artifact_reruns_not_observed",
        ],
        saved_artifact_reruns_observed(),
        "saved-artifact",
    )
    interpretation = payload.get("interpretation", {})
    for key in [
        "queue_is_execution_plan_not_completed_evidence",
        "paper_claims_must_remain_scoped_until_queue_observed",
    ]:
        if interpretation.get(key) is not True:
            fail(f"remaining experiment queue interpretation check failed: {key}")
    queue_fully_observed = (
        locked_final_test_observed()
        and bn_ablation_observed()
        and saved_artifact_reruns_observed()
    )
    expected_gpu_still_required = not queue_fully_observed
    if interpretation.get("gpu_reruns_still_required") is not expected_gpu_still_required:
        fail(
            "remaining experiment queue interpretation should record "
            f"gpu_reruns_still_required={expected_gpu_still_required} once queue_fully_observed={queue_fully_observed}"
        )
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Remaining Experiment Queue",
        "an execution plan, not completed experiment evidence",
        "locked_final_test_sgld_full_cifar",
        "bn_recalibrate_csgld_full_cifar",
        "saved_artifacts_jointdiag",
        "Post-Run Refresh",
        "This file is generated by `scripts/build_remaining_experiment_queue.py`.",
    ]:
        if phrase not in text:
            fail(f"remaining experiment queue markdown missing phrase: {phrase}")


def require_remaining_experiment_preflight_audit() -> None:
    json_path = ROOT / "runs" / "remaining_experiment_preflight_audit.json"
    doc_path = ROOT / "docs" / "remaining_experiment_preflight_audit.md"
    require_file(str(json_path.relative_to(ROOT)), 1000)
    require_file(str(doc_path.relative_to(ROOT)), 1000)
    payload = load_json(json_path)
    if payload.get("remaining_experiment_preflight_audit_ready") is not True:
        fail(f"remaining experiment preflight audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"remaining experiment preflight audit has risk flags: {payload['risk_flags']}")
    if payload.get("not_completed_experiment_evidence") is not True:
        fail("remaining experiment preflight audit must not claim completed evidence")
    if payload.get("audit_is_non_executing") is not True:
        fail("remaining experiment preflight audit must be non-executing")
    if payload.get("queue_json") != "runs/remaining_experiment_queue.json":
        fail("remaining experiment preflight audit points at wrong queue JSON")
    if payload.get("expected_entry_count") != 10 or payload.get("entry_count") != 10:
        fail("remaining experiment preflight audit should cover exactly ten entries")
    if payload.get("command_shape_ready_count") != 10:
        fail("remaining experiment preflight audit did not validate all command shapes")
    if payload.get("gpu_required_entry_count") != 10:
        fail("remaining experiment preflight audit should identify all queued rows as GPU runs")
    entries = payload.get("entries", [])
    by_name = {str(row.get("name")): row for row in entries if isinstance(row, dict)}
    expected_names = {
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
    }
    if set(by_name) != expected_names:
        fail(f"remaining experiment preflight entries changed: {sorted(set(by_name))}")
    for name, row in by_name.items():
        if row.get("training_started_by_this_audit") is not False:
            fail(f"remaining experiment preflight must not start training for {name}")
        if row.get("command_shape_ready") is not True:
            fail(f"remaining experiment preflight command shape not ready for {name}")
        if row.get("main_script_exists") is not True or row.get("summary_script_exists") is not True:
            fail(f"remaining experiment preflight script existence failed for {name}")
        if row.get("requires_gpu") is not True:
            fail(f"remaining experiment preflight did not mark GPU requirement for {name}")
        if row.get("cuda_visible_devices") in (None, "", "-1"):
            fail(f"remaining experiment preflight missing CUDA visible device for {name}")
        if row.get("validation_findings") not in ([], None):
            fail(f"remaining experiment preflight validation finding for {name}: {row.get('validation_findings')}")
        if not str(row.get("expected_receipt_json", "")).endswith(f"{name}_receipt.json"):
            fail(f"remaining experiment preflight receipt JSON malformed for {name}")
        if not str(row.get("expected_receipt_md", "")).endswith(f"{name}_receipt.md"):
            fail(f"remaining experiment preflight receipt markdown malformed for {name}")
    live_gpu_probe = payload.get("live_gpu_probe", {})
    if live_gpu_probe.get("training_started") is not False:
        fail("remaining experiment preflight live GPU probe must not start training")
    if live_gpu_probe.get("status") not in {
        "not_requested",
        "selected_gpu_busy",
        "selected_gpu_available",
        "gpu_inventory_unavailable",
    }:
        fail(f"remaining experiment preflight has unexpected live GPU status: {live_gpu_probe}")
    open_flags = set(payload.get("open_risk_flags", []))

    def _gate_preflight_flags(flags: list[str], cleared: bool, group_label: str) -> None:
        if cleared:
            leaked = [flag for flag in flags if flag in open_flags]
            if leaked:
                fail(
                    f"remaining experiment preflight should drop {group_label} risks: {leaked}"
                )
        else:
            for flag in flags:
                if flag not in open_flags:
                    fail(
                        f"remaining experiment preflight missing inherited open risk: {flag}"
                    )

    _gate_preflight_flags(
        [
            "locked_final_test_metrics_not_observed",
            "locked_final_test_rerun_not_observed",
        ],
        locked_final_test_observed(),
        "locked-final-test",
    )
    _gate_preflight_flags(
        [
            "full_cifar_bn_ablation_rerun_not_observed",
            "bn_policy_cifar_ablation_not_observed",
        ],
        bn_ablation_observed(),
        "BN-ablation",
    )
    _gate_preflight_flags(
        [
            "seed_level_saved_artifacts_incomplete_for_other_direct_rows",
            "seed_level_saved_artifact_reruns_not_observed",
        ],
        saved_artifact_reruns_observed(),
        "saved-artifact",
    )
    interpretation = payload.get("interpretation", {})
    for key in [
        "all_commands_parsed_without_starting_training",
        "queue_still_requires_gpu_reruns",
    ]:
        if interpretation.get(key) is not True:
            fail(f"remaining experiment preflight interpretation failed: {key}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Remaining Experiment Preflight Audit",
        "Non-executing audit: `True`",
        "Completed experiment evidence: `False`",
        "locked_final_test_sgld_full_cifar",
        "bn_recalibrate_csgld_full_cifar",
        "saved_artifacts_jointdiag",
        "This file is generated by `scripts/audit_remaining_experiment_preflight.py`.",
    ]:
        if phrase not in text:
            fail(f"remaining experiment preflight markdown missing phrase: {phrase}")


def require_open_blocker_claim_scope_audit() -> None:
    json_path = ROOT / "runs" / "open_blocker_claim_scope_audit.json"
    doc_path = ROOT / "docs" / "open_blocker_claim_scope_audit.md"
    require_file(str(json_path.relative_to(ROOT)), 1000)
    require_file(str(doc_path.relative_to(ROOT)), 1000)
    payload = load_json(json_path)
    if payload.get("open_blocker_claim_scope_audit_ready") is not True:
        fail(f"open blocker claim-scope audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"open blocker claim-scope audit has risk flags: {payload['risk_flags']}")
    if payload.get("not_blocker_closure_evidence") is not True:
        fail("open blocker claim-scope audit must not claim blocker closure")
    if payload.get("top_audit_json") != "runs/top_conference_completion_audit.json":
        fail("open blocker claim-scope audit points at the wrong top audit")
    if payload.get("top_conference_goal_complete") is not False:
        fail("open blocker claim-scope audit must preserve incomplete goal state")
    top_path = ROOT / "runs" / "top_conference_completion_audit.json"
    if top_path.exists():
        top = load_json(top_path)
        top_open = [str(flag) for flag in top.get("open_blockers", [])]
        if payload.get("open_risk_flags") != top_open:
            fail("open blocker claim-scope audit open flags drifted from top audit")
        if payload.get("open_blocker_count") != len(top_open):
            fail("open blocker claim-scope audit blocker count mismatch")
    elif int(payload.get("open_blocker_count", 0)) < 10:
        fail("open blocker claim-scope audit has too few recorded blockers")
    if payload.get("ungrouped_open_blockers") not in ([], None):
        fail(f"open blocker claim-scope audit left ungrouped blockers: {payload.get('ungrouped_open_blockers')}")
    expected_groups = {
        "final_venue_submission",
        "locked_final_test",
        "batchnorm_policy_ablation",
        "saved_artifact_seed_level_reruns",
        "strict_external_validation",
        "formal_external_screening",
        "backup_venue_cfp_watch",
    }
    groups = payload.get("groups", [])
    by_group = {str(row.get("group")): row for row in groups if isinstance(row, dict)}
    if set(by_group) != expected_groups:
        fail(f"open blocker claim-scope groups changed: {sorted(set(by_group))}")
    locked_observed = locked_final_test_observed()
    bn_observed = bn_ablation_observed()
    saved_observed = saved_artifact_reruns_observed()
    group_closed = {
        "locked_final_test": locked_observed,
        "batchnorm_policy_ablation": bn_observed,
        "saved_artifact_seed_level_reruns": saved_observed,
    }
    for name, row in by_group.items():
        is_closed = group_closed.get(name, False)
        expected_active = not is_closed
        if row.get("active") is not expected_active:
            fail(
                f"open blocker claim-scope group {name} active={row.get('active')} "
                f"but expected {expected_active} "
                f"(locked={locked_observed}, bn={bn_observed}, saved={saved_observed})"
            )
        if not is_closed:
            if row.get("mitigation_documented") is not True:
                fail(f"open blocker claim-scope group lacks mitigation: {name}")
            if row.get("missing_required_phrases") not in ([], None):
                fail(f"open blocker claim-scope missing phrases for {name}: {row.get('missing_required_phrases')}")
    interpretation = payload.get("interpretation", {})
    for key in [
        "all_open_blockers_have_scope_mitigation",
        "paper_or_operator_docs_keep_claims_scoped",
        "audit_does_not_reduce_scientific_or_external_blockers",
    ]:
        if interpretation.get(key) is not True:
            fail(f"open blocker claim-scope interpretation failed: {key}")
    scanned = set(str(path) for path in payload.get("scanned_paths", []))
    for path in [
        "paper/main.tex",
        "docs/remaining_experiment_preflight_audit.md",
        "docs/external_validation_readiness_audit.md",
        "docs/formal_plagiarism_screening_receipt_audit.md",
    ]:
        if path not in scanned:
            fail(f"open blocker claim-scope audit did not scan {path}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Open Blocker Claim-Scope Audit",
        "Not blocker closure evidence: `True`",
        "final_venue_submission",
        "locked_final_test",
        "strict_external_validation",
        "formal_external_screening",
        "This file is generated by `scripts/audit_open_blocker_claim_scope.py`.",
    ]:
        if phrase not in text:
            fail(f"open blocker claim-scope markdown missing phrase: {phrase}")


def require_locked_final_test_preflight_receipt() -> None:
    json_path = ROOT / "runs" / "validation_bn_plan_entry_locked_final_test_sgld_full_cifar_receipt.json"
    doc_path = ROOT / "docs" / "validation_bn_plan_entry_locked_final_test_sgld_full_cifar_receipt.md"
    require_file(str(json_path.relative_to(ROOT)), 500)
    require_file(str(doc_path.relative_to(ROOT)), 500)
    payload = load_json(json_path)
    if payload.get("entry") != "locked_final_test_sgld_full_cifar":
        fail("locked final-test preflight receipt has the wrong entry")
    locked_observed = locked_final_test_observed()
    gpu_preflight = payload.get("gpu_preflight", {})
    if gpu_preflight.get("required") is not True:
        fail("locked final-test receipt should require a CUDA occupancy check")
    if not gpu_preflight.get("selected_visible_devices"):
        fail("locked final-test receipt should record selected visible CUDA devices")
    commands = payload.get("commands", [])
    labels = {record.get("label") for record in commands}
    if not {"main", "summary"}.issubset(labels):
        fail("locked final-test receipt should record the main and summary commands")
    if locked_observed:
        if payload.get("preflight_only") is not False:
            fail("locked final-test receipt should be a completed-run receipt after the rerun is observed")
        if payload.get("status") != "completed":
            fail(f"locked final-test completed-run status should be 'completed': {payload.get('status')}")
        if payload.get("validation_bn_plan_entry_receipt_ready") is not True:
            fail("locked final-test completed-run receipt should be ready")
        for record in commands:
            if record.get("label") in {"main", "summary"} and record.get("returncode") != 0:
                fail(
                    f"locked final-test completed-run command failed: "
                    f"label={record.get('label')} returncode={record.get('returncode')}"
                )
    else:
        if payload.get("preflight_only") is not True:
            fail("locked final-test preflight receipt should be marked preflight-only")
        if payload.get("status") not in {"preflight_ready", "blocked_by_gpu_preflight"}:
            fail(f"unexpected locked final-test preflight status: {payload.get('status')}")
        if any(record.get("returncode") is not None for record in commands):
            fail("preflight-only receipt should not execute command records")
        if payload.get("validation_bn_plan_entry_receipt_ready") is False:
            if not payload.get("risk_flags"):
                fail("blocked locked final-test preflight should carry a risk flag")
        elif payload.get("validation_bn_plan_entry_receipt_ready") is not True:
            fail("locked final-test preflight receipt missing readiness boolean")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    always_phrases = [
        "Validation/BatchNorm Rerun Receipt: locked_final_test_sgld_full_cifar",
        "GPU Preflight",
        "This file is generated by `scripts/run_validation_bn_rerun_plan_entry.py`.",
    ]
    state_phrase = "Preflight only: `False`" if locked_observed else "Preflight only: `True`"
    for phrase in [*always_phrases, state_phrase]:
        if phrase not in text:
            fail(f"locked final-test receipt markdown missing phrase: {phrase}")


def require_locked_final_test_protocol_audit() -> None:
    json_path = ROOT / "runs" / "locked_final_test_protocol_audit.json"
    doc_path = ROOT / "docs" / "locked_final_test_protocol_audit.md"
    payload = load_json(json_path)
    if payload.get("locked_final_test_protocol_audit_ready") is not True:
        fail(f"locked final-test protocol audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"locked final-test protocol audit has risk flags: {payload['risk_flags']}")
    if payload.get("config_mismatches"):
        fail(
            "locked final-test config should match validation-selected config except split: "
            f"{payload['config_mismatches']}"
        )
    checks = payload.get("checks", {})
    for key in [
        "validation_entry_observed",
        "validation_metrics_present",
        "validation_evaluation_split_val",
        "validation_fraction_0p1",
        "validation_subset_seeded",
        "validation_sampler_sgld",
        "locked_command_has_selection_source_run",
        "locked_command_has_selection_source_summary",
    ]:
        if checks.get(key) is not True:
            fail(f"locked final-test protocol check failed: {key}")
    paths = payload.get("paths", {})
    if not paths.get("validation_metrics"):
        fail("locked final-test protocol audit should point to validation metrics")
    for key in [
        "validation_summary_csv",
        "validation_summary_md",
        "locked_summary_csv",
        "locked_summary_md",
    ]:
        if not paths.get(key):
            fail(f"locked final-test protocol audit should point to {key}")
    if not paths.get("locked_run_root"):
        fail("locked final-test protocol audit should point to the locked run root")
    if payload.get("summary_expected_comparisons") != [
        "chain_start_magnitude_vs_tickets",
        "posterior_samples_vs_tickets",
        "posterior_modes_vs_tickets",
    ]:
        fail("locked final-test protocol audit should declare expected summary rows")
    required_columns = set(payload.get("summary_required_columns", []))
    if not {"run", "dataset", "model", "posterior_sampler", "comparison"}.issubset(
        required_columns
    ):
        fail("locked final-test protocol audit should declare required summary columns")
    summary_checks = payload.get("summary_checks", {})
    validation_summary = summary_checks.get("validation", {})
    if validation_summary.get("required") is not True:
        fail("validation summary artifacts should be required by the locked protocol audit")
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
        if validation_summary.get(key) is not True:
            fail(f"validation summary artifact check failed: {key}")
    if validation_summary.get("csv_row_count", 0) < 3:
        fail("validation summary artifact should include all expected comparison rows")
    locked_summary = summary_checks.get("locked", {})
    interpretation = payload.get("interpretation", {})
    for key in [
        "validation_selection_observed",
        "locked_final_test_must_match_validation_config_except_split",
        "validation_summary_artifacts_observed",
        "future_locked_summary_required_when_metrics_observed",
    ]:
        if interpretation.get(key) is not True:
            fail(f"locked final-test protocol interpretation check failed: {key}")
    open_flags = set(payload.get("open_risk_flags", []))
    if checks.get("locked_metrics_present") is True:
        for key in [
            "locked_entry_observed",
            "locked_evaluation_split_test",
            "locked_after_validation_selection",
            "locked_selection_source_run_matches",
            "locked_selection_source_summary_matches",
            "locked_selection_source_run_exists",
            "locked_selection_source_summary_exists",
        ]:
            if checks.get(key) is not True:
                fail(f"locked final-test completed-run check failed: {key}")
        if locked_summary.get("required") is not True:
            fail("locked summary artifacts should become required when metrics are present")
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
            if locked_summary.get(key) is not True:
                fail(f"locked summary artifact check failed: {key}")
        if locked_summary.get("csv_row_count", 0) < 3:
            fail("locked summary artifact should include all expected comparison rows")
        if "locked_final_test_metrics_not_observed" in open_flags:
            fail("completed locked final-test audit should not keep missing-metrics open risk")
        if interpretation.get("locked_final_test_observed") is not True:
            fail("locked final-test interpretation should mark completed run observed")
    else:
        if locked_summary.get("required") is not False:
            fail("locked summary artifacts should not be required before locked metrics exist")
        if "locked_final_test_metrics_not_observed" not in open_flags:
            fail("missing locked final-test metrics should remain an explicit open risk")
        if interpretation.get("locked_final_test_observed") is not False:
            fail("locked final-test interpretation should keep completed run unobserved")
        if (
            interpretation.get(
                "missing_locked_final_test_is_open_blocker_not_a_protocol_mismatch"
            )
            is not True
        ):
            fail("missing locked final-test should be classified as an open blocker")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    always_phrases = [
        "Locked Final-Test Protocol Audit",
        "validation_select_sgld_full_cifar",
        "locked_final_test_sgld_full_cifar",
        "Summary Artifact Checks",
        "locked summary is required as soon as locked metrics are observed",
        "This file is generated by `scripts/audit_locked_final_test_protocol.py`.",
    ]
    locked_observed = locked_final_test_observed()
    conditional_phrases = (
        []
        if locked_observed
        else ["locked_final_test_metrics_not_observed"]
    )
    for phrase in [*always_phrases, *conditional_phrases]:
        if phrase not in text:
            fail(f"locked final-test protocol markdown missing phrase: {phrase}")


def require_validation_bn_smoke_audit() -> None:
    json_path = ROOT / "runs" / "validation_bn_smoke_audit.json"
    doc_path = ROOT / "docs" / "validation_bn_smoke_audit.md"
    payload = load_json(json_path)
    if payload.get("validation_bn_smoke_ready") is not True:
        fail(f"validation/BN smoke audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"validation/BN smoke audit has risk flags: {payload['risk_flags']}")
    checks = payload.get("checks", {})
    for key in [
        "run_root_exists",
        "metrics_present",
        "summary_csv_present",
        "summary_md_present",
        "dataset_fake_cifar",
        "model_resnet20",
        "validation_fraction_positive",
        "evaluation_split_val",
        "subset_strategy_seeded",
        "posterior_bn_policy_recalibrate",
        "bn_recalibration_batches_recorded",
        "reference_val_size_positive",
        "mask_artifact_present",
        "smoke_uses_mask_artifact_schema",
    ]:
        if checks.get(key) is not True:
            fail(f"validation/BN smoke check failed: {key}")
    open_flags = set(payload.get("open_risk_flags", []))
    if bn_ablation_observed():
        if "full_cifar_bn_ablation_rerun_not_observed" in open_flags:
            fail(
                "validation/BN smoke should drop full_cifar_bn_ablation_rerun_not_observed "
                "once every bn_* plan entry is observed"
            )
    else:
        expected_open = {"full_cifar_bn_ablation_rerun_not_observed"}
        if not expected_open.issubset(open_flags):
            fail(f"validation/BN smoke missing open risks: {sorted(expected_open - open_flags)}")
    if "full_cifar_validation_selected_rerun_not_observed" in open_flags:
        fail("validation/BN smoke should now observe the full CIFAR validation-selected rerun")
    interpretation = payload.get("interpretation", {})
    for key in [
        "validation_split_path_smoked",
        "batchnorm_recalibration_path_smoked",
        "seeded_subset_path_smoked",
        "mask_artifact_path_smoked",
        "full_cifar_validation_selected_rerun_observed",
        "full_cifar_reruns_still_required",
    ]:
        if interpretation.get(key) is not True:
            fail(f"validation/BN smoke interpretation check failed: {key}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Validation/BatchNorm Smoke Audit",
        "validation split, seeded subset, BatchNorm",
        "required full CIFAR reruns",
        "This file is generated by `scripts/audit_validation_bn_smoke.py`.",
    ]:
        if phrase not in text:
            fail(f"validation/BN smoke markdown missing phrase: {phrase}")


def require_mode_ticket_alignment_artifact_audit() -> None:
    audit_path = ROOT / "runs" / "mode_ticket_alignment_artifact_audit.json"
    doc_path = ROOT / "docs" / "mode_ticket_alignment_artifact_audit.md"
    payload = load_json(audit_path)
    overall = payload.get("overall", {})
    if int(overall.get("run_count", 0)) < 7:
        fail("mode/ticket alignment artifact audit should cover seven full-data CIFAR runs")
    if int(overall.get("aligned_run_count", 0)) != 2:
        fail("mode/ticket alignment artifact audit should cover activation and weight alignment")
    if overall.get("aligned_rows_all_fail_layer_ks") is not True:
        fail("aligned direct rows should fail the layer-KS criterion")
    if overall.get("aligned_rows_all_fail_hamming_overlap") is not True:
        fail("aligned direct rows should fail the Hamming-overlap criterion")
    if overall.get("any_direct_equivalence_pass") is not False:
        fail("no audited direct run should pass full mode/ticket equivalence")
    if overall.get("direct_rows_all_collapse_to_one_basin") is not True:
        fail("audited direct runs should collapse posterior samples to one basin")
    if overall.get("raw_mask_artifacts_present") is not False:
        fail("current direct-run release should not claim saved raw mask artifacts")
    if int(overall.get("raw_mask_or_state_file_count", -1)) != 0:
        fail("current direct-run release should have zero raw mask/state files")
    if overall.get("posthoc_exhaustive_permutation_supported") is not False:
        fail("post-hoc exhaustive permutation support should be explicitly false")
    limitation = str(overall.get("posthoc_limitation_statement", ""))
    if "post-hoc exhaustive graph/permutation realignment is not supported" not in limitation:
        fail("mode/ticket alignment artifact audit missing limitation statement")

    runs = {
        str(run.get("label")): run
        for run in payload.get("runs", [])
        if isinstance(run, dict)
    }
    for label in [
        "CIFAR activation-aligned SGLD",
        "CIFAR weight-aligned SGLD",
        "CIFAR LowRank128 Laplace direct",
        "CIFAR JointDiagLap270k direct",
    ]:
        if label not in runs:
            fail(f"mode/ticket alignment artifact audit missing run: {label}")
    for label in ["CIFAR activation-aligned SGLD", "CIFAR weight-aligned SGLD"]:
        run = runs[label]
        row = run.get("direct_sample_row", {})
        if row.get("passes_layer_ks") is not False:
            fail(f"{label} should fail layer-KS after alignment")
        if row.get("passes_hamming_overlap") is not False:
            fail(f"{label} should fail Hamming-overlap after alignment")
        if float(row.get("activation_cka_hungarian_mean", 0.0)) <= 0.85:
            fail(f"{label} should retain high activation CKA")
        alignment = run.get("alignment", {})
        if int(alignment.get("target_frame_count", 0)) != 1:
            fail(f"{label} should record one seed-0 target frame")
    jointdiag = runs["CIFAR JointDiagLap270k direct"].get("direct_sample_row", {})
    if jointdiag.get("passes_layer_ks") is not False:
        fail("JointDiagLap270k audited direct row should fail layer-KS")
    if jointdiag.get("passes_hamming_overlap") is not False:
        fail("JointDiagLap270k audited direct row should fail Hamming-overlap")
    lowrank = runs["CIFAR LowRank128 Laplace direct"].get("direct_sample_row", {})
    if lowrank.get("passes_layer_ks") is not False:
        fail("LowRank128 audited direct row should still fail layer-KS")
    if lowrank.get("direct_equivalence_pass") is not False:
        fail("LowRank128 audited direct row should not pass full direct equivalence")

    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "post-hoc exhaustive graph/permutation realignment is not supported",
        "raw posterior/ticket mask or state tensors",
        "CIFAR activation-aligned SGLD",
        "CIFAR weight-aligned SGLD",
        "Raw mask/state artifacts present: `False`",
    ]:
        if phrase not in text:
            fail(f"mode/ticket alignment artifact audit doc missing phrase: {phrase}")


def require_mode_ticket_mask_artifact_smoke() -> None:
    root = ROOT / "runs" / "fake_cifar10_mode_ticket_mask_artifact_smoke"
    metrics_paths = sorted(root.glob("*/metrics.json"))
    if not metrics_paths:
        fail("mode/ticket mask-artifact smoke metrics are missing")
    metrics_path = metrics_paths[-1]
    payload = load_json(metrics_path)
    config = payload.get("config", {})
    if config.get("dataset") != "fake-cifar10" or config.get("model") != "resnet20":
        fail("mode/ticket mask-artifact smoke should be fake-CIFAR ResNet-20")
    if config.get("save_mask_artifacts") is not True:
        fail("mode/ticket mask-artifact smoke did not enable mask saving")
    if config.get("save_state_artifacts") is not True:
        fail("mode/ticket mask-artifact smoke did not enable state saving")
    artifact = payload.get("mask_artifacts", {})
    artifact_path = ROOT / str(artifact.get("path", ""))
    if not artifact_path.exists():
        fail(f"mode/ticket mask artifact is missing: {artifact_path}")
    if int(artifact.get("parameter_count", 0)) != 4350:
        fail("mode/ticket mask-artifact smoke should cover 4,350 parameters")
    expected_collections = {
        "chain_start",
        "posterior_sample",
        "posterior_mode",
        "ticket",
        "activation_aligned_chain_start",
        "activation_aligned_posterior_sample",
        "activation_aligned_posterior_mode",
        "activation_aligned_ticket",
    }
    collections = {
        str(row.get("name")): row
        for row in artifact.get("collections", [])
        if isinstance(row, dict)
    }
    missing = sorted(expected_collections - set(collections))
    if missing:
        fail(f"mode/ticket mask artifact missing collections: {missing}")
    for name in expected_collections:
        row = collections[name]
        if int(row.get("masks", 0)) != 2 or int(row.get("ids", 0)) != 2:
            fail(f"mode/ticket mask artifact collection should have two masks: {name}")
        if int(row.get("states", 0)) != 2:
            fail(f"mode/ticket mask artifact collection should have two states: {name}")

    with np.load(artifact_path, allow_pickle=False) as data:
        if int(data["artifact_schema_version"][0]) != 1:
            fail("mode/ticket mask artifact schema should be version 1")
        parameter_count = int(data["parameter_sizes"].sum())
        if parameter_count != 4350:
            fail("mode/ticket mask artifact parameter sizes should sum to 4,350")
        if int(data["parameter_names"].shape[0]) != 22:
            fail("mode/ticket mask artifact should store 22 parameter names")
        if "parameter_shapes_json" not in data.files:
            fail("mode/ticket mask artifact missing parameter_shapes_json")
        shapes = json.loads(str(data["parameter_shapes_json"]))
        if shapes.get("conv1.weight") != [2, 3, 3, 3]:
            fail("mode/ticket mask artifact has wrong conv1 shape metadata")
        if shapes.get("fc.weight") != [10, 8]:
            fail("mode/ticket mask artifact has wrong fc shape metadata")
        for key in [
            "masks__posterior_sample",
            "masks__ticket",
            "masks__activation_aligned_posterior_sample",
            "masks__activation_aligned_ticket",
        ]:
            if key not in data.files:
                fail(f"mode/ticket mask artifact missing key: {key}")
            value = data[key]
            if value.shape != (2, parameter_count):
                fail(f"mode/ticket mask artifact has wrong shape for {key}: {value.shape}")
            if value.dtype != np.uint8:
                fail(f"mode/ticket mask artifact masks must be uint8 for {key}")
            if not np.isin(value, [0, 1]).all():
                fail(f"mode/ticket mask artifact masks must be binary for {key}")
        for key in [
            "states__posterior_sample",
            "states__ticket",
            "states__activation_aligned_posterior_sample",
            "states__activation_aligned_ticket",
        ]:
            if key not in data.files:
                fail(f"mode/ticket state artifact missing key: {key}")
            value = data[key]
            if value.shape != (2, parameter_count):
                fail(f"mode/ticket state artifact has wrong shape for {key}: {value.shape}")
            if value.dtype != np.float32:
                fail(f"mode/ticket state artifact states must be float32 for {key}")
        metadata = json.loads(str(data["metadata_json"]))
        if metadata.get("mask_encoding") != "uint8_keep_mask_flattened_by_parameter_names":
            fail("mode/ticket mask artifact metadata missing mask encoding")
        if metadata.get("state_encoding") != "float32_flattened_by_parameter_names":
            fail("mode/ticket mask artifact metadata missing state encoding")
        if int(metadata.get("resnet_width", 0)) != 2:
            fail("mode/ticket mask artifact metadata missing resnet_width=2")
        if metadata.get("input_shape") != [3, 32, 32]:
            fail("mode/ticket mask artifact metadata missing input shape")

    doc_text = (
        ROOT / "docs" / "fake_cifar10_mode_ticket_mask_artifact_smoke.md"
    ).read_text(encoding="utf-8")
    for phrase in [
        "Mask Artifact Check",
        "--save-mask-artifacts --save-state-artifacts",
        "parameter_shapes_json",
        "masks__posterior_sample",
        "states__activation_aligned_posterior_sample",
    ]:
        if phrase not in doc_text:
            fail(f"mode/ticket mask artifact smoke doc missing phrase: {phrase}")


def require_mask_artifact_posthoc_audit() -> None:
    audit_path = ROOT / "runs" / "fake_cifar10_mode_ticket_mask_artifact_posthoc_audit.json"
    doc_path = ROOT / "docs" / "fake_cifar10_mode_ticket_mask_artifact_posthoc_audit.md"
    payload = load_json(audit_path)
    overall = payload.get("overall", {})
    if int(overall.get("schema_version", 0)) != 1:
        fail("mask artifact post-hoc audit should use schema version 1")
    if overall.get("dataset") != "fake-cifar10" or overall.get("model") != "resnet20":
        fail("mask artifact post-hoc audit should target fake-CIFAR ResNet-20")
    if int(overall.get("parameter_count", 0)) != 4350:
        fail("mask artifact post-hoc audit should cover 4,350 parameters")
    if int(overall.get("parameter_name_count", 0)) != 22:
        fail("mask artifact post-hoc audit should cover 22 parameter tensors")
    if int(overall.get("mask_collection_count", 0)) != 8:
        fail("mask artifact post-hoc audit should cover eight mask collections")
    if int(overall.get("state_collection_count", 0)) != 8:
        fail("mask artifact post-hoc audit should cover eight state collections")
    if overall.get("parameter_shapes_present") is not True:
        fail("mask artifact post-hoc audit should have parameter shapes")
    if int(overall.get("resnet_channel_key_count", 0)) != 19:
        fail("mask artifact post-hoc audit should expose 19 ResNet channel keys")
    if overall.get("required_collections_present") is not True:
        fail("mask artifact post-hoc audit missing required collections")
    if overall.get("record_level_posthoc_matching_supported") is not True:
        fail("mask artifact post-hoc audit should support record-level matching")
    if overall.get("local_channel_permutation_matching_supported") is not True:
        fail("mask artifact post-hoc audit should support local channel matching")
    if overall.get("exhaustive_graph_channel_permutation_supported") is not False:
        fail("mask artifact post-hoc audit must not claim exhaustive channel permutation support")
    if "full-data rerun" not in str(overall.get("limitation_statement", "")):
        fail("mask artifact post-hoc audit missing full-data rerun limitation")

    artifact_path = ROOT / str(payload.get("artifact_path", ""))
    if not artifact_path.exists():
        fail(f"mask artifact post-hoc audit references missing artifact: {artifact_path}")

    collections = {
        str(row.get("name")): row
        for row in payload.get("collections", [])
        if isinstance(row, dict)
    }
    for name in [
        "posterior_sample",
        "ticket",
        "activation_aligned_posterior_sample",
        "activation_aligned_ticket",
    ]:
        row = collections.get(name)
        if row is None:
            fail(f"mask artifact post-hoc audit missing collection: {name}")
        if int(row.get("mask_count", 0)) != 2 or int(row.get("state_count", 0)) != 2:
            fail(f"mask artifact post-hoc audit collection should have two records: {name}")
        if abs(float(row.get("keep_fraction_mean", 0.0)) - 0.7) > 1e-6:
            fail(f"mask artifact post-hoc audit collection keep fraction changed: {name}")

    comparisons = {
        (str(row.get("left")), str(row.get("right"))): row
        for row in payload.get("comparisons", [])
        if isinstance(row, dict)
    }
    required_comparisons = [
        ("posterior_sample", "ticket"),
        ("activation_aligned_posterior_sample", "activation_aligned_ticket"),
        ("posterior_sample", "activation_aligned_posterior_sample"),
        ("ticket", "activation_aligned_ticket"),
    ]
    for key in required_comparisons:
        row = comparisons.get(key)
        if row is None:
            fail(f"mask artifact post-hoc audit missing comparison: {key}")
        natural = row.get("natural_hamming", {}).get("mean")
        optimal = row.get("optimal_hamming", {}).get("mean")
        if not finite(natural) or not finite(optimal):
            fail(f"mask artifact post-hoc audit comparison has non-finite hamming: {key}")
        if float(optimal) - float(natural) > 1e-12:
            fail(f"mask artifact post-hoc audit optimal hamming worsens direct pairing: {key}")
        if int(row.get("same_index_pair_count", 0)) != 2:
            fail(f"mask artifact post-hoc audit should compare two same-index pairs: {key}")
        if int(row.get("optimal_pair_count", 0)) != 2:
            fail(f"mask artifact post-hoc audit should compare two optimal pairs: {key}")
        if row.get("state_distance") is None:
            fail(f"mask artifact post-hoc audit should include state distance: {key}")
        channel = row.get("channel_permutation")
        if not isinstance(channel, dict):
            fail(f"mask artifact post-hoc audit should include channel permutation: {key}")
        if int(channel.get("channel_key_count", 0)) != 19:
            fail(f"mask artifact post-hoc audit channel key count changed: {key}")
        channel_hamming = channel.get("channel_optimal_hamming", {}).get("mean")
        if not finite(channel_hamming):
            fail(f"mask artifact post-hoc audit channel hamming is non-finite: {key}")

    doc_text = doc_path.read_text(encoding="utf-8")
    for phrase in [
        "Mask Artifact Post-hoc Matching Audit",
        "Parameter shapes present: `True`",
        "Record-level post-hoc matching supported: `True`",
        "Local channel-permutation matching supported: `True`",
        "Exhaustive graph/channel permutation supported: `False`",
        "Local Channel Permutation",
        "not claim-level CIFAR evidence",
        "full-data permutation rerun remains open",
    ]:
        if phrase not in doc_text:
            fail(f"mask artifact post-hoc audit doc missing phrase: {phrase}")


def require_mode_ticket_artifact_storage_budget() -> None:
    payload = load_json(ROOT / "runs" / "mode_ticket_artifact_storage_budget.json")
    doc_path = ROOT / "docs" / "mode_ticket_artifact_storage_budget.md"
    if payload.get("model") != "resnet20" or payload.get("dataset") != "cifar10":
        fail("mode/ticket artifact storage budget should target CIFAR ResNet-20")
    if int(payload.get("resnet_width", 0)) != 16:
        fail("mode/ticket artifact storage budget should use ResNet width 16")
    if int(payload.get("parameter_count", 0)) != 270896:
        fail("mode/ticket artifact storage budget should cover 270,896 weight parameters")
    fake = payload.get("fake_cifar_fixture", {})
    fake_path = ROOT / str(fake.get("path", ""))
    if not fake_path.exists():
        fail("mode/ticket artifact storage budget references missing fake fixture")
    if int(fake.get("bytes", 0)) <= 200_000:
        fail("mode/ticket artifact storage budget fake fixture is unexpectedly small")
    rows = {
        str(row.get("name")): row
        for row in payload.get("scenarios", [])
        if isinstance(row, dict)
    }
    required = {
        "sgld_activation_aligned_save_states": (220, 220, 297_985_600),
        "csgld_independent_multichain_save_states": (170, 170, 230_261_600),
        "jointdiag_laplace_save_states": (60, 60, 81_268_800),
    }
    for name, (mask_records, state_records, total_bytes) in required.items():
        row = rows.get(name)
        if row is None:
            fail(f"mode/ticket artifact storage budget missing scenario: {name}")
        if int(row.get("mask_record_count_upper_bound", 0)) != mask_records:
            fail(f"mode/ticket artifact storage budget mask records changed: {name}")
        if int(row.get("state_record_count_upper_bound", 0)) != state_records:
            fail(f"mode/ticket artifact storage budget state records changed: {name}")
        if int(row.get("total_bytes_uncompressed", 0)) != total_bytes:
            fail(f"mode/ticket artifact storage budget total bytes changed: {name}")
    recommended = payload.get("recommended_next_rerun", {})
    if recommended.get("scenario") != "sgld_activation_aligned_save_states":
        fail("mode/ticket artifact storage budget recommended wrong scenario")
    command = str(recommended.get("command", ""))
    for phrase in [
        "--save-mask-artifacts --save-state-artifacts",
        "--alignment-method activation",
        "activation_aligned_saved_artifacts_r5_p0p3",
    ]:
        if phrase not in command:
            fail(f"mode/ticket artifact storage budget command missing phrase: {phrase}")
    if float(recommended.get("estimated_total_mib_uncompressed", 0.0)) < 280.0:
        fail("mode/ticket artifact storage budget recommended MiB too small")
    doc_text = doc_path.read_text(encoding="utf-8")
    for phrase in [
        "Mode/Ticket Artifact Storage Budget",
        "Weight parameter count: `270896`",
        "sgld_activation_aligned_save_states",
        "284.18 MiB",
        "--save-mask-artifacts --save-state-artifacts",
    ]:
        if phrase not in doc_text:
            fail(f"mode/ticket artifact storage budget doc missing phrase: {phrase}")


def require_full_data_saved_artifact_posthoc_audit() -> None:
    run_root = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3"
    )
    run_dir = run_root / "20260506_230706"
    metrics_path = run_dir / "metrics.json"
    mask_path = run_dir / "mask_artifacts.npz"
    summary_csv_path = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3_summary.csv"
    )
    summary_doc_path = (
        ROOT
        / "docs"
        / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3.md"
    )
    posthoc_json_path = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.json"
    )
    posthoc_doc_path = (
        ROOT
        / "docs"
        / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.md"
    )
    for path, min_size in [
        (metrics_path, 50_000),
        (mask_path, 100_000_000),
        (summary_csv_path, 1_000),
        (summary_doc_path, 1_000),
        (posthoc_json_path, 10_000),
        (posthoc_doc_path, 1_000),
    ]:
        if not path.exists() or path.stat().st_size < min_size:
            fail(f"full-data saved-artifact output missing or too small: {path}")

    metrics = load_json(metrics_path)
    config = metrics.get("config", {})
    if config.get("dataset") != "cifar10" or config.get("model") != "resnet20":
        fail("full-data saved-artifact run should target CIFAR-10 ResNet-20")
    if config.get("seeds") != [0, 1, 2, 3, 4]:
        fail("full-data saved-artifact run should use seeds 0..4")
    if int(config.get("epochs", 0)) != 30 or int(config.get("imp_rounds", 0)) != 5:
        fail("full-data saved-artifact run should use the long30/r5 protocol")
    if config.get("alignment_method") != "activation":
        fail("full-data saved-artifact run should use activation alignment")
    if config.get("save_mask_artifacts") is not True:
        fail("full-data saved-artifact run should save masks")
    if config.get("save_state_artifacts") is not True:
        fail("full-data saved-artifact run should save states")
    artifact = metrics.get("mask_artifacts", {})
    if int(artifact.get("parameter_count", 0)) != 270896:
        fail("full-data mask artifact should cover 270,896 parameters")
    if artifact.get("save_states") is not True:
        fail("full-data mask artifact should include states")
    collection_counts = {
        str(row.get("name")): (int(row.get("masks", 0)), int(row.get("states", 0)))
        for row in artifact.get("collections", [])
        if isinstance(row, dict)
    }
    expected_counts = {
        "posterior_sample": (50, 50),
        "ticket": (5, 5),
        "activation_aligned_posterior_sample": (50, 50),
        "activation_aligned_ticket": (5, 5),
        "posterior_mode": (1, 1),
        "activation_aligned_posterior_mode": (1, 1),
    }
    for name, expected in expected_counts.items():
        if collection_counts.get(name) != expected:
            fail(f"full-data mask artifact collection count changed: {name}")

    with summary_csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 6:
        fail("full-data saved-artifact summary should contain six comparison rows")
    by_comparison = {row["comparison"]: row for row in rows}
    for name in [
        "posterior_samples_vs_tickets",
        "activation_aligned_posterior_samples_vs_tickets",
    ]:
        row = by_comparison.get(name)
        if row is None:
            fail(f"full-data saved-artifact summary missing row: {name}")
        if int(float(row["left_count"])) != 50 or int(float(row["right_count"])) != 5:
            fail(f"full-data saved-artifact row count changed: {name}")
        if float(row["layer_ks_pvalue"]) >= 1e-6:
            fail(f"full-data saved-artifact row should reject layer KS: {name}")
        if float(row["hamming_overlap"]) != 0.0:
            fail(f"full-data saved-artifact row should have zero Hamming overlap: {name}")
        if float(row["logit_cka_hungarian_mean"]) < 0.93:
            fail(f"full-data saved-artifact row CKA unexpectedly low: {name}")
        if str(row["passes_layer_ks"]) != "False" or str(row["passes_hamming_overlap"]) != "False":
            fail(f"full-data saved-artifact row should fail mask-distribution thresholds: {name}")

    posthoc = load_json(posthoc_json_path)
    overall = posthoc.get("overall", {})
    if overall.get("dataset") != "cifar10" or overall.get("model") != "resnet20":
        fail("full-data posthoc audit should target CIFAR ResNet-20")
    if int(overall.get("parameter_count", 0)) != 270896:
        fail("full-data posthoc audit should cover 270,896 parameters")
    if overall.get("record_level_posthoc_matching_supported") is not True:
        fail("full-data posthoc audit should support record-level matching")
    if overall.get("local_channel_permutation_matching_supported") is not False:
        fail("full-data posthoc audit should not claim local channel matching when capped")
    if int(overall.get("channel_permutation_skipped_count", 0)) != 7:
        fail("full-data posthoc audit should mark capped channel searches")
    if int(overall.get("max_channel_pair_count", 0)) != 1:
        fail("full-data posthoc audit should record the channel-pair cap")
    comparisons = {
        (str(row.get("left")), str(row.get("right"))): row
        for row in posthoc.get("comparisons", [])
        if isinstance(row, dict)
    }
    key = ("posterior_sample", "ticket")
    row = comparisons.get(key)
    if row is None:
        fail("full-data posthoc audit missing posterior_sample vs ticket")
    natural = float(row["natural_hamming"]["mean"])
    optimal = float(row["optimal_hamming"]["mean"])
    if not (0.20 < optimal < natural < 0.26):
        fail("full-data posthoc posterior-ticket hamming changed")
    skipped = posthoc.get("skipped_comparisons", [])
    if len(skipped) != 1 or int(skipped[0].get("pair_count", 0)) != 2500:
        fail("full-data posthoc should skip the 50x50 raw-vs-aligned comparison")

    doc_text = posthoc_doc_path.read_text(encoding="utf-8")
    for phrase in [
        "full-data CIFAR saved-artifact evidence",
        "full-data saved-artifact rerun is complete",
        "Local channel-permutation matching was not run",
        "record-level evidence plus a saved artifact",
    ]:
        if phrase not in doc_text:
            fail(f"full-data posthoc doc missing phrase: {phrase}")
    summary_text = summary_doc_path.read_text(encoding="utf-8")
    for phrase in [
        "Posterior-to-chain-start Hamming mean: 0.0511",
        "posterior_samples_vs_tickets",
        "activation_aligned_posterior_samples_vs_tickets",
    ]:
        if phrase not in summary_text:
            fail(f"full-data saved-artifact summary doc missing phrase: {phrase}")


def require_full_data_global_channel_permutation_audit() -> None:
    json_path = (
        ROOT
        / "runs"
        / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_global_channel_audit.json"
    )
    doc_path = (
        ROOT
        / "docs"
        / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_global_channel_audit.md"
    )
    if not json_path.exists() or json_path.stat().st_size < 20_000:
        fail("full-data global channel audit JSON missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 1_000:
        fail("full-data global channel audit doc missing or too small")
    payload = load_json(json_path)
    overall = payload.get("overall", {})
    if overall.get("dataset") != "cifar10" or overall.get("model") != "resnet20":
        fail("full-data global channel audit should target CIFAR ResNet-20")
    if int(overall.get("parameter_count", 0)) != 270896:
        fail("full-data global channel audit should cover 270,896 parameters")
    if int(overall.get("resnet_channel_key_count", 0)) != 19:
        fail("full-data global channel audit should cover 19 channel keys")
    if overall.get("objective") != "mask":
        fail("full-data global channel audit should optimize mask objective")
    if int(overall.get("max_iters", 0)) != 6:
        fail("full-data global channel audit iteration budget changed")
    if int(overall.get("comparison_count", 0)) != 6:
        fail("full-data global channel audit should include six comparisons")
    if overall.get("global_channel_coordinate_descent_supported") is not True:
        fail("full-data global channel audit should support coordinate descent")
    if overall.get("exhaustive_graph_channel_permutation_supported") is not False:
        fail("full-data global channel audit must not claim exhaustive search")

    rows = {
        (str(row.get("left")), str(row.get("right"))): row
        for row in payload.get("comparisons", [])
        if isinstance(row, dict)
    }
    required = [
        ("posterior_sample", "ticket"),
        ("activation_aligned_posterior_sample", "activation_aligned_ticket"),
        ("posterior_mode", "ticket"),
        ("activation_aligned_chain_start", "activation_aligned_ticket"),
    ]
    for key in required:
        if key not in rows:
            fail(f"full-data global channel audit missing comparison: {key}")
    raw = rows[("posterior_sample", "ticket")]
    raw_hamming = float(raw["raw_record_hamming"]["mean"])
    global_hamming = float(raw["global_channel_hamming"]["mean"])
    global_overlap = float(raw["global_channel_support_overlap_min"]["mean"])
    if not (0.20 < global_hamming < raw_hamming < 0.22):
        fail("raw posterior/ticket global channel Hamming changed")
    if global_overlap >= 0.40:
        fail("raw posterior/ticket global channel overlap unexpectedly high")
    aligned = rows[
        ("activation_aligned_posterior_sample", "activation_aligned_ticket")
    ]
    aligned_global = float(aligned["global_channel_hamming"]["mean"])
    aligned_improvement = float(aligned["hamming_improvement"]["mean"])
    if not (0.20 < aligned_global < 0.22):
        fail("aligned posterior/ticket global channel Hamming changed")
    if aligned_improvement <= 0.03:
        fail("aligned posterior/ticket channel optimization should reduce frame mismatch")
    mode = rows[("posterior_mode", "ticket")]
    if float(mode["global_channel_hamming"]["mean"]) <= 0.20:
        fail("posterior mode global channel Hamming should remain non-ticket-like")

    doc_text = doc_path.read_text(encoding="utf-8")
    for phrase in [
        "Full-data Global Channel Permutation Audit",
        "block-coordinate descent with exact per-key Hungarian updates",
        "Global-channel Hamming",
        "0.2105",
        "channel relabeling does not rescue",
        "not an exhaustive graph-isomorphism proof",
    ]:
        if phrase not in doc_text:
            fail(f"full-data global channel audit doc missing phrase: {phrase}")


def require_exhaustive_channel_permutation_feasibility_audit() -> None:
    json_path = ROOT / "runs" / "resnet_channel_permutation_exhaustive_feasibility_audit.json"
    doc_path = ROOT / "docs" / "resnet_channel_permutation_exhaustive_feasibility_audit.md"
    if not json_path.exists() or json_path.stat().st_size < 5_000:
        fail("exhaustive channel permutation feasibility JSON missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 1_000:
        fail("exhaustive channel permutation feasibility doc missing or too small")
    payload = load_json(json_path)
    overall = payload.get("overall", {})
    if overall.get("stage1_exact_enumeration_supported") is not True:
        fail("exhaustive feasibility audit should support stage-1 exact enumeration")
    if int(overall.get("stage1_parameter_count", 0)) != 270:
        fail("exhaustive feasibility audit stage-1 parameter count changed")
    if int(overall.get("stage1_exact_permutation_count", 0)) != 128:
        fail("exhaustive feasibility audit should enumerate 128 stage-1 assignments")
    if overall.get("stage1_coordinate_descent_all_exact") is not True:
        fail("stage-1 coordinate-descent audit should match exact enumeration")
    if overall.get("full_exhaustive_channel_permutation_supported") is not False:
        fail("exhaustive feasibility audit should not claim full-data exhaustive support")
    full_log10 = float(overall.get("full_log10_permutation_count", 0.0))
    if not (800.0 < full_log10 < 900.0):
        fail("full-data channel permutation search-space estimate changed")
    search_spaces = payload.get("search_spaces", {})
    stage1 = search_spaces.get("fake_stage1_subgraph", {})
    full = search_spaces.get("full_cifar_artifact", {})
    if int(stage1.get("channel_key_count", 0)) != 7:
        fail("stage-1 exact subgraph should contain seven channel keys")
    if int(full.get("channel_key_count", 0)) != 19:
        fail("full CIFAR search-space estimate should contain 19 channel keys")
    if full.get("channel_count_histogram") != {"16": 7, "32": 6, "64": 6}:
        fail("full CIFAR channel-count histogram changed")
    rows = {
        (str(row.get("left")), str(row.get("right"))): row
        for row in payload.get("exact_stage1_comparisons", [])
        if isinstance(row, dict)
    }
    ticket = rows.get(("ticket", "activation_aligned_ticket"))
    chain = rows.get(("chain_start", "activation_aligned_chain_start"))
    posterior = rows.get(("posterior_sample", "ticket"))
    aligned = rows.get(
        ("activation_aligned_posterior_sample", "activation_aligned_ticket")
    )
    if ticket is None or chain is None or posterior is None or aligned is None:
        fail("exhaustive feasibility audit missing expected stage-1 comparisons")
    for row in [ticket, chain, posterior, aligned]:
        if row.get("coordinate_descent_matches_exact") is not True:
            fail("coordinate descent should match exact enumeration on stage-1 audit")
    if float(ticket["exact_global_hamming"]["mean"]) != 0.0:
        fail("ticket raw-vs-aligned stage-1 exact Hamming should be zero")
    if float(chain["exact_global_hamming"]["mean"]) != 0.0:
        fail("chain-start raw-vs-aligned stage-1 exact Hamming should be zero")
    if float(posterior["exact_global_hamming"]["mean"]) >= 0.02:
        fail("fake stage-1 posterior-ticket exact Hamming unexpectedly high")
    if float(aligned["exact_improvement"]["mean"]) <= 0.04:
        fail("fake stage-1 aligned posterior/ticket exact audit should remove frame mismatch")
    doc_text = doc_path.read_text(encoding="utf-8")
    for phrase in [
        "Exhaustive Channel Permutation Feasibility Audit",
        "fake stage-1 subgraph",
        "Stage-1 exact assignments: `128`",
        "Coordinate descent matches exact enumeration: `True`",
        "full CIFAR artifact",
        "10^840.4",
        "infeasible and unimplemented",
    ]:
        if phrase not in doc_text:
            fail(f"exhaustive feasibility audit doc missing phrase: {phrase}")


def require_calibration_and_learned_masks(stats: dict[str, Any]) -> None:
    sources = {row["source"] for row in stats["calibration_ood"]}
    required_sources = {
        "dense",
        "imp",
        "swag_ensemble",
        "learned_random_0",
        "gem_miner",
        "variational_prune",
    }
    missing = sorted(required_sources - sources)
    if missing:
        fail(f"calibration/OOD summary missing sources: {missing}")
    for row in stats["calibration_ood"]:
        if row["source"] in required_sources:
            if int(row["id_accuracy"]["n"]) != 5:
                fail(f"calibration/OOD row is not five-seed: {row['source']}")
            if not finite(row["ood_msp_auroc"]["mean"]):
                fail(f"calibration/OOD row has non-finite OOD AUROC: {row['source']}")
    variational = rows_matching(stats["variational_pruning"], source="variational_prune")
    if not variational:
        fail("digits variational pruning summary missing variational_prune row")
    if float(variational[0]["accuracy_minus_imp"]["mean"]) >= 0.0:
        fail("digits variational pruning should not beat IMP in current evidence")
    learned_support = stats["trajectory_mask_training"]
    for source in ["gem_miner", "variational_prune", "hard_concrete"]:
        rows = rows_matching(learned_support, source=source)
        if not rows:
            fail(f"CIFAR learned-mask support row missing: {source}")
        row = rows[0]
        if int(row["trained_accuracy"]["n"]) != 5:
            fail(f"CIFAR learned-mask support row is not five-seed: {source}")
        if float(row["accuracy_minus_imp"]["mean"]) >= 0.0:
            fail(f"CIFAR learned-mask row should remain below IMP: {source}")
        if float(row["source_to_imp"]["mean"]) >= 0.10:
            fail(f"CIFAR learned-mask support should stay random-scale: {source}")
    hard = rows_matching(learned_support, source="hard_concrete")[0]
    if float(hard["trained_accuracy"]["mean"]) >= 0.50:
        fail("CIFAR hard-concrete full-data row should not be competitive")


def require_residual_process(stats: dict[str, Any]) -> None:
    process_rows = stats["residual_imp_process_round_exclusion"]
    final_rows = [
        row
        for row in process_rows
        if row.get("variant") == "round_excluded_oracle_final_imp_residual"
    ]
    if not final_rows:
        fail("round-exclusion process intervention rows are missing")
    if not all(int(row["trained_accuracy"]["n"]) == 5 for row in final_rows):
        fail("round-exclusion process rows must be five-seed summaries")
    layer_rows = stats["residual_imp_process_layer_exclusion_pairs"]
    layer_rms_r5 = [
        row
        for row in layer_rows
        if row.get("base_source") == "traj_rms_abs"
        and int(row.get("process_round")) == 5
        and abs(float(row.get("alpha")) - 0.5) < 1e-12
    ]
    if not layer_rms_r5:
        fail("tensor-matched round-exclusion RMS round-5 pair row is missing")
    row = layer_rms_r5[0]
    if int(row["round_minus_layer_excluded"]["n"]) != 5:
        fail("tensor-matched round-exclusion row must be five-seed")
    if float(row["round_minus_layer_excluded"]["mean"]) <= 0.0:
        fail("round-selected process residual should beat tensor-matched replacement")
    if int(row["round_minus_layer_excluded"]["positive"]) < 4:
        fail("tensor-matched round-exclusion paired wins are unexpectedly weak")
    tensor_score_rows = stats["residual_imp_process_tensor_score_exclusion_pairs"]
    tensor_score_rms_r5 = [
        row
        for row in tensor_score_rows
        if row.get("base_source") == "traj_rms_abs"
        and int(row.get("process_round")) == 5
        and abs(float(row.get("alpha")) - 0.5) < 1e-12
    ]
    if not tensor_score_rms_r5:
        fail("tensor+score-matched round-exclusion RMS round-5 pair row is missing")
    row = tensor_score_rms_r5[0]
    if int(row["round_minus_tensor_score_excluded"]["n"]) != 5:
        fail("tensor+score-matched round-exclusion row must be five-seed")
    if float(row["round_minus_tensor_score_excluded"]["mean"]) <= 0.0:
        fail("round-selected process residual should beat tensor+score-matched replacement")
    if int(row["round_minus_tensor_score_excluded"]["positive"]) < 4:
        fail("tensor+score-matched round-exclusion paired wins are unexpectedly weak")
    if (
        float(row["tensor_score_excluded_oracle_overlap"]["mean"])
        <= float(row["layer_excluded_oracle_overlap"]["mean"])
    ):
        fail("tensor+score replacement should improve oracle overlap over tensor-only replacement")
    projection_rows = stats["residual_imp_process_projection_pairs"]
    projection_rms_r5 = [
        row
        for row in projection_rows
        if row.get("base_source") == "traj_rms_abs"
        and int(row.get("process_round")) == 5
        and abs(float(row.get("alpha")) - 0.5) < 1e-12
    ]
    if not projection_rms_r5:
        fail("residualized-score projection RMS round-5 pair row is missing")
    row = projection_rms_r5[0]
    if int(row["round_minus_residualized"]["n"]) != 5:
        fail("residualized-score projection row must be five-seed")
    if float(row["round_minus_residualized"]["mean"]) <= 0.0:
        fail("round-selected process score should beat residualized score")
    if int(row["round_minus_residualized"]["positive"]) < 4:
        fail("residualized-score projection paired wins are unexpectedly weak")
    if float(row["round_minus_residualized_oracle"]["mean"]) <= 0.10:
        fail("residualized projection should materially lower oracle overlap")
    posterior_projection_rows = stats[
        "residual_imp_process_posterior_projection_pairs"
    ]
    posterior_projection_rms_r5 = [
        row
        for row in posterior_projection_rows
        if row.get("base_source") == "traj_rms_abs"
        and int(row.get("process_round")) == 5
        and abs(float(row.get("alpha")) - 0.5) < 1e-12
    ]
    if not posterior_projection_rms_r5:
        fail("posterior-residualized projection RMS round-5 pair row is missing")
    row = posterior_projection_rms_r5[0]
    if int(row["round_minus_residualized"]["n"]) != 5:
        fail("posterior-residualized projection row must be five-seed")
    if float(row["round_minus_residualized"]["mean"]) <= 0.0:
        fail("round-selected process score should beat posterior-residualized score")
    if int(row["round_minus_residualized"]["positive"]) != 5:
        fail("posterior-residualized projection should have 5/5 paired accuracy wins")
    if float(row["round_minus_residualized_oracle"]["mean"]) <= 0.18:
        fail("posterior-residualized projection should materially lower oracle overlap")
    learned_subspace_rows = stats[
        "residual_imp_process_learned_subspace_pairs"
    ]
    learned_subspace_rms_r5 = [
        row
        for row in learned_subspace_rows
        if row.get("base_source") == "traj_rms_abs"
        and int(row.get("process_round")) == 5
        and abs(float(row.get("alpha")) - 0.5) < 1e-12
    ]
    if not learned_subspace_rms_r5:
        fail("learned-subspace residualized projection RMS round-5 pair row is missing")
    row = learned_subspace_rms_r5[0]
    if int(row["round_minus_residualized"]["n"]) != 5:
        fail("learned-subspace residualized projection row must be five-seed")
    if float(row["round_minus_residualized"]["mean"]) <= 0.0:
        fail("round-selected process score should beat learned-subspace residualized score")
    if int(row["round_minus_residualized"]["positive"]) != 5:
        fail("learned-subspace projection should have 5/5 paired accuracy wins")
    if float(row["round_minus_residualized_oracle"]["mean"]) <= 0.18:
        fail("learned-subspace projection should materially lower oracle overlap")


def require_text_evidence() -> None:
    main_tex = " ".join(
        (ROOT / "paper" / "main.tex").read_text(encoding="utf-8").split()
    )
    submission_audit = " ".join(
        (ROOT / "docs" / "submission_readiness_audit.md").read_text(encoding="utf-8").split()
    )
    consistency_targets = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "docs/next_experiment_protocol.md": (
            ROOT / "docs" / "next_experiment_protocol.md"
        ).read_text(encoding="utf-8"),
        "docs/negative_result_paper_plan.md": (
            ROOT / "docs" / "negative_result_paper_plan.md"
        ).read_text(encoding="utf-8"),
        "docs/experiment_log.md": (ROOT / "docs" / "experiment_log.md").read_text(
            encoding="utf-8"
        ),
    }
    # Evidence anchors. These track the post-revision manuscript wording: the
    # paper was restructured to elevate the positive trajectory/process account,
    # add a pre-registered-gate framing, a graded support-equivalence finding,
    # and a TopK proposition, and several result paragraphs were compressed.
    expected_phrases = [
        "posterior supports beat uniform random masks in 58 of",
        "raw-parameter basin entropy is 0.0 nats",
        "full-data CIFAR-10 ResNet-20 strengthens",
        "Channel alignment does not change this conclusion",
        "weight-correlation alignment",
        "block-coordinate ResNet channel audit",
        "exact stage-1 enumeration",
        "75 cyclical-SGLD posterior samples",
        "rank-16/32/64/128 low-rank Laplace",
        "selected/tensor-block/joint-group full-covariance Laplace",
        "five exact block-diagonal and joint-group rows covering 22,064",
        "full 270,896-weight vector",
        "full-network exact/full-covariance Laplace",
        "exact dense full-network Laplace check",
        "linear connectivity audit",
        "orthogonal landscape diagnostics",
        "553.1 GiB",
        "tensor-matched excluded oracle",
        "tensor+score-matched oracle",
        "residualized round-score projection",
        "round-vs-residualized accuracy gap",
        "diagonal-Laplace posterior score subspace",
        "learned trajectory/process subspace",
        "Representative five-seed CIFAR-10 ResNet-20 epoch-1 rewind movement",
        "Generated Evidence Tables",
        "support-equivalence claim",
        "Scope of the claim",
        "Support-equivalence is graded",
        "pre-specified}, falsifiable",
        "What Winning Tickets Are",
        "Proposition~\\ref{prop:topk}",
        "Exploratory robustness: non-residual architecture (seed-level cell)",
        "non-residual three-convolution",
        "TinyCNN",
        "posterior-to-chain-start Hamming 0.061",
        "Validation-derived locked-test predictions",
        "all three derivable predictions",
        "three first-class contributions",
        "reusable posterior-vs-IMP audit framework",
        "underperforms IMP by 2.3 percentage points",
        "Anticipated Reviewer Objections",
        "Why rank-bounded posteriors should struggle",
        "We do not formalise",
        "Positive prediction: cross-seed mask transfer",
        "Dataset robustness: CIFAR-100 with a validation-selected locked test",
        "exploratory five-seed direct probe on",
        "locked CIFAR-100 result is \\emph{stronger}",
        "The pass is replicable, not single-run noise",
        "a replicated single-axis pass is still not the distributional",
        "explicit multiple-comparisons exposure",
        "Strong and weak forms of the hypothesis",
        "A finite-sample form, verified on saved states",
        "permutation-\\emph{invariant} metric closes this objection",
        "Gromov--Wasserstein",
        "survive Holm--Bonferroni",
        "TOST reanalysis",
        "Bayesian and learned-mask pruning",
        "standing open-challenge protocol",
        "non-residual---but not BN-free---robustness point",
        "Mask-overlap metric, made precise",
        "pairwise-distance histograms",
    ]
    for phrase in expected_phrases:
        if phrase not in main_tex:
            fail(f"paper/main.tex missing expected evidence phrase: {phrase}")
    expected_audit_phrases = [
        "posterior supports beat random masks in 58/59 groups",
        "0/59 groups",
        "55/57 groups",
        "20-snapshot full-network SWAG movement row",
        "block-diagonal",
        "tensor-matched round-exclusion",
        "tensor+score-matched round-exclusion",
        "residualized-score projection",
        "posterior-residualized",
        "learned-subspace residualized",
        "scoped support-equivalence claim",
        "hard-concrete L0 gate baseline",
        "post-hoc exhaustive graph/permutation realignment",
        "structured global channel audit",
        "exact stage-1 enumeration",
        "exact dense full-network Laplace sanity",
        "linear connectivity barrier audit",
    ]
    for phrase in expected_audit_phrases:
        if phrase not in submission_audit:
            fail(f"submission readiness audit missing expected evidence phrase: {phrase}")
    stale_audit_phrases = [
        "41/42",
        "38/40",
        "posterior beats random in 44/45",
        "posterior supports beat random in 44/45",
        "44/45 grouped support-overlap comparisons",
        "0/45 comparisons",
        "33/45",
        "12/45",
        "41/43 grouped comparisons",
        "48/49",
        "0/49",
        "45/47",
        "52/53",
        "0/53",
        "49/51",
        "52 of 53",
        "49 of 51",
        "53/54",
        "0/54",
        "50/52",
        "54/58",
        "57/58",
        "0/58",
        "54/56",
        "53 of 54",
        "50 of 52",
    ]
    for phrase in stale_audit_phrases:
        if phrase in submission_audit:
            fail(f"submission readiness audit contains stale count: {phrase}")
    for doc_path, text in consistency_targets.items():
        for phrase in stale_audit_phrases:
            if phrase in text:
                fail(f"{doc_path} contains stale mode-distribution count: {phrase}")


def require_bibliography() -> None:
    main_tex = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    refs = (ROOT / "paper" / "refs.bib").read_text(encoding="utf-8")
    cited_keys: set[str] = set()
    for match in re.finditer(r"\\cite[a-zA-Z*]*\{([^}]*)\}", main_tex):
        cited_keys.update(
            key.strip()
            for key in match.group(1).split(",")
            if key.strip()
        )
    bib_keys = set(re.findall(r"^@\w+\{([^,]+),", refs, flags=re.MULTILINE))
    missing = sorted(cited_keys - bib_keys)
    if missing:
        fail(f"paper/main.tex cites keys missing from paper/refs.bib: {missing}")
    expected_phrases = [
        "@inproceedings{paul2023unmasking",
        "Paul, Mansheej and Chen, Feng and Larsen, Brett W.",
        "@inproceedings{sakamoto2022pacbayes",
        "Sakamoto, Keitaro and Sato, Issei",
        "Analyzing Lottery Ticket Hypothesis from PAC-Bayesian Theory Perspective",
        "@misc{kuhn2026bayesian",
        "Kuhn, Nicholas and Weyrauch, Arvid",
        "2602.18825",
    ]
    for phrase in expected_phrases:
        if phrase not in refs:
            fail(f"paper/refs.bib missing expected citation metadata: {phrase}")


def require_reference_integrity_audit() -> None:
    json_path = ROOT / "runs" / "reference_integrity_audit.json"
    doc_path = ROOT / "docs" / "reference_integrity_audit.md"
    payload = load_json(json_path)
    if payload.get("reference_integrity_audit_ready") is not True:
        fail(f"reference integrity audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"reference integrity audit has risk flags: {payload['risk_flags']}")
    if int(payload.get("cited_key_count", 0)) < 10:
        fail("reference integrity audit should see the paper citations")
    checks = payload.get("interpretation", {})
    for key in [
        "all_cited_keys_have_bib_entries",
        "all_cited_entries_have_required_fields",
        "no_duplicate_bib_keys",
        "no_placeholder_metadata_detected",
        "key_method_and_competitor_metadata_present",
        "all_cited_entries_have_expected_metadata_smoke",
        "not_a_plagiarism_detector",
    ]:
        if checks.get(key) is not True:
            fail(f"reference integrity audit interpretation check failed: {key}")
    if int(payload.get("expected_metadata_checked_key_count", 0)) != int(
        payload.get("cited_key_count", 0)
    ):
        fail("reference integrity audit should metadata-check every cited key")
    open_flags = set(payload.get("open_risk_flags", []))
    if "formal_plagiarism_screening_not_performed" not in open_flags:
        fail("reference integrity audit should keep formal plagiarism screening open")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Reference Integrity Audit",
        "not a formal plagiarism detector",
        "Missing cited bib entries: `[]`",
        "Expected metadata checked keys:",
        "This file is generated by `scripts/audit_reference_integrity.py`.",
    ]:
        if phrase not in text:
            fail(f"reference integrity audit markdown missing phrase: {phrase}")


def require_manuscript_originality_audit() -> None:
    json_path = ROOT / "runs" / "manuscript_originality_audit.json"
    doc_path = ROOT / "docs" / "manuscript_originality_audit.md"
    payload = load_json(json_path)
    if payload.get("manuscript_originality_audit_ready") is not True:
        fail(f"manuscript originality audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"manuscript originality audit has risk flags: {payload['risk_flags']}")
    if int(payload.get("sentence_count", 0)) < 50:
        fail("manuscript originality audit scanned too few long prose sentences")
    if payload.get("placeholder_findings") not in ([], None):
        fail("manuscript originality audit found placeholder/copy markers")
    if payload.get("duplicate_sentence_findings") not in ([], None):
        fail("manuscript originality audit found duplicate long sentences")
    if payload.get("repeated_ngram_findings") not in ([], None):
        fail("manuscript originality audit found repeated long n-grams")
    related = payload.get("related_work_citation_coverage", {})
    if not isinstance(related, dict) or related.get("section_present") is not True:
        fail("manuscript originality audit should find the Related Work section")
    if related.get("paragraphs_without_citation") not in ([], None):
        fail("manuscript originality audit found uncited related-work paragraphs")
    claim_scope = payload.get("claim_scope_audit", {})
    required_scope = claim_scope.get("required_scope_phrases", [])
    if len(required_scope) < 7:
        fail("manuscript originality audit should cover the required claim-scope phrases")
    missing_scope = [row for row in required_scope if row.get("present") is not True]
    if missing_scope:
        fail(f"manuscript missing required claim-scope phrases: {missing_scope}")
    required_text = {row.get("phrase") for row in required_scope}
    locked_observed_local = locked_final_test_observed()
    required_guard_phrases = [
        "under the posterior families and CIFAR-10/MNIST/Fashion-MNIST settings tested here",
        "controlled negative result under the posterior approximations we can currently test",
        "Pooled direct mode/ticket p-values over posterior samples are descriptive",
        "BatchNorm buffers in sampled state dictionaries",
        "exact dense full-network CIFAR posterior remains absent",
    ]
    if locked_observed_local:
        required_guard_phrases.append("locked final-test rerun has been completed")
    else:
        required_guard_phrases.append("locked final test rerun is still required")
    for phrase in required_guard_phrases:
        if phrase not in required_text:
            fail(f"manuscript originality audit missing claim-scope guard phrase: {phrase}")
    if claim_scope.get("forbidden_overclaim_findings") not in ([], None):
        fail("manuscript originality audit found forbidden overclaim wording")
    checks = payload.get("interpretation", {})
    for key in [
        "local_prose_screen_only",
        "not_a_formal_plagiarism_detector",
        "formal_external_screening_still_required",
        "claim_scope_overclaim_guard_enabled",
    ]:
        if checks.get(key) is not True:
            fail(f"manuscript originality audit interpretation check failed: {key}")
    open_flags = set(payload.get("open_risk_flags", []))
    if "formal_external_plagiarism_database_screen_not_performed" not in open_flags:
        fail("manuscript originality audit should keep formal external screening open")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Manuscript Originality Audit",
        "not a formal plagiarism detector",
        "Claim Scope Guard",
        "Forbidden overclaim findings",
        "formal_external_plagiarism_database_screen_not_performed",
        "This file is generated by `scripts/audit_manuscript_originality.py`.",
    ]:
        if phrase not in text:
            fail(f"manuscript originality audit markdown missing phrase: {phrase}")


def require_formal_plagiarism_screening_runbook() -> None:
    json_path = ROOT / "runs" / "formal_plagiarism_screening_runbook.json"
    doc_path = ROOT / "docs" / "formal_plagiarism_screening_runbook.md"
    payload = load_json(json_path)
    if payload.get("formal_plagiarism_screening_runbook_ready") is not True:
        fail(f"formal plagiarism runbook is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"formal plagiarism runbook has local risk flags: {payload['risk_flags']}")
    if payload.get("formal_screening_completed") is not False:
        fail("formal plagiarism runbook must not claim external screening is completed")
    targets = payload.get("screening_scope", [])
    if not isinstance(targets, list) or len(targets) < 4:
        fail("formal plagiarism runbook has incomplete screening scope")
    targets_by_path = {
        str(target.get("path")): target for target in targets if isinstance(target, dict)
    }
    for rel in [
        "paper/iclr_submission.pdf",
        "paper/main_submission.pdf",
        "paper/main.tex",
        "paper/refs.bib",
    ]:
        target = targets_by_path.get(rel)
        if not isinstance(target, dict):
            fail(f"formal plagiarism runbook missing target: {rel}")
        if target.get("exists") is not True:
            fail(f"formal plagiarism runbook target should exist: {rel}")
        digest = str(target.get("sha256", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"formal plagiarism runbook target has invalid sha256: {rel}")
        if digest != sha256(ROOT / rel):
            fail(f"formal plagiarism runbook hash mismatch: {rel}")
    required_fields = payload.get("required_external_screening_receipt_fields", [])
    for field in [
        "schema_version",
        "screening_tool_or_vendor",
        "screening_report_id_or_url",
        "screening_report_export_sha256_or_private_location",
        "screened_file_path",
        "screened_file_sha256",
        "screened_date_utc",
        "operator",
        "screening_database_or_corpus",
        "external_corpus_searched",
        "total_similarity_percent",
        "max_single_source_similarity_percent",
        "top_matched_sources",
        "human_review_disposition",
        "material_matches_reviewed",
        "self_overlap_or_prior_version_reviewed",
        "pass",
        "notes",
    ]:
        if field not in required_fields:
            fail(f"formal plagiarism runbook missing receipt field: {field}")
    receipt_template = payload.get("receipt_template", {})
    if not isinstance(receipt_template, dict):
        fail("formal plagiarism runbook missing receipt template")
    for field in required_fields:
        if field not in receipt_template:
            fail(f"formal plagiarism receipt template missing field: {field}")
    tools = set(payload.get("acceptable_external_tools", []))
    for tool in ["iThenticate", "Turnitin"]:
        if tool not in tools:
            fail(f"formal plagiarism runbook missing external tool: {tool}")
    policy = payload.get("receipt_acceptance_policy", {})
    for key in [
        "screened_file_sha256_must_match_scope",
        "tool_must_search_external_corpus",
        "human_review_required_for_each_material_match",
        "material_matches_review_must_be_recorded",
        "self_overlap_or_prior_version_review_must_be_recorded",
        "receipt_intake_audit_required",
        "do_not_mark_complete_from_local_duplicate_sentence_audit_only",
    ]:
        if policy.get(key) is not True:
            fail(f"formal plagiarism runbook policy check failed: {key}")
    intake = payload.get("receipt_intake_audit", {})
    if intake.get("audit_json") != "runs/formal_plagiarism_screening_receipt_audit.json":
        fail("formal plagiarism runbook missing receipt intake audit JSON path")
    if intake.get("audit_md") != "docs/formal_plagiarism_screening_receipt_audit.md":
        fail("formal plagiarism runbook missing receipt intake audit markdown path")
    if intake.get("receipt_path") != "docs/formal_plagiarism_screening_receipt.json":
        fail("formal plagiarism runbook missing private receipt path")
    interpretation = payload.get("interpretation", {})
    for key in [
        "runbook_only",
        "formal_external_screening_still_required",
        "local_reference_integrity_audit_is_not_formal_detector",
        "local_manuscript_originality_audit_is_not_formal_detector",
        "no_similarity_result_recorded",
    ]:
        if interpretation.get(key) is not True:
            fail(f"formal plagiarism runbook interpretation check failed: {key}")
    open_flags = set(payload.get("open_risk_flags", []))
    if "formal_external_plagiarism_database_screen_not_performed" not in open_flags:
        fail("formal plagiarism runbook should keep external screening open")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Formal Plagiarism Screening Runbook",
        "iThenticate",
        "Turnitin",
        "Receipt Intake Audit",
        "not formal plagiarism detectors",
        "formal_external_plagiarism_database_screen_not_performed",
        "This file is generated by `scripts/build_formal_plagiarism_screening_runbook.py`.",
    ]:
        if phrase not in text:
            fail(f"formal plagiarism runbook markdown missing phrase: {phrase}")


def require_formal_plagiarism_screening_receipt_audit() -> None:
    json_path = ROOT / "runs" / "formal_plagiarism_screening_receipt_audit.json"
    doc_path = ROOT / "docs" / "formal_plagiarism_screening_receipt_audit.md"
    payload = load_json(json_path)
    if payload.get("formal_plagiarism_screening_receipt_audit_ready") is not True:
        fail(
            "formal plagiarism receipt audit is not ready: "
            f"{payload.get('risk_flags')}"
        )
    if payload.get("risk_flags"):
        fail(f"formal plagiarism receipt audit has local risk flags: {payload['risk_flags']}")
    if payload.get("receipt_path") != "docs/formal_plagiarism_screening_receipt.json":
        fail("formal plagiarism receipt audit points at the wrong receipt path")
    if payload.get("runbook") != "runs/formal_plagiarism_screening_runbook.json":
        fail("formal plagiarism receipt audit points at the wrong runbook")
    if payload.get("schema_version_expected") != "formal_plagiarism_screening_receipt_v1":
        fail("formal plagiarism receipt audit schema version changed unexpectedly")
    targets = payload.get("accepted_screening_targets", [])
    if not isinstance(targets, list) or len(targets) < 4:
        fail("formal plagiarism receipt audit has incomplete target scope")
    by_path = {str(target.get("path")): target for target in targets if isinstance(target, dict)}
    for rel in [
        "paper/iclr_submission.pdf",
        "paper/main_submission.pdf",
        "paper/main.tex",
        "paper/refs.bib",
    ]:
        target = by_path.get(rel)
        if not isinstance(target, dict):
            fail(f"formal plagiarism receipt audit missing target: {rel}")
        if target.get("current_hash_matches_runbook") is not True:
            fail(f"formal plagiarism receipt audit target hash is stale: {rel}")
        if target.get("current_sha256") != sha256(ROOT / rel):
            fail(f"formal plagiarism receipt audit target hash mismatch: {rel}")
    required_fields = set(str(field) for field in payload.get("required_fields", []))
    for field in [
        "schema_version",
        "screening_tool_or_vendor",
        "screening_report_id_or_url",
        "screening_report_export_sha256_or_private_location",
        "screened_file_path",
        "screened_file_sha256",
        "screened_date_utc",
        "screening_database_or_corpus",
        "external_corpus_searched",
        "material_matches_reviewed",
        "self_overlap_or_prior_version_reviewed",
        "pass",
    ]:
        if field not in required_fields:
            fail(f"formal plagiarism receipt audit missing required field: {field}")
    observed = payload.get("receipt_observed") is True
    completed = payload.get("formal_screening_completed") is True
    open_flags = set(str(flag) for flag in payload.get("open_risk_flags", []))
    if completed:
        if not observed:
            fail("formal plagiarism receipt audit cannot complete without a receipt")
        if open_flags:
            fail(f"completed formal plagiarism receipt audit still has open flags: {open_flags}")
        hv = payload.get("hash_validation", {})
        if hv.get("path_and_hash_match_same_target") is not True:
            fail("completed formal plagiarism receipt audit lacks path/hash match")
    else:
        if "formal_external_plagiarism_database_screen_not_performed" not in open_flags:
            fail("incomplete formal plagiarism receipt audit must keep external risk open")
    interpretation = payload.get("interpretation", {})
    for key in [
        "receipt_intake_gate_only",
        "missing_receipt_is_external_blocker_not_local_script_failure",
        "local_originality_audits_do_not_close_formal_screening",
    ]:
        if interpretation.get(key) is not True:
            fail(f"formal plagiarism receipt audit interpretation check failed: {key}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Formal Plagiarism Screening Receipt Audit",
        "Receipt observed:",
        "formal_external_plagiarism_database_screen_not_performed",
        "docs/formal_plagiarism_screening_receipt.json",
        "python scripts/audit_formal_plagiarism_screening_receipt.py --strict",
        "This file is generated by `scripts/audit_formal_plagiarism_screening_receipt.py`.",
    ]:
        if phrase not in text:
            fail(f"formal plagiarism receipt audit markdown missing phrase: {phrase}")


def require_iclr_openreview_packet() -> None:
    json_path = ROOT / "runs" / "iclr_openreview_packet.json"
    doc_path = ROOT / "docs" / "iclr_openreview_packet.md"
    payload = load_json(json_path)
    if payload.get("iclr_openreview_packet_ready") is not True:
        fail(f"ICLR OpenReview packet is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"ICLR OpenReview packet has local risk flags: {payload['risk_flags']}")
    if payload.get("ready_to_submit") is not False:
        fail("ICLR OpenReview packet must not claim final submit readiness yet")
    if payload.get("official_2027_cfp_observed") is not False:
        fail("ICLR OpenReview packet should keep the official 2027 CFP unobserved")
    metadata = payload.get("metadata", {})
    if "Winning Tickets Are Not Posterior Modes" not in str(metadata.get("title", "")):
        fail("ICLR OpenReview packet title does not match the paper")
    abstract_words = int(metadata.get("abstract_words", 0))
    if abstract_words <= 0 or abstract_words > 250:
        fail(f"ICLR OpenReview packet abstract word count invalid: {abstract_words}")
    paste = payload.get("paste_payload", {})
    if paste.get("paper_pdf") != "paper/iclr_submission.pdf":
        fail("ICLR OpenReview packet should use the ICLR-style PDF")
    if "LLM-based coding and writing assistants" not in str(
        paste.get("llm_usage_disclosure", "")
    ):
        fail("ICLR OpenReview packet missing LLM usage disclosure field")
    if "standard public benchmark datasets" not in str(paste.get("ethics_statement", "")):
        fail("ICLR OpenReview packet missing ethics statement field")
    if paste.get("external_urls_for_initial_submission") != []:
        fail("ICLR OpenReview packet should omit public external URLs initially")
    if paste.get("public_artifact_links_for_initial_submission") != []:
        fail("ICLR OpenReview packet should omit public artifact links initially")
    upload_files = payload.get("upload_files", [])
    by_path = {
        str(item.get("path")): item for item in upload_files if isinstance(item, dict)
    }
    for rel in [
        "paper/iclr_submission.pdf",
        "paper/main_submission.pdf",
        "paper/main.pdf",
        "paper/main.tex",
        "paper/refs.bib",
    ]:
        item = by_path.get(rel)
        if not isinstance(item, dict):
            fail(f"ICLR OpenReview packet missing upload/source file: {rel}")
        if item.get("exists") is not True:
            fail(f"ICLR OpenReview packet file should exist: {rel}")
        digest = str(item.get("sha256", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"ICLR OpenReview packet file has invalid sha256: {rel}")
        if digest != sha256(ROOT / rel):
            fail(f"ICLR OpenReview packet hash mismatch: {rel}")
    artifact = by_path.get("dist/lottery_artifact_public_release_2026-05-06.tar.gz")
    if not isinstance(artifact, dict) or artifact.get("exists") is not True:
        fail("ICLR OpenReview packet missing local supplementary artifact archive")
    if "sha256" in artifact:
        fail("ICLR OpenReview packet should not embed the release archive SHA256")
    for field in [
        "author_openreview_profiles",
        "author_conflicts_of_interest",
        "submission_agreement_confirmed",
    ]:
        if field not in payload.get("required_human_fields", []):
            fail(f"ICLR OpenReview packet missing human field: {field}")
    policy = payload.get("double_blind_policy", {})
    for key in [
        "paper_author_field_must_be_anonymous",
        "omit_public_artifact_urls_from_initial_submission",
        "artifact_archive_must_remain_anonymous",
        "human_author_identity_fields_not_stored_in_this_public_packet",
    ]:
        if policy.get(key) is not True:
            fail(f"ICLR OpenReview packet double-blind policy failed: {key}")
    open_flags = set(payload.get("open_risk_flags", []))
    for flag in [
        "iclr_2027_official_cfp_not_observed",
        "iclr_openreview_author_profile_and_coi_not_recorded",
        "iclr_openreview_submission_receipt_not_observed",
    ]:
        if flag not in open_flags:
            fail(f"ICLR OpenReview packet missing open risk: {flag}")
    interpretation = payload.get("interpretation", {})
    for key in [
        "local_openreview_packet_prepared",
        "not_a_final_openreview_submission_receipt",
        "must_update_after_official_2027_cfp",
        "must_record_human_author_profile_and_conflict_fields",
        "must_not_claim_ready_to_submit_until_open_risks_close",
    ]:
        if interpretation.get(key) is not True:
            fail(f"ICLR OpenReview packet interpretation check failed: {key}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "ICLR OpenReview Packet",
        "Ready to submit: `False`",
        "Official ICLR 2027 CFP observed: `False`",
        "Ethics statement",
        "LLM usage disclosure",
        "paper/iclr_submission.pdf",
        "iclr_openreview_author_profile_and_coi_not_recorded",
        "Do not paste public repository",
        "This file is generated by `scripts/build_iclr_openreview_packet.py`.",
    ]:
        if phrase not in text:
            fail(f"ICLR OpenReview packet markdown missing phrase: {phrase}")


def require_iclr_human_confirmation_template() -> None:
    json_path = ROOT / "runs" / "iclr_human_confirmation_template.json"
    doc_path = ROOT / "docs" / "iclr_human_confirmation_template.md"
    payload = load_json(json_path)
    if payload.get("iclr_human_confirmation_template_ready") is not True:
        fail(f"ICLR human confirmation template is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"ICLR human confirmation template has risk flags: {payload['risk_flags']}")
    if payload.get("confirmations_completed") is not False:
        fail("ICLR human confirmation template must not claim confirmations are complete")
    required = set(payload.get("required_confirmation_fields", []))
    for field in [
        "author_names",
        "author_emails",
        "author_openreview_profile_urls",
        "conflicts_recorded_in_openreview",
        "code_of_ethics_acknowledged_by_all_authors",
        "llm_usage_disclosure_confirmed_by_all_authors",
        "submission_agreement_confirmed",
        "openreview_submission_forum_url",
        "openreview_submission_id",
    ]:
        if field not in required:
            fail(f"ICLR human confirmation template missing required field: {field}")
    private_fields = set(payload.get("private_fields_not_for_public_release", []))
    for field in [
        "author_emails",
        "author_openreview_profile_urls",
        "conflicts_recorded_in_openreview",
        "openreview_submission_forum_url",
        "confirmation_email_or_receipt_path",
    ]:
        if field not in private_fields:
            fail(f"ICLR human confirmation template missing private-field warning: {field}")
    template = payload.get("confirmation_template", {})
    if not isinstance(template, dict):
        fail("ICLR human confirmation template payload missing template object")
    for field in required:
        if field not in template:
            fail(f"ICLR human confirmation template object missing field: {field}")
    intake = payload.get("receipt_intake_audit", {})
    if intake.get("receipt_path") != "docs/iclr_human_confirmation_receipt.json":
        fail("ICLR human confirmation template missing private receipt path")
    if intake.get("audit_json") != "runs/iclr_human_confirmation_receipt_audit.json":
        fail("ICLR human confirmation template missing receipt audit JSON path")
    if intake.get("audit_md") != "docs/iclr_human_confirmation_receipt_audit.md":
        fail("ICLR human confirmation template missing receipt audit markdown path")
    if intake.get("schema_version") != "iclr_human_confirmation_receipt_v1":
        fail("ICLR human confirmation template schema version changed")
    for field in [
        "author_names",
        "author_emails",
        "author_affiliations",
        "author_openreview_profile_urls",
    ]:
        if template.get(field) != []:
            fail(f"ICLR human confirmation template should not contain private author values: {field}")
    for field in [
        "author_order_confirmed",
        "all_authors_have_openreview_profiles",
        "conflicts_recorded_in_openreview",
        "code_of_ethics_acknowledged_by_all_authors",
        "ethics_statement_confirmed_by_all_authors",
        "llm_usage_disclosure_confirmed_by_all_authors",
        "submission_agreement_confirmed",
    ]:
        if template.get(field) is not False:
            fail(f"ICLR human confirmation template should keep boolean pending: {field}")
    open_flags = set(payload.get("open_risk_flags", []))
    for flag in [
        "iclr_openreview_author_profile_and_coi_not_recorded",
        "iclr_code_of_ethics_author_acknowledgement_not_recorded",
        "llm_usage_disclosure_author_confirmation_not_recorded",
        "iclr_openreview_submission_receipt_not_observed",
    ]:
        if flag not in open_flags:
            fail(f"ICLR human confirmation template missing open risk: {flag}")
    interpretation = payload.get("interpretation", {})
    for key in [
        "template_only",
        "does_not_record_private_author_information",
        "does_not_replace_openreview_submission_receipt",
        "human_confirmations_still_required",
    ]:
        if interpretation.get(key) is not True:
            fail(f"ICLR human confirmation template interpretation check failed: {key}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "ICLR Human Confirmation Template",
        "Confirmations completed: `False`",
        "Private Fields Not For Public Release",
        "Receipt Intake Audit",
        "iclr_openreview_author_profile_and_coi_not_recorded",
        "This file is generated by `scripts/build_iclr_human_confirmation_template.py`.",
    ]:
        if phrase not in text:
            fail(f"ICLR human confirmation template markdown missing phrase: {phrase}")


def require_iclr_human_confirmation_receipt_audit() -> None:
    json_path = ROOT / "runs" / "iclr_human_confirmation_receipt_audit.json"
    doc_path = ROOT / "docs" / "iclr_human_confirmation_receipt_audit.md"
    payload = load_json(json_path)
    if payload.get("iclr_human_confirmation_receipt_audit_ready") is not True:
        fail(
            "ICLR human confirmation receipt audit is not ready: "
            f"{payload.get('risk_flags')}"
        )
    if payload.get("risk_flags"):
        fail(f"ICLR human confirmation receipt audit has risk flags: {payload['risk_flags']}")
    if payload.get("receipt_path") != "docs/iclr_human_confirmation_receipt.json":
        fail("ICLR human confirmation receipt audit points at the wrong private receipt")
    if payload.get("template") != "runs/iclr_human_confirmation_template.json":
        fail("ICLR human confirmation receipt audit points at the wrong template")
    if payload.get("expected_schema_version") != "iclr_human_confirmation_receipt_v1":
        fail("ICLR human confirmation receipt audit schema version changed")
    if payload.get("expected_pdf_sha256") != sha256(ROOT / "paper" / "iclr_submission.pdf"):
        fail("ICLR human confirmation receipt audit expected PDF SHA is stale")
    privacy = payload.get("privacy", {})
    if privacy.get("does_not_echo_private_values") is not True:
        fail("ICLR human confirmation receipt audit must not echo private values")
    open_flags = set(str(flag) for flag in payload.get("open_risk_flags", []))
    if payload.get("confirmations_completed") is True:
        if open_flags:
            fail(f"completed ICLR human receipt audit still has open flags: {open_flags}")
    else:
        for flag in [
            "iclr_openreview_author_profile_and_coi_not_recorded",
            "iclr_code_of_ethics_author_acknowledgement_not_recorded",
            "llm_usage_disclosure_author_confirmation_not_recorded",
            "iclr_openreview_submission_receipt_not_observed",
        ]:
            if flag not in open_flags:
                fail(f"incomplete ICLR human receipt audit missing open risk: {flag}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "ICLR Human Confirmation Receipt Audit",
        "without echoing author names",
        "docs/iclr_human_confirmation_receipt.json",
        "iclr_openreview_author_profile_and_coi_not_recorded",
        "scripts/audit_iclr_human_confirmation_receipt.py",
    ]:
        if phrase not in text:
            fail(f"ICLR human confirmation receipt audit markdown missing phrase: {phrase}")


def require_iclr_policy_watch_audit() -> None:
    json_path = ROOT / "runs" / "iclr_policy_watch_audit.json"
    doc_path = ROOT / "docs" / "iclr_policy_watch_audit.md"
    probe_json_path = ROOT / "runs" / "iclr_policy_source_probe.json"
    probe_doc_path = ROOT / "docs" / "iclr_policy_source_probe.md"
    payload = load_json(json_path)
    if payload.get("iclr_policy_watch_audit_ready") is not True:
        fail(f"ICLR policy watch audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"ICLR policy watch audit has local risk flags: {payload['risk_flags']}")
    if payload.get("official_2027_cfp_observed") is not False:
        fail("ICLR policy watch should keep the official 2027 CFP unobserved")
    if payload.get("official_2027_author_guide_observed") is not False:
        fail("ICLR policy watch should keep the official 2027 author guide unobserved")
    if payload.get("source_observation_mode") not in {
        "static_snapshot",
        "live_probe",
        "recorded_live_probe",
    }:
        fail(f"unexpected ICLR policy source mode: {payload.get('source_observation_mode')}")
    if payload.get("source_observation_mode") in {"live_probe", "recorded_live_probe"}:
        require_file(str(probe_json_path.relative_to(ROOT)), 500)
        require_file(str(probe_doc_path.relative_to(ROOT)), 500)
        probe = load_json(probe_json_path)
        if probe.get("iclr_policy_source_probe_ready") is not True:
            fail("ICLR policy source probe should be ready")
        probe_observations = probe.get("official_source_observations", [])
        if probe_observations != payload.get("official_source_observations"):
            fail("ICLR policy watch observations should match source probe receipt")
    observations = payload.get("official_source_observations", [])
    by_role = {
        str(row.get("role")): row for row in observations if isinstance(row, dict)
    }
    expected_statuses = {
        "official_2027_call_for_papers_candidate": 404,
        "official_2027_author_guide_candidate": 404,
        "official_2026_call_for_papers_proxy": 200,
        "official_2026_author_guide_proxy": 200,
    }
    for role, status in expected_statuses.items():
        row = by_role.get(role)
        if not isinstance(row, dict):
            fail(f"ICLR policy watch missing source observation: {role}")
        if int(row.get("observed_http_status", -1)) != status:
            fail(f"ICLR policy watch source status changed for {role}")
    facts = payload.get("proxy_policy_facts", {})
    for key in [
        "proxy_only_not_2027_policy",
        "double_blind",
        "references_excluded_from_page_limit",
        "appendix_allowed_but_review_optional",
        "all_authors_need_openreview_profiles",
        "paper_must_be_anonymous",
        "llm_usage_disclosure_required_when_significant",
        "llms_not_eligible_for_authorship",
        "authors_responsible_for_llm_generated_content",
        "code_of_ethics_acknowledgement_required",
        "reproducibility_statement_strongly_encouraged",
    ]:
        if facts.get(key) is not True:
            fail(f"ICLR policy watch proxy fact failed: {key}")
    if facts.get("main_text_page_limit_at_submission") != 9:
        fail("ICLR policy watch proxy page limit should be 9")
    open_flags = set(payload.get("open_risk_flags", []))
    for flag in [
        "iclr_2027_official_cfp_not_observed",
        "iclr_2027_official_author_guide_not_observed",
    ]:
        if flag not in open_flags:
            fail(f"ICLR policy watch missing open risk: {flag}")
    interpretation = payload.get("interpretation", {})
    for key in [
        "official_2027_policy_not_confirmed",
        "uses_2026_policy_as_provisional_proxy",
        "uses_recorded_live_probe",
        "must_refresh_after_iclr_2027_cfp_posts",
        "must_not_claim_final_iclr_2027_compliance_yet",
    ]:
        if interpretation.get(key) is not True:
            fail(f"ICLR policy watch interpretation check failed: {key}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "ICLR Policy Watch Audit",
        "Official ICLR 2027 CFP observed: `False`",
        "Official ICLR 2027 author guide observed: `False`",
        "Source observation mode: `recorded_live_probe`",
        "https://iclr.cc/Conferences/2027/CallForPapers",
        "https://iclr.cc/Conferences/2026/AuthorGuide",
        "This file is generated by `scripts/build_iclr_policy_watch_audit.py`.",
    ]:
        if phrase not in text:
            fail(f"ICLR policy watch markdown missing phrase: {phrase}")
    probe_text = " ".join(probe_doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "ICLR Policy Source Probe",
        "official_2027_call_for_papers_candidate",
        "https://iclr.cc/Conferences/2027/CallForPapers",
        "This file is generated by `scripts/build_iclr_policy_watch_audit.py --live-probe`.",
    ]:
        if phrase not in probe_text:
            fail(f"ICLR policy source probe markdown missing phrase: {phrase}")


def require_llm_usage_disclosure_audit() -> None:
    json_path = ROOT / "runs" / "llm_usage_disclosure_audit.json"
    doc_path = ROOT / "docs" / "llm_usage_disclosure_audit.md"
    payload = load_json(json_path)
    if payload.get("llm_usage_disclosure_audit_ready") is not True:
        fail(f"LLM usage disclosure audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"LLM usage disclosure audit has risk flags: {payload['risk_flags']}")
    if payload.get("missing_source_phrases") not in ([], None):
        fail("LLM usage disclosure audit missing source phrases")
    if payload.get("missing_pdf_phrases") not in ([], None):
        fail("LLM usage disclosure audit missing PDF phrases")
    interpretation = payload.get("interpretation", {})
    for key in [
        "iclr_style_disclosure_section_present",
        "does_not_replace_author_confirmation",
        "must_refresh_after_official_iclr_2027_policy_posts",
    ]:
        if interpretation.get(key) is not True:
            fail(f"LLM usage disclosure interpretation check failed: {key}")
    open_flags = set(payload.get("open_risk_flags", []))
    if "llm_usage_disclosure_author_confirmation_not_recorded" not in open_flags:
        fail("LLM usage disclosure audit should keep author confirmation open")
    paper = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    normalized_paper = " ".join(paper.split())
    for phrase in [
        r"\section*{LLM Usage Disclosure}",
        "LLM-based coding and writing assistants",
        "not used as authors",
        "not treated as sources of scientific evidence",
        "reviewed and accepted by the human authors",
    ]:
        haystack = paper if phrase.startswith("\\") else normalized_paper
        if phrase not in haystack:
            fail(f"paper/main.tex missing LLM usage disclosure phrase: {phrase}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "LLM Usage Disclosure Audit",
        "Audit status: ready.",
        "llm_usage_disclosure_author_confirmation_not_recorded",
        "This file is generated by `scripts/audit_llm_usage_disclosure.py`.",
    ]:
        if phrase not in text:
            fail(f"LLM usage disclosure markdown missing phrase: {phrase}")


def require_ethics_statement_audit() -> None:
    json_path = ROOT / "runs" / "ethics_statement_audit.json"
    doc_path = ROOT / "docs" / "ethics_statement_audit.md"
    payload = load_json(json_path)
    if payload.get("ethics_statement_audit_ready") is not True:
        fail(f"ethics statement audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"ethics statement audit has risk flags: {payload['risk_flags']}")
    if payload.get("missing_source_phrases") not in ([], None):
        fail("ethics statement audit missing source phrases")
    if payload.get("missing_pdf_phrases") not in ([], None):
        fail("ethics statement audit missing PDF phrases")
    interpretation = payload.get("interpretation", {})
    for key in [
        "ethics_statement_present_in_iclr_pdf",
        "no_human_subjects_or_private_data_claimed",
        "overclaiming_risk_scoped",
        "does_not_replace_final_iclr_author_acknowledgement",
    ]:
        if interpretation.get(key) is not True:
            fail(f"ethics statement interpretation check failed: {key}")
    open_flags = set(payload.get("open_risk_flags", []))
    if "iclr_code_of_ethics_author_acknowledgement_not_recorded" not in open_flags:
        fail("ethics statement audit should keep final ICLR acknowledgement open")
    paper = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    normalized_paper = " ".join(paper.split())
    for phrase in [
        r"\section*{Ethics Statement}",
        "standard public benchmark datasets",
        "does not introduce human subjects data",
        "private personal data",
        "scientific overclaiming",
        "Code of Ethics",
    ]:
        haystack = paper if phrase.startswith("\\") else normalized_paper
        if phrase not in haystack:
            fail(f"paper/main.tex missing ethics statement phrase: {phrase}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Ethics Statement Audit",
        "Audit status: ready.",
        "iclr_code_of_ethics_author_acknowledgement_not_recorded",
        "This file is generated by `scripts/audit_ethics_statement.py`.",
    ]:
        if phrase not in text:
            fail(f"ethics statement markdown missing phrase: {phrase}")


def tex_sci(value: float) -> str:
    if value == 0.0:
        return "0.0"
    exponent = math.floor(math.log10(abs(value)))
    mantissa = value / (10**exponent)
    return f"{mantissa:.1f}{{\\times}}10^{{{exponent}}}"


def require_paper_numeric_claims(stats: dict[str, Any]) -> None:
    main_tex = " ".join(
        (ROOT / "paper" / "main.tex").read_text(encoding="utf-8").split()
    )

    def require_phrase(phrase: str) -> None:
        if phrase not in main_tex:
            fail(f"paper/main.tex missing generated numeric claim: {phrase}")

    random_rows = [
        row
        for row in stats["mode_distribution_equivalence"]
        if row.get("comparison") == "posterior-random"
    ]
    random_wins = sum(
        str(row.get("verdict")) == "posterior separates from random"
        for row in random_rows
    )
    require_phrase(
        "posterior supports beat uniform random masks in "
        f"{random_wins} of {len(random_rows)} grouped comparisons"
    )

    chain_rows = [
        row
        for row in stats["mode_distribution_equivalence"]
        if row.get("comparison") == "posterior-chain"
    ]
    chain_tied = sum(
        str(row.get("verdict")) == "practically tied to control"
        for row in chain_rows
    )
    chain_control = sum(
        str(row.get("verdict")) == "control closer to ticket"
        for row in chain_rows
    )
    chain_mixed = sum(str(row.get("verdict")) == "mixed" for row in chain_rows)
    mixed_text = "one" if chain_mixed == 1 else str(chain_mixed)
    require_phrase(
        f"none of the {len(chain_rows)} posterior-versus-chain-start comparisons"
    )
    require_phrase(
        f"{chain_tied} are practically tied to the control, "
        f"{chain_control} favor chain-start magnitude, and {mixed_text} is mixed"
    )

    rewind_rows = [
        row
        for row in stats["mode_distribution_equivalence"]
        if row.get("comparison") == "posterior-rewind"
    ]
    rewind_control = sum(
        str(row.get("verdict")) == "control closer to ticket"
        for row in rewind_rows
    )
    require_phrase(
        f"support in {rewind_control} of {len(rewind_rows)} grouped comparisons"
    )

    block_rows = rows_matching(
        stats["block_laplace"],
        sampler="BlockDiagLap",
        block="blockdiag:11blocks<=5000",
        scale=0.0001,
    )
    if not block_rows:
        fail("BlockDiagLap row unavailable for paper numeric claim checks")
    # The Richer Covariance subsection was condensed to a single paragraph in
    # the post-revision manuscript; exact per-row numbers now live in the claim
    # ledger (verified separately by require_paper_claim_ledger). Here we check
    # the condensed paragraph's stated anchors against the same stats.
    block = block_rows[0]
    parameter_count = int(round(float(block["parameter_count"]["mean"])))
    block_post_chain = float(block["global_post_chain"]["mean"])
    block_delta_signed = float(block["block_posterior_minus_chain"]["mean"])
    block_global_delta = float(block["global_posterior_minus_chain"]["mean"])
    block_rewind_delta = float(block["global_rewind_minus_posterior"]["mean"])

    wider_block_rows = rows_matching(
        stats["block_laplace"],
        sampler="BlockDiagLap",
        block="blockdiag:16blocks<=10000",
        scale=1e-05,
    )
    if not wider_block_rows:
        fail("BlockDiagLap max10k row unavailable for paper numeric claim checks")
    wider_block = wider_block_rows[0]
    wider_count = int(round(float(wider_block["parameter_count"]["mean"])))
    wider_post_chain = float(wider_block["global_post_chain"]["mean"])
    wider_rewind_delta = float(wider_block["global_rewind_minus_posterior"]["mean"])

    jointdiag_rows = rows_matching(
        stats["block_laplace"],
        sampler="JointDiagLap",
        block="jointdiag:8groups<=10000",
        scale=1e-05,
    )
    if not jointdiag_rows:
        fail("JointDiagLap max10k row unavailable for paper numeric claim checks")
    jointdiag = jointdiag_rows[0]
    jointdiag_count = int(round(float(jointdiag["parameter_count"]["mean"])))
    jointdiag_post_chain = float(jointdiag["global_post_chain"]["mean"])
    jointdiag_rewind_delta = float(jointdiag["global_rewind_minus_posterior"]["mean"])

    jointdiag20_rows = rows_matching(
        stats["block_laplace"],
        sampler="JointDiagLap",
        block="jointdiag:6groups<=20000",
        scale=3e-06,
    )
    if not jointdiag20_rows:
        fail("JointDiagLap max20k row unavailable for paper numeric claim checks")
    jointdiag20 = jointdiag20_rows[0]
    jointdiag20_count = int(round(float(jointdiag20["parameter_count"]["mean"])))
    jointdiag20_post_chain = float(jointdiag20["global_post_chain"]["mean"])
    jointdiag20_rewind_delta = float(jointdiag20["global_rewind_minus_posterior"]["mean"])

    jointdiag40_rows = rows_matching(
        stats["block_laplace"],
        sampler="JointDiagLap",
        block="jointdiag:8groups<=40000",
        scale=1e-06,
    )
    if not jointdiag40_rows:
        fail("JointDiagLap max40k row unavailable for paper numeric claim checks")
    jointdiag40 = jointdiag40_rows[0]
    jointdiag40_count = int(round(float(jointdiag40["parameter_count"]["mean"])))
    jointdiag40_post_chain = float(jointdiag40["global_post_chain"]["mean"])
    jointdiag40_global_delta = float(jointdiag40["global_posterior_minus_chain"]["mean"])
    jointdiag40_rewind_delta = float(jointdiag40["global_rewind_minus_posterior"]["mean"])

    require_phrase(
        f"covering {parameter_count:,}, {wider_count:,}, {jointdiag_count:,}, "
        f"{jointdiag20_count:,}, and {jointdiag40_count:,} trainable weights"
    )
    require_phrase(
        f"from {block_post_chain:.4f} at the {parameter_count:,}-parameter row"
    )
    other_post_chains = [
        wider_post_chain,
        jointdiag_post_chain,
        jointdiag20_post_chain,
        jointdiag40_post_chain,
    ]
    require_phrase(
        f"down to {min(other_post_chains):.4f}--{max(other_post_chains):.4f}"
    )
    require_phrase(
        f"between $-{abs(block_delta_signed):.4f}$ and $+{block_global_delta:.4f}$"
    )
    rewind_deltas = [
        block_rewind_delta,
        wider_rewind_delta,
        jointdiag_rewind_delta,
        jointdiag20_rewind_delta,
        jointdiag40_rewind_delta,
    ]
    require_phrase(f"by {min(rewind_deltas):.3f}--{max(rewind_deltas):.3f}")
    require_phrase(
        f"the full {jointdiag40_count:,}-weight vector and still reports global "
        f"posterior-minus-chain $-{abs(jointdiag40_global_delta):.4f}$"
    )

    direct_rows = rows_matching(
        stats["direct_mode_ticket_distribution"],
        setting="CIFAR full LowRank128Lap",
        comparison="posterior_samples_vs_tickets",
    )
    if not direct_rows:
        fail("LowRank128Lap direct mode/ticket row unavailable for paper checks")
    direct = direct_rows[0]
    sample_count = int(round(float(direct["left_count"])))
    require_phrase(
        f"{sample_count} posterior samples pass the Hamming-overlap "
        f"threshold ({float(direct['hamming_overlap']):.3f})"
    )
    require_phrase(
        "logit/final-hidden activation CKA "
        f"({float(direct['logit_cka_hungarian_mean']):.3f}/"
        f"{float(direct['activation_cka_hungarian_mean']):.3f})"
    )
    require_phrase(
        "layer-sparsity KS threshold "
        f"($p={tex_sci(float(direct['layer_ks_pvalue']))}$)"
    )
    require_phrase("collapse to one parameter-PCA basin")

    jointdiag_direct_rows = rows_matching(
        stats["direct_mode_ticket_distribution"],
        setting="CIFAR full JointDiagLap270k",
        comparison="posterior_samples_vs_tickets",
    )
    if not jointdiag_direct_rows:
        fail("JointDiagLap270k direct mode/ticket row unavailable for paper checks")
    jointdiag_direct = jointdiag_direct_rows[0]
    jointdiag_sample_count = int(round(float(jointdiag_direct["left_count"])))
    jointdiag_metrics_path = ROOT / str(jointdiag_direct["run"]) / "metrics.json"
    if not jointdiag_metrics_path.exists():
        fail("JointDiagLap270k direct metrics unavailable for paper checks")
    jointdiag_payload = load_json(jointdiag_metrics_path)
    jointdiag_diagnostics = jointdiag_payload.get("posterior_chain_diagnostics", {})
    jointdiag_sample_accuracy = float(
        jointdiag_diagnostics["posterior_sample_accuracy_mean"]
    )
    jointdiag_hamming = float(
        jointdiag_diagnostics["posterior_to_chain_start_hamming_mean"]
    )
    require_phrase(
        "A streamed exact joint-group direct probe over all "
        f"{jointdiag40_count:,} weight parameters"
    )
    require_phrase(f"{jointdiag_sample_count} joint-group posterior samples")
    require_phrase(f"sample accuracy at {100.0 * jointdiag_sample_accuracy:.1f}\\%")
    require_phrase(f"posterior-to-chain-start Hamming is {jointdiag_hamming:.4f}")
    require_phrase(
        "layer-sparsity KS is "
        f"$p={tex_sci(float(jointdiag_direct['layer_ks_pvalue']))}$"
    )
    require_phrase(
        f"Hamming overlap is {float(jointdiag_direct['hamming_overlap']):.3f}"
    )
    require_phrase(
        "logit/final-hidden activation CKA remains "
        f"{float(jointdiag_direct['logit_cka_hungarian_mean']):.3f}/"
        f"{float(jointdiag_direct['activation_cka_hungarian_mean']):.3f}"
    )
    require_phrase(
        f"all {jointdiag_sample_count} joint-group samples still collapse to one "
        "parameter-PCA basin"
    )
    require_phrase(
        "The layer-sparsity KS values in these direct rows are descriptive diagnostics "
        "over correlated posterior samples"
    )
    require_phrase(
        "posterior samples are farther from the same-seed IMP ticket than the "
        "chain-start support in 5/5 raw seeds and 5/5 activation-aligned seeds"
    )
    if saved_artifact_reruns_observed():
        require_phrase(
            "cyclical-SGLD multichain, rank-128"
        )
        require_phrase(
            "low-rank Laplace, and joint-group Laplace direct rows also write "
            "per-seed"
        )
        require_phrase("10/10 across both groups")
    else:
        require_phrase(
            "The remaining cSGLD, low-rank Laplace, and joint-group direct rows "
            "require the same saved-mask rerun"
        )
    require_phrase("direct distribution statistical unit")
    if saved_artifact_reruns_observed():
        require_phrase(
            "Pooled direct mode/ticket p-values over posterior samples are descriptive "
            "over correlated samples"
        )
        require_phrase("the headline SGLD direction now spans ten")
        require_phrase("two-sided sign $p = 0.002$")
    else:
        require_phrase(
            "Pooled direct mode/ticket p-values over posterior samples are descriptive "
            "unless raw masks are saved for seed-level reconstruction"
        )

    posterior_projection = rows_matching(
        stats["residual_imp_process_posterior_projection_pairs"],
        base_source="traj_rms_abs",
        process_round=5,
        alpha=0.5,
    )
    if not posterior_projection:
        fail("posterior-residualized projection row unavailable for paper checks")
    projection = posterior_projection[0]
    round_accuracy = float(projection["round_accuracy"]["mean"])
    residualized_accuracy = float(projection["residualized_accuracy"]["mean"])
    delta = projection["round_minus_residualized"]
    oracle_delta = projection["round_minus_residualized_oracle"]
    round_oracle = float(projection["round_oracle_overlap"]["mean"])
    residualized_oracle = float(projection["residualized_oracle_overlap"]["mean"])
    # Process-controls paragraph condensed to gap + CI form in the revision.
    _ = (round_accuracy, residualized_accuracy, round_oracle, residualized_oracle)
    require_phrase(
        f"{100.0 * float(delta['mean']):.2f}-point round-vs-residualized "
        f"accuracy gap ({int(delta['positive'])}/{int(delta['n'])} positive "
        f"seeds, 95\\% CI $[{100.0 * float(delta['ci95_low']):.2f},"
        f"{100.0 * float(delta['ci95_high']):.2f}]$)"
    )
    require_phrase(f"oracle overlap dropping {float(oracle_delta['mean']):.4f}")

    learned_subspace = rows_matching(
        stats["residual_imp_process_learned_subspace_pairs"],
        base_source="traj_rms_abs",
        process_round=5,
        alpha=0.5,
    )
    if not learned_subspace:
        fail("learned-subspace residualized projection row unavailable for paper checks")
    learned = learned_subspace[0]
    learned_round_accuracy = float(learned["round_accuracy"]["mean"])
    learned_accuracy = float(learned["residualized_accuracy"]["mean"])
    learned_delta = learned["round_minus_residualized"]
    learned_oracle_delta = learned["round_minus_residualized_oracle"]
    learned_round_oracle = float(learned["round_oracle_overlap"]["mean"])
    learned_oracle = float(learned["residualized_oracle_overlap"]["mean"])
    _ = (learned_round_accuracy, learned_accuracy, learned_round_oracle, learned_oracle)
    require_phrase(
        f"{100.0 * float(learned_delta['mean']):.2f}-point gap "
        f"({int(learned_delta['positive'])}/{int(learned_delta['n'])} seeds, "
        f"95\\% CI $[{100.0 * float(learned_delta['ci95_low']):.2f},"
        f"{100.0 * float(learned_delta['ci95_high']):.2f}]$)"
    )
    require_phrase(f"overlap dropping {float(learned_oracle_delta['mean']):.4f}")


def require_environment_lock() -> None:
    lock = load_json(ROOT / "docs" / "environment_lock.json")
    expected_packages = {
        "torch": "2.11.0",
        "torchvision": "0.26.0",
        "numpy": "1.26.4",
        "scipy": "1.11.4",
        "scikit-learn": "1.4.1.post1",
        "matplotlib": "3.6.3",
    }
    packages = lock.get("packages", {})
    for name, version in expected_packages.items():
        if packages.get(name) != version:
            fail(f"environment lock missing {name}=={version}")
    lock_text = (ROOT / "requirements-lock.txt").read_text(encoding="utf-8")
    for name, version in expected_packages.items():
        if f"{name}=={version}" not in lock_text:
            fail(f"requirements-lock.txt missing {name}=={version}")
    expected_gpu_packages = {
        name: version
        for name, version in expected_packages.items()
        if name != "matplotlib"
    }
    gpu_lock_text = (ROOT / "requirements-gpu-lock.txt").read_text(encoding="utf-8")
    for name, version in expected_gpu_packages.items():
        if f"{name}=={version}" not in gpu_lock_text:
            fail(f"requirements-gpu-lock.txt missing {name}=={version}")
    if "matplotlib==" in gpu_lock_text:
        fail("requirements-gpu-lock.txt should exclude plotting-only matplotlib")


def require_full_covariance_feasibility() -> None:
    payload = load_json(
        ROOT / "runs" / "cifar10_resnet20_full_covariance_feasibility.json"
    )
    all_trainable = payload.get("all_trainable", {})
    weight_only = payload.get("weight_only", {})
    weight_blocks = payload.get("weight_tensor_block_diagonal", {})
    largest = payload.get("largest_parameter_tensors", [])
    if int(all_trainable.get("parameter_count", 0)) < 270_000:
        fail("full-covariance feasibility audit has too few trainable parameters")
    if float(all_trainable.get("dense_precision_float64_gib", 0.0)) < 500.0:
        fail("full-covariance audit underestimates dense matrix memory")
    if float(all_trainable.get("precision_plus_cholesky_float64_gib", 0.0)) < 1000.0:
        fail("full-covariance audit underestimates Cholesky memory")
    if float(weight_only.get("cholesky_flops", 0.0)) < 1e15:
        fail("full-covariance audit underestimates full-network Cholesky cost")
    if float(weight_blocks.get("precision_plus_cholesky_float64_gib", 0.0)) < 100.0:
        fail("full-covariance audit underestimates tensor-block memory")
    if not largest:
        fail("full-covariance audit has no largest tensor rows")
    top = largest[0]
    if int(top.get("parameter_count", 0)) != 36_864:
        fail("full-covariance audit top tensor should have 36,864 parameters")
    if float(top.get("dense_precision_float64_gib", 0.0)) < 10.0:
        fail("full-covariance audit top tensor memory is too small")
    text = (
        ROOT / "docs" / "cifar10_resnet20_full_covariance_feasibility.md"
    ).read_text(encoding="utf-8")
    for phrase in [
        "not a runnable exact",
        "553.1",
        "1,106.3",
        "full-network rank-16/rank-32/rank-64/rank-128 Hessian-plus-diagonal Laplace",
    ]:
        if phrase not in text:
            fail(f"full-covariance feasibility doc missing phrase: {phrase}")


def require_posterior_covariance_robustness_audit() -> None:
    csv_path = ROOT / "runs" / "posterior_covariance_robustness_audit.csv"
    json_path = ROOT / "runs" / "posterior_covariance_robustness_audit.json"
    doc_path = ROOT / "docs" / "posterior_covariance_robustness_audit.md"
    for path, label in [
        (csv_path, "CSV"),
        (json_path, "JSON"),
        (doc_path, "doc"),
    ]:
        if not path.exists() or path.stat().st_size < 500:
            fail(f"posterior covariance robustness audit {label} missing or too small")

    with csv_path.open(encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    if len(csv_rows) != 11:
        fail("posterior covariance robustness audit CSV should contain 11 rows")
    labels = {row["label"] for row in csv_rows}
    required_labels = {
        "LowRank16 Laplace",
        "LowRank32 Laplace",
        "LowRank64 Laplace",
        "LowRank128 Laplace",
        "BlockDiag22k Laplace",
        "BlockDiag68k Laplace",
        "JointDiag68k Laplace",
        "JointDiag86k Laplace",
        "JointDiag270k Laplace",
        "LowRank128 direct samples",
        "JointDiag270k direct samples",
    }
    missing = sorted(required_labels - labels)
    if missing:
        fail(f"posterior covariance robustness audit missing labels: {missing}")

    payload = load_json(json_path)
    rows = payload.get("rows", [])
    if len(rows) != 11:
        fail("posterior covariance robustness audit JSON should contain 11 rows")
    checks = payload.get("interpretation_checks", {})
    if checks.get("posterior_covariance_robustness_ready") is not True:
        fail("posterior covariance robustness audit should be ready")
    if int(checks.get("movement_row_count", 0)) != 9:
        fail("posterior covariance audit should include nine movement rows")
    if int(checks.get("direct_row_count", 0)) != 2:
        fail("posterior covariance audit should include two direct rows")
    if checks.get("all_movement_rows_five_seed") is not True:
        fail("posterior covariance movement rows should be five-seed")
    if checks.get("all_movement_rows_preserve_accuracy") is not True:
        fail("posterior covariance movement rows should preserve sample accuracy")
    if checks.get("no_movement_row_beats_chain_start_by_0p005") is not True:
        fail("posterior covariance movement rows should not beat chain-start")
    if checks.get("exact_rows_rewind_remains_closer") is not True:
        fail("posterior covariance exact rows should keep rewind support closer")
    if checks.get("direct_rows_fail_equivalence") is not True:
        fail("posterior covariance direct rows should fail proposal equivalence")
    if checks.get("dense_full_covariance_infeasible") is not True:
        fail("posterior covariance audit should bind dense CIFAR infeasibility")
    if float(checks.get("max_movement_posterior_minus_chain_start_jaccard", 1.0)) > 0.005:
        fail("posterior covariance max movement gain is too large")
    if float(checks.get("min_exact_rewind_minus_posterior_jaccard", 0.0)) <= 0.025:
        fail("posterior covariance exact rewind-posterior margin is too small")
    if float(checks.get("min_movement_sample_accuracy", 0.0)) < 0.875:
        fail("posterior covariance movement sample accuracy is too small")
    dense = payload.get("dense_feasibility", {})
    if int(dense.get("parameter_count", 0)) != 272474:
        fail("posterior covariance audit dense parameter count changed")
    if float(dense.get("precision_plus_cholesky_float64_gib", 0.0)) < 1000.0:
        fail("posterior covariance audit should keep dense Cholesky bound")

    by_label = {row["label"]: row for row in rows}
    if by_label["LowRank128 direct samples"].get("direct_equivalence_passed") is not False:
        fail("LowRank128 covariance direct row should fail equivalence")
    if by_label["JointDiag270k direct samples"].get("direct_equivalence_passed") is not False:
        fail("JointDiag270k covariance direct row should fail equivalence")
    if float(by_label["JointDiag270k direct samples"]["layer_ks_pvalue"]) >= 0.001:
        fail("JointDiag270k covariance direct row should fail layer KS")
    if float(by_label["JointDiag270k direct samples"]["hamming_overlap"]) >= 0.70:
        fail("JointDiag270k covariance direct row should fail Hamming overlap")

    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Posterior Covariance Robustness Audit",
        "covariance-fidelity spectrum",
        "Movement rows: 9; direct rows: 2.",
        "maximum posterior-chain 0.0036",
        "minimum rewind-posterior 0.0292",
        "553.1 GiB",
        "1106.3 GiB",
        "bounded open limitation",
    ]:
        if phrase not in text:
            fail(f"posterior covariance robustness audit doc missing phrase: {phrase}")


def require_digits_fullnet_laplace_probe() -> None:
    csv_path = ROOT / "runs" / "digits_fullnet_laplace_tiny_r2_p0p3_summary.csv"
    doc_path = ROOT / "docs" / "digits_fullnet_laplace_tiny_r2_p0p3.md"
    if not csv_path.exists() or csv_path.stat().st_size < 500:
        fail("tiny full-network dense Laplace summary CSV missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 500:
        fail("tiny full-network dense Laplace summary doc missing or too small")

    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 4:
        fail("tiny full-network dense Laplace summary should contain four scales")
    scales = {round(float(row["full_laplace_scale"]), 8) for row in rows}
    expected_scales = {round(value, 8) for value in [1e-5, 1e-4, 1e-3, 1e-2]}
    if scales != expected_scales:
        fail(f"tiny full-network dense Laplace scales changed: {scales}")
    selected = [
        row
        for row in rows
        if abs(float(row["full_laplace_scale"]) - 1e-3) < 1e-12
    ]
    if len(selected) != 1:
        fail("tiny full-network dense Laplace scale 1e-3 row missing")
    row = selected[0]
    if int(float(row["num_runs"])) != 5:
        fail("tiny full-network dense Laplace row must be five-seed")
    if int(round(float(row["parameter_count"]))) != 310:
        fail("tiny full-network dense Laplace row should cover 310 trainable parameters")
    if float(row["examples_seen"]) < 1400:
        fail("tiny full-network dense Laplace Hessian should see the full digits train set")
    if float(row["dense_accuracy"]) <= 0.80:
        fail("tiny full-network dense Laplace dense model accuracy unexpectedly low")
    if float(row["imp_accuracy"]) <= 0.84:
        fail("tiny full-network dense Laplace IMP accuracy unexpectedly low")
    if float(row["sample_accuracy_mean"]) <= 0.83:
        fail("tiny full-network dense Laplace samples should remain accurate")
    if float(row["posterior_minus_chain_start_jaccard"]) >= -0.05:
        fail("tiny full-network dense Laplace posterior should remain below chain-start support")
    if float(row["posterior_to_chain_start_magnitude_jaccard_mean"]) >= 0.85:
        fail("tiny full-network dense Laplace scale 1e-3 samples should move from chain-start")
    if float(row["chain_start_magnitude_to_imp_jaccard"]) <= float(
        row["posterior_jaccard_mean"]
    ):
        fail("tiny full-network dense Laplace posterior should not beat chain-start support")

    metrics_paths = sorted(
        (ROOT / "runs" / "digits_fullnet_laplace_tiny_r2_p0p3").glob("*/metrics.json")
    )
    if len(metrics_paths) != 5:
        fail(
            "tiny full-network dense Laplace raw metrics should contain five seeds, "
            f"found {len(metrics_paths)}"
        )
    seeds = set()
    for path in metrics_paths:
        payload = load_json(path)
        seeds.add(int(payload.get("seed", -1)))
        factors = payload.get("full_laplace", {})
        if int(factors.get("parameter_count", 0)) != 310:
            fail(f"tiny full-network dense Laplace raw metrics parameter count changed: {path}")
        if factors.get("precision_cholesky_shape") != [310, 310]:
            fail(f"tiny full-network dense Laplace raw metrics Cholesky shape changed: {path}")
        if len(payload.get("rows", [])) != 4:
            fail(f"tiny full-network dense Laplace raw metrics should contain four scale rows: {path}")
    if seeds != {0, 1, 2, 3, 4}:
        fail(f"tiny full-network dense Laplace raw metrics seeds changed: {sorted(seeds)}")

    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Full-network Dense Laplace Probe Summary",
        "exact dense full-network softmax-GGN/Laplace",
        "310.0000",
        "0.7545",
        "not CIFAR-scale evidence",
    ]:
        if phrase not in text:
            fail(f"tiny full-network dense Laplace doc missing phrase: {phrase}")


def require_fake_resnet_fullnet_laplace_smoke() -> None:
    csv_path = ROOT / "runs" / "fake_cifar10_resnet20_w1_fullnet_laplace_smoke_summary.csv"
    doc_path = ROOT / "docs" / "fake_cifar10_resnet20_w1_fullnet_laplace_smoke.md"
    if not csv_path.exists() or csv_path.stat().st_size < 500:
        fail("fake-CIFAR ResNet full-network dense Laplace summary CSV missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 500:
        fail("fake-CIFAR ResNet full-network dense Laplace summary doc missing or too small")

    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 2:
        fail("fake-CIFAR ResNet full-network dense Laplace summary should contain two scales")
    scales = {round(float(row["full_laplace_scale"]), 8) for row in rows}
    expected_scales = {round(value, 8) for value in [1e-5, 1e-3]}
    if scales != expected_scales:
        fail(f"fake-CIFAR ResNet full-network dense Laplace scales changed: {scales}")
    selected = [
        row
        for row in rows
        if abs(float(row["full_laplace_scale"]) - 1e-3) < 1e-12
    ]
    if len(selected) != 1:
        fail("fake-CIFAR ResNet full-network dense Laplace scale 1e-3 row missing")
    row = selected[0]
    if int(float(row["num_runs"])) != 5:
        fail("fake-CIFAR ResNet full-network dense Laplace row must be five-seed")
    if int(round(float(row["parameter_count"]))) != 1229:
        fail("fake-CIFAR ResNet full-network dense Laplace row should cover 1,229 trainable parameters")
    if int(round(float(row["weight_parameter_count"]))) != 1121:
        fail("fake-CIFAR ResNet full-network dense Laplace row should cover 1,121 weight parameters")
    if int(round(float(row["examples_seen"]))) != 16:
        fail("fake-CIFAR ResNet full-network dense Laplace smoke should use one Hessian batch")
    if float(row["posterior_to_chain_start_magnitude_jaccard_mean"]) >= 0.60:
        fail("fake-CIFAR ResNet full-network dense Laplace smoke should move from chain-start support")
    if float(row["posterior_minus_chain_start_jaccard"]) >= -0.30:
        fail("fake-CIFAR ResNet full-network dense Laplace smoke should remain below chain-start support")

    metrics_paths = sorted(
        (ROOT / "runs" / "fake_cifar10_resnet20_w1_fullnet_laplace_smoke").glob(
            "*/metrics.json"
        )
    )
    if len(metrics_paths) != 5:
        fail(
            "fake-CIFAR ResNet full-network dense Laplace raw metrics should contain "
            f"five seeds, found {len(metrics_paths)}"
        )
    seeds = set()
    for path in metrics_paths:
        payload = load_json(path)
        seeds.add(int(payload.get("seed", -1)))
        config = payload.get("config", {})
        if config.get("dataset") != "fake-cifar10" or config.get("model") != "resnet20":
            fail(f"fake-CIFAR ResNet full-network dense Laplace raw config changed: {path}")
        if int(config.get("resnet_width", 0)) != 1:
            fail(f"fake-CIFAR ResNet full-network dense Laplace should use width 1: {path}")
        factors = payload.get("full_laplace", {})
        if int(factors.get("parameter_count", 0)) != 1229:
            fail(f"fake-CIFAR ResNet full-network dense Laplace parameter count changed: {path}")
        if factors.get("precision_cholesky_shape") != [1229, 1229]:
            fail(f"fake-CIFAR ResNet full-network dense Laplace Cholesky shape changed: {path}")
        if len(payload.get("rows", [])) != 2:
            fail(f"fake-CIFAR ResNet full-network dense Laplace raw metrics should contain two scale rows: {path}")
    if seeds != {0, 1, 2, 3, 4}:
        fail(f"fake-CIFAR ResNet full-network dense Laplace raw seeds changed: {sorted(seeds)}")

    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "fake-CIFAR ResNet-20 width-1",
        "convolutional/residual/BatchNorm code-path smoke test",
        "1229.0000",
        "0.5392",
        "not real CIFAR evidence",
    ]:
        if phrase not in text:
            fail(f"fake-CIFAR ResNet full-network dense Laplace doc missing phrase: {phrase}")


def require_linear_connectivity_barrier_audit() -> None:
    csv_path = ROOT / "runs" / "linear_connectivity_barrier_audit.csv"
    json_path = ROOT / "runs" / "linear_connectivity_barrier_audit.json"
    doc_path = ROOT / "docs" / "linear_connectivity_barrier_audit.md"
    for path, label in [
        (csv_path, "CSV"),
        (json_path, "JSON"),
        (doc_path, "doc"),
    ]:
        if not path.exists() or path.stat().st_size < 500:
            fail(f"linear connectivity barrier audit {label} missing or too small")

    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 6:
        fail("linear connectivity barrier audit should contain six rows")
    by_label = {row["label"]: row for row in rows}
    required_labels = {
        "MNIST Gate1 SGLD r5",
        "Fashion-MNIST Gate1 SGLD r5",
        "CIFAR-10 ResNet-20 long SGLD r5",
        "CIFAR-10 ResNet-20 long SWAG r5",
        "CIFAR-10 ResNet-20 3-chain SGLD r5",
        "CIFAR-10 ResNet-20 short SWAG r5",
    }
    missing = sorted(required_labels - set(by_label))
    if missing:
        fail(f"linear connectivity barrier audit missing rows: {missing}")
    for row in rows:
        if int(row["num_runs"]) != 5:
            fail(f"linear connectivity audit row should be five-seed: {row['label']}")
        if float(row["posterior_minus_chain_start_jaccard_mean"]) > 0.001:
            fail(f"posterior should not beat chain-start in connectivity audit: {row['label']}")
    mnist = by_label["MNIST Gate1 SGLD r5"]
    fashion = by_label["Fashion-MNIST Gate1 SGLD r5"]
    cifar_sgld = by_label["CIFAR-10 ResNet-20 long SGLD r5"]
    cifar_swag = by_label["CIFAR-10 ResNet-20 long SWAG r5"]
    if float(mnist["dense_imp_barrier_mean"]) >= 0.01:
        fail("MNIST dense-IMP linear barrier should stay near zero")
    if float(fashion["dense_imp_barrier_mean"]) >= 0.05:
        fail("Fashion-MNIST dense-IMP linear barrier should stay near zero")
    if float(cifar_sgld["dense_imp_barrier_mean"]) <= 2.0:
        fail("CIFAR long SGLD linear barrier should be large")
    if float(cifar_swag["dense_imp_barrier_mean"]) <= 2.0:
        fail("CIFAR long SWAG linear barrier should be large")

    payload = load_json(json_path)
    checks = payload.get("interpretation_checks", {})
    for key in [
        "all_rows_five_seed",
        "mnist_dense_imp_barrier_near_zero",
        "fashion_dense_imp_barrier_near_zero",
        "cifar_dense_imp_barriers_large",
        "posterior_never_beats_chain_start",
    ]:
        if checks.get(key) is not True:
            fail(f"linear connectivity barrier audit check failed: {key}")

    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Linear Connectivity Barrier Audit",
        "MNIST Gate1 SGLD r5",
        "0.0026",
        "3.0827",
        "orthogonal landscape diagnostics",
        "not evidence of posterior-ticket equivalence",
    ]:
        if phrase not in text:
            fail(f"linear connectivity barrier audit doc missing phrase: {phrase}")


def require_container_lock() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    gpu_dockerfile = (ROOT / "Dockerfile.gpu").read_text(encoding="utf-8")
    container_doc = (ROOT / "docs" / "container_lock.md").read_text(
        encoding="utf-8"
    )
    gpu_container_doc = (ROOT / "docs" / "gpu_training_container.md").read_text(
        encoding="utf-8"
    )
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    ci_workflow = (ROOT / ".github" / "workflows" / "check.yml").read_text(
        encoding="utf-8"
    )
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    ci_requirements = (ROOT / "requirements-ci.txt").read_text(encoding="utf-8")
    gpu_requirements = (ROOT / "requirements-gpu-lock.txt").read_text(encoding="utf-8")
    expected_digest = (
        "python:3.12.3-slim-bookworm@sha256:"
        "fd3817f3a855f6c2ada16ac9468e5ee93e361005bd226fd5a5ee1a504e038c84"
    )
    expected_gpu_digest = (
        "nvidia/cuda:13.0.1-cudnn-devel-ubuntu24.04@sha256:"
        "5a2d3b02eb7412847d051d0f2b0f0a5031057a0172d9ca78743cc41cfc5d037f"
    )
    for phrase in [
        expected_digest,
        "requirements-ci.txt",
        "git",
        "poppler-utils",
        "texlive-latex-base",
        "texlive-bibtex-extra",
        "texlive-latex-extra",
        "ripgrep",
        "make source-repository-check PYTHON=python",
        "make ci-check paper-check PYTHON=python",
        "Full artifact payload absent",
    ]:
        if phrase not in dockerfile:
            fail(f"Dockerfile missing container lock phrase: {phrase}")
    for phrase in [
        expected_digest,
        "numpy==1.26.4",
        "git",
        "poppler-utils",
        "make container-build",
        "make container-check",
        "make source-repository-check PYTHON=python",
        "CPU-only artifact-verification container",
        "Dockerfile.gpu",
        "make external-gpu-container-receipt",
        "scripts/build_external_gpu_container_receipt.py",
    ]:
        if phrase not in container_doc:
            fail(f"container lock doc missing phrase: {phrase}")
    for phrase in [
        expected_gpu_digest,
        "requirements-gpu-lock.txt",
        'CMD ["python", "scripts/check_gpu_training_environment.py"]',
    ]:
        if phrase not in gpu_dockerfile:
            fail(f"Dockerfile.gpu missing GPU container phrase: {phrase}")
    for phrase in [
        expected_gpu_digest,
        "make gpu-container-build",
        "make gpu-container-env-check",
        "make external-gpu-container-receipt",
        "requirements-gpu-lock.txt",
        "torch==2.11.0",
        "Torch CUDA `13.0`",
        "scripts/build_external_gpu_container_receipt.py",
        "runs/external_gpu_container_receipt.json",
    ]:
        if phrase not in gpu_container_doc:
            fail(f"GPU training container doc missing phrase: {phrase}")
    for phrase in [
        "container-build",
        "container-check",
        "CONTAINER_IMAGE",
        "gpu-container-build",
        "gpu-container-env-check",
        "external-gpu-container-receipt",
        "GPU_CONTAINER_IMAGE",
        "scripts/run_gpu_container_env_check.py",
        "scripts/build_external_gpu_container_receipt.py",
    ]:
        if phrase not in makefile:
            fail(f"Makefile missing container target phrase: {phrase}")
    for phrase in [
        "sudo apt-get update",
        "git",
        "make",
        "poppler-utils",
        "ripgrep",
        "texlive-bibtex-extra",
        "texlive-fonts-recommended",
        "texlive-latex-extra",
        "texlive-latex-base",
        "texlive-latex-recommended",
        "make source-repository-check PYTHON=python",
        "Full artifact payload absent",
        "make ci-check paper-check PYTHON=python",
        "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24",
        "actions/checkout@v5",
        "actions/setup-python@v6",
        "branches:",
        "- main",
    ]:
        if phrase not in ci_workflow:
            fail(f"CI workflow missing paper-build phrase: {phrase}")
    for phrase in [
        "paper/main_submission.aux",
        "paper/main_submission.bbl",
        "paper/main_submission.blg",
        "paper/main_submission.log",
        "paper/main_submission.out",
        "paper/neurips_submission.aux",
        "paper/neurips_submission.bbl",
        "paper/neurips_submission.blg",
        "paper/neurips_submission.log",
        "paper/neurips_submission.out",
    ]:
        if phrase not in dockerignore:
            fail(f".dockerignore missing submission build artifact: {phrase}")
    if "numpy==1.26.4" not in ci_requirements:
        fail("requirements-ci.txt missing numpy==1.26.4")
    for phrase in [
        "numpy==1.26.4",
        "scikit-learn==1.4.1.post1",
        "scipy==1.11.4",
        "torch==2.11.0",
        "torchvision==0.26.0",
    ]:
        if phrase not in gpu_requirements:
            fail(f"requirements-gpu-lock.txt missing GPU package phrase: {phrase}")
    if "matplotlib==" in gpu_requirements:
        fail("requirements-gpu-lock.txt should not install matplotlib")


def require_claim_ledger() -> None:
    text = (ROOT / "docs" / "paper_claim_ledger.md").read_text(encoding="utf-8")
    expected_phrases = [
        "Posterior support is not random",
        "58/59 groups",
        "0/59 groups",
        "55/57 groups",
        "Full-data CIFAR direct mode/ticket probes",
        "rank-16, rank-32, rank-64, and rank-128 Hessian-plus-diagonal Laplace",
        "tiny exact dense full-network Laplace",
        "fullnet scale=0.0010",
        "fullnet params=310",
        "fullnet post-chain=0.8084",
        "fullnet posterior-chain=-0.1050",
        "convolutional ResNet smoke",
        "fake-resnet fullnet scale=0.0010",
        "params=1229",
        "post-chain=0.5398",
        "Linear connectivity barriers are orthogonal",
        "MNIST dense-IMP barrier=0.0026",
        "CIFAR long SGLD/SWAG dense-IMP barriers=3.0827/3.7402",
        "68,144-parameter exact block-diagonal",
        "68,144-parameter exact joint-group",
        "86,576-parameter exact joint-group",
        "270,896-parameter exact joint-group",
        "covariance-fidelity spectrum",
        "movement/direct rows=9/2",
        "max movement posterior-chain=0.0036",
        "270,896-parameter direct joint-group",
        "post-hoc exhaustive graph/permutation realignment",
        "raw mask/state files=0",
        "mask-artifact smoke parameters=4350",
        "record-level posthoc matching=True",
        "local channel matching=True",
        "full-data saved-artifact budget=284.18 MiB",
        "full-data record-level posthoc=True",
        "full-data channel skipped=7",
        "full-data local channel=False",
        "global-channel hamming raw/aligned=0.2105/0.2113",
        "global-channel support overlap=0.3738",
        "exact stage1 assignments=128",
        "stage1 coordinate exact=True",
        "full channel assignments log10=840.4",
        "tensor+score replacement acc",
        "residualized-score acc",
        "posterior-residualized acc",
        "learned-subspace residualized acc",
        "oracle-overlap drop",
        "Open limitation, bounded",
        "Seed-level architecture sanity cell",
        "posterior-to-chain-start Hamming 0.0612",
        "reproduces on CIFAR-100 ResNet-20",
    ]
    for phrase in expected_phrases:
        if phrase not in text:
            fail(f"paper claim ledger missing phrase: {phrase}")
    pass_count = text.count("| Pass |")
    if pass_count < 7:
        fail(f"paper claim ledger has too few passing claim rows: {pass_count}")


def require_proposal_to_artifact_audit() -> None:
    json_path = ROOT / "runs" / "proposal_to_artifact_audit_2026-05-12.json"
    doc_path = ROOT / "docs" / "proposal_to_artifact_audit.md"
    payload = load_json(json_path)
    text = doc_path.read_text(encoding="utf-8")
    if payload.get("proposal_to_artifact_audit_verified") is not True:
        fail("proposal-to-artifact audit is not verified")
    if payload.get("goal_complete") is True:
        fail("proposal-to-artifact audit should not mark the active goal complete")
    if int(payload.get("row_count", 0)) != 10:
        fail("proposal-to-artifact audit should contain ten rows")
    statuses = {str(row.get("status")) for row in payload.get("rows", [])}
    expected_statuses = {
        "covered_negative_reframe",
        "falsified_current_artifacts",
        "unsupported_current_artifacts",
        "covered_negative",
        "bounded_negative",
        "covered_with_bounded_limitation",
        "covered",
        "bounded_open_limitation",
        "venue_target_selected",
        "external_blocked",
    }
    missing = sorted(expected_statuses - statuses)
    if missing:
        fail(f"proposal-to-artifact audit missing statuses: {missing}")
    for phrase in [
        "H1: lottery tickets correspond one-to-one to posterior modes",
        "posterior>random 58/59",
        "posterior>chain by >0.005 0/59",
        "rewind>posterior by >0.005 55/57",
        "direct CIFAR sample rows one-cluster 7/7",
        "H3: variational mode-finding pruning",
        "full search log10 assignments=840.4",
        "Top-conference venue targeting",
        "primary=TMLR (rolling)",
        "backup1=ICLR 2027",
        "external_gpu_container_run_not_observed",
    ]:
        if phrase not in text:
            fail(f"proposal-to-artifact audit missing phrase: {phrase}")


def require_reviewer_objection_matrix() -> None:
    json_path = ROOT / "runs" / "reviewer_objection_matrix.json"
    doc_path = ROOT / "docs" / "reviewer_objection_matrix.md"
    if not json_path.exists() or json_path.stat().st_size < 1000:
        fail("reviewer objection matrix JSON missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 1000:
        fail("reviewer objection matrix doc missing or too small")
    payload = load_json(json_path)
    rows = payload.get("rows", [])
    if len(rows) != 9:
        fail("reviewer objection matrix should contain nine rows")
    objections = {str(row.get("objection")) for row in rows}
    expected_objections = {
        "Posterior masks only need to beat random masks.",
        "The posterior sampler is too weak or stuck in one chain.",
        "Function-space agreement is enough even if masks differ.",
        "A channel permutation or re-basin step would align posterior masks.",
        "The covariance posterior is too diagonal, local, or head-only.",
        "Linear mode connectivity explains the ticket/posterior relation.",
        "Learned Bayesian or variational masks could recover tickets.",
        "A simpler trajectory or process subspace explains the IMP residual.",
        "The artifact is venue-submission ready, but strict external GPU hardening is pending.",
    }
    missing = sorted(expected_objections - objections)
    if missing:
        fail(f"reviewer objection matrix missing objections: {missing}")
    summary = payload.get("summary", {})
    if int(summary.get("closed_count", 0)) < 5:
        fail("reviewer objection matrix should close at least five objections")
    if int(summary.get("bounded_open_count", 0)) != 2:
        fail("reviewer objection matrix should have two bounded-open limitations")
    if int(summary.get("open_packaging_count", 0)) != 0:
        fail("reviewer objection matrix should route public-receipt gaps through the external hardening limitation")
    if int(summary.get("external_hardening_count", 0)) != 1:
        fail("reviewer objection matrix should record one external hardening limitation")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Reviewer Objection Matrix",
        "posterior>random 58/59 groups",
        "dense-start cSGLD samples=75",
        "global-channel posterior/ticket Hamming=0.2105",
        "movement/direct covariance rows=9/2",
        "min exact rewind-posterior=0.0292",
        "dense CIFAR matrix=553.1 GiB",
        "MNIST/Fashion dense-IMP barriers=0.0026/0.0395",
        "variational/hard-concrete support=0.0907/0.0922",
        "Open external hardening limitation",
        "external_gpu_container_run_not_observed",
        "not a claim that every robustness gap is closed",
    ]:
        if phrase not in text:
            fail(f"reviewer objection matrix missing phrase: {phrase}")


def require_paper_submission_shape_audit() -> None:
    json_path = ROOT / "runs" / "paper_submission_shape_audit.json"
    doc_path = ROOT / "docs" / "paper_submission_shape_audit.md"
    if not json_path.exists() or json_path.stat().st_size < 1000:
        fail("paper submission shape audit JSON missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 1000:
        fail("paper submission shape audit doc missing or too small")
    payload = load_json(json_path)
    if payload.get("paper_tex") != "paper/main.tex":
        fail("paper submission shape audit should target paper/main.tex")
    if int(payload.get("section_count", 0)) < 7:
        fail("paper submission shape audit section count unexpectedly low")
    if int(payload.get("main_body_lines_before_appendix", 0)) > 850:
        fail("paper submission shape audit should keep the main body within target")
    result_sections = [
        section
        for section in payload.get("sections", [])
        if section.get("title") == "The Posterior-Mode Account Fails the Gates"
    ]
    if not result_sections:
        fail("paper submission shape audit missing posterior-mode results section")
    if int(result_sections[0].get("lines", 0)) > 450:
        fail("paper submission shape audit should keep the results section within target")
    if int(payload.get("reviewer_objection_rows", 0)) != 9:
        fail("paper submission shape audit should consume the nine-row reviewer matrix")
    if payload.get("submission_shape_ready") is not True:
        fail("paper submission shape audit should mark the condensed draft ready")
    risk_flags = set(payload.get("risk_flags", []))
    if risk_flags:
        fail(f"paper submission shape audit should have no blocking risk flags: {sorted(risk_flags)}")
    checks = payload.get("objection_checks", {})
    for key in [
        "random_control",
        "sampler_movement",
        "function_vs_mask",
        "alignment_permutation",
        "covariance_fidelity",
        "linear_connectivity",
        "learned_masks",
        "process_mechanism",
    ]:
        if checks.get(key) is not True:
            fail(f"paper submission shape audit missing objection coverage: {key}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Paper Submission Shape Audit",
        "Current status: ready",
        "PDF pages are total compiled pages",
        "Completed Condensation",
        "Main-body lines are within the 850-line target",
        "results section is within the 450-line target",
    ]:
        if phrase not in text:
            fail(f"paper submission shape audit missing phrase: {phrase}")


def require_submission_pdf_shape_audit() -> None:
    json_path = ROOT / "runs" / "submission_pdf_shape_audit.json"
    doc_path = ROOT / "docs" / "submission_pdf_shape_audit.md"
    if not json_path.exists() or json_path.stat().st_size < 250:
        fail("submission PDF shape audit JSON missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 500:
        fail("submission PDF shape audit doc missing or too small")
    payload = load_json(json_path)
    if payload.get("submission_pdf") != "paper/main_submission.pdf":
        fail("submission PDF shape audit should target paper/main_submission.pdf")
    if payload.get("submission_pdf_ready") is not True:
        fail("submission PDF shape audit should mark the main-only PDF ready")
    if payload.get("risk_flags"):
        fail(f"submission PDF shape audit has risk flags: {payload['risk_flags']}")
    if int(payload.get("pdf_page_count", 0)) > int(payload.get("max_pages", 10)):
        fail("submission PDF exceeds page budget")
    if int(payload.get("size_bytes", 0)) < 100_000:
        fail("submission PDF audit reports an unexpectedly small PDF")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Submission PDF Shape Audit",
        "Current status: ready",
        "main-only submission PDF",
        "paper/main_submission.pdf",
        "Risk Flags",
        "none",
    ]:
        if phrase not in text:
            fail(f"submission PDF shape audit missing phrase: {phrase}")


def require_venue_submission_compliance_audit() -> None:
    json_path = ROOT / "runs" / "venue_submission_compliance_audit.json"
    doc_path = ROOT / "docs" / "venue_submission_compliance_audit.md"
    if not json_path.exists() or json_path.stat().st_size < 500:
        fail("venue submission compliance audit JSON missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 500:
        fail("venue submission compliance audit doc missing or too small")
    payload = load_json(json_path)
    if payload.get("paper_tex") != "paper/main.tex":
        fail("venue submission audit should target paper/main.tex")
    if payload.get("submission_pdf") != "paper/neurips_submission.pdf":
        fail("venue submission audit should target paper/neurips_submission.pdf")
    if payload.get("venue_profile") != "neurips_2026_main":
        fail("venue submission audit should use the NeurIPS 2026 profile")
    if payload.get("target_venue") != "NeurIPS 2026 Main Track":
        fail("venue submission audit should target NeurIPS 2026 Main Track")
    if payload.get("content_packet_ready") is not True:
        fail(f"venue content packet should be ready: {payload.get('content_risk_flags')}")
    if payload.get("venue_binding_ready") is not True:
        fail(
            f"NeurIPS style/checklist binding should be ready: "
            f"{payload.get('venue_binding_risk_flags')}"
        )
    if payload.get("checklist_release_ready") is not True:
        fail(
            f"venue submission audit should have resolved checklist release risks: "
            f"{payload.get('checklist_release_risk_flags')}"
        )
    if payload.get("release_packaging_ready") is not True:
        fail("venue submission audit should accept local GPU-container validation for submission packaging")
    if payload.get("local_submission_ready") is not True:
        fail("venue submission audit should mark the local submission packet ready")
    if payload.get("venue_submission_ready") is not True:
        fail("venue submission audit should mark the venue submission packet ready")
    if payload.get("document_class") != "article":
        fail("venue submission audit should record the current article class")
    if payload.get("known_venue_style_detected") is not True:
        fail("venue submission audit should detect the official NeurIPS style")
    if payload.get("official_style_file_present") is not True:
        fail("venue submission audit should confirm paper/neurips_2026.sty")
    if payload.get("neurips_style_source_wired") is not True:
        fail("venue submission audit should confirm NeurIPS source wiring")
    if payload.get("neurips_checklist_present") is not True:
        fail("venue submission audit should confirm the NeurIPS checklist")
    if payload.get("neurips_checklist_no_todos") is not True:
        fail("venue submission audit should confirm no checklist TODOs")
    if payload.get("anonymous_author") is not True:
        fail("venue submission audit should confirm anonymous author")
    if int(payload.get("abstract_word_count", 9999)) > int(
        payload.get("max_abstract_words", 250)
    ):
        fail("venue submission audit abstract exceeds the local word budget")
    content_pages = payload.get("content_pages_before_references")
    if content_pages is None:
        fail("venue submission audit should locate References in the NeurIPS PDF")
    if int(content_pages) > int(payload.get("max_pages_before_references", 9)):
        fail("venue submission audit NeurIPS main content exceeds page budget")
    if payload.get("reference_start_page") is None:
        fail("venue submission audit should record the References start page")
    if payload.get("appendix_after_references_wired") is not True:
        fail("venue submission audit should keep appendix/checklist after references")
    binding_flags = set(payload.get("venue_binding_risk_flags", []))
    if binding_flags:
        fail(f"venue submission audit has binding flags: {sorted(binding_flags)}")
    metadata_docs = payload.get("release_metadata_docs", {})
    for key in [
        "compute_resource_accounting",
        "asset_license_inventory",
        "new_asset_inventory",
    ]:
        status = metadata_docs.get(key)
        if not isinstance(status, dict):
            fail(f"venue submission audit missing release metadata doc status: {key}")
        if status.get("exists") is not True:
            fail(f"release metadata doc should exist: {key}")
        if status.get("required_terms_present") is not True:
            fail(f"release metadata doc missing required terms: {key}: {status}")
    checklist_flags = set(payload.get("checklist_release_risk_flags", []))
    if checklist_flags:
        fail(f"unexpected venue checklist release flags: {sorted(checklist_flags)}")
    packaging_flags = set(payload.get("release_packaging_risk_flags", []))
    if packaging_flags:
        fail(f"unexpected venue release packaging flags: {sorted(packaging_flags)}")
    packaging_warning_flags = set(payload.get("release_packaging_warning_flags", []))
    if packaging_warning_flags != {"external_gpu_container_run_not_observed"}:
        fail(f"unexpected venue release packaging warning flags: {sorted(packaging_warning_flags)}")
    public_release_flags = set(payload.get("public_release_risk_flags", []))
    allowed_public_release_flags = {
        "public_release_upload_not_verified",
        "public_repository_upload_not_verified",
        "external_ci_run_not_observed",
    }
    if public_release_flags - allowed_public_release_flags:
        fail(f"unexpected venue public release flags: {sorted(public_release_flags)}")
    local_gpu = payload.get("local_gpu_validation", {})
    if not isinstance(local_gpu, dict) or local_gpu.get("local_gpu_container_ready") is not True:
        fail(f"venue submission audit missing ready local GPU validation: {local_gpu}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Venue Submission Compliance Audit",
        "Current content-packet status: ready",
        "Current venue-binding status: ready",
        "Current checklist-release status: ready",
        "Current release-packaging status: ready",
        "Current public-release status:",
        "Current local-submission status: ready",
        "Current venue-submission status: ready",
        "paper/neurips_submission.pdf",
        "runs/external_validation_readiness_audit.json",
        "runs/local_gpu_container_validation.json",
        "Release Metadata Docs",
        "docs/compute_resource_accounting.md",
        "docs/asset_license_inventory.md",
        "docs/new_asset_inventory.md",
        "Main-content pages before references",
        "external_gpu_container_run_not_observed",
    ]:
        if phrase not in text:
            fail(f"venue submission compliance audit missing phrase: {phrase}")


def require_iclr_submission_readiness_audit() -> None:
    json_path = ROOT / "runs" / "iclr_submission_readiness_audit.json"
    doc_path = ROOT / "docs" / "iclr_submission_readiness_audit.md"
    if not json_path.exists() or json_path.stat().st_size < 1000:
        fail("ICLR submission readiness audit JSON missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 1000:
        fail("ICLR submission readiness audit doc missing or too small")
    payload = load_json(json_path)
    if payload.get("iclr_submission_readiness_audit_ready") is not True:
        fail(f"ICLR readiness audit has local risk flags: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"ICLR readiness audit has risk flags: {payload['risk_flags']}")
    if payload.get("provisional_primary_venue") != "ICLR 2027":
        fail("ICLR readiness audit should record ICLR 2027 as the provisional primary venue")
    if payload.get("iclr_submission_ready") is not False:
        fail("ICLR readiness audit must not claim final ICLR submission readiness yet")
    if payload.get("provisional_strategy_ready") is not True:
        fail("ICLR readiness audit should mark the local strategy shape as ready")
    policy = payload.get("reference_policy", {})
    if policy.get("official_2027_cfp_observed") is not False:
        fail("ICLR readiness audit should keep the official 2027 CFP unobserved")
    checks = payload.get("checks", {})
    for key in [
        "paper_tex_exists",
        "document_class_article",
        "anonymous_author",
        "title_present",
        "abstract_present",
        "abstract_within_250_words",
        "main_submission_pdf_exists",
        "main_submission_pdf_page_count_available",
        "references_heading_found",
        "main_text_pages_before_references_within_budget",
        "main_only_source_flag_wired",
        "claim_ledger_present",
        "reproducibility_manifest_present",
        "release_manifest_present",
        "artifact_verifier_present",
        "ethics_statement_present",
        "llm_usage_disclosure_present",
        "iclr_policy_watch_present",
        "iclr_policy_source_probe_present",
        "iclr_policy_watch_uses_recorded_live_probe",
        "iclr_2026_policy_proxy_sources_observed",
        "formal_plagiarism_screening_runbook_present",
        "formal_plagiarism_receipt_fields_declared",
        "formal_plagiarism_receipt_intake_audit_present",
        "iclr_openreview_packet_present",
        "iclr_openreview_paste_payload_declared",
        "iclr_human_confirmation_template_present",
        "iclr_human_confirmation_receipt_audit_present",
        "iclr_style_file_present",
        "iclr_bibliography_style_present",
        "iclr_source_flag_wired",
        "iclr_make_target_present",
        "iclr_submission_pdf_exists",
        "iclr_submission_pdf_page_count_available",
        "iclr_references_heading_found",
        "iclr_main_text_pages_before_references_within_budget",
    ]:
        if checks.get(key) is not True:
            fail(f"ICLR readiness check failed: {key}")
    if int(payload.get("content_pages_before_references", 999)) > int(
        payload.get("max_main_pages_before_references", 9)
    ):
        fail("ICLR readiness audit reports content pages over budget")
    open_flags = set(payload.get("open_risk_flags", []))
    expected_open = {
        "iclr_2027_official_cfp_not_observed",
        "iclr_2027_official_author_guide_not_observed",
        "iclr_code_of_ethics_author_acknowledgement_not_recorded",
        "iclr_openreview_author_profile_and_coi_not_recorded",
        "iclr_openreview_submission_receipt_not_observed",
        "llm_usage_disclosure_author_confirmation_not_recorded",
        "formal_external_plagiarism_database_screen_not_performed",
    }
    if external_receipts_registry_available():
        if not external_receipt_observed("public_release_upload"):
            expected_open.add("public_release_upload_not_verified")
        elif "public_release_upload_not_verified" in open_flags:
            fail("ICLR readiness audit should drop the public-release risk after the receipt is observed")
        if not external_receipt_observed("external_ci"):
            expected_open.add("external_ci_run_not_observed")
        elif "external_ci_run_not_observed" in open_flags:
            fail("ICLR readiness audit should drop the external-CI risk after the receipt is observed")
    if locked_final_test_observed():
        if "locked_final_test_metrics_not_observed" in open_flags:
            fail("ICLR readiness audit should drop locked-final-test risk after the rerun is observed")
    else:
        expected_open.add("locked_final_test_metrics_not_observed")
    if bn_ablation_observed():
        if "full_cifar_bn_ablation_rerun_not_observed" in open_flags:
            fail("ICLR readiness audit should drop full-CIFAR BN ablation risk after the rerun is observed")
    else:
        expected_open.add("full_cifar_bn_ablation_rerun_not_observed")
    if saved_artifact_reruns_observed():
        if "seed_level_saved_artifacts_incomplete_for_other_direct_rows" in open_flags:
            fail(
                "ICLR readiness audit should drop seed-level saved-artifact risk "
                "after every saved_artifacts_* plan entry is observed"
            )
    else:
        # historic state: this flag remained even before sprint 3 because the
        # other direct rows lacked saved artifacts; keep it as open if not all
        # saved-artifact reruns are observed yet.
        pass
    if not expected_open.issubset(open_flags):
        fail(f"ICLR readiness audit missing open risks: {sorted(expected_open - open_flags)}")
    for closed_flag in [
        "iclr_style_binding_not_implemented",
        "iclr_style_pdf_not_built",
        "iclr_style_pdf_shape_not_verified",
        "iclr_openreview_packet_not_prepared",
    ]:
        if closed_flag in open_flags:
            fail(f"ICLR readiness audit should close provisional style risk: {closed_flag}")
    interpretation = payload.get("interpretation", {})
    for key in [
        "not_a_final_submission_gate",
        "local_shape_is_compatible_with_iclr_page_budget",
        "provisional_iclr_style_build_available",
        "must_not_claim_iclr_ready_until_open_risks_close",
    ]:
        if interpretation.get(key) is not True:
            fail(f"ICLR readiness interpretation check failed: {key}")
    if interpretation.get("venue_specific_reformatting_still_required") is not False:
        fail("ICLR readiness audit should mark provisional style reformatting as implemented")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    iclr_phrases = [
        "ICLR Submission Readiness Audit",
        "Recommended primary target: `ICLR 2027`",
        "ICLR-style submission PDF",
        "Official 2027 CFP observed: `False`",
        "Final ICLR submission status: not ready",
        "ethics statement audit",
        "LLM usage disclosure audit",
        "full-CIFAR BatchNorm posterior-policy ablations",
        "ICLR policy watch",
        "provisional OpenReview packet",
        "human confirmation template",
        "human confirmation receipt audit",
        "formal screening runbook",
        "formal screening receipt intake audit",
        "This file is generated by `scripts/audit_iclr_submission_readiness.py`.",
    ]
    if not locked_final_test_observed():
        iclr_phrases.append("locked_final_test_metrics_not_observed")
    for phrase in iclr_phrases:
        if phrase not in text:
            fail(f"ICLR submission readiness audit missing phrase: {phrase}")


def require_venue_strategy_matrix() -> None:
    json_path = ROOT / "runs" / "venue_strategy_matrix.json"
    doc_path = ROOT / "docs" / "venue_strategy_matrix.md"
    if not json_path.exists() or json_path.stat().st_size < 1000:
        fail("venue strategy matrix JSON missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 1000:
        fail("venue strategy matrix doc missing or too small")
    payload = load_json(json_path)
    if payload.get("venue_strategy_matrix_ready") is not True:
        fail(f"venue strategy matrix has local risk flags: {payload.get('risk_flags')}")
    if payload.get("risk_flags") != []:
        fail(f"venue strategy matrix risk flags are not empty: {payload.get('risk_flags')}")
    if payload.get("not_a_final_submission_gate") is not True:
        fail("venue strategy matrix must declare that it is not a final submission gate")
    if payload.get("source_observation_mode") != "recorded_live_probe":
        fail("venue strategy matrix should reuse a recorded live source probe")
    if payload.get("source_probe_json") != "runs/venue_source_probe.json":
        fail("venue strategy matrix points at the wrong source-probe JSON")
    if payload.get("source_probe_md") != "docs/venue_source_probe.md":
        fail("venue strategy matrix points at the wrong source-probe doc")
    source_probe = load_json(ROOT / "runs" / "venue_source_probe.json")
    if source_probe.get("venue_source_probe_ready") is not True:
        fail(f"venue source probe is not ready: {source_probe}")
    source_probe_text = (ROOT / "docs" / "venue_source_probe.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "Venue Source Probe",
        "Probe ready: `True`",
        "cikm_2026_full_research",
        "emnlp_2026_main_cfp",
        "bigdata_2026_cfp",
        "webconf_series_2027_listing",
    ]:
        if phrase not in source_probe_text:
            fail(f"venue source probe markdown missing phrase: {phrase}")
    observations = payload.get("source_probe_observations", [])
    if not isinstance(observations, list) or len(observations) < 10:
        fail("venue strategy matrix has incomplete source probe observations")
    observed_roles = {str(row.get("role")) for row in observations if isinstance(row, dict)}
    for role in [
        "iclr_2027_cfp_candidate",
        "iclr_2026_cfp_proxy",
        "aistats_2026_cfp_proxy",
        "aaai_26_main_track_proxy",
        "icdm_2026_research_track",
        "cikm_2026_full_research",
        "bigdata_2026_cfp",
        "wsdm_2027_host_bid_page",
        "emnlp_2026_main_cfp",
        "webconf_series_2027_listing",
        "icde_2027_research_track",
    ]:
        if role not in observed_roles:
            fail(f"venue strategy source probe missing role: {role}")
    decision = payload.get("decision", {})
    if decision.get("primary_target") != "TMLR (rolling)":
        fail(f"venue strategy primary target should be TMLR (rolling): {decision}")
    if decision.get("first_backup") != "ICLR 2027":
        fail(f"venue strategy first backup should be ICLR 2027: {decision}")
    if decision.get("second_backup") != "AISTATS 2027":
        fail(f"venue strategy second backup should be AISTATS 2027: {decision}")
    rows = payload.get("rows", [])
    venues = [row.get("venue") for row in rows]
    expected = [
        "TMLR (rolling)",
        "ICLR 2027",
        "AISTATS 2027",
        "AAAI 2027",
        "ICDM 2026",
        "CIKM 2026",
        "BIGDATA 2026",
        "WSDM 2027",
        "EMNLP 2026",
        "WWW 2027",
        "ICDE 2027",
    ]
    if venues != expected:
        fail(f"venue strategy ranking changed unexpectedly: {venues}")
    scores = [int(row.get("score", -1)) for row in rows]
    if scores != sorted(scores, reverse=True):
        fail(f"venue strategy scores are not descending: {scores}")
    open_flags = set(payload.get("open_risk_flags", []))
    always_open_venue_flags = [
        "iclr_2027_official_cfp_not_observed",
        "aistats_2027_official_cfp_not_observed",
        "aaai_2027_official_cfp_not_observed",
        "wsdm_2027_official_cfp_not_observed",
        "www_2027_official_cfp_not_observed",
        "formal_external_plagiarism_database_screen_not_performed",
        "external_gpu_container_run_not_observed",
    ]
    for flag in always_open_venue_flags:
        if flag not in open_flags:
            fail(f"venue strategy matrix missing open risk: {flag}")
    if locked_final_test_observed():
        if "locked_final_test_metrics_not_observed" in open_flags:
            fail("venue strategy matrix should drop locked-final-test risk after the rerun is observed")
    else:
        if "locked_final_test_metrics_not_observed" not in open_flags:
            fail("venue strategy matrix missing open risk: locked_final_test_metrics_not_observed")
    if "icde_2027_official_cfp_not_observed" in open_flags:
        fail("venue strategy matrix still treats observed ICDE 2027 CFP as missing")
    required_before = " ".join(payload.get("required_before_primary_submission", []))
    for phrase in [
        "locked final-test",
        "BatchNorm",
        "formal external plagiarism",
        "external CUDA/GPU receipts",
        "submit the prepared TMLR packet",
    ]:
        if phrase not in required_before:
            fail(f"venue strategy required-before list missing phrase: {phrase}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Venue Strategy Matrix",
        "Primary target: `TMLR (rolling)`",
        "First backup: `ICLR 2027`",
        "Source observation mode: `recorded_live_probe`",
        "Official Source Observations",
        "docs/venue_source_probe.md",
        "Do not chase fast deadlines",
        "`CIKM 2026`",
        "`EMNLP 2026`",
        "This file is generated by `scripts/build_venue_strategy_matrix.py`.",
    ]:
        if phrase not in text:
            fail(f"venue strategy matrix markdown missing phrase: {phrase}")


def require_top_conference_completion_audit() -> None:
    json_path = ROOT / "runs" / "top_conference_completion_audit.json"
    doc_path = ROOT / "docs" / "top_conference_completion_audit.md"
    if not json_path.exists() or json_path.stat().st_size < 1000:
        fail("top-conference completion audit JSON missing or too small")
    if not doc_path.exists() or doc_path.stat().st_size < 1000:
        fail("top-conference completion audit doc missing or too small")
    payload = load_json(json_path)
    if payload.get("top_conference_completion_audit_ready") is not True:
        fail(f"top-conference completion audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags") != []:
        fail(f"top-conference completion audit has generator risk flags: {payload.get('risk_flags')}")
    if payload.get("top_conference_goal_complete") is not False:
        fail("top-conference completion audit must not mark the active goal complete yet")
    if payload.get("must_not_mark_goal_complete") is not True:
        fail("top-conference completion audit should block goal completion")
    facts = payload.get("current_authoritative_facts", {})
    if facts.get("primary_venue") != "TMLR (rolling)":
        fail(f"top-conference completion audit primary venue changed: {facts}")
    archive = load_json(ROOT / "runs" / "public_release_archive_audit.json")
    snapshot = load_json(ROOT / "runs" / "public_repository_snapshot_audit.json")
    if facts.get("artifact_archive_sha256") != archive.get("archive_sha256"):
        fail("top-conference completion audit archive SHA is stale")
    if facts.get("source_repository_snapshot_commit") != snapshot.get("git", {}).get("commit"):
        fail("top-conference completion audit source snapshot commit is stale")
    if facts.get("external_validation_ready") is not False:
        fail("top-conference completion audit should reflect incomplete external validation")
    if facts.get("top_conference_release_ready") is not False:
        fail("top-conference completion audit should reflect incomplete strict release readiness")
    deliverables = payload.get("deliverables", [])
    if not isinstance(deliverables, list) or len(deliverables) < 6:
        fail("top-conference completion audit has too few deliverables")
    deliverable_names = {str(row.get("deliverable")) for row in deliverables if isinstance(row, dict)}
    for name in [
        "Venue strategy",
        "Local paper packet",
        "Final venue submission gate",
        "Scientific protocol hardening",
        "Local reproducibility package",
        "Strict external validation",
        "Originality and reference integrity",
    ]:
        if name not in deliverable_names:
            fail(f"top-conference completion audit missing deliverable: {name}")
    paper_packet = next(
        row
        for row in deliverables
        if isinstance(row, dict) and row.get("deliverable") == "Local paper packet"
    )
    if "docs/paper_asset_freshness_audit.md" not in set(
        str(item) for item in paper_packet.get("evidence", [])
    ):
        fail("top-conference completion audit local paper packet omits asset freshness")
    final_gate = next(
        row
        for row in deliverables
        if isinstance(row, dict) and row.get("deliverable") == "Final venue submission gate"
    )
    if "docs/iclr_human_confirmation_receipt_audit.md" not in set(
        str(item) for item in final_gate.get("evidence", [])
    ):
        fail("top-conference completion audit final gate omits human receipt audit")
    scientific_gate = next(
        row
        for row in deliverables
        if isinstance(row, dict) and row.get("deliverable") == "Scientific protocol hardening"
    )
    if "docs/remaining_experiment_queue.md" not in set(
        str(item) for item in scientific_gate.get("evidence", [])
    ):
        fail("top-conference completion audit scientific gate omits remaining experiment queue")
    if "docs/remaining_experiment_preflight_audit.md" not in set(
        str(item) for item in scientific_gate.get("evidence", [])
    ):
        fail("top-conference completion audit scientific gate omits remaining experiment preflight audit")
    checklist = payload.get("prompt_to_artifact_checklist", [])
    if not isinstance(checklist, list) or len(checklist) < 5:
        fail("top-conference completion audit checklist is incomplete")
    checklist_requirements = " ".join(str(row.get("explicit_requirement", "")) for row in checklist if isinstance(row, dict))
    for phrase in [
        "top conference level paper",
        "research results strong enough for review",
        "reproducible code and artifact",
        "plagiarism, hallucinated reference, and logic risk checked",
        "completion audit before goal closure",
    ]:
        if phrase not in checklist_requirements:
            fail(f"top-conference completion audit checklist missing phrase: {phrase}")
    open_blockers = set(str(flag) for flag in payload.get("open_blockers", []))
    expected_blockers = {
        "iclr_2027_official_cfp_not_observed",
        "iclr_openreview_submission_receipt_not_observed",
        "external_gpu_container_run_not_observed",
        "formal_external_plagiarism_database_screen_not_performed",
    }
    if external_receipts_registry_available():
        for receipt_name, blocker in (
            ("public_release_upload", "public_release_upload_not_verified"),
            ("public_repository", "public_repository_state_not_verified"),
            ("external_ci", "external_ci_run_not_observed"),
        ):
            if not external_receipt_observed(receipt_name):
                expected_blockers.add(blocker)
            elif blocker in open_blockers:
                fail(
                    "top-conference completion audit should drop "
                    f"{blocker} after the {receipt_name} receipt is observed"
                )
    else:
        # Release-package mode: the mutable registry is intentionally not
        # packaged, so accept either state for these receipt-tracked flags.
        for blocker in (
            "public_release_upload_not_verified",
            "public_repository_state_not_verified",
            "external_ci_run_not_observed",
        ):
            if blocker in open_blockers:
                expected_blockers.add(blocker)
    if locked_final_test_observed():
        leaked = {
            "locked_final_test_metrics_not_observed",
            "locked_final_test_rerun_not_observed",
        } & open_blockers
        if leaked:
            fail(f"top-conference completion audit should drop locked-final-test blockers: {sorted(leaked)}")
    else:
        expected_blockers.update(
            {
                "locked_final_test_metrics_not_observed",
                "locked_final_test_rerun_not_observed",
            }
        )
    if bn_ablation_observed():
        if "full_cifar_bn_ablation_rerun_not_observed" in open_blockers:
            fail(
                "top-conference completion audit should drop full_cifar_bn_ablation_rerun_not_observed "
                "after every bn_* plan entry is observed"
            )
    else:
        expected_blockers.add("full_cifar_bn_ablation_rerun_not_observed")
    if saved_artifact_reruns_observed():
        if "seed_level_saved_artifacts_incomplete_for_other_direct_rows" in open_blockers:
            fail(
                "top-conference completion audit should drop seed_level_saved_artifacts_incomplete_for_other_direct_rows "
                "after every saved_artifacts_* plan entry is observed"
            )
    else:
        expected_blockers.add("seed_level_saved_artifacts_incomplete_for_other_direct_rows")
    missing = expected_blockers.difference(open_blockers)
    if missing:
        fail(f"top-conference completion audit missing blockers: {sorted(missing)}")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in [
        "Top-Conference Completion Audit",
        "Goal status: not complete.",
        "Must not mark goal complete: True.",
        "Objective Restatement",
        "Prompt-To-Artifact Checklist",
        "docs/paper_asset_freshness_audit.md",
        "docs/iclr_human_confirmation_receipt_audit.md",
        "Open Blockers",
        "Do not mark the active goal complete",
        "scripts/build_top_conference_completion_audit.py",
    ]:
        if phrase not in text:
            fail(f"top-conference completion audit markdown missing phrase: {phrase}")


def require_release_metadata_docs() -> None:
    doc_terms = {
        "docs/compute_resource_accounting.md": [
            "Compute Resource Accounting",
            "NVIDIA GeForce RTX 5090",
            "Torch CUDA 13.0",
            "553.1 GiB",
            "1,106.3 GiB",
            "wall-clock",
            "mask_artifacts.npz",
        ],
        "docs/asset_license_inventory.md": [
            "Asset License Inventory",
            "MIT License",
            "LICENSE",
            "Anonymous Authors",
            "MNIST",
            "Fashion-MNIST",
            "CIFAR-10",
            "CIFAR-100",
            "raw benchmark datasets",
            "third-party",
        ],
        "docs/new_asset_inventory.md": [
            "New Asset Inventory",
            "public_release_manifest",
            "mask_artifacts.npz",
            "paper/neurips_submission.pdf",
            "data/",
            "Public Release Status",
        ],
    }
    for rel, phrases in doc_terms.items():
        path = ROOT / rel
        if not path.exists() or path.stat().st_size < 1000:
            fail(f"release metadata doc missing or too small: {rel}")
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                fail(f"release metadata doc {rel} missing phrase: {phrase}")


def require_release_manifest() -> None:
    manifest = load_json(ROOT / "runs" / "public_release_manifest.json")
    if manifest.get("root") != ".":
        fail("public release manifest root should be anonymized as '.'")
    manifest_text = json.dumps(manifest, sort_keys=True)
    forbidden_manifest_terms = [
        "/home/",
        "/Users/",
        "\\\\Users\\\\",
        "/Projects/" + "Lottery",
        "suan" + "lab",
        "MyUbuntu" + "5090",
    ]
    for term in forbidden_manifest_terms:
        if term in manifest_text:
            fail(f"public release manifest contains local identity/path term: {term}")
    if int(manifest.get("file_count", 0)) < 150:
        fail("public release manifest has too few files")
    files = {
        str(entry["path"]): entry
        for entry in manifest.get("files", [])
        if isinstance(entry, dict) and "path" in entry
    }
    if any(path.startswith("data/") for path in files):
        fail("public release manifest should not include raw data/ caches")
    stale_venue_paths = [
        path
        for path in files
        if "tmlr" in path.lower()
        # tmlr_packet_freshness_audit.* is a public-facing freshness audit
        # produced by scripts/audit_tmlr_packet_freshness.py; it is generated
        # at make-check time, never carries author identity, and is the
        # mechanism that flags the 2026-05-08 TMLR operator packet as
        # stale. It is therefore allowed in the public release manifest.
        and "tmlr_packet_freshness_audit" not in path
    ]
    if stale_venue_paths:
        fail(f"public release manifest should exclude stale TMLR operator files: {stale_venue_paths[:5]}")
    if "docs/external_validation_receipts.json" in files:
        fail("public release manifest should exclude the mutable external receipt registry")
    for mutable_receipt in [
        "docs/external_gpu_container_receipt.md",
        "runs/external_gpu_container_receipt.json",
        "docs/formal_plagiarism_screening_receipt.json",
        "docs/iclr_human_confirmation_receipt.json",
    ]:
        if mutable_receipt in files:
            fail(f"public release manifest should exclude mutable receipt: {mutable_receipt}")
    required_paths = [
        ".dockerignore",
        ".github/workflows/check.yml",
        ".gitignore",
        "Dockerfile",
        "Dockerfile.gpu",
        "LICENSE",
        "Makefile",
        "README.md",
        "requirements-ci.txt",
        "requirements-gpu-lock.txt",
        "requirements-lock.txt",
        "docs/container_lock.md",
        "docs/gpu_training_container.md",
        "docs/local_gpu_container_validation.md",
        "docs/compute_resource_accounting.md",
        "docs/asset_license_inventory.md",
        "docs/new_asset_inventory.md",
        "docs/cifar10_resnet20_full_covariance_feasibility.md",
        "docs/digits_fullnet_laplace_tiny_r2_p0p3.md",
        "docs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke.md",
        "docs/linear_connectivity_barrier_audit.md",
        "docs/posterior_covariance_robustness_audit.md",
        "docs/cifar10_resnet20_long30_rewind1_lowrank_laplace_movement_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_lowrank32_laplace_movement_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_lowrank64_laplace_movement_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_lowrank128_laplace_movement_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_max10k_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max10k_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max20k_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max40k_stream_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_hessian32_subspace_hmc_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_hard_concrete_selected_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_weight_aligned_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_independent_multichain_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_r5_p0p3.md",
        "docs/fake_cifar10_mode_ticket_mask_artifact_smoke.md",
        "docs/fake_cifar10_mode_ticket_mask_artifact_posthoc_audit.md",
        "docs/mode_ticket_artifact_storage_budget.md",
        "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.md",
        "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_global_channel_audit.md",
        "docs/resnet_channel_permutation_exhaustive_feasibility_audit.md",
        "docs/cifar10_subset_hard_concrete_mask_training_smoke.md",
        "docs/cifar10_resnet20_long30_rewind1_residual_imp_process_stratified_exclusion_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_residual_imp_process_projection_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_residual_imp_process_posterior_projection_r5_p0p3.md",
        "docs/cifar10_resnet20_long30_rewind1_residual_imp_process_learned_subspace_r5_p0p3.md",
        "docs/environment_lock.json",
        "docs/mode_ticket_alignment_artifact_audit.md",
        "docs/paper_claim_ledger.md",
        "docs/paper_submission_shape_audit.md",
        "docs/submission_pdf_shape_audit.md",
        "docs/venue_submission_compliance_audit.md",
        "docs/ethics_statement_audit.md",
        "docs/llm_usage_disclosure_audit.md",
        "docs/iclr_policy_watch_audit.md",
        "docs/iclr_policy_source_probe.md",
        "docs/venue_source_probe.md",
        "docs/iclr_openreview_packet.md",
        "docs/iclr_human_confirmation_template.md",
        "docs/iclr_human_confirmation_receipt_audit.md",
        "docs/venue_strategy_matrix.md",
        "docs/formal_plagiarism_screening_runbook.md",
        "docs/formal_plagiarism_screening_receipt_audit.md",
        "docs/reviewer_objection_matrix.md",
        "docs/reproducibility_manifest.md",
        "docs/unit_smoke_tests.md",
        "docs/submission_readiness_audit.md",
        "docs/thread_goal_completion_audit.md",
        "docs/remaining_experiment_queue.md",
        "docs/remaining_experiment_preflight_audit.md",
        "runs/mode_ticket_alignment_artifact_audit.json",
        "runs/fake_cifar10_mode_ticket_mask_artifact_posthoc_audit.json",
        "runs/mode_ticket_artifact_storage_budget.json",
        "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.json",
        "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_global_channel_audit.json",
        "runs/resnet_channel_permutation_exhaustive_feasibility_audit.json",
        "runs/paper_submission_shape_audit.json",
        "runs/submission_pdf_shape_audit.json",
        "runs/venue_submission_compliance_audit.json",
        "runs/ethics_statement_audit.json",
        "runs/llm_usage_disclosure_audit.json",
        "runs/iclr_policy_watch_audit.json",
        "runs/iclr_policy_source_probe.json",
        "runs/venue_source_probe.json",
        "runs/iclr_openreview_packet.json",
        "runs/iclr_human_confirmation_template.json",
        "runs/iclr_human_confirmation_receipt_audit.json",
        "runs/venue_strategy_matrix.json",
        "runs/formal_plagiarism_screening_runbook.json",
        "runs/formal_plagiarism_screening_receipt_audit.json",
        "runs/unit_smoke_tests.json",
        "runs/local_gpu_container_validation.json",
        "runs/reviewer_objection_matrix.json",
        "runs/paper_stats.json",
        "runs/paper_asset_freshness_audit.json",
        "runs/remaining_experiment_queue.json",
        "runs/remaining_experiment_preflight_audit.json",
        "paper/main.tex",
        "paper/refs.bib",
        "paper/main.pdf",
        "paper/main_submission.pdf",
        "paper/neurips_2026.sty",
        "paper/neurips_checklist.tex",
        "paper/neurips_submission.pdf",
        "paper/iclr2026_conference.sty",
        "paper/iclr2026_conference.bst",
        "paper/iclr_submission.pdf",
        "paper/tables/statistical_summary.tex",
        "scripts/audit_mode_ticket_alignment_artifacts.py",
        "scripts/audit_paper_asset_freshness.py",
        "scripts/audit_mask_artifact_posthoc_matching.py",
        "scripts/audit_full_data_channel_permutation_matching.py",
        "scripts/audit_exhaustive_channel_permutation_feasibility.py",
        "scripts/audit_mode_ticket_artifact_storage_budget.py",
        "scripts/run_digits_fullnet_laplace_probe.py",
        "scripts/summarize_fullnet_laplace_probe.py",
        "scripts/audit_linear_connectivity_barriers.py",
        "scripts/audit_posterior_covariance_robustness.py",
        "src/lottery/full_laplace.py",
        "scripts/build_paper_claim_ledger.py",
        "scripts/run_unit_smoke_tests.py",
        "scripts/audit_paper_submission_shape.py",
        "scripts/audit_submission_pdf_shape.py",
        "scripts/audit_venue_submission_compliance.py",
        "scripts/build_remaining_experiment_queue.py",
        "scripts/audit_remaining_experiment_preflight.py",
        "scripts/audit_open_blocker_claim_scope.py",
        "scripts/audit_iclr_submission_readiness.py",
        "scripts/audit_ethics_statement.py",
        "scripts/audit_llm_usage_disclosure.py",
        "scripts/build_iclr_policy_watch_audit.py",
        "scripts/build_iclr_openreview_packet.py",
        "scripts/build_iclr_human_confirmation_template.py",
        "scripts/build_formal_plagiarism_screening_runbook.py",
        "scripts/audit_formal_plagiarism_screening_receipt.py",
        "scripts/build_reviewer_objection_matrix.py",
        "scripts/audit_external_validation_readiness.py",
        "scripts/build_external_validation_receipt_template.py",
        "scripts/update_external_validation_receipts.py",
        "scripts/build_external_validation_runbook.py",
        "scripts/build_submission_handoff.py",
        "scripts/run_validation_bn_rerun_plan_entry.py",
        "scripts/stage_public_repository_snapshot.py",
        "scripts/smoke_public_repository_snapshot.py",
        "scripts/verify_source_repository_snapshot.py",
        "scripts/audit_release_anonymization.py",
        "scripts/build_public_release_archive.py",
        "scripts/smoke_public_release_archive.py",
        "scripts/check_gpu_training_environment.py",
        "scripts/run_gpu_container_env_check.py",
        "scripts/build_local_gpu_container_validation.py",
        "scripts/build_external_gpu_container_receipt.py",
        "runs/cifar10_resnet20_full_covariance_feasibility.json",
        "runs/digits_fullnet_laplace_tiny_r2_p0p3_summary.csv",
        "runs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke_summary.csv",
        "runs/linear_connectivity_barrier_audit.csv",
        "runs/linear_connectivity_barrier_audit.json",
        "runs/posterior_covariance_robustness_audit.csv",
        "runs/posterior_covariance_robustness_audit.json",
        "runs/cifar10_resnet20_long30_rewind1_lowrank_laplace_movement_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_lowrank32_laplace_movement_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_lowrank64_laplace_movement_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_lowrank128_laplace_movement_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_max10k_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max10k_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max20k_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max40k_stream_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_hessian32_subspace_hmc_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_hard_concrete_selected_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_weight_aligned_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_independent_multichain_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3/20260506_230706/metrics.json",
        "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3/20260506_230706/mask_artifacts.npz",
        "runs/fake_cifar10_mode_ticket_mask_artifact_smoke_summary.csv",
        "runs/cifar10_subset_hard_concrete_mask_training_smoke_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_residual_imp_process_stratified_exclusion_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_residual_imp_process_projection_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_residual_imp_process_posterior_projection_r5_p0p3_summary.csv",
        "runs/cifar10_resnet20_long30_rewind1_residual_imp_process_learned_subspace_r5_p0p3_summary.csv",
    ]
    missing = [path for path in required_paths if path not in files]
    if missing:
        fail(f"public release manifest missing required paths: {missing}")
    mask_artifact_paths = [
        path
        for path in files
        if path.startswith("runs/fake_cifar10_mode_ticket_mask_artifact_smoke/")
        and path.endswith("/mask_artifacts.npz")
    ]
    if not mask_artifact_paths:
        fail("public release manifest missing mask_artifacts.npz smoke fixture")
    for rel in required_paths:
        expected = str(files[rel].get("sha256", ""))
        actual = sha256(ROOT / rel)
        if actual != expected:
            fail(f"public release manifest hash mismatch for {rel}")
    for rel in mask_artifact_paths:
        expected = str(files[rel].get("sha256", ""))
        actual = sha256(ROOT / rel)
        if actual != expected:
            fail(f"public release manifest hash mismatch for {rel}")
    release_text = (ROOT / "docs" / "public_release_manifest.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "Total files:",
        "Required Artifacts",
        "make paper-check",
        "make paper-neurips-check",
        "make paper-iclr-check",
    ]:
        if phrase not in release_text:
            fail(f"public release manifest markdown missing phrase: {phrase}")


def require_release_anonymization_audit() -> None:
    payload = load_json(ROOT / "runs" / "release_anonymization_audit.json")
    if payload.get("manifest") != "runs/public_release_manifest.json":
        fail("release anonymization audit points at the wrong manifest")
    if payload.get("manifest_root") != ".":
        fail("release anonymization audit should confirm manifest root '.'")
    if payload.get("release_anonymization_ready") is not True:
        fail(
            "release anonymization audit should be ready: "
            f"{payload.get('risk_flags')}"
        )
    if payload.get("risk_flags") != []:
        fail(f"release anonymization audit has risk flags: {payload.get('risk_flags')}")
    if int(payload.get("finding_count", -1)) != 0:
        fail("release anonymization audit should have zero findings")
    if payload.get("findings") not in ([], None):
        fail("release anonymization audit findings should be empty")
    if payload.get("forbidden_manifest_paths") not in ([], None):
        fail("release anonymization audit should not find forbidden manifest paths")
    if payload.get("missing_paths") not in ([], None):
        fail("release anonymization audit should not find missing manifest paths")
    if int(payload.get("manifest_file_count", 0)) < 150:
        fail("release anonymization audit saw too few manifest files")
    if int(payload.get("scanned_text_files", 0)) < 100:
        fail("release anonymization audit scanned too few text files")

    doc_text = (ROOT / "docs" / "release_anonymization_audit.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "Release Anonymization Audit",
        "Current status: ready.",
        "runs/public_release_manifest.json",
        "Risk Flags",
        "- none",
        "This file is generated by `scripts/audit_release_anonymization.py`.",
    ]:
        if phrase not in doc_text:
            fail(f"release anonymization audit markdown missing phrase: {phrase}")


def require_public_release_archive() -> None:
    payload = load_json(ROOT / "runs" / "public_release_archive_audit.json")
    if payload.get("archive_ready") is not True:
        fail(f"public release archive should be ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags") != []:
        fail(f"public release archive has risk flags: {payload.get('risk_flags')}")
    if payload.get("manifest_root") != ".":
        fail("public release archive audit should confirm manifest root '.'")
    if payload.get("package_root") != "lottery_artifact_public_release":
        fail("public release archive package root changed unexpectedly")
    if int(payload.get("manifest_file_count", 0)) < 150:
        fail("public release archive audit saw too few manifest files")
    if int(payload.get("release_metadata_count", 0)) != 4:
        fail("public release archive should include four release metadata sidecars")
    if int(payload.get("expected_member_count", 0)) != int(
        payload.get("actual_member_count", -1)
    ):
        fail("public release archive member count mismatch")
    if int(payload.get("archive_bytes", 0)) < 100_000_000:
        fail("public release archive is unexpectedly small")
    for key in [
        "missing_source_paths",
        "missing_members",
        "extra_members",
        "unsafe_members",
        "non_file_members",
        "member_size_mismatches",
    ]:
        if payload.get(key) not in ([], None):
            fail(f"public release archive audit has {key}: {payload.get(key)}")
    expected_metadata = {
        "docs/public_release_manifest.md",
        "runs/public_release_manifest.json",
        "docs/release_anonymization_audit.md",
        "runs/release_anonymization_audit.json",
    }
    if set(payload.get("release_metadata_paths", [])) != expected_metadata:
        fail("public release archive metadata sidecars changed unexpectedly")

    archive = ROOT / str(payload.get("archive", ""))
    sidecar = ROOT / str(payload.get("sha256_sidecar", ""))
    if not archive.exists():
        fail(f"public release archive missing: {archive}")
    if not sidecar.exists():
        fail(f"public release archive sha256 sidecar missing: {sidecar}")
    digest = sha256(archive)
    if digest != payload.get("archive_sha256"):
        fail("public release archive sha256 does not match audit JSON")
    sidecar_text = sidecar.read_text(encoding="utf-8").strip()
    if not sidecar_text.startswith(f"{digest}  "):
        fail("public release archive sha256 sidecar does not match archive")

    doc_text = (ROOT / "docs" / "public_release_archive_audit.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "Public Release Archive Audit",
        "Current status: ready.",
        "dist/lottery_artifact_public_release_2026-05-06.tar.gz",
        "Release metadata sidecars",
        "Risk Flags",
        "- none",
        "This file is generated by `scripts/build_public_release_archive.py`.",
    ]:
        if phrase not in doc_text:
            fail(f"public release archive audit markdown missing phrase: {phrase}")


def require_public_release_archive_smoke() -> None:
    payload = load_json(ROOT / "runs" / "public_release_archive_smoke.json")
    if payload.get("release_archive_smoke_ready") is not True:
        fail(f"public release archive smoke should be ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags") != []:
        fail(f"public release archive smoke has risk flags: {payload.get('risk_flags')}")
    if payload.get("package_root") != "lottery_artifact_public_release":
        fail("public release archive smoke package root changed unexpectedly")
    if payload.get("manifest_root") != ".":
        fail("public release archive smoke should confirm manifest root '.'")
    if int(payload.get("manifest_file_count", 0)) < 150:
        fail("public release archive smoke saw too few manifest files")
    if int(payload.get("expected_file_count", 0)) != int(
        payload.get("actual_file_count", -1)
    ):
        fail("public release archive smoke extracted file count mismatch")
    if int(payload.get("checked_hash_count", 0)) < 150:
        fail("public release archive smoke checked too few manifest hashes")
    verifier = payload.get("verifier", {})
    if not isinstance(verifier, dict) or verifier.get("returncode") != 0:
        fail(f"public release extracted-package verifier failed: {verifier}")
    if "verified research artifacts" not in str(verifier.get("stdout_tail", "")):
        fail("public release extracted-package verifier output missing success marker")
    for key in ["metadata_missing", "missing_files", "extra_files", "hash_mismatches"]:
        if payload.get(key) not in ([], None):
            fail(f"public release archive smoke has {key}: {payload.get(key)}")

    doc_text = (ROOT / "docs" / "public_release_archive_smoke.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "Public Release Archive Smoke Test",
        "Current status: ready.",
        "runs the artifact verifier in release-package mode",
        "Risk Flags",
        "- none",
        "verified research artifacts",
        "This file is generated by `scripts/smoke_public_release_archive.py`.",
    ]:
        if phrase not in doc_text:
            fail(f"public release archive smoke markdown missing phrase: {phrase}")


def require_public_repository_snapshot_audit() -> None:
    payload = load_json(ROOT / "runs" / "public_repository_snapshot_audit.json")
    if payload.get("public_repository_snapshot_ready") is not True:
        fail(f"public repository snapshot should be ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags") != []:
        fail(f"public repository snapshot has risk flags: {payload.get('risk_flags')}")
    if payload.get("marker") != ".lottery_public_repository_snapshot":
        fail("public repository snapshot marker changed unexpectedly")
    if int(payload.get("source_file_count", 0)) < 100:
        fail("public repository snapshot has too few source files")
    if int(payload.get("tracked_file_count", 0)) != int(payload.get("source_file_count", -1)) + 1:
        fail("public repository snapshot tracked count should include source files plus marker")
    if int(payload.get("max_file_bytes", 0)) != 100_000_000:
        fail("public repository snapshot max file limit changed unexpectedly")
    if payload.get("oversized_files") not in ([], None):
        fail(f"public repository snapshot has oversized files: {payload.get('oversized_files')}")
    if payload.get("text_findings") not in ([], None):
        fail(f"public repository snapshot has text findings: {payload.get('text_findings')}")
    git = payload.get("git", {})
    if not isinstance(git, dict) or git.get("git_ready") is not True:
        fail(f"public repository snapshot git state is not ready: {git}")
    if git.get("git_clean") is not True:
        fail("public repository snapshot git state should be clean")
    commit = str(git.get("commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        fail(f"public repository snapshot commit is not a git SHA1: {commit}")
    stage_dir = ROOT / str(payload.get("stage_dir", ""))
    if not (stage_dir / ".git").is_dir():
        fail(f"public repository snapshot stage dir missing .git: {stage_dir}")
    if not (stage_dir / ".lottery_public_repository_snapshot").is_file():
        fail(f"public repository snapshot marker missing: {stage_dir}")
    stale_venue_paths = [
        path.relative_to(stage_dir).as_posix()
        for path in stage_dir.rglob("*")
        if path.is_file()
        and "tmlr" in path.relative_to(stage_dir).as_posix().lower()
        # See public-release-manifest exemption above: the freshness audit
        # is the mechanism that flags the 2026-05-08 packet as stale and is
        # safe to publish.
        and "tmlr_packet_freshness_audit"
        not in path.relative_to(stage_dir).as_posix()
    ]
    if stale_venue_paths:
        fail(f"public repository snapshot should exclude stale TMLR operator files: {stale_venue_paths[:5]}")
    doc_text = (ROOT / "docs" / "public_repository_snapshot_audit.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "Public Repository Snapshot Audit",
        "Current status: ready.",
        "source-only anonymous git repository",
        "mutable external receipt registry",
        "run-artifact package remains the separate public",
        "Git commit",
        "Risk Flags",
        "- none",
        "This file is generated by `scripts/stage_public_repository_snapshot.py`.",
    ]:
        if phrase not in doc_text:
            fail(f"public repository snapshot audit markdown missing phrase: {phrase}")


def require_public_repository_snapshot_smoke() -> None:
    payload = load_json(ROOT / "runs" / "public_repository_snapshot_smoke.json")
    if payload.get("source_repository_smoke_ready") is not True:
        fail(f"public repository snapshot smoke should be ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags") != []:
        fail(f"public repository snapshot smoke has risk flags: {payload.get('risk_flags')}")
    check = payload.get("check", {})
    if not isinstance(check, dict) or check.get("returncode") != 0:
        fail(f"public repository snapshot smoke check failed: {check}")
    if check.get("success_marker_seen") is not True:
        fail("public repository snapshot smoke missing source verification marker")
    git = payload.get("git", {})
    if not isinstance(git, dict) or not re.fullmatch(r"[0-9a-f]{40}", str(git.get("commit", ""))):
        fail(f"public repository snapshot smoke missing git commit: {git}")
    doc_text = (ROOT / "docs" / "public_repository_snapshot_smoke.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "Public Repository Snapshot Smoke Test",
        "Current status: ready.",
        "make source-repository-check",
        "source_repository_snapshot_verified",
        "Risk Flags",
        "- none",
        "This file is generated by `scripts/smoke_public_repository_snapshot.py`.",
    ]:
        if phrase not in doc_text:
            fail(f"public repository snapshot smoke markdown missing phrase: {phrase}")


def require_external_validation_readiness_audit() -> None:
    payload = load_json(ROOT / "runs" / "external_validation_readiness_audit.json")
    local = payload.get("local", {})
    if not isinstance(local, dict):
        fail("external validation audit missing local gate payload")
    if local.get("local_artifact_release_ready") is not True:
        fail(f"external validation audit local release gates are not ready: {local}")
    gates = local.get("gates", {})
    for key in [
        "release_anonymization",
        "public_release_archive",
        "public_release_archive_smoke",
        "archive_sha256_sidecar",
    ]:
        if not isinstance(gates, dict) or gates.get(key) is not True:
            fail(f"external validation audit local gate not ready: {key}")
    required_receipts = set(payload.get("required_receipts", []))
    expected_receipts = {
        "public_release_upload",
        "public_repository",
        "external_ci",
        "external_gpu_container",
    }
    if required_receipts != expected_receipts:
        fail(f"external validation audit required receipts changed: {required_receipts}")
    receipt_rows = payload.get("receipt_statuses", [])
    if not isinstance(receipt_rows, list) or len(receipt_rows) != len(expected_receipts):
        fail("external validation audit has incomplete receipt rows")
    row_keys = {str(row.get("key")) for row in receipt_rows if isinstance(row, dict)}
    if row_keys != expected_receipts:
        fail(f"external validation audit receipt rows changed: {row_keys}")
    repository_snapshot = payload.get("public_repository_snapshot", {})
    if not isinstance(repository_snapshot, dict):
        fail("external validation audit missing public repository snapshot status")
    if repository_snapshot.get("public_repository_snapshot_ready") is not True:
        fail(f"external validation audit should see a ready repository snapshot: {repository_snapshot}")
    if payload.get("local_clean_repository_ready") is not True:
        fail("external validation audit should mark local clean repository staging ready")
    if payload.get("clean_repository_ready") is not True:
        fail("external validation audit should mark clean repository status ready locally")
    risk_flags = set(payload.get("risk_flags", []))
    open_receipt_flags: set[str] = set()
    stale_receipt_keys: set[str] = set()
    for row in receipt_rows:
        if not isinstance(row, dict):
            fail(f"external validation audit receipt row is not an object: {row}")
        invalid = set(str(item) for item in row.get("invalid", []))
        mismatch_reasons = invalid.intersection(
            {"artifact_sha256_mismatch", "commit_mismatch"}
        )
        comparison_details = row.get("comparison_details", [])
        if not isinstance(comparison_details, list):
            fail(f"external validation audit receipt comparisons are not a list: {row}")
        if "artifact_sha256_mismatch" in mismatch_reasons:
            if not any(
                isinstance(item, dict) and item.get("field") == "artifact_sha256"
                for item in comparison_details
            ):
                fail(f"external validation audit missing archive SHA comparison: {row}")
        if "commit_mismatch" in mismatch_reasons:
            if not any(
                isinstance(item, dict) and item.get("field") == "commit"
                for item in comparison_details
            ):
                fail(f"external validation audit missing commit comparison: {row}")
        expected_stale = row.get("status") == "observed" and bool(mismatch_reasons)
        if row.get("stale") is not expected_stale:
            fail(f"external validation audit stale receipt marker is wrong: {row}")
        stale_reasons = set(str(item) for item in row.get("stale_reasons", []))
        if not mismatch_reasons.issubset(stale_reasons):
            fail(f"external validation audit stale reasons omit mismatch details: {row}")
        if expected_stale:
            stale_receipt_keys.add(str(row.get("key")))
        flag = str(row.get("risk_flag", "")).strip()
        if row.get("ready") is True:
            if flag:
                fail(f"ready external receipt still carries a risk flag: {row}")
        else:
            if not flag:
                fail(f"open external receipt missing risk flag: {row}")
            open_receipt_flags.add(flag)
    if payload.get("external_validation_ready") is True:
        external_flags = {
            "public_release_upload_not_verified",
            "public_repository_state_not_verified",
            "external_ci_run_not_observed",
            "external_gpu_container_run_not_observed",
        }
        if risk_flags & external_flags:
            fail("external validation audit is ready but still has external risk flags")
        if open_receipt_flags:
            fail(f"external validation audit is ready but has open receipt flags: {open_receipt_flags}")
        if payload.get("top_conference_release_ready") is not True:
            fail("external validation audit ready state should imply top-conference release ready")
    else:
        if not open_receipt_flags:
            fail("external validation audit is not ready but no open receipt flags were found")
        missing_flags = sorted(open_receipt_flags.difference(risk_flags))
        if missing_flags:
            fail(f"external validation audit missing open receipt flags: {missing_flags}")
        if payload.get("top_conference_release_ready") is True:
            fail("external validation audit top-conference status should not be ready while receipts are missing")
    doc_text = (ROOT / "docs" / "external_validation_readiness_audit.md").read_text(
        encoding="utf-8"
    )
    required_phrases = [
        "External Validation Readiness Audit",
        "Current local artifact-release status: ready.",
        "Current external-validation status:",
        "Current top-conference release status:",
        "Public Repository Snapshot",
        "runs/public_repository_snapshot_audit.json",
        "docs/external_validation_receipts.json",
        "URL checks enabled:",
        "Strict Gate",
        "python scripts/audit_external_validation_readiness.py --strict",
        "This file is generated by `scripts/audit_external_validation_readiness.py`.",
    ]
    if payload.get("external_validation_ready") is not True:
        required_phrases.extend(sorted(open_receipt_flags))
    if stale_receipt_keys:
        required_phrases.extend(
            [
                "Stale Observed Receipts",
                "Evidence comparison",
                "must be replaced, not reused",
            ]
        )
        required_phrases.extend(sorted(stale_receipt_keys))
    for phrase in required_phrases:
        if phrase not in doc_text:
            fail(f"external validation readiness audit markdown missing phrase: {phrase}")


def require_external_validation_claim_audit() -> None:
    json_path = ROOT / "runs" / "external_validation_claim_audit.json"
    doc_path = ROOT / "docs" / "external_validation_claim_audit.md"
    payload = load_json(json_path)
    if payload.get("external_validation_claim_audit_ready") is not True:
        fail(f"external validation claim audit is not ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags"):
        fail(f"external validation claim audit has risk flags: {payload.get('risk_flags')}")
    readiness = load_json(ROOT / "runs" / "external_validation_readiness_audit.json")
    if payload.get("external_validation_ready") != readiness.get("external_validation_ready"):
        fail("external validation claim audit readiness state is stale")
    if payload.get("top_conference_release_ready") != readiness.get("top_conference_release_ready"):
        fail("external validation claim audit top-conference state is stale")
    if int(payload.get("scanned_file_count", 0)) < 10:
        fail("external validation claim audit scanned too few files")
    if int(payload.get("forbidden_rule_count", 0)) < 5:
        fail("external validation claim audit rule set is too small")
    if payload.get("findings") not in ([], None):
        fail(f"external validation claim audit should have no stale positive findings: {payload.get('findings')}")
    doc_text = (ROOT / "docs" / "external_validation_claim_audit.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "External Validation Claim Audit",
        "Stale Positive Claim Findings",
        "This file is generated by `scripts/audit_external_validation_claims.py`.",
    ]:
        if phrase not in doc_text:
            fail(f"external validation claim audit markdown missing phrase: {phrase}")


def require_external_validation_receipt_template() -> None:
    payload = load_json(ROOT / "runs" / "external_validation_receipt_template.json")
    if payload.get("external_validation_receipt_template_ready") is not True:
        fail(f"external validation receipt template should be ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags") != []:
        fail(f"external validation receipt template has risk flags: {payload.get('risk_flags')}")
    archive = load_json(ROOT / "runs" / "public_release_archive_audit.json")
    snapshot = load_json(ROOT / "runs" / "public_repository_snapshot_audit.json")
    facts = payload.get("local_facts", {})
    if facts.get("archive_sha256") != archive.get("archive_sha256"):
        fail("external validation receipt template archive SHA256 does not match archive audit")
    source_commit = snapshot.get("git", {}).get("commit")
    if facts.get("source_repository_commit") != source_commit:
        fail("external validation receipt template source commit does not match snapshot audit")
    template = payload.get("receipt_template", {})
    receipts = template.get("receipts", {}) if isinstance(template, dict) else {}
    expected = {
        "public_release_upload",
        "public_repository",
        "external_ci",
        "external_gpu_container",
    }
    if set(receipts) != expected:
        fail(f"external validation receipt template receipts changed: {set(receipts)}")
    if receipts["public_release_upload"].get("artifact_sha256") != archive.get("archive_sha256"):
        fail("external validation receipt template has stale archive SHA256")
    for key in ["public_repository", "external_ci", "external_gpu_container"]:
        if receipts[key].get("commit") != source_commit:
            fail(f"external validation receipt template has stale source commit for {key}")
    for key, row in receipts.items():
        if row.get("status") != "pending":
            fail(f"external validation receipt template should not mark observed evidence: {key}")
    doc_text = (ROOT / "docs" / "external_validation_receipt_template.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "External Validation Receipt Template",
        "Template status: ready.",
        "Archive SHA256",
        "Source snapshot commit",
        "Prefilled Fields",
        "Manual Fields",
        "Receipt Update Helper",
        "scripts/update_external_validation_receipts.py --require-all",
        "Final Validation",
        "runs/external_validation_receipt_template.json",
        "scripts/build_external_validation_receipt_template.py",
    ]:
        if phrase not in doc_text:
            fail(f"external validation receipt template markdown missing phrase: {phrase}")


def require_external_validation_runbook() -> None:
    payload = load_json(ROOT / "runs" / "external_validation_runbook.json")
    if payload.get("external_validation_runbook_ready") is not True:
        fail(f"external validation runbook should be ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags") != []:
        fail(f"external validation runbook has risk flags: {payload.get('risk_flags')}")
    archive = load_json(ROOT / "runs" / "public_release_archive_audit.json")
    snapshot = load_json(ROOT / "runs" / "public_repository_snapshot_audit.json")
    facts = payload.get("local_facts", {})
    if facts.get("archive_sha256") != archive.get("archive_sha256"):
        fail("external validation runbook archive SHA256 does not match archive audit")
    if facts.get("source_repository_commit") != snapshot.get("git", {}).get("commit"):
        fail("external validation runbook source commit does not match snapshot audit")
    required = set(payload.get("required_external_receipts", []))
    expected = {
        "public_release_upload",
        "public_repository",
        "external_ci",
        "external_gpu_container",
    }
    if required != expected:
        fail(f"external validation runbook required receipts changed: {required}")
    readiness = load_json(ROOT / "runs" / "external_validation_readiness_audit.json")
    readiness_stale = {
        str(row.get("key"))
        for row in readiness.get("receipt_statuses", [])
        if isinstance(row, dict) and row.get("stale") is True
    }
    blocking_receipts = payload.get("blocking_receipts", [])
    if not isinstance(blocking_receipts, list):
        fail("external validation runbook blocking receipts should be a list")
    runbook_stale = {
        str(row.get("key"))
        for row in blocking_receipts
        if isinstance(row, dict) and row.get("stale") is True
    }
    if runbook_stale != readiness_stale:
        fail(
            "external validation runbook stale receipts do not match readiness audit: "
            f"{runbook_stale} != {readiness_stale}"
        )
    for row in blocking_receipts:
        if not isinstance(row, dict):
            fail(f"external validation runbook blocking receipt is not an object: {row}")
        invalid = set(str(item) for item in row.get("invalid", []))
        comparison_details = row.get("comparison_details", [])
        if invalid.intersection({"artifact_sha256_mismatch", "commit_mismatch"}):
            if not isinstance(comparison_details, list) or not comparison_details:
                fail(f"external validation runbook missing mismatch comparisons: {row}")
    commands = payload.get("commands", {})
    facts = payload.get("local_facts", {})
    if facts.get("receipt_template") != "docs/external_validation_receipt_template.md":
        fail("external validation runbook missing receipt template fact")
    for section in [
        "local_preflight",
        "archive_upload",
        "source_repository_publish",
        "external_ci",
        "external_gpu_container",
        "receipt_registry_update",
        "final_gate",
    ]:
        if not isinstance(commands, dict) or not commands.get(section):
            fail(f"external validation runbook missing commands section: {section}")
    doc_text = (ROOT / "docs" / "external_validation_runbook.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "External Validation Runbook",
        "Runbook status: ready.",
        "Archive SHA256",
        "Source snapshot commit",
        "Required Receipts",
        "Evidence comparison",
        "Local Preflight",
        "Archive Upload",
        "Source Repository Publish",
        "External CI",
        "External GPU Container",
        "Receipt Registry Update",
        "Final Gate",
        "docs/external_validation_receipts.json",
        "docs/external_validation_receipt_template.md",
        "make check",
        "make container-check",
        "scripts/build_external_validation_receipt_template.py",
        "scripts/update_external_validation_receipts.py --require-all",
        "git push -u origin main",
        "make gpu-container-env-check",
        "scripts/build_external_gpu_container_receipt.py",
        "runs/external_gpu_container_receipt.json",
        "scripts/audit_external_validation_readiness.py --strict",
        "This file is generated by `scripts/build_external_validation_runbook.py`.",
    ]:
        if phrase not in doc_text:
            fail(f"external validation runbook markdown missing phrase: {phrase}")
    if readiness_stale:
        for phrase in ["Stale Receipt Replacement", "Do not carry these values forward"]:
            if phrase not in doc_text:
                fail(f"external validation runbook markdown missing stale phrase: {phrase}")


def require_submission_handoff() -> None:
    payload = load_json(ROOT / "runs" / "submission_handoff.json")
    if payload.get("submission_handoff_ready") is not True:
        fail(f"submission handoff should be ready: {payload.get('risk_flags')}")
    if payload.get("risk_flags") != []:
        fail(f"submission handoff has risk flags: {payload.get('risk_flags')}")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        fail("submission handoff missing metadata payload")
    if "Winning Tickets Are Not Posterior Modes" not in str(metadata.get("title", "")):
        fail("submission handoff title does not match paper title")
    if metadata.get("venue") != "TMLR (rolling)":
        fail(f"submission handoff should target TMLR (rolling): {metadata.get('venue')}")
    if metadata.get("venue_first_backup") != "ICLR 2027":
        fail("submission handoff should record ICLR 2027 as first venue backup")
    if metadata.get("venue_second_backup") != "AISTATS 2027":
        fail("submission handoff should record AISTATS 2027 as second venue backup")
    abstract_words = int(metadata.get("abstract_words", 0))
    if abstract_words <= 0 or abstract_words > 250:
        fail(f"submission handoff abstract word count invalid: {abstract_words}")
    venue = payload.get("venue_audit", {})
    if venue.get("venue_strategy_matrix_ready") is not True:
        fail("submission handoff venue strategy matrix should be ready")
    if venue.get("venue_strategy_primary_target") != "TMLR (rolling)":
        fail("submission handoff venue strategy primary target should be TMLR (rolling)")
    if venue.get("venue_strategy_first_backup") != "ICLR 2027":
        fail("submission handoff venue strategy first backup should be ICLR 2027")
    if venue.get("provisional_strategy_ready") is not True:
        fail("submission handoff ICLR provisional strategy should be ready")
    if venue.get("iclr_submission_ready") is not False:
        fail("submission handoff must not claim final ICLR submission readiness yet")
    open_iclr_risks = venue.get("open_iclr_risk_flags", [])
    handoff_expected_flags = [
        "iclr_2027_official_cfp_not_observed",
        "formal_external_plagiarism_database_screen_not_performed",
    ]
    if not locked_final_test_observed():
        handoff_expected_flags.append("locked_final_test_metrics_not_observed")
    elif "locked_final_test_metrics_not_observed" in open_iclr_risks:
        fail("submission handoff should drop locked-final-test risk after the rerun is observed")
    for flag in handoff_expected_flags:
        if flag not in open_iclr_risks:
            fail(f"submission handoff missing open ICLR risk: {flag}")
    archive = load_json(ROOT / "runs" / "public_release_archive_audit.json")
    snapshot = load_json(ROOT / "runs" / "public_repository_snapshot_audit.json")
    paper_files = payload.get("paper_files", {})
    if paper_files.get("primary_submission_pdf") != "paper/iclr_submission.pdf":
        fail("submission handoff primary PDF should be the ICLR-style submission")
    if paper_files.get("alternate_neurips_pdf") != "paper/neurips_submission.pdf":
        fail("submission handoff should keep the NeurIPS PDF only as an alternate gate")
    supplement = payload.get("supplement_files", {})
    if supplement.get("artifact_archive_sha256") != archive.get("archive_sha256"):
        fail("submission handoff archive SHA256 does not match archive audit")
    if supplement.get("source_repository_snapshot_commit") != snapshot.get("git", {}).get("commit"):
        fail("submission handoff source commit does not match snapshot audit")
    if supplement.get("external_receipt_template") != "docs/external_validation_receipt_template.md":
        fail("submission handoff missing external receipt template reference")
    if supplement.get("ethics_statement_audit") != "docs/ethics_statement_audit.md":
        fail("submission handoff missing ethics statement audit reference")
    if supplement.get("llm_usage_disclosure_audit") != "docs/llm_usage_disclosure_audit.md":
        fail("submission handoff missing LLM usage disclosure audit reference")
    if supplement.get("iclr_policy_watch") != "docs/iclr_policy_watch_audit.md":
        fail("submission handoff missing ICLR policy watch reference")
    if supplement.get("iclr_policy_source_probe") != "docs/iclr_policy_source_probe.md":
        fail("submission handoff missing ICLR policy source probe reference")
    if supplement.get("iclr_openreview_packet") != "docs/iclr_openreview_packet.md":
        fail("submission handoff missing ICLR OpenReview packet reference")
    if supplement.get("iclr_human_confirmation_template") != "docs/iclr_human_confirmation_template.md":
        fail("submission handoff missing ICLR human confirmation template reference")
    if supplement.get("venue_strategy_matrix") != "docs/venue_strategy_matrix.md":
        fail("submission handoff missing venue strategy matrix reference")
    commands = payload.get("check_commands", [])
    for command in [
        "make check",
        "make paper-iclr-check",
        "make container-check",
        "make external-validation-readiness",
    ]:
        if command not in commands:
            fail(f"submission handoff missing local check command: {command}")
    doc_text = (ROOT / "docs" / "submission_handoff.md").read_text(encoding="utf-8")
    for phrase in [
        "Submission Handoff",
        "Handoff status: ready.",
        "Submission Metadata",
        "Winning Tickets Are Not Posterior Modes",
        "Venue: TMLR (rolling)",
        "Venue backups: ICLR 2027, AISTATS 2027",
        "Final ICLR submission status: False.",
        "Provisional ICLR strategy status: True.",
        "Venue Metrics",
        "Venue strategy matrix ready",
        "Files To Upload Or Reference",
        "paper/iclr_submission.pdf",
        "paper/neurips_submission.pdf",
        "dist/lottery_artifact_public_release_2026-05-06.tar.gz",
        "docs/external_validation_receipt_template.md",
        "docs/ethics_statement_audit.md",
        "docs/llm_usage_disclosure_audit.md",
        "docs/iclr_policy_watch_audit.md",
        "docs/iclr_openreview_packet.md",
        "docs/iclr_human_confirmation_template.md",
        "docs/venue_strategy_matrix.md",
        "scripts/update_external_validation_receipts.py",
        "Local Checks",
        "Final External Gate",
        "Release Blockers",
        "Open ICLR Risks",
        "iclr_2027_official_cfp_not_observed",
        "This file is generated by `scripts/build_submission_handoff.py`.",
    ]:
        if phrase not in doc_text:
            fail(f"submission handoff markdown missing phrase: {phrase}")


def main(*, release_package_mode: bool = False) -> None:
    required_files = [
        ("proposal_A3_lottery_ticket_bayesian_modes.md", 1000),
        ("README.md", 1000),
        ("Makefile", 100),
        (".dockerignore", 20),
        (".gitignore", 20),
        ("Dockerfile", 500),
        ("Dockerfile.gpu", 500),
        ("LICENSE", 500),
        ("requirements.txt", 20),
        ("requirements-ci.txt", 20),
        ("requirements-gpu-lock.txt", 50),
        ("requirements-lock.txt", 50),
        ("docs/container_lock.md", 1000),
        ("docs/gpu_training_container.md", 1000),
        ("docs/local_gpu_container_validation.md", 500),
        ("docs/compute_resource_accounting.md", 1000),
        ("docs/asset_license_inventory.md", 1000),
        ("docs/new_asset_inventory.md", 1000),
        ("docs/cifar10_resnet20_full_covariance_feasibility.md", 1000),
        ("docs/digits_fullnet_laplace_tiny_r2_p0p3.md", 500),
        ("docs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke.md", 500),
        ("docs/linear_connectivity_barrier_audit.md", 500),
        ("docs/posterior_covariance_robustness_audit.md", 500),
        (
            "docs/cifar10_resnet20_long30_rewind1_lowrank_laplace_movement_selected_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_lowrank32_laplace_movement_selected_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_lowrank64_laplace_movement_selected_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_lowrank128_laplace_movement_selected_r5_p0p3.md",
            800,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_selected_r5_p0p3.md",
            800,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_max10k_selected_r5_p0p3.md",
            800,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max10k_selected_r5_p0p3.md",
            800,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max20k_selected_r5_p0p3.md",
            800,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max40k_stream_selected_r5_p0p3.md",
            800,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_hessian32_subspace_hmc_selected_r5_p0p3.md",
            800,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_hard_concrete_selected_r5_p0p3.md",
            500,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_weight_aligned_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_independent_multichain_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_r5_p0p3.md",
            1000,
        ),
        ("docs/fake_cifar10_mode_ticket_mask_artifact_smoke.md", 1000),
        ("docs/fake_cifar10_mode_ticket_mask_artifact_posthoc_audit.md", 1000),
        ("docs/mode_ticket_artifact_storage_budget.md", 1000),
        (
            "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_global_channel_audit.md",
            1000,
        ),
        ("docs/direct_mode_ticket_seed_level_audit.md", 1000),
        ("docs/batchnorm_posterior_policy_audit.md", 1000),
        ("docs/validation_test_usage_policy_audit.md", 1000),
        ("docs/validation_bn_rerun_plan.md", 1000),
        ("docs/remaining_experiment_queue.md", 1000),
        ("docs/remaining_experiment_preflight_audit.md", 1000),
        ("docs/locked_final_test_protocol_audit.md", 1000),
        ("docs/validation_bn_smoke_audit.md", 1000),
        ("docs/fake_cifar10_validation_bn_policy_smoke.md", 1000),
        ("docs/resnet_channel_permutation_exhaustive_feasibility_audit.md", 1000),
        ("docs/cifar10_subset_hard_concrete_mask_training_smoke.md", 500),
        ("docs/environment_snapshot.md", 500),
        ("docs/environment_lock.json", 200),
        ("docs/mode_ticket_alignment_artifact_audit.md", 1000),
        ("docs/reproducibility_manifest.md", 1000),
        ("docs/public_release_manifest.md", 1000),
        ("docs/release_anonymization_audit.md", 500),
        ("docs/paper_claim_ledger.md", 1000),
        ("docs/paper_submission_shape_audit.md", 1000),
        ("docs/submission_pdf_shape_audit.md", 500),
        ("docs/venue_submission_compliance_audit.md", 500),
        ("docs/reviewer_objection_matrix.md", 1000),
        ("docs/unit_smoke_tests.md", 500),
        ("docs/submission_readiness_audit.md", 1000),
        ("docs/thread_goal_completion_audit.md", 1000),
        ("docs/paper_stats.md", 1000),
        ("docs/paper_asset_freshness_audit.md", 700),
        ("runs/mode_ticket_alignment_artifact_audit.json", 1000),
        ("runs/fake_cifar10_mode_ticket_mask_artifact_posthoc_audit.json", 1000),
        ("runs/mode_ticket_artifact_storage_budget.json", 1000),
        (
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_posthoc_audit.json",
            10000,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_global_channel_audit.json",
            20000,
        ),
        ("runs/direct_mode_ticket_seed_level_audit.json", 1000),
        ("runs/batchnorm_posterior_policy_audit.json", 1000),
        ("runs/validation_test_usage_policy_audit.json", 1000),
        ("runs/validation_bn_rerun_plan.json", 1000),
        ("runs/remaining_experiment_queue.json", 1000),
        ("runs/remaining_experiment_preflight_audit.json", 1000),
        ("runs/locked_final_test_protocol_audit.json", 1000),
        ("runs/validation_bn_smoke_audit.json", 1000),
        ("runs/unit_smoke_tests.json", 500),
        ("runs/fake_cifar10_validation_bn_policy_smoke_summary.csv", 100),
        (
            "runs/fake_cifar10_validation_bn_policy_smoke/20260513_145944/metrics.json",
            1000,
        ),
        (
            "runs/fake_cifar10_validation_bn_policy_smoke/20260513_145944/mask_artifacts.npz",
            1000,
        ),
        ("runs/resnet_channel_permutation_exhaustive_feasibility_audit.json", 5000),
        ("runs/paper_submission_shape_audit.json", 1000),
        ("runs/submission_pdf_shape_audit.json", 250),
        ("runs/venue_submission_compliance_audit.json", 500),
        ("runs/local_gpu_container_validation.json", 500),
        ("runs/reviewer_objection_matrix.json", 1000),
        ("runs/paper_stats.json", 1000),
        ("runs/paper_asset_freshness_audit.json", 500),
        ("runs/cifar10_resnet20_full_covariance_feasibility.json", 1000),
        ("runs/digits_fullnet_laplace_tiny_r2_p0p3_summary.csv", 500),
        ("runs/fake_cifar10_resnet20_w1_fullnet_laplace_smoke_summary.csv", 500),
        ("runs/linear_connectivity_barrier_audit.csv", 500),
        ("runs/linear_connectivity_barrier_audit.json", 500),
        ("runs/posterior_covariance_robustness_audit.csv", 500),
        ("runs/posterior_covariance_robustness_audit.json", 1000),
        (
            "runs/cifar10_resnet20_long30_rewind1_lowrank_laplace_movement_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_residual_imp_process_stratified_exclusion_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_residual_imp_process_projection_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_residual_imp_process_posterior_projection_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_residual_imp_process_learned_subspace_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_lowrank32_laplace_movement_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_lowrank64_laplace_movement_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_lowrank128_laplace_movement_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_blockdiag_laplace_max10k_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max10k_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max20k_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_jointdiag_laplace_max40k_stream_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_hessian32_subspace_hmc_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_hard_concrete_selected_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_weight_aligned_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_csgld_independent_multichain_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_lowrank128_laplace_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_jointdiag_laplace_max40k_stream_r5_p0p3_summary.csv",
            100,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3_summary.csv",
            1000,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3/20260506_230706/metrics.json",
            50000,
        ),
        (
            "runs/cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3/20260506_230706/mask_artifacts.npz",
            100_000_000,
        ),
        ("runs/fake_cifar10_mode_ticket_mask_artifact_smoke_summary.csv", 100),
        ("runs/cifar10_subset_hard_concrete_mask_training_smoke_summary.csv", 100),
        ("runs/public_release_manifest.json", 1000),
        ("runs/release_anonymization_audit.json", 300),
        ("scripts/audit_release_anonymization.py", 1000),
        ("scripts/audit_external_validation_readiness.py", 1000),
        ("scripts/audit_external_validation_claims.py", 1000),
        ("scripts/build_external_validation_receipt_template.py", 1000),
        ("scripts/update_external_validation_receipts.py", 1000),
        ("scripts/build_external_validation_runbook.py", 1000),
        ("scripts/build_external_gpu_container_receipt.py", 1000),
        ("scripts/build_submission_handoff.py", 1000),
        ("scripts/stage_public_repository_snapshot.py", 1000),
        ("scripts/smoke_public_repository_snapshot.py", 1000),
        ("scripts/verify_source_repository_snapshot.py", 1000),
        ("scripts/build_public_release_archive.py", 1000),
        ("scripts/smoke_public_release_archive.py", 1000),
        ("scripts/audit_paper_asset_freshness.py", 1000),
        ("scripts/audit_posterior_covariance_robustness.py", 1000),
        ("scripts/audit_direct_mode_ticket_seed_level_artifacts.py", 1000),
        ("scripts/audit_batchnorm_posterior_policy.py", 1000),
        ("scripts/audit_validation_test_usage_policy.py", 1000),
        ("scripts/build_validation_bn_rerun_plan.py", 1000),
        ("scripts/build_remaining_experiment_queue.py", 1000),
        ("scripts/audit_remaining_experiment_preflight.py", 1000),
        ("scripts/audit_open_blocker_claim_scope.py", 1000),
        ("scripts/audit_locked_final_test_protocol.py", 1000),
        ("scripts/audit_validation_bn_smoke.py", 1000),
        ("scripts/audit_reference_integrity.py", 1000),
        ("scripts/audit_manuscript_originality.py", 1000),
        ("scripts/build_formal_plagiarism_screening_runbook.py", 1000),
        ("scripts/audit_formal_plagiarism_screening_receipt.py", 1000),
        ("scripts/audit_ethics_statement.py", 1000),
        ("scripts/audit_llm_usage_disclosure.py", 1000),
        ("scripts/build_iclr_policy_watch_audit.py", 1000),
        ("scripts/build_iclr_openreview_packet.py", 1000),
        ("scripts/build_iclr_human_confirmation_template.py", 1000),
        ("scripts/audit_iclr_human_confirmation_receipt.py", 1000),
        ("scripts/audit_iclr_submission_readiness.py", 1000),
        ("scripts/build_venue_strategy_matrix.py", 1000),
        (
            "docs/cifar10_resnet20_long30_rewind1_residual_imp_process_stratified_exclusion_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_residual_imp_process_projection_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_residual_imp_process_posterior_projection_r5_p0p3.md",
            1000,
        ),
        (
            "docs/cifar10_resnet20_long30_rewind1_residual_imp_process_learned_subspace_r5_p0p3.md",
            1000,
        ),
        ("paper/main.tex", 1000),
        ("paper/refs.bib", 1000),
        ("docs/reference_integrity_audit.md", 700),
        ("runs/reference_integrity_audit.json", 700),
        ("docs/manuscript_originality_audit.md", 700),
        ("runs/manuscript_originality_audit.json", 500),
        ("docs/formal_plagiarism_screening_runbook.md", 700),
        ("runs/formal_plagiarism_screening_runbook.json", 500),
        ("docs/formal_plagiarism_screening_receipt_audit.md", 700),
        ("runs/formal_plagiarism_screening_receipt_audit.json", 500),
        ("docs/ethics_statement_audit.md", 700),
        ("runs/ethics_statement_audit.json", 500),
        ("docs/llm_usage_disclosure_audit.md", 700),
        ("runs/llm_usage_disclosure_audit.json", 500),
        ("docs/iclr_policy_watch_audit.md", 700),
        ("runs/iclr_policy_watch_audit.json", 500),
        ("docs/iclr_policy_source_probe.md", 500),
        ("runs/iclr_policy_source_probe.json", 500),
        ("docs/iclr_openreview_packet.md", 700),
        ("runs/iclr_openreview_packet.json", 500),
        ("docs/iclr_human_confirmation_template.md", 700),
        ("runs/iclr_human_confirmation_template.json", 500),
        ("docs/iclr_human_confirmation_receipt_audit.md", 700),
        ("runs/iclr_human_confirmation_receipt_audit.json", 500),
        ("docs/venue_strategy_matrix.md", 1000),
        ("runs/venue_strategy_matrix.json", 1000),
        ("paper/main.pdf", 200_000),
        ("paper/main_submission.pdf", 100_000),
        ("paper/neurips_2026.sty", 1000),
        ("paper/neurips_checklist.tex", 1000),
        ("paper/neurips_submission.pdf", 100_000),
        ("paper/iclr2026_conference.sty", 1000),
        ("paper/iclr2026_conference.bst", 1000),
        ("paper/iclr_submission.pdf", 100_000),
        ("paper/tables/statistical_summary.tex", 1000),
    ]
    if not release_package_mode:
        required_files.extend(
            [
                ("runs/iclr_submission_readiness_audit.json", 1000),
                ("docs/iclr_submission_readiness_audit.md", 1000),
                ("docs/open_blocker_claim_scope_audit.md", 1000),
                ("runs/open_blocker_claim_scope_audit.json", 1000),
                ("docs/public_release_archive_audit.md", 500),
                ("docs/public_release_archive_smoke.md", 500),
                ("runs/public_release_archive_audit.json", 300),
                ("runs/public_release_archive_smoke.json", 300),
                ("docs/public_repository_snapshot_audit.md", 500),
                ("runs/public_repository_snapshot_audit.json", 500),
                ("docs/public_repository_snapshot_smoke.md", 500),
                ("runs/public_repository_snapshot_smoke.json", 500),
                ("docs/external_validation_receipts.json", 500),
                ("docs/external_validation_readiness_audit.md", 500),
                ("runs/external_validation_readiness_audit.json", 500),
                ("docs/external_validation_receipt_template.md", 500),
                ("runs/external_validation_receipt_template.json", 500),
                ("docs/external_validation_runbook.md", 500),
                ("runs/external_validation_runbook.json", 500),
                ("docs/external_validation_claim_audit.md", 500),
                ("runs/external_validation_claim_audit.json", 500),
                ("docs/submission_handoff.md", 500),
                ("runs/submission_handoff.json", 500),
                ("docs/proposal_to_artifact_audit.md", 500),
                ("runs/proposal_to_artifact_audit_2026-05-12.json", 500),
                ("scripts/build_proposal_to_artifact_audit.py", 1000),
                (
                    "dist/lottery_artifact_public_release_2026-05-06.tar.gz",
                    100_000_000,
                ),
                (
                    "dist/lottery_artifact_public_release_2026-05-06.tar.gz.sha256",
                    50,
                ),
            ]
        )
    for path, min_size in required_files:
        require_file(path, min_size)
    stats = load_json(ROOT / "runs" / "paper_stats.json")
    require_stats_sections(stats)
    require_paper_asset_freshness_audit()
    require_gate1(stats)
    require_movement(stats)
    require_block_laplace(stats)
    require_subspace_hmc(stats)
    require_mode_distribution_audit(stats)
    require_direct_mode_ticket(stats)
    require_direct_mode_ticket_seed_level_audit()
    require_batchnorm_posterior_policy_audit()
    require_unit_smoke_tests()
    require_validation_test_usage_policy_audit()
    require_validation_bn_rerun_plan()
    require_validation_bn_rerun_runner()
    require_remaining_experiment_queue()
    require_remaining_experiment_preflight_audit()
    if not release_package_mode:
        # The open-blocker claim-scope audit aggregates mutable post-release
        # receipt state and is intentionally excluded from the archive.
        require_open_blocker_claim_scope_audit()
    require_locked_final_test_preflight_receipt()
    require_locked_final_test_protocol_audit()
    require_validation_bn_smoke_audit()
    require_mode_ticket_alignment_artifact_audit()
    require_mode_ticket_mask_artifact_smoke()
    require_mask_artifact_posthoc_audit()
    require_mode_ticket_artifact_storage_budget()
    require_full_data_saved_artifact_posthoc_audit()
    require_full_data_global_channel_permutation_audit()
    require_exhaustive_channel_permutation_feasibility_audit()
    require_digits_fullnet_laplace_probe()
    require_fake_resnet_fullnet_laplace_smoke()
    require_linear_connectivity_barrier_audit()
    require_calibration_and_learned_masks(stats)
    require_residual_process(stats)
    require_text_evidence()
    require_bibliography()
    require_reference_integrity_audit()
    require_manuscript_originality_audit()
    require_formal_plagiarism_screening_runbook()
    require_formal_plagiarism_screening_receipt_audit()
    require_ethics_statement_audit()
    require_llm_usage_disclosure_audit()
    require_iclr_policy_watch_audit()
    require_iclr_openreview_packet()
    require_iclr_human_confirmation_template()
    require_iclr_human_confirmation_receipt_audit()
    require_venue_strategy_matrix()
    require_paper_numeric_claims(stats)
    require_environment_lock()
    require_full_covariance_feasibility()
    require_posterior_covariance_robustness_audit()
    require_container_lock()
    require_claim_ledger()
    require_reviewer_objection_matrix()
    require_paper_submission_shape_audit()
    require_submission_pdf_shape_audit()
    require_venue_submission_compliance_audit()
    if not release_package_mode:
        # Same rationale: the ICLR readiness aggregate clears flags when
        # receipts are recorded, so it is excluded from the archive.
        require_iclr_submission_readiness_audit()
    require_release_metadata_docs()
    require_release_manifest()
    require_release_anonymization_audit()
    if not release_package_mode:
        require_public_release_archive()
        require_public_release_archive_smoke()
        require_public_repository_snapshot_audit()
        require_public_repository_snapshot_smoke()
        require_external_validation_readiness_audit()
        require_external_validation_claim_audit()
        require_external_validation_receipt_template()
        require_external_validation_runbook()
        require_submission_handoff()
        require_proposal_to_artifact_audit()
        require_top_conference_completion_audit()
        require_paper_pdf_freshness_audit()
        require_tmlr_packet_freshness_audit()
    print("verified research artifacts: core paper evidence and generated stats are present")


if __name__ == "__main__":
    try:
        main(release_package_mode=parse_args().release_package_mode)
    except AssertionError as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
