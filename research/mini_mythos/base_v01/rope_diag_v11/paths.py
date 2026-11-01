"""Frozen RoPE diagnostic paths; no imports or work with numerical side effects.

Every call constructs all of its own inputs.  ``torch`` is supplied by the
formal runner only after its environment and import guards have passed.
This module does not implement N: N must call the pinned upstream helper.
Returned tensors are private diagnostic evidence, not a public Git artifact.
"""


def _layout(torch, cosine, sine):
    """Use the exact upstream stack/axis order, without a layout repair."""
    return torch.stack(
        [cosine[None, :, None, :], sine[None, :, None, :]], dim=4
    )


def build_path(torch, name, dim, end, theta, condense_ratio, capture=None):
    """Construct one independent path and retain each intermediate immediately.

    ``theta`` keeps its original Python scalar type.  ``capture``, if supplied,
    must be an empty caller-owned dict; it keeps any already-computed private
    evidence if validation raises part-way through a path.  No previous path
    or repeat may be passed as capture.  No cached tensors are used.
    """
    if name not in {"I32", "T", "P", "R", "Q"}:
        raise ValueError("Unknown path; expected I32, T, P, R or Q")
    if type(dim) is not int or dim <= 0 or dim % 2:
        raise ValueError("dim must be a positive even integer")
    if type(end) is not int or end <= 0:
        raise ValueError("end must be a positive integer")
    if capture is None:
        record = {}
    elif type(capture) is dict and not capture:
        record = capture
    else:
        raise ValueError("capture must be a fresh empty dict")

    def keep(key, tensor):
        # Save before checking, so a failed tensor is retained for sealing.
        record[key] = tensor
        shape, dtype = _record_spec(torch, key, dim, end)
        _validate_tensor(torch, tensor, shape, dtype, name + "/" + key)
        if key == "output":
            validate_final(torch, tensor, dim, end, name + "/output")
        return tensor

    if name in {"I32", "T", "P"}:
        # Every call recomputes this expression, independently of both N and
        # the saved I32 record.  The latter is compared by the runner only.
        omega32 = keep("omega32", 1.0 / (
            theta ** (torch.arange(0, dim, 2, dtype=torch.float32) / dim)
        ))
        t32 = keep("t32", torch.arange(
            end, dtype=torch.float32, device=omega32.device
        ) / condense_ratio)

        if name in {"I32", "T"}:
            phi32 = keep("phi32", torch.outer(t32, omega32).float())
            if name == "I32":
                cos32 = keep("cos32", torch.cos(phi32))
                sin32 = keep("sin32", torch.sin(phi32))
                keep("output", _layout(torch, cos32, sin32))
                return record
            # T promotes the already-rounded FP32 phase, not its factors.
            phi64 = keep("phi64", phi32.to(dtype=torch.float64))
        else:
            # P promotes the two FP32 factors before forming a new outer.
            omega64_from32 = keep("omega64_from32", omega32.to(dtype=torch.float64))
            t64 = keep("t64", t32.to(dtype=torch.float64))
            phi64 = keep("phi64", torch.outer(t64, omega64_from32))

    else:
        # R and Q each call this branch independently.  Q does not read R.
        omega64 = keep("omega64", 1.0 / (
            theta ** (torch.arange(0, dim, 2, dtype=torch.float64) / dim)
        ))
        if name == "Q":
            # Round the FULL expression after pow AND reciprocal, before
            # the native FP32 outer/trig.  Not pow->FP32->reciprocal.
            omega32 = keep("omega32", omega64.to(dtype=torch.float32))
            t32 = keep("t32", torch.arange(
                end, dtype=torch.float32, device=omega32.device
            ) / condense_ratio)
            phi32 = keep("phi32", torch.outer(t32, omega32).float())
            cos32 = keep("cos32", torch.cos(phi32))
            sin32 = keep("sin32", torch.sin(phi32))
            keep("output", _layout(torch, cos32, sin32))
            return record
        t64 = keep("t64", torch.arange(
            end, dtype=torch.float64, device=omega64.device
        ) / condense_ratio)
        phi64 = keep("phi64", torch.outer(t64, omega64))

    # Only T/P/R reach this shared tail; all inputs were made in this call.
    cos64 = keep("cos64", torch.cos(phi64))
    sin64 = keep("sin64", torch.sin(phi64))
    precast64 = keep("precast64", _layout(torch, cos64, sin64))
    keep("output", precast64.to(dtype=torch.float32))
    return record


def bitwise_equal(torch, left, right):
    """Compare dtype, shape and IEEE bytes, preserving the sign of zero.

    Layout is checked separately by validate_record/validate_final.  A
    contiguous *view for comparison* does not replace a path output.
    """
    if left.device.type != "cpu" or right.device.type != "cpu":
        return False
    if left.dtype != right.dtype or tuple(left.shape) != tuple(right.shape):
        return False
    a = left.detach().contiguous().reshape(-1).view(torch.uint8)
    b = right.detach().contiguous().reshape(-1).view(torch.uint8)
    return bool(torch.equal(a, b))


def canonical_bytes(torch, tensor):
    """Return private CPU bytes without depending on NumPy interoperability."""
    if tensor.device.type != "cpu":
        raise ValueError("canonical_bytes requires an already-CPU tensor")
    byte_view = tensor.detach().contiguous().reshape(-1).view(torch.uint8)
    return bytes(byte_view.tolist())


def _record_spec(torch, key, dim, end):
    fp32_keys = {"omega32", "t32", "phi32", "cos32", "sin32", "output"}
    fp64_keys = {"omega64", "omega64_from32", "t64", "phi64", "cos64", "sin64", "precast64"}
    if key not in fp32_keys | fp64_keys:
        raise ValueError("Unknown intermediate key: " + key)
    if key.startswith("omega"):
        shape = (dim // 2,)
    elif key in {"t32", "t64"}:
        shape = (end,)
    elif key in {"output", "precast64"}:
        shape = (1, end, 1, dim // 2, 2)
    else:
        shape = (end, dim // 2)
    return shape, torch.float32 if key in fp32_keys else torch.float64


def _validate_tensor(torch, tensor, shape, dtype, label):
    if not isinstance(tensor, torch.Tensor):
        raise ValueError(label + ": not a tensor")
    if tensor.device.type != "cpu" or tensor.dtype != dtype:
        raise ValueError(label + ": unexpected device or dtype")
    if tuple(tensor.shape) != tuple(shape):
        raise ValueError(label + ": unexpected shape")
    if not tensor.is_contiguous():
        raise ValueError(label + ": not contiguous; no repair is permitted")
    stride = 1
    canonical_stride = []
    for extent in reversed(shape):
        canonical_stride.append(stride)
        stride *= extent
    if tuple(tensor.stride()) != tuple(reversed(canonical_stride)):
        raise ValueError(label + ": unexpected canonical element strides")
    if not bool(torch.isfinite(tensor).all().item()):
        raise ValueError(label + ": non-finite tensor")


def validate_final(torch, tensor, dim, end, label, require_origin=True):
    """Check an N/candidate output, without silently casting or reshaping it.

    For S, pass require_origin=False: finite zero-radius S is a structural
    finding for metrics rather than an excuse to force a candidate invariant.
    """
    _validate_tensor(
        torch, tensor, (1, end, 1, dim // 2, 2), torch.float32, label
    )
    expected_stride = (end * dim, dim, dim, 2, 1)
    if tuple(tensor.stride()) != expected_stride:
        raise ValueError(label + ": unexpected canonical element strides")
    if require_origin:
        at_origin = tensor[0, 0, 0]
        if not bool((at_origin[:, 0] == 1).all().item()):
            raise ValueError(label + ": position-0 cosine is not one")
        if not bool((at_origin[:, 1] == 0).all().item()):
            raise ValueError(label + ": position-0 sine is not zero")


def validate_record(torch, record, name, dim, end):
    """Reject malformed/non-finite path evidence before the next path runs."""
    keys_by_path = {
        "I32": {"omega32", "t32", "phi32", "cos32", "sin32", "output"},
        "T": {"omega32", "t32", "phi32", "phi64", "cos64", "sin64",
              "precast64", "output"},
        "P": {"omega32", "t32", "omega64_from32", "t64", "phi64",
              "cos64", "sin64", "precast64", "output"},
        "R": {"omega64", "t64", "phi64", "cos64", "sin64", "precast64",
              "output"},
        "Q": {"omega64", "omega32", "t32", "phi32", "cos32", "sin32",
              "output"},
    }
    if name not in keys_by_path or set(record) != keys_by_path[name]:
        raise ValueError("Unexpected path record keys")
    for key, tensor in record.items():
        shape, dtype = _record_spec(torch, key, dim, end)
        _validate_tensor(torch, tensor, shape, dtype, name + "/" + key)
    validate_final(torch, record["output"], dim, end, name + "/output")


def verify_i32_intermediates(torch, name, record, i32_record):
    """Check freshly rebuilt T/P inputs against the already-validated I32."""
    keys = {"T": ("omega32", "t32", "phi32"), "P": ("omega32", "t32")}
    if name not in keys:
        raise ValueError("I32 intermediate comparison applies only to T/P")
    for key in keys[name]:
        if not bitwise_equal(torch, record[key], i32_record[key]):
            raise ValueError(name + "/" + key + ": differs from I32 bytes")


def verify_repeat(torch, first, second):
    """Compare every retained intermediate and final tensor, without retries."""
    if set(first) != set(second):
        raise ValueError("Repeat records have different tensor keys")
    for key in first:
        if not bitwise_equal(torch, first[key], second[key]):
            raise ValueError("Repeat differs in " + key)
