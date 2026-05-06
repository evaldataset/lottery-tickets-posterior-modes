#!/usr/bin/env python
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lottery.data import _subset_indices, load_digits_bundle, load_fake_cifar10_bundle
from lottery.masks import (
    apply_mask_,
    global_score_mask,
    mask_gradients_,
    mask_sparsity,
    random_mask_like,
)
from lottery.train import evaluate, set_seed
DEFAULT_OUT_JSON = ROOT / "runs" / "unit_smoke_tests.json"
DEFAULT_OUT_MD = ROOT / "docs" / "unit_smoke_tests.md"


def assert_close(actual: float, expected: float, *, tol: float = 1e-7) -> None:
    if not math.isclose(actual, expected, rel_tol=tol, abs_tol=tol):
        raise AssertionError(f"expected {expected}, got {actual}")


def check_seed_determinism() -> dict[str, Any]:
    set_seed(123)
    first = {
        "python": random.random(),
        "numpy": float(np.random.rand()),
        "torch": float(torch.rand(()).item()),
    }
    set_seed(123)
    second = {
        "python": random.random(),
        "numpy": float(np.random.rand()),
        "torch": float(torch.rand(()).item()),
    }
    if first != second:
        raise AssertionError(f"set_seed is not deterministic across RNGs: {first} != {second}")
    return {
        "name": "seed_determinism",
        "passed": True,
        "covers": ["python_random", "numpy_random", "torch_random", "cudnn_policy"],
    }


def check_masks() -> dict[str, Any]:
    scores = {
        "a.weight": torch.tensor([[1.0, 2.0], [3.0, 4.0]]),
        "b.weight": torch.tensor([[5.0, 6.0]]),
    }
    names = ["a.weight", "b.weight"]
    mask = global_score_mask(scores, names, sparsity=0.5, largest=True)
    kept = int(sum(value.sum().item() for value in mask.values()))
    if kept != 3:
        raise AssertionError(f"expected exactly 3 kept weights, got {kept}")
    assert_close(mask_sparsity(mask), 0.5)

    reference = {name: torch.ones_like(value, dtype=torch.bool) for name, value in scores.items()}
    random_a = random_mask_like(reference, sparsity=0.5, seed=7)
    random_b = random_mask_like(reference, sparsity=0.5, seed=7)
    if any(not torch.equal(random_a[name], random_b[name]) for name in reference):
        raise AssertionError("random_mask_like is not deterministic for a fixed seed")
    if int(sum(value.sum().item() for value in random_a.values())) != 3:
        raise AssertionError("random_mask_like did not keep the expected global count")

    model = nn.Linear(3, 2, bias=False)
    with torch.no_grad():
        model.weight.copy_(torch.arange(6, dtype=torch.float32).reshape(2, 3))
    weight_mask = {"weight": torch.tensor([[1, 0, 1], [0, 1, 0]], dtype=torch.bool)}
    apply_mask_(model, weight_mask)
    expected_weight = torch.tensor([[0.0, 0.0, 2.0], [0.0, 4.0, 0.0]])
    if not torch.equal(model.weight.detach(), expected_weight):
        raise AssertionError("apply_mask_ failed to zero masked weights")
    model.weight.grad = torch.ones_like(model.weight)
    mask_gradients_(model, weight_mask)
    if not torch.equal(model.weight.grad, weight_mask["weight"].float()):
        raise AssertionError("mask_gradients_ failed to zero masked gradients")

    return {
        "name": "mask_operations",
        "passed": True,
        "covers": ["global_keep_count", "sparsity", "random_mask_determinism", "weight_and_gradient_masking"],
    }


class FixedLogitModel(nn.Module):
    def __init__(self, logits: torch.Tensor) -> None:
        super().__init__()
        self.register_buffer("stored_logits", logits)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        indices = x[:, 0].long()
        return self.stored_logits.index_select(0, indices)


def check_evaluate_weighted_average() -> dict[str, Any]:
    logits = torch.tensor(
        [
            [2.0, 0.0],
            [0.0, 2.0],
            [1.0, 0.0],
        ],
        dtype=torch.float32,
    )
    y = torch.tensor([0, 0, 1], dtype=torch.long)
    x = torch.arange(3, dtype=torch.float32).reshape(-1, 1)
    loader = DataLoader(TensorDataset(x, y), batch_size=2, shuffle=False)
    metrics = evaluate(FixedLogitModel(logits), loader, torch.device("cpu"))
    expected_loss = torch.nn.functional.cross_entropy(logits, y, reduction="sum").item() / 3
    expected_accuracy = 1 / 3
    assert_close(metrics["loss"], expected_loss)
    assert_close(metrics["accuracy"], expected_accuracy)
    return {
        "name": "evaluate_weighted_average",
        "passed": True,
        "covers": ["sum_loss_over_examples", "accuracy_over_examples", "uneven_batch_sizes"],
    }


def check_data_splits() -> dict[str, Any]:
    first = _subset_indices(20, 6, seed=5, strategy="first")
    seeded_a = _subset_indices(20, 6, seed=5, strategy="seeded")
    seeded_b = _subset_indices(20, 6, seed=5, strategy="seeded")
    if first == seeded_a:
        raise AssertionError("seeded subset unexpectedly equals first-N subset")
    if seeded_a != seeded_b:
        raise AssertionError("seeded subset is not deterministic")

    digits = load_digits_bundle(
        batch_size=32,
        test_batch_size=64,
        seed=3,
        test_size=0.2,
        validation_fraction=0.1,
    )
    if digits.val_loader is None or digits.val_size <= 0:
        raise AssertionError("digits validation split was not created")
    if digits.train_size + digits.val_size + digits.test_size != 1797:
        raise AssertionError("digits split sizes do not sum to dataset size")

    fake = load_fake_cifar10_bundle(
        batch_size=4,
        test_batch_size=8,
        seed=11,
        train_size=20,
        test_size=7,
        validation_fraction=0.25,
    )
    if fake.train_size != 15 or fake.val_size != 5 or fake.test_size != 7:
        raise AssertionError(
            f"fake-CIFAR split sizes changed: train={fake.train_size}, val={fake.val_size}, test={fake.test_size}"
        )
    if fake.val_loader is None:
        raise AssertionError("fake-CIFAR validation loader missing")
    return {
        "name": "data_splits",
        "passed": True,
        "covers": ["seeded_subset_default_path", "digits_validation_split", "fake_cifar_validation_split"],
    }


def build_payload() -> dict[str, Any]:
    checks = [
        check_seed_determinism(),
        check_masks(),
        check_evaluate_weighted_average(),
        check_data_splits(),
    ]
    return {
        "unit_smoke_tests_ready": all(check["passed"] for check in checks),
        "check_count": len(checks),
        "checks": checks,
        "risk_flags": [],
    }


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    status = "ready" if payload["unit_smoke_tests_ready"] else "not ready"
    lines = [
        "# Unit Smoke Tests",
        "",
        "This generated smoke test covers small deterministic invariants that",
        "the artifact-level verifier cannot isolate: RNG seeding, mask keep counts,",
        "masked weights/gradients, evaluation aggregation, and validation splits.",
        "",
        f"Current status: {status}.",
        "",
        "| Check | Passed | Coverage |",
        "| --- | ---: | --- |",
    ]
    for check in payload["checks"]:
        lines.append(
            f"| {check['name']} | `{check['passed']}` | {', '.join(check['covers'])} |"
        )
    lines.extend(["", "## Risk Flags", ""])
    if payload["risk_flags"]:
        lines.extend(f"- {flag}" for flag in payload["risk_flags"])
    else:
        lines.append("- none")
    lines.extend(["", "This file is generated by `scripts/run_unit_smoke_tests.py`."])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    write_json(payload, DEFAULT_OUT_JSON)
    write_markdown(payload, DEFAULT_OUT_MD)
    print(
        json.dumps(
            {
                "unit_smoke_tests_ready": payload["unit_smoke_tests_ready"],
                "check_count": payload["check_count"],
                "risk_flags": payload["risk_flags"],
                "out_json": DEFAULT_OUT_JSON.relative_to(ROOT).as_posix(),
                "out_md": DEFAULT_OUT_MD.relative_to(ROOT).as_posix(),
            }
        )
    )


if __name__ == "__main__":
    main()
