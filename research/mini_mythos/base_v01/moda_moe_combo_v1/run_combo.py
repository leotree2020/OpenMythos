"""Frozen CPU recipe pilot. Existing source/checkpoints are read-only inputs.

The main process trains four small source-MoE residuals; a distinct interpreter
reloads all nine predeclared configurations. This is development/regression,
not a fresh generalization or routing-causality experiment.
"""
from __future__ import annotations
import argparse
import datetime
import gc
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time
import traceback

CONFIGS = (("F", None), ("H", 4101), ("Esolo", 4101), ("HE", 4101),
           ("EjointHoff", 4101), ("H", 4202), ("Esolo", 4202),
           ("HE", 4202), ("EjointHoff", 4202))
ENV = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "1",
       "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false", "CUDA_VISIBLE_DEVICES": "",
       "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
RAW_BYTES, META_BYTES, RESERVE = 8388608, 64 * 1024**2, 256 * 1024**2
MAIN_EXPECTED = dict(model_loads=1, calls_started=783, calls_completed=783,
                     identity_calls=7, train_steps=128, backward_calls=128,
                     optimizer_steps=128, quality_rows=648, full_matrix_audits=648)
RELOAD_EXPECTED = dict(model_loads=1, calls_started=9, calls_completed=9,
                       reload_rows=9, full_matrix_audits=9)
STABLE = ("h0_sha256", "rng_before_sha256", "rng_after_sha256", "seed")


class Stop(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def read(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith(".gz") else b)


def sha(b): return hashlib.sha256(b).hexdigest()


def pin(p):
    h = hashlib.sha256()
    n = 0
    with Path(p).open("rb") as s:
        for b in iter(lambda: s.read(1048576), b""):
            n += len(b)
            h.update(b)
    return dict(bytes=n, sha256=h.hexdigest())


def module(path, name, expected=None):
    path = Path(path)
    if expected is not None and pin(path)["sha256"] != expected:
        raise Stop("FAIL", "Source byte binding: " + str(path))
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


def stable(observer): return {k: observer[k] for k in STABLE}


def key(config, seed): return config if seed is None else config + "_" + str(seed)


def cases(wiki, news):
    result = []
    for domain, data in (("wiki", wiki), ("news", news)):
        for index, sample in enumerate(data["eval"]):
            for seed in (5101, 5202):
                result.append((domain, index, sample, seed))
    return result


def input_tensor(torch, sample):
    """All native call sites require batch1, not a bare token vector."""
    if len(sample["tokens"]) != 129:
        raise Stop("FAIL", "Exactly129 token IDs per frozen window")
    return torch.tensor([sample["tokens"][:128]], dtype=torch.long)


def restored_data(spec, news_rows):
    wiki = read(spec["wiki_data"]["path"])
    news = read(spec["news_data"]["path"])
    if pin(spec["wiki_data"]["path"]) != spec["wiki_data"]["pin"] or pin(spec["news_data"]["path"]) != spec["news_data"]["pin"]:
        raise Stop("FAIL", "Exact frozen data file pins")
    if spec["data_path"] != spec["news_data"]["path"] or news["eval"] != news_rows:
        raise Stop("FAIL", "Inherited loader returns the exact pinned sample list")
    if len(wiki["train"]) != 16 or len(wiki["eval"]) != 16 or len(news["eval"]) != 20:
        raise Stop("FAIL", "Frozen training and domain counts")
    if any(len(row["tokens"]) != 129 or any(type(t) is not int or not 0 <= t < 32768 for t in row["tokens"])
           for row in wiki["train"] + wiki["eval"] + news["eval"]):
        raise Stop("FAIL", "All original129-token windows unchanged")
    return wiki, news


def optimizer_receipt(torch, optimizer, bank, expected_steps):
    rows = {}
    for name, parameter in bank.named_parameters():
        count = expected_steps[name]
        state = optimizer.state.get(parameter)
        if not count:
            if state: raise Stop("FAIL", "Unused parameter unexpectedly has Adam state")
            rows[name] = dict(updates=0, state_present=False)
            continue
        if state is None or set(state) != {"step", "exp_avg", "exp_avg_sq"}:
            raise Stop("FAIL", "Missing/incomplete Adam state " + name)
        if any(not torch.is_tensor(v) or not bool(torch.isfinite(v).all()) for v in state.values()):
            raise Stop("FAIL", "Nonfinite Adam state " + name)
        if float(state["step"]) != count or any(state[k].shape != parameter.shape for k in ("exp_avg", "exp_avg_sq")):
            raise Stop("FAIL", "Adam per-active-parameter step/shape " + name)
        if bool((state["exp_avg_sq"] < 0).any()):
            raise Stop("FAIL", "Negative Adam second moment")
        rows[name] = dict(updates=count, state_present=True, step=float(state["step"]), finite=True)
    return rows


def own_aggregate(rows):
    """Worker aggregation independent of the NumPy auditor implementation."""
    domains = {}
    for domain, count in (("wiki", 16), ("news", 20)):
        means = {}
        for config, seed in CONFIGS:
            selected = [r for r in rows if (r["domain"], r["config"], r["train_seed"]) == (domain, config, seed)]
            if len(selected) != count * 2:
                raise Stop("FAIL", "Worker quality coverage " + domain + "/" + key(config, seed))
            n = count * 128
            correct = sum(r["correct"] for r in selected)
            means[key(config, seed)] = dict(mean_nll=math.fsum(r["nll_sum"] for r in selected) / n,
                                            correct=correct, scored_observations=n, accuracy=correct / n)
        comparisons, screens = {}, {}
        for ref in ("F", "H", "Esolo"):
            title = "HE_vs_" + ref
            passed = []
            for seed in (4101, 4202):
                a, b = means[key("HE", seed)], means[key(ref, None if ref == "F" else seed)]
                dn, da = a["mean_nll"] - b["mean_nll"], a["accuracy"] - b["accuracy"]
                p = dn <= -.01 and da >= -.01
                comparisons[title + "_" + str(seed)] = dict(delta_nll=dn, delta_accuracy=da, screen=p)
                passed.append(p)
            screens[title] = "PASS" if all(passed) else "FAIL"
        domains[domain] = dict(means=means, primary_comparisons=comparisons, scientific_screens=screens)
    return dict(domains=domains)


class Run:
    def __init__(self, spec, out, reload_mode):
        self.spec, self.root, self.reload_mode = spec, Path(out), reload_mode
        self.root.mkdir(exist_ok=False)
        self.public, self.private = self.root / "public", self.root / "private"
        self.public.mkdir()
        self.private.mkdir()
        self.actual = {k: 0 for k in (RELOAD_EXPECTED if reload_mode else MAIN_EXPECTED)}
        self.started = time.perf_counter()
        self.checks, self.rows, self.reload_rows, self.training = [], [], [], []
        self.last_raw, self.last_identity = None, None
        self.model, self.library, self.before = None, None, {}
        self.adapter_before, self.banks, self.new_banks, self.saved = {}, {}, {}, []
        self.training_pairs, self.initial_moe = {}, {}
        self.audit_seconds, self.serialization_seconds = 0., 0.
        self.salvage = False
        self.event = (self.public / "events.jsonl").open("x", encoding="utf-8")
        self.audit_receipts = self.public / "audits"
        self.audit_receipts.mkdir()

    def guard(self, additional=0, raw_write=False):
        base = Path(self.spec["run_root"])
        files = [p for p in base.rglob("*") if p.is_file()]
        total = sum(p.stat().st_size for p in files)
        raw = sum(p.stat().st_size for p in files if p.name in ("final_sentinel.bin", "failed_scored_logits.bin"))
        needed = additional if self.salvage else max(additional, RAW_BYTES + META_BYTES - total)
        limit = META_BYTES if self.salvage else META_BYTES - 65536
        if raw + (additional if raw_write else 0) > RAW_BYTES or total - raw + (0 if raw_write else additional) > limit or shutil_free(base) < needed + RESERVE:
            raise Stop("BLOCKED", "Current evidence allocation or disk reserve unavailable")

    def save(self, name, value):
        p = self.public / name
        p.parent.mkdir(parents=True, exist_ok=True)
        b = (json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if str(p).endswith(".gz"):
            b = gzip.compress(b, compresslevel=9, mtime=0)
        self.guard(len(b))
        with p.open("xb") as stream:
            stream.write(b)

    def check(self, purpose, condition, status="FAIL"):
        item = dict(Purpose=purpose, Expected=True, Actual=bool(condition), Status="PASS" if condition else status)
        self.checks.append(item)
        self.event.write(json.dumps(item, allow_nan=False) + "\n")
        self.event.flush()
        if not condition:
            raise Stop(status, purpose)

    def call(self, runner, ids, seed, **kwargs):
        self.actual["calls_started"] += 1
        result = runner.forward(ids, seed, **kwargs)
        self.actual["calls_completed"] += 1
        return result

    def capture(self, logits, identity):
        b = self.library.raw(logits[0, 64:].contiguous())
        self.check("Current scored matrix layout", len(b) == RAW_BYTES)
        self.last_raw, self.last_identity = b, identity
        return b

    def audit(self, raw, targets, label):
        start = time.perf_counter()
        argv = [self.spec["audit_python"], "-I", "-B", str(Path(__file__).with_name("audit_combo.py")),
                "--stream", "--targets-json", json.dumps(targets, separators=(",", ":"))]
        timed_out = False
        try:
            proc = subprocess.run(argv, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env={**os.environ, **ENV}, timeout=60, cwd=self.spec["repo"])
            stdout_bytes, stderr_bytes, returncode = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout_bytes, stderr_bytes, returncode = exc.stdout or b"", exc.stderr or b"", None
        self.audit_seconds += time.perf_counter() - start
        # Target IDs are private inputs. Neither the argv nor target JSON is published.
        stderr = self.public / "audits" / (label + ".stderr")
        self.guard(len(stderr_bytes))
        with stderr.open("xb") as stream:
            stream.write(stderr_bytes)
        self.save("audits/" + label + "_process.json", dict(returncode=returncode, timed_out=timed_out,
                  timeout_seconds=60, seconds=time.perf_counter()-start, stdout_sha256=sha(stdout_bytes),
                  stdout_bytes=len(stdout_bytes), stderr_sha256=sha(stderr_bytes), stderr_bytes=len(stderr_bytes),
                  targets_sha256=sha(struct.pack("<64q", *targets)), argument_target_ids_redacted=True))
        if timed_out:
            self.save("audits/" + label + "_partial_stdout.json", dict(utf8=stdout_bytes.decode("utf-8", errors="backslashreplace")))
            raise Stop("BLOCKED", "Independent matrix audit timeout " + label)
        try:
            result = json.loads(stdout_bytes)
        except (ValueError, UnicodeError):
            self.save("audits/" + label + "_malformed.json", dict(returncode=returncode, stdout_sha256=sha(stdout_bytes),
                      utf8=stdout_bytes.decode("utf-8", errors="backslashreplace")))
            raise Stop("FAIL", "Malformed independent matrix audit")
        self.save("audits/" + label + ".json.gz", result)
        self.check("Independent full matrix audit " + label, returncode == 0 and result["Status"] == "PASS",
                   status="BLOCKED" if result.get("Status") == "BLOCKED" else "FAIL")
        a = result["Actual"]
        self.check("Audited exact raw identity " + label, a["raw"] == dict(bytes=RAW_BYTES, sha256=sha(raw)) and a["finite_components"] == 2097152)
        self.actual["full_matrix_audits"] += 1
        return result


def shutil_free(path):
    import shutil
    return shutil.disk_usage(path).free


def peak_rss_bytes():
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    except ImportError:
        return None


def initialize(run):
    s = run.spec
    for k, v in ENV.items(): os.environ[k] = v
    loader = module(s["loader"], "frozen_combo_native_loader", "617a0e01b1b904fe543ebcb356dff5e95de1d4effe47f43e014f98dd4cf2e3f5")
    torch, lib, old_runner, news_rows = loader.initialize(run)
    combo = module(Path(__file__).with_name("combo_model.py"), "frozen_combo_model")
    wiki, news = restored_data(s, news_rows)
    run.check("Frozen Wiki training/evaluation inputs", pin(s["wiki_data"]["path"]) == s["wiki_data"]["pin"]
              and len(wiki["train"]) == len(wiki["eval"]) == 16 and all(len(r["tokens"]) == 129 for r in wiki["train"] + wiki["eval"]))
    run.check("Frozen news regression inputs", pin(s["news_data"]["path"]) == s["news_data"]["pin"] and len(news["eval"]) == 20
              and s["data_path"] == s["news_data"]["path"] and news["eval"] == news_rows)
    source = lib.load_source(s["moda_source"])
    return torch, lib, old_runner, combo, source, wiki, news


def clear_graph(runner, bank=None):
    runner.depth_deltas, runner.depth_keys, runner.depth_values = [], [], []
    if bank is not None: bank.reset_records()


def identities(run, torch, lib, old_runner, combo, source, news):
    sample = news["eval"][0]
    ids = input_tensor(torch, sample)
    references = old_baselines(run)
    ref, obs = run.call(old_runner, ids, 5101, banks=None, training=False)
    f = lib.raw(ref)
    raw = run.capture(ref, dict(phase="identity", config="F", domain="news", article_id=sample["id"], eval_seed=5101))
    prior = references["news", "F", None, 5101, sample["id"]]
    run.check("Initial historical native bridge before any training", sha(raw) == prior["logits_sha256"] and stable(obs) == stable(prior["observer"]), status="BLOCKED")
    run.actual["identity_calls"] += 1
    control = [dict(config="F", train_seed=None, full_logits_sha256=sha(f), observer=obs)]
    for seed in (4101, 4202):
        moe = combo.MoEResidual(source, seed=seed)
        run.check("All source MoE parameters train and correct count", sum(p.numel() for p in moe.parameters()) == 187392 and len(list(moe.parameters())) == 16)
        run.initial_moe[seed] = lib.state_hashes(moe)
        runner = combo.NativeCombo(run.model)
        out, o = run.call(runner, ids, 5101, moda=None, moe=moe, training=False)
        run.capture(out, dict(phase="identity", config="Ezero", train_seed=seed))
        run.actual["identity_calls"] += 1
        run.check("Full native/zero-MoE bitwise identity " + str(seed), lib.raw(out) == f and stable(o) == stable(obs))
        control.append(dict(config="Ezero", train_seed=seed, full_logits_sha256=sha(lib.raw(out)), observer=o))
        h = run.banks["depth", seed]
        h_out, h_obs = run.call(old_runner, ids, 5101, banks=h, training=False)
        h_raw = lib.raw(h_out)
        raw = run.capture(h_out, dict(phase="identity", config="Hreference", train_seed=seed, domain="news", article_id=sample["id"], eval_seed=5101))
        prior = references["news", "H", seed, 5101, sample["id"]]
        run.check("Initial historical H bridge before any training " + str(seed), sha(raw) == prior["logits_sha256"] and stable(h_obs) == stable(prior["observer"]), status="BLOCKED")
        run.actual["identity_calls"] += 1
        out, o = run.call(runner, ids, 5101, moda=h, moe=moe, training=False)
        run.capture(out, dict(phase="identity", config="HEzero", train_seed=seed))
        run.actual["identity_calls"] += 1
        run.check("Full frozen-H/zero-MoE bitwise identity " + str(seed), lib.raw(out) == h_raw and stable(o) == stable(h_obs))
        run.check("Zero controls leave every MoE state unchanged", lib.state_hashes(moe) == run.initial_moe[seed])
        control.extend([dict(config="Hreference", train_seed=seed, full_logits_sha256=sha(h_raw), observer=h_obs),
                        dict(config="HEzero", train_seed=seed, full_logits_sha256=sha(lib.raw(out)), observer=o)])
        clear_graph(runner, moe)
        del runner, moe, out, h_out, h_raw
    run.save("identity.json", dict(Status="PASS", rows=control, identity_calls=7, compared_positions=128, compared_vocab=32768,
                                  domain="news", article_index=0, eval_seed=5101, historical_before_training_bridges=3))
    del f, ref
    clear_graph(old_runner)
    gc.collect()


def training(run, torch, lib, combo, source, wiki):
    for seed in (4101, 4202):
        for config in ("Esolo", "HE"):
            name = key(config, seed)
            bank = combo.MoEResidual(source, seed=seed)
            run.check("Paired initial E state " + name, lib.state_hashes(bank) == run.initial_moe[seed])
            h = run.banks["depth", seed] if config == "HE" else None
            parameters = list(bank.parameters())
            optimizer = torch.optim.AdamW(parameters, lr=.001, betas=(.9, .999), eps=1e-8, weight_decay=0., foreach=False)
            run.check("Optimizer membership only full MoE", {id(p) for g in optimizer.param_groups for p in g["params"]} == {id(p) for p in parameters})
            runner = combo.NativeCombo(run.model)
            coverage = {n: False for n, p in bank.named_parameters()}
            update_steps = {n: 0 for n, p in bank.named_parameters()}
            for step in range(32):
                begin = time.perf_counter()
                sample = wiki["train"][step % 16]
                ids = input_tensor(torch, sample)
                target = torch.tensor(sample["tokens"][1:129], dtype=torch.long)
                optimizer.zero_grad(set_to_none=True)
                logits, observer = run.call(runner, ids, 1000000 + 100 * seed + step, moda=h, moe=bank, training=True)
                run.capture(logits, dict(phase="training", config=config, train_seed=seed, step=step, article_id=sample["id"]))
                paired = (seed, step)
                if paired not in run.training_pairs: run.training_pairs[paired] = stable(observer)
                run.check("Training h0 and RNG paired " + name + "/" + str(step), stable(observer) == run.training_pairs[paired])
                loss = torch.nn.functional.cross_entropy(logits.reshape(-1, 32768), target)
                run.check("Finite128-target training loss", bool(torch.isfinite(loss)))
                loss.backward()
                run.actual["backward_calls"] += 1
                gradients = {n: combo.gradient_record(p) for n, p in bank.named_parameters()}
                run.check("Every present MoE parameter gradient finite", all(r["finite"] is not False for r in gradients.values()))
                depth_gradients = [combo.gradient_record(d) for d in runner.depth_deltas]
                run.check("Full32 branch gradients connected and finite", len(depth_gradients) == 32 and all(r["present"] and r["finite"] for r in depth_gradients))
                for n, g in gradients.items(): coverage[n] |= bool(g["present"] and g["nonzero"])
                for n, g in gradients.items(): update_steps[n] += int(g["present"])
                norm = torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True, foreach=False)
                run.check("Nonzero finite total gradient", bool(torch.isfinite(norm)) and float(norm) > 0)
                before = lib.state_hashes(bank)
                optimizer.step()
                run.actual["optimizer_steps"] += 1
                after = lib.state_hashes(bank)
                run.check("Finite nonzero MoE parameter update", all(lib.finite(p) for p in parameters) and before != after)
                run.check("Frozen native and H parameter gradients absent", all(p.grad is None and not p.requires_grad for p in run.model.parameters())
                          and all(p.grad is None and not p.requires_grad for b in run.banks.values() for p in b.parameters()))
                record = dict(config=config, train_seed=seed, step=step, article_id=sample["id"], targets=128,
                              loss=float(loss.detach()), observer=observer, gradient_norm_before_clip=float(norm),
                              parameter_gradients=gradients, per_depth_gradients=depth_gradients,
                              routing=runner.route_records, updated_state=after, endpoint_step_seconds=time.perf_counter() - begin)
                run.training.append(record)
                run.save("steps/" + name + "_" + str(step).zfill(2) + ".json.gz", record)
                run.actual["train_steps"] += 1
                print(json.dumps(dict(phase="training", config=config, train_seed=seed, step=step + 1,
                                      training_steps=run.actual["train_steps"], quality_rows=0)), flush=True)
                optimizer.zero_grad(set_to_none=True)
                clear_graph(runner, bank)
                del logits, loss
                run.guard()
            run.check("Base state unchanged after training " + name, lib.state_hashes(run.model) == run.before)
            run.check("All old adapters unchanged after training " + name, {key(a, s): lib.state_hashes(b) for (a, s), b in run.banks.items()} == run.adapter_before)
            adam = optimizer_receipt(torch, optimizer, bank, update_steps)
            run.save("optimizer_" + name + ".json", dict(Status="PASS", parameters=adam, optimizer_steps=32,
                     unused_experts_are_allowed=True))
            checkpoint = dict(config=config, train_seed=seed, steps=32, state_dict=bank.state_dict(), optimizer=optimizer.state_dict(),
                              rng_state=torch.get_rng_state(), freeze_commit=run.spec["freeze_commit"],
                              source_sha256=run.spec["moda_source_sha256"], inputs_sha256=run.spec["wiki_data"]["pin"]["sha256"],
                              total_parameters=187392, MoDA_updated=False)
            path = run.private / (name + ".pt")
            buffer = io.BytesIO()
            torch.save(checkpoint, buffer)
            encoded = buffer.getvalue()
            run.check("Complete adapter/Adam/RNG archive within measured2.5MiB cap", len(encoded) <= 2621440, status="BLOCKED")
            run.guard(len(encoded))
            with path.open("xb") as s: s.write(encoded)
            run.saved.append(dict(config=config, train_seed=seed, path="private/" + path.name, pin=pin(path),
                                  final_state=lib.state_hashes(bank), nonzero_gradient_parameter_coverage=coverage))
            bank.eval()
            bank.requires_grad_(False)
            run.new_banks[config, seed] = bank
            del optimizer, checkpoint, buffer, encoded, runner
            gc.collect()
    run.save("adapters.json", dict(rows=run.saved, optimizer_steps=128, source_parameters_per_run=187392))


def components(run, config, seed):
    h = run.banks["depth", seed] if config in ("H", "HE") else None
    e = run.new_banks.get(("HE" if config == "EjointHoff" else config, seed)) if config not in ("F", "H") else None
    return h, e


def eval_endpoint(run, torch, lib, runner, sample, seed, h, e):
    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
    ids = input_tensor(torch, sample)
    targets = torch.tensor(sample["tokens"][1:129], dtype=torch.long)
    logits, observer = run.call(runner, ids, seed, moda=h, moe=e, training=False)
    values = logits[0, 64:].detach().double()
    target = targets[64:]
    peak = values.max(-1).values
    gold = values.gather(1, target[:, None]).squeeze(1)
    nll = peak - gold + torch.log(torch.exp(values - peak[:, None]).sum(-1))
    predictions = values.argmax(-1)
    metrics = dict(nll_sum=float(nll.sum()), nll_mean=float(nll.mean()), correct=int((predictions == target).sum()), target_count=64,
                   worker_per_token=dict(nll=nll.tolist(), predictions=predictions.tolist()))
    endpoint_wall, endpoint_cpu = time.perf_counter_ns() - wall, time.process_time_ns() - cpu
    return logits, observer, metrics, endpoint_wall, endpoint_cpu


def old_baselines(run):
    result = {}
    for domain, path in (("wiki", run.spec["old_evaluation_path"]), ("news", run.spec["v7_evaluation_path"])):
        rows = read(path)["rows"]
        for row in rows:
            arm = row.get("arm")
            if arm not in ("fixed32", "depth"): continue
            config = "F" if arm == "fixed32" else "H"
            result[domain, config, row.get("train_seed"), row["eval_seed"], row["article_id"]] = row
    return result


def evaluation(run, torch, lib, combo, wiki, news):
    reference = old_baselines(run)
    runner = combo.NativeCombo(run.model)
    paired = {}
    bridge_count = 0
    for case, (domain, article_index, sample, h0) in enumerate(cases(wiki, news)):
        for slot in range(9):
            config, seed = CONFIGS[(case + slot) % 9]
            h, e = components(run, config, seed)
            logits, observer, metrics, wall, cpu = eval_endpoint(run, torch, lib, runner, sample, h0, h, e)
            row = dict(domain=domain, config=config, train_seed=seed, eval_seed=h0, article_id=sample["id"],
                       article_index=article_index, case_index=case, slot=slot, row_index=len(run.rows), observer=observer,
                       endpoint_wall_ns=wall, endpoint_cpu_ns=cpu, **metrics)
            raw = run.capture(logits, {k: row[k] for k in ("domain", "config", "train_seed", "eval_seed", "article_id")})
            row["logits_sha256"] = sha(raw)
            target_ids = sample["tokens"][65:129]
            row["targets_sha256"] = sha(struct.pack("<64q", *target_ids))
            row["shape"], row["dtype"] = [64, 32768], "float32-le"
            pair = (domain, article_index, h0)
            if pair not in paired: paired[pair] = stable(observer)
            run.check("All nine candidates paired actual h0/RNG", stable(observer) == paired[pair])
            if config in ("F", "H"):
                old = reference[domain, config, seed, h0, sample["id"]]
                old_hash = old.get("logits_sha256", old.get("raw_logits_sha256", old.get("raw_sha256")))
                run.check("Historical F/H output bridge " + str(len(run.rows)), old_hash == row["logits_sha256"] and stable(old["observer"]) == stable(observer), status="BLOCKED")
                bridge_count += 1
            label = "row_" + str(len(run.rows)).zfill(3)
            audit = run.audit(raw, target_ids, label)
            columns = audit["Actual"]["columns"]
            run.check("Independent per-token prediction/NLL " + label,
                      columns["predictions"] == row["worker_per_token"]["predictions"]
                      and max(abs(a-b) for a, b in zip(columns["nll"], row["worker_per_token"]["nll"])) <= 1e-10)
            row["audit_receipt"] = "audits/" + label + ".json.gz"
            row["routing"] = runner.route_records
            run.rows.append(row)
            run.actual["quality_rows"] += 1
            print(json.dumps(dict(phase="evaluation", domain=domain, config=config, train_seed=seed,
                                  quality_rows=run.actual["quality_rows"], training_steps=128)), flush=True)
            clear_graph(runner, e)
            del logits
    run.check("All216 original F/H predictions bridged", bridge_count == 216)
    run.save("baseline_bridges.json", dict(Status="PASS", exact_rows=216, additional_forward_calls=0))
    run.save("evaluation.json.gz", dict(rows=run.rows))
    run.save("results.json", own_aggregate(run.rows))


def reload_validation(run, torch, lib, combo, source, news):
    main = Path(run.spec["run_root"]) / "worker"
    saved = read(main / "public/adapters.json")["rows"]
    for row in saved:
        path = main / row["path"]
        run.check("Reload checkpoint bytes", pin(path) == row["pin"])
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        run.check("Reload frozen checkpoint identity", checkpoint["freeze_commit"] == run.spec["freeze_commit"]
                  and checkpoint["steps"] == 32 and checkpoint["total_parameters"] == 187392)
        bank = combo.MoEResidual(source, seed=row["train_seed"])
        bank.load_state_dict(checkpoint["state_dict"], strict=True)
        bank.requires_grad_(False)
        bank.eval()
        run.check("Reload exact new adapter state", lib.state_hashes(bank) == row["final_state"])
        run.new_banks[row["config"], row["train_seed"]] = bank
        del checkpoint
    refs = read(main / "public/evaluation.json.gz")["rows"]
    sample = news["eval"][0]
    runner = combo.NativeCombo(run.model)
    for index, (config, seed) in enumerate(CONFIGS):
        reference = [r for r in refs if r["domain"] == "news" and r["article_index"] == 0 and r["eval_seed"] == 5101
                     and (r["config"], r["train_seed"]) == (config, seed)]
        run.check("Unique predeclared reload reference", len(reference) == 1)
        reference = reference[0]
        h, e = components(run, config, seed)
        logits, observer, metrics, _, _ = eval_endpoint(run, torch, lib, runner, sample, 5101, h, e)
        raw = run.capture(logits, dict(phase="reload", config=config, train_seed=seed, eval_seed=5101, article_id=sample["id"]))
        run.check("New interpreter full-matrix/h0 reproduction " + str(index), sha(raw) == reference["logits_sha256"] and observer == reference["observer"])
        audit = run.audit(raw, sample["tokens"][65:129], "reload_" + str(index))
        row = dict(config=config, train_seed=seed, eval_seed=5101, article_id=sample["id"], observer=observer,
                   logits_sha256=sha(raw), reference_row_index=reference["row_index"], **metrics)
        run.reload_rows.append(row)
        run.actual["reload_rows"] += 1
        if index == 8:
            run.check("Frozen final sentinel identity", config == "EjointHoff" and seed == 4202)
            run.guard(RAW_BYTES, raw_write=True)
            path = run.private / "final_sentinel.bin"
            with path.open("xb") as stream: stream.write(raw)
            run.save("sentinel.json", dict(identity=run.last_identity, raw=pin(path), audit="audits/reload_8.json.gz"))
        clear_graph(runner, e)
        del logits
    run.save("reload.json", dict(Status="PASS", rows=run.reload_rows, quality_rows_added=0, new_interpreter=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    spec = read(args.spec)
    run = Run(spec, args.out, args.reload)
    status, error, preservation = "NOT TESTED", None, "NOT TESTED"
    def interrupted(signum, frame): raise Stop("BLOCKED", "Interrupted by signal " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        torch, lib, old_runner, combo, source, wiki, news = initialize(run)
        if args.reload:
            reload_validation(run, torch, lib, combo, source, news)
        else:
            identities(run, torch, lib, old_runner, combo, source, news)
            training(run, torch, lib, combo, source, wiki)
            evaluation(run, torch, lib, combo, wiki, news)
        expected = RELOAD_EXPECTED if args.reload else MAIN_EXPECTED
        run.check("Complete frozen worker count inventory", run.actual == expected)
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED" if isinstance(exc, (OSError, MemoryError, KeyboardInterrupt, subprocess.SubprocessError)) else "FAIL")
        error = dict(type=type(exc).__name__, reason=str(exc), traceback=traceback.format_exc())
    finally:
        run.salvage = status != "PASS"
        if status != "PASS" and run.last_raw is not None:
            try:
                path = run.private / "failed_scored_logits.bin"
                if not (run.private / "final_sentinel.bin").exists():
                    if shutil_free(path.parent) < RAW_BYTES + RESERVE:
                        raise OSError("Cannot preserve failure raw without disk reserve")
                    with path.open("xb") as stream: stream.write(run.last_raw)
                    run.save("failed_raw.json", dict(identity=run.last_identity, raw=pin(path)))
            except BaseException as e:
                error = dict(original=error, raw_preservation_error=repr(e))
        try:
            if run.model is not None:
                run.check("Original63 native state entries unchanged", run.library.state_hashes(run.model) == run.before)
                run.check("All old MoDA states unchanged", {key(a, s): run.library.state_hashes(b) for (a, s), b in run.banks.items()} == run.adapter_before)
                run.check("No lingering native hooks or native gradients", not any(m._forward_hooks or m._forward_pre_hooks for m in run.model.modules())
                          and all(p.grad is None and not p.requires_grad for p in run.model.parameters()))
                run.save("base_state_after.json", run.library.state_hashes(run.model))
                run.save("old_adapters_after.json", {key(a, s): run.library.state_hashes(b) for (a, s), b in run.banks.items()})
                preservation = "PASS"
        except BaseException as e:
            status, preservation = "FAIL", "FAIL"
            error = dict(original=error, custody_error=repr(e))
        if status != "PASS":
            try: run.save("partial_evaluation.json.gz", dict(rows=run.rows, reload_rows=run.reload_rows, training_completed=len(run.training)))
            except BaseException: pass
        report = dict(Purpose="CPU MoDA/source-MoE recipe pilot and interpreter reload", Environment=dict(device="CPU", threads=[2,1]),
                      Input=dict(freeze=spec["freeze_commit"], base=spec["base_commit"], mode="reload" if args.reload else "main"),
                      Expected=RELOAD_EXPECTED if args.reload else MAIN_EXPECTED, Actual=run.actual, Status=status, error=error,
                      preservation=preservation, seconds=time.perf_counter()-run.started,
                      audit_seconds=run.audit_seconds, load_seconds=getattr(run, "load_seconds", None),
                      peak_rss_bytes=peak_rss_bytes(),
                      FORMAL_ACCEPTANCE_READY=False, Formal_Oracle="BLOCKED/NOT_READY")
        run.event.close()
        run.save("completion.json", report)
        print(json.dumps(report), flush=True)
    return 0 if status == "PASS" else 2


if __name__ == "__main__": raise SystemExit(main())
