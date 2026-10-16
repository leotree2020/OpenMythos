#!/usr/bin/env python3
"""R2 Gate D: immutable PR27 GPT-2 tokenizer identity contract (no model weights).

Upstream PR #27 uses gpt2 training tokenizer but allows independent tokenizer
selection at evaluation. Research-only tool freezes immutable HF model revision,
hashes complete token->ID map, fast backend rules, special IDs, encoding probes.
No upstream train/eval changes; MUST integrate in checkpoint paths before GPU.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from common import atomic_json, commit_id, get_repo


PR27_TOKENIZER = "gpt2"
CONTRACT_VERSION = 1
SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
PROBES = (
    "The quick brown fox jumps over the lazy dog.",
    " Myths, models, and 42!",
    "Hello\nworld\n",
    "日本語 中文 한국어",
    "def model(x): return x + 1",
    " \t  spaces and tabs",
)


def canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256_canonical(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_source_id(identifier, revision):
    if identifier != PR27_TOKENIZER:
        raise ValueError(
            "Gate D freezes PR27's training tokenizer gpt2; "
            "different tokenizers require a separate protocol"
        )
    if not isinstance(revision, str) or not SHA_PATTERN.fullmatch(revision):
        raise ValueError("Tokenizer revision must be an immutable 40-hex commit SHA")


def describe_tokenizer(tokenizer, *, identifier, pinned_revision):
    """Content-level identity independent of HF cache or download paths."""
    validate_source_id(identifier, pinned_revision)
    if not bool(getattr(tokenizer, "is_fast", False)):
        raise ValueError("Gate D requires a fast tokenizer for backend fingerprints")
    vocabulary = tokenizer.get_vocab()
    if not isinstance(vocabulary, dict) or not vocabulary:
        raise ValueError("Tokenizer vocabulary is missing")
    if (any(not isinstance(k, str) or not isinstance(v, int) or v < 0
            for k, v in vocabulary.items()) or
            len(set(vocabulary.values())) != len(vocabulary)):
        raise ValueError("Invalid or duplicated token-to-ID vocabulary map")
    rows = sorted(vocabulary.items())
    config = tokenizer.backend_tokenizer.to_str()
    if not isinstance(config, str) or not config:
        raise ValueError("Tokenizer backend serialization unavailable")

    metadata = {
        "eos_token": tokenizer.eos_token,
        "eos_token_id": tokenizer.eos_token_id,
        "bos_token": tokenizer.bos_token,
        "bos_token_id": tokenizer.bos_token_id,
        "unk_token": tokenizer.unk_token,
        "unk_token_id": tokenizer.unk_token_id,
        "pad_token": tokenizer.pad_token,
        "pad_token_id": tokenizer.pad_token_id,
        "all_special_ids": list(tokenizer.all_special_ids),
        "added_vocab_sha256": sha256_canonical(sorted(
            tokenizer.get_added_vocab().items()
        )),
    }
    probe_ids = [
        {"text": text, "ids": [
            int(i) for i in tokenizer.encode(text, add_special_tokens=False)
        ]}
        for text in PROBES
    ]
    result = {
        "contract_version": CONTRACT_VERSION,
        "identifier": identifier,
        "pinned_revision": pinned_revision.lower(),
        "tokenizer_type": type(tokenizer).__name__,
        "is_fast": True,
        "vocab_size_property": int(tokenizer.vocab_size),
        "len_tokenizer": int(len(tokenizer)),
        "vocabulary_entries": len(vocabulary),
        "maximum_token_id": max(vocabulary.values()),
        "token_to_id_sha256": sha256_canonical(rows),
        "backend_serialization_sha256": hashlib.sha256(
            config.encode("utf-8")
        ).hexdigest(),
        "special_tokens": metadata,
        "encoding_probes": probe_ids,
    }
    if result["maximum_token_id"] >= result["len_tokenizer"]:
        raise ValueError("Vocabulary contains IDs beyond embedding dimension")
    if result["vocab_size_property"] != result["len_tokenizer"]:
        raise ValueError(
            "Tokenizer includes added tokens: PR27 constructs model embeddings "
            "from tok.vocab_size instead of len(tok), IDs may exceed embeddings"
        )
    if (metadata["eos_token_id"] is None or
            metadata["pad_token_id"] != metadata["eos_token_id"]):
        raise ValueError(
            "PR27 get_tokenizer() aliases GPT2 pad token to its EOS token"
        )
    return result


def create_contract(fingerprint):
    if not isinstance(fingerprint, dict):
        raise ValueError("Missing tokenizer fingerprint")
    validate_source_id(
        fingerprint.get("identifier"), fingerprint.get("pinned_revision"))
    return {
        "purpose": "R2 PR27 training+evaluation tokenizer identity (research-only)",
        "version": CONTRACT_VERSION,
        "fingerprint": fingerprint,
        "fingerprint_sha256": sha256_canonical(fingerprint),
        "integration_status": "NOT_INTEGRATED_IN_PR27_TRAIN_OR_EVAL",
        "limitations": "Identity snapshot and verification contract only, "
                       "not a modification to PR27 checkpoint or evaluation.",
    }


def validate_contract(contract, *, candidate, embedding_rows=None):
    """Fail closed on token map, backend rules, specials, revision mismatches."""
    if not isinstance(contract, dict) or contract.get("version") != CONTRACT_VERSION:
        raise ValueError("Unknown tokenizer contract version")
    expected = contract.get("fingerprint")
    if not isinstance(expected, dict):
        raise ValueError("Tokenizer contract fingerprint missing")
    validate_source_id(expected.get("identifier"), expected.get("pinned_revision"))
    if contract.get("fingerprint_sha256") != sha256_canonical(expected):
        raise ValueError("Stored tokenizer fingerprint checksum mismatch")
    if not isinstance(candidate, dict):
        raise ValueError("Candidate tokenizer fingerprint missing")
    differences = [
        field for field in expected
        if expected[field] != candidate.get(field)
    ]
    differences += [
        field for field in candidate
        if field not in expected
    ]
    if differences:
        raise ValueError(
            "Tokenizer train/eval identity mismatch in: " +
            ", ".join(sorted(set(differences)))
        )
    if embedding_rows is not None:
        if not isinstance(embedding_rows, int) or embedding_rows <= 0:
            raise ValueError("Embedding vocab dimension must be a positive integer")
        if (expected["len_tokenizer"] != embedding_rows or
                expected["maximum_token_id"] >= embedding_rows):
            raise ValueError("Tokenizer IDs incompatible with embedding vocab")
    return True


def checkpoint_tokenizer_guard(checkpoint_metadata, contract):
    """Fail closed on metadata-only dict; never unpickle model weights."""
    if not isinstance(checkpoint_metadata, dict):
        raise ValueError("Missing checkpoint metadata")
    if (checkpoint_metadata.get("tokenizer_contract_sha256") !=
            contract.get("fingerprint_sha256")):
        raise ValueError("Checkpoint tokenizer identity absent or inconsistent")
    if checkpoint_metadata.get("tokenizer_revision") != (
        contract["fingerprint"]["pinned_revision"]
    ):
        raise ValueError("Checkpoint tokenizer revision absent or inconsistent")
    validate_contract(
        contract, candidate=contract["fingerprint"],
        embedding_rows=checkpoint_metadata.get("embedding_vocab_rows")
    )
    return True


def load_tokenizer(identifier, pinned_revision, *, offline=False):
    validate_source_id(identifier, pinned_revision)
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("Install transformers to load PR27 tokenizer") from exc
    tokenizer = AutoTokenizer.from_pretrained(
        identifier, revision=pinned_revision,
        use_fast=True, local_files_only=offline
    )
    # Same pad-token alias as PR27 experiments/data.py get_tokenizer().
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("freeze", "verify"))
    p.add_argument("--repo", default=".")
    p.add_argument("--revision", default="main")
    p.add_argument("--candidate-identifier", default=PR27_TOKENIZER)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--manifest", default="research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json")
    args = p.parse_args()
    root = get_repo(args.repo)
    path = Path(args.manifest).resolve()
    if not path.is_relative_to(root / "research/mini_mythos/results"):
        p.error("Manifest must be in Git-ignored research results directory")
    if args.action == "freeze":
        if path.exists():
            p.error("Contract exists; refusing to overwrite frozen identity")
        if args.offline:
            p.error("Freeze resolves and pins revision via Hugging Face Hub")
        if args.candidate_identifier != PR27_TOKENIZER:
            p.error("PR27 training tokenizer must be gpt2")
        try:
            from huggingface_hub import HfApi
        except ImportError as exc:
            raise RuntimeError("Install huggingface_hub to resolve model SHA") from exc
        info = HfApi().model_info(
            repo_id=PR27_TOKENIZER, revision=args.revision
        )
        revision = info.sha
        validate_source_id(PR27_TOKENIZER, revision)
        tok = load_tokenizer(PR27_TOKENIZER, revision)
        fingerprint = describe_tokenizer(
            tok, identifier=PR27_TOKENIZER, pinned_revision=revision
        )
        contract = create_contract(fingerprint)
        contract["source_provenance"] = {
            "github_pr27_commit": "2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4",
            "working_fork_commit": commit_id(root),
            "requested_revision": args.revision,
            "resolved_model_revision": revision,
        }
        atomic_json(path, contract)
        print("Pinned PR27 GPT2 model revision:", revision)
        print("Tokenizer embedding rows required:", fingerprint["len_tokenizer"])
        print("Token-to-ID mapping SHA256:", fingerprint["token_to_id_sha256"])
        print("Backend config SHA256:", fingerprint["backend_serialization_sha256"])
        print("Contract fingerprint SHA256:", contract["fingerprint_sha256"])
        print("WARNING: Upstream PR27 checkpoint/eval integration NOT DONE")
        print("Saved:", path)
    else:
        if not path.is_file():
            p.error("Frozen contract not found. Run freeze once first.")
        contract = json.loads(path.read_text(encoding="utf-8"))
        expected = contract["fingerprint"]
        validate_source_id(
            args.candidate_identifier, expected["pinned_revision"])
        tok = load_tokenizer(
            args.candidate_identifier,
            expected["pinned_revision"], offline=args.offline
        )
        candidate = describe_tokenizer(
            tok, identifier=args.candidate_identifier,
            pinned_revision=expected["pinned_revision"]
        )
        validate_contract(
            contract, candidate=candidate,
            embedding_rows=int(tok.vocab_size)
        )
        print("Tokenizer train/eval fingerprint: MATCH")
        print("Pinned revision:", expected["pinned_revision"])
        print("Token-to-ID SHA256:", expected["token_to_id_sha256"])
        print("Special token IDs:", expected["special_tokens"])
        print("Checkpoint integration: NOT_DONE (research validation only)")
        print("Contract:", path)


if __name__ == "__main__":
    main()
