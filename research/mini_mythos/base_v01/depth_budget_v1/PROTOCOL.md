# MYTHOS-DEPTH-BUDGET-CPU-V1

## Purpose and authorization

Measure the relation between fixed recursive computation and language-prediction loss in the existing released Parcae140M. This is the first measurement toward OpenMythos's computation-budget idea. It does not transplant a learned ACT gate, train a model, change architecture, or claim adaptive execution is implemented. The user's new instruction authorizes autonomous R&D and supersedes the previous checkpoint's suggested GPU-only next action. It does not reopen or resume the stopped official CORE attempt.

Base checkpoint `2f7529bd057d52d6cfde14bf05c19ea10c3c08a7`; isolated branch `mythos-depth-budget-cpu-v1`, changes confined to `research/mini_mythos/base_v01/depth_budget_v1/`. Original Parcae upstream `69284c13746e849104f738d6d1a347b1f457df76` remains read-only. Historical B1 A5, D1, continuation quality and partial CORE statuses remain unchanged. No B1 rerun, B2/D2-A, training, optimizer, GPU, PR24 operation, paid resource or result-dependent retry.

## Mechanism provenance and hypotheses

OpenMythos `open_mythos/main.py` at the base commit, Git blob `65b0fa829f5371d633d2c397bde5175aa73851b4`, defines a shared recursive block and a learned Linear/sigmoid ACT halting gate (lines750–891). Its block is still computed over the whole tensor; partial-token halting is not itself a measured compute saving. We use only the research question of changing recursive compute budgets. No ACT, MoE, MoDA, LoRA, loop-position embedding or dual-state module is installed into the pretrained model.

Competing hypotheses: more recursion reduces prediction loss; the trained depth8 is already saturated so depth4 changes little; or reducing recursion helps some contexts and hurts others. Different outcomes are retained. Prior micro-model depth failures are not erased or extrapolated to this checkpoint.

Primary contrast: article-averaged `NLL(depth4) - NLL(depth8)`. Secondary exploratory contrast: `NLL(depth2) - NLL(depth8)`. Depth8 is the frozen-weight reference, not a separately trained matched Transformer. This experiment cannot identify an architectural advantage over Transformers or the optimum training depth.

## Environment and protected inputs

Designated Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`,2 vCPU/~8GiB RAM. Reuse original CPU environment `/workspaces/mythos-base-v01-cpu312/bin/python`, Python3.12.3 and Torch2.11.0+cpu. Runtime: FP32 model, batch1, `eval()` and no gradients;2 intra-op threads,1 inter-op thread, deterministic algorithms enabled, no enabled autocast, no forced attention backend, no cache. Upstream's disabled-autocast context may exist. Record actual settings, package inventory and warnings. The separate existing evaluation environment is used only for PyArrow/tokenizer preparation; no dependency installation.

Run with `-I -B`; before interpreter startup set `PYTHONDONTWRITEBYTECODE=1`, `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`, `CUDA_VISIBLE_DEVICES=''`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`. Never resolve a venv interpreter symlink to another Python. Protect original environment inventory and upstream Git status before/after.

Original local model directory `/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/model`:

- Weight SHA256 `ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621`.
- Config SHA256 `5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13`.
- Tokenizer JSON SHA256 `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`, original `downloads/tokenizer/tokenizer.json`.

Use the original official `ModelingParcae.from_pretrained` loader on that local directory without config overrides. Independently load original tensors and verify every normalized state_dict key, dtype, shape and bytes, including buffers, against the loaded model; do not replace a buffer or compare only parameters. Model state hashes before/after must match. This establishes restored original-buffer identity, not a retrospective relaxation of historical A5.

## Data freeze before observing model results

Source: `Salesforce/wikitext`, `wikitext-2-raw-v1`, test split, revision `6231e49f19a707241d6b84d9cff60a3a86b85a85`. Parquet731216 bytes, SHA256 `3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925`,4358 text rows. Attribution/licensing: https://huggingface.co/datasets/Salesforce/wikitext, CC-BY-SA-3.0/GFDL. Corpus and token windows remain external with manifests, not copied into Git.

This benchmark was previously used in project development. It is explicitly **historical development data**, not a fresh confirmation set. Whether the released model saw overlapping text during pretraining is unknown. No weights or settings are fitted to these samples in this protocol.

Frozen selection algorithm in `prepare_inputs.py`:

1. A top-level article title is a row whose stripped text begins and ends with `=` and has exactly2 `=` characters. The title starts the next article. Ignore pre-title rows. Body is the unmodified concatenation of subsequent original text rows, with no inserted separators, through the next top-level title. Section headings remain body rows.
2. Encode the body with the exact original tokenizer JSON, `add_special_tokens=False`; add no BOS, EOS, padding or normalization. This differs from CORE's BOS fallback and is a separate language-loss protocol.
3. Eligible articles contain at least257 tokens. Article ID is SHA256 of UTF8 `stripped_title + newline + exact_body`. Sort eligible articles by this ID and take the first32. Require distinct article IDs and body hashes; insufficient inputs are BLOCKED, not an invitation to change sample size after model observation.
4. Take each selected article's first257 token IDs. `input=tokens[0:256]`, `targets=tokens[1:257]`. Score prediction positions64 through255 inclusive:192 tokens. The first64 prediction positions are burn-in; they are still part of the input context. No second shift and no loss on padding.
5. Save source row boundaries, article identities, tokenizer/corpus hashes, exact token vectors and selection metadata externally; commit its file SHA before model execution. Canonical ID hashes use JSON with separators `(',', ':')` and UTF8.

## Controlled conditions and observation

Depths2,4,8 use the same weights and input. Call the original native forward with `labels=None, return_logits=True, num_steps_pair=torch.tensor([depth,0])`, no mask and no padding. Do not change `mean_recurrence`, injection, h0 initialization, weights or RoPE. No generation, sampling or previous probability-sum gate.

Each article has3 h0 replicas with base seeds3101,3202,3303. Actual seed is base seed plus100000×article_index. Capture the complete CPU RNG state and restore it before each depth. Verify the actual returned h0 bytes through a read-only profile observer on `initialize_state`; merely setting equal seed numbers is insufficient. h0 and final RNG hashes must match across each article/replica triple. Profile and forward hooks may count/record only; they must return no replacement tensors and consume no randomness.

Depth execution orders are the lexicographically ordered six permutations of(2,4,8), selected by `(article_index*3 + replica_index) %6`; each occurs16 times. This balances order, but shared-CPU latency is still descriptive. Record actual calls to each Prelude/core/Coda block. Expected block calls are2,2×depth,2 respectively: total8/12/20. Do not call depth4 half of the entire model's compute.

## Gates and expected coverage

All checks have Purpose, Environment, Input, Expected, Actual and PASS/FAIL/BLOCKED/NOT TESTED. Fixture tests use tiny artificial tensors/models only and are development checks, not140M evidence. Freeze implementation, protocol, selected inputs and source hashes before any formal model invocation.

G0: Restore clean base, fixed upstream, original inputs/dependencies and manifest. Missing access/input/environment is BLOCKED; unexplained identity contradictions are FAIL. Save evidence and stop.

G1: Load one official model; exact full state comparison, all parameters FP32/CPU,144323136 parameters,61 unique parameter tensors and63 state_dict entries. Mismatches are FAIL.

G2: Nine controlled forward calls on article0/replica0 before the scientific matrix:

| ID | Call | Required comparison |
|---|---|---|
|C1|Bare native depth8|Reference logits and final RNG|
|C2|Bare official `forward_for_generation`, depth8, no cache|Bitwise equal to C1; final RNG equal|
|C3|Observed native depth8|Bitwise equal to C1; final RNG equal; h0/counters captured|
|C4|Observed native depth8 repeated|Bitwise equal to C3, h0 and RNG equal|
|C5|Observed native depth2, original input|Causal reference depth2|
|C6|Observed native depth2, future-mutated input|Same whole h0; prefix logits equal to C5|
|C7|Observed native depth4, original input|Causal reference depth4|
|C8|Observed native depth4, future-mutated input|Same whole h0; prefix logits equal to C7|
|C9|Observed native depth8, future-mutated input|Same whole h0; prefix logits equal to C3|

Future mutation keeps input shape `[1,256]` and changes only input indices128–255 to `(token_id+1)%32768`. Restore identical RNG before each call; compare logits at positions0–127 bitwise, including signed-zero distinctions. This does not use a shorter input shape. Check each observed call's actual block counts and one h0 observation. An identity, causality, nonfinite or call-count contradiction is FAIL; stop without a repair/retry.

G3: Exactly32×3×3=288 scientific rows, one per article/replica/depth, plus the9 controls. Every full logits tensor must be finite. For scored positions convert the final FP32 logits exactly to FP64; retain per-token FP64 logsumexp, target logit and NLL difference. Independently compute FP64 cross_entropy and compare each per-token value at absolute1e-10, relative0. This is a numerical consistency threshold, not a scientific improvement threshold. Save row means, call counts, h0/RNG hashes, input/target hashes, elapsed forward time and process RSS; flush each row. No hidden retries or altered conditions after seeing results.

G4: Original model state, file/source manifest, upstream and baseline environment preserved; all288 unique rows and terminal completion present. Run the frozen read-only auditor after the model stops; recompute saved losses, coverage, paired summaries and evidence hashes. Only complete engineering/evidence gates can be PASS. Exit0 alone is insufficient.

Use the unchanged previously validated `mythos_launch.py`, SHA256 `8083b948eebdf08c2d14a79d940ccead72db5f10c6bac8d9061816b6c9ea05c3`, in a fresh operator directory with an exclusive claim and **3600-second** ceiling. No parent or child from an earlier experiment is reused. Timeout/missing completion means BLOCKED/PARTIAL; preserve all available records and stop. No third attempts, budget extension or new model experiment in response to these results.

## Scientific report and decisions

Report NLL and corresponding `exp(mean NLL)` by depth over the identical target positions. Aggregate the3 h0 replicas inside each article first, then compare the32 paired article means. Report primary4−8 and secondary2−8 differences, every article's paired effect, sign counts and per-replica summaries.

Exploratory95% bootstrap intervals:10000 resamples of32 whole article indices with replacement, `random.Random(20261101)`, identical resample indices for both contrasts. Percentiles use nearest-rank `ceil(p*n)-1`, p=.025/.975. Token positions and h0 replicas are not independent new documents. These intervals describe this selected development sample, not fresh-test generalization or formal statistical confirmation.

- Positive4−8: reducing depth raises average loss on this probe; report its size and uncertainty.
- Negative4−8: lower-depth prediction is a candidate signal requiring a separate confirmation protocol, not architectural superiority.
- Mixed effects or an interval spanning0: describe uncertainty; do not claim equivalence or absence of any effect.

No universal NLL/PPL pass score, noninferiority margin, confidence threshold for deployment, answer-dependent depth selection or post-hoc best-depth policy. A dynamic controller is NOT TESTED. Runtime summaries include observer overhead and are not hardware-efficiency acceptance. Training usefulness, natural text generation, reasoning gains, equal-compute superiority, candidate selection and full official-score reproduction are NOT TESTED here.

## Deliverables and stop

Commit code, protocol, source/data manifests, development checks, static review, compact original records, independent audit, results and checkpoint. Keep original corpus, tokenizer, weights, environment and any binary state external with hashes. Checkpoint records exact Git commits/branch, dependencies, all outcomes, limitations and a single next instruction determined by the result. No old result or threshold is rewritten. Formal Oracle remains BLOCKED/NOT_READY; `FORMAL_ACCEPTANCE_READY=False`.
