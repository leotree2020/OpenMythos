#!/usr/bin/env python3
"""Round 1, task 3: parameter count of the pinned Qwen3-1.7B from config.json and the safetensors
headers only (no tensor data is read, no model is loaded), and the FP32 memory estimate per arm.

  python3 param_count.py --model-dir <local snapshot of Qwen/Qwen3-1.7B@70d244cc>
"""
import argparse
import glob
import json
import math
import os
import struct

GB, GIB = 1e9, 2 ** 30


def header(path):
    """The JSON header of a safetensors file: 8-byte little-endian length, then the header."""
    with open(path, "rb") as fh:
        n = struct.unpack("<Q", fh.read(8))[0]
        return json.loads(fh.read(n))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-dir", required=True)
    a = p.parse_args()
    cfg = json.load(open(os.path.join(a.model_dir, "config.json")))
    keys = ("hidden_size", "intermediate_size", "num_hidden_layers", "num_attention_heads", "num_key_value_heads",
            "head_dim", "vocab_size", "tie_word_embeddings", "torch_dtype")
    print("config.json:", json.dumps({k: cfg[k] for k in keys}))

    # 1. from the safetensors headers
    tensors = {}
    for f in sorted(glob.glob(os.path.join(a.model_dir, "model-*.safetensors"))):
        h = header(f)
        h.pop("__metadata__", None)
        print("header of %s: %d tensors" % (os.path.basename(f), len(h)))
        tensors.update(h)
    stored = sum(math.prod(v["shape"]) for v in tensors.values())
    dtypes = sorted({v["dtype"] for v in tensors.values()})
    print("tensors: %d, elements stored: %d, dtypes: %s" % (len(tensors), stored, dtypes))
    print("model.embed_tokens.weight:", tensors["model.embed_tokens.weight"]["shape"],
          "| lm_head.weight:", tensors["lm_head.weight"]["shape"] if "lm_head.weight" in tensors else "absent")
    tied = cfg["tie_word_embeddings"] and "lm_head.weight" in tensors
    unique = stored - (math.prod(tensors["lm_head.weight"]["shape"]) if tied else 0)
    print("tie_word_embeddings = %s -> lm_head shares the embedding matrix; unique parameters = %d - %d = %d" % (
        cfg["tie_word_embeddings"], stored, stored - unique, unique))

    # 2. independent check from the config alone
    H, I, L, V = cfg["hidden_size"], cfg["intermediate_size"], cfg["num_hidden_layers"], cfg["vocab_size"]
    nq, nkv, hd = cfg["num_attention_heads"], cfg["num_key_value_heads"], cfg["head_dim"]
    q, k, v_, o = H * nq * hd, H * nkv * hd, H * nkv * hd, nq * hd * H
    mlp = 3 * H * I
    norms = 2 * H + 2 * hd                       # input / post-attention RMSNorm + q_norm / k_norm
    per_layer = q + k + v_ + o + mlp + norms
    formula = V * H + L * per_layer + H          # embedding (tied head) + layers + final norm
    print("config formula: embedding %d*%d = %d; per layer q %d + k %d + v %d + o %d + mlp 3*%d*%d = %d + norms %d = %d; "
          "%d layers = %d; final norm %d; total = %d" % (V, H, V * H, q, k, v_, o, H, I, mlp, norms, per_layer, L,
                                                         L * per_layer, H, formula))
    print("header count == config formula:", unique == formula)

    # 3. memory, FP32 (4 bytes per number)
    copy = unique * 4
    print("one FP32 copy = %d * 4 B = %d B = %.2f GB = %.2f GiB" % (unique, copy, copy / GB, copy / GIB))
    lay = {kk.split("layers.0.")[1]: vv["shape"] for kk, vv in tensors.items()
           if ".layers.0." in kk and kk.endswith("proj.weight")}
    per_rank = sum(s[0] + s[1] for s in lay.values())          # A: r x in, B: out x r
    rows = [("F, S, Y: weights + gradients + AdamW m + AdamW v", 4 * copy, "4 copies"),
            ("A: F + frozen FP32 base copy for the KL anchor", 5 * copy, "5 copies"),
            ("L, rank 8: frozen weights + adapters x 4", copy + 4 * 4 * 8 * per_rank * L, "1 copy + 4 x %d adapter params" % (8 * per_rank * L)),
            ("L, rank 32: frozen weights + adapters x 4", copy + 4 * 4 * 32 * per_rank * L, "1 copy + 4 x %d adapter params" % (32 * per_rank * L)),
            ("N: frozen weights (evaluation only)", copy, "1 copy")]
    print("arm memory (parameters and optimizer state only):")
    for name, b, how in rows:
        print("  %-52s %-34s %7.2f GB  %6.2f GiB" % (name, how, b / GB, b / GIB))
    # transient extras that do not depend on running the model
    bf16_cast = unique * 2
    logits_anchor = 4 * 128 * V * 4
    print("transient: bf16 autocast weight copies up to %.2f GB; FP32 logits of 4 x 128 anchor tokens %.2f GB per model "
          "(x2 models + log-softmax copies for the KL); activations at batch 8 x <= 32 tokens are below 1 GB" % (
              bf16_cast / GB, logits_anchor / GB))
    peak_A = 5 * copy + bf16_cast + 4 * logits_anchor
    print("upper estimate for the largest arm (A): %.1f GB + %.1f GB + %.1f GB = %.1f GB; headroom on an 80 GB A100: %.1f GB" % (
        5 * copy / GB, bf16_cast / GB, 4 * logits_anchor / GB, peak_A / GB, 80 - peak_A / GB))


if __name__ == "__main__":
    main()
