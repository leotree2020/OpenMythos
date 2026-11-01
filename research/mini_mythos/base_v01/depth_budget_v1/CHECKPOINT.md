# MYTHOS-DEPTH-BUDGET-CPU-V1 checkpoint: ready for first formal run

The experiment still has **no model results**. Preparation1 remains BLOCKED at `2e28a6e865554c5315350c730075fbeecc1b5358`. The distinct isolated preparation recovery was preregistered at `445304332b7290c07ad7f77c3990ad733d1eaa15` and passed without changing either original environment. Corpus identity PASS;32-article input freeze PASS;16/16 development fixtures PASS. Formal model gates and scientific analysis NOT TESTED. `formal_run_started=False`.

Base checkpoint: `2f7529bd057d52d6cfde14bf05c19ea10c3c08a7`. Branch: `mythos-depth-budget-cpu-v1`. The commit containing this checkpoint and the approved source/manifest is implementation freeze A; its exact SHA is recorded by the following execution reservation before any model invocation. Retrieve it via `git log -1 --format=%H -- research/mini_mythos/base_v01/depth_budget_v1/CHECKPOINT.md` at this stage.

Frozen runner SHA: `c6f55d688fbcb64212c09c910710351e550a385f9164e110232772de1d2fe2e7`. Auditor SHA: `2fe59e330f1f82e3078d44b16ba2965d36c928a981e69601f9a0bba63f625539`. Input JSON167672 bytes SHA `f38a1618d7904df7c530d9f0f322949a847befcb75e4177de2bc8e65bc53a315`, external location in INPUT_MANIFEST.json. Internal static review is recorded separately; this is not Claude/Grok/human review.

Dependencies: original model environment remains Python3.12.3/Torch2.11.0+cpu/NumPy1.26.4/tokenizers0.23.2. New preparation-only venv uses PyArrow19.0.1, fixed wheel SHA and unchanged baseline NumPy/tokenizers via read-only .pth. Existing evaluation overlay remains untouched. New data-reader environment does not run the model. Full commands/actual imports/original inventories are in ENVIRONMENT_RECOVERY.json.

Protected states: upstream clean at `69284c13746e849104f738d6d1a347b1f457df76`; B1 clean at `d88be474ebb2529c5b095e3732b1f25509f9b824`; PR24 head observed `4308099bfc90d9398f54a47f9272b6bd4582f7b9`, not operated on. No GPU, optimizer, B1 rerun, B2/D2-A or A5 relaxation.

Unresolved: actual140M gates, depth scores and costs. WikiText is historical development data, pretraining overlap unknown; only one checkpoint is examined. ACT/controller/architectural superiority/fresh-test generalization are NOT TESTED. Historical D1, B1 A5 and partial CORE conclusions remain unchanged. Formal Oracle BLOCKED/NOT_READY; `FORMAL_ACCEPTANCE_READY=False`.

Next unique instruction: reserve one fresh external run, verify clean freeze/source/input identity, then execute only this frozen CPU protocol once with the unchanged3600s launcher ceiling; stop the first formal BLOCKED/FAIL, save complete or partial evidence, independently audit, commit and checkpoint. Do not extend, retry or launch another model experiment in response to the result.
