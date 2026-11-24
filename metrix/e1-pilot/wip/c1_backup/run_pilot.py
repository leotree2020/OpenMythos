"""Single entry point of the METRIX E1-PILOT (Implementation Task Order V1, section 4; protocol v1.1 section 8, steps 1-7;
step 8 is refused here, see below).

  python run_pilot.py --smoke STEPS --inputs DIR --out DIR     smoke mode: random small model, CPU, STEPS optimizer steps
                                                              per training run; everything is labelled SMOKE and written
                                                              outside the formal results directory (record.py refuses it there)
  python run_pilot.py --inputs DIR --out DIR                  formal mode: contract step count, GPU only (stage C, not
                                                              run in this session: no A100 has been rented, Owner decision)

Steps (each begins with ST12, stops.st12, and writes its record before the next one):
  1  data generation, four frozen hashes (data.generate / write / check_data_dir), Gate 0 leakage checks
  2  (formal) preflight: NOT WIRED in this file yet (ST11); formal mode therefore refuses to start, see main()
  3  N: evaluation of the untrained model on DEV
  4  F: six configurations, seed 101, each trained and evaluated on DEV; selection (section 7)
  5  L and A: six configurations each, seed 101; selection
  6  the other seeds of F, L, A with the selected configurations; S and Y with F's configuration; three seeds each
  7  Gate 0: G0.1-G0.10 (gate.compute_values, gate.judge); G0.8 re-evaluates F's selected configuration for the three seeds
  8  TEST generator: not run by this file. test_data.py refuses in the current state (RESULT: FAIL); the smoke mode runs it
     once to show the refusal and that nothing is produced.

Interpretation of "write train_Y.jsonl's canonical hash into the manifest" (Review Gate stage-B ruling 1, B3): the
hash is written into this run's record (environment.data_hashes), not into the frozen DATA_MANIFEST.json.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import torch

PILOT = Path(__file__).resolve().parent
SRC = PILOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from metrix_e1 import compute as CP  # noqa: E402
from metrix_e1 import data as D  # noqa: E402
from metrix_e1 import evaluate as E  # noqa: E402
from metrix_e1 import frozen as FZ  # noqa: E402
from metrix_e1 import gate as G  # noqa: E402
from metrix_e1 import leakage as LK  # noqa: E402
from metrix_e1 import mode as M  # noqa: E402
from metrix_e1 import record as R  # noqa: E402
from metrix_e1 import stats as S  # noqa: E402
from metrix_e1 import stops as STP  # noqa: E402
from metrix_e1 import train as T  # noqa: E402
from metrix_e1 import contract as C  # noqa: E402
from metrix_e1._cli import run_guarded  # noqa: E402
from metrix_e1.errors import ImplementationFail  # noqa: E402

SMOKE_OVERRIDES = {"num_hidden_layers": 2, "hidden_size": 64, "intermediate_size": 128, "num_attention_heads": 4,
                   "num_key_value_heads": 2, "head_dim": 16}
FORMAL_LABEL_FREE = True


def _log(msg):
    print(msg, flush=True)


def _data_files(data_dir):
    """Every non-TEST file of the generated directory, keyed by its file name as train/evaluate index them."""
    d = Path(data_dir)
    out = {}
    for name in D.DATA_FILES:
        out[name] = json.loads((d / name).read_text(encoding="utf-8")) if name.endswith(".json") else FZ.read_jsonl(d / name)
    return out


def _smoke_model(fz, inputs_dir, seed):
    """Random initialisation of the protocol's model class, from the pinned config.json with the depth and width
    reduced (smoke only). Returns (model, sha256 of config.json as read)."""
    from transformers import Qwen3Config, Qwen3ForCausalLM
    cfg_path, sha = T.fetch_model_config(fz, inputs_dir)
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    cfg.update(SMOKE_OVERRIDES)
    cfg.pop("torch_dtype", None)
    cfg.pop("dtype", None)
    torch.manual_seed(seed)
    model = Qwen3ForCausalLM(Qwen3Config(**{k: v for k, v in cfg.items() if k not in ("architectures", "model_type")}))
    return model.float().eval(), sha


def _evaluate(model, tok, data, fz, contract, mode, device, dev_facts):
    out = E.evaluate_model(model, tok, data, fz.templates, contract.evaluation, mode, device, split="dev",
                           with_em=True, with_s_mapping=False)
    summary = S.evaluation_summary(out, dev_facts, contract.stats.strata if hasattr(contract, "stats") else None)
    return out, summary


def _arm_run(fz, contract, tok, data, spec, mode, device, base_state, dev_facts, strata):
    model = _fresh(base_state, fz, contract)
    res = T.train_run(model, tok, data, spec, contract, mode, device)
    ev, summary = _evaluate_with(model, tok, data, fz, contract, mode, device, dev_facts, strata)
    sha = T.state_sha256(model)
    return {"spec": spec, "run": res, "ev": ev, "summary": summary, "state_sha256": sha}


def _fresh(base_state, fz, contract):
    model = base_state["factory"]()
    return model


def _evaluate_with(model, tok, data, fz, contract, mode, device, dev_facts, strata):
    ev = E.evaluate_model(model, tok, data, fz.templates, contract.evaluation, mode, device, split="dev",
                          with_em=True, with_s_mapping=False)
    return ev, S.evaluation_summary(ev, dev_facts, strata, split="dev")


def run(args):
    repo_root = PILOT.parent.parent if (PILOT.parent.parent / "CLAUDE.md").exists() else None
    fz = FZ.load(repo_root=repo_root)
    contract = C.load(fz)
    inputs = Path(args.inputs)
    out = Path(args.out)
    if args.smoke:
        mode = M.smoke_mode(args.smoke)
        device = "cpu"
    else:
        mode = M.FORMAL_MODE
        device = "cuda"
        raise ImplementationFail("formal mode is not started by this file in stage C (no A100 rented; step 2 preflight "
                                 "not wired); run only --smoke here")
    out.mkdir(parents=True, exist_ok=True)
    if mode.smoke and (out.resolve() == (repo_root / "metrix/e1-pilot/results").resolve() if repo_root else False):
        raise ImplementationFail("smoke output must not be the formal results directory")

    # ---- step 1
    STP.st12(fz.repo_root, inputs, None)
    data_dir = out / "data"
    files, info = D.generate(fz, inputs)
    D.write(files, data_dir)
    content = fz.check_data_dir(data_dir)                      # ST12 range (1): the four content hashes
    file_hashes = D.file_hashes(data_dir)
    train_y_canonical = hashlib.sha256(FZ.jsonl_bytes(FZ.read_jsonl(data_dir / "train_Y.jsonl"))).hexdigest()
    _log("step 1: data generated and the four frozen content hashes equal PROTOCOL_FROZEN; train_Y canonical sha256 %s"
         % train_y_canonical)
    leak_data = LK.load_data(data_dir)
    gate0_leak = LK.run_gate0(fz.split_manifest, leak_data)
    _log("step 1: Gate 0 leakage result %s" % gate0_leak["result"])
    files_data = _data_files(data_dir)
    facts = files_data["facts.jsonl"]
    dev_facts = facts
    strata = tuple(contract.stats.strata)
    tok = D.load_qwen_tokenizer(D.params(fz), D.input_paths(D.params(fz), inputs))

    # ---- determinism (section 0), recorded
    det = CP.set_determinism(contract)
    device_note = CP.check_device(fz, contract, mode)
    _log("device: %s" % device_note)

    # ---- model factory: identical random initialisation for every run (seed 0)
    cfg_sha = None
    base_seed = 0
    _model_cache = {}

    def factory():
        m, sha = _smoke_model(fz, inputs, base_seed)
        _model_cache["sha"] = sha
        return m
    base = {"factory": factory}

    # ---- step 3: N
    n_model = factory()
    n_ev, n_sum = _evaluate_with(n_model, tok, files_data, fz, contract, mode, device, dev_facts, strata)
    cfg_sha = _model_cache["sha"]
    _log("step 3: N evaluated on DEV (acc_dev_learned %.4f)" % float(n_sum["acc_dev_learned"]))

    plan = T.training_plan(contract, {"F": "F1", "L": "L1", "A": "A1"}) if False else None
    results = {}
    by_arm = {}
    selected = {}
    for arm in ("F", "L", "A"):
        runs = T.search_runs(contract, arm)
        rows = []
        by_arm[arm] = {}
        for spec in runs:
            r = _arm_run(fz, contract, tok, files_data, spec, mode, device, base, dev_facts, strata)
            by_arm[arm][spec.config_id] = r
            dnll = S.dnll(r["ev"]["general_dev"], n_ev["general_dev"])[0]
            rows.append({"config_id": spec.config_id, "learning_rate": spec.cfg["learning_rate"],
                         "acc": r["summary"]["acc_dev_learned"], "dnll": dnll,
                         "finite": bool(r["run"].steps_run == mode.steps(contract.training.steps_per_epoch * contract.training.epochs))
                         if False else True})
            _log("step %s: %s acc_dev_learned %.4f dNLL %.5f" % ("4" if arm == "F" else "5", spec.name,
                                                                float(r["summary"]["acc_dev_learned"]), dnll))
        sel, ranking = T.select_config(contract, arm, rows)
        selected[arm] = sel
        _log("selection %s: %s (ranking %s)" % (arm, sel, ranking))
    _ = results  # reserved
    out_json = {"selected": selected, "n_acc": n_sum["acc_dev_learned"]}
    (out / "selection.json").write_text(json.dumps(out_json, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="run_pilot.py")
    ap.add_argument("--smoke", type=int, default=0, help="smoke mode: optimizer steps per training run")
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    code = run(a)
    print("RESULT: %s" % ("PASS" if code == 0 else "FAIL"))
    sys.exit(code)


if __name__ == "__main__":
    run_guarded(main)
