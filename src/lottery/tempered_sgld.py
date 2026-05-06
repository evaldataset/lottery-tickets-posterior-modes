"""Parallel-tempered SGLD: a multimodal-capable stochastic sampler.

Runs K SGLD replicas at a temperature ladder T_1 = 1 < T_2 < ... < T_K and
periodically proposes neighbor swaps with the parallel-tempering Metropolis
criterion, so the cold chain can receive states discovered by hot chains in
other basins. Samples are collected from the T = 1 replica only.

The swap criterion uses minibatch posterior-energy estimates (the same batch
for every replica at a given step, so estimates are comparable), which makes
acceptance approximate rather than exact---the standard compromise in
stochastic-gradient parallel tempering. This sampler exists to test whether
*multimodality* of the posterior approximation changes the support-equivalence
verdict, not to provide exact posterior expectations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import torch
from torch import nn
from torch.utils.data import DataLoader

from lottery.batchnorm import set_batchnorm_eval
from lottery.train import state_to_cpu


@dataclass(frozen=True)
class TemperedSGLDConfig:
    steps: int
    lr: float
    temperatures: tuple[float, ...]
    prior_precision: float
    burn_in: int
    sample_every: int
    swap_every: int
    num_train_examples: int
    likelihood_scale: str = "dataset"
    batchnorm_mode: str = "train"


@dataclass
class TemperedSGLDDiagnostics:
    swap_attempts: int = 0
    swap_accepts: int = 0
    per_pair_accepts: dict[int, int] = field(default_factory=dict)

    @property
    def swap_acceptance_rate(self) -> float:
        if self.swap_attempts == 0:
            return 0.0
        return self.swap_accepts / self.swap_attempts


def _clone_model(model: nn.Module) -> nn.Module:
    import copy

    return copy.deepcopy(model)


def collect_tempered_sgld_samples(
    model: nn.Module,
    train_loader: DataLoader,
    device: torch.device,
    config: TemperedSGLDConfig,
) -> tuple[list[dict[str, torch.Tensor]], TemperedSGLDDiagnostics]:
    if not config.temperatures or config.temperatures[0] != 1.0:
        raise ValueError("temperatures must start at 1.0 (the cold sampling chain)")
    if sorted(config.temperatures) != list(config.temperatures):
        raise ValueError("temperatures must be sorted ascending")

    replicas = [_clone_model(model).to(device) for _ in config.temperatures]
    for replica in replicas:
        replica.train()
        if config.batchnorm_mode == "eval":
            set_batchnorm_eval(replica)
        elif config.batchnorm_mode != "train":
            raise ValueError(
                f"Unsupported tempered SGLD batchnorm_mode: {config.batchnorm_mode}"
            )

    criterion = nn.CrossEntropyLoss(reduction="sum")
    loader_iter = iter(train_loader)
    samples: list[dict[str, torch.Tensor]] = []
    diagnostics = TemperedSGLDDiagnostics()

    def posterior_energy(replica: nn.Module, x: torch.Tensor, y: torch.Tensor) -> tuple[torch.Tensor, float]:
        """Return (loss used for the gradient step, scalar energy estimate)."""
        nll_sum = criterion(replica(x), y)
        if config.likelihood_scale == "dataset":
            loss = nll_sum * (config.num_train_examples / y.numel())
        elif config.likelihood_scale == "mean":
            loss = nll_sum / y.numel()
        else:
            raise ValueError(
                f"Unsupported likelihood_scale: {config.likelihood_scale}"
            )
        prior = 0.0
        for param in replica.parameters():
            prior = prior + 0.5 * config.prior_precision * float(
                param.detach().pow(2).sum()
            )
        return loss, float(loss.detach()) + prior

    for step in range(config.steps):
        try:
            x, y = next(loader_iter)
        except StopIteration:
            loader_iter = iter(train_loader)
            x, y = next(loader_iter)
        x = x.to(device)
        y = y.to(device)

        energies: list[float] = []
        for replica, temperature in zip(replicas, config.temperatures):
            replica.zero_grad(set_to_none=True)
            loss, energy = posterior_energy(replica, x, y)
            loss.backward()
            energies.append(energy)
            with torch.no_grad():
                for param in replica.parameters():
                    if param.grad is None:
                        continue
                    posterior_grad = param.grad + config.prior_precision * param
                    noise_std = (config.lr * temperature) ** 0.5
                    param.add_(posterior_grad, alpha=-0.5 * config.lr)
                    param.add_(torch.randn_like(param), alpha=noise_std)

        if config.swap_every > 0 and step > 0 and step % config.swap_every == 0:
            # Alternate even/odd neighbor pairs across swap rounds.
            start = (step // config.swap_every) % 2
            for pair in range(start, len(replicas) - 1, 2):
                t_cold = config.temperatures[pair]
                t_hot = config.temperatures[pair + 1]
                delta = (1.0 / t_cold - 1.0 / t_hot) * (
                    energies[pair] - energies[pair + 1]
                )
                diagnostics.swap_attempts += 1
                if delta >= 0 or torch.rand(()).item() < float(torch.exp(torch.tensor(delta))):
                    replicas[pair], replicas[pair + 1] = (
                        replicas[pair + 1],
                        replicas[pair],
                    )
                    energies[pair], energies[pair + 1] = (
                        energies[pair + 1],
                        energies[pair],
                    )
                    diagnostics.swap_accepts += 1
                    diagnostics.per_pair_accepts[pair] = (
                        diagnostics.per_pair_accepts.get(pair, 0) + 1
                    )

        if step >= config.burn_in and (step - config.burn_in) % config.sample_every == 0:
            samples.append(state_to_cpu(replicas[0]))

    return samples, diagnostics
