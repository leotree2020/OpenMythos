# MYTHOS-ROUTING-FEASIBILITY-CPU-V2 checkpoint

Status: **FAIL**.

Freeze commit: `1ff8c902cb003ba1010be76f067de2708e0206bd`. Branch: `mythos-routing-feasibility-cpu-v2`.

Environment: model Python3.12.3/Torch2.11.0+cpu; CPU FP32,2 intraop/1 interop; existing data env for PyArrow/tokenizers preparation and independent no-Torch audit. No training/GPU.

Read evidence/summary.json for Purpose, Environment, Input, Expected, Actual, checks and error. Read evidence/data/public/completion.json, evidence/audit.json and evidence/worker/public/completion.json when present. No missing stage is PASS.

External raw evidence: `/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v2`. Files present at sealing are bound in EXTERNAL_EVIDENCE_MANIFEST.json; publication.json is a subsequently generated receipt outside that manifest. This checkpoint commit is the subsequent Git HEAD, verified against origin by the operator.

Protected-file/environment preservation results are recorded in custody.json; do not infer unchanged state for any unverified or failed check. No A5 relaxation, B1 rerun, B2/D2-A or PR24 operation was scheduled. Old V1 interpretation remains rejected. 32-call normal-prefix routing feasibility only. A valid all-depth32 result is engineering PASS and scientific early-exit screen FAIL/NO_EARLY_EXIT_ON_THIS_SAMPLE, not implementation failure. Recorded scientific screen: NOT TESTED. Sources are new to the prior Parcae depth/routing inputs only, not guaranteed unseen in earlier project tests or pretraining. No quality, fresh-test, training benefit, ACT superiority or hardware acceptance. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Unresolved: {'type': 'Stop', 'reason': 'Formal worker did not pass; no retry', 'traceback': 'Traceback (most recent call last):\n  File "/workspaces/mythos-routing-feasibility-cpu-v2/research/mini_mythos/base_v01/routing_feasibility_v2/execute_once.py", line 320, in main\n    raise Stop(completion.get(\'Status\') if completion.get(\'Status\') in (\'FAIL\', \'BLOCKED\') else \'BLOCKED\',\nStop: Formal worker did not pass; no retry\n'}

Next unique instruction: review selection, routing distribution and complete overhead. If all32 calls select32, stop expansion and record no early-exit signal on this sample; otherwise freeze a separate quality/cost protocol before new model calls. if blocked or failed, resolve only the recorded cause under a separate protocol. No retry or automatic next phase.
