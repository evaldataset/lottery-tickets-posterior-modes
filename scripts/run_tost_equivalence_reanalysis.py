#!/usr/bin/env python
"""TOST equivalence / non-superiority reanalysis of the support-gap claims.

The paper's tracking claim ("posterior-minus-chain-start gaps stay near
zero") is an absence-of-evidence statement when reported only as a failed
difference test. The statistically correct frame for that claim is
equivalence testing. This script reanalyses existing seed-level summaries
with two pre-specified procedures, both using the paper's own materiality
margin delta = 0.005 Jaccard (the threshold already used by the grouped
mode-distribution audit):

1. TOST equivalence on the Gate1 sparsity sweeps (per-seed CSVs): the
   posterior-to-IMP minus chain-start-to-IMP Jaccard gap must lie within
   (-delta, +delta) by two one-sided t-tests at alpha = 0.05, df = n-1.
2. One-sided non-superiority on the CIFAR movement rows (mean/std CSVs):
   posterior support must not beat the chain-start control by more than
   delta. Movement rows where samples move *away* from the chain start
   are expected to fail symmetric equivalence while passing
   non-superiority; that asymmetry is exactly the paper's claim.

Read-only: no rerun or GPU. Outputs runs/tost_equivalence_audit.json and
docs/tost_equivalence_audit.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "runs" / "tost_equivalence_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "tost_equivalence_audit.md"

DELTA = 0.005
ALPHA = 0.05

# One-sided 95% Student-t critical values by degrees of freedom.
T95_ONE_SIDED = {
    1: 6.314,
    2: 2.920,
    3: 2.353,
    4: 2.132,
    5: 2.015,
    6: 1.943,
    7: 1.895,
    8: 1.860,
    9: 1.833,
    10: 1.812,
}

GATE1_SOURCES = [
    ("MNIST r2 p0.30", "runs/mnist_gate1_full_r2_p0p3_summary.csv"),
    ("MNIST r3 p0.30", "runs/mnist_gate1_full_r3_p0p3_summary.csv"),
    ("MNIST r5 p0.30", "runs/mnist_gate1_full_r5_p0p3_summary.csv"),
    ("MNIST r8 p0.30", "runs/mnist_gate1_full_r8_p0p3_summary.csv"),
    ("Fashion r2 p0.30", "runs/fashion_gate1_full_r2_p0p3_summary.csv"),
    ("Fashion r3 p0.30", "runs/fashion_gate1_full_r3_p0p3_summary.csv"),
    ("Fashion r5 p0.30", "runs/fashion_gate1_full_r5_p0p3_summary.csv"),
    ("Fashion r8 p0.30", "runs/fashion_gate1_full_r8_p0p3_summary.csv"),
]

MOVEMENT_SOURCES = [
    ("SGLD", "runs/cifar10_resnet20_long30_rewind1_sgld_movement_selected_r5_p0p3_summary.csv"),
    ("SGHMC", "runs/cifar10_resnet20_long30_rewind1_sghmc_movement_selected_r5_p0p3_summary.csv"),
    ("cSGLD", "runs/cifar10_resnet20_long30_rewind1_csgld_movement_selected_r5_p0p3_summary.csv"),
    ("DiagLap", "runs/cifar10_resnet20_long30_rewind1_diag_laplace_movement_selected_r5_p0p3_summary.csv"),
    ("KFACLap", "runs/cifar10_resnet20_long30_rewind1_kfac_laplace_movement_selected_r5_p0p3_summary.csv"),
    ("LowRank16Lap", "runs/cifar10_resnet20_long30_rewind1_lowrank_laplace_movement_selected_r5_p0p3_summary.csv"),
    ("LowRank32Lap", "runs/cifar10_resnet20_long30_rewind1_lowrank32_laplace_movement_selected_r5_p0p3_summary.csv"),
    ("LowRank64Lap", "runs/cifar10_resnet20_long30_rewind1_lowrank64_laplace_movement_selected_r5_p0p3_summary.csv"),
    ("LowRank128Lap", "runs/cifar10_resnet20_long30_rewind1_lowrank128_laplace_movement_selected_r5_p0p3_summary.csv"),
    ("SWAG20", "runs/cifar10_resnet20_long30_rewind1_swag_movement_selected20_lr1e3_r5_p0p3_summary.csv"),
]


def t_critical(df: int) -> float:
    if df in T95_ONE_SIDED:
        return T95_ONE_SIDED[df]
    if df > max(T95_ONE_SIDED):
        return 1.645
    raise SystemExit(f"no one-sided t critical value for df={df}")


def mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var)


def tost_from_moments(mean: float, std: float, n: int, delta: float) -> dict:
    df = n - 1
    crit = t_critical(df)
    se = std / math.sqrt(n)
    if se == 0.0:
        equivalent = abs(mean) < delta
        return {
            "mean_gap": mean,
            "se": 0.0,
            "df": df,
            "t_lower": math.inf if mean > -delta else -math.inf,
            "t_upper": math.inf if mean < delta else -math.inf,
            "t_critical": crit,
            "equivalent_within_delta": equivalent,
            "non_superior_within_delta": mean < delta,
        }
    t_lower = (mean + delta) / se
    t_upper = (delta - mean) / se
    return {
        "mean_gap": mean,
        "se": se,
        "df": df,
        "t_lower": t_lower,
        "t_upper": t_upper,
        "t_critical": crit,
        "equivalent_within_delta": t_lower > crit and t_upper > crit,
        "non_superior_within_delta": t_upper > crit,
    }


def gate1_rows(delta: float) -> list[dict]:
    rows = []
    for label, rel in GATE1_SOURCES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"missing gate1 source: {rel}")
        with path.open() as fh:
            seed_rows = list(csv.DictReader(fh))
        gaps = [
            float(r["posterior_jaccard_mean"])
            - float(r["chain_start_magnitude_to_imp_jaccard_mean"])
            for r in seed_rows
        ]
        mean, std = mean_std(gaps)
        result = tost_from_moments(mean, std, len(gaps), delta)
        result.update({"label": label, "source": rel, "n_seeds": len(gaps)})
        rows.append(result)
    return rows


def movement_rows(delta: float) -> list[dict]:
    rows = []
    for label, rel in MOVEMENT_SOURCES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"missing movement source: {rel}")
        with path.open() as fh:
            csv_rows = list(csv.DictReader(fh))
        config_col = list(csv_rows[0].keys())[0]
        for r in csv_rows:
            mean = float(r["posterior_minus_chain_start_jaccard"])
            std = float(r["posterior_minus_chain_start_jaccard_std"])
            n = int(float(r["num_runs"]))
            result = tost_from_moments(mean, std, n, delta)
            result.update(
                {
                    "label": f"{label} {config_col}={r[config_col]}",
                    "sampler": label,
                    "source": rel,
                    "n_seeds": n,
                }
            )
            rows.append(result)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--delta", type=float, default=DELTA)
    args = parser.parse_args()

    gate1 = gate1_rows(args.delta)
    movement = movement_rows(args.delta)

    gate1_all_equivalent = all(r["equivalent_within_delta"] for r in gate1)
    movement_all_non_superior = all(r["non_superior_within_delta"] for r in movement)
    movement_equiv_count = sum(r["equivalent_within_delta"] for r in movement)

    audit = {
        "tost_equivalence_audit_ready": bool(
            gate1_all_equivalent and movement_all_non_superior
        ),
        "delta_jaccard": args.delta,
        "alpha_one_sided": ALPHA,
        "gate1_rows": gate1,
        "gate1_all_equivalent_within_delta": gate1_all_equivalent,
        "movement_rows": movement,
        "movement_all_non_superior": movement_all_non_superior,
        "movement_equivalent_count": movement_equiv_count,
        "movement_row_count": len(movement),
        "interpretation": {
            "gate1_tracking_claim_is_equivalence_tested": gate1_all_equivalent,
            "no_movement_row_beats_chain_start_by_delta": movement_all_non_superior,
            "movement_rows_moving_away_fail_symmetric_equivalence_by_design": (
                movement_equiv_count < len(movement)
            ),
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(audit, indent=2) + "\n")

    def fmt(value: float) -> str:
        if math.isinf(value):
            return "inf"
        return f"{value:.3f}"

    lines = [
        "# TOST Equivalence / Non-Superiority Reanalysis",
        "",
        "Generated by `scripts/run_tost_equivalence_reanalysis.py`. Read-only",
        "reanalysis of existing per-seed Gate1 CSVs and CIFAR movement summary",
        "CSVs; no rerun or GPU is involved.",
        "",
        f"- Materiality margin: delta = {args.delta} Jaccard (the same threshold",
        "  the grouped mode-distribution audit uses).",
        f"- Both procedures use one-sided alpha = {ALPHA} Student-t tests over",
        "  seed-level statistics (df = n_seeds - 1).",
        "",
        "## 1. Gate1 tracking claim, equivalence-tested (TOST)",
        "",
        "The claim 'posterior support tracks the chain-start magnitude support'",
        "is tested as |posterior-to-IMP minus chain-start-to-IMP| < delta:",
        "",
        "| Row | Mean gap | SE | t_lower | t_upper | t_crit | Equivalent |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in gate1:
        lines.append(
            f"| {r['label']} | {r['mean_gap']:+.5f} | {r['se']:.5f} "
            f"| {fmt(r['t_lower'])} | {fmt(r['t_upper'])} | {r['t_critical']:.3f} "
            f"| {'yes' if r['equivalent_within_delta'] else 'NO'} |"
        )
    lines += [
        "",
        f"All Gate1 rows equivalence-pass at delta = {args.delta}: "
        f"**{'yes' if gate1_all_equivalent else 'NO'}**.",
        "",
        "## 2. CIFAR movement rows, non-superiority-tested",
        "",
        "Movement rows are tested one-sided: posterior support must not beat",
        "the chain-start control by more than delta. Rows whose samples move",
        "*away* from the chain start are expected to fail symmetric",
        "equivalence while passing non-superiority; that asymmetry is the",
        "paper's claim, not a defect:",
        "",
        "| Row | Mean gap | SE | t_upper | t_crit | Non-superior | Symmetric equiv |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in movement:
        lines.append(
            f"| {r['label']} | {r['mean_gap']:+.5f} | {r['se']:.5f} "
            f"| {fmt(r['t_upper'])} | {r['t_critical']:.3f} "
            f"| {'yes' if r['non_superior_within_delta'] else 'NO'} "
            f"| {'yes' if r['equivalent_within_delta'] else 'no'} |"
        )
    lines += [
        "",
        f"All {len(movement)} movement rows are non-superior within delta: "
        f"**{'yes' if movement_all_non_superior else 'NO'}**"
        f" ({movement_equiv_count}/{len(movement)} also symmetric-equivalent).",
        "",
        f"tost_equivalence_audit_ready: {audit['tost_equivalence_audit_ready']}",
        "",
    ]
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(lines))

    print(
        "tost equivalence audit:"
        f" gate1_all_equivalent={gate1_all_equivalent}"
        f" movement_all_non_superior={movement_all_non_superior}"
        f" movement_equivalent={movement_equiv_count}/{len(movement)}"
    )
    if not audit["tost_equivalence_audit_ready"]:
        raise SystemExit("tost equivalence audit not ready")


if __name__ == "__main__":
    main()
