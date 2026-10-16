#!/usr/bin/env python3
"""Research-only OpenMythos multi-token cached-chunk causal mask intervention.

The upstream OpenMythos.forward constructs a T x T attention mask even when
the cache already has P tokens, when a chunk of T>1 new tokens needs a T x (P+T)
mask. This module applies a temporary instance-local mask override to one
forward call. It is diagnostic and is NOT a production patch.
"""
from contextlib import contextmanager

import torch


def chunk_causal_mask(chunk_len: int, prefix_len: int, device, dtype):
    """Mask shape (1,1,T,P+T); query i may see keys 0..P+i."""
    if chunk_len < 1 or prefix_len < 0:
        raise ValueError("chunk_len must be positive and prefix_len >= 0")
    total = prefix_len + chunk_len
    keys = torch.arange(total, device=device).unsqueeze(0)
    queries = (prefix_len + torch.arange(chunk_len, device=device)).unsqueeze(1)
    blocked = keys > queries
    mask = torch.zeros((chunk_len, total), device=device, dtype=dtype)
    mask.masked_fill_(blocked, float("-inf"))
    return mask[None, None]


def validate_prefix_cache(kv_cache, expected_prefix):
    """Fail closed if attention cache length disagrees with the start position."""
    if not isinstance(kv_cache, dict) or not kv_cache or expected_prefix < 0:
        raise ValueError("Expected a populated KV cache and nonnegative prefix length")
    for layer, tensors in kv_cache.items():
        if not isinstance(tensors, dict):
            raise ValueError(f"Invalid KV-cache entry: {layer}")
        key = "k" if "k" in tensors else "c_kv" if "c_kv" in tensors else None
        if key is None or tensors[key].ndim < 2:
            raise ValueError(f"Missing usable cache tensor: {layer}")
        if int(tensors[key].shape[1]) != expected_prefix:
            raise ValueError(f"KV-cache length mismatch for {layer}: "
                             f"{tensors[key].shape[1]} != {expected_prefix}")


@contextmanager
def temporary_chunk_mask(model, prefix_len: int):
    """Intercept instance-specific mask creation; restore it even on exceptions.

    Non-thread-safe on a shared model. Only for sequential offline experiments.
    """
    if "_causal_mask" in model.__dict__:
        raise ValueError("Model already has an instance-level causal-mask override")

    def mask_override(chunk_len, device, dtype):
        return chunk_causal_mask(chunk_len, prefix_len, device, dtype)

    model._causal_mask = mask_override
    try:
        yield
    finally:
        del model._causal_mask


def cached_chunk_forward(model, input_ids, kv_cache, start_pos, *, n_loops=2):
    """Forward with corrected attention mask, without changing upstream source."""
    if not isinstance(input_ids, torch.Tensor) or input_ids.ndim != 2:
        raise ValueError("input_ids must have shape (batch, sequence)")
    if input_ids.shape[1] < 2 or start_pos < 1:
        raise ValueError("This intervention is for cached chunks of >=2 new tokens")
    validate_prefix_cache(kv_cache, start_pos)
    with temporary_chunk_mask(model, start_pos):
        return model(input_ids, n_loops=n_loops, kv_cache=kv_cache,
                     start_pos=start_pos)
