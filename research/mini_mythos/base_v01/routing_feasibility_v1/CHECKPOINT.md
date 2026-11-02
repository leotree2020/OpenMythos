# MYTHOS-ROUTING-FEASIBILITY-CPU-V1 checkpoint

Status: **BLOCKED**.

Freeze commit: `578a7d21a3b15b2d56378baffab9127c6ac956e9`. Branch: `mythos-routing-feasibility-cpu-v1`.

Environment: model Python3.12.3/Torch2.11.0+cpu; CPU FP32,2 intraop/1 interop; existing data env for PyArrow/tokenizers preparation and independent no-Torch audit. No training/GPU.

Read evidence/summary.json for Purpose, Environment, Input, Expected, Actual, checks and error. Read evidence/data/public/completion.json, evidence/audit.json and evidence/worker/public/completion.json when present. No missing stage is PASS.

External raw evidence: `/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v1`. Files present at sealing are bound in EXTERNAL_EVIDENCE_MANIFEST.json; publication.json is a subsequently generated receipt outside that manifest. This checkpoint commit is the subsequent Git HEAD, verified against origin by the operator.

Protected-file/environment preservation results are recorded in custody.json; do not infer unchanged state for any unverified or failed check. No A5 relaxation, B1 rerun, B2/D2-A or PR24 operation was scheduled. Old V1 interpretation remains rejected. 32-call normal-prefix routing feasibility only. A valid all-depth32 result is engineering PASS and scientific early-exit screen FAIL/NO_EARLY_EXIT_ON_THIS_SAMPLE, not implementation failure. Recorded scientific screen: NOT TESTED. Sources are new to the prior Parcae depth/routing inputs only, not guaranteed unseen in earlier project tests or pretraining. No quality, fresh-test, training benefit, ACT superiority or hardware acceptance. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Unresolved: {'type': 'FileNotFoundError', 'reason': "[Errno 2] No such file or directory: '/workspaces/mythos-evidence/base_v01/depth_budget/preparation-v1-20261101/inputs.json'", 'traceback': 'Traceback (most recent call last):\n  File "/workspaces/mythos-routing-feasibility-cpu-v1/research/mini_mythos/base_v01/routing_feasibility_v1/execute_once.py", line 214, in main\n    actual = info(path)\n             ^^^^^^^^^^\n  File "/workspaces/mythos-routing-feasibility-cpu-v1/research/mini_mythos/base_v01/routing_feasibility_v1/execute_once.py", line 74, in info\n    with Path(path).open(\'rb\') as stream:\n         ^^^^^^^^^^^^^^^^^^^^^\n  File "/usr/lib/python3.12/pathlib.py", line 1015, in open\n    return io.open(self, mode, buffering, encoding, errors, newline)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nFileNotFoundError: [Errno 2] No such file or directory: \'/workspaces/mythos-evidence/base_v01/depth_budget/preparation-v1-20261101/inputs.json\'\n'}

Next unique instruction: review selection, routing distribution and complete overhead. If all32 calls select32, stop expansion and record no early-exit signal on this sample; otherwise freeze a separate quality/cost protocol before new model calls. if blocked or failed, resolve only the recorded cause under a separate protocol. No retry or automatic next phase.

## Post-stop clarification

The current attempt remains BLOCKED before any helper subprocess, data preparation, model import/load or forward. The source freeze and blocked evidence remain unchanged. Target read-only path audit verified that the original inputs are under preparation-v2-20261101/inputs.json (167672 bytes, SHA f38a1618d7904df7c530d9f0f322949a847befcb75e4177de2bc8e65bc53a315); the operator incorrectly reused the corpus preparation-v1 directory. This is an implementation path error, not missing original data or a model failure. No path repair or retry was applied.

The environment listed above describes the intended model runtime; no model runtime was exercised. Partial custody found no Git/package changes, but full artifact baseline capture was incomplete and its status is NOT TESTED. All routing and quality conclusions remain NOT TESTED.

The later evidence/POST_STOP_PATH_AUDIT.json is an additional post-seal record, not part of the original EXTERNAL_EVIDENCE_MANIFEST. Its bytes and digest are versioned by this commit.

Next unique instruction (supersedes generic text above): under a separate continuation protocol, correct only the historical input path to the verified v2 artifact, preflight every required path and hash before freezing, and use a new attempt directory. Keep this stopped attempt immutable, the controller threshold0.01 and upstream unchanged. No such continuation was executed in this stage.
