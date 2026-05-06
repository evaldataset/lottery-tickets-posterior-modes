#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = (
    ROOT
    / "runs"
    / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3"
    / "20260506_230706"
    / "mask_artifacts.npz"
)
DEFAULT_PAPER_STATS = ROOT / "runs" / "paper_stats.json"
DEFAULT_OUT_JSON = ROOT / "runs" / "direct_mode_ticket_seed_level_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "direct_mode_ticket_seed_level_audit.md"

T_CRIT_95 = {
    2: 12.706,
    3: 4.303,
    4: 3.182,
    5: 2.776,
    6: 2.571,
    7: 2.447,
    8: 2.365,
    9: 2.306,
    10: 2.262,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--paper-stats", type=Path, default=DEFAULT_PAPER_STATS)
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


def seed_from_id(identifier: Any) -> int:
    match = re.search(r"seed_(\d+)", str(identifier))
    if match is None:
        raise ValueError(f"could not parse seed from id: {identifier}")
    return int(match.group(1))


def ci95(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    if len(arr) < 2:
        return {"mean": mean, "ci95_low": math.nan, "ci95_high": math.nan}
    tcrit = T_CRIT_95.get(len(arr), 1.96)
    half = float(tcrit * arr.std(ddof=1) / math.sqrt(len(arr)))
    return {"mean": mean, "ci95_low": mean - half, "ci95_high": mean + half}


def two_sided_sign_p(nonzero_count: int, same_direction_count: int) -> float:
    if nonzero_count <= 0:
        return math.nan
    tail = min(same_direction_count, nonzero_count - same_direction_count)
    probability = sum(math.comb(nonzero_count, k) for k in range(tail + 1)) / (2**nonzero_count)
    return float(min(1.0, 2.0 * probability))


def summarize_deltas(values: list[float]) -> dict[str, Any]:
    positive = sum(value > 0.0 for value in values)
    negative = sum(value < 0.0 for value in values)
    zero = len(values) - positive - negative
    nonzero = positive + negative
    same_direction = max(positive, negative)
    out: dict[str, Any] = {
        "n": len(values),
        "positive": positive,
        "negative": negative,
        "zero": zero,
        "two_sided_sign_p": two_sided_sign_p(nonzero, same_direction),
    }
    out.update(ci95(values))
    return out


def hamming(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.count_nonzero(a != b) / a.size)


def layer_keep_profile(
    mask: np.ndarray, offsets: np.ndarray, sizes: np.ndarray
) -> np.ndarray:
    values = []
    for offset, size in zip(offsets.tolist(), sizes.tolist()):
        chunk = mask[int(offset) : int(offset) + int(size)]
        values.append(float(chunk.mean()))
    return np.asarray(values, dtype=float)


def index_by_seed(ids: np.ndarray, masks: np.ndarray) -> dict[int, np.ndarray]:
    by_seed: dict[int, np.ndarray] = {}
    for identifier, mask in zip(ids, masks):
        by_seed[seed_from_id(identifier)] = mask
    return by_seed


def sample_indices_by_seed(ids: np.ndarray) -> dict[int, list[int]]:
    by_seed: dict[int, list[int]] = {}
    for index, identifier in enumerate(ids):
        by_seed.setdefault(seed_from_id(identifier), []).append(index)
    return by_seed


def analyze_variant(
    artifact: np.lib.npyio.NpzFile, *, prefix: str, label: str
) -> dict[str, Any]:
    posterior_ids = artifact[f"ids__{prefix}posterior_sample"]
    posterior_masks = artifact[f"masks__{prefix}posterior_sample"]
    chain_starts = index_by_seed(
        artifact[f"ids__{prefix}chain_start"],
        artifact[f"masks__{prefix}chain_start"],
    )
    tickets = index_by_seed(
        artifact[f"ids__{prefix}ticket"],
        artifact[f"masks__{prefix}ticket"],
    )
    sample_by_seed = sample_indices_by_seed(posterior_ids)
    offsets = artifact["parameter_offsets"]
    sizes = artifact["parameter_sizes"]

    rows: list[dict[str, Any]] = []
    hamming_deltas: list[float] = []
    layer_gap_deltas: list[float] = []
    posterior_hamming_values: list[float] = []
    chain_hamming_values: list[float] = []

    for seed in sorted(tickets):
        sample_indices = sample_by_seed.get(seed, [])
        if not sample_indices:
            raise ValueError(f"no posterior samples for seed {seed} in {label}")
        ticket = tickets[seed]
        chain = chain_starts[seed]
        posterior_to_ticket = [
            hamming(posterior_masks[index], ticket) for index in sample_indices
        ]
        posterior_hamming = float(np.mean(posterior_to_ticket))
        chain_hamming = hamming(chain, ticket)
        posterior_profile = np.mean(
            [
                layer_keep_profile(posterior_masks[index], offsets, sizes)
                for index in sample_indices
            ],
            axis=0,
        )
        ticket_profile = layer_keep_profile(ticket, offsets, sizes)
        chain_profile = layer_keep_profile(chain, offsets, sizes)
        posterior_layer_gap = float(np.mean(np.abs(posterior_profile - ticket_profile)))
        chain_layer_gap = float(np.mean(np.abs(chain_profile - ticket_profile)))
        hamming_delta = posterior_hamming - chain_hamming
        layer_gap_delta = posterior_layer_gap - chain_layer_gap
        posterior_hamming_values.append(posterior_hamming)
        chain_hamming_values.append(chain_hamming)
        hamming_deltas.append(hamming_delta)
        layer_gap_deltas.append(layer_gap_delta)
        rows.append(
            {
                "seed": seed,
                "posterior_sample_count": len(sample_indices),
                "posterior_to_own_ticket_hamming_mean": posterior_hamming,
                "chain_start_to_own_ticket_hamming": chain_hamming,
                "posterior_minus_chain_hamming": hamming_delta,
                "posterior_layer_keep_gap_to_ticket": posterior_layer_gap,
                "chain_layer_keep_gap_to_ticket": chain_layer_gap,
                "posterior_minus_chain_layer_keep_gap": layer_gap_delta,
            }
        )

    hamming_summary = summarize_deltas(hamming_deltas)
    layer_gap_summary = summarize_deltas(layer_gap_deltas)
    return {
        "label": label,
        "mask_prefix": prefix,
        "seed_count": len(rows),
        "sample_count": int(sum(row["posterior_sample_count"] for row in rows)),
        "posterior_to_own_ticket_hamming": ci95(posterior_hamming_values),
        "chain_start_to_own_ticket_hamming": ci95(chain_hamming_values),
        "posterior_minus_chain_hamming": hamming_summary,
        "posterior_minus_chain_layer_keep_gap": layer_gap_summary,
        "posterior_not_closer_than_chain_in_all_seeds": (
            hamming_summary["positive"] == len(rows) and hamming_summary["negative"] == 0
        ),
        "rows": rows,
    }


def direct_rows_without_saved_masks(paper_stats: Path, artifact_run: str) -> list[str]:
    if not paper_stats.exists():
        return []
    stats = load_json(paper_stats)
    rows = stats.get("direct_mode_ticket_distribution", [])
    missing = []
    for row in rows:
        if row.get("comparison") != "posterior_samples_vs_tickets":
            continue
        run = str(row.get("run", ""))
        if run == artifact_run:
            continue
        missing.append(f"{row.get('setting')}::{row.get('comparison')}")
    return missing


def build_audit(artifact_path: Path, paper_stats: Path) -> dict[str, Any]:
    if not artifact_path.exists():
        return {
            "direct_seed_level_audit_ready": False,
            "artifact": relpath(artifact_path),
            "risk_flags": ["mask_artifact_missing"],
        }
    artifact = np.load(artifact_path, allow_pickle=False)
    metadata = json.loads(str(artifact["metadata_json"]))
    artifact_run = artifact_path.parent.as_posix()
    try:
        artifact_run = artifact_path.parent.relative_to(ROOT).as_posix()
    except ValueError:
        pass
    variants = [
        analyze_variant(artifact, prefix="", label="raw_saved_artifact"),
        analyze_variant(
            artifact,
            prefix="activation_aligned_",
            label="activation_aligned_saved_artifact",
        ),
    ]
    direct_missing = direct_rows_without_saved_masks(paper_stats, artifact_run)
    risk_flags: list[str] = []
    open_risk_flags: list[str] = []
    if any(variant["seed_count"] != 5 for variant in variants):
        risk_flags.append("seed_count_not_five")
    if any(
        not variant["posterior_not_closer_than_chain_in_all_seeds"]
        for variant in variants
    ):
        risk_flags.append("posterior_closer_than_chain_for_some_seed")
    if direct_missing:
        # Surface direct rows without saved-mask coverage as an open risk so the
        # paper's "can be applied" wording is not silently mis-read as
        # "has been applied". The blocking risk_flags stays scoped to the
        # covered SGLD artifact's actual integrity.
        open_risk_flags.append("direct_rows_missing_saved_masks")

    return {
        "direct_seed_level_audit_ready": not risk_flags,
        "artifact": relpath(artifact_path),
        "paper_stats": relpath(paper_stats),
        "artifact_metadata": metadata,
        "variants": variants,
        "interpretation_checks": {
            "seed_level_artifact_available_for_saved_full_data_sgld": True,
            "pooled_direct_distribution_pvalues_are_descriptive": True,
            "raw_posterior_not_closer_than_chain_in_5_of_5_seeds": variants[0][
                "posterior_not_closer_than_chain_in_all_seeds"
            ],
            "activation_aligned_posterior_not_closer_than_chain_in_5_of_5_seeds": variants[
                1
            ]["posterior_not_closer_than_chain_in_all_seeds"],
            "other_direct_rows_require_saved_masks_for_seed_level_reanalysis": bool(
                direct_missing
            ),
        },
        "direct_rows_without_saved_masks": direct_missing,
        "risk_flags": risk_flags,
        "open_risk_flags": open_risk_flags,
    }


def fmt(value: Any, digits: int = 4) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(number):
        return "n/a"
    if abs(number) < 0.001 and number != 0.0:
        return f"{number:.2e}"
    return f"{number:.{digits}f}"


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["direct_seed_level_audit_ready"] else "not ready"
    lines = [
        "# Direct Mode/Ticket Seed-Level Artifact Audit",
        "",
        "This generated audit addresses a statistical reliability risk in the",
        "proposal-level direct mode/ticket distribution rows. Pooled layer-KS",
        "p-values over posterior samples are treated as descriptive diagnostics;",
        "the seed-level paired result below uses saved full-data mask artifacts",
        "and compares posterior samples to the matching seed's IMP ticket.",
        "",
        f"Current status: {status}.",
        "",
        "## Scope",
        "",
        f"- Artifact: `{payload.get('artifact')}`",
        "- Covered row: full-data CIFAR-10 ResNet-20 saved SGLD mask artifact.",
        "- Primary paired metric: mean Hamming distance from posterior samples",
        "  to the same seed's IMP ticket minus the chain-start-to-ticket Hamming",
        "  distance. Positive values mean posterior samples are farther from the",
        "  matching IMP ticket than the chain-start magnitude support.",
        "- Pooled direct distribution p-values remain descriptive unless the raw",
        "  masks/states are saved for seed-level reconstruction.",
        "",
        "## Variant Summary",
        "",
        "| Variant | Seeds | Samples | Posterior Hamming | Chain Hamming | Posterior-Chain Hamming | + | - | sign p | Layer-gap delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant in payload.get("variants", []):
        hamming_delta = variant["posterior_minus_chain_hamming"]
        layer_delta = variant["posterior_minus_chain_layer_keep_gap"]
        lines.append(
            f"| {variant['label']} | {variant['seed_count']} | "
            f"{variant['sample_count']} | "
            f"{fmt(variant['posterior_to_own_ticket_hamming']['mean'])} | "
            f"{fmt(variant['chain_start_to_own_ticket_hamming']['mean'])} | "
            f"{fmt(hamming_delta['mean'])} "
            f"[{fmt(hamming_delta['ci95_low'])}, {fmt(hamming_delta['ci95_high'])}] | "
            f"{hamming_delta['positive']} | {hamming_delta['negative']} | "
            f"{fmt(hamming_delta['two_sided_sign_p'])} | "
            f"{fmt(layer_delta['mean'])} |"
        )
    lines.extend(["", "## Seed Rows", ""])
    for variant in payload.get("variants", []):
        lines.extend(
            [
                f"### {variant['label']}",
                "",
                "| Seed | Samples | Posterior Hamming | Chain Hamming | Delta | Posterior layer gap | Chain layer gap | Layer delta |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in variant["rows"]:
            lines.append(
                f"| {row['seed']} | {row['posterior_sample_count']} | "
                f"{fmt(row['posterior_to_own_ticket_hamming_mean'])} | "
                f"{fmt(row['chain_start_to_own_ticket_hamming'])} | "
                f"{fmt(row['posterior_minus_chain_hamming'])} | "
                f"{fmt(row['posterior_layer_keep_gap_to_ticket'])} | "
                f"{fmt(row['chain_layer_keep_gap_to_ticket'])} | "
                f"{fmt(row['posterior_minus_chain_layer_keep_gap'])} |"
            )
        lines.append("")

    missing = payload.get("direct_rows_without_saved_masks", [])
    lines.extend(["## Direct Rows Still Requiring Saved Masks", ""])
    if missing:
        lines.extend(f"- {row}" for row in missing)
    else:
        lines.append("- none")
    lines.extend(["", "## Risk Flags", ""])
    if payload.get("risk_flags"):
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This file is generated by `scripts/audit_direct_mode_ticket_seed_level_artifacts.py`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = build_audit(args.artifact, args.paper_stats)
    write_json(payload, args.out_json)
    write_markdown(payload, args.out_md)
    print(
        json.dumps(
            {
                "direct_seed_level_audit_ready": payload["direct_seed_level_audit_ready"],
                "risk_flags": payload["risk_flags"],
                "artifact": payload["artifact"],
                "out_json": relpath(args.out_json),
                "out_md": relpath(args.out_md),
            }
        )
    )


if __name__ == "__main__":
    main()
