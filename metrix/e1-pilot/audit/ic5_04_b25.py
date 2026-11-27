"""ic5_04 (implementation stage C, C1 second submission, round 1, task 4): interpretation B25 (Review Gate's ruling on
C1, item 3). I implement the checkpoint hash from the TEXT of interpretations.B25 (read with ast from
src/metrix_e1/interpretations.py, never imported), build random tiny Qwen3 models myself (no weights loaded:
Qwen3ForCausalLM(config) with torch.manual_seed(seed); the configuration values are those the probe's tinysha uses,
so that both sides hash the same model), and compare my hashes with the probe's `tinysha:SEED` output (the probe
reports/impl_c/c1b_gate_probe.py is run as a driver subprocess, ruling item 5). My hashes are computed and printed
before the probe is started.
B25 text (computation): h = SHA-256(); for each key k of module.state_dict() in sorted order (Python string order),
with t = the tensor detached, moved to the CPU and made contiguous: h.update(UTF-8 bytes of k + b'\\0' + str(t.dtype)
+ b'\\0' + str(tuple(t.shape)) + b'\\0'), then h.update(the raw bytes of t, flattened and viewed as uint8, in the
host's byte order); the hash is h.hexdigest().
My implementation takes the raw bytes through numpy (t.numpy().tobytes() for dtypes numpy has; through an int16 view
for bfloat16), not through a uint8 view, so the byte source is independent of the one in train.py.
Also: the hash is the same in train() and eval() mode, a single changed element changes it, the tied embedding is
hashed under both of its state_dict names, and non-persistent buffers are not part of it.
Data Auditor's own script; nothing of the package is imported, called or copied.
usage: python -I ic5_04_b25.py <repo_root> <python_for_probe> <scratch_dir_outside_repo>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from ia_common import jsonl_bytes, run

INTERP = "metrix/e1-pilot/src/metrix_e1/interpretations.py"
PROBE = "metrix/e1-pilot/reports/impl_c/c1b_gate_probe.py"
SEEDS = [0, 1, 4, 7, 12345]
CFG = dict(vocab_size=151936, hidden_size=64, intermediate_size=128, num_hidden_layers=2, num_attention_heads=4,
           num_key_value_heads=2, head_dim=16, tie_word_embeddings=True)


def b25_text(repo):
    t = ast.parse(open(os.path.join(repo, INTERP), encoding="utf-8").read())
    consts = {s.targets[0].id: s.value.value for s in t.body if isinstance(s, ast.Assign) and len(s.targets) == 1
              and isinstance(s.targets[0], ast.Name) and isinstance(s.value, ast.Constant)}
    ent = next(s.value for s in t.body if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "ENTRIES")
    for d in ent.elts:
        e = {k.value: (consts[v.id] if isinstance(v, ast.Name) else ast.literal_eval(v)) for k, v in zip(d.keys, d.values)}
        if e["id"] == "B25":
            return e


def raw_bytes(t):
    import numpy as np
    import torch
    if t.dtype == torch.bfloat16:
        a = t.view(torch.int16).numpy()
    else:
        a = t.numpy()
    a = np.ascontiguousarray(a).reshape(-1)
    return a.tobytes(order="C")


def my_b25(module):
    import torch
    h = hashlib.sha256()
    sd = module.state_dict()
    for k in sorted(sd):
        t = sd[k].detach().to("cpu").contiguous()
        h.update(k.encode("utf-8") + b"\0" + str(t.dtype).encode("utf-8") + b"\0" + str(tuple(t.shape)).encode("utf-8")
                 + b"\0")
        h.update(raw_bytes(t))
    assert torch is not None
    return h.hexdigest()


def tiny(seed):
    import torch
    from transformers import Qwen3Config, Qwen3ForCausalLM
    torch.manual_seed(seed)
    return Qwen3ForCausalLM(Qwen3Config(**CFG)).eval()


def main():
    repo, py, scratch = sys.argv[1], sys.argv[2], Path(sys.argv[3]).resolve()
    ok = True
    e = b25_text(repo)
    print("interpretations.B25 (read with ast): status %r | ruling %r | where %r" % (e.get("status"), e.get("ruling"),
                                                                                  e.get("where")))
    print("text: %s" % e["text"])
    must = ["sorted order", "str(t.dtype)", "str(tuple(t.shape))", "b'\\0'", "viewed as uint8", "hexdigest",
            "detached, moved to the CPU and made contiguous", "not a file-byte hash"]
    print("the text states every element my implementation follows %s: %s" % (must, all(m in e["text"] for m in must)))
    ok &= all(m in e["text"] for m in must) and e.get("status") == "ACCEPTED（Review Gate 2026-11-25）"
    import sys as _s
    import torch
    import numpy
    print("torch %s | numpy %s | host byte order %s" % (torch.__version__, numpy.__version__, _s.byteorder))
    print("tiny configuration (the values the probe's tinysha uses): %s" % CFG)
    mine = {}
    for s in SEEDS:
        m = tiny(s)
        sd = m.state_dict()
        mine[s] = my_b25(m)
        if s == 0:
            keys = sorted(sd)
            print("seed 0: %d state_dict keys; first %s; last %s" % (len(keys), keys[:3], keys[-2:]))
            print("  dtypes %s | lm_head.weight and model.embed_tokens.weight both keys: %s, same storage: %s" % (
                sorted({str(v.dtype) for v in sd.values()}), "lm_head.weight" in sd and "model.embed_tokens.weight" in sd,
                sd["lm_head.weight"].data_ptr() == sd["model.embed_tokens.weight"].data_ptr()))
            bufs = [n for n, _ in m.named_buffers()]
            print("  named buffers %s; in state_dict: %s" % (bufs, [b for b in bufs if b in sd]))
            m.train()
            same_train = my_b25(m) == mine[s]
            m.eval()
            with torch.no_grad():
                p = dict(m.named_parameters())["model.layers.1.mlp.down_proj.weight"]
                old = p[0, 0].item()
                p[0, 0] = old + 1.0
                changed = my_b25(m) != mine[s]
                p[0, 0] = old
            back = my_b25(m) == mine[s]
            bf = tiny(s).to(torch.bfloat16)
            print("  same hash in train() mode: %s | one element changed -> hash changes: %s | restored -> same: %s | "
                  "bfloat16 copy hashes (mine) %s" % (same_train, changed, back, my_b25(bf)))
            ok &= same_train and changed and back
    print("my B25 hashes (computed before the probe runs):")
    for s in SEEDS:
        print("  seed %-6d %s" % (s, mine[s]))
    sys.stdout.flush()
    if scratch.exists():
        shutil.rmtree(scratch)
    (scratch / "repo").mkdir(parents=True)
    subprocess.run(["git", "-C", str(scratch / "repo"), "init", "-q"], check=True)
    td = scratch / "test_dir"
    td.mkdir()
    (td / "test_qa.jsonl").write_bytes(jsonl_bytes([{"fact_id": "audit-synthetic-0", "template_id": "AUDIT_SYNTHETIC",
                                                     "question": "Auditor synthetic question, not a TEST row?"}]))
    (td / "general_test.jsonl").write_bytes(jsonl_bytes([{"domain": "audit-synthetic", "doc_id": "a-0", "ids": [1, 2],
                                                          "text": "auditor synthetic window"}]))
    cmd = [py, "-I", "-B", os.path.join(repo, PROBE), str(scratch / "repo"), str(td)] + ["tinysha:%d" % s for s in SEEDS]
    print("$ " + " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(scratch),
                       env=dict(os.environ, GIT_CONFIG_NOSYSTEM="1", PYTHONDONTWRITEBYTECODE="1"))
    print("----- probe stdout+stderr -----")
    print(r.stdout + r.stderr, end="")
    print("----- exit %d -----" % r.returncode)
    got = {}
    for ln in r.stdout.splitlines():
        if ln.startswith("tinysha:"):
            op, kind, val = ln.split(" ", 2)
            got[int(op.split(":")[1])] = (kind, val)
    for s in SEEDS:
        k, v = got.get(s, ("MISSING", None))
        same = k == "ACCEPT" and v == mine[s]
        print("  seed %-6d mine %s | probe (train.state_sha256) %s %s | equal %s" % (s, mine[s], k, v, same))
        ok &= same
    print("distinct hashes over the seeds: %d of %d" % (len(set(mine.values())), len(SEEDS)))
    ok &= len(set(mine.values())) == len(SEEDS) and r.returncode == 0
    print(json.dumps({"b25_matches_probe": all(got.get(s, (None, None))[1] == mine[s] for s in SEEDS)}))
    print("note: this script constructs random-initialised Qwen3ForCausalLM(config) models in memory (no from_pretrained, "
          "no weight file read, no download); the generic 'modules' line below comes from ia_common.run")
    return bool(ok)


run(main)
