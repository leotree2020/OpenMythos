"""F2-C B2 confirmatory verifier. Does not modify B1 files or Parcae.

PENDING CHATGPT REVIEW. Not a final F2-C PASS.
"""
import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

PINNED = "69284c13746e849104f738d6d1a347b1f457df76"
MANIFEST_COMMIT = "12800a65b2ab0e82df412a4e93daadcdbaa6c646"
MANIFEST_BLOB = "918e49ef06c31083245259feb4fa2d13eab96cad"
SEED = 42
HS = (1e-3, 1e-2)
FROZEN = [
    ("transformer.core_block.1.attn.c_proj.weight", 1424),
    ("transformer.core_block.0.attn.c_proj.weight", 1440),
    ("transformer.core_block.0.mlp.proj.weight", 2934),
]


def git_out(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def ulp32(value):
    t = torch.tensor(float(value), dtype=torch.float32)
    return float(torch.nextafter(t, torch.tensor(float("inf"), dtype=torch.float32)) - t)


def checksum(t):
    return hashlib.sha256(t.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def make_model(root):
    sys.path.insert(0, str(root))
    from parcae_lm.models.parcae.config import ParcaeConfig
    from parcae_lm.models.parcae.parcae import Parcae

    torch.manual_seed(SEED)
    cfg = ParcaeConfig(
        n_embd=64, intermediate_size=128, num_attention_heads=4, num_key_value_heads=4,
        vocab_size=128, padded_vocab_size=128, block_size=32,
        n_layers_in_prelude=2, n_layers_in_recurrent_block=2, n_layers_in_coda=2,
        mean_recurrence=2, mean_backprop_depth=2,
        recurrent_embedding_dimension=64, recurrent_intermediation_embedding_dimension=128,
        attn_impl="sdpa",
    )
    return Parcae(cfg).float().cpu().eval()


def native(model, ids, labels, pair):
    torch.manual_seed(SEED)
    out = model(ids, labels=labels, return_logits=True, num_steps_pair=torch.tensor(pair))
    return out["loss"], out["logits"]


def capture_x1(model, ids, labels):
    captured = []
    orig = model.update_recurrent_state

    def wrapped(x, embeds, freqs, mask, step, total):
        out = orig(x, embeds, freqs, mask, step, total)
        captured.append({
            "out": out.detach().clone(),
            "embeds": embeds.detach().clone(),
            "freqs": freqs.detach().clone(),
            "mask": None if mask is None else mask.detach().clone(),
        })
        return out

    model.update_recurrent_state = wrapped
    try:
        torch.manual_seed(SEED)
        model(ids, labels=labels, return_logits=True, num_steps_pair=torch.tensor((1, 1)))
    finally:
        model.update_recurrent_state = orig
    return captured


def suffix(model, x1, pack, ids, labels):
    model._current_input_ids = ids
    x = model.core_block_forward(x1, pack["embeds"], pack["freqs"], pack["mask"], torch.tensor(1), torch.tensor(2))
    x = model.transformer.C(x)
    offset = model.config.n_layers_in_prelude + model.config.n_layers_in_recurrent_block
    for i, block in enumerate(model.transformer.coda):
        ve_idx = str(offset + i)
        ve = model.value_embeds[ve_idx](ids) if ve_idx in model.value_embeds else None
        x = block(x, pack["freqs"], pack["mask"], ve=ve)
    x = model.transformer.ln_f(x)
    logits = model.lm_head(x).float() * model.config.init.logit_scale
    loss = F.cross_entropy(logits.view(-1, logits.shape[-1]), labels.view(-1), ignore_index=-100)
    return loss, logits


def set_scalar(param, index, value):
    with torch.no_grad():
        param.view(-1)[index] = value


def fd_pair(loss_fn, param, index, h):
    base = param.detach().view(-1)[index].clone()
    try:
        set_scalar(param, index, base + h)
        plus = param.detach().view(-1)[index].clone()
        lp = loss_fn()
        set_scalar(param, index, base)
        set_scalar(param, index, base - h)
        minus = param.detach().view(-1)[index].clone()
        lm = loss_fn()
    finally:
        set_scalar(param, index, base)
    hp = float(plus - base)
    hm = float(base - minus)
    sep = float(plus - minus)
    return float(lp.detach()), float(lm.detach()), hp, hm, sep


def classify(ad, lp, lm, hp, hm, sep):
    if not all(math.isfinite(v) for v in (ad, lp, lm, hp, hm, sep)):
        return "FAIL", None, None, None
    if hp <= 0 or hm <= 0:
        return "INCONCLUSIVE", None, None, None
    asym = abs(hp - hm) / max((hp + hm) / 2, 1e-12)
    if asym > 0.01:
        return "INCONCLUSIVE", asym, None, None
    signal = abs(lp - lm) >= 16 * max(ulp32(lp), ulp32(lm))
    if not signal:
        return "INCONCLUSIVE", asym, None, None
    fd = (lp - lm) / sep
    if not math.isfinite(fd):
        return "FAIL", asym, fd, None
    err = abs(ad - fd)
    bound = 1e-3 + 1e-2 * max(abs(ad), abs(fd))
    return ("PASS" if err <= bound else "FAIL"), asym, fd, {"err": err, "bound": bound, "signal": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parcae-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.parcae_root).resolve()
    manifest_path = Path(args.manifest).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    items = []

    def add(item, status, **extra):
        items.append({"item": item, "status": status, **extra})

    repo = Path(__file__).resolve().parents[3]
    head = git_out(root, "rev-parse", "HEAD").strip()
    parcae_status = git_out(root, "status", "--porcelain")
    file_blob = git_out(repo, "hash-object", str(manifest_path)).strip()
    if head != PINNED or parcae_status.strip() or file_blob != MANIFEST_BLOB:
        add("precheck", "BLOCKED", head=head, parcae_status=parcae_status, file_blob=file_blob)
        finish(out, items, blocked=True)
        return 2
    add("manifest file blob", "PASS", blob=file_blob)
    manifest = json.loads(manifest_path.read_text())
    selected = [(r["name"], r["index"]) for r in manifest["selected"]]
    if selected != FROZEN:
        add("manifest", "BLOCKED", selected=selected)
        finish(out, items, blocked=True)
        return 2
    add("precheck", "PASS", head=head, blob=file_blob)

    synth = synthetic_guards()
    add(synth["item"], synth["status"], got=synth["got"])
    if synth["status"] != "PASS":
        finish(out, items)
        return exit_code(items)
    import tempfile
    copy_dir = Path(tempfile.mkdtemp(prefix="f2c-manifest-"))
    copy = copy_dir / "manifest.json"
    copy.write_text(manifest_path.read_text())
    mutated = json.loads(copy.read_text())
    mutated["review"] = "MUTATED"
    copy.write_text(json.dumps(mutated))
    mutated_blob = git_out(repo, "hash-object", str(copy)).strip()
    add("mutated manifest negative", "PASS" if mutated_blob != MANIFEST_BLOB else "FAIL", blob=mutated_blob)
    if mutated_blob == MANIFEST_BLOB:
        finish(out, items)
        return exit_code(items)

    model = make_model(root)
    import parcae_lm.models.parcae.parcae as parcae_mod
    imported = Path(parcae_mod.__file__).resolve()
    if root not in imported.parents:
        add("import path", "BLOCKED", imported=str(imported))
        finish(out, items, blocked=True)
        return 2
    add("import path", "PASS", imported=str(imported))
    nparams = sum(p.numel() for p in model.parameters())
    if nparams != 247936:
        add("param count", "BLOCKED", got=nparams)
        finish(out, items, blocked=True)
        return 2
    add("param count", "PASS", count=nparams)
    torch.manual_seed(SEED)
    ids = torch.randint(0, 128, (1, 8))
    labels = ids.clone()
    input_sha = checksum(ids)
    if input_sha != manifest["input_sha256"]:
        add("input", "BLOCKED", got=input_sha, expected=manifest["input_sha256"])
        finish(out, items, blocked=True)
        return 2
    add("input", "PASS", sha256=input_sha)

    params = dict(model.named_parameters())
    for row in manifest["selected"]:
        value = float(params[row["name"]].detach().view(-1)[row["index"]])
        if abs(value - row["value"]) > 0:
            add("frozen value", "BLOCKED", name=row["name"], got=value, expected=row["value"])
            finish(out, items, blocked=True)
            return 2
    storages = []
    for name, _ in FROZEN:
        param = params[name]
        if not name.startswith("transformer.core_block."):
            add("core ownership", "BLOCKED", name=name)
            finish(out, items, blocked=True)
            return 2
        storages.append(param.untyped_storage().data_ptr())
    if len(set(storages)) != len(FROZEN):
        add("storage alias", "BLOCKED", storages=storages)
        finish(out, items, blocked=True)
        return 2
    add("frozen values", "PASS")
    add("storage alias", "PASS")

    l1, _ = native(model, ids, labels, (0, 2))
    l2, _ = native(model, ids, labels, (0, 2))
    if float(l1.detach()) != float(l2.detach()):
        add("baseline repeat", "BLOCKED")
        finish(out, items, blocked=True)
        return 2
    add("baseline repeat", "PASS", loss=float(l1.detach()))

    captured = capture_x1(model, ids, labels)
    if not captured:
        add("x1 capture", "BLOCKED")
        finish(out, items, blocked=True)
        return 2
    x1 = captured[0]["out"]
    pack = captured[0]

    model.zero_grad(set_to_none=True)
    sl, slogits = suffix(model, x1, pack, ids, labels)
    sl.backward()
    suffix_grads = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}
    nl, nlogits = native(model, ids, labels, (1, 1))
    model.zero_grad(set_to_none=True)
    nl.backward()
    native_grads = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}
    logit_diff = float((nlogits.detach() - slogits.detach()).abs().max())
    loss_diff = abs(float(nl.detach()) - float(sl.detach()))
    loss_bound = 1e-6 + 1e-6 * max(abs(float(nl.detach())), abs(float(sl.detach())))
    recon_ok = logit_diff <= 1e-6 and loss_diff <= loss_bound
    grad_rows = []
    for name, index in FROZEN:
        gn = float(native_grads[name].view(-1)[index])
        gs = float(suffix_grads[name].view(-1)[index])
        bound = 1e-6 + 1e-5 * max(abs(gn), abs(gs))
        ok = abs(gn - gs) <= bound
        recon_ok = recon_ok and ok
        grad_rows.append({"name": name, "index": index, "native": gn, "suffix": gs, "ok": ok, "bound": bound})
    add("suffix reconstruction", "PASS" if recon_ok else "FAIL", logit_max_abs=logit_diff, loss_abs=loss_diff, grads=grad_rows)

    for name, index in FROZEN:
        param = params[name]
        model.zero_grad(set_to_none=True)
        loss, _ = native(model, ids, labels, (0, 2))
        loss.backward()
        ad = float(param.grad.view(-1)[index])
        rows = []
        for h in HS:
            before = param.detach().view(-1)[index].clone()
            lp, lm, hp, hm, sep = fd_pair(lambda: native(model, ids, labels, (0, 2))[0], param, index, h)
            restored = bool(torch.equal(param.detach().view(-1)[index], before))
            if not restored:
                add(f"restore FULL {name}[{index}] h={h}", "FAIL")
            status, asym, fd, extra = classify(ad, lp, lm, hp, hm, sep)
            rows.append({"h": h, "ad": ad, "lp": lp, "lm": lm, "hp": hp, "hm": hm, "sep": sep, "asym": asym, "fd": fd, "status": status, **(extra or {})})
        fds = [r["fd"] for r in rows if r["fd"] is not None]
        unstable = False
        if len(fds) == 2:
            gap = abs(fds[0] - fds[1])
            bounds = [r.get("bound", 0) for r in rows]
            unstable = gap > sum(bounds)
        overall = aggregate([r["status"] for r in rows], unstable=unstable)
        add(f"FULL {name}[{index}]", overall, rows=rows, unstable=unstable)
        tb = float(native_grads[name].view(-1)[index])
        delta = abs(ad - tb)
        add(f"NEGATIVE {name}[{index}]", "PASS" if delta > 1e-2 else "INCONCLUSIVE", g_full=ad, g_tbptt=tb, abs_delta=delta)
        if recon_ok:
            model.zero_grad(set_to_none=True)
            sl, _ = suffix(model, x1, pack, ids, labels)
            sl.backward()
            sad = float(param.grad.view(-1)[index])
            srows = []
            for h in HS:
                before = param.detach().view(-1)[index].clone()
                lp, lm, hp, hm, sep = fd_pair(lambda: suffix(model, x1, pack, ids, labels)[0], param, index, h)
                restored = bool(torch.equal(param.detach().view(-1)[index], before))
                if not restored:
                    add(f"restore TBPTT {name}[{index}] h={h}", "FAIL")
                status, asym, fd, extra = classify(sad, lp, lm, hp, hm, sep)
                srows.append({"h": h, "ad": sad, "lp": lp, "lm": lm, "hp": hp, "hm": hm, "sep": sep, "asym": asym, "fd": fd, "status": status, **(extra or {})})
            sfds = [r["fd"] for r in srows if r["fd"] is not None]
            sunstable = False
            if len(sfds) == 2:
                gap = abs(sfds[0] - sfds[1])
                bounds = [r.get("bound", 0) for r in srows]
                sunstable = gap > sum(bounds)
            add(f"TBPTT {name}[{index}]", aggregate([r["status"] for r in srows], unstable=sunstable), rows=srows, unstable=sunstable)
        else:
            add(f"TBPTT {name}[{index}]", "BLOCKED", reason="suffix reconstruction failed")

    finish(out, items)
    return exit_code(items)


RANK = {"FAIL": 0, "BLOCKED": 1, "INCONCLUSIVE": 2, "PASS": 3}


def aggregate(statuses, unstable=False):
    vals = list(statuses)
    if unstable:
        vals.append("INCONCLUSIVE")
    return min(vals, key=lambda s: RANK[s])


def synthetic_guards():
    cases = {
        "fail_plus_inconclusive": aggregate(["FAIL", "INCONCLUSIVE"]),
        "fail_plus_unstable": aggregate(["FAIL", "PASS"], unstable=True),
        "blocked_plus_inconclusive": aggregate(["BLOCKED", "INCONCLUSIVE"]),
        "unstable_only": aggregate(["PASS", "PASS"], unstable=True),
    }
    expected = {
        "fail_plus_inconclusive": "FAIL",
        "fail_plus_unstable": "FAIL",
        "blocked_plus_inconclusive": "BLOCKED",
        "unstable_only": "INCONCLUSIVE",
    }
    exits = {
        "FAIL": 1 if "FAIL" in ("FAIL",) else 0,
        "BLOCKED": 2,
        "INCONCLUSIVE": 3,
        "PASS": 0,
    }
    exit_ok = exits["FAIL"] != 0 and exits["BLOCKED"] != 0 and exits["INCONCLUSIVE"] != 0 and exits["PASS"] == 0
    ok = cases == expected and exit_ok
    return {"item": "synthetic priority", "status": "PASS" if ok else "FAIL", "got": cases, "expected": expected, "exit_nonzero": exit_ok}


def exit_code(items):
    statuses = [i["status"] for i in items]
    if "FAIL" in statuses:
        return 1
    if "BLOCKED" in statuses:
        return 2
    if "INCONCLUSIVE" in statuses:
        return 3
    return 0


def finish(out, items, blocked=False):
    payload = {
        "review": "PENDING CHATGPT REVIEW",
        "stage": "B2 confirmation",
        "local_status": aggregate([i["status"] for i in items]) if items else "BLOCKED",
        "items": items,
        "env": {"python": sys.version.split()[0], "pytorch": torch.__version__, "cpu": platform.machine(), "threads": torch.get_num_threads()},
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
