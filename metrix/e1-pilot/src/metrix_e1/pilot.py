"""Orchestration of METRIX E1-PILOT: protocol v1.1 section 8, steps 1-8, run by metrix/e1-pilot/run_pilot.py.

Implementation Task Order V1 section 5 (run_pilot.py: steps 1-8 in order, ST12 before every step, the step's record
committed at its end), section 7 (smoke mode), section 11 (acceptance). Protocol sections 7 (search, selection,
training contract), 8 (steps; Gate 0; TEST), 10 (experiment record), 11 (stops). Review Gate's ruling on C1 of
2026-11-25 (tasks/IMPL_C1_RULING.md): item 3 (checkpoint hash = train.state_sha256; the smoke test saves and reloads
every checkpoint and shows the hash unchanged). Review Gate's ruling of 2026-11-27 (tasks/IMPL_C2_OWNER_MESSAGE.md): item
1 (TEST evaluation calls do not fetch; begin and finish do; nobody pushes to the pilot's branch between them).

Commands (run_pilot.py; every command prints RESULT: PASS / RESULT: FAIL, exit 0 only on PASS):
  smoke          steps 1-7 on the CPU with a random small model of the protocol's class (the pinned config.json
                 with fewer layers and a smaller width; no weight file is downloaded or loaded), STEPS optimizer steps
                 per training run, then step 8 only as the refusal of the TEST generator. Nothing is committed; every
                 output carries SMOKE_LABEL (JSON: its "label" field; checkpoints: their "label" entry; data files,
                 which must stay byte-identical to the frozen hashes: the LABEL.txt of their directory); records go to
                 <work>/records, which record.write_record refuses to be the formal results directory. Gate 0 is
                 computed and its status fixed to NOT_TESTED; the stops that read result values (SMOKE_RECORDED_STOPS)
                 are recorded as "would stop" and the run continues, all other stops stop it.
  formal         steps 1-7 on the A100, and when Gate 0 is PASS the freeze record of step 8. Every step commits and
                 pushes its record (testgate.commit_paths: the pilot's checkout at the remote branch's latest commit).
                 The contract's step count only: RunMode refuses a shortened count in formal mode, and the formal
                 command has no step option.
  test-generate  step 8, TEST generation: python -m metrix_e1.test_data as a subprocess (it checks the generator's
                 preconditions, writes test_qa.jsonl and general_test.jsonl to <work>/test, runs the TEST part of the
                 leakage checks and commits the ST10 record). The data-auditor's L6 count follows outside this file.
  test-evaluate  step 8, TEST evaluated once: testgate.begin_test_evaluation, N and the 15 checkpoints of the
                 marker through evaluate.evaluate_model(split="test"), T1-T3, testgate.finish_test_evaluation.
  fetch-model    the pinned model revision's files (weights included) into <inputs>/qwen_model, on the A100 host only.

Directories. <work> (outside the repository; refused inside it) holds the data files, the checkpoints, the device
ledger and the GPU clock (formal), the TEST files and the per-question TEST details (outside the repository: no TEST
content is committed). Formal records go to the repository's results directory (record.FORMAL_RESULTS_REL): one record
per step, one per training run (with the DEV summary), the per-question DEV details, the Gate 0 and freeze records, and
the experiment record of protocol section 10 (one file per command run, named with its start time) at the end of the
commands formal, test-evaluate and, for an ST10 stop, test-generate; stopped runs included. A stop inside a step first
writes that step's record; records written but not yet committed when a run stops are committed with its experiment
record. One exception (final_record): a formal run that stops before step 1 began writes its experiment record to
<work> only.

Continuity (start_checks). A formal pilot is one sequence of commands on one machine with one --work: once a formal
run has committed step records, formal and test-evaluate refuse a --work without the device ledger (the recorded device
name, ST9, and the GPU clock, ST7, live there), and formal refuses to run again once a freeze record is committed. How
a stopped pilot is restarted is the Owner's decision (RUNBOOK_A100.md).

Checkpoints (protocol section 7: only the final checkpoint of a run is kept and evaluated). Each run's final state is
hashed (train.state_sha256, interpretation B25), saved with torch.save, reloaded into a fresh model of the run's
structure and hashed again; the two hashes must be equal, and the reloaded model is the one evaluated, so every
evaluation reads the saved checkpoint. All 30 are kept (none is deleted: metrix/CLAUDE.md section 7); the RUNBOOK
gives the disk size.

Preflight (section 8 step 2, ST11; interpretation B17). ST11 reads B17's estimate (compute.estimate_total_hours)
unchanged. The preflight also measures one model load, one state_sha256, one checkpoint save, one reload and one file
hash of the first configuration's model (DEFERRED_MINORS 1.27 CA21) and reports, beside B17's estimate,
  CHECKPOINT_OVERHEAD = loads x load + runs x (2 hashes + save + reload + file hash)
                        + TEST state hashes x hash + TEST checkpoint files x file hash
(evaluation_plan: base loads of N, the 30 runs and N at TEST; reloads of the G0.8 checkpoints and the 15 TEST
checkpoints; the TEST models' state hashes in testgate.require_test_session plus N's in begin; the 15 TEST checkpoint
files) and the sum; whether ST11
should read the sum is for Review Gate (reports/IMPL_C_REPORT.md). The measured times also give the ST7 look-ahead
(next_seconds): before a training run its training, save and DEV evaluation; before an evaluation the evaluation; before
the TEST evaluation begins, the whole TEST evaluation (test_evaluation_seconds), so that ST7 does not stop it half-way.
"""
import dataclasses
import gc
import json
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

import torch

from . import compute as CP
from . import contract as C
from . import data as D
from . import evaluate as E
from . import frozen as FZ
from . import gate as G
from . import leakage as LK
from . import mode as M
from . import record as R
from . import stats as S
from . import stops as STP
from . import testgate as TG
from . import train as T
from .errors import ImplementationFail, ProtocolStop, ST12Error

SMOKE_MODEL_OVERRIDES = {"num_hidden_layers": 2, "hidden_size": 64, "intermediate_size": 128,
                         "num_attention_heads": 4, "num_key_value_heads": 2, "head_dim": 16}
SMOKE_INIT_SEED = 0                 # torch.manual_seed of the small model's random initialisation (smoke only)
SMOKE_RECORDED_STOPS = ("ST2", "ST3", "ST4", "ST5", "ST11")   # read result values or timings: smoke values only
LABEL_FILE = "LABEL.txt"
DATA_DIR, CHECKPOINT_DIR, TEST_DIR, TEST_DETAILS_DIR, PREFLIGHT_DIR = "data", "checkpoints", "test", "test_details", "preflight"
SMOKE_RECORDS_DIR = "records"
STEP1_RECORD_REL = R.FORMAL_RESULTS_REL + "/step1_record.json"
RUNS_DIR, DETAILS_DIR = "training_runs", "details"     # under the records directory ("runs" is in the repository's
                                                       # .gitignore; tests/test_run_pilot.py checks every record path)
DEVICE_LEDGER, GPU_CLOCK = "device_ledger.json", "gpu_clock.json"
GENERATED = "GENERATED"             # DATA_MANIFEST.json files.<name>.status once step 1 has written the hashes


# --------------------------------------------------------------------------------------------------- helpers

def plain(obj):
    """JSON-ready copy: exact fractions as floats, tuples and sets as lists, dataclasses as dicts."""
    if isinstance(obj, Fraction):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [plain(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(plain(v) for v in obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return plain(dataclasses.asdict(obj))
    if isinstance(obj, Path):
        return str(obj)
    return obj


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def outside(path, root):
    """True iff `path` is neither the repository root nor inside it."""
    p, r = Path(path).resolve(), Path(root).resolve()
    return p != r and r not in p.parents


def load_rows(data_dir):
    """The parsed non-TEST data files: {file name: rows}; candidates.json as its object."""
    d = Path(data_dir)
    out = {}
    for name in D.DATA_FILES:
        raw = (d / name).read_bytes()
        out[name] = json.loads(raw) if name.endswith(".json") else FZ.parse_jsonl(raw)
    return out


def manifest_bytes(obj):
    """The layout of DATA_MANIFEST.json and SPLIT_MANIFEST.json in the repository (indent 2, UTF-8, final newline)."""
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def step1_manifests(fz, current, file_hashes):
    """Section 8 step 1: the two manifests with the field step 1 writes filled in (frozen.STEP1_FIELDS; ST12 leaves
    exactly these out). DATA_MANIFEST.json files.<name> of the 8 non-TEST files: status GENERATED, byte_sha256,
    canonical_sha256; SPLIT_MANIFEST.json split_sha256.<name> of the non-TEST split files: canonical_sha256
    (interpretation B3's ruling note: the canonical hash of train_Y.jsonl among them). TEST entries stay as they are.
    `current`: {repository path: bytes} of the two manifests as in the working tree. Returns {path: new bytes};
    raises ST12Error when anything outside the step-1 field would change."""
    dm = json.loads(current[FZ.DATA_MANIFEST_REL])
    sm = json.loads(current[FZ.SPLIT_MANIFEST_REL])
    for name in D.DATA_FILES:
        dm["files"][name].update(status=GENERATED, byte_sha256=file_hashes[name]["byte_sha256"],
                                 canonical_sha256=file_hashes[name]["canonical_sha256"])
    for name in sm["split_sha256"]:
        if name in D.DATA_FILES:
            sm["split_sha256"][name] = file_hashes[name]["canonical_sha256"]
    out = {FZ.DATA_MANIFEST_REL: manifest_bytes(dm), FZ.SPLIT_MANIFEST_REL: manifest_bytes(sm)}
    for rel, blob in out.items():
        if FZ.strip_step1_fields(rel, json.loads(blob)) != FZ.strip_step1_fields(rel, json.loads(fz.blobs[rel])):
            raise ST12Error("%s: step 1 would change it outside %r" % (rel, FZ.STEP1_FIELDS[rel]))
    return out


def evaluation_plan(contract):
    """Counts of the checkpoint overhead: base-model loads (N, one per training run, N at TEST), checkpoints saved and
    reloaded (30), further checkpoint reloads (one G0.8 re-evaluation per training seed, the 15 TEST checkpoints),
    state hashes at TEST (the 16 models in require_test_session and N's once more in begin), TEST checkpoint files
    hashed before the marker (15)."""
    seeds = len(contract.training.training_seeds)
    runs = contract.arms.counts["total_training_runs"]
    test_models = 1 + len(T.ARMS_TRAINED) * seeds
    return {"base_loads": 1 + runs + 1, "checkpoints": runs, "checkpoint_reloads": seeds + test_models - 1,
            "test_state_hashes": test_models + 1, "test_file_hashes": test_models - 1, "test_models": test_models}


def checkpoint_overhead_seconds(contract, load_s, hash_s, save_s, reload_s, file_hash_s):
    """Report only (ST11 reads B17's estimate): base loads x load_s, every checkpoint hashed twice, saved, reloaded and
    file-hashed, the further reloads x reload_s, the TEST state hashes and the TEST checkpoint file hashes."""
    n = evaluation_plan(contract)
    return (n["base_loads"] * load_s + n["checkpoints"] * (2 * hash_s + save_s + reload_s + file_hash_s)
            + n["checkpoint_reloads"] * reload_s + n["test_state_hashes"] * hash_s
            + n["test_file_hashes"] * file_hash_s), n


def test_evaluation_seconds(contract, pre):
    """ST7 look-ahead before the TEST evaluation begins, for the GPU time from that check on: N loaded (load_s) and the
    15 checkpoints loaded (load_checkpoint: reload_s), the state hashes (N twice), each model evaluated once on TEST (a
    DEV evaluation scaled by test / dev questions per fact, as B17). The 15 checkpoint file hashes happen before the
    GPU clock opens and are not counted. No margin is added (for Review Gate, reports/IMPL_C_REPORT.md C2). `pre`: the
    timing block of the committed step 2 record."""
    n = evaluation_plan(contract)
    acc = contract.accounting
    per_eval = pre["dev_evaluation_seconds"] * acc.test_questions_per_fact / acc.dev_questions_per_fact
    checkpoints = n["test_models"] - 1
    return (pre["load_s"] + checkpoints * pre["reload_s"] + n["test_models"] * per_eval
            + n["test_state_hashes"] * pre["hash_s"])


# --------------------------------------------------------------------------------------------------- the pilot

class Pilot:
    """State of one command: frozen files, contract, mode, directories, tokenizer, data, device bookkeeping."""

    def __init__(self, mode, inputs, work, device, repo_root=None, log=None):
        self.mode = mode
        self.device = device
        self.log = log or (lambda msg: print("[%s] %s" % (utc(), msg), flush=True))
        self.root = Path(repo_root).resolve() if repo_root is not None else FZ.default_repo_root().resolve()
        self.inputs = Path(inputs).resolve()
        self.work = Path(work).resolve()
        if not outside(self.work, self.root):
            raise ImplementationFail("--work %s is inside the repository %s (data, checkpoints and TEST files are "
                                     "never committed)" % (self.work, self.root))
        self.model_dir = self.inputs / T.MODEL_CONFIG_DIR
        self.data_dir = self.work / DATA_DIR
        self.ckpt_dir = self.work / CHECKPOINT_DIR
        self.records = self.root / R.FORMAL_RESULTS_REL if mode.formal else self.work / SMOKE_RECORDS_DIR
        self.fz = STP.st12(self.root)                   # PROTOCOL_FROZEN, the four frozen files (git cat-file)
        self.contract = C.load(self.fz)
        self.determinism = CP.set_determinism(self.contract)     # protocol section 0; before CUDA is initialised
        self.started = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        self.device_info_record = None
        self.model_files = None
        self.ledger = CP.DeviceLedger(self.work / DEVICE_LEDGER) if mode.formal else None
        self.clock = CP.GpuClock(self.work / GPU_CLOCK) if mode.formal else None
        self.clock_opened = False
        self.device_name = None
        self.rows = None
        self.tok = None
        self.base_sha = None
        self.pre = None                             # preflight timings (ST7 look-ahead), set by preflight()
        self.smoke_stops = []
        self.excluded = []
        self.runs = {}                              # run name -> result of train_and_evaluate (kept for a stopped run)
        self.code_commit = None
        self.step1_started = False                  # formal: the repository is written only from step 1 on
        self.steps = {}
        self.written = []
        self.uncommitted = []                       # formal records written and not yet committed
        self.begin_called = False                   # test_evaluate called testgate.begin_test_evaluation
        self.marker_before_begin = None

    # -- output
    def label_dir(self, d):
        """Smoke: the LABEL.txt of a directory whose files cannot carry the label inside (data, checkpoints)."""
        d.mkdir(parents=True, exist_ok=True)
        if self.mode.smoke:
            (d / LABEL_FILE).write_text(M.SMOKE_LABEL + "\n", encoding="utf-8")

    def write(self, name, obj):
        """A JSON record of this command under the records directory with its mode and label; the formal results
        directory refuses smoke and preflight records and a formal record goes nowhere else (record.write_record; the
        one exception is the experiment record of a formal run that stopped before step 1, final_record)."""
        rec = dict(plain(obj), mode=self.mode.name, label=self.mode.label)
        path = R.write_record(rec, self.records / name, self.root)
        self.written.append(path)
        if self.mode.formal and path not in self.uncommitted:
            self.uncommitted.append(path)
        return path

    def rel(self, path):
        return Path(path).resolve().relative_to(self.root).as_posix()

    def commit(self, paths, message, what):
        """Formal: commit those of `paths` whose bytes differ from HEAD (a path equal to its committed version, e.g.
        a deterministic record written again, is not staged by git and is left out) and push (testgate.commit_paths;
        the preconditions were checked before they were written: precommit()). Returns the commit, or None when
        nothing changed. Smoke: nothing is committed."""
        if not self.mode.formal:
            return None
        rels = [self.rel(x) for x in paths]
        changed = [r for r in rels if TG._blob(self.root, "HEAD:%s" % r) != (self.root / r).read_bytes()]
        head = TG.commit_paths(self.root, changed, message, what) if changed else None
        for x in paths:                             # after a successful commit (or nothing to commit) only
            if x in self.uncommitted:
                self.uncommitted.remove(x)
        if head is None:
            self.log("%s: equal to the committed version, nothing to commit" % what)
        else:
            self.log("committed and pushed %s: %s" % (what, head))
        return head

    def precommit(self, what):
        if self.mode.formal:
            TG.check_commit_preconditions(self.root, what)

    # -- stops
    def stop_check(self, fn, *args):
        """Run a stop check. Formal: a stop propagates. Smoke: a stop of SMOKE_RECORDED_STOPS is recorded as
        'would stop' (smoke values are not results) and the run continues."""
        try:
            fn(*args)
        except STP.Stop as e:
            if self.mode.smoke and e.stop in SMOKE_RECORDED_STOPS:
                self.smoke_stops.append({"stop": e.stop, "would_stop": str(e), "label": M.SMOKE_LABEL})
                self.log("smoke: %s would stop here (smoke value, not a result): %s" % (e.stop, e))
                return False
            raise
        return True

    def stop_in_step(self, k, record, paths, fn, *args):
        """stop_check inside step k: when the stop propagates, the step's record (with what the step computed and the
        stop) is written and, in formal mode, committed first; then the stop is raised again."""
        try:
            return self.stop_check(fn, *args)
        except STP.Stop as e:
            rec = dict(record, stopped={"code": e.stop, "status": e.status, "message": str(e)})
            try:
                self.step_end(k, rec, paths, "metrix: E1-PILOT formal step %d record (stop %s)" % (k, e.stop))
            except ProtocolStop as e2:
                self.log("the step %d record of the stop was not committed: %s" % (k, e2))
            raise

    def start_checks(self, command):
        """Continuity of a formal pilot (module docstring): once a formal run committed step records, a --work
        without the device ledger is refused (ST9 and ST7 read it); formal refuses to run again once a freeze record
        is committed. Raises a BLOCKED stop before anything is written."""
        if not self.mode.formal:
            return
        if TG._blob(self.root, "HEAD:%s" % STEP1_RECORD_REL) is not None and not self.ledger.path.exists():
            raise ProtocolStop(None, "BLOCKED", "a formal run has committed step records (%s) but --work %s holds no "
                               "device ledger: either this is not that run's --work, or that run stopped before its "
                               "first model load (step 2); a restart is the Owner's decision" % (
                                   STEP1_RECORD_REL, self.work))
        if command == "formal" and TG._blob(self.root, "HEAD:%s" % R.SELECTION_FREEZE_REL) is not None:
            raise ProtocolStop(None, "BLOCKED", "a freeze record is committed (%s): Gate 0 passed and the "
                               "configurations are frozen; formal is not run again" % R.SELECTION_FREEZE_REL)
        if command == "formal" and self.ckpt_dir.is_dir() and any(self.ckpt_dir.glob("*.pt")):
            raise ProtocolStop(None, "BLOCKED", "--work %s already holds checkpoints of a formal run: each run is "
                               "trained once; a restart is the Owner's decision" % self.work)

    def run_seconds(self, spec):
        """ST7 look-ahead of a training run: the base model loaded, the preflight's per-step time x the contract's
        steps (x the A factor for arm A only, as B17), the checkpoint hashed, saved, file-hashed, reloaded and hashed,
        one DEV evaluation (0 before the preflight)."""
        if self.pre is None:
            return 0.0
        q = self.pre
        factor = q["a_factor"] if spec.arm == "A" else 1.0
        return (q["load_s"] + q["mean_step_s"] * self.contract.training.total_steps * factor + 2 * q["hash_s"]
                + q["save_s"] + q["file_hash_s"] + q["reload_s"] + q["dev_evaluation_seconds"])

    def eval_seconds(self, load):
        """ST7 look-ahead of one DEV evaluation (0 before the preflight); `load`: "load" (the base model loaded
        first), "reload" (a checkpoint loaded first, load_checkpoint) or None (the model is in memory)."""
        if self.pre is None:
            return 0.0
        return {"load": self.pre["load_s"], "reload": self.pre["reload_s"], None: 0.0}[load] + \
            self.pre["dev_evaluation_seconds"]

    def step_start(self, k):
        """ST12 before every step (Implementation Task Order V1 section 5): PROTOCOL_FROZEN, the four frozen files,
        and from step 2 on the inputs and the whole data directory (data.verify). ST13 by detection
        (stops.st13_scan): no TEST file in the data or TEST directory before the freeze record is committed."""
        self.fz = STP.st12(self.root, self.inputs, self.data_dir if k > 1 else None)
        STP.st13_scan(self.fz, self.root, [self.data_dir, self.work / TEST_DIR])
        self.precommit("the step %d record" % k)
        self.step1_started = True
        if torch.device(self.device).type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        self.steps[k] = {"step": k, "started_utc": utc(), "t0": time.perf_counter(), "files": []}
        self.log("step %d: ST12 passed%s" % (k, " (frozen files)" if k == 1 else " (frozen files, inputs, data)"))

    def step_end(self, k, record, paths=(), message=None):
        """The step's record (seconds, peak memory, files written) under the records directory; formal: committed with
        `paths` and pushed."""
        st = self.steps[k]
        st["seconds"] = time.perf_counter() - st.pop("t0")
        st["peak_memory_bytes"] = CP.peak_memory_bytes(self.device)
        st["peak_memory_kind"] = ("CUDA max_memory_allocated of the step" if torch.device(self.device).type == "cuda"
                                  else "peak resident set size of the process so far (CPU)")
        files = [str(x) for x in paths] + [str(x) for x in record.pop("_files", [])]
        st["files"] = sorted(set(files))
        rec_path = self.write("step%d_record.json" % k, dict(record, step_info=st, kind="step%d" % k))
        self.commit(list(paths) + [rec_path], message or "metrix: E1-PILOT formal step %d record" % k,
                    "the step %d record" % k)
        self.log("step %d done in %.1f s" % (k, st["seconds"]))
        return rec_path

    # -- device and GPU time (sections 7, 11: ST7, ST8, ST9)
    def device_check(self):
        """ST8 (formal); smoke: 'smoke: device check skipped'."""
        info = CP.check_device(self.fz, self.contract, self.mode)
        if self.mode.formal:
            self.device_name = info["name"]
        return info

    def before_run(self, next_seconds=0.0):
        """At the start of every training or evaluation run (formal): the device name against the recorded one (ST9)
        and the GPU wall-clock (ST7)."""
        if not self.mode.formal:
            return
        self.first_load()
        self.ledger.check(self.fz, CP.device_info()["name"])
        self.clock.check(self.fz, self.contract, next_seconds)

    def first_load(self):
        """Right before the first model load of this command (called by before_run and base_model): records the
        device name at the pilot's first load (section 7) and opens a GPU clock segment (a segment left open by a
        process that died is closed first, counted up to now). No CUDA device: ST8."""
        if not self.mode.formal or self.clock_opened:
            return
        name = CP.check_device(self.fz, self.contract, self.mode)["name"]
        if self.ledger.recorded() is None:
            self.ledger.record_first(name)
            self.log("device name recorded at the first model load: %r" % name)
        self.ledger.check(self.fz, name)
        if self.clock._state()["open"] is not None:
            self.clock.close()
            self.log("GPU clock: a segment left open by an earlier process was closed (counted up to now)")
        self.clock.open()
        self.clock_opened = True

    def close_clock(self):
        if self.clock_opened:
            self.clock.close()
            self.clock_opened = False

    # -- models and checkpoints
    def base_model(self):
        """A fresh model with the base weights. Formal: the pinned model from <inputs>/qwen_model (train.load_model).
        Smoke: the protocol's model class from the pinned config.json with SMOKE_MODEL_OVERRIDES, randomly initialised
        with SMOKE_INIT_SEED (every call gives the same weights), float32, eager attention as train.load_model."""
        self.first_load()
        if self.mode.formal:
            if self.model_files is None:
                self.model_files = check_model_dir(self.fz, self.model_dir, weights=True)
            return T.load_model(self.model_dir, self.device)
        from transformers import AutoModelForCausalLM
        check_model_dir(self.fz, self.model_dir, weights=False)
        cfg = smoke_config(self.model_dir)
        torch.manual_seed(SMOKE_INIT_SEED)
        m = AutoModelForCausalLM.from_config(cfg, dtype=torch.float32, attn_implementation="eager")
        return m.to(self.device).eval()

    def model_for(self, spec):
        """A fresh model of the run's structure (arm L: LoRA applied, train.prepare_arm) with the base weights."""
        m = self.base_model()
        if spec.arm == "L":
            T.prepare_arm(m, spec, self.contract, self.mode)
        return m

    def save_checkpoint(self, spec, model):
        """B25 / C1 ruling 3: state_sha256 of the trained model; torch.save; reload into a fresh model of the run's
        structure; state_sha256 again, equal or IMPLEMENTATION_FAIL. Returns (reloaded model, checkpoint info)."""
        self.label_dir(self.ckpt_dir)
        t0 = time.perf_counter()
        sha = T.state_sha256(model)
        t1 = time.perf_counter()
        path = self.ckpt_dir / ("%s.pt" % spec.name)
        if path.exists():
            raise ImplementationFail("checkpoint %s exists: each run is trained once" % path)
        torch.save({"label": self.mode.label, "run": spec.name, "state_sha256": sha, "state_dict": model.state_dict()},
                   path)
        t2 = time.perf_counter()
        reloaded = self.load_checkpoint(spec, path)     # the caller still holds `model` (80 GB hold both)
        t3 = time.perf_counter()
        again = T.state_sha256(reloaded)
        t4 = time.perf_counter()
        if again != sha:
            raise ImplementationFail("%s: state sha256 %s after saving and reloading, %s before" % (spec.name, again, sha))
        info = {"state_sha256": sha, "reloaded_state_sha256": again, "file": path.name,
                "file_sha256": FZ.file_sha256(path), "file_bytes": path.stat().st_size,
                "seconds": {"hash": t1 - t0, "save": t2 - t1, "reload": t3 - t2, "hash_after_reload": t4 - t3}}
        return reloaded, info

    def load_checkpoint(self, spec, path):
        ck = torch.load(path, map_location=self.device, weights_only=True)
        if ck.get("run") != spec.name or ck.get("label") != self.mode.label:
            raise ImplementationFail("%s holds run %r label %r, not %s of this %s run" % (
                path, ck.get("run"), ck.get("label"), spec.name, self.mode.name))
        m = self.model_for(spec)
        m.load_state_dict(ck["state_dict"], strict=True)
        return m.eval()

    # -- data
    def load_data(self):
        self.rows = load_rows(self.data_dir)
        p = D.params(self.fz)
        self.tok = D.load_qwen_tokenizer(p, D.check_inputs(self.fz, p, self.inputs))

    def evaluate(self, model, split="dev", **kw):
        return E.evaluate_model(model, self.tok, self.rows, self.fz.templates, self.contract.evaluation, self.mode,
                                self.device, split=split, **kw)

    def summary(self, ev, split="dev"):
        return S.evaluation_summary(ev, self.rows["facts.jsonl"], self.contract.statistics.strata, split)


def smoke_config(model_dir):
    """The pinned config.json with SMOKE_MODEL_OVERRIDES (the smoke test's small model of the protocol's class)."""
    from transformers import AutoConfig
    cfg = AutoConfig.from_pretrained(str(model_dir), local_files_only=True)
    for k, v in SMOKE_MODEL_OVERRIDES.items():
        setattr(cfg, k, v)
    return cfg


def check_model_dir(fz, model_dir, weights):
    """ST12 for the model: config.json (and, with `weights`, every *.safetensors file and at least one) in model_dir
    was downloaded from the frozen revision (DATA_MANIFEST.json model.revision): the first line of the
    huggingface_hub download metadata of each file is that commit. Returns {file: sha256} of the weight files."""
    rev = fz.data_manifest["model"]["revision"]
    d = Path(model_dir)
    names = ["config.json"] + (sorted(p.name for p in d.glob("*.safetensors")) if weights else [])
    if weights and len(names) == 1:
        raise ST12Error("no *.safetensors weight file in %s (run_pilot.py fetch-model)" % d)
    out = {}
    for n in names:
        meta = d / ".cache" / "huggingface" / "download" / ("%s.metadata" % n)
        try:
            got = meta.read_text(encoding="utf-8").split("\n")[0].strip()
        except OSError as e:
            raise ST12Error("%s: no download metadata %s (%r)" % (n, meta, e)) from e
        if got != rev:
            raise ST12Error("%s in %s was downloaded from revision %r, the frozen revision is %s" % (n, d, got, rev))
        if n != "config.json":
            out[n] = FZ.file_sha256(d / n)
    return out


def fetch_model(fz, inputs_dir):
    """The pinned revision's files (config, generation config, weights, index) into <inputs>/qwen_model with
    huggingface_hub; on the A100 host only (Implementation Task Order V1 red line 2: never in the CPU environment):
    the ST8 device check runs first and refuses any other host."""
    from huggingface_hub import snapshot_download
    CP.check_device(fz, C.load(fz), M.FORMAL_MODE)
    m = fz.data_manifest["model"]
    d = Path(inputs_dir) / T.MODEL_CONFIG_DIR
    snapshot_download(m["repo"], revision=m["revision"], local_dir=str(d), allow_patterns=["*.json", "*.safetensors"])
    return check_model_dir(fz, d, weights=True)


# --------------------------------------------------------------------------------------------------- steps 1-7

def step1(p):
    """Section 8 step 1: environment and provenance; the non-TEST data on the CPU; the four frozen content hashes
    (ST12); formal: the hashes written into the two manifests and committed. The GPU check (ST8) ran at the start of
    the command, before anything was written (device_check)."""
    p.step_start(1)
    files, info = D.generate(p.fz, p.inputs)
    D.write(files, p.data_dir)
    p.label_dir(p.data_dir)
    content = p.fz.check_data_dir(p.data_dir)
    hashes = D.file_hashes(p.data_dir)
    current = {rel: (p.root / rel).read_bytes() for rel in (FZ.DATA_MANIFEST_REL, FZ.SPLIT_MANIFEST_REL)}
    new = step1_manifests(p.fz, current, hashes)
    committed = {rel: FZ.git_blob(p.root, "HEAD", rel) for rel in new}
    changed = [rel for rel in new if new[rel] != committed[rel]]      # against HEAD: a crashed run's write counts
    paths = []
    if p.mode.formal:
        for rel in new:
            if new[rel] != current[rel]:
                (p.root / rel).write_bytes(new[rel])
        paths = [p.root / rel for rel in changed]
        p.fz = STP.st12(p.root)                         # ST12 still holds with the step-1 fields written
    else:
        p.write("step1_manifest_fields.json", {"kind": "step1_manifest_fields", "note": "smoke: the manifests are not "
                "changed; the fields step 1 would write", "fields": {rel: json.loads(b)[FZ.STEP1_FIELDS[rel]]
                                                                     for rel, b in new.items()}})
    p.load_data()
    rec = {"data_generation": {k: v for k, v in info.items() if k != "name_log"}, "name_log": info["name_log"],
           "content_hashes": content, "file_hashes": hashes, "manifests_changed": changed,
           "manifests_already_written": not changed, "environment": R.environment(p.fz, p.device_name or p.device,
                                                                                  CP.determinism_settings(), hashes),
           "device": p.device_info_record, "_files": [p.data_dir / n for n in D.DATA_FILES]}
    p.step_end(1, rec, paths, "metrix: E1-PILOT formal step 1 (non-TEST data hashes written into the manifests)")
    return content, hashes


def step2(p):
    """Section 8 step 2: the Gate 0 leakage checks (ST1); the preflight (ST11)."""
    p.step_start(2)
    report = LK.run_gate0(p.fz.split_manifest, LK.load_data(p.data_dir))
    p.stop_in_step(2, {"leakage": report}, [], STP.st1, p.fz, report)
    p.log("step 2: leakage L1-L6 (Gate 0 part) %s" % report["result"])
    pre = preflight(p)
    files = pre.pop("_files")
    rec = {"leakage": report, "preflight": pre, "_files": files}
    ok = p.stop_in_step(2, dict(rec, _files=list(files)), [], STP.st11, p.fz, p.contract, pre["b17_estimate_hours"])
    pre["st11"] = "within bound" if ok else "smoke: would stop"
    p.step_end(2, rec)
    return report


def preflight(p):
    """Section 8 step 2 (ST11; B17 plus the checkpoint overhead, see the module docstring): the first configuration
    for the protocol's preflight steps (formal: preflight mode on the A100; smoke: smoke mode on the CPU, its numbers
    are smoke values). Its outputs are timing only."""
    pmode = M.preflight_mode(p.contract) if p.mode.formal else p.mode
    spec = T.search_runs(p.contract, "F")[0]
    p.before_run()
    t0 = time.perf_counter()
    model = p.base_model()
    load_s = time.perf_counter() - t0
    try:
        res = T.train_run(model, p.tok, p.rows, spec, p.contract, pmode, p.device)
        summ = CP.preflight_summary(res.log, p.device)
        t0 = time.perf_counter()
        E.evaluate_model(model, p.tok, p.rows, p.fz.templates, p.contract.evaluation, pmode, p.device, split="dev")
        eval_s = time.perf_counter() - t0
    except T.NonFinite as e:            # no estimate, so no ST11 judgement: stopped as for a control (ST6)
        STP.st6(p.fz, e.values or [float("nan")], "preflight %s: %s" % (spec.name, e), True)
        raise
    t0 = time.perf_counter()
    T.state_sha256(model)
    hash_s = time.perf_counter() - t0
    d = p.work / PREFLIGHT_DIR
    p.label_dir(d)
    path = d / "preflight_checkpoint.pt"
    t0 = time.perf_counter()
    torch.save({"label": pmode.label, "state_dict": model.state_dict()}, path)
    save_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    FZ.file_sha256(path)
    file_hash_s = time.perf_counter() - t0
    del model
    gc.collect()
    t0 = time.perf_counter()
    fresh = p.base_model()
    fresh.load_state_dict(torch.load(path, map_location=p.device, weights_only=True)["state_dict"], strict=True)
    reload_s = time.perf_counter() - t0
    del fresh
    gc.collect()
    anchors = [r["ids"] for r in p.rows[T.ANCHOR_FILE]]
    steps = list(T.step_numbers(p.contract.training.total_steps))
    anchor_per_step = sum(sum(len(anchors[i]) for i in T.anchor_docs(s, p.contract.arms)) for s in steps) / len(steps)
    fact_per_step = sum(e["fact_tokens"] for e in res.log) / len(res.log)
    used = p.clock.used() if p.clock is not None else 0.0
    hours, parts = CP.estimate_total_hours(p.contract, summ["mean_seconds_per_step_excluding_first"], fact_per_step,
                                           anchor_per_step, eval_s, used)
    overhead, counts = checkpoint_overhead_seconds(p.contract, load_s, hash_s, save_s, reload_s, file_hash_s)
    p.pre = {"mean_step_s": summ["mean_seconds_per_step_excluding_first"], "a_factor": parts["a_factor"],
             "dev_evaluation_seconds": eval_s, "load_s": load_s, "hash_s": hash_s, "save_s": save_s,
             "reload_s": reload_s, "file_hash_s": file_hash_s}
    out = {"label": pmode.label, "mode": pmode.name, "run": spec.name, "steps": res.steps_run, "summary": summ,
           "dev_evaluation_seconds": eval_s, "fact_tokens_per_step": fact_per_step,
           "anchor_tokens_per_step": anchor_per_step, "b17_estimate_hours": hours, "b17_parts": parts,
           "st11_reads": "b17_estimate_hours", "st11_bound_hours": p.contract.stops.st11_hours,
           "checkpoint_overhead_report_only": {"seconds": overhead, "counts": counts},
           "b17_plus_checkpoint_overhead_hours_report_only": hours + overhead / 3600.0,
           "timing": p.pre, "checkpoint_file": str(path), "_files": [path]}
    p.log("preflight (%s): %.4f s/step, DEV evaluation %.1f s, B17 estimate %.3f h (ST11); checkpoint overhead %.3f h "
          "(report only; sum %.3f h)" % (pmode.name, p.pre["mean_step_s"], eval_s, hours, overhead / 3600.0,
                                        hours + overhead / 3600.0))
    return out


def step3(p):
    """Section 8 step 3: N on TRAIN closed book, DEV-QA, general DEV; ST2 on G0.3."""
    p.step_start(3)
    p.before_run(p.eval_seconds("load") + (p.pre["hash_s"] if p.pre else 0.0))     # N is also hashed
    model = p.base_model()
    p.base_sha = T.state_sha256(model)
    ev = control_evaluation(p, model, "N on DEV", with_em=True)
    summ = p.summary(ev)
    vals = G.n_range_values(summ, p.contract.statistics.strata, "dev")
    ok = G.n_ranges_hold(vals, p.contract, "dev")
    det = p.write(DETAILS_DIR + "/N_dev.json", {"kind": "evaluation_details", "model": "N", "split": "dev", "evaluation": ev})
    del model
    gc.collect()
    p.log("step 3: N acc_dev_learned %.4f acc_dev_unread %.4f acc_cb %.4f; G0.3 ranges %s" % (
        vals["acc_dev_learned"], vals["acc_dev_unread"], vals["acc_cb"], "hold" if ok else "do not hold"))
    rec = {"N": {"state_sha256": p.base_sha, "summary": _summary_record(summ), "g03_values": vals, "g03_holds": ok}}
    stop = p.stop_in_step(3, rec, [det], STP.st2, p.fz, ok)
    rec["N"]["st2"] = "not triggered" if stop else "smoke: would stop"
    p.step_end(3, rec, [det])
    return {"ev": ev, "summary": summ}


def control_evaluation(p, model, what, split="dev", **kw):
    """An evaluation of N or of a selected configuration's checkpoint: a non-finite value is ST6 on a control or a
    selected configuration (IMPLEMENTATION_FAIL)."""
    try:
        return p.evaluate(model, split=split, **kw)
    except T.NonFinite as e:
        STP.st6(p.fz, e.values or [float("nan")], "%s: %s" % (what, e), True)
        raise


def _summary_record(summ):
    """An evaluation summary for a record: accuracies and per-fact scores; the general-text NLL rows stay in the
    details."""
    return {k: v for k, v in summ.items() if not k.startswith("general_")}


def train_and_evaluate(p, spec, n_general, selected_or_control):
    """One training run (protocol sections 4, 7) and the DEV evaluation of its saved final checkpoint. A non-finite
    value (ST6): outside the selected configurations and the controls the configuration is excluded from selection
    (returns a result with finite False); otherwise IMPLEMENTATION_FAIL (the stop propagates)."""
    p.before_run(p.run_seconds(spec))
    model = p.base_model()                              # train.train_run sets up the arm (LoRA for L)
    rec = {"kind": "training_run", "run": spec.name, "arm": spec.arm, "config_id": spec.config_id,
           "config": spec.cfg, "seed": spec.seed, "phase": spec.phase, "device_name": p.device_name}
    ck = None
    try:
        res = T.train_run(model, p.tok, p.rows, spec, p.contract, p.mode, p.device)
        params_forward = sum(q.numel() for q in model.parameters())
        reloaded, ck = p.save_checkpoint(spec, model)
        del model
        model = None
        p.before_run(p.eval_seconds(None))
        ev = p.evaluate(reloaded, with_em=True, with_s_mapping=spec.arm == "S")
    except T.NonFinite as e:
        try:
            STP.st6(p.fz, e.values or [float("nan")], "%s: %s" % (spec.name, e), selected_or_control)
        except STP.Stop as stop:
            if not stop.exclude_config:
                raise
            if ck is None:                  # stopped in training: the state at the stop is the run's final state
                _, ck = p.save_checkpoint(spec, model)
            p.excluded.append({"run": spec.name, "reason": str(stop)})
            p.log("ST6: %s excluded from selection: %s" % (spec.name, stop))
            rec.update(finite=False, excluded=str(stop), checkpoint=ck)
            return {"spec": spec, "finite": False, "state_sha256": ck["state_sha256"],
                    "record": p.write("%s/%s.json" % (RUNS_DIR, spec.name), rec)}
        raise ImplementationFail("non-finite values %r without a stop" % (e.values,))
    summ = p.summary(ev)
    dnll, ppl = S.dnll(ev["general_dev"], n_general)
    rec.update(finite=True, steps_run=res.steps_run, contract_steps=p.contract.training.total_steps,
               mode_steps=p.mode.steps(p.contract.training.total_steps), trainable=res.trainable,
               frozen_sha256_before=res.frozen_sha256_before, frozen_sha256_after=res.frozen_sha256_after,
               base_trainable=res.base_trainable, notes=res.notes, log=res.log,
               accounting=CP.run_flops(p.contract, res, params_forward), checkpoint=ck,
               dev=_summary_record(summ), dnll=dnll, ppl_degradation_pct=ppl)
    run_path = p.write("%s/%s.json" % (RUNS_DIR, spec.name), rec)
    det = p.write(DETAILS_DIR + "/%s_dev.json" % spec.name, {"kind": "evaluation_details", "model": spec.name, "split": "dev",
                                                       "evaluation": ev})
    del reloaded
    gc.collect()
    if torch.device(p.device).type == "cuda":
        torch.cuda.empty_cache()
    p.log("%s: %d steps, acc_dev_learned %.4f acc_cb %.4f dNLL %.5f, state sha256 %s (unchanged after reload)" % (
        spec.name, res.steps_run, float(summ["acc_dev_learned"]), float(summ["acc_cb"]), dnll, ck["state_sha256"][:16]))
    return {"spec": spec, "finite": True, "ev": ev, "summary": summ, "dnll": dnll, "state_sha256": ck["state_sha256"],
            "record": run_path, "details": det}


def search(p, arm, n_general):
    """Section 7: the arm's 6 configurations with the search seed, then the selection on DEV."""
    results = {}
    for spec in T.search_runs(p.contract, arm):
        results[spec.name] = train_and_evaluate(p, spec, n_general, selected_or_control=False)
    rows = []
    for r in results.values():
        s = r["spec"]
        rows.append({"config_id": s.config_id, "learning_rate": s.cfg["learning_rate"], "finite": r["finite"],
                     "acc": r["summary"]["acc_dev_learned"] if r["finite"] else float("nan"),
                     "dnll": r["dnll"] if r["finite"] else float("nan")})
    chosen, ranking = T.select_config(p.contract, arm, rows)
    p.log("selection %s: %s (ranking %s)" % (arm, chosen, ranking))
    return results, {"selected": chosen, "ranking": ranking, "rows": rows}


def step4(p, runs, n_general):
    """Section 8 step 4: F's 6 configurations (seed 101) -> selection -> positive control of the selected
    configuration (ST3)."""
    p.step_start(4)
    res, sel = search(p, "F", n_general)
    runs.update(res)
    f101 = runs[_name("F", sel["selected"], p.contract.training.search_seed)]["summary"]
    cb, acc = float(f101["acc_cb"]), float(f101["acc_dev_learned"])
    rec = {"selection": sel, "positive_control": {"acc_cb": cb, "acc_dev_learned": acc}}
    stop = p.stop_in_step(4, rec, _run_files(res), STP.st3, p.fz, p.contract, cb, acc)
    rec["positive_control"]["st3"] = "not triggered" if stop else "smoke: would stop"
    p.step_end(4, rec, _run_files(res))
    return sel["selected"]


def step5(p, runs, n_general):
    """Section 8 step 5: L and A searches -> selection."""
    p.step_start(5)
    out, files = {}, []
    for arm in ("L", "A"):
        res, sel = search(p, arm, n_general)
        runs.update(res)
        out[arm] = sel
        files += _run_files(res)
    p.step_end(5, {"selection": out}, files)
    return {a: out[a]["selected"] for a in ("L", "A")}


def step6(p, runs, n_general, selected):
    """Section 8 step 6: F, L, A with the other two seeds; S and Y with F's configuration, three seeds each."""
    p.step_start(6)
    res = {}
    for spec in T.seed_runs(p.contract, selected):
        res[spec.name] = train_and_evaluate(p, spec, n_general, selected_or_control=True)
    runs.update(res)
    plan = T.training_plan(p.contract, selected)
    missing = [s.name for s in plan if s.name not in runs]
    if missing or len(runs) != len(plan):
        raise ImplementationFail("training runs %d, plan %d, missing %s" % (len(runs), len(plan), missing))
    p.step_end(6, {"selected": selected, "training_plan": [s.name for s in plan],
                   "runs_completed": sorted(runs), "excluded": p.excluded}, _run_files(res))


def step7(p, runs, n, leakage, selected):
    """Section 8 step 7: G0.8 re-evaluation of F's selected configuration (each of the 3 checkpoints reloaded and
    evaluated a second time), Gate 0 G0.1-G0.10, the section 6 comparisons (reported). Formal: the Gate 0 record is
    committed; ST4 / ST5 when G0.7 / G0.6 do not hold."""
    p.step_start(7)
    seeds = p.contract.training.training_seeds
    repro, files = {}, []
    for seed in seeds:
        spec = runs[_name("F", selected["F"], seed)]["spec"]
        p.before_run(p.eval_seconds("reload"))
        model = p.load_checkpoint(spec, p.ckpt_dir / ("%s.pt" % spec.name))
        ev2 = control_evaluation(p, model, "G0.8 second evaluation of %s" % spec.name, with_em=False)
        del model
        gc.collect()
        repro[seed] = (runs[spec.name]["ev"], ev2)
        files.append(p.write(DETAILS_DIR + "/%s_dev_g08.json" % spec.name, {"kind": "evaluation_details", "model": spec.name,
                                                                     "split": "dev", "evaluation": ev2,
                                                                     "purpose": "G0.8 second evaluation"}))
    # G0.2 reads the values used: a non-finite value in a used run (N, a selected configuration, S, Y, the G0.8
    # re-evaluations) stops the pilot with ST6 before this point; configurations excluded by ST6 during the search
    # (section 7: "出现非有限损失或分数的配置剔除") are not used and are listed in the step 7 record ("excluded"). How G0.2
    # reads an excluded configuration is for Review Gate (reports/IMPL_C_REPORT.md).
    inp = {"leakage": leakage, "all_finite": True, "nonfinite": [], "facts": p.rows["facts.jsonl"], "N": n["summary"],
           "repro": repro}
    for arm in ("F", "L", "A"):
        inp[arm] = {s: runs[_name(arm, selected[arm], s)]["summary"] for s in seeds}
    for arm in p.contract.arms.inheriting:
        inp[arm] = {s: runs[_name(arm, selected["F"], s)]["summary"] for s in seeds}
    values = G.compute_values(inp, p.contract)
    judged = G.judge(values, p.contract, p.mode)
    comparisons = G.report_comparisons(inp, p.contract, "dev")
    s_mapping = {s: {k: inp["S"][s][k] for k in ("s_mapping_dev_learned", "s_mapping_cb")} for s in seeds}
    g0_path = p.write(R.GATE0_RECORD, R.gate0_record(p.fz, p.mode, judged))
    p.log("Gate 0: %s %s" % (judged["gate0_status"], judged.get("reasons") or judged.get("note") or ""))
    rec = {"values": values, "gate0": judged, "comparisons": comparisons, "s_own_mapping": s_mapping,
           "excluded": p.excluded, "smoke_stops": p.smoke_stops}
    p.step_end(7, rec, [g0_path] + files, "metrix: E1-PILOT formal step 7 (Gate 0 record)")
    sat = {c: judged["conditions"][c]["satisfied"] for c in G.CONDITIONS}
    p.stop_check(STP.st4, p.fz, sat["G0.7"])
    p.stop_check(STP.st5, p.fz, sat["G0.6"])
    return values, judged, g0_path


def step8_freeze(p, runs, selected, content):
    """Section 8 step 8, first part (formal, Gate 0 PASS): the freeze record of the selected configurations, the data
    content hashes and the 30 checkpoint hashes, bound to the committed Gate 0 record; committed and pushed. TEST is
    not generated here (test-generate, on the Owner's decision)."""
    p.step_start(8)                                     # ST12, ST13, the commit preconditions
    _, g0_sha = R.committed_json(p.root, R.GATE0_RECORD_REL)
    plan = T.training_plan(p.contract, selected)
    checkpoints = {s.name: runs[s.name]["state_sha256"] for s in plan}      # excluded runs included (their stop state)
    rec = R.selection_freeze_record(p.fz, p.mode, selected, content, checkpoints, g0_sha)
    problem = R.freeze_record_problem(rec, p.contract, p.fz.check_data_dir(p.data_dir), g0_sha)
    if problem:
        raise ImplementationFail("freeze record: %s" % problem)
    path = p.write(R.SELECTION_FREEZE_RECORD, rec)
    p.step_end(8, {"freeze_record": p.rel(path), "gate0_record_sha256": g0_sha, "excluded": p.excluded}, [path],
               "metrix: E1-PILOT formal step 8 freeze record (selected configurations, data hashes, checkpoint hashes)")
    return path


def step8_smoke_refusal(p):
    """Smoke, step 8 (Implementation Task Order V1 sections 6 item 9 and 7): the TEST generator, run as run_pilot runs
    it (test_generate_command), refuses: RESULT: FAIL, non-zero exit, its --out not created; no TEST file anywhere
    under <work>."""
    p.step_start(8)
    out = p.work / "step8_refused_out"
    if out.exists():
        raise ImplementationFail("%s exists before the refusal test" % out)
    formal = [rel for rel in (R.GATE0_RECORD_REL, R.SELECTION_FREEZE_REL, TG.ST10_RECORD_REL)
              if TG._blob(p.root, "HEAD:%s" % rel) is not None or (p.root / rel).exists()]
    if formal:                          # there the generator's preconditions may hold: it would generate TEST
        raise ImplementationFail("smoke step 8 refused: this checkout holds formal records %s; the refusal test runs "
                                 "only where no Gate 0, freeze or ST10 record exists" % formal)
    r = subprocess.run(test_generate_command(p, out), cwd=str(p.root), capture_output=True, text=True, check=False,
                       env=_subprocess_env())
    lines = (r.stdout or "").strip().split("\n")
    test_files = sorted(str(x) for n in D.TEST_FILES for x in p.work.rglob(n))
    refused = r.returncode != 0 and lines[-1:] == ["RESULT: FAIL"] and not out.exists() and not test_files
    rec = {"command": test_generate_command(p, out), "returncode": r.returncode, "stdout": r.stdout,
           "stderr": r.stderr, "out_exists": out.exists(), "test_files_under_work": test_files, "refused": refused}
    p.log("step 8 (smoke): TEST generator exit %d, last line %r, --out created %s, TEST files %s" % (
        r.returncode, lines[-1:], out.exists(), test_files))
    p.step_end(8, rec)
    if not refused:
        raise ImplementationFail("the TEST generator did not refuse in smoke mode")
    return rec


def _name(arm, config_id, seed):
    """The run name of train.RunSpec.name."""
    return T.RunSpec(arm, config_id, (), seed, "").name


def _run_files(res):
    return [r["record"] for r in res.values()] + [r["details"] for r in res.values() if "details" in r]


# --------------------------------------------------------------------------------------------------- commands

def experiment_values(p, command, status, actual, next_single, runs=None, stop=None):
    """The 20 fields of the protocol section 10 template (record.template_fields)."""
    c = p.contract
    gpu_s = p.clock.used() if p.clock is not None else None
    acc = [plain(json.loads(Path(r["record"]).read_text(encoding="utf-8")).get("accounting"))
           for r in (runs or {}).values() if r.get("finite")]
    return {
        "Experiment ID": experiment_id(p, command),
        "Hypothesis": "none: E1-PILOT has no mechanism hypothesis (protocol sections 1 and 9); it qualifies the "
                      "training-evaluation system",
        "Purpose": C.protocol_line(p.fz.protocol_text, "**唯一问题**"),
        "Independent Variable": "arm (N, F, L, A, S, Y; protocol section 4)",
        "Controls": "N (no learning), S (shuffled label), Y (style only); unread facts (protocol sections 4, 5)",
        "Environment (CPU/GPU, commit, seed)": {"device": p.device_name or p.device, "mode": p.mode.name,
                                                "code_commit": p.code_commit,
                                                "seeds": p.fz.seeds, "training_seeds": c.training.training_seeds,
                                                "environment": R.environment(p.fz, p.device_name or p.device,
                                                                             CP.determinism_settings())},
        "Input (data SHA, split SHA)": {"content_hashes": _safe(lambda: p.fz.check_data_dir(p.data_dir)),
                                        "file_hashes": _safe(lambda: D.file_hashes(p.data_dir)),
                                        "split_manifest_split_sha256": _safe(lambda: json.loads(
                                            (p.root / FZ.SPLIT_MANIFEST_REL).read_bytes())["split_sha256"]),
                                        "model_files_sha256": p.model_files},
        "Hyperparameter budget": {"counts": c.arms.counts, "configs": c.arms.configs},
        "Compute accounting (tokens / steps / FLOPs / wall-clock)": {"runs": acc, "gpu_wall_clock_seconds": gpu_s,
                                                                     "steps": {k: v.get("seconds")
                                                                               for k, v in p.steps.items()}},
        "Expected (pre-registered)": "protocol section 8 Gate 0 table and T1-T3 (thresholds below, from the frozen "
                                     "protocol text)",
        "Acceptance (quantified)": plain(c.gate),
        "Stop Conditions": {"protocol": "section 11, ST1-ST13", "stop": stop, "smoke_recorded": p.smoke_stops,
                            "excluded_by_st6": p.excluded},
        "Positive control result": (actual or {}).get("positive_control"),
        "Negative control result": (actual or {}).get("negative_controls"),
        "Statistical plan": plain(c.statistics),
        "Actual": actual,
        "Status": status,
        "Interpretation": M.SMOKE_GATE_NOTE if p.mode.smoke else (actual or {}).get("interpretation"),
        "Non-claims": "protocol section 1 Non-claims" + ("; smoke values are not results" if p.mode.smoke else ""),
        "Next (single)": next_single,
    }


def _safe(fn):
    """A value for a record of a stopped run: fn() or the error that prevented it (e.g. no data generated yet)."""
    try:
        return fn()
    except Exception as e:           # noqa: BLE001 -- the record of a stopped run is written whatever is missing
        return {"not_available": repr(e)}


def experiment_id(p, command):
    return "METRIX-E1-PILOT-%s-%s" % (command, p.started)


def write_experiment_record(p, command, status, actual, next_single, runs=None, stop=None, outside_repo=False):
    """Protocol section 10: one record per run, stopped runs included; JSON and the template as text. Under the
    records directory, or with `outside_repo` in <work> (a formal run that stopped before step 1, final_record)."""
    values = experiment_values(p, command, status, actual, next_single, runs, stop)
    env = R.environment(p.fz, p.device_name or p.device, CP.determinism_settings())
    rec = R.new_record(p.fz, p.mode, values["Experiment ID"], plain(values), env)
    name = "experiment_record_%s_%s.json" % (command, p.started)       # one file per run: none overwritten
    if outside_repo:
        p.work.mkdir(parents=True, exist_ok=True)
        path = p.work / name
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n",
                        encoding="utf-8")
    else:
        path = R.write_record(rec, p.records / name, p.root)
    (path.with_suffix(".txt")).write_text(R.render_text(rec), encoding="utf-8")
    return [path, path.with_suffix(".txt")]


def gate_steps(p):
    """Steps 1-7 (and the step 8 freeze record or the smoke refusal). Returns (status, actual, next, runs)."""
    content, _ = step1(p)
    leakage = step2(p)
    n = step3(p)
    n_general = n["ev"]["general_dev"]
    runs = p.runs
    selected = {"F": step4(p, runs, n_general)}
    selected.update(step5(p, runs, n_general))
    step6(p, runs, n_general, selected)
    values, judged, _ = step7(p, runs, n, leakage, selected)
    seeds = p.contract.training.training_seeds
    f101 = runs[_name("F", selected["F"], p.contract.training.search_seed)]["summary"]
    actual = {"selected": selected, "gate0": judged, "values": values,
              "positive_control": {"run": _name("F", selected["F"], p.contract.training.search_seed),
                                   "acc_cb": f101["acc_cb"], "acc_dev_learned": f101["acc_dev_learned"]},
              "negative_controls": {"G0.6 (S)": values["G0.6"], "G0.7 (Y)": values["G0.7"], "G0.3 (N)": values["G0.3"]},
              "runs_completed": len(runs), "training_seeds": seeds,
              "interpretation": {"reasons": judged.get("reasons"), "notes": {c: x["note"] for c, x in
                                                                             judged["conditions"].items() if x["note"]}}}
    if p.mode.smoke:
        actual["step8"] = step8_smoke_refusal(p)
        return judged["gate0_status"], actual, "Review Gate reviews the smoke report (C2)", runs
    if judged["gate0_status"] == "PASS":
        actual["freeze_record"] = p.rel(step8_freeze(p, runs, selected, content))
        # Section 9: PASS is Gate 0 and T1-T3; until TEST the pilot stopped without violating a condition: NOT_TESTED
        # (Gate 0 PASS is in Actual; the word for this field is for Review Gate, reports/IMPL_C_REPORT.md).
        actual["gate0_status"] = "PASS"
        return "NOT_TESTED", actual, ("Owner decides on TEST generation (run_pilot.py test-generate, "
                                      "RUNBOOK_A100.md); the pilot's final status follows the TEST confirmation"), runs
    return judged["gate0_status"], actual, "report to the Owner: Gate 0 not passed, no TEST", runs


def run_gate(p, command):
    """The command formal or smoke: steps 1-7 (+ the step 8 part), then the experiment record (also for a stopped
    or crashed run). Returns (completed without a stop, Gate 0 status or the stop's status)."""
    crash, gate0 = None, None
    try:
        p.device_info_record = p.device_check()
        if p.mode.formal:                           # the records name the code that ran (testgate.code_commit)
            p.code_commit = TG.code_commit(p.root)
            p.start_checks(command)
        status, actual, nxt, _ = gate_steps(p)
        gate0 = actual["gate0"]["gate0_status"]
        stop = None
    except ProtocolStop as e:
        status = e.status or "NOT_TESTED"
        actual, nxt = stopped_actual(p, e), "report to the Owner (stop %s)" % (e.stop,)
        stop = {"code": e.stop, "status": e.status, "message": str(e), "void_pilot": getattr(e, "void_pilot", False)}
        p.log("STOP: %s" % e)
    except Exception as e:           # a crash: the record is written (section 10: stopped runs too), then re-raised
        crash = e                    # (NOT_TESTED: the word for a crash is for Review Gate, reports/IMPL_C_REPORT.md)
        status, actual, nxt = "NOT_TESTED", stopped_actual(p, e), "report to the Owner (the run crashed)"
        stop = {"code": None, "status": None, "message": "crash: %r" % (e,)}
    finally:
        p.close_clock()
    final_record(p, command, status, actual, nxt, p.runs, stop)
    if p.mode.smoke:
        report = smoke_report(p, p.runs, actual)
        p.write("smoke_report.json", report)
        print_smoke_report(p, report)
    if crash is not None:
        raise crash
    return stop is None, gate0 if gate0 is not None else status


def stopped_actual(p, e):
    """Actual of a stopped run: the stop, the steps reached (seconds, files) and the step records written; the
    step's own numbers are in its record (Pilot.stop_in_step)."""
    return {"stopped": str(e), "steps": {k: {x: v.get(x) for x in ("seconds", "files")} for k, v in p.steps.items()},
            "step_records": [str(x) for x in p.written if Path(x).name.startswith("step")]}


def final_record(p, command, status, actual, nxt, runs, stop):
    """Write the experiment record; formal: commit and push it. A failing commit or push leaves it in the working
    tree (reported; the Owner decides) and is re-raised only when the run itself did not stop.
    A formal run that stopped before step 1 began (the device check ST8, the code not committed, the commit
    preconditions of step 1) did not start on this machine: its record is written to <work>, outside the repository,
    and nothing is committed (no formal command writes into or pushes from a clone on a machine that is not the
    pilot's); the operator reports it with the log (RUNBOOK_A100.md section 4). This includes ST8 on the A100 host
    (e.g. a 40 GB card), ST12 or ST13 at the start of step 1, the continuity checks (start_checks), and ST12 in
    Pilot() itself (no Pilot, so no record at all: run_pilot.py exits with the traceback). Whether such a record
    belongs in the repository is for Review Gate (protocol section 10; reports/IMPL_C_REPORT.md).
    Records written by the run and not yet committed (a stop or crash inside a step) are committed with it."""
    if p.mode.formal and command == "formal" and not p.step1_started:
        paths = write_experiment_record(p, command, status, actual, nxt, runs, stop, outside_repo=True)
        p.log("experiment record: %s (status %s; the run stopped before step 1: not committed)" % (paths[0], status))
        return paths
    paths = write_experiment_record(p, command, status, actual, nxt, runs, stop)
    p.log("experiment record: %s (status %s)" % (paths[0], status))
    try:
        p.precommit("the experiment record")
        left = [x for x in p.uncommitted if x not in paths]
        p.commit(left + paths, "metrix: E1-PILOT formal %s experiment record (status %s)%s" % (
            command, status, "; %d records of the stopped step" % len(left) if left else ""), "the experiment record")
    except ProtocolStop as e:
        p.log("the experiment record was not committed: %s; it stays in the working tree; report to the Owner" % e)
        if stop is None:
            raise
    return paths


def smoke_report(p, runs, actual):
    """Implementation Task Order V1 section 7: per step seconds, peak memory and files; every G0 value (smoke
    values); the 30 trainings."""
    return {"kind": "smoke_report", "note": M.SMOKE_GATE_NOTE, "device_note": M.SMOKE_DEVICE_NOTE,
            "small_model": smoke_model_config(p), "steps_per_run": p.mode.shortened_steps,
            "steps": {k: {x: v[x] for x in ("seconds", "peak_memory_bytes", "peak_memory_kind", "files")}
                      for k, v in p.steps.items()},
            "g0_values_smoke": (actual or {}).get("values"),
            "gate0_smoke": (actual or {}).get("gate0"),
            "trainings": {name: {"steps_run": json.loads(Path(r["record"]).read_text(encoding="utf-8")).get("steps_run"),
                                 "state_sha256": r.get("state_sha256"), "finite": r["finite"]}
                          for name, r in sorted(runs.items())},
            "trainings_completed": sum(1 for r in runs.values() if r["finite"]),
            "smoke_recorded_stops": p.smoke_stops, "files_written": [str(x) for x in p.written]}


def smoke_model_config(p):
    cfg = smoke_config(p.model_dir)
    return {"config_json_sha256": FZ.file_sha256(p.model_dir / "config.json"), "overrides": SMOKE_MODEL_OVERRIDES,
            "init_seed": SMOKE_INIT_SEED, "config": cfg.to_dict()}


def print_smoke_report(p, rep):
    p.log("SMOKE REPORT (%s)" % M.SMOKE_LABEL)
    for k, v in sorted(rep["steps"].items()):
        p.log("  step %s: %.1f s, peak memory %.1f MiB (%s), %d files" % (
            k, v["seconds"], v["peak_memory_bytes"] / 2 ** 20, v["peak_memory_kind"], len(v["files"])))
    for c, x in ((rep.get("gate0_smoke") or {}).get("conditions") or {}).items():
        p.log("  %s satisfied (smoke value) %s" % (c, x["satisfied"]))
    p.log("  Gate 0 status %s (%s)" % ((rep.get("gate0_smoke") or {}).get("gate0_status"), rep["note"]))
    p.log("  trainings completed: %d; steps per run %s" % (rep["trainings_completed"], sorted(
        {t["steps_run"] for t in rep["trainings"].values()})))


def test_generate_command(p, out):
    """The TEST generator as run_pilot.py runs it (testgate, test_data: main is the only caller of generate_test)."""
    return [sys.executable, "-m", "metrix_e1.test_data", "--inputs", str(p.inputs), "--data", str(p.data_dir),
            "--out", str(out)]


def run_test_generate(p):
    """Section 8 step 8, TEST generation (formal, on the Owner's decision): test_data.main as a subprocess with --out
    <work>/test; its output is passed through; the return code is its exit code. When the generator stopped with ST10
    (its committed ST10 record has a count over its frozen limit), the stop is a protocol stop of the pilot: the
    experiment record (BLOCKED, ST10) is written and committed. A refusal before generation leaves no record."""
    if not p.mode.formal:
        raise ImplementationFail("TEST is generated in formal mode only")
    p.code_commit = TG.code_commit(p.root)
    p.start_checks("test-generate")                 # the same --work as the formal run (device ledger)
    before = TG._blob(p.root, "HEAD:%s" % TG.ST10_RECORD_REL)
    cmd = test_generate_command(p, p.work / TEST_DIR)
    p.log("running %s" % " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(p.root), check=False, env=_subprocess_env())
    over = st10_over_limit(p) if before is None else []       # only an ST10 record committed by this run
    if over:
        stop = {"code": "ST10", "status": "BLOCKED", "message": "TEST part over limit %s (committed %s)" % (
            over, TG.ST10_RECORD_REL)}
        final_record(p, "test-generate", "BLOCKED", {"stopped": stop["message"], "st10_record": TG.ST10_RECORD_REL},
                     "report to the Owner (ST10: TEST is not evaluated)", None, stop)
    return r.returncode


def st10_over_limit(p):
    """The checks of the committed ST10 record over their frozen limits ([] when there is no committed record)."""
    try:
        rec, _ = R.committed_json(p.root, TG.ST10_RECORD_REL)
    except R.NotCommitted:
        return []
    return TG.over_limit(p.fz, rec.get("counts") or {})


def _subprocess_env():
    import os
    env = dict(os.environ)
    src = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def test_evaluate(p):
    """Section 8 step 8, TEST evaluated once (formal): the generator's preconditions again (test_data.check_preconditions:
    ST12, the committed Gate 0 and freeze records, every interpretation ruled) give the TestAuthorization; before the
    marker is written: the continuity checks, the checkpoint files of the marker's models against their committed run
    records, the base model's state hash against N's in the committed step 3 record, and ST7 with the whole TEST
    evaluation as the look-ahead (test_evaluation_seconds, from the committed step 2 record); then
    testgate.begin_test_evaluation (ST10 from the committed records, the marker committed and pushed); every model of
    the marker evaluated once with evaluate_model(split="test") (a non-finite value: ST6 on a selected configuration
    or a control); T1-T3 (gate.judge_test) and the section 6 comparisons on TEST; testgate.finish_test_evaluation
    commits the result: aggregate values and per-fact scores only (no question text, no general-text rows; the
    per-question details stay in <work>/test_details, outside the repository)."""
    from . import test_data as TD
    if not p.mode.formal:
        raise ImplementationFail("TEST is evaluated in formal mode only")
    p.begin_called, p.marker_before_begin = False, None
    p.code_commit = TG.code_commit(p.root)
    p.start_checks("test-evaluate")             # before anything that can stop with a code: a wrong --work is refused
    refuse_if_test_evaluated(p)                 # read-only, before any stop with a code (ST7, ST8, ST9, ST12)
    fz, auth = TD.check_preconditions(p.root, p.inputs, p.data_dir)
    p.fz = fz
    p.device_info_record = p.device_check()
    try:
        p.load_data()
        tdir = p.work / TEST_DIR
        data = dict(p.rows, **{n: FZ.read_jsonl(tdir / n) for n in D.TEST_FILES})
        freeze, _ = R.committed_record(p.root, R.SELECTION_FREEZE_REL, "selection_freeze", fz.record.commit)
        gate0, _ = R.committed_record(p.root, R.GATE0_RECORD_REL, "gate0", fz.record.commit)
        step2, _ = R.committed_json(p.root, "%s/step2_record.json" % R.FORMAL_RESULTS_REL)
        step3, _ = R.committed_json(p.root, "%s/step3_record.json" % R.FORMAL_RESULTS_REL)
        selected = freeze["selected"]
        specs = {s.name: s for s in T.training_plan(p.contract, selected)}
        models = TG.evaluated_models(p.contract, selected)
        for name in models[1:]:                     # before the marker: the files are the ones of the runs
            run_rec, _ = R.committed_json(p.root, "%s/%s/%s.json" % (R.FORMAL_RESULTS_REL, RUNS_DIR, name))
            got = FZ.file_sha256(p.ckpt_dir / ("%s.pt" % name))
            if (got != run_rec["checkpoint"]["file_sha256"]
                    or run_rec["checkpoint"]["state_sha256"] != freeze["checkpoints"][name]):
                raise ProtocolStop(None, "BLOCKED", "checkpoint %s: file sha256 %s, run record %s / freeze record "
                                   "differs; TEST not started; report to the Owner" % (
                                       name, got, run_rec["checkpoint"]["file_sha256"]))
        look_ahead = test_evaluation_seconds(p.contract, step2["preflight"]["timing"])
        n_sha = step3["N"]["state_sha256"]
    except (R.NotCommitted, KeyError, OSError, TypeError, ValueError) as e:
        raise ProtocolStop(None, "BLOCKED", "TEST not started: a committed record, a TEST file or a checkpoint file is "
                           "missing or incomplete (%r); report to the Owner" % (e,)) from e
    head = None
    try:
        p.before_run(look_ahead)                    # ST7: the whole TEST evaluation must fit before it begins
        base = p.base_model()
        base_sha = T.state_sha256(base)
        if base_sha != n_sha:
            raise ProtocolStop(None, "BLOCKED", "the base model's state sha256 %s is not N's %s of the step 3 record; "
                               "TEST not started; report to the Owner" % (base_sha, n_sha))
        p.marker_before_begin = (p.root / TG.MARKER_REL).exists()
        p.begin_called = True                       # run_test_evaluate: TEST counts as begun by this process
        session = TG.begin_test_evaluation(fz, auth, data, base_sha)
        p.log("TEST marker committed and pushed (%s); evaluating %d models once" % (session.marker_commit, len(models)))
        p.rows = data
        summaries, details = {}, p.work / TEST_DETAILS_DIR
        details.mkdir(parents=True, exist_ok=True)
        for name in models:
            p.before_run()
            model = base if name == TG.BASE_MODEL else p.load_checkpoint(specs[name], p.ckpt_dir / ("%s.pt" % name))
            ev = control_evaluation(p, model, "TEST evaluation of %s" % name, split="test", with_em=True,
                                    test_authorization=auth, fz=fz, test_session=session, checkpoint_name=name)
            (details / ("%s_test.json" % name)).write_text(json.dumps(plain(ev), ensure_ascii=False) + "\n",
                                                          encoding="utf-8")
            summaries[name] = p.summary(ev, "test")
            del model
            if name == TG.BASE_MODEL:
                base = None
            gc.collect()
            p.log("TEST %s: acc_test_learned %.4f" % (name, float(summaries[name]["acc_test_learned"])))
        inp = {"facts": p.rows["facts.jsonl"], "N": summaries[TG.BASE_MODEL]}
        seeds = p.contract.training.training_seeds
        for arm in ("F", "L", "A"):
            inp[arm] = {s: summaries[_name(arm, selected[arm], s)] for s in seeds}
        for arm in p.contract.arms.inheriting:
            inp[arm] = {s: summaries[_name(arm, selected["F"], s)] for s in seeds}
        values = G.compute_test_values(inp, p.contract)
        final = G.judge_test(values, gate0["gate0"]["gate0_status"], p.contract, p.mode)
        comparisons = G.report_comparisons(inp, p.contract, "test")
        result = plain({"kind": "test_evaluation_result", "frozen_commit": fz.record.commit, "values": values,
                        "final": final, "comparisons": comparisons,
                        "summaries": {m: _summary_record(s) for m, s in summaries.items()}})
        head = TG.finish_test_evaluation(fz, session, result)
        p.log("TEST result committed and pushed (%s); final status %s" % (head, final["final_status"]))
    finally:
        p.close_clock()
    actual = {"final": final, "values": values, "result_commit": head,
              "interpretation": {"reasons": final.get("reasons"),
                                 "notes": {c: x["note"] for c, x in final["conditions"].items() if x["note"]}}}
    return final["final_status"], actual


def refuse_if_test_evaluated(p):
    """Before test-evaluate does anything that can stop with a stop code: TEST was evaluated (a TEST result in the
    working tree or at HEAD) -> TestAlreadyEvaluated; an earlier run began it (a marker without a result) -> BLOCKED
    without a stop code. Neither writes a record (run_test_evaluate). Read-only and without fetching: begin repeats the
    full check (testgate.refuse_if_marker) after fetching."""
    def present(rel):
        return (p.root / rel).exists() or TG._blob(p.root, "HEAD:%s" % rel) is not None
    if present(TG.RESULT_REL):
        raise TG.TestAlreadyEvaluated("TEST was evaluated (%s exists): no further TEST evaluation" % TG.RESULT_REL)
    if present(TG.MARKER_REL):
        raise ProtocolStop(None, "BLOCKED", "TEST evaluation was already started (%s) and no result was committed: it "
                           "counts as evaluated; no further TEST evaluation; report to the Owner" % TG.MARKER_REL)


def begun_by_this_process(p):
    """TEST counts as begun by this process: begin_test_evaluation was called, the marker did not exist before and
    exists now (it may have raised after writing it: commit, push or the pushed-bytes check)."""
    return p.begin_called and not p.marker_before_begin and (p.root / TG.MARKER_REL).exists()


def run_test_evaluate(p):
    """The command test-evaluate. Before this process began the TEST evaluation (begun_by_this_process), a refusal
    without a stop code (a precondition of the generator, the continuity checks, a committed record or a file, the
    checkout and commit preconditions in begin) leaves no experiment record: nothing was evaluated; a protocol stop
    (ST7 look-ahead, ST8, ST9, ST10, ST12) gets one. TestAlreadyEvaluated (TEST was evaluated by an earlier run) writes
    nothing and is raised: the pilot's status is the one of its result. Once this process began the evaluation, the
    experiment record (BLOCKED for a stop or a crash, KeyboardInterrupt included) is written and committed whatever
    happens; the exception is raised again. Returns (completed without a stop, final status or the stop's status)."""
    from . import test_data as TD
    crash = None
    try:
        status, actual = test_evaluate(p)
        nxt, stop = "Owner and Review Gate read the TEST result (an E1-V1 protocol only after PASS)", None
    except (ProtocolStop, TD.PreconditionFailed) as e:
        p.close_clock()
        code = getattr(e, "stop", None)
        begun = begun_by_this_process(p)
        if not begun and code is None:
            p.log("TEST evaluation refused before it began (nothing evaluated): %s" % e)
            return False, getattr(e, "status", None)
        status = getattr(e, "status", None) or "BLOCKED"
        actual, nxt = {"stopped": str(e), "test_begun": begun}, "report to the Owner (stop %s)" % code
        stop = {"code": code, "status": getattr(e, "status", None), "message": str(e)}
        p.log("STOP (%s): %s" % ("after this process began TEST: TEST counts as evaluated" if begun
                                 else "before TEST began, a protocol stop", e))
    except TG.TestAlreadyEvaluated:
        p.close_clock()
        raise
    except BaseException as e:       # noqa: BLE001 -- a crash or interrupt after the begin is recorded, then raised
        p.close_clock()
        if not begun_by_this_process(p):
            raise
        crash = e
        status, actual, nxt = "BLOCKED", {"crashed": repr(e), "test_begun": True}, ("report to the Owner (crash after "
                                                                                    "the TEST marker)")
        stop = {"code": None, "status": "BLOCKED", "message": "crash after the TEST marker: %r" % (e,)}
        p.log("CRASH after the TEST marker (TEST counts as evaluated): %r" % (e,))
    final_record(p, "test-evaluate", status, actual, nxt, None, stop)
    if crash is not None:
        raise crash
    return stop is None, status
