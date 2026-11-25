#!/usr/bin/env python3
"""Stage C, C1, second submission (after Review Gate's ruling on C1 of 2026-11-25): black-box probe of the TEST gates
(src/metrix_e1/testgate.py and evaluate.evaluate_model's TEST path) for the data-auditor, which may run it as a driver
subprocess and must compute the expected outcomes itself (ruling item 5). It runs the package's gate functions on a
repository the caller built and prints one outcome line per operation. The probe of the first submission
(c1_gate_probe.py) is kept as it ran; this one follows the changed interface (no remote or branch arguments, every
interpretation ruled, finish and the ST10 record check added).

  python c1b_gate_probe.py REPO TEST_DIR OP [OP ...]

REPO      a throw-away git repository holding metrix/e1-pilot/PROTOCOL_FROZEN (the real one), the committed Gate 0
          and freeze records (results/gate0_record.json, results/selection_freeze_record.json) and, as the scenario
          needs, the ST10 record, the data-auditor's count and markers; a remote named "origin" with branch "main"
          (testgate.PILOT_REMOTE is "origin").
          The probe refuses to run on this repository or on a clone whose origin is the pilot's repository
          (testgate.CANONICAL_REPO): its begin would commit and push a real marker. For REPO, testgate.CANONICAL_REPO
          is set to the repository of REPO's origin and testgate.PILOT_BRANCH to "main" (printed).
TEST_DIR  a directory outside REPO with test_qa.jsonl and general_test.jsonl (synthetic rows written by the caller).
OP        st10                 testgate.st10_check for the TEST rows of TEST_DIR
          st10rec              testgate.refuse_if_st10_record(REPO)
          marker               testgate.refuse_if_marker(REPO)
          pre                  testgate.check_commit_preconditions(REPO, "the probe's record")
          begin:BASESHA        testgate.begin_test_evaluation(..., base_model_sha256=BASESHA, retries=1)
          gate:NAME:SHA        testgate.require_test_session for checkpoint NAME and a stand-in model whose state
                               sha256 is SHA, then testgate.claim_checkpoint (needs an earlier begin in the same run)
          eval:NAME:SEED       evaluate.evaluate_model(split="test") on a random tiny Qwen3 model (torch.manual_seed(SEED),
                               2 layers, hidden 64; no weights), checkpoint NAME, formal mode, device cpu: a call that
                               passes every gate is refused by require_gpu ("ACCEPTED-BY-GATES")
          finish               testgate.finish_test_evaluation(..., {"probe": "synthetic result"}, retries=1)
          tinysha:SEED         prints the state sha256 of that tiny model (to put into the scenario's records)
The authorization is built from the sha256 of the committed Gate 0 and freeze records of REPO and the frozen commit of
the real PROTOCOL_FROZEN (what test_data.check_preconditions would return once its conditions hold); the frozen files
are frozen.load() of this checkout, re-rooted at REPO. Outcome lines:
  <op> ACCEPT <detail> | <op> REFUSE <message> | <op> STOP <stop code or -> <status> <message>
  | <op> EVALUATED <message> (testgate.TestAlreadyEvaluated) | <op> ERROR <exception>
No TEST row of the real data is generated, read or counted; no model weights; no GPU.
"""
import dataclasses
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PILOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PILOT / "src"))

from metrix_e1 import evaluate as E  # noqa: E402
from metrix_e1 import frozen as FZ  # noqa: E402
from metrix_e1 import leakage as LK  # noqa: E402
from metrix_e1 import mode as M  # noqa: E402
from metrix_e1 import record as R  # noqa: E402
from metrix_e1 import testgate as TG  # noqa: E402
from metrix_e1.errors import ImplementationFail, ProtocolStop  # noqa: E402

GPU_REFUSAL = "formal mode evaluates only on the GPU"


def tiny(seed):
    import torch
    from transformers import Qwen3Config, Qwen3ForCausalLM
    torch.manual_seed(seed)
    cfg = Qwen3Config(vocab_size=151936, hidden_size=64, intermediate_size=128, num_hidden_layers=2,
                      num_attention_heads=4, num_key_value_heads=2, head_dim=16, tie_word_embeddings=True)
    return Qwen3ForCausalLM(cfg).eval()


class _ShaModel:
    """Stands for a model whose train.state_sha256 is `sha` (gate:NAME:SHA): train.state_sha256 is wrapped below to
    return `sha` for these objects only (real models are hashed as before)."""

    def __init__(self, sha):
        self.sha = sha


def _wrap_state_sha256():
    from metrix_e1 import train as T
    real = T.state_sha256
    T.state_sha256 = lambda m: m.sha if isinstance(m, _ShaModel) else real(m)


def committed_sha(repo, rel):
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", "HEAD:%s" % rel], capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


def main():
    args = sys.argv[1:]
    repo, test_dir, ops = Path(args[0]).resolve(), Path(args[1]), args[2:]
    origin = TG.repo_id(TG.remote_url(repo, "origin"))
    if repo == PILOT.parents[1] or origin == TG.CANONICAL_REPO:
        sys.exit("probe refused: %s (origin %s) is the pilot's repository" % (repo, origin))
    TG.CANONICAL_REPO, TG.PILOT_BRANCH = origin, "main"
    print("probe: testgate.CANONICAL_REPO = %r (REPO's origin), testgate.PILOT_BRANCH = 'main'" % origin)
    _wrap_state_sha256()
    fz = dataclasses.replace(FZ.load(), repo_root=repo)
    auth = LK.TestAuthorization(fz.record.commit, committed_sha(repo, R.GATE0_RECORD_REL),
                                committed_sha(repo, R.SELECTION_FREEZE_REL))
    data = {n: FZ.read_jsonl(test_dir / n) for n in ("test_qa.jsonl", "general_test.jsonl")}
    contract_ev = None
    session = None
    for op in ops:
        kind, _, arg = op.partition(":")
        try:
            if kind == "st10":
                print("%s ACCEPT %s" % (op, list(TG.st10_check(fz, auth, TG.rows_hashes_of(data)))))
            elif kind == "st10rec":
                TG.refuse_if_st10_record(repo)
                print("%s ACCEPT no ST10 record" % op)
            elif kind == "marker":
                TG.refuse_if_marker(repo)
                print("%s ACCEPT no marker" % op)
            elif kind == "pre":
                TG.check_commit_preconditions(repo, "the probe's record")
                print("%s ACCEPT" % op)
            elif kind == "begin":
                session = TG.begin_test_evaluation(fz, auth, data, arg, retries=1, sleep=lambda s: None)
                models = json.loads(subprocess.run(["git", "-C", str(repo), "show", "HEAD:%s" % TG.MARKER_REL],
                                                   capture_output=True, text=True).stdout)["models"]
                print("%s ACCEPT marker commit %s models %d" % (op, session.marker_commit, len(models)))
            elif kind == "gate":
                name, sha = arg.split(":")
                TG.require_test_session(fz, auth, session, name, data, _ShaModel(sha))
                TG.claim_checkpoint(session, name)
                print("%s ACCEPT" % op)
            elif kind == "eval":
                name, seed = arg.split(":")
                if contract_ev is None:
                    from metrix_e1 import contract as C
                    contract_ev = C.load(fz).evaluation
                try:
                    E.evaluate_model(tiny(int(seed)), None, data, None, contract_ev, M.FORMAL_MODE, "cpu", split="test",
                                     test_authorization=auth, fz=fz, test_session=session, checkpoint_name=name)
                    print("%s ERROR evaluated on CPU in formal mode" % op)
                except ImplementationFail as e:
                    if GPU_REFUSAL in str(e):
                        print("%s ACCEPT ACCEPTED-BY-GATES (stopped at require_gpu)" % op)
                    else:
                        raise
            elif kind == "finish":
                head = TG.finish_test_evaluation(fz, session, {"probe": "synthetic result"}, retries=1,
                                                 sleep=lambda s: None)
                print("%s ACCEPT result commit %s" % (op, head))
            elif kind == "tinysha":
                from metrix_e1.train import state_sha256
                print("%s ACCEPT %s" % (op, state_sha256(tiny(int(arg)))))
            else:
                print("%s ERROR unknown operation" % op)
        except TG.TestAlreadyEvaluated as e:
            print("%s EVALUATED %s" % (op, str(e).replace("\n", " ")))
        except ImplementationFail as e:
            print("%s REFUSE %s" % (op, str(e).replace("\n", " ")))
        except ProtocolStop as e:
            print("%s STOP %s %s %s" % (op, e.stop or "-", e.status, str(e).replace("\n", " ")))
        except Exception as e:  # noqa: BLE001
            print("%s ERROR %s: %s" % (op, type(e).__name__, str(e).replace("\n", " ")))
        sys.stdout.flush()
    print(json.dumps({"repo_head": subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                                                  text=True).stdout.strip()}))


if __name__ == "__main__":
    main()
