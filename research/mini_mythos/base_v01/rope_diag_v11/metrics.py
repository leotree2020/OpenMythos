"""Frozen-protocol RoPE metrics; no torch import or work at module import.

The caller supplies its already-validated torch module and final FP32 tensors.
Nothing here loads weights, invokes a path, writes files, or changes an input.
Undefined observations are represented by a Boolean mask internally and by
JSON null plus explicit reason counts in the reports. Internal zero slots for
masked values are placeholders only: no summary includes those placeholders.
"""

import math


THRESHOLD = 1e-6  # A Python binary64 scalar, never made into a float32 tensor.
EXPECTED_SHAPE = (1, 2048, 1, 64, 2)
EXPECTED_PHASE_SHAPE = (2048, 64)
QUANTILES = (("median", 50), ("p95", 95), ("p99", 99))


def _number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite defined metric; refuse a JSON NaN/Inf")
    return result


def _count(mask):
    return int(mask.sum().item())


def _validate(torch, reference, candidate, phi32):
    for name, value in (("reference", reference), ("candidate", candidate)):
        if tuple(value.shape) != EXPECTED_SHAPE:
            raise ValueError(name + ": expected [1,2048,1,64,2]")
        if value.dtype != torch.float32 or value.device.type != "cpu":
            raise ValueError(name + ": final output must already be CPU FP32")
        if not value.is_contiguous():
            raise ValueError(name + ": expected contiguous canonical layout")
        if not bool(torch.isfinite(value).all().item()):
            raise ValueError(name + ": non-finite input")
    if tuple(phi32.shape) != EXPECTED_PHASE_SHAPE:
        raise ValueError("phi32 must be I32's [2048,64] phase")
    if phi32.dtype != torch.float32 or phi32.device.type != "cpu":
        raise ValueError("phi32 must already be CPU FP32")
    if not bool(torch.isfinite(phi32).all().item()):
        raise ValueError("phi32: non-finite input")


def _summary(torch, values, valid=None, reasons=None):
    """Nearest-rank order statistics, including the stipulated lower median."""
    flat = values.reshape(-1)
    total = flat.numel()
    selected = flat if valid is None else flat[valid.reshape(-1)]
    count = selected.numel()
    reason_counts = {} if reasons is None else {
        name: _count(mask) for name, mask in reasons.items()
    }
    if sum(reason_counts.values()) != total - count:
        raise ValueError("Undefined-observation reasons do not partition N/A")
    result = {
        "total_count": total, "defined_count": count,
        "na_count": total - count, "na_reasons": reason_counts,
        "min": None, "max": None, "mean": None,
        "median": None, "p95": None, "p99": None,
        "summary_na_reason": "no_defined_observations" if count == 0 else None,
    }
    if count == 0:
        return result
    if not bool(torch.isfinite(selected).all().item()):
        raise ValueError("Non-finite defined observations")
    ordered = torch.sort(selected).values
    result.update(min=_number(ordered[0].item()),
                  max=_number(ordered[-1].item()),
                  mean=_number(selected.mean().item()))
    for name, numerator in QUANTILES:
        # Integer arithmetic is exactly ceil((numerator/100)*count).
        rank = (numerator * count + 99) // 100
        result[name] = _number(ordered[rank - 1].item())
    return result


def _axis_summaries(torch, matrix, valid=None, reasons=None):
    """Summaries of rows, vectorized to avoid thousands of tensor reductions.

Infinity is used only as an internal sorting sentinel for undefined slots;
it is not a measured value and is never returned or serialized.
"""
    if matrix.ndim != 2:
        raise ValueError("Axis summaries require a matrix")
    if valid is None:
        valid = torch.ones_like(matrix, dtype=torch.bool)
    if not bool(torch.isfinite(matrix[valid]).all().item()):
        raise ValueError("Non-finite defined axis observation")
    rows, width = matrix.shape
    count = valid.sum(dim=1)
    reason_counts = {} if reasons is None else {
        name: mask.sum(dim=1).tolist() for name, mask in reasons.items()
    }
    ordered = torch.sort(
        torch.where(valid, matrix, torch.full_like(matrix, float("inf"))), dim=1
    ).values
    safe_count = count.clamp_min(1)
    row_index = torch.arange(rows, dtype=torch.int64, device="cpu")
    columns = {
        "min": ordered[:, 0].tolist(),
        "max": ordered[row_index, (count - 1).clamp_min(0)].tolist(),
        "mean": (torch.where(valid, matrix, torch.zeros_like(matrix)).sum(dim=1)
                 / safe_count).tolist(),
    }
    for name, numerator in QUANTILES:
        rank = ((count * numerator + 99) // 100).clamp_min(1)
        columns[name] = ordered[row_index, rank - 1].tolist()
    counts = count.tolist()
    result = []
    for row, n in enumerate(counts):
        reason_row = {name: int(items[row]) for name, items in reason_counts.items()}
        if sum(reason_row.values()) != width - n:
            raise ValueError("Axis N/A reason partition mismatch")
        item = {
            "total_count": width, "defined_count": int(n),
            "na_count": width - int(n), "na_reasons": reason_row,
            "summary_na_reason": "no_defined_observations" if n == 0 else None,
        }
        for name, items in columns.items():
            item[name] = _number(items[row]) if n else None
        result.append(item)
    return result


def _worst_private(torch, errors, reference, candidate):
    """Reference/candidate component values are deliberately private only."""
    flat = errors.reshape(-1)
    maximum = flat.max()
    ties = torch.nonzero(flat == maximum, as_tuple=False).reshape(-1)
    ref_flat, cand_flat = reference.reshape(-1), candidate.reshape(-1)
    first = []
    for index in ties[:10].tolist():
        position, within_position = divmod(index, 128)
        frequency_index, component = divmod(within_position, 2)
        first.append({
            "flat_index": index,
            "coordinate": [0, position, 0, frequency_index, component],
            "position": position, "frequency_index": frequency_index,
            "frequency_exponent_index": 2 * frequency_index,
            "component": "cos" if component == 0 else "sin",
            "reference_value": _number(ref_flat[index].item()),
            "candidate_value": _number(cand_flat[index].item()),
            "absolute_error": _number(flat[index].item()),
        })
    return {"max": _number(maximum.item()), "tie_count": ties.numel(),
            "tie_order": "ascending canonical flattened index",
            "first_10": first}


def _geometry(torch, ref64, cand64, phase):
    c_s, s_s = ref64[..., 0], ref64[..., 1]
    c_x, s_x = cand64[..., 0], cand64[..., 1]
    r_s = torch.sqrt(c_s.square() + s_s.square())
    r_x = torch.sqrt(c_x.square() + s_x.square())
    zero_s, zero_x = r_s == 0, r_x == 0
    radius_valid = ~(zero_s | zero_x)
    angle = torch.zeros_like(c_s)
    raw_angle = torch.atan2(
        c_s[radius_valid] * s_x[radius_valid] - s_s[radius_valid] * c_x[radius_valid],
        c_s[radius_valid] * c_x[radius_valid] + s_s[radius_valid] * s_x[radius_valid],
    )
    finite_angle = torch.isfinite(raw_angle)
    angle_valid = radius_valid.clone()
    angle_valid[radius_valid] = finite_angle
    angle[angle_valid] = raw_angle[finite_angle]
    angle_reasons = {
        "zero_reference_radius_only": zero_s & ~zero_x,
        "zero_candidate_radius_only": zero_x & ~zero_s,
        "zero_both_radii": zero_s & zero_x,
        "invalid_angle": radius_valid & ~angle_valid,
    }
    nonzero_phase = phase != 0
    ratio_valid = angle_valid & nonzero_phase
    ratio_reasons = dict(angle_reasons)
    ratio_reasons["zero_phase_with_defined_angle"] = angle_valid & ~nonzero_phase
    phase64 = phase.to(torch.float64)
    next_phase32 = torch.nextafter(phase, torch.full_like(phase, float("inf")))
    ulp64 = next_phase32.to(torch.float64) - phase64
    if not bool((torch.isfinite(ulp64) & (ulp64 > 0)).all().item()):
        raise ValueError("Unexpected invalid I32 phase ULP")
    relative_angle = torch.zeros_like(angle)
    ulp_angle = torch.zeros_like(angle)
    relative_angle[ratio_valid] = angle[ratio_valid].abs() / phase64[ratio_valid].abs()
    ulp_angle[ratio_valid] = angle[ratio_valid].abs() / ulp64[ratio_valid]
    all_valid = torch.ones_like(angle_valid)
    values = {
        "chord_length": (torch.sqrt((c_x - c_s).square() + (s_x - s_s).square()), all_valid, {}),
        "wrapped_angle_x_minus_reference": (angle, angle_valid, angle_reasons),
        "absolute_wrapped_angle": (angle.abs(), angle_valid, angle_reasons),
        "reference_radius": (r_s, all_valid, {}),
        "candidate_radius": (r_x, all_valid, {}),
        "radial_difference_x_minus_reference": (r_x - r_s, all_valid, {}),
        "absolute_radial_difference": ((r_x - r_s).abs(), all_valid, {}),
        "reference_unit_circle_residual": (c_s.square() + s_s.square() - 1, all_valid, {}),
        "candidate_unit_circle_residual": (c_x.square() + s_x.square() - 1, all_valid, {}),
        "absolute_angle_over_absolute_phi32": (relative_angle, ratio_valid, ratio_reasons),
        "absolute_angle_over_ulp32_phi32": (ulp_angle, ratio_valid, ratio_reasons),
    }
    findings = {
        "reference_zero_radius_pairs": _count(zero_s),
        "candidate_zero_radius_pairs": _count(zero_x),
        "finite_zero_reference_radius_is_structural_finding_not_automatic_fail": True,
    }
    return values, findings


def _component_axis(torch, error, equal_bits, axis):
    positions = error.shape[0]
    if axis == "position":
        matrix = error.reshape(positions, 128)
        equal_matrix = equal_bits.reshape(positions, 128)
    else:
        matrix = error.permute(1, 0, 2).reshape(64, positions * 2)
        equal_matrix = equal_bits.permute(1, 0, 2).reshape(64, positions * 2)
    summaries = _axis_summaries(torch, matrix)
    above = (matrix > THRESHOLD).sum(dim=1).tolist()
    same = equal_matrix.sum(dim=1).tolist()
    width = matrix.shape[1]
    for index, item in enumerate(summaries):
        item.update(index=index, count_above_threshold=int(above[index]),
                    fraction_above_threshold=above[index] / width,
                    bit_identical_count=int(same[index]),
                    bit_identical_fraction=same[index] / width)
        if axis == "frequency":
            item["frequency_exponent_index"] = 2 * index
    return summaries


def _scope(torch, reference, candidate, phi32, end):
    ref32 = reference[0, :end, 0, :, :]
    cand32 = candidate[0, :end, 0, :, :]
    phase = phi32[:end]
    # This exact order is the frozen A5-compatible comparison.
    a5_error32 = (ref32 - cand32).abs()
    a5_max32 = a5_error32.max()
    a5_error64 = a5_error32.to(torch.float64)
    ref64, cand64 = ref32.to(torch.float64), cand32.to(torch.float64)
    descriptive_error64 = (cand64 - ref64).abs()
    same_bits = ref32.view(torch.int32) == cand32.view(torch.int32)
    count = ref32.numel()
    bit_count = _count(same_bits)
    a5_summary = _summary(torch, a5_error64)
    a5_summary["max"] = _number(a5_max32.item())
    fp64_summary = _summary(torch, descriptive_error64)
    for item, errors in ((a5_summary, a5_error64), (fp64_summary, descriptive_error64)):
        # Both error arrays are FP64 here; threshold was not rounded to FP32.
        above = _count(errors > THRESHOLD)
        item.update(count_above_threshold=above, fraction_above_threshold=above / count)
    geometries, findings = _geometry(torch, ref64, cand64, phase)
    geometry_summaries = {}
    per_position_geometry, per_frequency_geometry = {}, {}
    for name, (values, valid, reasons) in geometries.items():
        geometry_summaries[name] = _summary(torch, values, valid, reasons)
        per_position_geometry[name] = _axis_summaries(torch, values, valid, reasons)
        per_frequency_geometry[name] = _axis_summaries(
            torch, values.transpose(0, 1), valid.transpose(0, 1),
            {key: mask.transpose(0, 1) for key, mask in reasons.items()},
        )
    public = {
        "position_range_half_open": [0, end],
        "component_count": count, "pair_count": end * 64,
        "a5_compatible_fp32_error": a5_summary,
        "fp64_descriptive_error": fp64_summary,
        "bit_identical_count": bit_count,
        "bit_identical_fraction": bit_count / count,
        "all_components_bitwise_identical": bit_count == count,
        "geometry": geometry_summaries,
        "structural_findings": findings,
    }
    # All stratified reports are private. Publishing only whole-scope aggregates
    # avoids exposing a dense system of constraints on the stored S components.
    stratified = {
        "per_position": {
            "a5_compatible": _component_axis(torch, a5_error64, same_bits, "position"),
            "fp64_descriptive": _component_axis(torch, descriptive_error64, same_bits, "position"),
            "geometry": per_position_geometry,
        },
        "per_frequency": {
            "a5_compatible": _component_axis(torch, a5_error64, same_bits, "frequency"),
            "fp64_descriptive": _component_axis(torch, descriptive_error64, same_bits, "frequency"),
            "geometry": per_frequency_geometry,
        },
    }
    private = {
        "position_range_half_open": [0, end],
        "component_shape": [end, 64, 2],
        "component_flatten_order": "position, frequency, cos/sin",
        "a5_absolute_errors": a5_error64.reshape(-1).tolist(),
        "fp64_absolute_errors": descriptive_error64.reshape(-1).tolist(),
        "bit_identical_components": same_bits.reshape(-1).tolist(),
        "worst_a5_components": _worst_private(torch, a5_error64, ref64, cand64),
        "worst_fp64_components": _worst_private(torch, descriptive_error64, ref64, cand64),
        "stratified_metrics": stratified,
        "pair_element_arrays": {
            "stored": False,
            "reason": "Derivable from separately preserved private reference/candidate tensors and I32 phase; complete per-position/per-frequency summaries are retained above.",
        },
    }
    return public, private


def compute_comparison(torch, reference, candidate, phi32, label):
    """Return JSON-ready {public, private} for an explicitly directed pair.

    Use reference=S and candidate=X for S-vs-X. For a descriptive T-N comparison,
    use reference=N and candidate=T; angle/radial signs are always candidate minus
    reference. `phi32` must always come from the validated I32 control.

    Do not publish `private`: it contains component values, per-element arrays,
    and all position/frequency-stratified summaries. The caller must separately
    preserve reference/candidate tensors and I32 phase as private evidence.
    Serialize with allow_nan=False. The caller should save/release comparisons one
    at a time rather than retaining every private result in memory.
    """
    _validate(torch, reference, candidate, phi32)
    if not isinstance(label, str) or not label:
        raise ValueError("An explicit comparison label is required")
    ref, cand, phase = reference.detach(), candidate.detach(), phi32.detach()
    full_public, full_private = _scope(torch, ref, cand, phase, 2048)
    slice_public, slice_private = _scope(torch, ref, cand, phase, 112)
    maximum = full_public["a5_compatible_fp32_error"]["max"]
    public = {
        "label": label,
        "reference_role": "first supplied tensor",
        "candidate_role": "second supplied tensor",
        "signed_metric_direction": "candidate_minus_reference",
        "primary_operands": "final_FP32_outputs_exactly_extended_to_FP64",
        "a5_error_definition": "FP32_subtract_abs_max_then_Python_scalar",
        "threshold_python_scalar": THRESHOLD,
        "threshold_comparison_dtype": "FP64 errors / Python scalar; no FP32 threshold cast",
        "quantile_definition": "nearest_rank_ceil(p*n)_1_based; median p=0.5",
        "diagnostic_match": maximum <= THRESHOLD,
        "bitwise_match": full_public["all_components_bitwise_identical"],
        "match_is_compatibility_screen_not_scientific_acceptance": True,
        "full_primary": full_public,
        "slice_0_112_secondary": slice_public,
        "interpretation": {
            "chord_includes_radial_error": True,
            "angle_is_wrapped_not_absolute_phase_error": True,
            "phi32_source": "I32 reconstructed phase, not an observed native intermediate",
            "zero_phase_ratios": "N/A; no epsilon",
            "public_report_excludes_reference_candidate_component_values": True,
        },
    }
    return {"public": public, "private": {
        "label": label, "classification": "target_private_only",
        "full_primary": full_private, "slice_0_112_secondary": slice_private,
    }}
