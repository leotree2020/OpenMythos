"""Training of the arms F, L, A, S, Y of METRIX E1-PILOT.

Protocol v1.1 section 4 (arms; arm A loss; LoRA of arm L), section 7 (search budget, selection, training contract),
section 8 steps 4-6 (order of the 30 training runs). Every number comes from metrix_e1.contract (frozen files).
Choices the protocol leaves open are listed in metrix_e1.interpretations (B1-B7) and named where they are made.

  arm  corpus          batch  trainable                      loss
  F    train_F.jsonl   8      all parameters                 CE
  L    train_F.jsonl   8      LoRA A, B only (base frozen)   CE
  A    train_F.jsonl   8      all parameters                 CE + lambda * KL(p_base || p_theta) on 4 anchor documents
  S    train_S.jsonl   8      all parameters (F's config)    CE
  Y    train_Y.jsonl   16     all parameters (F's config)    CE
Training input: statement ids + <|endoftext|>; no chat template; right padding to the longest sequence of the batch;
padding excluded from the loss. AdamW, warmup + cosine, global-norm clipping, bf16 autocast with float32 master
weights, 300 steps. Only the final state is kept.

Modes (metrix_e1.mode): formal mode always runs the contract's steps and only on the GPU (RunMode refuses a shortened
count in formal mode); smoke mode runs a chosen shortened number of steps (CPU allowed); preflight mode runs exactly
the protocol's preflight steps of the first configuration (section 8 step 2), on the GPU.
"""
import copy
import hashlib
import math
import time
from dataclasses import dataclass, field

import torch
import torch.nn.functional as Fn

from . import frozen as FZ
from .errors import ImplementationFail, ProtocolStop

ARMS_TRAINED = ("F", "L", "A", "S", "Y")
CORPUS = {"F": "train_F.jsonl", "L": "train_F.jsonl", "A": "train_F.jsonl", "S": "train_S.jsonl", "Y": "train_Y.jsonl"}
ANCHOR_FILE = "anchor_text.jsonl"


class NonFinite(ProtocolStop):
    """Protocol section 11 ST6: a non-finite value in a training run or an evaluation. Stops that run. It carries no
    status: whether the run's configuration is excluded from selection (section 7) or the pilot is
    IMPLEMENTATION_FAIL (selected configuration or a control) is decided by stops.st6 with what the caller knows."""

    def __init__(self, message, values=()):
        super().__init__("ST6", None, message)
        self.values = list(values)


# --------------------------------------------------------------------------------------------- run plan (7, 8)

@dataclass(frozen=True)
class RunSpec:
    arm: str
    config_id: str          # e.g. "F3"; S and Y carry the id of the F configuration they inherit
    config: tuple           # sorted (key, value) pairs of the configuration
    seed: int
    phase: str              # "search" (section 7, seed 101) or "seeds" (the other seeds; S and Y)

    @property
    def cfg(self):
        return dict(self.config)

    @property
    def name(self):
        return "%s-%s-seed%d" % (self.arm, self.config_id, self.seed)


def _cfg(c):
    return tuple(sorted(c.items()))


def search_runs(contract, arm):
    """Section 7: the 6 configurations of arm F, L or A, each trained once with the search seed."""
    if arm not in ("F", "L", "A"):
        raise ValueError("only F, L and A are searched (section 7); got %r" % arm)
    seed = contract.training.search_seed
    return [RunSpec(arm, c["id"], _cfg(c), seed, "search") for c in contract.arms.configs[arm]]


def seed_runs(contract, selected):
    """Section 7 / section 8 step 6, after selection: F, L, A with their selected configuration and the seeds other
    than the search seed (seed 101 is the search run itself); S and Y with the configuration selected for F and all
    three seeds. `selected` maps "F", "L", "A" to the selected config id. S and Y are never searched."""
    by_id = {c["id"]: c for a in ("F", "L", "A") for c in contract.arms.configs[a]}
    for a in ("F", "L", "A"):
        if selected.get(a) not in by_id or not selected[a].startswith(a):
            raise ValueError("selected configuration of %s is %r" % (a, selected.get(a)))
    seeds = contract.training.training_seeds
    out = []
    for a in ("F", "L", "A"):
        c = by_id[selected[a]]
        out += [RunSpec(a, c["id"], _cfg(c), s, "seeds") for s in seeds if s != contract.training.search_seed]
    f = by_id[selected["F"]]
    inherited = _cfg({"id": f["id"], "learning_rate": f["learning_rate"], "weight_decay": f["weight_decay"]})
    for a in contract.arms.inheriting:
        out += [RunSpec(a, f["id"], inherited, s, "seeds") for s in seeds]
    return out


def training_plan(contract, selected):
    """All training runs of section 8 steps 4-6 in order: F search, L search, A search, then seed runs. Returns the
    list; its length must equal counts.total_training_runs (30)."""
    plan = search_runs(contract, "F") + search_runs(contract, "L") + search_runs(contract, "A") + seed_runs(contract, selected)
    if len(plan) != contract.arms.counts["total_training_runs"]:
        raise ImplementationFail("training plan has %d runs, SEARCH_SPACE counts.total_training_runs is %d" % (
            len(plan), contract.arms.counts["total_training_runs"]))
    return plan


def select_config(contract, arm, results):
    """Section 7 selection, DEV only. `results`: one dict per configuration of `arm` with keys config_id,
    learning_rate, acc (Acc(arm, DEV-QA, learned), exact fractions.Fraction or float), dnll (general DEV dNLL),
    finite (False if any loss or score of the run was non-finite). Highest acc; ties: lower dNLL, lower learning rate,
    lower config index; non-finite configurations are excluded. Returns (config_id, ranking)."""
    order = [c["id"] for c in contract.arms.configs[arm]]
    if sorted(r["config_id"] for r in results) != sorted(order):
        raise ValueError("selection of %s needs one result per configuration %s" % (arm, order))
    kept = [r for r in results if r["finite"] and math.isfinite(float(r["acc"])) and math.isfinite(float(r["dnll"]))]
    if not kept:
        raise ImplementationFail("every configuration of %s has a non-finite loss or score" % arm)
    ranking = sorted(kept, key=lambda r: (-r["acc"], r["dnll"], r["learning_rate"], order.index(r["config_id"])))
    return ranking[0]["config_id"], [r["config_id"] for r in ranking]


# --------------------------------------------------------------------------------- order and schedule (7; B1-B3)

def step_numbers(total):
    """B1: optimizer steps are numbered 1..total (used by batch_schedule, hence by train_run)."""
    return range(1, total + 1)


def epoch_batches(n_rows, batch_size, seed, epoch, purpose_template):
    """B3: one permutation of the corpus per epoch from rng_rule(seed, 'order:<epoch>'), epochs numbered from 1;
    consecutive slices of batch_size."""
    if n_rows % batch_size:
        raise ImplementationFail("corpus of %d rows is not a whole number of batches of %d" % (n_rows, batch_size))
    r = FZ.rng_rule(seed, purpose_template.replace("<epoch>", str(epoch)))
    p = list(range(n_rows))
    r.shuffle(p)
    return [p[i:i + batch_size] for i in range(0, n_rows, batch_size)]


def batch_schedule(tr, n_rows, batch_size, seed):
    """[(step, epoch, row indices)] for steps 1..total (B1, B3)."""
    batches = [(e, b) for e in range(1, tr.epochs + 1) for b in epoch_batches(n_rows, batch_size, seed, e, tr.order_purpose)]
    if len(batches) != tr.total_steps:
        raise ImplementationFail("%d rows / batch %d x %d epochs gives %d steps, the contract says %d" % (
            n_rows, batch_size, tr.epochs, len(batches), tr.total_steps))
    return [(s, e, b) for s, (e, b) in zip(step_numbers(tr.total_steps), batches)]


def lr_at(step, peak, tr):
    """B2: linear warmup from 0 over the first warmup_steps steps, then cosine from the peak to final_lr_fraction of the
    peak at final_lr_step."""
    w, end, f = tr.warmup_steps, tr.final_lr_step, tr.final_lr_fraction
    if not 1 <= step <= end:
        raise ValueError("step %d outside 1..%d" % (step, end))
    if step <= w:
        return peak * step / w
    return peak * (f + (1.0 - f) * 0.5 * (1.0 + math.cos(math.pi * (step - w) / (end - w))))


def anchor_docs(step, arms):
    """B1: documents (mul * s + i) mod n, i = 0..i_max, for step s (protocol 2.7)."""
    mul, mod, imax = arms.anchor_schedule
    return [(mul * step + i) % mod for i in range(imax + 1)]


# ------------------------------------------------------------------------------------------------ tensors

def encode_corpus(tok, rows, endoftext_id):
    """Training input (protocol section 0): statement ids (no special tokens added) followed by <|endoftext|>."""
    return [tok.encode(r["text"], add_special_tokens=False) + [endoftext_id] for r in rows]


def pad_right(seqs, pad_id, device):
    """Right padding to the longest sequence; returns (input_ids, attention_mask) as long tensors."""
    n = max(len(s) for s in seqs)
    ids = torch.full((len(seqs), n), pad_id, dtype=torch.long)
    mask = torch.zeros((len(seqs), n), dtype=torch.long)
    for i, s in enumerate(seqs):
        ids[i, :len(s)] = torch.tensor(s, dtype=torch.long)
        mask[i, :len(s)] = 1
    return ids.to(device), mask.to(device)


def token_ce(logits, input_ids, attention_mask):
    """B4: token-weighted cross entropy over every non-padding target position (t >= 2). Logits in float32."""
    logp = torch.log_softmax(logits[:, :-1].float(), dim=-1)
    tgt = input_ids[:, 1:]
    m = attention_mask[:, 1:].to(logp.dtype)
    nll = -logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
    return (nll * m).sum() / m.sum()


def anchor_kl(logits_theta, logits_base, attention_mask):
    """Protocol section 4, arm A: [sum_x sum_{t=2..n_x} KL(p_base(.|x_<t) || p_theta(.|x_<t))] / [sum_x (n_x - 1)].
    Logits position j (0-based) gives the distribution of token j+1 given tokens 0..j, so t = 2..n_x is j = 0..n_x-2,
    i.e. the positions whose next token is a real (non-padding) token: attention_mask[:, 1:]. KL(p || q) =
    sum_v p(v) (log p(v) - log q(v)) with p = p_base, q = p_theta; token-weighted over all documents of the step
    (one division by the total token count, no per-document mean). Float32 (B6)."""
    lt = torch.log_softmax(logits_theta[:, :-1].float(), dim=-1)
    lb = torch.log_softmax(logits_base[:, :-1].float(), dim=-1)
    kl_pos = (lb.exp() * (lb - lt)).sum(-1)
    m = attention_mask[:, 1:].to(kl_pos.dtype)
    return (kl_pos * m).sum() / m.sum()


# --------------------------------------------------------------------------------------------- LoRA (arm L)

def lora_a_init(rank, in_features, rng):
    """B5: LoRA A (rank x in_features), uniform in [-1/sqrt(in_features), 1/sqrt(in_features)], every value drawn
    from `rng` (a random.Random from rng_rule; protocol section 0: all random numbers come from rng_rule) with
    rng.uniform, row by row; float32."""
    bound = 1.0 / math.sqrt(in_features)
    vals = [rng.uniform(-bound, bound) for _ in range(rank * in_features)]
    return torch.tensor(vals, dtype=torch.float64).reshape(rank, in_features).to(torch.float32)


class LoRALinear(torch.nn.Module):
    """y = W x (+ b) + (alpha / r) * B (A x). The wrapped base Linear is frozen; A (r x in) and B (out x r) are the
    only trainable parameters; B starts at 0, so the wrapped layer equals the base layer at step 0; dropout 0 (no
    dropout module). A's initialisation: lora_a_init (B5); `rng` is the random.Random of the module."""

    def __init__(self, base, rank, alpha, rng):
        super().__init__()
        if not isinstance(base, torch.nn.Linear):
            raise TypeError("LoRA wraps torch.nn.Linear, got %s" % type(base).__name__)
        self.base = base
        for p in base.parameters():
            p.requires_grad_(False)
        self.rank, self.alpha, self.scaling = rank, alpha, alpha / rank
        a = lora_a_init(rank, base.in_features, rng)
        dev = base.weight.device
        self.lora_A = torch.nn.Parameter(a.to(dev))
        self.lora_B = torch.nn.Parameter(torch.zeros((base.out_features, rank), dtype=torch.float32, device=dev))

    def forward(self, x):
        return self.base(x) + Fn.linear(Fn.linear(x, self.lora_A), self.lora_B) * self.scaling


def decoder_layers(model):
    return model.model.layers


def apply_lora(model, arms, rank, seed, expect_layers):
    """Freeze every parameter of `model`, then wrap the protocol's target modules of every decoder layer with
    LoRALinear (alpha = alpha_per_rank * rank, dropout 0). `expect_layers`: the protocol's layer count (28) in formal
    mode; None in smoke mode (the small model has fewer layers). Returns the wrapped module paths."""
    if arms.lora_dropout != 0.0:
        raise ImplementationFail("LoRA dropout %r: only dropout 0 is implemented" % arms.lora_dropout)
    layers = decoder_layers(model)
    if expect_layers is not None and len(layers) != expect_layers:
        raise ImplementationFail("model has %d decoder layers; the protocol puts LoRA on all %d" % (len(layers), expect_layers))
    model.requires_grad_(False)
    alpha = arms.lora_alpha_per_rank * rank
    paths = []
    for li, layer in enumerate(layers):
        for name in arms.lora_modules:
            parent = layer.self_attn if name in ("q_proj", "k_proj", "v_proj", "o_proj") else layer.mlp
            path = "model.layers.%d.%s.%s" % (li, "self_attn" if parent is layer.self_attn else "mlp", name)
            setattr(parent, name, LoRALinear(getattr(parent, name), rank, alpha, FZ.rng_rule(seed, "lora_A:%s" % path)))
            paths.append(path)
    return paths


def trainable_parameters(model):
    return [p for p in model.parameters() if p.requires_grad]


def count_trainable(model):
    """Number of trainable scalars (tied embedding / lm_head counted once: parameters() removes duplicates)."""
    return sum(p.numel() for p in trainable_parameters(model))


def make_optimizer(params, tr, peak_lr, weight_decay):
    """AdamW (betas, eps of the contract); weight decay only on 2-D parameters (B7)."""
    decay = [p for p in params if p.ndim == 2]
    other = [p for p in params if p.ndim != 2]
    groups = [{"params": decay, "weight_decay": weight_decay}, {"params": other, "weight_decay": 0.0}]
    return torch.optim.AdamW(groups, lr=peak_lr, betas=tr.betas, eps=tr.eps)


def state_sha256(module):
    """SHA-256 over the state dict of `module` (sorted names; name, dtype, shape and bytes of each tensor)."""
    h = hashlib.sha256()
    sd = module.state_dict()
    for name in sorted(sd):
        t = sd[name].detach().to("cpu").contiguous()
        h.update(name.encode("utf-8") + b"\0" + str(t.dtype).encode() + b"\0" + str(tuple(t.shape)).encode() + b"\0")
        h.update(t.reshape(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()


def params_sha256(named_params):
    """SHA-256 over (name, bytes) of the given (name, tensor) pairs in sorted order."""
    h = hashlib.sha256()
    for name, t in sorted(named_params, key=lambda x: x[0]):
        t = t.detach().to("cpu").contiguous()
        h.update(name.encode("utf-8") + b"\0" + t.reshape(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()


# --------------------------------------------------------------------------------------------- one training run

@dataclass
class RunResult:
    spec: RunSpec
    mode: str
    steps_run: int
    trainable: int
    log: list = field(default_factory=list)          # one dict per step
    frozen_sha256_before: str = None                 # L: base parameters; A: the base copy
    frozen_sha256_after: str = None
    fact_tokens: int = 0
    anchor_tokens: int = 0
    wall_seconds: float = 0.0
    base_trainable: int = None                       # A: parameters of the base copy with requires_grad (must be 0)
    notes: list = field(default_factory=list)


def _finite(x, what, spec, step):
    if not math.isfinite(x):
        raise NonFinite("%s: %s is %r at step %d" % (spec.name, what, x, step), [x])
    return x


def _sync(device):
    """Wait for queued CUDA work so that wall-clock timestamps cover it (no-op on CPU)."""
    if torch.device(device).type == "cuda":
        torch.cuda.synchronize(device)


def make_base_copy(model):
    """Arm A's frozen base copy (protocol section 4: p_base from the weights of arm N, no gradient): a deep copy of the
    model before training, every parameter with requires_grad False, in eval mode."""
    base = copy.deepcopy(model)
    base.requires_grad_(False)
    base.eval()
    if count_trainable(base):
        raise ImplementationFail("the base copy has trainable parameters")
    return base


def prepare_arm(model, spec, contract, mode):
    """Set what is trainable for the arm. F, A, S, Y: every parameter. L: LoRA (base frozen). Returns notes."""
    notes = []
    if spec.arm == "L":
        expect = None if mode.smoke else contract.arms.lora_layers
        if expect is None:
            notes.append("smoke: LoRA layer-count check (all %d layers) skipped; the small model has %d layers" % (
                contract.arms.lora_layers, len(decoder_layers(model))))
        apply_lora(model, contract.arms, spec.cfg["rank"], spec.seed, expect)
    elif spec.arm in ("F", "A", "S", "Y"):
        model.requires_grad_(True)
    else:
        raise ValueError("arm %r is not trained" % spec.arm)
    return notes


def train_run(model, tok, data, spec, contract, mode, device, log_fn=None):
    """Train `model` in place for one run (protocol sections 4 and 7). `data`: dict with the parsed corpus rows
    (data[file name] = list of row dicts) of the generated data directory. Returns RunResult. Raises NonFinite (ST6)
    on a non-finite loss or gradient norm."""
    tr, ar, ev = contract.training, contract.arms, contract.evaluation
    cfg = spec.cfg
    if spec.arm in ("L", "A") and cfg["weight_decay"] != tr.weight_decay_LA:
        raise ImplementationFail("%s: weight decay %r, the contract fixes %r for L and A" % (spec.name, cfg["weight_decay"], tr.weight_decay_LA))
    if not mode.smoke and torch.device(device).type != "cuda":
        raise ImplementationFail("%s mode trains only on the GPU (protocol sections 0 and 7: no model training on CPU)"
                                 % mode.name)
    if mode.preflight and mode.shortened_steps != contract.preflight_steps:
        raise ImplementationFail("preflight runs the protocol's %d steps, not %d" % (contract.preflight_steps,
                                                                                  mode.shortened_steps))
    if mode.preflight and spec != search_runs(contract, "F")[0]:
        raise ImplementationFail("preflight runs the first configuration %s, not %s" % (
            search_runs(contract, "F")[0].name, spec.name))
    steps = mode.steps(tr.total_steps)
    notes = prepare_arm(model, spec, contract, mode)
    params = trainable_parameters(model)
    result = RunResult(spec=spec, mode=mode.name, steps_run=0, trainable=count_trainable(model), notes=notes)
    if spec.arm == "L":
        frozen_named = [(n, p) for n, p in model.named_parameters() if not p.requires_grad]
        result.frozen_sha256_before = params_sha256(frozen_named)
    base = None
    if spec.arm == "A":
        base = make_base_copy(model)
        result.base_trainable = count_trainable(base)
        result.frozen_sha256_before = state_sha256(base)
        anchors = [r["ids"] for r in data[ANCHOR_FILE]]
        if len(anchors) != ar.anchor_n_docs:
            raise ImplementationFail("anchor_text.jsonl has %d documents, the protocol %d" % (len(anchors), ar.anchor_n_docs))
    rows = data[CORPUS[spec.arm]]
    seqs = encode_corpus(tok, rows, ev.endoftext_id)
    bsz = tr.y_batch_size if spec.arm == "Y" else tr.batch_size
    expected_rows = tr.y_sentences if spec.arm == "Y" else tr.n_statements
    if len(seqs) != expected_rows:
        raise ImplementationFail("%s: corpus has %d rows, the contract says %d" % (spec.name, len(seqs), expected_rows))
    schedule = batch_schedule(tr, len(seqs), bsz, spec.seed)
    opt = make_optimizer(params, tr, cfg["learning_rate"], cfg["weight_decay"])
    model.train()
    dev_type = torch.device(device).type
    _sync(device)
    t0 = time.perf_counter()
    for s, epoch, rows_idx in schedule[:steps]:
        lr = lr_at(s, cfg["learning_rate"], tr)
        for g in opt.param_groups:
            g["lr"] = lr
        ids, mask = pad_right([seqs[i] for i in rows_idx], ev.endoftext_id, device)
        with torch.autocast(device_type=dev_type, dtype=torch.bfloat16):
            logits = model(input_ids=ids, attention_mask=mask).logits
        ce = token_ce(logits, ids, mask)
        loss = ce
        entry = {"step": s, "epoch": epoch, "lr": lr, "rows": list(rows_idx), "fact_tokens": int(mask.sum())}
        if spec.arm == "A":
            docs = anchor_docs(s, ar)
            if len(docs) != ar.anchor_docs_per_step:
                raise ImplementationFail("step %d: %d anchor documents, the protocol %d" % (s, len(docs), ar.anchor_docs_per_step))
            a_ids, a_mask = pad_right([anchors[d] for d in docs], ev.endoftext_id, device)
            with torch.no_grad(), torch.autocast(device_type=dev_type, dtype=torch.bfloat16):
                lb = base(input_ids=a_ids, attention_mask=a_mask).logits
            with torch.autocast(device_type=dev_type, dtype=torch.bfloat16):
                lt = model(input_ids=a_ids, attention_mask=a_mask).logits
            kl = anchor_kl(lt, lb, a_mask)
            loss = ce + cfg["anchor_lambda"] * kl
            entry.update({"anchor_docs": docs, "anchor_tokens": int(a_mask.sum()), "kl": _finite(kl.item(), "KL", spec, s)})
            result.anchor_tokens += entry["anchor_tokens"]
        entry["ce"] = _finite(ce.item(), "CE", spec, s)
        entry["loss"] = _finite(loss.item(), "loss", spec, s)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(params, tr.grad_clip_norm)
        entry["grad_norm"] = _finite(float(gn), "gradient norm", spec, s)
        opt.step()
        _sync(device)
        entry["seconds"] = time.perf_counter() - t0
        result.fact_tokens += entry["fact_tokens"]
        result.log.append(entry)
        result.steps_run = s
        if log_fn is not None:
            log_fn(entry)
    result.wall_seconds = time.perf_counter() - t0
    model.eval()
    if spec.arm == "L":
        result.frozen_sha256_after = params_sha256([(n, p) for n, p in model.named_parameters() if not p.requires_grad])
    if base is not None:
        result.frozen_sha256_after = state_sha256(base)
        del base
    if result.frozen_sha256_after != result.frozen_sha256_before:
        raise ImplementationFail("%s: frozen parameters changed during training" % spec.name)
    return result


# ------------------------------------------------------------------------------------------- model loading

def load_model(model_dir, device):
    """The pinned model in float32 from a local snapshot directory (formal mode, on the A100; stage C)."""
    from transformers import AutoModelForCausalLM
    m = AutoModelForCausalLM.from_pretrained(str(model_dir), dtype=torch.float32, attn_implementation="eager",
                                             local_files_only=True)
    return m.to(device).eval()


MODEL_CONFIG_DIR = "qwen_model"


def fetch_model_config(fz, inputs_dir):
    """Download config.json (no weight file) of the pinned model revision into <inputs>/qwen_model/; returns (path,
    sha256). Used to build the protocol architecture on the meta device (parameter counts) and, in stage C, the
    reduced random model of the smoke test."""
    from huggingface_hub import hf_hub_download
    m = fz.data_manifest["model"]
    path = hf_hub_download(m["repo"], "config.json", revision=m["revision"], local_dir=str(inputs_dir) + "/" + MODEL_CONFIG_DIR)
    return path, FZ.file_sha256(path)


def main(argv=None):
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="python -m metrix_e1.train")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("fetch-config")
    a1.add_argument("--inputs", required=True)
    a = ap.parse_args(argv)
    fz = FZ.load()
    path, sha = fetch_model_config(fz, a.inputs)
    print("config.json of %s@%s: %s sha256 %s (not a weight file)" % (
        fz.data_manifest["model"]["repo"], fz.data_manifest["model"]["revision"], path, sha))
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    from ._cli import run_guarded
    run_guarded(main)
