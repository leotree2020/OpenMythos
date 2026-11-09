#!/usr/bin/env python3
"""Stage 3b training, unfrozen: ALL Parcae weights train together with an extra component that
starts at zero - MoDA-P (mechanism, M) or LoRA r28 (control, C). Two learning rates: --lr for the
Parcae weights, --extra-lr for the extra component (same warmup + cosine shape). Packing keeps the
remainders of cropped documents (stage3b/packing.py). Otherwise the Stage 3a regime: bf16 autocast,
8 recurrence steps with gradients through the last 4, no BOS/EOS. Then the FP32 dev evaluation.

  python -B train.py --mode moda --lr 1e-5 --extra-lr 3e-4 --seed 0 --tokens N --out RUN

Writes final_base.pt (Parcae state dict) and final_params.pt (extra component); the training
checkpoint is deleted once the run is finished. Exit codes: 0 done, 3 stopped on request.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "stage3"))
sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402
import mechanisms as M  # noqa: E402
from packing import pack_rows_keep  # noqa: E402


def parse():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["lora", "moda"], required=True)
    p.add_argument("--lr", type=float, required=True, help="learning rate of the Parcae weights")
    p.add_argument("--extra-lr", type=float, required=True, help="learning rate of the extra component")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--data", required=True, help="Stage 1 data dir with train_tokens.u16")
    p.add_argument("--sets", required=True, help="Stage 1 eval_sets.jsonl")
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
    p.add_argument("--alpha", type=float, default=0, help="LoRA alpha; 0 means 2 * rank")
    p.add_argument("--warmup", type=float, default=0.05)
    p.add_argument("--min-lr-ratio", type=float, default=0.1)
    p.add_argument("--clip", type=float, default=1.0)
    p.add_argument("--ckpt-every", type=int, default=200)
    p.add_argument("--keep-ckpt", action="store_true", help="do not delete ckpt.pt at the end")
    p.add_argument("--stop-after-step", type=int, default=0)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--no-eval", action="store_true")
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


def main():
    args = parse()
    torch = G.setup(args.device, args.threads)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.global_batch % args.micro_batch:
        raise SystemExit("global batch must be a multiple of the micro batch")
    accum = args.global_batch // args.micro_batch
    steps = args.tokens // (args.global_batch * args.seq_len)
    config = {k: v for k, v in vars(args).items() if k not in ("resume", "stop_after_step", "no_eval", "keep_ckpt")}
    config.update(total_steps=steps, accum=accum, unfreeze=True, packing="keep-remainder")
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
        p.requires_grad_(True)
    mech = M.attach(torch, model, args.mode, rank=args.rank, alpha=args.alpha, seed=args.seed)
    base = {"base." + n: p for n, p in model.named_parameters()}
    named = {**base, **mech.params}
    params = list(named.values())
    trainable = sum(p.numel() for p in params)
    opt = torch.optim.AdamW([{"params": list(base.values()), "lr": args.lr, "peak": args.lr},
                             {"params": mech.parameters(), "lr": args.extra_lr, "peak": args.extra_lr}],
                            betas=(0.9, 0.95), eps=1e-8, weight_decay=0.0)

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

    pair = torch.tensor([int(x) for x in args.steps_pair.split(",")], dtype=torch.long)
    dev_type = args.device.split(":")[0]
    use_amp = args.precision == "bf16"
    log = open(out / "train_log.jsonl", "a", encoding="utf-8")
    if args.device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    for step in range(start, steps):
        for g in opt.param_groups:
            g["lr"] = lr_at(step, steps, g["peak"], args.warmup, args.min_lr_ratio)
        lr = opt.param_groups[0]["lr"]
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
        log.write(json.dumps({"step": step, "loss": total_loss, "lr": lr, "extra_lr": opt.param_groups[1]["lr"], "grad_norm": gnorm, "seconds": dt,
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
    torch.save({k: v.detach().cpu() for k, v in mech.params.items()}, out / "final_params.pt")
    torch.save({k: v.detach().cpu() for k, v in model.state_dict().items()}, out / "final_base.pt")
    peak = torch.cuda.max_memory_allocated() / 2 ** 30 if args.device.startswith("cuda") else None
    summary = {"steps": steps, "train_seconds_this_process": time.time() - t0, "peak_memory_gib": peak,
               "trainable_params": trainable}
    if not args.no_eval:
        windows = G.load_windows(args.sets, "dev")
        t1 = time.time()
        if args.mode == "moda":
            mech.collect_stats = True
        per = G.evaluate(torch, model, windows, args.device)
        summary["eval_seconds"] = time.time() - t1
        if args.mode == "moda":
            summary["moda_stats_dev"] = mech.summary_stats()
        G.write_per_window(out / "eval_dev.csv", per, windows)
        summary["dev_domain_mean_nll"] = G.domain_means(per, windows)
    G.s0.write_json(out / "summary.json", summary)
    if not args.keep_ckpt and ckpt_path.exists():
        ckpt_path.unlink()
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
