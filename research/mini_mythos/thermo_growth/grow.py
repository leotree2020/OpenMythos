#!/usr/bin/env python3
"""Read books; let the knowledge space grow by itself where reality surprises the model.

Loop, page after page, book after book (reading order, nothing shuffled):
  1. predict: the model reads a chunk; its loss on that chunk, before anything is changed, is the
     surprise (prequential). The native Parcae is scored on the same chunk with the same h0.
  2. refresh: the reads R of the directions already grown are updated from that surprise (AdamW).
  3. grow: at the end of every page the pull of reality is measured in two halves (see
     knowledge_space.py). Mode `auto`: a new direction grows by itself when the reproducible pull
     beats the noise by the temperature T; T cools page by page. Nobody schedules it.
Held-out checks at the start and every few books: the books' own tails (never read), unseen books
(Stage 1 book windows), and the other domains (is the foundation intact?).

Modes (controls): `schedule` grows the same number of directions at evenly spaced pages, along the
same surprise direction (tests the timing); `static` has that many random directions from the start
(tests growing at all). `--k-target` sets the number for both.

  python -B grow.py --mode auto --data BOOKS --sets EVAL_SETS --out RUN --upstream P --model-dir M --tokenizer T

Writes RUN/config.json, read_log.jsonl (per micro-batch), growth.jsonl (per page), evals.jsonl,
final_space.pt and summary.json.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "stage2"))
import books as BK  # noqa: E402
import gpu_common as G  # noqa: E402

CAPTURE = "coda.1.mlp.proj"          # where the tokens behind a new direction are read off


def parse():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["auto", "schedule", "static"], default="auto")
    p.add_argument("--data", required=True, help="books dir from books.py")
    p.add_argument("--sets", required=True, help="Stage 1 eval_sets.jsonl")
    p.add_argument("--out", required=True)
    p.add_argument("--upstream", default=G.s0.DEFAULTS["upstream"])
    p.add_argument("--model-dir", default=G.s0.DEFAULTS["model_dir"])
    p.add_argument("--tokenizer", default=G.s0.DEFAULTS["tokenizer"])
    p.add_argument("--device", default="cpu")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--precision", choices=["bf16", "fp32"], default="bf16")
    p.add_argument("--books", type=int, default=0, help="read only the first N books (0 = all)")
    p.add_argument("--seq-len", type=int, default=512)
    p.add_argument("--micro-batch", type=int, default=2, help="chunks per forward pass")
    p.add_argument("--page", type=int, default=4, help="micro-batches per page (even: two halves)")
    p.add_argument("--steps-pair", default="4,4")
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--warmup", type=int, default=20, help="micro-batches of linear LR warmup")
    p.add_argument("--clip", type=float, default=1.0)
    p.add_argument("--t0", type=float, default=2.0, help="starting temperature (structure / noise needed to grow)")
    p.add_argument("--t-min", type=float, default=1.0)
    p.add_argument("--cool", type=float, default=0.95, help="temperature factor per page")
    p.add_argument("--k-max", type=int, default=256)
    p.add_argument("--k-target", type=int, default=0, help="schedule/static: number of directions")
    p.add_argument("--eval-every", type=int, default=5, help="books between held-out checks")
    p.add_argument("--per-domain", type=int, default=25, help="dev windows per domain for the checks")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--unfreeze", action="store_true",
                   help="Parcae's own weights change too while reading (the native baseline is a frozen copy)")
    p.add_argument("--base-lr", type=float, default=1e-5, help="learning rate of Parcae's weights with --unfreeze")
    p.add_argument("--crystallize", type=int, default=0,
                   help="pages after its birth over which a direction cools: its updates shrink linearly to 0, "
                        "then it is frozen as part of the foundation (0 = never)")
    p.add_argument("--norm-limit", type=float, default=0.0,
                   help="stability guard (0 = off): the hidden state may be at most this many times larger than "
                        "native's on the text being read (penalty above it), and rows on which native itself "
                        "diverges are left out of the anchor")
    p.add_argument("--norm-weight", type=float, default=1.0, help="weight of the hidden-norm penalty")
    p.add_argument("--blow-factor", type=float, default=2.5,
                   help="a row counts as diverged when its largest hidden norm exceeds this many times the median "
                        "of native's rows so far")
    p.add_argument("--anchor", type=float, default=0.0,
                   help="weight of KL(native || model) on the text being read: stay close to what Parcae already "
                        "predicts, change only where reality disagrees (0 = off)")
    p.add_argument("--no-pin-check", action="store_true")
    args = p.parse_args()
    if args.page < 2 or args.page % 2:
        raise SystemExit("--page must be even")
    if args.mode != "auto" and args.k_target < 1:
        raise SystemExit("--k-target is required for schedule/static")
    return args


def temperature(args, page):
    return max(args.t_min, args.t0 * args.cool ** page)


def pages_of(tokens, rows, args):
    """Reading order: book by book, consecutive chunks of seq_len + 1 tokens, grouped into micro-batches
    and pages. Yields (book, page_in_book, [micro-batch arrays])."""
    L = args.seq_len + 1
    for b in rows:
        arr = tokens[b["offset"]:b["offset"] + b["tokens"]]
        n = len(arr) // L
        chunks = arr[:n * L].reshape(n, L)
        mbs = [chunks[i:i + args.micro_batch] for i in range(0, n - args.micro_batch + 1, args.micro_batch)]
        for pg in range(len(mbs) // args.page):
            yield b["book"], pg, mbs[pg * args.page:(pg + 1) * args.page]


def eval_windows(sets, rows, per_domain, heldout=()):
    dev = G.load_windows(sets, "dev")
    by = {}
    for w in dev:
        if len(by.setdefault(w["domain"], [])) < per_domain:
            by[w["domain"]].append(w)
    tails = [{"index": 900000 + 10 * r["book"] + j, "domain": "own-book-%d" % r["book"], "split": "tail",
              "doc_id": "book%d-tail%d" % (r["book"], j), "tokens": t} for r in rows for j, t in enumerate(r["tail"])]
    unseen = [{"index": 950000 + 10 * r["book"] + j, "domain": "heldout-books", "split": "heldout",
               "doc_id": "heldout%d-w%d" % (r["book"], j), "tokens": t} for r in heldout for j, t in enumerate(r["windows"])]
    return [w for d in sorted(by) for w in by[d]] + tails + unseen


def score(torch, model, windows, device, norms=None):
    """Replica-0 NLL per window. If `norms` is a dict, it receives the largest hidden-state norm
    (input of ln_f) of every window."""
    seen = []
    handle = model.transformer.ln_f.register_forward_hook(
        lambda mod, inputs, output: seen.append(inputs[0].detach().float().norm(dim=-1).amax(dim=1)))
    try:
        per = G.evaluate(torch, model, windows, device, replicas=1)
    finally:
        handle.remove()
    if norms is not None:
        flat = torch.cat(seen).tolist()
        norms.update({w["doc_id"]: flat[i] for i, w in enumerate(windows)})
    return {w["doc_id"]: per[w["doc_id"]][0] for w in windows}


def summarize_eval(scores, native, windows, books_read):
    def mean(keys):
        return float(np.mean([scores[k] - native[k] for k in keys])) if keys else None
    out = {"domains": {}}
    for d in ("books", "c4", "fineweb", "wikitext"):
        out["domains"][d] = mean([w["doc_id"] for w in windows if w["domain"] == d])
    out["own_books_read"] = mean([w["doc_id"] for w in windows if w["split"] == "tail"
                                  and int(w["domain"].split("-")[-1]) < books_read])
    out["heldout_books"] = mean([w["doc_id"] for w in windows if w["split"] == "heldout"])
    out["own_books_unread"] = mean([w["doc_id"] for w in windows if w["split"] == "tail"
                                    and int(w["domain"].split("-")[-1]) >= books_read])
    return out


def cool_factor(page, born, crystallize):
    """Step-size factor of a direction: 1 at birth, falling linearly to 0 over `crystallize` pages
    (frozen afterwards); 1 forever when crystallize is 0."""
    if crystallize <= 0:
        return 1.0
    return max(0.0, 1.0 - (page - born) / crystallize)


def blown(row_max, history, factor):
    """Which rows diverged: largest hidden norm above factor x the median native row norm seen so far
    (`history` already includes the current native rows). Returns (list of bool, reference norm)."""
    ref = float(np.median(history)) if len(history) else float("inf")
    return [float(v) > factor * ref for v in row_max], ref


def norm_penalty(torch, mod_norm, nat_norm, limit, keep):
    """Mean over the tokens of the kept rows of relu(log(|h_model| / |h_native|) - log(limit))^2.
    mod_norm, nat_norm: [rows, tokens]; keep: [rows] of 0/1."""
    excess = torch.relu(torch.log(mod_norm / nat_norm.clamp(min=1e-6)) - math.log(limit))
    denom = (keep.sum() * mod_norm.shape[1]).clamp(min=1)
    return (excess.pow(2) * keep[:, None]).sum() / denom


def retention(path):
    """Book by book: the gain on its held-out tail right after reading it, and after all books.
    Books forgotten = gain lost; 'kept' = end gain / gain right after (books with a gain > 0.01)."""
    rows = [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]
    if not rows:
        return {}
    end = {int(b): -v for b, v in rows[-1]["per_book"].items()}
    after = {}
    for r in rows:
        for b, v in r["per_book"].items():
            if int(b) == r["books_read"] - 1:
                after[int(b)] = -v
    books = sorted(b for b in after if b in end)
    lost = [after[b] - end[b] for b in books]
    learned = [b for b in books if after[b] > 0.01]
    return {"book_gain_right_after": float(np.mean([after[b] for b in books])) if books else None,
            "book_gain_at_end": float(np.mean([end[b] for b in books])) if books else None,
            "book_gain_lost": float(np.mean(lost)) if lost else None,
            "book_gain_kept_fraction": float(np.mean([end[b] / after[b] for b in learned])) if learned else None}


def main():
    args = parse()
    torch = G.setup(args.device, args.threads)
    import knowledge_space as KS
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tokens, rows = BK.load(args.data)
    if args.books:
        rows = rows[:args.books]
    model, _ = G.load_model(torch, args.upstream, args.model_dir, args.tokenizer, args.device,
                            pin_check=not args.no_pin_check)
    for prm in model.parameters():
        prm.requires_grad_(False)
    native_model = None
    if args.unfreeze:                       # a frozen copy keeps scoring the native Parcae
        import copy
        native_model = copy.deepcopy(model)
        base0 = {n: q.detach().clone() for n, q in model.named_parameters()}
        for prm in model.parameters():
            prm.requires_grad_(True)
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(args.tokenizer))
    ks = KS.KnowledgeSpace(model, k_max=args.k_max)
    groups = [{"params": ks.parameters(), "lr": args.lr, "peak": args.lr}]
    if args.unfreeze:
        groups.append({"params": list(model.parameters()), "lr": args.base_lr, "peak": args.base_lr})
    opt = torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8, weight_decay=0.0)
    trainable = [q for g in groups for q in g["params"]]
    gen = torch.Generator().manual_seed(args.seed)
    plan = list(pages_of(tokens, rows, args))
    n_pages = len(plan)
    grow_at = set()
    if args.mode == "schedule":
        grow_at = {int((i + 1) * n_pages / (args.k_target + 1)) for i in range(args.k_target)}
    born = []                                       # page at which each direction appeared
    if args.mode == "static":
        for _ in range(args.k_target):
            ks.grow(ks.random_direction(gen))
            born.append(0)
    config = dict(vars(args), pages=n_pages, books_read=len(rows), tokens_per_page=args.page * args.micro_batch * args.seq_len,
                  params_per_direction=ks.count(1), schedule_pages=sorted(grow_at))
    G.s0.write_json(out / "config.json", {"config": config, "environment": G.s0.environment_facts(torch)})

    windows = eval_windows(args.sets, rows, args.per_domain, BK.load_heldout(args.data))
    native_norms = {}
    native = score(torch, model, windows, args.device, native_norms)   # k = 0 or reads 0: exactly the native model
    ref_norm = float(np.median(list(native_norms.values())))
    native_diverged = sorted(k for k, v in native_norms.items() if v > args.blow_factor * ref_norm)
    evals = open(out / "evals.jsonl", "w", encoding="utf-8")

    def check(books_read, tokens_read):
        t = time.time()
        norms = {}
        s = score(torch, model, windows, args.device, norms)
        diverged = sorted(k for k, v in norms.items() if v > args.blow_factor * ref_norm)
        rec = {"books_read": books_read, "tokens_read": tokens_read, "k": ks.k, "seconds": time.time() - t,
               "diverged_windows": diverged, "native_diverged_windows": native_diverged,
               "max_hidden_norm_ratio": max(norms[k] / native_norms[k] for k in norms),
               **summarize_eval(s, native, windows, books_read)}
        evals.write(json.dumps(rec) + "\n")
        evals.flush()
        print("check after %d books: k %d own-read %s heldout-books %s stage1-books %s c4 %s wiki %s fineweb %s" % (
            books_read, ks.k, *("%+.4f" % v if v is not None else "-" for v in (
                rec["own_books_read"], rec["heldout_books"], rec["domains"]["books"], rec["domains"]["c4"],
                rec["domains"]["wikitext"], rec["domains"]["fineweb"]))) + " | diverged windows %d (native %d)" % (
                    len(diverged), len(native_diverged)), flush=True)
        return rec

    tail_windows = [w for w in windows if w["split"] == "tail"]
    tails_log = open(out / "tails.jsonl", "w", encoding="utf-8")

    def tails_check(books_read):
        """Every read book's held-out tail, after each book: did earlier books stay learned?"""
        s = score(torch, model, tail_windows, args.device)
        per = {}
        for w in tail_windows:
            per.setdefault(int(w["domain"].split("-")[-1]), []).append(s[w["doc_id"]] - native[w["doc_id"]])
        tails_log.write(json.dumps({"books_read": books_read, "k": ks.k,
                                    "per_book": {b: float(np.mean(v)) for b, v in per.items()}}) + "\n")
        tails_log.flush()

    def cool_directions(before, page_idx):
        """Per-direction step size: 1 at birth, falling linearly to 0 after `crystallize` pages."""
        with torch.no_grad():
            for name, prm in ks.R.items():
                for j in range(ks.k):
                    m = cool_factor(page_idx, born[j], args.crystallize)
                    if m < 1.0:
                        prm[:, j] = before[name][:, j] + m * (prm[:, j] - before[name][:, j])

    check(0, 0)
    pair = torch.tensor([int(x) for x in args.steps_pair.split(",")], dtype=torch.long)
    dev_type = args.device.split(":")[0]
    amp = args.precision == "bf16"
    hid = {}                                        # hidden states (input of ln_f) of the two reading passes
    phase = ["model"]
    model.transformer.ln_f.register_forward_hook(lambda mod, inputs, output: hid.__setitem__(phase[0], inputs[0]))
    if native_model is not None:
        native_model.transformer.ln_f.register_forward_hook(
            lambda mod, inputs, output: hid.__setitem__("native", inputs[0]))
    norm_hist = []                                  # native row norms seen so far
    read_log = open(out / "read_log.jsonl", "w", encoding="utf-8")
    growth_log = open(out / "growth.jsonl", "w", encoding="utf-8")
    events = []
    step, tokens_read, last_book, t0 = 0, 0, rows[0]["book"], time.time()
    for page_idx, (book, pg, mbs) in enumerate(plan):
        if book != last_book:
            tails_check(book - rows[0]["book"])
            if (book - rows[0]["book"]) % args.eval_every == 0:
                check(book - rows[0]["book"], tokens_read)
            last_book = book
        ks.reset_page()
        ks.collect = args.mode in ("auto", "schedule")
        captured_targets = None
        for m, mb in enumerate(mbs):
            ks.half = m % 2
            last = m == len(mbs) - 1
            ks.capture = CAPTURE if last and ks.collect else None
            ks.captured = {}
            batch = torch.from_numpy(mb.astype("int64")).to(args.device)
            x, y = batch[:, :-1].contiguous(), batch[:, 1:].contiguous()
            seed = 1_000_000 * (args.seed + 1) + step
            with torch.no_grad(), torch.autocast(device_type=dev_type, dtype=torch.bfloat16, enabled=amp):
                torch.manual_seed(seed)                 # native Parcae on the same chunk, same h0
                want = args.anchor > 0
                phase[0] = "native"
                if native_model is not None:
                    nat = native_model(x, labels=y, num_steps_pair=pair, return_logits=want)
                else:
                    k_saved, ks.k = ks.k, 0
                    nat = model(x, labels=y, num_steps_pair=pair, return_logits=want)
                    ks.k = k_saved
                phase[0] = "model"
                nat_norm = hid["native"].float().norm(dim=-1)            # [rows, tokens]
                norm_hist.extend(nat_norm.amax(dim=1).tolist())
                nat_blown, ref = blown(nat_norm.amax(dim=1).tolist(), norm_hist, args.blow_factor)
                native_loss = float(nat["loss"])
                native_logp = torch.log_softmax(nat["logits"].float(), -1) if want else None
                del nat
            torch.manual_seed(seed)
            with torch.autocast(device_type=dev_type, dtype=torch.bfloat16, enabled=amp):
                res = model(x, labels=y, num_steps_pair=pair, return_logits=args.anchor > 0)
            loss = res["loss"]
            if not bool(torch.isfinite(loss)):
                raise SystemExit("non-finite loss at step %d" % step)
            mod_norm = hid["model"].float().norm(dim=-1)                 # [rows, tokens], in the graph
            mod_blown = [float(v) > args.blow_factor * ref for v in mod_norm.detach().amax(dim=1)]
            guard = args.norm_limit > 0
            keep = torch.tensor([0.0 if (guard and b) else 1.0 for b in nat_blown], device=mod_norm.device)
            kl, pen = None, None
            total = loss
            if args.anchor > 0:                         # free energy: fit reality + stay near what is known
                logp = torch.log_softmax(res["logits"].float(), -1)
                kl_tok = (native_logp.exp() * (native_logp - logp)).sum(-1)          # [rows, tokens]
                # guard: a row on which native itself diverged is no teacher
                kl = (kl_tok * keep[:, None]).sum() / (keep.sum() * kl_tok.shape[1]).clamp(min=1)
                total = loss + args.anchor * kl
            if guard:                                   # the hidden state must not grow beyond native's
                pen = norm_penalty(torch, mod_norm, nat_norm, args.norm_limit, keep)
                total = total + args.norm_weight * pen
            del res
            total.backward()
            if last and ks.capture:
                captured_targets = y.clone()
            ramp = min(1.0, (step + 1) / max(1, args.warmup))
            for g in opt.param_groups:
                g["lr"] = g["peak"] * ramp
            if ks.k or args.unfreeze:
                torch.nn.utils.clip_grad_norm_(trainable, args.clip)
                before = ({n: q[:, :ks.k].detach().clone() for n, q in ks.R.items()}
                          if args.crystallize and ks.k else None)
                opt.step()
                if before is not None:
                    cool_directions(before, page_idx)
            opt.zero_grad(set_to_none=True)
            tokens_read += x.numel()
            read_log.write(json.dumps({"step": step, "book": book, "page": page_idx, "k": ks.k,
                                       "loss": float(loss), "native": native_loss,
                                       "kl_to_native": float(kl) if kl is not None else None,
                                       "native_norm": float(nat_norm.max()), "model_norm": float(mod_norm.max()),
                                       "native_diverged_rows": int(sum(nat_blown)),
                                       "model_diverged_rows": int(sum(mod_blown)),
                                       "norm_penalty": float(pen) if pen is not None else None,
                                       "tokens_read": tokens_read}) + "\n")
            step += 1
        ks.collect, ks.capture = False, None
        T = temperature(args, page_idx)
        rec = {"page": page_idx, "book": book, "page_in_book": pg, "tokens_read": tokens_read, "T": T, "k_before": ks.k}
        u = None
        if args.mode in ("auto", "schedule"):
            s = ks.surprise()
            if s is not None:
                lam_c, lam_n, top = s
                rec.update(structure=lam_c, noise=lam_n, ratio=lam_c / lam_n if lam_n > 0 else None)
                want = (lam_c > T * lam_n) if args.mode == "auto" else (page_idx in grow_at)
                if want and ks.k < args.k_max:
                    u = ks.grow(top)
                    born.append(page_idx + 1)           # it starts learning on the next page
        rec["grew"] = u is not None
        rec["k"] = ks.k
        if u is not None and CAPTURE in ks.captured and captured_targets is not None:
            g = torch.cat(ks.captured[CAPTURE], 0).double().cpu()                 # [B, T, D]
            s_tok = g @ u                                                          # pull along the new direction
            flat = s_tok.flatten()
            top_idx = torch.topk(flat.abs(), min(12, flat.numel())).indices.tolist()
            tgt = captured_targets.flatten().cpu().tolist()
            rec["tokens_behind"] = [{"token": tok.decode([tgt[i]]), "pull": float(flat[i])} for i in top_idx]
            events.append(rec)
            print("page %d (book %d): grew direction %d  structure/noise %.2f > T %.2f  tokens: %s" % (
                page_idx, book, ks.k, rec["ratio"], T, " ".join(repr(t["token"]) for t in rec["tokens_behind"][:8])),
                flush=True)
        growth_log.write(json.dumps(rec) + "\n")
        growth_log.flush()
        if page_idx % 10 == 0:
            print("page %d/%d book %d k %d T %.2f ratio %s (%.0f tok/s)" % (
                page_idx, n_pages, book, ks.k, T, "%.2f" % rec["ratio"] if rec.get("ratio") is not None else "-",
                tokens_read / (time.time() - t0)), flush=True)
    read_log.close()
    growth_log.close()
    tails_check(len(rows))
    tails_log.close()
    final = check(len(rows), tokens_read)
    evals.close()
    torch.save(ks.state(), out / "final_space.pt")
    drift = None
    if args.unfreeze:                       # how far the foundation itself moved, per part
        acc = {}
        for n, q in model.named_parameters():
            part = n.split(".")[1] if n.startswith("transformer.") else n.split(".")[0]
            a = acc.setdefault(part, [0.0, 0.0])
            a[0] += float((q.detach() - base0[n]).double().pow(2).sum())
            a[1] += float(base0[n].double().pow(2).sum())
        drift = {part: math.sqrt(d / w) if w else None for part, (d, w) in sorted(acc.items())}
        torch.save({n: q.detach().cpu() for n, q in model.state_dict().items()}, out / "final_base.pt")
    logs = [json.loads(x) for x in open(out / "read_log.jsonl", encoding="utf-8")]
    per_book = {}
    for r in logs:
        per_book.setdefault(r["book"], []).append(r["native"] - r["loss"])
    general = [final["domains"][d] for d in ("c4", "wikitext", "fineweb")]
    summary = {"mode": args.mode, "unfreeze": bool(args.unfreeze), "base_lr": args.base_lr if args.unfreeze else None,
               "anchor": args.anchor,
               "forgetting_nats": float(np.mean(general)),
               "forgetting_ppl_pct": 100.0 * (math.exp(float(np.mean(general))) - 1.0),
               "base_relative_change": drift,
               "k_final": ks.k, "trainable_params_final": ks.count(), "tokens_read": tokens_read,
               "pages": n_pages, "growth_pages": [e["page"] for e in events] if args.mode == "auto" else sorted(grow_at),
               "orthonormality_error": KS.orthonormality_error(ks.directions().cpu()),
               "prequential_gain_per_book": {b: float(np.mean(v)) for b, v in per_book.items()},
               "prequential_gain_all": float(np.mean([r["native"] - r["loss"] for r in logs])),
               "prequential_gain_second_half": float(np.mean([r["native"] - r["loss"] for r in logs[len(logs) // 2:]])),
               "final_check": final, "seconds": time.time() - t0,
               "crystallize": args.crystallize, **retention(out / "tails.jsonl"),
               "norm_limit": args.norm_limit,
               "read_chunks": len(logs),
               "read_chunks_native_diverged": sum(1 for r in logs if r["native_diverged_rows"]),
               "read_chunks_model_diverged": sum(1 for r in logs if r["model_diverged_rows"]),
               "read_chunks_model_only_diverged": sum(1 for r in logs if r["model_diverged_rows"] > r["native_diverged_rows"]),
               "final_diverged_windows": final["diverged_windows"],
               "native_diverged_windows": final["native_diverged_windows"]}
    G.s0.write_json(out / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "prequential_gain_per_book"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
