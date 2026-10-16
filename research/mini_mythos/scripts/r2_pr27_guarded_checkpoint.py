#!/usr/bin/env python3
"""R2 Gate E: fail-closed tokenizer-bound checkpoint IO for PR27-style runs.

Runs on CPU with a tiny REAL GPT-2-vocab-sized PyTorch demo embedding/head.
It is not PR27 itself, and does not load or modify original PR27 train.py,
evaluate.py, OpenMythos core source, or any 118M parameter weights.

Boundary:
  (1) compare frozen tokenizer contract with the actually loaded tokenizer;
  (2) validate a standalone sidecar header and checkpoint SHA256 *before*
      unpickling or allocating model checkpoint tensors;
  (3) use torch.load(weights_only=True), validate embedded metadata and
      actual embedding tensor shape, then allow resume/eval code to consume.
The SHA and metadata detect accidental mismatch/damage, NOT malicious
tampering of both manifest and checkpoint: no digital signature is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import torch
import torch.nn.functional as F

from common import get_repo
from r2_pr27_tokenizer_contract import (
    checkpoint_tokenizer_guard, describe_tokenizer, load_tokenizer,
    validate_contract, validate_source_id,
)

PROTOCOL = "PR27_GUARDED_CHECKPOINT_RESEARCH_V1"
PR27_FROZEN_GPT2_COMMIT = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
PR27_FROZEN_CONTRACT_SHA = "d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9"
PR27_VOCAB = 50257
GITHUB_PR27_SOURCE = "2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4"


def stream_sha256(filename):
    """Hash checkpoint without deserializing any of its tensor objects."""
    h = hashlib.sha256()
    with Path(filename).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_frozen_contract(filename, *, strict_gate=True):
    contract = json.loads(Path(filename).read_text(encoding="utf-8"))
    if not isinstance(contract, dict):
        raise ValueError("Tokenizer contract must be a JSON object")
    expected = contract.get("fingerprint")
    if not isinstance(expected, dict):
        raise ValueError("Tokenizer fingerprint missing")
    # Fail closed on malformed/tampered contract even without real tokenizer.
    validate_contract(contract, candidate=expected)
    if strict_gate:
        if (expected["pinned_revision"] != PR27_FROZEN_GPT2_COMMIT or
                expected["identifier"] != "gpt2" or
                expected["len_tokenizer"] != PR27_VOCAB or
                contract["fingerprint_sha256"] != PR27_FROZEN_CONTRACT_SHA):
            raise ValueError(
                "Gate E requires the EXACT previously frozen PR27 GPT2 tokenizer identity"
            )
    return contract


def identity_metadata(contract, embedding_rows):
    if not isinstance(embedding_rows, int) or embedding_rows <= 0:
        raise ValueError("Embedding vocab size must be specified")
    candidate = contract["fingerprint"]
    validate_contract(contract, candidate=candidate, embedding_rows=embedding_rows)
    return {
        "tokenizer_contract_sha256": contract["fingerprint_sha256"],
        "tokenizer_revision": candidate["pinned_revision"],
        "embedding_vocab_rows": embedding_rows,
    }


def require_real_tokenizer_identity(tokenizer, contract):
    expected = contract["fingerprint"]
    candidate = describe_tokenizer(
        tokenizer, identifier=expected["identifier"],
        pinned_revision=expected["pinned_revision"]
    )
    validate_contract(
        contract, candidate=candidate,
        embedding_rows=int(expected["len_tokenizer"])
    )
    return candidate


def validate_bundle_structure(bundle, expected_header):
    """Validate primitive-only checkpoint metadata and actual embedding rows."""
    if not isinstance(bundle, dict):
        raise ValueError("Checkpoint must be a dictionary")
    if bundle.get("format") != PROTOCOL:
        raise ValueError("Unexpected checkpoint format")
    header = bundle.get("tokenizer_metadata")
    checkpoint_tokenizer_guard(header, expected_header)
    if header != identity_metadata(expected_header, header["embedding_vocab_rows"]):
        raise ValueError("Unexpected checkpoint metadata fields")
    for name in ("model", "opt", "cfg", "mcfg"):
        if not isinstance(bundle.get(name), dict):
            raise ValueError(f"Checkpoint {name} dictionary missing")
    if bundle["cfg"].get("tokenizer") != "gpt2":
        raise ValueError("Training configuration tokenizer differs from bound gpt2")
    if bundle["mcfg"].get("vocab_size") != header["embedding_vocab_rows"]:
        raise ValueError("Model configuration embedding size differs from contract")
    tensor_name = bundle.get("embedding_key")
    if not isinstance(tensor_name, str) or not tensor_name:
        raise ValueError("Explicit embedding tensor key missing")
    tensor = bundle["model"].get(tensor_name)
    if (not isinstance(tensor, torch.Tensor) or tensor.ndim != 2
            or tensor.shape[0] != header["embedding_vocab_rows"]):
        raise ValueError("Checkpoint actual embedding tensor rows do not match contract")
    if (not isinstance(bundle.get("step"), int) or bundle["step"] < 0 or
            not isinstance(bundle.get("tokens_seen"), int) or
            bundle["tokens_seen"] < 0):
        raise ValueError("Checkpoint step/tokens_seen invalid")
    return True


def manifest_for(bundle, frozen_contract, checkpoint_sha):
    validate_bundle_structure(bundle, frozen_contract)
    return {
        "format": PROTOCOL,
        "source_PR27_commit": GITHUB_PR27_SOURCE,
        "checkpoint_sha256": checkpoint_sha,
        "tokenizer_metadata": dict(bundle["tokenizer_metadata"]),
        "step": bundle["step"],
        "tokens_seen": bundle["tokens_seen"],
        "scope": "R2 RESEARCH CHECKPOINT IO; NOT original PR27 trainer/evaluator",
        "integrity_note": "SHA256 not a signature; tamper-resistant provenance "
                          "requires signed/published digest in a trusted channel",
    }


def validate_manifest_before_loading(
    checkpoint_path, manifest_path, frozen_contract, runtime_fingerprint
):
    """Mandatory precondition before any torch.load / checkpoint deserialization."""
    if not Path(manifest_path).is_file():
        raise ValueError("Independent checkpoint manifest missing")
    validate_contract(
        frozen_contract, candidate=runtime_fingerprint,
        embedding_rows=frozen_contract["fingerprint"]["len_tokenizer"]
    )
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("format") != PROTOCOL:
        raise ValueError("Checkpoint manifest format invalid")
    if manifest.get("source_PR27_commit") != GITHUB_PR27_SOURCE:
        raise ValueError("Checkpoint source PR revision mismatch")
    meta = manifest.get("tokenizer_metadata")
    checkpoint_tokenizer_guard(meta, frozen_contract)
    if meta != identity_metadata(frozen_contract, meta["embedding_vocab_rows"]):
        raise ValueError("Checkpoint manifest has unexpected metadata")
    if not isinstance(manifest.get("step"), int) or manifest["step"] < 0:
        raise ValueError("Checkpoint manifest step invalid")
    if not isinstance(manifest.get("tokens_seen"), int) or manifest["tokens_seen"] < 0:
        raise ValueError("Checkpoint manifest training token count invalid")
    observed_sha = stream_sha256(checkpoint_path)
    if observed_sha != manifest.get("checkpoint_sha256"):
        raise ValueError("Checkpoint bytes SHA256 mismatch; refuse deserialization")
    return manifest


def safe_load_bound_checkpoint(
    checkpoint_path, manifest_path, frozen_contract, runtime_fingerprint
):
    """Resume/eval entry: refuse wrong tokenizer *before* torch.load."""
    manifest = validate_manifest_before_loading(
        checkpoint_path, manifest_path, frozen_contract, runtime_fingerprint
    )
    bundle = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    validate_bundle_structure(bundle, frozen_contract)
    if (bundle["tokenizer_metadata"] != manifest["tokenizer_metadata"] or
            bundle["step"] != manifest["step"] or
            bundle["tokens_seen"] != manifest["tokens_seen"]):
        raise ValueError("Embedded checkpoint metadata differs from prechecked sidecar")
    return bundle


def save_bound_checkpoint(
    checkpoint_path, manifest_path, bundle, frozen_contract, runtime_fingerprint
):
    """Write new safe tensor/primitive checkpoint and sidecar; NEVER overwrite."""
    validate_contract(
        frozen_contract, candidate=runtime_fingerprint,
        embedding_rows=frozen_contract["fingerprint"]["len_tokenizer"]
    )
    validate_bundle_structure(bundle, frozen_contract)
    ckpt, sidecar = Path(checkpoint_path), Path(manifest_path)
    if ckpt.resolve() == sidecar.resolve():
        raise ValueError("Checkpoint and manifest paths must differ")
    if ckpt.exists() or sidecar.exists():
        raise FileExistsError("Checkpoint or manifest exists: refusing overwrite")
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    temp = ckpt.with_name(ckpt.name + ".tmp")
    if temp.exists():
        raise FileExistsError("Checkpoint temporary file exists")
    try:
        torch.save(bundle, temp)
        header = manifest_for(bundle, frozen_contract, stream_sha256(temp))
        # Persist checkpoint first. Missing manifest after a crash => fail closed.
        os.replace(temp, ckpt)
        with sidecar.open("x", encoding="utf-8") as f:
            json.dump(header, f, ensure_ascii=False, indent=2)
    finally:
        if temp.exists():
            temp.unlink()
    return header


def synthetic_one_step_bundle(frozen_contract, tokenizer):
    """Tiny real-token-ID CPU *wiring demo*; not OpenMythos weights/training."""
    rows = int(frozen_contract["fingerprint"]["len_tokenizer"])
    torch.manual_seed(27027)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    embedding = torch.nn.Embedding(rows, 4)
    head = torch.nn.Linear(4, rows, bias=False)
    model = torch.nn.ModuleDict({"embedding": embedding, "head": head})
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    ids = tokenizer.encode(
        "The tokenizer contract is immutable.",
        add_special_tokens=False
    )
    if len(ids) < 2:
        raise ValueError("Frozen tokenizer encoded demo sentence too short")
    x = torch.tensor(ids[:-1], dtype=torch.long)
    y = torch.tensor(ids[1:], dtype=torch.long)
    loss = F.cross_entropy(head(embedding(x)), y)
    loss.backward()
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    if not torch.isfinite(loss.detach()):
        raise RuntimeError("Toy checkpoint smoke loss is nonfinite")
    bundle = {
        "format": PROTOCOL,
        "step": 1, "tokens_seen": len(y),
        "model": model.state_dict(), "opt": optimizer.state_dict(),
        "cfg": {"tokenizer": "gpt2", "note": "TINY SYNTHETIC IO DEMO ONLY"},
        "mcfg": {"vocab_size": rows, "architecture": "toy_embedding_head"},
        "tokenizer_metadata": identity_metadata(frozen_contract, rows),
        "embedding_key": "embedding.weight",
    }
    validate_bundle_structure(bundle, frozen_contract)
    return bundle, float(loss.detach())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("smoke", "verify"))
    p.add_argument("--repo", default=".")
    p.add_argument("--tokenizer-contract",
                   default="research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json")
    p.add_argument("--checkpoint",
                   default="research/mini_mythos/results/r2/pr27_bound_toy_checkpoint.pt")
    p.add_argument("--manifest",
                   default="research/mini_mythos/results/r2/pr27_bound_toy_checkpoint.manifest.json")
    a = p.parse_args()
    root = get_repo(a.repo)
    results_dir = (root / "research/mini_mythos/results").resolve()
    paths = [Path(n).resolve() for n in (
        a.tokenizer_contract, a.checkpoint, a.manifest
    )]
    if not all(p.is_relative_to(results_dir) for p in paths):
        p.error("All paths must remain in research/mini_mythos/results")
    contract = read_frozen_contract(paths[0])
    tok = load_tokenizer(
        contract["fingerprint"]["identifier"],
        contract["fingerprint"]["pinned_revision"],
        offline=True
    )
    fingerprint = require_real_tokenizer_identity(tok, contract)
    if a.action == "smoke":
        bundle, loss = synthetic_one_step_bundle(contract, tok)
        save_bound_checkpoint(
            paths[1], paths[2], bundle, contract, fingerprint
        )
        print("Tiny synthetic CPU optimizer-step loss:", f"{loss:.6f}")
    checked = safe_load_bound_checkpoint(
        paths[1], paths[2], contract, fingerprint
    )
    print("PR27 GPT2 pinned tokenizer:", fingerprint["pinned_revision"])
    print("Token-ID and backend identity: MATCH")
    print("Checkpoint token contract: PASS")
    print("Checkpoint metadata + file SHA256: PASS")
    print("Embedding tensor rows:", checked["model"]["embedding.weight"].shape[0])
    print("Loaded safe toy checkpoint step:", checked["step"])
    print("Upstream PR27 train/evaluate patched: False")
    print("118M parameter GPU training performed: False")
    print("Checkpoint:", paths[1])
    print("Sidecar:", paths[2])


if __name__ == "__main__":
    main()
