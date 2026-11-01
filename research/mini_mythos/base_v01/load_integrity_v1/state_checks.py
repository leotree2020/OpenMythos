"""Read-only, CPU state comparison; torch is supplied by the formal runner.

No model loading, device conversion, mutation, or top-level numerical imports.
Byte order is native to the recorded host. Each comparison block is at most
1 MiB per side; contiguous conversion never materializes an entire large view.
The uint8 NumPy bridge exposes bytes only (including BF16 and signed zero).
"""

from collections import defaultdict
from collections.abc import Mapping
import hashlib
import sys


BLOCK_BYTES = 1024 * 1024


def normalize_checkpoint(mapping):
    """Return (normalized, original_to_normalized), rejecting silent overwrite.

    Reproduce the upstream ordered, single-pass prefix loop exactly. For example,
    a prefix appearing again after its turn is not stripped a second time.
    """
    if not isinstance(mapping, Mapping):
        raise ValueError("checkpoint is not a mapping")
    normalized = {}
    provenance = {}
    owner = {}
    for original, value in mapping.items():
        if not isinstance(original, str) or not original:
            raise ValueError("checkpoint key must be a nonempty string")
        key = original
        for prefix in ("module.", "_orig_mod.", "model."):
            if key.startswith(prefix):
                key = key[len(prefix):]
        if not key:
            raise ValueError("checkpoint key is empty after prefix normalization")
        if key in normalized:
            raise ValueError(
                "normalized key collision: %r and %r -> %r"
                % (owner[key], original, key)
            )
        normalized[key] = value
        provenance[original] = key
        owner[key] = original
    return normalized, provenance


def _tensor_metadata(torch, tensor):
    if not isinstance(tensor, torch.Tensor):
        return {"is_tensor": False, "python_type": type(tensor).__name__}
    result = {
        "is_tensor": True,
        "shape": list(tensor.shape),
        "dtype": str(tensor.dtype),
        "device": str(tensor.device),
        "layout": str(tensor.layout),
        "numel": tensor.numel(),
        "element_size": tensor.element_size(),
        "object_id": id(tensor),
        "is_nested": bool(tensor.is_nested),
        "is_quantized": bool(tensor.is_quantized),
        "is_conj": bool(tensor.is_conj()),
        "is_neg": bool(tensor.is_neg()),
    }
    if (tensor.layout == torch.strided and tensor.device.type == "cpu"
            and not result["is_nested"] and not result["is_quantized"]):
        storage = tensor.untyped_storage()
        result.update({
            "stride": list(tensor.stride()),
            "storage_offset": tensor.storage_offset(),
            "data_ptr": tensor.data_ptr(),
            "storage_data_ptr": storage.data_ptr(),
            "storage_nbytes": storage.nbytes(),
            "is_contiguous": tensor.is_contiguous(),
        })
    return result


def _alias_groups(entries, field):
    groups = defaultdict(list)
    for entry in entries:
        metadata = entry["metadata"]
        value = metadata.get(field)
        # A null address is not evidence of shared storage for empty tensors.
        if value is not None and not (field.endswith("ptr") and value == 0):
            groups[value].append(entry["name"])
    return [names for names in groups.values() if len(names) > 1]


def _paired_blocks(left, right, max_elements):
    """Yield equal logical C-order slices with bounded materialization size."""
    if left.numel() <= max_elements:
        yield left, right
        return
    elements_per_row = left.numel() // left.shape[0]
    if elements_per_row <= max_elements:
        rows = max(1, max_elements // elements_per_row)
        for start in range(0, left.shape[0], rows):
            yield left[start:start + rows], right[start:start + rows]
    else:
        for index in range(left.shape[0]):
            yield from _paired_blocks(left[index], right[index], max_elements)


def _raw_bytes(torch, tensor):
    # reshape before dtype view also handles scalar tensors.
    byte_view = tensor.detach().contiguous().reshape(-1).view(torch.uint8)
    return byte_view.numpy().tobytes(order="C")


def compare_state(torch, original_normalized, model, emit_row):
    """Return a serializable PASS/FAIL/BLOCKED report; stream per-key rows.

    All metadata is inventoried before values are compared. Stop immediately on
    the first failing tensor, including nonfinite input. Callback / runtime I/O
    errors propagate to the runner for evidence-preserving BLOCKED handling.
    """
    report = {
        "status": "NOT TESTED", "errors": [], "row_count": 0,
        "byte_order": sys.byteorder, "block_bytes": BLOCK_BYTES,
        "inventory": [], "registered_buffer_slots": [],
        "nonpersistent_buffers": [], "none_buffer_slots": [],
    }

    def error(status, reason, **details):
        report["errors"].append({"status": status, "reason": reason, **details})

    def finish():
        statuses = {item["status"] for item in report["errors"]}
        report["status"] = "FAIL" if "FAIL" in statuses else (
            "BLOCKED" if "BLOCKED" in statuses else "PASS")
        return report

    if not isinstance(original_normalized, Mapping):
        error("FAIL", "normalized checkpoint is not a mapping")
        return finish()
    if any(not isinstance(key, str) or not key for key in original_normalized):
        error("FAIL", "normalized checkpoint contains invalid keys")
        return finish()

    state = model.state_dict()
    parameters = dict(model.named_parameters(remove_duplicate=False))
    buffers = dict(model.named_buffers(remove_duplicate=False))
    registered = {**parameters, **buffers}
    report["source_keys"] = sorted(original_normalized)
    report["state_keys"] = sorted(state)
    report["parameter_names"] = sorted(parameters)
    report["buffer_names"] = sorted(buffers)
    missing = sorted(set(state) - set(original_normalized))
    unexpected = sorted(set(original_normalized) - set(state))
    report["missing_keys"] = missing
    report["unexpected_keys"] = unexpected
    if missing or unexpected:
        error("FAIL", "complete state_dict keys differ", missing=missing,
              unexpected=unexpected)
    overlap = sorted(set(parameters) & set(buffers))
    if overlap:
        error("FAIL", "parameter/buffer classification overlaps", names=overlap)

    for prefix, module in model.named_modules(remove_duplicate=False):
        for local_name, value in module._buffers.items():
            name = prefix + "." + local_name if prefix else local_name
            persistent = local_name not in module._non_persistent_buffers_set
            slot = {"name": name, "persistent": persistent,
                    "is_none": value is None,
                    "checkpoint_present": name in original_normalized,
                    "state_dict_present": name in state}
            if value is None:
                slot["state_dict_exclusion_reason"] = (
                    "registered None slot is not a tensor and is omitted by state_dict")
            report["registered_buffer_slots"].append(slot)
            if value is None:
                report["none_buffer_slots"].append(name)
            if not persistent and value is not None:
                report["nonpersistent_buffers"].append(name)
            if value is not None and not persistent:
                error("BLOCKED", "buffer lies outside complete persistent tensor coverage",
                      **slot)

    unsupported = sorted(set(state) - set(registered))
    uncovered = sorted(set(registered) - set(state))
    if unsupported:
        error("BLOCKED", "state entries are not named parameters or buffers",
              names=unsupported)
    if uncovered:
        error("BLOCKED", "named tensors lack state_dict entries", names=uncovered)

    # Inventory all named tensors and all source/state keys, even if metadata
    # already establishes failure. This does not inspect any tensor values.
    for name in sorted(set(registered) | set(state) | set(original_normalized)):
        category = "parameter" if name in parameters else (
            "buffer" if name in buffers else "unclassified")
        entry = {"name": name, "category": category}
        for label, mapping in (("metadata", registered), ("state_metadata", state),
                               ("source_metadata", original_normalized)):
            entry[label] = (_tensor_metadata(torch, mapping[name])
                            if name in mapping else None)
        report["inventory"].append(entry)
        if name not in state or name not in registered or name not in original_normalized:
            continue
        source = entry["source_metadata"]
        actual = entry["metadata"]
        exported = entry["state_metadata"]
        for label, meta in (("source", source), ("model", actual), ("state", exported)):
            if not meta["is_tensor"]:
                error("BLOCKED", "non-tensor state is unsupported", name=name, side=label)
                continue
            if meta["device"] != "cpu" or meta["layout"] != str(torch.strided):
                error("FAIL", "requires CPU strided dense tensor", name=name, side=label)
            if any(meta[flag] for flag in ("is_nested", "is_quantized", "is_conj", "is_neg")):
                error("BLOCKED", "unsupported tensor representation", name=name, side=label)
        if not all(meta["is_tensor"] for meta in (source, actual, exported)):
            continue
        for field in ("shape", "dtype", "numel", "element_size"):
            if source[field] != actual[field] or actual[field] != exported[field]:
                error("FAIL", "state metadata differs", name=name, field=field,
                      source=source[field], model=actual[field], state=exported[field])
        # A standard state_dict tensor shares backing with its registered tensor.
        # A custom transformed export would require a different explicit protocol.
        for field in ("data_ptr", "storage_offset", "stride"):
            if actual.get(field) != exported.get(field):
                error("BLOCKED", "state_dict does not directly expose registered tensor",
                      name=name, field=field)

    named_entries = [item for item in report["inventory"] if item["metadata"] is not None]
    report["same_object_aliases"] = _alias_groups(named_entries, "object_id")
    report["shared_storage_aliases"] = _alias_groups(named_entries, "storage_data_ptr")
    if report["errors"]:
        return finish()

    for entry in report["inventory"]:
        name = entry["name"]
        source = original_normalized[name]
        actual = registered[name]
        float_like = source.is_floating_point() or source.is_complex()
        row = {
            "name": name, "category": entry["category"],
            "numel": source.numel(), "shape": list(source.shape),
            "dtype": str(source.dtype), "source_stride": list(source.stride()),
            "model_stride": list(actual.stride()), "status": "NOT TESTED",
            "bytewise_equal": None, "hash_complete": False,
            "source_sha256": None, "model_sha256": None,
            "source_prefix_sha256": None, "model_prefix_sha256": None,
            "source_bytes_hashed": 0, "model_bytes_hashed": 0,
            "bytes_hashed": 0, "expected_bytes": source.numel() * source.element_size(),
            "source_finite": None if float_like else "N/A",
            "model_finite": None if float_like else "N/A",
        }
        source_hash = hashlib.sha256()
        model_hash = hashlib.sha256()
        failed = None
        max_elements = max(1, BLOCK_BYTES // source.element_size())
        for left, right in _paired_blocks(source.detach(), actual.detach(), max_elements):
            if float_like:
                if not bool(torch.isfinite(left).all().item()):
                    row["source_finite"] = False
                    failed = "checkpoint contains nonfinite values"
                    break
                if not bool(torch.isfinite(right).all().item()):
                    row["model_finite"] = False
                    failed = "model contains nonfinite values"
                    break
            source_bytes = _raw_bytes(torch, left)
            model_bytes = _raw_bytes(torch, right)
            expected_source_block_bytes = left.numel() * left.element_size()
            expected_model_block_bytes = right.numel() * right.element_size()
            if (len(source_bytes) != expected_source_block_bytes
                    or len(model_bytes) != expected_model_block_bytes
                    or expected_source_block_bytes != expected_model_block_bytes):
                row["failed_block_byte_counts"] = {
                    "source_actual": len(source_bytes),
                    "source_expected": expected_source_block_bytes,
                    "model_actual": len(model_bytes),
                    "model_expected": expected_model_block_bytes,
                }
                failed = "canonical block byte counts differ from tensor metadata"
                break
            source_hash.update(source_bytes)
            model_hash.update(model_bytes)
            row["source_bytes_hashed"] += len(source_bytes)
            row["model_bytes_hashed"] += len(model_bytes)
            # Compatibility field: paired coverage only after both sizes were
            # checked independently; it is not an alias of the source count.
            row["bytes_hashed"] += expected_source_block_bytes
            if source_bytes != model_bytes:
                row["bytewise_equal"] = False
                failed = "canonical tensor bytes differ"
                break
        if failed is None and any(row[key] != row["expected_bytes"] for key in
                                  ("source_bytes_hashed", "model_bytes_hashed", "bytes_hashed")):
            failed = "canonical byte coverage is incomplete"
        row["source_prefix_sha256"] = source_hash.hexdigest()
        row["model_prefix_sha256"] = model_hash.hexdigest()
        if failed is not None:
            row["status"] = "FAIL"
            row["reason"] = failed
            error("FAIL", failed, name=name)
        else:
            row["status"] = "PASS"
            row["bytewise_equal"] = True
            row["hash_complete"] = True
            row["source_sha256"] = source_hash.hexdigest()
            row["model_sha256"] = model_hash.hexdigest()
            if float_like:
                row["source_finite"] = True
                row["model_finite"] = True
        emit_row(row)
        report["row_count"] += 1
        if failed is not None:
            return finish()
    report["compared_key_count"] = report["row_count"]
    return finish()
