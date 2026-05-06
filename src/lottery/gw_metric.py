"""Permutation-invariant Gromov-Wasserstein distances between sparse masks.

Channel-permutation objections to mask comparisons ask whether two masks that
look different coordinate-wise are actually the same subnetwork up to channel
relabeling. Exhaustive graph isomorphism over the full network is infeasible
(see the exhaustive-permutation feasibility audit), so this module takes the
metric route instead: represent each weight tensor's mask as a weighted
bipartite graph over its input and output channels and compare masks by
entropic Gromov-Wasserstein (GW) distance, which is invariant to channel
relabeling by construction.

The per-tensor decomposition is deliberately a *relaxation*: GW couplings are
computed independently per tensor, so channel matchings are not required to
be consistent across tensors the way a true network symmetry is. Every valid
global channel permutation induces per-tensor permutations, hence the
aggregate per-tensor GW distance lower-bounds the distance under any valid
network symmetry. A large per-tensor GW distance therefore certifies that no
channel permutation can reconcile the two masks; a small one is necessary but
not sufficient.

Numpy-only (no new dependencies); entropic GW follows the projected
mirror-descent scheme of Peyre, Cuturi & Solomon (2016) with the square loss.
"""

from __future__ import annotations

import json

import numpy as np

__all__ = [
    "load_mask_artifact",
    "mask_to_channel_graphs",
    "entropic_gw_distance",
    "masked_tensor_gw_distance",
    "aggregate_gw_distance",
    "random_channel_permutation",
]


def load_mask_artifact(path) -> dict:
    """Load a mask_artifacts.npz file into a dict of named mask groups.

    Returns {"parameter_names": [...], "shapes": {name: shape}, and for each group key (e.g. "ticket",
    "posterior_sample", "chain_start"): {"ids": [...], "masks": uint8 array (count, total_params)}}.
    """
    z = np.load(path, allow_pickle=True)
    names = [str(n) for n in z["parameter_names"]]
    shapes = json.loads(str(z["parameter_shapes_json"]))
    offsets = list(z["parameter_offsets"])
    sizes = list(z["parameter_sizes"])
    groups = {}
    for key in z.keys():
        if key.startswith("ids__"):
            group = key[len("ids__"):]
            groups[group] = {
                "ids": [str(i) for i in z[key]],
                "masks": np.asarray(z[f"masks__{group}"], dtype=np.uint8),
            }
    return {
        "parameter_names": names,
        "shapes": {n: tuple(shapes[n]) for n in names},
        "offsets": {n: int(o) for n, o in zip(names, offsets)},
        "sizes": {n: int(s) for n, s in zip(names, sizes)},
        "groups": groups,
    }


def mask_to_channel_graphs(flat_mask: np.ndarray, artifact: dict) -> dict:
    """Collapse a flat mask into per-tensor kept-count channel matrices.

    For a conv weight of shape (O, I, kh, kw) the result is an (O, I) array counting kept weights per (out-channel,
    in-channel) pair; linear weights (O, I) pass through. Tensors with fewer than 2 dims are skipped.
    """
    graphs = {}
    for name in artifact["parameter_names"]:
        shape = artifact["shapes"][name]
        if len(shape) < 2:
            continue
        off = artifact["offsets"][name]
        size = artifact["sizes"][name]
        block = flat_mask[off : off + size].reshape(shape).astype(np.float64)
        axes = tuple(range(2, len(shape)))
        graphs[name] = block.sum(axis=axes) if axes else block
    return graphs


def _bipartite_structure(channel_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build the (in+out)-node structure matrix and node measure for one tensor."""
    out_n, in_n = channel_matrix.shape
    n = out_n + in_n
    structure = np.zeros((n, n), dtype=np.float64)
    structure[:out_n, out_n:] = channel_matrix
    structure[out_n:, :out_n] = channel_matrix.T
    peak = channel_matrix.max()
    if peak <= 0:
        # Empty tensor mask: uniform measure on an edgeless graph.
        measure = np.full(n, 1.0 / n)
        return structure, measure
    # Normalize by the per-pair kept-count ceiling (kernel size) so structure
    # entries live in [0, 1] and squared-loss costs stay O(1); a total-mass
    # normalization would shrink entries to ~1/(O*I) and let any entropic
    # epsilon swamp the geometry.
    structure = structure / peak
    degrees = structure.sum(axis=1)
    deg_total = degrees.sum()
    if deg_total <= 0:
        measure = np.full(n, 1.0 / n)
    else:
        # Mix degree measure with a uniform floor so isolated channels keep
        # positive mass and Sinkhorn stays well-posed.
        measure = 0.9 * degrees / deg_total + 0.1 / n
        measure = measure / measure.sum()
    return structure, measure


def entropic_gw_distance(
    c1: np.ndarray,
    p: np.ndarray,
    c2: np.ndarray,
    q: np.ndarray,
    epsilon: float = 5e-3,
    max_outer: int = 50,
    max_sinkhorn: int = 200,
    tol: float = 1e-7,
) -> float:
    """Entropic Gromov-Wasserstein discrepancy with square loss.

    Returns the (non-entropic) GW objective evaluated at the converged entropic coupling. Symmetric in its arguments up
    to solver tolerance.
    """
    n, m = len(p), len(q)
    transport = np.outer(p, q)
    # Square-loss decomposition constants (Peyre et al. 2016, Prop. 1).
    const = (c1**2 @ p)[:, None] + (q @ (c2**2).T)[None, :]
    # Scale the entropic regularizer to the cost magnitude so the geometry,
    # not the entropy term, decides the coupling regardless of tensor size.
    cost_scale = float(np.median(const)) if np.median(const) > 0 else 1.0
    eps = max(epsilon * cost_scale, 1e-12)
    prev_cost = np.inf
    for _ in range(max_outer):
        cost = const - 2.0 * (c1 @ transport @ c2.T)
        kernel = np.exp(-(cost - cost.min()) / eps)
        kernel = np.maximum(kernel, 1e-300)
        u = np.ones(n) / n
        for _ in range(max_sinkhorn):
            v = q / (kernel.T @ u)
            u_new = p / (kernel @ v)
            if np.max(np.abs(u_new - u)) < tol:
                u = u_new
                break
            u = u_new
        transport = u[:, None] * kernel * v[None, :]
        gw_cost = float((cost * transport).sum())
        if abs(prev_cost - gw_cost) < tol:
            break
        prev_cost = gw_cost
    return max(gw_cost, 0.0)


def masked_tensor_gw_distance(
    channel_matrix_a: np.ndarray,
    channel_matrix_b: np.ndarray,
    epsilon: float = 5e-3,
) -> float:
    """GW distance between one tensor's channel graphs under two masks."""
    c1, p = _bipartite_structure(channel_matrix_a)
    c2, q = _bipartite_structure(channel_matrix_b)
    return entropic_gw_distance(c1, p, c2, q, epsilon=epsilon)


def aggregate_gw_distance(
    flat_mask_a: np.ndarray,
    flat_mask_b: np.ndarray,
    artifact: dict,
    epsilon: float = 5e-3,
) -> dict:
    """Size-weighted aggregate per-tensor GW distance between two masks."""
    graphs_a = mask_to_channel_graphs(flat_mask_a, artifact)
    graphs_b = mask_to_channel_graphs(flat_mask_b, artifact)
    per_tensor = {}
    total_weight = 0.0
    weighted_sum = 0.0
    for name, ga in graphs_a.items():
        gb = graphs_b[name]
        dist = masked_tensor_gw_distance(ga, gb, epsilon=epsilon)
        weight = float(artifact["sizes"][name])
        per_tensor[name] = dist
        weighted_sum += weight * dist
        total_weight += weight
    return {
        "aggregate": weighted_sum / total_weight if total_weight else 0.0,
        "per_tensor": per_tensor,
    }


def random_channel_permutation(
    flat_mask: np.ndarray,
    artifact: dict,
    tensor_name: str,
    consumer_name: str,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply one valid channel symmetry: permute a tensor's out-channels and the matching in-channels of its direct
    consumer.

    This is a genuine network symmetry for a producer/consumer conv pair inside a residual block (e.g. layer1.0.conv1 ->
    layer1.0.conv2), so a permutation-invariant metric must assign the permuted mask distance ~0 from the original even
    though its coordinate-wise Hamming distance is large.
    """
    out = flat_mask.copy()
    shape_t = artifact["shapes"][tensor_name]
    shape_c = artifact["shapes"][consumer_name]
    if shape_t[0] != shape_c[1]:
        raise ValueError(
            f"{tensor_name} out-channels {shape_t[0]} do not feed"
            f" {consumer_name} in-channels {shape_c[1]}"
        )
    perm = rng.permutation(shape_t[0])

    off_t = artifact["offsets"][tensor_name]
    size_t = artifact["sizes"][tensor_name]
    block_t = out[off_t : off_t + size_t].reshape(shape_t)
    out[off_t : off_t + size_t] = block_t[perm].reshape(-1)

    off_c = artifact["offsets"][consumer_name]
    size_c = artifact["sizes"][consumer_name]
    block_c = out[off_c : off_c + size_c].reshape(shape_c)
    out[off_c : off_c + size_c] = block_c[:, perm].reshape(-1)
    return out
