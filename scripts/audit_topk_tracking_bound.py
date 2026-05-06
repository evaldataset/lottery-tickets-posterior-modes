#!/usr/bin/env python
"""Finite-sample verification of the TopK tracking bound (Proposition topk).

The paper's Proposition topk is an asymptotic statement: high-SNR posterior
TopK masks track the chain-start magnitude mask. This audit verifies its
quantitative finite-sample form against the saved full-data SGLD states.

Bound. Model coordinates as theta_i ~ N(mu_i, sigma_i^2) independently and
let tau be the K-th largest |mu| (the TopK(|mu|) threshold). Any coordinate
swapped into TopK(|theta|) relative to TopK(|mu|) displaces a kept
coordinate, and for the cut t = tau each swap forces at least one of: an
excluded coordinate rising above tau, or a kept coordinate falling below
tau. Hence the swap count D satisfies

    E[D] <= B(tau) = sum_{kept i} Qbar(rho_i) + 2 sum_{excluded j} Qbar(rho_j),

where rho_i = | |mu_i| - tau | / sigma_i is the boundary signal-to-noise
ratio and Qbar is the standard normal upper tail. Since both masks keep
exactly K coordinates, J = (K - D) / (K + D), which is convex in D, so by
Jensen

    E[J(TopK(|theta|), TopK(|mu|))] >= (K - B(tau)) / (K + B(tau)).

As min rho -> infinity, B -> 0 and the bound recovers Proposition topk.

Verification. Per seed, mu and sigma are estimated from the 10 saved SGLD
samples (Gaussian surrogate; SGLD samples are not exactly Gaussian, so this
is a model-based prediction checked against the data, not a theorem about
SGLD). The audit computes the predicted lower bound from (mu_hat,
sigma_hat) and compares it with the observed Jaccard overlap between each
sample's TopK mask and the TopK(|mu_hat|) mask, at the artifact's IMP
sparsity. The bound must hold for the observed per-seed mean in every seed.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ARTIFACT = (
    ROOT
    / "runs"
    / "cifar10_resnet20_long30_rewind1_mode_ticket_distribution_activation_aligned_saved_artifacts_r5_p0p3"
    / "20260506_230706"
    / "mask_artifacts.npz"
)
DEFAULT_OUT_JSON = ROOT / "runs" / "topk_tracking_bound_audit.json"
DEFAULT_OUT_MD = ROOT / "docs" / "topk_tracking_bound_audit.md"


def qbar(x: np.ndarray) -> np.ndarray:
    """Standard normal upper tail Qbar(x) = P(Z > x), elementwise."""
    return 0.5 * np.array([math.erfc(v / math.sqrt(2.0)) for v in np.ravel(x)]).reshape(
        np.shape(x)
    )


def seed_of(identifier: str) -> int:
    match = re.search(r"seed_(\d+)", identifier)
    if not match:
        raise SystemExit(f"cannot parse seed from id: {identifier}")
    return int(match.group(1))


def topk_mask(values: np.ndarray, k: int) -> np.ndarray:
    idx = np.argpartition(np.abs(values), -k)[-k:]
    mask = np.zeros(values.shape[0], dtype=bool)
    mask[idx] = True
    return mask


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter) / float(union) if union else 1.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    z = np.load(args.artifact, allow_pickle=True)
    sample_ids = [str(i) for i in z["state_ids__posterior_sample"]]
    sample_states = np.asarray(z["states__posterior_sample"], dtype=np.float64)
    ticket_masks = np.asarray(z["masks__ticket"], dtype=bool)

    # K from the artifact's own IMP sparsity (kept count of the tickets).
    k = int(ticket_masks[0].sum())

    by_seed: dict[int, list[int]] = {}
    for row, identifier in enumerate(sample_ids):
        by_seed.setdefault(seed_of(identifier), []).append(row)

    per_seed = []
    for seed in sorted(by_seed):
        rows = by_seed[seed]
        states = sample_states[rows]
        mu = states.mean(axis=0)
        sigma = states.std(axis=0, ddof=1)
        # Floor sigma at a tiny positive value: coordinates the sampler never
        # moves have rho = inf and contribute zero to B, which the floor
        # preserves numerically.
        sigma = np.maximum(sigma, 1e-12)

        abs_mu = np.abs(mu)
        tau = np.partition(abs_mu, -k)[-k]
        rho = np.abs(abs_mu - tau) / sigma
        kept = abs_mu >= tau
        tails = qbar(np.minimum(rho, 40.0))
        b_tau = float(tails[kept].sum() + 2.0 * tails[~kept].sum())
        bound = (k - b_tau) / (k + b_tau) if b_tau < k else -1.0

        mu_mask = topk_mask(mu, k)
        observed = [jaccard(topk_mask(states[i], k), mu_mask) for i in range(len(rows))]
        observed_mean = float(np.mean(observed))
        per_seed.append(
            {
                "seed": seed,
                "samples": len(rows),
                "kept_k": k,
                "tau": float(tau),
                "boundary_budget_b_tau": b_tau,
                "predicted_jaccard_lower_bound": bound,
                "observed_jaccard_mean": observed_mean,
                "observed_jaccard_min": float(np.min(observed)),
                "bound_holds_for_mean": bool(observed_mean >= bound),
                "median_boundary_rho_within_2sigma_band": float(
                    np.median(rho[np.abs(abs_mu - tau) < 2.0 * sigma])
                    if np.any(np.abs(abs_mu - tau) < 2.0 * sigma)
                    else float("inf")
                ),
            }
        )

    all_hold = all(row["bound_holds_for_mean"] for row in per_seed)
    bounds = [row["predicted_jaccard_lower_bound"] for row in per_seed]
    observed_means = [row["observed_jaccard_mean"] for row in per_seed]

    audit = {
        "topk_tracking_bound_audit_ready": all_hold,
        "artifact": str(args.artifact.relative_to(ROOT)),
        "kept_k": k,
        "total_parameters": int(sample_states.shape[1]),
        "per_seed": per_seed,
        "bound_holds_in_all_seeds": all_hold,
        "predicted_bound_range": [min(bounds), max(bounds)],
        "observed_mean_range": [min(observed_means), max(observed_means)],
        "interpretation": {
            "gaussian_surrogate_bound_consistent_with_sgld_samples": all_hold,
            "bound_is_model_based_prediction_not_a_theorem_about_sgld": True,
            "high_snr_limit_recovers_proposition_topk": True,
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(audit, indent=2) + "\n")

    lines = [
        "# TopK Tracking Bound Audit",
        "",
        "Generated by `scripts/audit_topk_tracking_bound.py`. Verifies the",
        "finite-sample form of Proposition topk on the saved full-data SGLD",
        "states: E[J] >= (K - B(tau)) / (K + B(tau)) with the boundary budget",
        "B(tau) computed from per-coordinate boundary SNR under a Gaussian",
        "surrogate fitted to the 10 saved samples per seed.",
        "",
        "| Seed | K | B(tau) | Predicted lower bound | Observed mean J | Holds |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in per_seed:
        lines.append(
            f"| {row['seed']} | {row['kept_k']} | {row['boundary_budget_b_tau']:.1f} "
            f"| {row['predicted_jaccard_lower_bound']:.4f} "
            f"| {row['observed_jaccard_mean']:.4f} "
            f"| {'yes' if row['bound_holds_for_mean'] else 'NO'} |"
        )
    lines += [
        "",
        f"Bound holds for the observed per-seed mean in all seeds: "
        f"**{'yes' if all_hold else 'NO'}**.",
        "",
        "The bound is a model-based prediction under the Gaussian surrogate,",
        "checked against data; it is not a theorem about SGLD itself. Its",
        "high-SNR limit (B -> 0, J -> 1) recovers Proposition topk, and the",
        "boundary budget B(tau) makes the proposition's `boundary",
        "coordinates' quantitative: only coordinates within a few sigma of",
        "the TopK threshold contribute.",
        "",
        f"topk_tracking_bound_audit_ready: {all_hold}",
        "",
    ]
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(lines))

    print(
        "topk tracking bound audit:"
        f" all_hold={all_hold}"
        f" bounds={[round(b, 4) for b in bounds]}"
        f" observed={[round(o, 4) for o in observed_means]}"
    )
    if not all_hold:
        raise SystemExit("topk tracking bound audit not ready")


if __name__ == "__main__":
    main()
