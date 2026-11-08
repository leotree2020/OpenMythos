"""Shared helpers for Stage 0: runtime setup, model/tokenizer loading, BOS-aware scoring.

Import this module before importing torch anywhere else: `setup_runtime()` sets the
thread environment variables that must be in place before torch starts.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

BOS_ID = 0
EOS_ID = 1
WINDOW = 256          # model input length for every scored window
SCORE_FROM = 65       # primary metric scores text tokens t[65..255] (>=64 tokens of context)
DEPTHS = (8, 16, 32)

# Default locations in the designated Codespace.
DEFAULTS = {
    "upstream": "/workspaces/mythos-parcae-pinned",
    "model_dir": "/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/model",
    "tokenizer": "/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/tokenizer/tokenizer.json",
}
PINNED = {
    "upstream_commit": "69284c13746e849104f738d6d1a347b1f457df76",
    "weights_sha256": "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621",
    "config_sha256": "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13",
    "tokenizer_sha256": "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77",
}


def setup_runtime(threads=2):
    """Thread/bytecode settings; must run before `import torch`."""
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[key] = str(threads)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    sys.dont_write_bytecode = True
    import torch
    torch.set_num_threads(threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass  # already set in this process
    torch.use_deterministic_algorithms(True)
    torch.set_grad_enabled(False)
    return torch


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def environment_facts(torch):
    return {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "threads": torch.get_num_threads(),
        "cpu_capability": torch.backends.cpu.get_cpu_capability(),
        "deterministic": torch.are_deterministic_algorithms_enabled(),
        "hostname": os.uname().nodename,
    }


def check_inputs(model_dir, tokenizer_path, strict=True):
    """Hash-check the pinned artifacts. With strict=False (tests) mismatches are only reported."""
    model_dir = Path(model_dir)
    actual = {
        "weights_sha256": sha256_file(model_dir / "pytorch_model.bin"),
        "config_sha256": sha256_file(model_dir / "config.json"),
        "tokenizer_sha256": sha256_file(tokenizer_path),
    }
    bad = {k: v for k, v in actual.items() if v != PINNED[k]}
    if bad and strict:
        raise SystemExit("pinned input mismatch: %s" % bad)
    return {"actual": actual, "mismatch": sorted(bad)}


def load_tokenizer(path):
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(path))
    if tok.token_to_id("<|bos|>") != BOS_ID or tok.token_to_id("<|eos|>") != EOS_ID:
        raise SystemExit("tokenizer special ids differ from BOS=0/EOS=1")
    return tok


def encode(tok, text):
    """Plain text ids, no special tokens (BOS is added explicitly by the caller)."""
    return tok.encode(text, add_special_tokens=False).ids


def load_model(torch, upstream, model_dir, verify_state=True):
    """Official pinned loader, then (optionally) a full tensor equality check against the file,
    because the official loader uses strict=False and ignores the key report."""
    upstream = str(Path(upstream).resolve())
    if upstream not in sys.path:
        sys.path.insert(0, upstream)
    from receval.models.parcae import ModelingParcae
    torch.manual_seed(0)
    model = ModelingParcae.from_pretrained(str(model_dir), device="cpu")
    model.eval()
    report = {"entries": None, "all_equal": None}
    if verify_state:
        sd = torch.load(str(Path(model_dir) / "pytorch_model.bin"), map_location="cpu", weights_only=True)
        sd = {_strip(k): v for k, v in sd.items()}
        state = model.state_dict()
        missing = sorted(set(state) - set(sd))
        unexpected = sorted(set(sd) - set(state))
        unequal = [k for k in state if k in sd and not (state[k].dtype == sd[k].dtype and torch.equal(state[k], sd[k]))]
        report = {"entries": len(state), "missing": missing, "unexpected": unexpected, "unequal": unequal,
                  "all_equal": not (missing or unexpected or unequal)}
        del sd
        if not report["all_equal"]:
            raise SystemExit("loaded model differs from checkpoint: %s" % report)
    return model, report


def _strip(key):
    for prefix in ("module.", "_orig_mod.", "model."):
        if key.startswith(prefix):
            key = key[len(prefix):]
    return key


def build_window(tokens, use_bos):
    """Return (input_ids, positions) for one scored window.

    `tokens` must hold at least WINDOW+1 text ids t[0..256]. Both conditions use an input of
    exactly WINDOW ids so that the random initial state has the same shape:
      no BOS : input t[0:256];          text token t[k] is predicted at position k-1
      BOS    : input [BOS] + t[0:255];  text token t[k] is predicted at position k
    `positions[k-1]` gives the logit row that predicts t[k] for k = 1..255, so both
    conditions are scored on exactly the same 255 text tokens.
    """
    if len(tokens) < WINDOW + 1:
        raise ValueError("window needs at least %d tokens" % (WINDOW + 1))
    if use_bos:
        ids = [BOS_ID] + list(tokens[:WINDOW - 1])
        positions = list(range(1, WINDOW))
    else:
        ids = list(tokens[:WINDOW])
        positions = list(range(0, WINDOW - 1))
    targets = list(tokens[1:WINDOW])
    return ids, positions, targets


def token_nll(torch, model, ids, positions, targets, depth, seed):
    """Per-token NLL (nats, FP64) of `targets` read at `positions`, one forward at `depth`.

    The recurrent initial state is random; `seed` fixes it so different depths and
    BOS conditions of the same window share the same initial state.
    """
    x = torch.tensor([ids], dtype=torch.long)
    torch.manual_seed(seed)
    start = time.perf_counter()
    out = model(x, return_logits=True, num_steps_pair=torch.tensor([depth, 0], dtype=torch.long))
    seconds = time.perf_counter() - start
    logits = out["logits"][0].double()
    if not bool(torch.isfinite(logits).all()):
        raise RuntimeError("non-finite logits")
    logp = torch.log_softmax(logits[positions], dim=-1)
    tgt = torch.tensor(targets, dtype=torch.long)
    nll = -logp.gather(1, tgt[:, None]).squeeze(1)
    return nll.tolist(), seconds
