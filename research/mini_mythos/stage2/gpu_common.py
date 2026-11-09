"""Stage 2 helpers: device setup, model loading, paired evaluation, LoRA, best-fit packing.

Evaluation reproduces the Stage 1 CPU baseline exactly except for hardware kernels: the random
initial recurrent state h0 is drawn on the CPU with the Stage 1 seed of each window
(2_000_000 + 1000 * index_in_eval_sets + replica) and then moved to the device.
"""
import contextlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage0"))
import common as s0  # noqa: E402

SEED_BASE = 2_000_000          # Stage 1 baseline seeds
PRIMARY = slice(64, 255)       # scored text tokens t[65..255] (Stage 0/1 primary scope)
WINDOW = 256


def setup(device, threads=4, deterministic=True):
    """Set before CUDA starts: deterministic cuBLAS, no TF32. Returns torch."""
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    sys.dont_write_bytecode = True
    import torch
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(deterministic, warn_only=True)
    if device.startswith("cuda"):
        if not torch.cuda.is_available():
            raise SystemExit("CUDA requested but not available")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
    return torch


def load_model(torch, upstream, model_dir, tokenizer, device, pin_check=True):
    """Pinned-hash check, official loader + full tensor check on CPU, then move to the device."""
    s0.check_inputs(model_dir, tokenizer, strict=pin_check)
    model, report = s0.load_model(torch, upstream, model_dir, verify_state=True)
    model.to(device)
    model.eval()
    return model, report


@contextlib.contextmanager
def cpu_seeded_h0(model, seeds):
    """Make initialize_state draw one h0 per batch row on the CPU from `seeds` (one per row),
    exactly as a batch-one CPU forward seeded with torch.manual_seed(seed) would."""
    original = model.initialize_state

    import torch

    def init(embeds):
        if embeds.shape[0] != len(seeds):
            raise RuntimeError("seed count does not match the batch")
        rows = []
        for seed in seeds:
            torch.manual_seed(seed)
            proto = torch.zeros((1,) + tuple(embeds.shape[1:]), dtype=embeds.dtype)
            rows.append(original(proto))
        return torch.cat(rows, 0).to(embeds.device)

    model.initialize_state = init
    try:
        yield
    finally:
        del model.initialize_state   # back to the class method


def load_windows(path, split="dev"):
    """Eval windows with their Stage 1 index (needed for the seeds)."""
    out = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            r = json.loads(line)
            if split is None or r["split"] == split:
                out.append({"index": i, "domain": r["domain"], "split": r["split"], "doc_id": r["doc_id"],
                            "tokens": r["tokens"]})
    return out


def evaluate(torch, model, windows, device, depth=8, replicas=2, batch=16, bf16=False):
    """Primary-scope mean NLL per window and replica (no BOS; FP32 unless bf16=True).
    Returns {doc_id: [nll_rep0, nll_rep1, ...]}."""
    result = {w["doc_id"]: [None] * replicas for w in windows}
    steps = torch.tensor([depth, 0], dtype=torch.long)
    with torch.no_grad(), torch.autocast(device_type=device.split(":")[0], dtype=torch.bfloat16, enabled=bf16):
        for rep in range(replicas):
            for k in range(0, len(windows), batch):
                chunk = windows[k:k + batch]
                x = torch.tensor([w["tokens"][:WINDOW] for w in chunk], dtype=torch.long, device=device)
                y = torch.tensor([w["tokens"][1:WINDOW] for w in chunk], dtype=torch.long, device=device)
                seeds = [SEED_BASE + 1000 * w["index"] + rep for w in chunk]
                with cpu_seeded_h0(model, seeds):
                    logits = model(x, return_logits=True, num_steps_pair=steps)["logits"]
                logp = torch.log_softmax(logits[:, :WINDOW - 1].double(), dim=-1)
                nll = -logp.gather(2, y[:, :, None]).squeeze(2)        # [B, 255]: t[1..255]
                if not bool(torch.isfinite(nll).all()):
                    raise RuntimeError("non-finite NLL")
                for w, v in zip(chunk, nll[:, PRIMARY].mean(1).tolist()):
                    result[w["doc_id"]][rep] = v
    return result


def domain_means(per_window, windows):
    by = {}
    for w in windows:
        by.setdefault(w["domain"], []).append(float(np.mean(per_window[w["doc_id"]])))
    return {d: float(np.mean(v)) for d, v in sorted(by.items())}


def write_per_window(path, per_window, windows):
    with open(path, "w", encoding="utf-8") as f:
        reps = len(next(iter(per_window.values())))
        f.write("domain,split,doc_id," + ",".join("nll_rep%d" % r for r in range(reps)) + "\n")
        for w in windows:
            f.write("%s,%s,%s,%s\n" % (w["domain"], w["split"], w["doc_id"],
                                       ",".join("%.6f" % v for v in per_window[w["doc_id"]])))


def read_per_window(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        header = f.readline().strip().split(",")
        for line in f:
            parts = line.strip().split(",")
            row = dict(zip(header, parts))
            out[row["doc_id"]] = [float(row[h]) for h in header if h.startswith("nll_rep")]
    return out


# ---------------------------------------------------------------- LoRA (hooks; upstream untouched)

def lora_targets(model):
    """All nn.Linear layers inside attention and MLP of every prelude/core/coda block."""
    import torch
    names = []
    for part in ("prelude", "core_block", "coda"):
        for i, block in enumerate(model.transformer[part]):
            for sub in ("attn", "mlp"):
                for name, mod in getattr(block, sub).named_modules():
                    if isinstance(mod, torch.nn.Linear):
                        names.append((("%s.%d.%s.%s" % (part, i, sub, name)).rstrip("."), mod))
    return names


class LoRA:
    """Rank-r adapters added through forward hooks: y = W x + (alpha/r) * B A x, B initialised to 0."""

    def __init__(self, torch, model, rank=8, alpha=16, seed=0):
        gen = torch.Generator().manual_seed(seed)
        self.scale = alpha / rank
        self.params, self.handles = {}, []
        device = next(model.parameters()).device
        for name, mod in lora_targets(model):
            a = torch.empty(rank, mod.in_features)
            bound = 1.0 / math.sqrt(mod.in_features)
            a.uniform_(-bound, bound, generator=gen)
            A = torch.nn.Parameter(a.to(device))
            B = torch.nn.Parameter(torch.zeros(mod.out_features, rank, device=device))
            self.params[name + ".A"], self.params[name + ".B"] = A, B
            self.handles.append(mod.register_forward_hook(self._hook(A, B)))

    def _hook(self, A, B):
        scale = self.scale

        def hook(module, inputs, output):
            x = inputs[0]
            return output + (x @ A.t().to(x.dtype) @ B.t().to(x.dtype)) * scale
        return hook

    def parameters(self):
        return list(self.params.values())

    def count(self):
        return sum(p.numel() for p in self.params.values())

    def remove(self):
        for h in self.handles:
            h.remove()


# ---------------------------------------------------------------- best-fit packing (as upstream)

def pack_rows(tokens, lengths, row_len, seed, buffer_size=1000, max_rows=None):
    """Upstream BestFitPackingCollator semantics, deterministic given `seed`: documents in a seeded
    random order; each row is filled with the largest buffered document that still fits; if none
    fits, the shortest buffered document is cropped to fill the row (its remainder is dropped).
    No BOS/EOS. Returns a uint16 array [rows, row_len]."""
    lengths = np.asarray(lengths, dtype=np.int64)
    starts = np.concatenate([[0], np.cumsum(lengths)[:-1]])
    order = np.random.default_rng(seed).permutation(len(lengths))
    nxt = 0
    buf = []                                 # document ids
    rows = []
    while max_rows is None or len(rows) < max_rows:
        row = np.empty(row_len, dtype=np.uint16)
        pos = 0
        while pos < row_len:
            while len(buf) < buffer_size and nxt < len(order):
                buf.append(int(order[nxt]))
                nxt += 1
            if not buf:
                return np.stack(rows) if rows else np.zeros((0, row_len), dtype=np.uint16)
            remaining = row_len - pos
            lens = lengths[buf]
            fits = np.where(lens <= remaining, lens, -1)
            j = int(fits.argmax())
            if fits[j] > 0:
                d = buf.pop(j)
                row[pos:pos + lengths[d]] = tokens[starts[d]:starts[d] + lengths[d]]
                pos += int(lengths[d])
            else:
                j = int(lens.argmin())
                d = buf.pop(j)
                row[pos:] = tokens[starts[d]:starts[d] + remaining]
                pos = row_len
        rows.append(row)
    return np.stack(rows)


def load_train_corpus(data_dir):
    tokens = np.fromfile(Path(data_dir) / "train_tokens.u16", dtype="<u2")
    lengths = np.fromfile(Path(data_dir) / "train_doc_lengths.i32", dtype="<i4")
    if int(lengths.sum()) != len(tokens):
        raise SystemExit("training corpus lengths do not match the token file")
    return tokens, lengths
