#!/usr/bin/env python3
"""Thermo-B training (README.md): Parcae frozen, LoRA r28 on all attention/MLP linears (the Stage 3a
control), three arms that differ only in how the rank is opened:

  --arm full     rank 28 from the first step (control C)
  --arm expand   ranks 1 -> 2 -> 4 -> 8 -> 16 -> 28 in six equal stages, new components start at 0 (E)
  --arm thermo   as expand, plus annealed gradient noise on the newly opened components (T)

Everything else is the Stage 3a regime with the Stage 3b packing (remainders kept): bf16 autocast,
8 recurrence steps with gradients through the last 4, global batch 32 x 1024, AdamW, 5% warmup then
cosine, clip 1.0, no BOS/EOS. Learning curve: at step 0 and at the end of each of the six stages
(same steps for every arm) the probe windows (by default all dev windows) are scored (FP32, replica
0) and the geometry is measured (report only), in one forward pass; the RNG state is restored
afterwards, so the training itself is not affected. At the end: final_params.pt and the FP32 dev
evaluation (2 replicas), as in Stage 3a. Runs on CPU too (--device cpu); run_thermo_b_cpu.sh sets a
small CPU configuration.

  python -B train.py --arm expand --lr 3e-4 --seed 0 --tokens N --out RUN --data D --sets S
  python -B train.py ... --stop-after-step 100      # simulate an interruption (checkpoint, exit 3)
  python -B train.py ... --resume                   # continue from RUN/ckpt.pt

Exit codes: 0 done, 3 stopped on request, 5 the model at step 0 differs from the native scores.
"""
import argparse
import contextlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "stage2"))
sys.path.insert(0, str(HERE.parent / "stage3b"))
import geometry as GEO  # noqa: E402
import gpu_common as G  # noqa: E402
from packing import pack_rows_keep  # noqa: E402
from rank_lora import RANKS, RankLoRA, Schedule, curve_steps  # noqa: E402

PROBE_PER_DOMAIN = 100         # dev windows per domain used for the geometry probe (all of them)
PROBE_TOKENS = 10              # token vectors per window (fixed positions, same for every run)
PROBE_SEED = 20261109


def parse():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arm", choices=["full", "expand", "thermo"], required=True)
    p.add_argument("--lr", type=float, required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--data", required=True, help="data dir with train_tokens.u16 / train_doc_lengths.i32")
    p.add_argument("--sets", required=True, help="eval_sets.jsonl")
    p.add_argument("--native-dev", help="native per-window dev CSV; step 0 must reproduce replica 0 (<= 1e-6)")
    p.add_argument("--upstream", default=G.s0.DEFAULTS["upstream"])
    p.add_argument("--model-dir", default=G.s0.DEFAULTS["model_dir"])
    p.add_argument("--tokenizer", default=G.s0.DEFAULTS["tokenizer"])
    p.add_argument("--device", default="cuda")
    p.add_argument("--precision", choices=["bf16", "fp32"], default="bf16")
    p.add_argument("--tokens", type=int, required=True, help="training token budget (same for every run)")
    p.add_argument("--seq-len", type=int, default=1024)
    p.add_argument("--micro-batch", type=int, default=8)
    p.add_argument("--global-batch", type=int, default=32, help="rows per optimizer step")
    p.add_argument("--steps-pair", default="4,4", help="recurrence steps without,with gradient")
    p.add_argument("--rank", type=int, default=28)
    p.add_argument("--ranks", default=",".join(str(r) for r in RANKS), help="expand/thermo stage ranks")
    p.add_argument("--alpha", type=float, default=0, help="LoRA alpha; 0 means 2 * rank")
    p.add_argument("--t0", type=float, default=1.0, help="thermo: starting temperature (noise / gradient rms)")
    p.add_argument("--anneal", type=float, default=0.5, help="thermo: fraction of each stage the noise lasts")
    p.add_argument("--warmup", type=float, default=0.05)
    p.add_argument("--min-lr-ratio", type=float, default=0.1)
    p.add_argument("--clip", type=float, default=1.0)
    p.add_argument("--ckpt-every", type=int, default=100)
    p.add_argument("--stop-after-step", type=int, default=0)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--no-eval", action="store_true")
    p.add_argument("--probe-per-domain", type=int, default=PROBE_PER_DOMAIN,
                   help="first N dev windows per domain for the learning curve and the geometry (100 = all)")
    p.add_argument("--dev-per-domain", type=int, default=0,
                   help="final dev evaluation on the first N windows per domain; 0 = all (the plan)")
    p.add_argument("--eval-replicas", type=int, default=2, help="replicas of the final dev evaluation")
    p.add_argument("--probe-tokens", type=int, default=PROBE_TOKENS, help="token vectors per probe window")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--no-pin-check", action="store_true")
    args = p.parse_args()
    if args.alpha == 0:
        args.alpha = 2.0 * args.rank
    return args


def lr_at(step, total, base, warmup, min_ratio):
    w = max(1, int(total * warmup))
    if step < w:
        return base * (step + 1) / w
    t = (step - w) / max(1, total - w)
    return base * (min_ratio + (1 - min_ratio) * 0.5 * (1 + math.cos(math.pi * t)))


def make_schedule(args, steps):
    if args.arm == "full":
        return Schedule("full", steps, max_rank=args.rank)
    ranks = tuple(int(r) for r in args.ranks.split(","))
    t0 = args.t0 if args.arm == "thermo" else 0.0
    return Schedule("expand", steps, ranks=ranks, max_rank=args.rank, t0=t0, anneal=args.anneal)


@contextlib.contextmanager
def rng_preserved(torch, device):
    cpu = torch.get_rng_state()
    cuda = torch.cuda.get_rng_state_all() if device.startswith("cuda") else None
    try:
        yield
    finally:
        torch.set_rng_state(cpu)
        if cuda is not None:
            torch.cuda.set_rng_state_all(cuda)


def probe_windows(windows, per_domain):
    by = {}
    for w in windows:
        lst = by.setdefault(w["domain"], [])
        if len(lst) < per_domain:
            lst.append(w)
    return [w for d in sorted(by) for w in by[d]]


def features(torch, model, windows, device, per_window, depth=8, batch=16):
    """One FP32 pass over `windows` with the replica-0 seeds: the primary-scope NLL of each window,
    computed exactly as gpu_common.evaluate does for replica 0, and the final hidden states (ln_f
    output) at the primary positions. Returns ({domain: {"tokens": [n * per_window, D],
    "windows": [n, D]}} (float64), {doc_id: [nll_rep0]}): `per_window` token
    vectors per window at fixed positions (seeded by the window index, so the same in every run),
    and the mean over the primary positions of each window (one vector per text, as in the
    published intrinsic-dimension studies of language models)."""
    captured = []
    handle = model.transformer.ln_f.register_forward_hook(lambda m, i, o: captured.append(o.detach()))
    tok, win, per = {}, {}, {}
    steps = torch.tensor([depth, 0], dtype=torch.long)
    try:
        with torch.no_grad():
            for k in range(0, len(windows), batch):
                chunk = windows[k:k + batch]
                x = torch.tensor([w["tokens"][:G.WINDOW] for w in chunk], dtype=torch.long, device=device)
                y = torch.tensor([w["tokens"][1:G.WINDOW] for w in chunk], dtype=torch.long, device=device)
                captured.clear()
                with G.cpu_seeded_h0(model, [G.SEED_BASE + 1000 * w["index"] for w in chunk]):
                    logits = model(x, return_logits=True, num_steps_pair=steps)["logits"]
                logp = torch.log_softmax(logits[:, :G.WINDOW - 1].double(), dim=-1)
                nll = -logp.gather(2, y[:, :, None]).squeeze(2)
                if not bool(torch.isfinite(nll).all()):
                    raise RuntimeError("non-finite NLL")
                for w, v in zip(chunk, nll[:, G.PRIMARY].mean(1).tolist()):
                    per[w["doc_id"]] = [v]
                h = captured[-1][:, G.PRIMARY].double()
                for w, hv in zip(chunk, h):
                    idx = torch.randperm(hv.shape[0], generator=torch.Generator().manual_seed(PROBE_SEED + w["index"]))
                    sel = torch.sort(idx[:per_window]).values.to(hv.device)
                    tok.setdefault(w["domain"], []).append(hv[sel])
                    win.setdefault(w["domain"], []).append(hv.mean(0, keepdim=True))
    finally:
        handle.remove()
    return {d: {"tokens": torch.cat(tok[d], 0), "windows": torch.cat(win[d], 0)} for d in tok}, per


def _shape(torch, h, dh):
    """Linear (PR) and nonlinear (TwoNN) dimension of the states h and of the change dh."""
    return {"pr_h": GEO.participation_ratio(torch, h), "twonn_h": GEO.twonn(torch, h)[0],
            "pr_dh": GEO.participation_ratio(torch, dh), "twonn_dh": GEO.twonn(torch, dh)[0],
            "dh_rms": float(dh.pow(2).mean().sqrt()), "points": int(h.shape[0])}


def geometry_record(torch, lora, feats, native):
    rec = {"adapter": GEO.adapter_summary(lora.spectra(torch)), "domains": {}, "pooled": {}}
    doms = sorted(feats)
    for level in ("tokens", "windows"):
        for d in doms:
            rec["domains"].setdefault(d, {})[level] = _shape(torch, feats[d][level], feats[d][level] - native[d][level])
        H = torch.cat([feats[d][level] for d in doms], 0)
        N = torch.cat([native[d][level] for d in doms], 0)
        rec["pooled"][level] = _shape(torch, H, H - N)
    return rec


def read_jsonl(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def main():
    args = parse()
    torch = G.setup(args.device, args.threads)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.global_batch % args.micro_batch:
        raise SystemExit("global batch must be a multiple of the micro batch")
    accum = args.global_batch // args.micro_batch
    steps = args.tokens // (args.global_batch * args.seq_len)
    if steps < 1:
        raise SystemExit("token budget smaller than one optimizer step")
    sched = make_schedule(args, steps)
    n_curve = len(args.ranks.split(","))         # same curve points for every arm
    skip = ("resume", "stop_after_step", "no_eval", "native_dev")
    config = {k: v for k, v in vars(args).items() if k not in skip}
    config.update(total_steps=steps, accum=accum, mode="lora", packing="keep-remainder",
                  schedule=sched.describe(), curve_steps=curve_steps(steps, n_curve))
    cfg_path = out / "config.json"
    if cfg_path.exists():
        old = json.loads(cfg_path.read_text())
        if {k: old["config"].get(k) for k in config} != config:
            raise SystemExit("run directory holds a different configuration")

    model, state = G.load_model(torch, args.upstream, args.model_dir, args.tokenizer, args.device,
                                pin_check=not args.no_pin_check)
    for p in model.parameters():
        p.requires_grad_(False)
    lora = RankLoRA(torch, model, rank=args.rank, alpha=args.alpha, seed=args.seed)
    named = lora.params
    params = lora.parameters()
    trainable = lora.count()
    opt = torch.optim.AdamW(params, lr=args.lr, betas=(0.9, 0.95), eps=1e-8, weight_decay=0.0)

    tokens, lengths = G.load_train_corpus(args.data)
    rows = pack_rows_keep(tokens, lengths, args.seq_len + 1, seed=args.seed, max_rows=steps * args.global_batch)
    if len(rows) < steps * args.global_batch:
        raise SystemExit("training corpus too small for the token budget")
    del tokens

    start = 0
    torch.manual_seed(args.seed)
    ckpt_path = out / "ckpt.pt"
    if args.resume and ckpt_path.exists():
        ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        with torch.no_grad():
            for name, value in ck["params"].items():
                named[name].copy_(value.to(named[name].device))
        opt.load_state_dict(ck["opt"])
        torch.set_rng_state(ck["rng_cpu"])
        if args.device.startswith("cuda"):
            torch.cuda.set_rng_state_all(ck["rng_cuda"])
        start = ck["step"]
        print("resumed at step %d" % start, flush=True)
    if not cfg_path.exists():
        G.s0.write_json(cfg_path, {"config": config, "trainable_params": trainable, "state_check": state,
                                   "environment": G.s0.environment_facts(torch),
                                   "device_name": torch.cuda.get_device_name() if args.device.startswith("cuda") else "cpu"})

    def save(step, path):
        tmp = Path(str(path) + ".tmp")
        payload = {"params": {k: v.detach().cpu() for k, v in named.items()}, "opt": opt.state_dict(),
                   "step": step, "rng_cpu": torch.get_rng_state()}
        if args.device.startswith("cuda"):
            payload["rng_cuda"] = torch.cuda.get_rng_state_all()
        torch.save(payload, tmp)
        tmp.replace(path)

    dev_all = G.load_windows(args.sets, "dev")
    dev = probe_windows(dev_all, args.dev_per_domain) if args.dev_per_domain > 0 else dev_all
    probe = probe_windows(dev_all, args.probe_per_domain)
    curve_path = out / "curve.jsonl"
    done_points = {r["step"] for r in read_jsonl(curve_path)}
    native_feats = {}

    def curve_point(at):
        """Dev scores (replica 0) and geometry on the probe windows after `at` optimizer steps,
        from one forward pass; the RNG state is restored afterwards."""
        if at in done_points or args.no_eval:
            return
        t = time.time()
        with rng_preserved(torch, args.device):
            feats, per = features(torch, model, probe, args.device, args.probe_tokens)
            if not native_feats:                           # mask 0 == native model, exactly
                active = lora.active
                lora.set_rank(0)
                native_feats.update(features(torch, model, probe, args.device, args.probe_tokens)[0])
                lora.set_rank(active)
            geo = geometry_record(torch, lora, feats, native_feats)
        rec = {"step": at, "tokens": at * args.global_batch * args.seq_len, "rank": lora.active,
               "dev_rep0_domain_mean_nll": G.domain_means(per, probe), "curve_windows": len(probe),
               "geometry": geo, "seconds": time.time() - t}
        if at == 0 and args.native_dev:
            ref = G.read_per_window(args.native_dev)
            diff = max(abs(per[w["doc_id"]][0] - ref[w["doc_id"]][0]) for w in probe)
            rec["init_vs_native_max_abs_diff"] = diff
            if diff > 1e-6:
                with open(curve_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
                print("step 0 differs from the native scores: max |diff| %.3g > 1e-6" % diff, flush=True)
                raise SystemExit(5)
        with open(curve_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        done_points.add(at)
        print("curve step %d rank %d dev %s (%.0f s)" % (at, lora.active, json.dumps(
            {k: round(v, 4) for k, v in rec["dev_rep0_domain_mean_nll"].items()}), rec["seconds"]), flush=True)

    points = set(curve_steps(steps, n_curve))
    lora.set_rank(sched.rank(min(start, steps - 1)))
    if start in points:
        curve_point(start)

    pair = torch.tensor([int(x) for x in args.steps_pair.split(",")], dtype=torch.long)
    dev_type = args.device.split(":")[0]
    use_amp = args.precision == "bf16"
    log = open(out / "train_log.jsonl", "a", encoding="utf-8")
    if args.device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    for step in range(start, steps):
        r = sched.rank(step)
        if r != lora.active:
            lora.set_rank(r)
        lr = lr_at(step, steps, args.lr, args.warmup, args.min_lr_ratio)
        for g in opt.param_groups:
            g["lr"] = lr
        t_step = time.time()
        total_loss = 0.0
        for m in range(accum):
            k = step * args.global_batch + m * args.micro_batch
            batch = torch.from_numpy(rows[k:k + args.micro_batch].astype("int64")).to(args.device)
            with torch.autocast(device_type=dev_type, dtype=torch.bfloat16, enabled=use_amp):
                loss = model(batch[:, :-1].contiguous(), labels=batch[:, 1:].contiguous(), num_steps_pair=pair)["loss"]
            if not bool(torch.isfinite(loss)):
                raise SystemExit("non-finite loss at step %d" % step)
            (loss / accum).backward()
            total_loss += float(loss) / accum
        gnorm = float(torch.nn.utils.clip_grad_norm_(params, args.clip))
        temp = sched.temperature(step)
        lo, hi = sched.new_components(step)
        noised = lora.add_gradient_noise(torch, lo, hi, temp, args.seed, step) if temp > 0 else 0
        opt.step()
        opt.zero_grad(set_to_none=True)
        if args.device.startswith("cuda"):
            torch.cuda.synchronize()
        dt = time.time() - t_step
        log.write(json.dumps({"step": step, "loss": total_loss, "lr": lr, "grad_norm": gnorm, "rank": r,
                              "temperature": temp, "noised_entries": noised, "seconds": dt,
                              "tokens_per_s": args.global_batch * args.seq_len / dt}) + "\n")
        log.flush()
        if step % 50 == 0 or step == steps - 1:
            print("step %d/%d rank %d T %.2f loss %.4f lr %.2e %.0f tok/s" % (
                step + 1, steps, r, temp, total_loss, lr, args.global_batch * args.seq_len / dt), flush=True)
        if (step + 1) % args.ckpt_every == 0 or step + 1 == steps:
            save(step + 1, ckpt_path)
        if step + 1 in points:
            curve_point(step + 1)
        if args.stop_after_step and step + 1 == args.stop_after_step and step + 1 < steps:
            save(step + 1, ckpt_path)
            print("STOPPED on request after step %d; rerun with --resume" % (step + 1), flush=True)
            return 3
    log.close()
    if lora.active != args.rank:
        raise SystemExit("schedule did not end at the full rank")
    torch.save({k: v.detach().cpu() for k, v in named.items()}, out / "final_params.pt")
    peak = torch.cuda.max_memory_allocated() / 2 ** 30 if args.device.startswith("cuda") else None
    summary = {"steps": steps, "train_seconds_this_process": time.time() - t0, "peak_memory_gib": peak,
               "trainable_params": trainable, "arm": args.arm}
    if not args.no_eval:
        t1 = time.time()
        per = G.evaluate(torch, model, dev, args.device, replicas=args.eval_replicas)
        summary["eval_seconds"] = time.time() - t1
        G.write_per_window(out / "eval_dev.csv", per, dev)
        summary["dev_domain_mean_nll"] = G.domain_means(per, dev)
    G.s0.write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
