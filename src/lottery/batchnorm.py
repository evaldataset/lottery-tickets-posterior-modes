from __future__ import annotations

from collections.abc import Mapping

import torch
from torch import nn
from torch.utils.data import DataLoader


BatchNorm = nn.BatchNorm1d | nn.BatchNorm2d | nn.BatchNorm3d


def batchnorm_modules(model: nn.Module) -> list[BatchNorm]:
    return [
        module
        for module in model.modules()
        if isinstance(module, (nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d))
    ]


def set_batchnorm_eval(model: nn.Module) -> int:
    modules = batchnorm_modules(model)
    for module in modules:
        module.eval()
    return len(modules)


def batchnorm_buffer_names(model: nn.Module) -> set[str]:
    names: set[str] = set()
    for module_name, module in model.named_modules():
        if not isinstance(module, (nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d)):
            continue
        prefix = f"{module_name}." if module_name else ""
        for buffer_name, _buffer in module.named_buffers(recurse=False):
            names.add(f"{prefix}{buffer_name}")
    return names


def copy_batchnorm_buffers(
    state: Mapping[str, torch.Tensor],
    reference_state: Mapping[str, torch.Tensor],
    model: nn.Module,
) -> dict[str, torch.Tensor]:
    buffer_names = batchnorm_buffer_names(model)
    copied = {key: value.detach().clone() for key, value in state.items()}
    for key in buffer_names:
        if key in copied and key in reference_state:
            copied[key] = reference_state[key].detach().clone()
    return copied


@torch.no_grad()
def recalibrate_batchnorm(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    *,
    max_batches: int | None = None,
) -> int:
    modules = batchnorm_modules(model)
    if not modules:
        return 0

    model.to(device)
    was_training = model.training
    momenta = {module: module.momentum for module in modules}
    for module in modules:
        module.reset_running_stats()
        module.momentum = None

    model.eval()
    for module in modules:
        module.train()

    try:
        seen_batches = 0
        for x, _y in loader:
            model(x.to(device))
            seen_batches += 1
            if max_batches is not None and seen_batches >= max_batches:
                break
    finally:
        for module in modules:
            module.momentum = momenta[module]
        model.train(was_training)

    return seen_batches
