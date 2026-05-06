from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Subset, TensorDataset


@dataclass(frozen=True)
class DatasetBundle:
    train_loader: DataLoader
    test_loader: DataLoader
    input_dim: int
    input_shape: tuple[int, ...]
    num_classes: int
    train_size: int
    test_size: int
    val_loader: DataLoader | None = None
    val_size: int = 0


def _validate_fraction(name: str, value: float) -> None:
    if value < 0.0 or value >= 1.0:
        raise ValueError(f"{name} must be in [0.0, 1.0), got {value}")


def _subset_indices(
    dataset_size: int,
    subset_size: int | None,
    *,
    seed: int,
    strategy: str,
) -> list[int]:
    if subset_size is None:
        return list(range(dataset_size))
    count = min(subset_size, dataset_size)
    if strategy == "first":
        return list(range(count))
    if strategy == "seeded":
        generator = torch.Generator()
        generator.manual_seed(seed)
        return torch.randperm(dataset_size, generator=generator)[:count].tolist()
    raise ValueError(f"Unsupported subset strategy: {strategy}")


def _dataset_targets(dataset: object) -> np.ndarray | None:
    targets = getattr(dataset, "targets", None)
    if targets is None:
        targets = getattr(dataset, "labels", None)
    if targets is None:
        return None
    if torch.is_tensor(targets):
        return targets.detach().cpu().numpy()
    return np.asarray(targets)


def _split_indices_for_validation(
    indices: list[int],
    targets: np.ndarray | None,
    *,
    validation_fraction: float,
    seed: int,
) -> tuple[list[int], list[int]]:
    _validate_fraction("validation_fraction", validation_fraction)
    if validation_fraction == 0.0:
        return indices, []
    if len(indices) < 2:
        raise ValueError("validation_fraction requires at least two training examples")
    val_count = max(1, int(round(len(indices) * validation_fraction)))
    if val_count >= len(indices):
        raise ValueError("validation split would leave no training examples")

    stratify = None
    if targets is not None:
        selected_targets = targets[np.asarray(indices)]
        unique, counts = np.unique(selected_targets, return_counts=True)
        if (
            len(unique) > 1
            and counts.min() >= 2
            and val_count >= len(unique)
            and (len(indices) - val_count) >= len(unique)
        ):
            stratify = selected_targets

    train_indices, val_indices = train_test_split(
        indices,
        test_size=val_count,
        random_state=seed,
        stratify=stratify,
    )
    return list(train_indices), list(val_indices)


def load_digits_bundle(
    batch_size: int,
    test_batch_size: int,
    seed: int,
    test_size: float = 0.2,
    validation_fraction: float = 0.0,
) -> DatasetBundle:
    _validate_fraction("test_size", test_size)
    _validate_fraction("validation_fraction", validation_fraction)
    digits = load_digits()
    x = digits.data.astype(np.float32)
    y = digits.target.astype(np.int64)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=seed,
        stratify=y,
    )
    if validation_fraction > 0.0:
        x_train, x_val, y_train, y_val = train_test_split(
            x_train,
            y_train,
            test_size=validation_fraction,
            random_state=seed,
            stratify=y_train,
        )
    else:
        x_val = np.empty((0, x.shape[1]), dtype=np.float32)
        y_val = np.empty((0,), dtype=np.int64)

    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train).astype(np.float32)
    if len(x_val) > 0:
        x_val = scaler.transform(x_val).astype(np.float32)
    x_test = scaler.transform(x_test).astype(np.float32)

    train_ds = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train))
    val_ds = TensorDataset(torch.from_numpy(x_val), torch.from_numpy(y_val))
    test_ds = TensorDataset(torch.from_numpy(x_test), torch.from_numpy(y_test))

    generator = torch.Generator()
    generator.manual_seed(seed)
    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
    )
    val_loader = None
    if len(val_ds) > 0:
        val_loader = DataLoader(val_ds, batch_size=test_batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=test_batch_size, shuffle=False)
    return DatasetBundle(
        train_loader=train_loader,
        test_loader=test_loader,
        input_dim=x.shape[1],
        input_shape=(x.shape[1],),
        num_classes=int(y.max()) + 1,
        train_size=len(train_ds),
        test_size=len(test_ds),
        val_loader=val_loader,
        val_size=len(val_ds),
    )


def load_torchvision_bundle(
    dataset: str,
    batch_size: int,
    test_batch_size: int,
    seed: int,
    root: str | Path = "data",
    flatten: bool = True,
    train_subset: int | None = None,
    test_subset: int | None = None,
    augment: bool = False,
    validation_fraction: float = 0.0,
    subset_strategy: str = "seeded",
) -> DatasetBundle:
    _validate_fraction("validation_fraction", validation_fraction)
    try:
        from torchvision import datasets, transforms
    except ImportError as exc:
        raise RuntimeError(
            "torchvision is required for MNIST/Fashion-MNIST/CIFAR-10. "
            "Use .venv/bin/python after creating the project venv."
        ) from exc

    dataset_key = dataset.lower().replace("_", "-")
    if dataset_key == "mnist":
        dataset_cls = datasets.MNIST
        mean = (0.1307,)
        std = (0.3081,)
        num_classes = 10
    elif dataset_key in {"fashion-mnist", "fashion"}:
        dataset_cls = datasets.FashionMNIST
        mean = (0.2860,)
        std = (0.3530,)
        num_classes = 10
    elif dataset_key in {"cifar10", "cifar-10"}:
        dataset_cls = datasets.CIFAR10
        mean = (0.4914, 0.4822, 0.4465)
        std = (0.2470, 0.2435, 0.2616)
        num_classes = 10
    elif dataset_key in {"cifar100", "cifar-100"}:
        dataset_cls = datasets.CIFAR100
        mean = (0.5071, 0.4865, 0.4409)
        std = (0.2673, 0.2564, 0.2762)
        num_classes = 100
    else:
        raise ValueError(f"Unsupported torchvision dataset: {dataset}")

    train_transform_steps = []
    if augment:
        if dataset_key not in {"cifar10", "cifar-10", "cifar100", "cifar-100"}:
            raise ValueError(
                "augment=True is currently supported only for CIFAR-10 and CIFAR-100"
            )
        if flatten:
            raise ValueError("CIFAR augmentation requires image tensors; set flatten=False")
        train_transform_steps.extend(
            [
                transforms.RandomCrop(32, padding=4),
                transforms.RandomHorizontalFlip(),
            ]
        )
    transform_steps = [
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ]
    if flatten:
        transform_steps.append(transforms.Lambda(lambda tensor: tensor.flatten()))
    train_transform = transforms.Compose([*train_transform_steps, *transform_steps])
    test_transform = transforms.Compose(transform_steps)
    train_source_ds = dataset_cls(root=root, train=True, download=True, transform=train_transform)
    val_source_ds = dataset_cls(root=root, train=True, download=True, transform=test_transform)
    test_ds = dataset_cls(root=root, train=False, download=True, transform=test_transform)
    train_indices = _subset_indices(
        len(train_source_ds),
        train_subset,
        seed=seed,
        strategy=subset_strategy,
    )
    train_indices, val_indices = _split_indices_for_validation(
        train_indices,
        _dataset_targets(train_source_ds),
        validation_fraction=validation_fraction,
        seed=seed,
    )
    train_ds = Subset(train_source_ds, train_indices)
    val_ds = Subset(val_source_ds, val_indices)
    if test_subset is not None:
        test_indices = _subset_indices(
            len(test_ds),
            test_subset,
            seed=seed + 10_000,
            strategy=subset_strategy,
        )
        test_ds = Subset(test_ds, test_indices)
    sample, _ = train_ds[0]

    generator = torch.Generator()
    generator.manual_seed(seed)

    def _seed_worker(worker_id: int) -> None:
        # Each DataLoader worker is given its own deterministic seed derived
        # from the main process seed + worker id. Without this, the workers
        # inherit a NumPy/Python random state that does not survive process
        # forks, so augmentation order becomes nondeterministic across runs.
        worker_seed = (seed + worker_id) % (2**32)
        np.random.seed(worker_seed)
        import random as _random

        _random.seed(worker_seed)

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
        num_workers=2,
        pin_memory=torch.cuda.is_available(),
        worker_init_fn=_seed_worker,
    )
    val_loader = None
    if len(val_ds) > 0:
        val_loader = DataLoader(
            val_ds,
            batch_size=test_batch_size,
            shuffle=False,
            num_workers=2,
            pin_memory=torch.cuda.is_available(),
            worker_init_fn=_seed_worker,
        )
    test_loader = DataLoader(
        test_ds,
        batch_size=test_batch_size,
        shuffle=False,
        num_workers=2,
        pin_memory=torch.cuda.is_available(),
        worker_init_fn=_seed_worker,
    )
    return DatasetBundle(
        train_loader=train_loader,
        test_loader=test_loader,
        input_dim=int(sample.numel()),
        input_shape=tuple(sample.shape),
        num_classes=num_classes,
        train_size=len(train_ds),
        test_size=len(test_ds),
        val_loader=val_loader,
        val_size=len(val_ds),
    )


def load_fake_cifar10_bundle(
    batch_size: int,
    test_batch_size: int,
    seed: int,
    train_size: int = 2048,
    test_size: int = 512,
    validation_fraction: float = 0.0,
) -> DatasetBundle:
    _validate_fraction("validation_fraction", validation_fraction)
    generator = torch.Generator()
    generator.manual_seed(seed)
    val_size = 0
    if validation_fraction > 0.0:
        val_size = max(1, int(round(train_size * validation_fraction)))
        if val_size >= train_size:
            raise ValueError("validation split would leave no fake training examples")
    effective_train_size = train_size - val_size
    x_train = torch.randn(effective_train_size, 3, 32, 32, generator=generator)
    y_train = torch.randint(0, 10, (effective_train_size,), generator=generator)
    x_val = torch.randn(val_size, 3, 32, 32, generator=generator)
    y_val = torch.randint(0, 10, (val_size,), generator=generator)
    x_test = torch.randn(test_size, 3, 32, 32, generator=generator)
    y_test = torch.randint(0, 10, (test_size,), generator=generator)
    train_ds = TensorDataset(x_train, y_train)
    val_ds = TensorDataset(x_val, y_val)
    test_ds = TensorDataset(x_test, y_test)

    loader_generator = torch.Generator()
    loader_generator.manual_seed(seed)
    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        generator=loader_generator,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = None
    if len(val_ds) > 0:
        val_loader = DataLoader(
            val_ds,
            batch_size=test_batch_size,
            shuffle=False,
            num_workers=0,
            pin_memory=torch.cuda.is_available(),
        )
    test_loader = DataLoader(
        test_ds,
        batch_size=test_batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )
    return DatasetBundle(
        train_loader=train_loader,
        test_loader=test_loader,
        input_dim=3 * 32 * 32,
        input_shape=(3, 32, 32),
        num_classes=10,
        train_size=effective_train_size,
        test_size=test_size,
        val_loader=val_loader,
        val_size=val_size,
    )
