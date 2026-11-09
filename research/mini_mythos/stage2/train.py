#!/usr/bin/env python3
"""Stage 2 fine-tuning without any mechanism: C-LoRA (rank-r adapters on all attention/MLP
linears, base frozen) or C-Full (all parameters). Parcae's own regime: bf16 autocast, recurrence
8 steps with gradients through the last 4, best-fit packed rows, no BOS/EOS. Then evaluates the
dev windows exactly like the Stage 1 baseline (FP32, CPU-seeded h0).

  python -B train.py --mode lora --lr 3e-4 --seed 0 --out RUN
  python -B train.py ... --stop-after-step 100      # simulate an interruption (checkpoint, exit 3)
  python -B train.py ... --resume                   # continue from RUN/ckpt.pt

Exit codes: 0 done, 3 stopped on request (resume to continue).
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gpu_common as G  # noqa: E402


def parse():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["lora", "full"], required=True)
    p.add_argument("--lr", type=float, required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--data", required=True, help="Stage 1 data dir with train_tokens.u16")
    p.add_argument("--sets", required=True, help="Stage 1 eval_sets.jsonl")
    p.add_argument("--upstream", default=G.s0.DEFAULTS["upstream"])
    p.add_argument("--model-dir", default=G.s0.DEFAULTS["model_dir"])
    p.add_argument("--tokenizer", default=G.s0.DEFAULTS["tokenizer"])
    p.add_argument("--device", default="cuda")
    p.add_argument("--precision", choices=["bf16", "fp32"], default="bf16")
    p.add_argument("--tokens", type=int, default=20_000_000, help="training token budget")
    p.add_argument("--seq-len", type=int, default=1024)
    p.add_argument("--micro-batch", type=int, default=8)
    p.add_argument("--global-batch", type=int, default=32, help="rows per optimizer step")
    p.add_argument("--steps-pair", default="4,4", help="recurrence steps without,with gradient")
    p.add_argument("--rank", type=int, default=8)
    p.add_argument("--alpha", type=float, default=16)
    p.add_argument("--warmup", type=float, default=0.05)
    p.add_argument("--min-lr-ratio", type=float, default=0.1)
    p.add_argument("--clip", type=float, default=1.0)
    p.add_argument("--ckpt-every", type=int, default=100)
    p.add_argument("--stop-after-step", type=int, default=0)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--no-eval", action="store_true")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--no-pin-check", action="store_true")
    return p.parse_args()


def lr_at(step, total, base, warmup, min_ratio):
    w = max(1, int(total * warmup))
    if step < w:
        return base * (step + 1) / w
    t = (step - w) / max(1, total - w)
    return base * (min_ratio + (1 - min_ratio) * 0.5 * (1 + math.cos(math.pi * t)))


def main():
    args = parse()
    torch = G.setup(args.device, args.threads)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.global_batch % args.micro_batch:
        raise SystemExit("global batch must be a multiple of the micro batch")
    accum = args.global_batch // args.micro_batch
    steps = args.tokens // (args.global_batch * args.seq_len)
    config = {k: v for k, v in vars(args).items() if k not in ("resume", "stop_after_step", "no_eval")}
    config.update(total_steps=steps, accum=accum)
    cfg_path = out / "config.json"
    if cfg_path.exists():
        old = json.loads(cfg_path.read_text())
        if {k: old["config"].get(k) for k in config} != config:
            raise SystemExit("run directory holds a different configuration")
    if steps < 1:
        raise SystemExit("token budget smaller than one optimizer step")

    model, state = G.load_model(torch, args.upstream, args.model_dir, args.tokenizer, args.device,
                                pin_check=not args.no_pin_check)
    for p in model.parameters():
        p.requires_grad_(args.mode == "full")
    lora = None
    if args.mode == "lora":
        lora = G.LoRA(torch, model, rank=args.rank, alpha=args.alpha, seed=args.seed)
        params = lora.parameters()
        named = lora.params
    else:
        named = dict(model.named_parameters())
        params = list(named.values())
    trainable = sum(p.numel() for p in params)
    opt = torch.optim.AdamW(params, lr=args.lr, betas=(0.9, 0.95), eps=1e-8, weight_decay=0.0)

    tokens, lengths = G.load_train_corpus(args.data)
    rows = G.pack_rows(tokens, lengths, args.seq_len + 1, seed=args.seed, max_rows=steps * args.global_batch)
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

    pair = torch.tensor([int(x) for x in args.steps_pair.split(",")], dtype=torch.long)
    dev_type = args.device.split(":")[0]
    use_amp = args.precision == "bf16"
    log = open(out / "train_log.jsonl", "a", encoding="utf-8")
    if args.device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    for step in range(start, steps):
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
        opt.step()
        opt.zero_grad(set_to_none=True)
        if args.device.startswith("cuda"):
            torch.cuda.synchronize()
        dt = time.time() - t_step
        log.write(json.dumps({"step": step, "loss": total_loss, "lr": lr, "grad_norm": gnorm, "seconds": dt,
                              "tokens_per_s": args.global_batch * args.seq_len / dt}) + "\n")
        log.flush()
        if step % 50 == 0 or step == steps - 1:
            print("step %d/%d loss %.4f lr %.2e %.0f tok/s" % (step + 1, steps, total_loss, lr,
                                                               args.global_batch * args.seq_len / dt), flush=True)
        if (step + 1) % args.ckpt_every == 0 or step + 1 == steps:
            save(step + 1, ckpt_path)
        if args.stop_after_step and step + 1 == args.stop_after_step and step + 1 < steps:
            save(step + 1, ckpt_path)
            print("STOPPED on request after step %d; rerun with --resume" % (step + 1), flush=True)
            return 3
    log.close()
    torch.save({k: v.detach().cpu() for k, v in named.items()}, out / "final_params.pt")
    peak = torch.cuda.max_memory_allocated() / 2 ** 30 if args.device.startswith("cuda") else None
    summary = {"steps": steps, "train_seconds_this_process": time.time() - t0, "peak_memory_gib": peak,
               "trainable_params": trainable}
    if not args.no_eval:
        windows = G.load_windows(args.sets, "dev")
        t1 = time.time()
        per = G.evaluate(torch, model, windows, args.device)
        summary["eval_seconds"] = time.time() - t1
        G.write_per_window(out / "eval_dev.csv", per, windows)
        summary["dev_domain_mean_nll"] = G.domain_means(per, windows)
    G.s0.write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
