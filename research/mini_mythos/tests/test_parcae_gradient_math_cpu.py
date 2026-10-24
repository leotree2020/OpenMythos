"""F2-C B1 discovery harness. Standalone. Not B2 confirmation.

PENDING CHATGPT REVIEW. Does not modify Parcae.
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
SEED = 42
HS = (1e-3, 1e-2)


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
    model = Parcae(cfg).float().cpu().eval()
    return model


def native_loss(model, ids, labels, pair):
    torch.manual_seed(SEED)
    out = model(ids, labels=labels, return_logits=True, num_steps_pair=torch.tensor(pair))
    return out["loss"], out["logits"]


def scalar_grad(model, ids, labels, pair, name, index):
    model.zero_grad(set_to_none=True)
    loss, logits = native_loss(model, ids, labels, pair)
    loss.backward()
    param = dict(model.named_parameters())[name]
    return float(loss.detach()), logits.detach().clone(), float(param.grad.view(-1)[index])


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
            "step": step.detach().clone(),
            "total": total.detach().clone(),
        })
        return out

    model.update_recurrent_state = wrapped
    try:
        torch.manual_seed(SEED)
        model(ids, labels=labels, return_logits=True, num_steps_pair=torch.tensor((1, 1)))
    finally:
        model.update_recurrent_state = orig
    return captured


def suffix_forward(model, x1, pack, ids, labels):
    model._current_input_ids = ids
    step = torch.tensor(1)
    total = torch.tensor(2)
    x = model.core_block_forward(x1, pack["embeds"], pack["freqs"], pack["mask"], step, total)
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


def perturb(param, index, delta):
    with torch.no_grad():
        flat = param.view(-1)
        old = flat[index].detach().clone()
        flat[index] = old + delta
    return old


def restore(param, index, old):
    with torch.no_grad():
        param.view(-1)[index] = old


def fd_native(model, ids, labels, pair, name, index, h):
    param = dict(model.named_parameters())[name]
    base = param.view(-1)[index].detach().clone()
    try:
        perturb(param, index, h)
        plus = param.view(-1)[index].detach().clone()
        lp, _ = native_loss(model, ids, labels, pair)
        restore(param, index, base)
        perturb(param, index, -h)
        minus = param.view(-1)[index].detach().clone()
        lm, _ = native_loss(model, ids, labels, pair)
    finally:
        restore(param, index, base)
    hp = float(plus - base)
    hm = float(base - minus)
    sep = float(plus - minus)
    return float(lp), float(lm), hp, hm, sep


def aux64():
    def f(x):
        return x ** 3 + torch.sin(x)

    x = torch.tensor(0.7, dtype=torch.float64, requires_grad=True)
    y = f(x)
    y.backward()
    ad = float(x.grad)
    rows = []
    ok = True
    for h in (1e-4, 1e-3):
        fd = float((f(x.detach() + h) - f(x.detach() - h)) / (2 * h))
        err = abs(ad - fd)
        bound = 1e-5 + 1e-3 * max(abs(ad), abs(fd))
        passed = math.isfinite(fd) and err <= bound
        ok = ok and passed
        rows.append({"h": h, "ad": ad, "fd": fd, "err": err, "bound": bound, "status": "PASS" if passed else "FAIL"})
    return {"item": "AUX64", "status": "PASS" if ok else "FAIL", "rows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parcae-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.parcae_root).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    head = git_out(root, "rev-parse", "HEAD").strip()
    status = git_out(root, "status", "--porcelain")
    if head != PINNED or status.strip():
        payload = {"status": "BLOCKED", "head": head, "status": status}
        out.write_text(json.dumps(payload, indent=2))
        print(json.dumps(payload, indent=2))
        return 2

    model = make_model(root)
    torch.manual_seed(SEED)
    ids = torch.randint(0, 128, (1, 8))
    labels = ids.clone()
    params = sum(p.numel() for p in model.parameters())
    l1, _ = native_loss(model, ids, labels, (0, 2))
    l2, _ = native_loss(model, ids, labels, (0, 2))
    repeat_ok = float(l1) == float(l2)
    results = []
    if not repeat_ok:
        results.append({"item": "baseline repeat", "status": "BLOCKED"})
    else:
        results.append({"item": "baseline repeat", "status": "PASS", "loss": float(l1)})

    model.zero_grad(set_to_none=True)
    loss_full, _ = native_loss(model, ids, labels, (0, 2))
    loss_full.backward()
    full = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}
    model.zero_grad(set_to_none=True)
    loss_t, _ = native_loss(model, ids, labels, (1, 1))
    loss_t.backward()
    trunc = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}

    core_names = [n for n in full if n.startswith("transformer.core_block.")]
    candidates = []
    for name in core_names:
        delta = (full[name] - trunc[name]).abs().view(-1)
        g = full[name].abs().view(-1)
        score = delta.clone()
        score[g <= 1e-3] = 0
        index = int(score.argmax())
        candidates.append({
            "name": name,
            "index": index,
            "value": float(dict(model.named_parameters())[name].view(-1)[index]),
            "g_full": float(full[name].view(-1)[index]),
            "g_tbptt": float(trunc[name].view(-1)[index]),
            "abs_delta": float(delta[index]),
        })
    candidates.sort(key=lambda r: r["abs_delta"], reverse=True)
    selected = []
    seen = set()
    for row in candidates:
        tensor = row["name"]
        if tensor in seen:
            continue
        if abs(row["g_full"]) <= 1e-3:
            continue
        selected.append(row)
        seen.add(tensor)
        if len(selected) == 3:
            break

    aux = aux64()
    results.append(aux)
    discovery = []
    for row in selected:
        name, index = row["name"], row["index"]
        checks = []
        signal_any = False
        for h in HS:
            lp, lm, hp, hm, sep = fd_native(model, ids, labels, (0, 2), name, index, h)
            asym = abs(hp - hm) / max((hp + hm) / 2, 1e-12)
            signal = abs(lp - lm) >= 16 * max(ulp32(lp), ulp32(lm))
            distinct = hp > 0 and hm > 0
            fd = (lp - lm) / sep
            ad = row["g_full"]
            err = abs(ad - fd)
            bound = 1e-3 + 1e-2 * max(abs(ad), abs(fd))
            status = "INCONCLUSIVE"
            if not distinct or asym > 0.01:
                status = "INCONCLUSIVE"
            elif not signal:
                status = "INCONCLUSIVE"
            elif not math.isfinite(fd):
                status = "FAIL"
            elif err <= bound:
                status = "EXPLORATORY PASS"
                signal_any = True
            else:
                status = "DISCREPANCY"
                signal_any = True
            checks.append({
                "h": h, "lp": lp, "lm": lm, "hp": hp, "hm": hm, "sep": sep,
                "asym": asym, "signal": signal, "fd": fd, "ad": ad, "err": err,
                "bound": bound, "status": status,
            })
        fds = [c["fd"] for c in checks if c["signal"]]
        unstable = False
        if len(fds) == 2:
            gap = abs(fds[0] - fds[1])
            bounds = [c["bound"] for c in checks]
            unstable = gap > sum(bounds)
        discovery.append({
            **row,
            "checks": checks,
            "signal_any": signal_any,
            "unstable": unstable,
            "negative": row["abs_delta"] > 1e-2,
            "status": "INCONCLUSIVE" if not signal_any or unstable else "DISCOVERY RECORDED",
        })

    captured = capture_x1(model, ids, labels)
    recon = {"item": "suffix reconstruction", "status": "BLOCKED", "reason": "capture failed"}
    if len(captured) >= 1:
        x1 = captured[0]["out"]
        pack = captured[0]
        model.zero_grad(set_to_none=True)
        sl, slogits = suffix_forward(model, x1, pack, ids, labels)
        sl.backward()
        native_l, native_logits = native_loss(model, ids, labels, (1, 1))
        model.zero_grad(set_to_none=True)
        native_l.backward()
        native_grads = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}
        model.zero_grad(set_to_none=True)
        sl, slogits = suffix_forward(model, x1, pack, ids, labels)
        sl.backward()
        suffix_grads = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}
        logit_diff = float((native_logits - slogits).abs().max())
        loss_diff = abs(float(native_l) - float(sl))
        loss_bound = 1e-6 + 1e-6 * max(abs(float(native_l)), abs(float(sl)))
        grad_rows = []
        grad_ok = True
        for row in selected:
            gn = float(native_grads[row["name"]].view(-1)[row["index"]])
            gs = float(suffix_grads[row["name"]].view(-1)[row["index"]])
            bound = 1e-6 + 1e-5 * max(abs(gn), abs(gs))
            ok = abs(gn - gs) <= bound
            grad_ok = grad_ok and ok
            grad_rows.append({"name": row["name"], "index": row["index"], "native": gn, "suffix": gs, "ok": ok})
        passed = logit_diff <= 1e-6 and loss_diff <= loss_bound and grad_ok
        recon = {
            "item": "suffix reconstruction",
            "status": "PASS" if passed else "SUFFIX RECONSTRUCTION FAIL / NOT VALIDATED",
            "logit_max_abs": logit_diff,
            "loss_abs": loss_diff,
            "loss_bound": loss_bound,
            "grads": grad_rows,
        }
    results.append(recon)
    results.extend(discovery)
    negative = [r for r in discovery if r["negative"]]
    results.append({
        "item": "negative discovery",
        "status": "RECORDED" if negative else "INCONCLUSIVE",
        "count": len(negative),
        "threshold": 1e-2,
    })

    payload = {
        "review": "PENDING CHATGPT REVIEW",
        "stage": "B1 discovery only",
        "params": params,
        "seed": SEED,
        "input_sha256": checksum(ids),
        "env": {
            "python": sys.version.split()[0],
            "pytorch": torch.__version__,
            "cpu": platform.machine(),
            "threads": torch.get_num_threads(),
            "parcae_head": head,
            "parcae_status": status,
        },
        "results": results,
        "selected": discovery,
        "overall": "PENDING CHATGPT REVIEW",
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
