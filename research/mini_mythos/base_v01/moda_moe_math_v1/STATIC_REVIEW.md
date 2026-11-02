# MoDA/MoE source-readiness design review

Status: STATIC IMPLEMENTATION APPROVE, numerical validation NOT TESTED. This reviewer has read source and implementation and written review documents. No fixture, model, GPU, target process or experiment was run by this reviewer. Formal execution still requires the preceding stage's accepted checkpoint, target guard checks and the exact frozen inventory.

## Source facts actually inspected

Read open_mythos/moda.py at OpenMythos d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85, Git blob94f6af593f86410dd20c81510428f5055bd97931, including DeepSeekGate, DeepSeekMoE, balance loss, MoDAAttention, MoDABlock and MoDAModel loss accounting. Git blob and source-byte SHA256 are distinct identities; the execution manifest must bind both.

The source MoDA path uses current causal sequence KV and previous-depth same-position KV under one softmax. It repeats GQA KV heads with repeat_interleave and uses query_head//group correspondence. Its zero-history branch uses scaled_dot_product_attention, whereas nonzero history uses explicit logits and softmax; both need independent checks. The source block writes history from its full output and rotates depth keys once. Source histories are passed explicitly; a full model initializes local history lists per forward.

DeepSeekGate explicitly casts scores to FP32. Calling .double() on a module does not remove this cast. Consequently the protocol separates FP64 MoDA checks from cast-faithful FP32 MoE checks; it makes no all-FP64 MoE or finite-difference-router assertion. Top-K derivatives are meaningful only for the fixed selected branch away from score ties. Dense all-expert computation followed by an independently constructed gather/weighted sum is a useful reference for sparse dispatch.

The balance expression is sum f_i*P_i. The docstring's claim that minimizing this increases overloaded probabilities is backwards. A closed-form derivative test should confirm the implemented formula, and the discrepancy must remain documented without editing source. MoDAModel applies moe_balance_alpha once after averaging the raw per-layer terms; the tiny full-model test is loss accounting only, not a combined-mechanism research result.

## Design acceptance and limitations

Accepted design direction: separate small deterministic source controls, explicit forward references and independent vector-Jacobian comparisons, fixed numeric bounds, causal perturbations, repeat/reload controls and failfast reporting. It is more informative than running the repository's general tests and calling the mechanism ready. The bounds are fixed fixture criteria, not evidence that an untested native140M integration is correct.

Source defaults describe a newly initialized model that combines attention and experts. They do not supply a mapping from pretrained Parcae weights to a complete MoDA/MoE architecture. There is no basis to call a random module replacement a faithful pretrained reproduction or to infer quality from toy losses. Any subsequent low-width residual branch must be labeled as an inspired adaptation and independently controlled.

The sparse-worktree and32MiB evidence allocation avoid another full-checkout/large-logit footprint. After the previous stage, resource admission must use current free bytes rather than old estimates. Preserve256MiB reserve and all old data. The future140M stage may adopt a preregistered streaming independent audit or reduced scored-token budget, but this document does not change previous custody policies or approve discarding old logits.

## Implementation review checklist

- The actual pinned source is imported, its bytes verified before import, and no copied edited implementation substitutes for it.
- Formal runtime guards occur before tests; developer-runtime differences are disclosed.
- MoDA reference explicitly enumerates permitted keys, uses one normalization, and does not reuse source forward or expansion helpers.
- FP64 references use the same converted source RoPE values; no claim of a different untested trigonometric path.
- MoE reference preserves score casts and selected-weight semantics. Unused expert gradients are treated correctly; gate finite differences are not silently introduced.
- Causality tests demonstrate that the perturbation has a downstream effect while earlier outputs remain unchanged.
- Balance-loss derivative and coefficient accounting are independently computed, without differentiating hard counts.
- Reload checks use fresh module instances and exact state/output comparisons where declared.
- Test inventory binds all cases, configuration, seed and tolerance; first failure stops remaining cases with explicit NOT TESTED states.
- Raw reporting preserves evidence and separates MoDA readiness, MoE readiness, target execution and untested140M quality.

## Implementation cross-review before numerical execution

Read shared_helpers.py, test_moda.py and test_moe.py in this package. The current inventory has11 MoDA and9 MoE tests. The source-byte identity supplied by the source custodian is42070 bytes, SHA256335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492; formal source validation remains an operator requirement. This reviewer did not execute even the development numerical tests.

The attention reference independently enumerates per-query legal sequence and depth keys, uses a distinct explicit positional transform, uses head//group selection, and performs one softmax. Main attention and low-width comparisons include independently constructed input/parameter/history gradient graphs. The MoE reference evaluates all experts densely and masks with independently ranked selected scores, matches the FP32 gate semantics, distinguishes unused experts from disconnected selected paths, and checks coefficient accounting and its gradient. No finite-difference claim appears.

Resolved pre-execution findings:

- Runtime now sets2 intra-op/1 inter-op threads, installs environment values before Torch import, records actual state and verifies source import did not change it.
- Input/cache byte immutability, repeat, explicit future-position perturbation and empty-history-after-history controls are included in m11.
- Low-width m09 now compares reference VJPs rather than only checking nonzero gradients.
- Source block causal perturbation m05 uses the predeclared mixed FP32-gate numerical class. Standalone attention m11 uses the FP64 class. Altering future tokens may alter expert dispatch batch shapes, so strict bitwise equality is reserved for identical-input repeat/reload. This was clarified before any numerical execution and does not relax a failed threshold.
- Reload controls compare all state keys and tensor bytes as well as outputs.
- The planned inventory is built before runtime/source admission, allowing preflight BLOCKED reports to identify every unexecuted case as NOT TESTED.

Final static verdict: APPROVE for the reviewed mathematical test implementation, subject to separate launcher/custody review and all target guards. This does not claim that any of the20 numerical tests has passed. Pure attention comparisons, mixed source-block controls, and tiny full-model loss/cache bookkeeping have distinct scopes; none is a140M adaptation or language-quality result.
