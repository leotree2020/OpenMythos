"""Lossless, bounded custody-manifest storage; no protected-path deduplication.

The complete path-to-pin map is canonical JSON inside one deterministic-header
gzip member. Identical pins at different paths remain distinct records. The
receipt binds both byte representations; file readers never trust gzip alone.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zlib

COMPRESSED_LIMIT = 2 * 1024**2
CANONICAL_LIMIT = 32 * 1024**2
SCHEMA = "mythos-protected-path-map-gzip-v1"
COMPRESSION = "gzip-single-member-deflate-level9-mtime0-no-filename"
HEADER = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff"


class CodecError(ValueError):
    """A representation, integrity, scope, or resource check did not pass."""


class StorageLimitError(CodecError):
    """A frozen representation-size limit blocked storage admission."""


def _require(condition, message):
    if not condition:
        raise CodecError(message)


def _within(condition, message):
    if not condition:
        raise StorageLimitError(message)


def _pin(payload):
    return {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _valid_pin(value):
    return (type(value) is dict and set(value) == {"bytes", "sha256"}
            and type(value["bytes"]) is int and value["bytes"] >= 0
            and type(value["sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None)


def validate_mapping(mapping):
    _require(type(mapping) is dict and bool(mapping), "Nonempty complete path map required")
    for name, value in mapping.items():
        _require(type(name) is str and "\x00" not in name, "String non-NUL protected path required")
        path = PurePosixPath(name)
        _require(path.is_absolute() and str(path) == name and ".." not in path.parts,
                 "Canonical absolute POSIX protected path required")
        _require(_valid_pin(value), "Protected record requires exact bytes/SHA256 pin")
    return mapping


def canonical_bytes(mapping):
    validate_mapping(mapping)
    try:
        raw = (json.dumps(mapping, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except (UnicodeError, TypeError, ValueError) as exc:
        raise CodecError("Manifest cannot be represented as canonical UTF8 JSON") from exc
    _within(len(raw) <= CANONICAL_LIMIT,
            f"Canonical manifest bytes={len(raw)} exceed frozen decompression limit={CANONICAL_LIMIT}")
    return raw


def validate_receipt(receipt):
    _require(type(receipt) is dict and set(receipt) ==
             {"schema", "compression", "record_count", "canonical", "compressed"},
             "Exact custody receipt schema required")
    _require(receipt["schema"] == SCHEMA and receipt["compression"] == COMPRESSION,
             "Unsupported custody encoding")
    _require(type(receipt["record_count"]) is int and receipt["record_count"] > 0,
             "Positive integer record count required")
    _require(_valid_pin(receipt["canonical"]) and _valid_pin(receipt["compressed"]),
             "Receipt requires exact canonical/compressed byte pins")
    _require(receipt["canonical"]["bytes"] > 0 and receipt["compressed"]["bytes"] >= 18,
             "Declared manifest size is invalid")
    _within(receipt["canonical"]["bytes"] <= CANONICAL_LIMIT,
            f"Declared canonical bytes={receipt['canonical']['bytes']} exceed frozen limit={CANONICAL_LIMIT}")
    _within(receipt["compressed"]["bytes"] <= COMPRESSED_LIMIT,
            f"Declared compressed bytes={receipt['compressed']['bytes']} exceed frozen limit={COMPRESSED_LIMIT}")
    return receipt


def pack(mapping):
    """Return compressed bytes and a small receipt without writing any file."""
    raw = canonical_bytes(mapping)
    stream = io.BytesIO()
    # GzipFile fixes OS255 and omits filename; gzip.compress(mtime=0) on
    # Python3.12 can inherit a platform-dependent zlib OS header byte.
    with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0,
                       compresslevel=9) as compressor:
        compressor.write(raw)
    encoded = stream.getvalue()
    _require(encoded[:10] == HEADER, "Canonical gzip header differs")
    _within(len(encoded) <= COMPRESSED_LIMIT,
            f"Compressed manifest bytes={len(encoded)} exceed frozen2MiB limit={COMPRESSED_LIMIT}")
    receipt = {"schema": SCHEMA, "compression": COMPRESSION,
               "record_count": len(mapping), "canonical": _pin(raw),
               "compressed": _pin(encoded)}
    validate_receipt(receipt)
    return encoded, receipt


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key is forbidden")
        result[key] = value
    return result


def unpack(encoded, receipt):
    """Verify both byte pins and strict bounded single-member decoding."""
    validate_receipt(receipt)
    _require(type(encoded) is bytes, "Compressed custody payload must be bytes")
    _within(len(encoded) <= COMPRESSED_LIMIT,
            f"Compressed payload bytes={len(encoded)} exceed frozen2MiB limit={COMPRESSED_LIMIT}")
    _require(_pin(encoded) == receipt["compressed"], "Compressed custody bytes/SHA256 differ")
    _require(encoded[:10] == HEADER, "Canonical gzip header differs")
    inflater = zlib.decompressobj(wbits=31)
    try:
        raw = inflater.decompress(encoded, CANONICAL_LIMIT + 1)
    except zlib.error as exc:
        raise CodecError("Invalid gzip stream or CRC") from exc
    _within(len(raw) <= CANONICAL_LIMIT,
            f"Decoded manifest bytes>={len(raw)} exceed frozen decompression limit={CANONICAL_LIMIT}")
    _require(inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail,
             "Truncated, trailing, concatenated, or over-bound gzip member")
    _require(_pin(raw) == receipt["canonical"], "Canonical custody bytes/SHA256 differ")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                            parse_constant=lambda value: (_ for _ in ()).throw(CodecError("Nonfinite JSON constant")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CodecError("Invalid custody UTF8 JSON") from exc
    validate_mapping(result)
    _require(len(result) == receipt["record_count"], "Decoded protected-path count differs")
    _require(canonical_bytes(result) == raw, "Decoded JSON is not the frozen canonical representation")
    return result


def _regular_location(path, exists):
    path = Path(path)
    _require(path.is_absolute(), "Manifest path must be absolute")
    _require(not any(p.is_symlink() for p in (path, *path.parents)),
             "Symlink custody output/input or parent is forbidden")
    _require(path.parent.is_dir(), "Manifest parent directory must already exist")
    if exists:
        _require(path.is_file() and stat.S_ISREG(path.stat().st_mode), "Regular manifest file required")
    else:
        _require(not os.path.lexists(path), "Existing manifest is preserved without overwrite")
    return path


def write_manifest(path, mapping):
    """Write only a new regular gzip file; caller owns receipt serialization."""
    path = _regular_location(path, exists=False)
    encoded, receipt = pack(mapping)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
    _require(read_manifest(path, receipt) == mapping, "Written complete custody map differs")
    return receipt


def read_manifest(path, receipt):
    path = _regular_location(path, exists=True)
    validate_receipt(receipt)
    _require(path.stat().st_size == receipt["compressed"]["bytes"], "Manifest file size differs")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "Regular opened manifest required")
        encoded = stream.read(COMPRESSED_LIMIT + 1)
    return unpack(encoded, receipt)
