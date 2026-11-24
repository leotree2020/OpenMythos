"""IB-4 (implementation stage B, task 4): training inputs and order, built by me and compared with the Executor's dump
(audit_dump_b.json keys training_sequences, batch_schedule, anchor_docs, lr_factor).

Training sequences (protocol section 0 "训练输入", 7 "序列"): for train_F, train_S, train_Y (my regeneration, file
order): encode(text, add_special_tokens=False) + [151643].
Order / anchor / lr: the readings B1-B3 written by the Executor in src/metrix_e1/interpretations.py (read as text, not
imported), implemented here by me:
  B3  epochs e = 1..20; r = rng_rule(TRAIN_SEED, "order:<e>"); p = list(range(N)); r.shuffle(p); batches of epoch e are
      p[0:B], p[B:2B], ...; rows indexed in corpus file order; global steps s = 1..300 (N = 120, B = 8; N = 240, B = 16)
  B1  step s = 1..300 uses anchor documents (4s + i) mod 512, i = 0..3 (documents numbered 0..511 in file order)
  B2  lr(s)/peak = s/15 for s <= 15; for s >= 15: 0.1 + 0.9 * 0.5 * (1 + cos(pi * (s - 15) / (300 - 15)))
Compared for seeds 101, 202, 303.  The protocol sentences behind B1-B3 are printed from the freeze commit, and the
alternative readings are computed (informational only) to show which choices change the numbers.
Data Auditor's own script; no Executor code imported, called or copied.  Loads the tokenizer only.
usage: python -I ib_04_training.py <repo_root> <qwen_tok_dir> <my_out_dir> <audit_dump_b.json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, math
from collections import Counter
from ia_common import rng_rule, frozen_json, frozen_protocol, read_jsonl, load_qwen, enc, run

EOT = 151643
SEEDS = [101, 202, 303]
EPOCHS, STEPS_PER_EPOCH, TOTAL, WARMUP, FLOOR, NDOC = 20, 15, 300, 15, 0.1, 512


def schedule(seed, n, b, epochs=range(1, EPOCHS + 1)):
    out, s = [], 0
    for e in epochs:
        r = rng_rule(seed, f"order:{e}")
        p = list(range(n))
        r.shuffle(p)
        for j in range(0, n, b):
            s += 1
            out.append([s, e, p[j:j + b]])
    return out


def lr_factor(s):
    if s <= WARMUP:
        return s / WARMUP
    return FLOOR + (1 - FLOOR) * 0.5 * (1 + math.cos(math.pi * (s - WARMUP) / (TOTAL - WARMUP)))


def main():
    repo, qdir, mine, dump_path = sys.argv[1:5]
    ok = True
    dump = json.load(open(dump_path, encoding="utf-8"))
    ss = frozen_json(repo, "SEARCH_SPACE.json")["training_contract"]
    print("freeze-commit SEARCH_SPACE training_contract:", {k: ss[k] for k in ("epochs", "batch_size_statements", "steps_per_epoch",
                                                                             "total_steps", "example_order", "warmup", "scheduler", "training_seeds")})
    ok &= (ss["epochs"], ss["batch_size_statements"], ss["steps_per_epoch"], ss["total_steps"], ss["training_seeds"]) == (EPOCHS, 8, 15, 300, SEEDS)
    proto = frozen_protocol(repo).split("\n")
    print("protocol sentences (freeze commit):")
    for ln in proto:
        if any(k in ln for k in ("| 顺序 |", "| warmup |", "| scheduler |", "| batch |", "| Y 的训练量 |", "| 训练量 |", "第 s 步使用第", "| 序列 |", "| 训练输入 |")):
            print("  " + ln.strip()[:400])
    tok = load_qwen(qdir)

    print("\n== training sequences: encode(text) + [151643], file order")
    corp = {"train_F.jsonl": [r["text"] for r in json.load(open(os.path.join(mine, "train_F.json"), encoding="utf-8"))],
            "train_S.jsonl": [r["text"] for r in read_jsonl(os.path.join(mine, "train_S.jsonl"))],
            "train_Y.jsonl": [r["text"] for r in json.load(open(os.path.join(mine, "train_Y.json"), encoding="utf-8"))]}
    ex_ts = dump["training_sequences"]
    print("dump training_sequences keys:", sorted(ex_ts), "| == mine:", sorted(ex_ts) == sorted(corp))
    ok &= sorted(ex_ts) == sorted(corp)
    special = set(tok.all_special_ids)
    for name, texts in corp.items():
        seqs = [enc(tok, t) + [EOT] for t in texts]
        ex = ex_ts.get(name, [])
        diff = [i for i, (a, b) in enumerate(zip(seqs, ex)) if a != b]
        inner_special = sum(bool(special & set(s[:-1])) for s in seqs)
        print(f"  {name}: mine {len(seqs)} | Executor {len(ex)} | differing sequences {len(diff)} {diff[:3]} | tokens incl. <|endoftext|> "
              f"{sum(map(len, seqs))} | max length {max(map(len, seqs))} | every sequence ends with 151643 {all(s[-1] == EOT for s in ex)} "
              f"| special ids before the last position {inner_special}")
        ok &= len(seqs) == len(ex) and not diff and inner_special == 0
    print(f"  F / S fact tokens (incl. <|endoftext|>): {sum(len(enc(tok, t)) + 1 for t in corp['train_F.jsonl'])} / "
          f"{sum(len(enc(tok, t)) + 1 for t in corp['train_S.jsonl'])} (protocol 7: F, L, A, S have the same fact-token count)")
    ok &= sum(len(enc(tok, t)) for t in corp["train_F.jsonl"]) == sum(len(enc(tok, t)) for t in corp["train_S.jsonl"])

    print("\n== batch schedule (B3)")
    ex_bs = dump["batch_schedule"]
    print("dump batch_schedule keys:", sorted(ex_bs))
    want_keys = sorted(f"{s}:{n}:{b}" for s in SEEDS for n, b in ((120, 8), (240, 16)))
    ok &= sorted(ex_bs) == want_keys
    for seed in SEEDS:
        for n, b in ((120, 8), (240, 16)):
            k = f"{seed}:{n}:{b}"
            m = schedule(seed, n, b)
            ex = ex_bs.get(k, [])
            diff = [i for i, (x, y) in enumerate(zip(m, ex)) if list(x) != [y[0], y[1], list(y[2])]]
            per_epoch_ok = all(sorted(i for st in m if st[1] == e for i in st[2]) == list(range(n)) for e in range(1, EPOCHS + 1))
            sizes = Counter(len(st[2]) for st in m)
            print(f"  seed {seed}, {n} rows, batch {b}: steps mine {len(m)} | Executor {len(ex)} | differing steps {len(diff)} {diff[:2]} "
                  f"| step numbers 1..300 {[st[0] for st in ex] == list(range(1, TOTAL + 1))} | each epoch a permutation {per_epoch_ok} "
                  f"| batch sizes {dict(sizes)} | step 1 batch {m[0][2]}")
            ok &= len(m) == TOTAL == len(ex) and not diff and per_epoch_ok and sizes == Counter({b: TOTAL})
    f101, s101 = schedule(101, 120, 8), None
    print("  (F, L, A, S at the same seed use the same 120-row index order; S rows are permuted answers of the same i)")

    print("\n== anchor documents (B1)")
    ex_ad = dump["anchor_docs"]
    m_ad = {str(s): [(4 * s + i) % NDOC for i in range(4)] for s in range(1, TOTAL + 1)}
    d = [s for s in m_ad if ex_ad.get(s) != m_ad[s]]
    use = Counter(x for v in m_ad.values() for x in v)
    print(f"steps mine {len(m_ad)} | Executor {len(ex_ad)} | same step keys {sorted(ex_ad, key=int) == sorted(m_ad, key=int)} | differing steps {len(d)} {d[:3]}")
    print(f"step 1 {m_ad['1']} | step 127 {m_ad['127']} | step 128 {m_ad['128']} | step 300 {m_ad['300']} | uses per document {dict(sorted(Counter(use.values()).items()))}")
    ok &= len(ex_ad) == TOTAL and not d

    print("\n== learning-rate factor lr(s)/peak (B2)")
    ex_lr = dump["lr_factor"]
    m_lr = {str(s): lr_factor(s) for s in range(1, TOTAL + 1)}
    exact = [s for s in m_lr if ex_lr.get(s) != m_lr[s]]
    mad = max(abs(ex_lr[s] - m_lr[s]) for s in m_lr if s in ex_lr)
    print(f"steps mine {len(m_lr)} | Executor {len(ex_lr)} | same keys {sorted(ex_lr, key=int) == sorted(m_lr, key=int)} | not bit-identical {len(exact)} {exact[:5]} | max |diff| {mad:.3e}")
    for s in ("1", "2", "14", "15", "16", "150", "299", "300"):
        print(f"  s {s:>3}: mine {m_lr[s]!r} | Executor {ex_lr.get(s)!r}")
    mono = all(m_lr[str(s)] < m_lr[str(s + 1)] for s in range(1, WARMUP)) and all(m_lr[str(s)] > m_lr[str(s + 1)] for s in range(WARMUP, TOTAL))
    print(f"increasing on 1..15, decreasing on 15..300: {mono} | lr(15) == 1: {m_lr['15'] == 1.0} | lr(300) == 0.1: {abs(m_lr['300'] - 0.1) < 1e-15}")
    ok &= len(ex_lr) == TOTAL and mad <= 1e-12 and mono

    print("\n== alternative readings (informational, not compared with anything)")
    alt_e0 = schedule(101, 120, 8, epochs=range(0, EPOCHS))
    print(f"  epochs numbered 0..19 ('order:0'..'order:19'): seed 101 step 1 batch {alt_e0[0][2]} (B3 reading: {f101[0][2]}); "
          f"steps with a different batch {sum(a[2] != b[2] for a, b in zip(alt_e0, f101))} / 300")
    alt_samp = []
    for e in range(1, EPOCHS + 1):
        alt_samp += [rng_rule(101, f"order:{e}").sample(range(120), 120)]
    print(f"  permutation by r.sample(range(120), 120) instead of r.shuffle(list(range(120))): epoch 1 first batch {alt_samp[0][:8]} "
          f"| same as shuffle {alt_samp[0][:8] == f101[0][2]}")
    alt_ad0 = {s + 1: [(4 * s + i) % NDOC for i in range(4)] for s in range(0, TOTAL)}
    print(f"  steps numbered 0..299 for the anchor rule: first step docs {alt_ad0[1]} (B1: {m_ad['1']}); steps with different docs "
          f"{sum(alt_ad0[s] != m_ad[str(s)] for s in range(1, TOTAL + 1))} / 300")
    hf = [k / WARMUP if k < WARMUP else FLOOR + (1 - FLOOR) * 0.5 * (1 + math.cos(math.pi * (k - WARMUP) / (TOTAL - WARMUP))) for k in range(TOTAL)]
    print(f"  0-based warmup (first step at lr 0, peak at the 16th step): first 3 factors {hf[:3]} | 15th {hf[14]} | 16th {hf[15]} | last {hf[-1]:.6f} "
          f"(B2: {m_lr['1']:.6f}, {m_lr['2']:.6f}, {m_lr['3']:.6f} | 15th {m_lr['15']} | last {m_lr['300']:.6f})")
    return bool(ok)


run(main)
