#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lottery.data import load_torchvision_bundle
from lottery.models import ResNetCIFAR
from lottery.train import evaluate, set_seed, state_to_cpu


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=0.1)
    parser.add_argument("--lr-schedule", choices=["constant", "cosine"], default="cosine")
    parser.add_argument("--weight-decay", type=float, default=5e-4)
    parser.add_argument("--resnet-width", type=int, default=16)
    parser.add_argument("--augment", action="store_true")
    parser.add_argument("--train-subset", type=int, default=None)
    parser.add_argument("--test-subset", type=int, default=None)
    parser.add_argument("--validation-fraction", type=float, default=0.0)
    parser.add_argument("--subset-strategy", choices=["first", "seeded"], default="seeded")
    parser.add_argument("--evaluation-split", choices=["test", "val"], default="test")
    parser.add_argument("--out-dir", type=Path, default=Path("runs/cifar10_resnet20_baseline"))
    return parser.parse_args()


def train_one_epoch(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
    optimizer: torch.optim.Optimizer,
) -> dict[str, float]:
    model.train()
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    correct = 0
    total = 0
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * y.numel()
        correct += (logits.argmax(dim=1) == y).sum().item()
        total += y.numel()
    return {"loss": total_loss / total, "accuracy": correct / total}


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle = load_torchvision_bundle(
        "cifar10",
        batch_size=args.batch_size,
        test_batch_size=1024,
        seed=args.seed,
        flatten=False,
        train_subset=args.train_subset,
        test_subset=args.test_subset,
        augment=args.augment,
        validation_fraction=args.validation_fraction,
        subset_strategy=args.subset_strategy,
    )
    if args.evaluation_split == "val":
        if bundle.val_loader is None:
            raise ValueError("--evaluation-split val requires --validation-fraction > 0")
        eval_loader = bundle.val_loader
    else:
        eval_loader = bundle.test_loader
    model = ResNetCIFAR(
        input_shape=bundle.input_shape,
        num_classes=bundle.num_classes,
        blocks_per_stage=3,
        width=args.resnet_width,
    ).to(device)
    optimizer = torch.optim.SGD(
        model.parameters(),
        lr=args.lr,
        momentum=0.9,
        weight_decay=args.weight_decay,
    )
    if args.lr_schedule == "constant":
        scheduler = None
    elif args.lr_schedule == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=max(1, args.epochs),
        )
    else:
        raise ValueError(f"Unsupported lr_schedule: {args.lr_schedule}")

    history = []
    for epoch in range(1, args.epochs + 1):
        train_metrics = train_one_epoch(model, bundle.train_loader, device, optimizer)
        eval_metrics = evaluate(model, eval_loader, device)
        row = {
            "epoch": epoch,
            "lr": float(optimizer.param_groups[0]["lr"]),
            "train_loss": train_metrics["loss"],
            "train_accuracy": train_metrics["accuracy"],
            "evaluation_split": args.evaluation_split,
            "evaluation_loss": eval_metrics["loss"],
            "evaluation_accuracy": eval_metrics["accuracy"],
            f"{args.evaluation_split}_loss": eval_metrics["loss"],
            f"{args.evaluation_split}_accuracy": eval_metrics["accuracy"],
        }
        history.append(row)
        print(json.dumps(row), flush=True)
        if scheduler is not None:
            scheduler.step()

    metrics = {
        "seed": args.seed,
        "dataset": "cifar10",
        "model": "resnet20",
        "device": str(device),
        "train_size": bundle.train_size,
        "val_size": bundle.val_size,
        "test_size": bundle.test_size,
        "training": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "lr_schedule": args.lr_schedule,
            "weight_decay": args.weight_decay,
            "augment": args.augment,
            "resnet_width": args.resnet_width,
            "train_subset": args.train_subset,
            "test_subset": args.test_subset,
            "validation_fraction": args.validation_fraction,
            "subset_strategy": args.subset_strategy,
            "evaluation_split": args.evaluation_split,
        },
        "final": history[-1],
        "history": history,
    }
    run_dir = args.out_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=False)
    with (run_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    torch.save(state_to_cpu(model), run_dir / "model_state.pt")
    print(f"wrote {run_dir}")


if __name__ == "__main__":
    main()
