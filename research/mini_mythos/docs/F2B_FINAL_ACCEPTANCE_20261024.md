# Mini-Mythos P1-N2-F2-B — Final Independent Acceptance

Date: 2026-10-24 (Asia/Tokyo)  
Reviewer: ChatGPT (independent code, artifact, and hash review)  
Decision: **PASS — CPU recurrence mechanism probe only**  
Review type: Static source review + review of Grok-generated CPU execution evidence + independent SHA-256 recomputation. **Not** an independent ChatGPT execution of the model.

## Purpose and scope

Check native upstream Parcae recurrent-core fixed-depth behavior, RNG control, gradient-enabled step ordering, gradient presence and finiteness, selected causal-prefix invariance, and the reliability of the test-side acceptance criteria. No language-model training, CUDA execution, full numerical gradcheck, optimizer validation, or Gate 2.2-C equivalence is implied.

## Source provenance and Git status

- Research repository: `leotree2020/OpenMythos`
- Branch: `mini-mythos-p1c-gate22c-readiness`
- Original F2-B code: `1bebc85a00b5b8629c935b407f81d92aac0355b9`
- R1 revised probe: `daf8850f936e9946faddaaa30ac991afbe229078`
- R2 strict-acceptance probe: `b329cf44957a058516fabc8426157d25d33a5a31`
- Evidence-closure commit: `1ce3db57585c0ae7ae9c432fe6285d9973f19bd7`
- Pinned Parcae HEAD: `69284c13746e849104f738d6d1a347b1f457df76`; closure metadata reports an empty Parcae porcelain status and an import path beneath the Parcae root.
- The closure commit adds **six evidence/documentation files, 493 lines, zero deletions**; the tested script and upstream Parcae code are unchanged in that commit.
- Grok previously reported an unrelated local, uncommitted `gate2_1/TEST_RESULTS.json` modification. This was not changed by the closure commit; the current local working-tree state was not independently inspected by ChatGPT. Preserve it.

## Environment and execution

- Probe interpreter: Python 3.11.2.
- Probe PyTorch: 2.14.1+cpu; device CPU, float32, reported two CPU threads and x86_64.
- Evidence archiver: Python 3.10.21 (distinct from the Python running the probe).
- Command recorded in `RUN_META.json`: `PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 /tmp/om/research/mini_mythos/tests/test_parcae_recurrence_cpu.py --parcae-root /tmp/parcae-src --output /tmp/om/research/mini_mythos/gate2_2/evidence/f2b/closure/F2B_CLOSURE_RESULTS.json --require-pinned`.
- Reported process result: `EXIT:0`; stderr is empty.
- Full dependency environment beyond the explicit versions above is **not** established by this closure alone.

## Experiment inputs and expected behavior

- Model: native Parcae 2/2/2 Prelude/Recurrent Core/Coda; 247,936 parameters; 74 trainable parameter tensors in the tested configuration.
- Fixed seed 42; input length 8, synthetic vocabulary size 128; `state_init=like-init` reseeded for fixed-depth comparisons.
- Pairs: `(0,1)`, `(0,2)`, `(1,1)`, `(2,2)`.
- Expected `torch.is_grad_enabled()` for recurrent-core calls: `[True]`, `[True,True]`, `[False,True]`, `[False,False,True,True]`, respectively.
- Under the same model, seed, inputs and total depth, `(0,2)` and `(1,1)` should have matching forward output but can have different gradients owing to truncated backpropagation.
- Causality tolerance predeclared as 1e-5 for prefix logits when perturbing positions 5, 6, or 7.

## Recorded actual results and adjudication

| Item | Actual | Decision |
|---|---|---|
| Pinned source/import/worktree checks | Matching Parcae SHA, source inside root, empty reported worktree | PASS (recorded run) |
| Four depth pairs | Expected gradient-enabled call order, calls 1/2/2/4 | PASS |
| Fixed-seed repeat | Logits, loss and gradients: maximum reported difference 0 | PASS |
| Gradient coverage and validity | 74/74, no missing, zero or nonfinite gradient tensors | PASS |
| Acceptance negative controls | Synthetic missing and all-zero gradient reports correctly rejected | PASS |
| Equal total depth comparison | `(0,2)` vs `(1,1)`: logits max diff 0; grad max diff 0.3440886437892914 | RECORDED; supports intended truncation |
| Causal prefix checks | Positions 5/6/7 max diff 0 (<1e-5) | PASS within tested conditions |
| Training/evaluation repeat | Two runs per mode repeat exactly | PASS within tested conditions |
| Unseeded initialization | Logit max diff 0.3412642478942871 | RECORDED; expected stochastic `like-init` |

The reviewer inspected the R2 source and the closure JSON/stdout/stderr/exit artifacts from the exact closure commit. Independent SHA-256 recomputation of the GitHub-hosted UTF-8 ASCII file contents matched all four hashes recorded in `RUN_META.json`:

- `F2B_CLOSURE_RESULTS.json`: `698d212612caf5c8bba0304251cc4e55cf2676cf2383ab626eb7701aad70caf3`
- `stdout.txt`: `4164111839e90efccf5b8595f4c076fce5c1019b06212c44289de957e32fec31`
- `stderr.txt`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `exit_code.txt`: `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`

## Limits and unresolved questions

- **NOT TESTED**: independent ChatGPT CPU rerun, full numerical derivative correctness, optimization or language learning.
- **NOT TESTED**: native Parcae `train.py` lifecycle, CUDA/GPU forward-backward, GPU MuonAdamW, GPU performance, distributed execution.
- **NOT TESTED**: Gate 2.2-C numerical equivalence and native checkpoint/RNG resume.
- The original archival host paths and `PYTHONPATH` are environment-specific; future reruns should use the probe's CLI flags and a fresh, pinned CPU environment.
- The parent research branch contains additional commits; avoid bulk merging it into `mini-mythos-research` without separate review.
- This decision closes **F2-B only**, not all of P1-N2 or P1.

## Next experimental instruction: P1-N2-F2-C (CPU)

Perform a **design-first, code-second** numerical gradient correctness test of the pinned native Parcae micro architecture. Freeze RNG/state, use a differentiable full-graph case such as `(0,2)` for autograd versus finite difference on a small selected parameter subset, and define a different truncated-graph surrogate/reference before comparing `(1,1)` gradients. Never compare TBPTT gradients to a finite difference of the untruncated full forward and call that a model error. Set tolerance and pass/fail criteria before running, use CPU, do not edit upstream Parcae or AxoNN, and obtain independent Grok/ChatGPT review. Preserve exact Git status, dependencies, input, expected and actual results, and checkpoint at phase end.
