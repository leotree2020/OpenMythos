"""
Shared pieces of Gate E (PREREGISTRATION.md, revisions 1-2): paths, task
geometry for K statements, the held-out rule of the K=2 task, the model
states, fixed sets and their manifest. Module names carry an e_ prefix so they
never shadow the archived modules this stage imports (gate_d/common.py,
gate_d/runner.py, basic_learn/models.py, gen_gate_a/levels.py, ...).
Nothing here trains or modifies a model.
"""

import hashlib
import json
import os
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, "..")
ROOT = os.path.join(EXP, "..")
for p in (ROOT, os.path.join(EXP, "basic_learn"), os.path.join(EXP, "gen_gate_a"),
          os.path.join(EXP, "budget_a"), os.path.join(EXP, "gate_d")):
    if p not in sys.path:
        sys.path.append(p)

from models import build  # noqa: E402
from common import param_hash  # noqa: E402  (gate_d/common.py, archived)

ARMS = ("openmythos", "transformer")
LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
SETS = os.path.join(HERE, "sets")
RUNS = os.path.join(HERE, "runs")
BRIDGE = os.path.join(RUNS, "bridge")
BUDGET = os.path.join(EXP, "budget_a", "runs")

# PREREGISTRATION 2.1 / 9.6
K2_SEEDS = (1, 2, 3, 4, 5)
K2_STEPS = (0, 25, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000, 3000,
            4500, 6000, 9000, 12000)
BRIDGE_SEEDS = (1, 2, 3)
BRIDGE_STEPS = (0, 25, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000, 3000)
K2_TRAIN_RNG_BASE = 60_000


class Geom:
    """Positions of a K-statement direct-lookup prompt 'a=3;b=7;|b?'."""

    def __init__(self, K):
        self.K = K
        self.L = 4 * K + 3  # input length (answer excluded)
        self.Q_POS = 4 * K + 1
        self.READ_POS = 4 * K + 2
        self.VAR_POS = tuple(4 * j for j in range(K))
        self.EQ_POS = tuple(4 * j + 1 for j in range(K))
        self.DIGIT_POS = tuple(4 * j + 2 for j in range(K))


# ---------------------------------------------------------------- held-out rule


def statements(body):
    """'a=3;b=7;' -> [('a', '3'), ('b', '7')] in order of appearance."""
    assert len(body) % 4 == 0, body
    return [(body[i], body[i + 2]) for i in range(0, len(body), 4)]


def body_key(body):
    """Unordered set of statements: both statement orders share one key."""
    return ";".join(sorted(f"{v}={d}" for v, d in statements(body)))


def is_heldout(body):
    """PREREGISTRATION 1.2: sha256(key) mod 10 == 0 (about 10% of bodies)."""
    return int(hashlib.sha256(body_key(body).encode()).hexdigest(), 16) % 10 == 0


# ---------------------------------------------------------------- states


def state_name(arm, K, seed, step):
    return f"K{K}_{arm}_s{seed}_step{step}"


def all_states():
    out = [(a, 2, s, t) for a in ARMS for s in K2_SEEDS for t in K2_STEPS]
    out += [(a, 4, s, t) for a in ARMS for s in BRIDGE_SEEDS for t in BRIDGE_STEPS]
    return out


def ckpt_path(arm, K, seed, step):
    """Saved checkpoint of a state (None: step 0 of the bridge is rebuilt)."""
    if K == 2:
        return os.path.join(RUNS, f"K2_{arm}_s{seed}_step{step}.pt")
    if step == 0:
        return None
    if step == 3000:
        return os.path.join(BRIDGE, f"A_{arm}_s{seed}.pt")  # final file of train_level.py
    return os.path.join(BRIDGE, f"A_{arm}_s{seed}_step{step}.pt")


def rebuild_init(arm, K, seed):
    torch.manual_seed(seed)
    return build(arm, K)


def load_state(arm, K, seed, step, path=None):
    """Model in eval mode; checkpoint fields are checked against the state."""
    path = path or ckpt_path(arm, K, seed, step)
    if path is None:
        model = rebuild_init(arm, K, seed)
    else:
        ck = torch.load(path, map_location="cpu", weights_only=False)
        assert ck["arm"] == arm and ck["seed"] == seed, (path, ck["arm"], ck["seed"])
        if "step" in ck:
            assert ck["step"] == step, (path, ck["step"], step)
        if "K" in ck:
            assert ck["K"] == K, (path, ck["K"], K)
        model = build(arm, K)
        model.load_state_dict(ck["model"])
    model.eval()
    return model


# ---------------------------------------------------------------- sets


def load_set(name):
    """Rows of a frozen set, checked against sets/manifest.json."""
    text = open(os.path.join(SETS, f"{name}.jsonl")).read()
    want = json.load(open(os.path.join(SETS, "manifest.json")))[name]["sha256"]
    if hashlib.sha256(text.encode()).hexdigest() != want:
        raise RuntimeError(f"{name} does not match its manifest hash")
    return [json.loads(line) for line in text.splitlines()]


def encode(prompts, g):
    x = torch.tensor([list(p.encode()) for p in prompts], dtype=torch.long)
    assert x.shape[1] == g.L and bool((x[:, g.READ_POS] == ord("?")).all())
    return x


def family_tensors(rows, g):
    """rows: one per body with 'body', 'queries' (K letters in statement-slot
    order), 'answers' (K digits). Returns x (KN, L) body-major, y (KN,),
    slot (KN,), body index (KN,), roots (N, K) digit bytes."""
    K = g.K
    prompts, ys, slots, bid, roots = [], [], [], [], []
    for i, r in enumerate(rows):
        for k in range(K):
            prompts.append(r["body"] + "|" + r["queries"][k] + "?")
            ys.append(ord(r["answers"][k]))
            slots.append(k)
            bid.append(i)
        roots.append([ord(d) for d in r["answers"]])
    return (encode(prompts, g), torch.tensor(ys), torch.tensor(slots), torch.tensor(bid),
            torch.tensor(roots))


def atomic_write_json(path, obj, **kw):
    """Write JSON to a temporary file in the same directory, fsync, then rename
    (PREREGISTRATION 12.4.5): an interruption never leaves a half-written file
    under the final name."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".{os.path.basename(path)}.tmp.{os.getpid()}")
    with open(tmp, "w") as f:
        json.dump(obj, f, **kw)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_torch_save(obj, path):
    d = os.path.dirname(os.path.abspath(path))
    tmp = os.path.join(d, f".{os.path.basename(path)}.tmp.{os.getpid()}")
    with open(tmp, "wb") as f:
        torch.save(obj, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, torch.Tensor):
        return o.tolist()
    if hasattr(o, "tolist"):
        return o.tolist()
    if isinstance(o, float) and o != o:
        return None
    return o


__all__ = ["param_hash"]
