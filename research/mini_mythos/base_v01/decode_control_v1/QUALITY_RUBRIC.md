# MYTHOS CPU decoding control: frozen quality assessment

Status at freeze: all new decoding outcomes and quality assessments are NOT TESTED.
This rubric is frozen before reading this experiment's generated outputs. It does
not change any historical acceptance, including B1 A5 or the earlier inference
quality FAIL. Engineering acceptance and language-quality screening are separate.

## Purpose, environment, inputs, and expectation

- Purpose: test whether either of two fixed sampling policies meets the existing
  small-model quality screen on the same 12 previously viewed development prompts.
- Environment: the separately frozen CPU decoding protocol, original model and
  tokenizer, unchanged upstream, fixed inputs and deterministic runtime controls.
- Input: exactly 84 planned outputs, each retaining all 64 raw new tokens. No new
  prompt, replacement output, retry, best-of selection, or seed search is allowed.
- Expected: complete engineering evidence; assess the predeclared quality screen
  for each policy without assuming it will pass.
- Actual and PASS / FAIL / BLOCKED / NOT TESTED: recorded only after execution and
  review. Command completion is not evidence of language quality.

| Policy | Role | Settings | Panels | Outputs |
|---|---|---|---|---|
| G | Greedy reference | Greedy, temperature 1, no top-k/top-p | 0 only | 12 |
| S | Primary sampling policy | Sampling, temperature 1, no filtering | 1, 2, 3 | 36 |
| P | Secondary sampling policy | Sampling, temperature 0.8, top-p 0.9, no top-k | 1, 2, 3 | 36 |

Every panel contains prompt IDs 1 through 12 exactly once. The global model seed
is `731000 + prompt_id`. The separate sampling seed is
`841000 + 100 * panel + prompt_id`; G does not draw a sampled token. Seeds are
fixed inputs, not a claim that every later internal state is identical across
different generated prefixes. There is no seed replacement after seeing results.

## Scoring unit and unchanged automatic rules

One scoring unit is one planned `(policy, panel, prompt_id)` output. Retain all 64
raw new token IDs. For scoring, use only tokens strictly before the first raw EOS
ID 1; if there is no EOS, use all 64. Do not include the prompt or EOS itself.
Do not trim whitespace, repair text, remove repeated phrases, or choose a prefix.

The automatic pass requires all five original rules:

1. At least 16 effective continuation tokens.
2. Every contiguous token 4-gram occurs fewer than three times. Count overlapping
   occurrences on effective token IDs, not on text words.
3. The longest run of the same token is fewer than six tokens.
4. Decoding succeeds with `skip_special_tokens=False`.
5. The decoded effective continuation contains no U+FFFD anywhere.

The token-count boundary and repetition thresholds are unchanged. The fixed
64-token cutoff, including a trailing incomplete sentence or UTF-8 fragment, is
not repaired. A U+FFFD still fails the original rule regardless of its cause.
Early EOS, repeated text, or insufficient length is a quality outcome, not an
engineering failure. An invalid token sequence or failed engine guard follows
the separate engineering stop protocol.

## Two independent, blinded AI coherence reviews

Before scoring, prepare a fixed anonymous mapping for all 84 planned samples.
Each reviewer receives the prompt and the complete effective continuation only,
with an anonymous sample ID. Hide policy, panel, seed, automatic pass/fail, and
the other reviewer's labels. Neither reviewer may request another generation.
Retain the mapping and each reviewer's original labels and reasons as evidence.

Each reviewer independently assigns a Boolean `coherent` label and a brief reason.
Use the earlier inference review's distinction between understandable language
and factual correctness; do not copy an old label instead of reading this output.

Assign true when all of the following hold:

- The continuation can be understood in its prompt context.
- It connects to the prompt and maintains a locally interpretable language or
  code structure.
- It is not dominated by meaningless word sequences, unresolved contradictions,
  circular explanation, or structural collapse that prevents interpretation.

Repetition alone does not force coherence false when the repeated content remains
understandable and connected; the unchanged automatic rule assesses repetition
separately. A fixed-length incomplete ending alone does not force false. A wrong
fact or an imperfect code fragment alone does not force false. No complete answer,
high reasoning ability, executable code, or factual correctness is required by
this coherence label.

Assign false when the overall continuation loses meaning or structure. Examples
of applicable distinctions, derived from the historical review, are:

- A readable but factually wrong explanation may be true; give its factual defect
  separately. Two unexplained, incompatible answers to the same definition may
  make the overall explanation incoherent.
- Repeated readable sentences may be true; replacing a causal explanation with
  the event as its own cause can be false.
- An incomplete but structurally interpretable code fragment may be true. A
  function body replaced by unstructured prose can be false because it fails to
  continue the code structure, without requiring a code execution test.
- A counting continuation that loses its sequence rule and collapses into an
  unrelated repeated number can be false.

Record factual, logical, and code issues in a separate field. Use "not assessed"
or "not applicable" where appropriate; do not invent a factual defect or treat a
fictional passage as a factual claim. No model, code, or web execution is needed
for this limited text review. This is AI-assisted screening, not human evaluation
or independent ground truth about competence.

The final coherence label is `review_a is True AND review_b is True`. Keep both
labels and reasons. A disagreement is recorded and conservatively does not pass;
do not negotiate a higher label or replace the reviewer. Any necessary clerical
correction must retain the original record and its explanation, and cannot
change this rubric. Review all planned samples, including automatic failures.

## Primary endpoint and per-panel decision

For policy `j` and panel `r`, define:

`J[j,r] = count(auto_pass AND review_a AND review_b)` across its 12 prompts.

Panel quality PASS requires `J[j,r] >= 9`. The unchanged panel denominator is 12.
For S and P, policy quality PASS requires all three panels to pass separately:

`min(J[j,1], J[j,2], J[j,3]) >= 9`.

S is the primary policy and P is secondary. Do not exchange their roles after
observing results. G is a one-panel reference; its decision is reported separately
and is not an extra pass/fail prerequisite for S or P. Engineering checks on G,
if any, retain their own predeclared meanings.

No pooled threshold, best seed, two-of-three rule, or per-prompt majority vote
replaces this endpoint. In particular, `[8,10,10]` fails despite totaling 28/36.
Per-prompt repeat counts, pooled counts, and the minimum joint count are reported
descriptively. The repetitions share 12 tasks and are not 36 independent tasks.

The summary input is a complete list of rows:
`{id, policy, panel, auto_pass, review_a, review_b}`.
Policy names are exactly G/S/P; panels are G=0 and S/P=1/2/3. IDs are 1..12.
`auto_pass` is Boolean. Review labels are Boolean or explicit null while pending.
Missing rows, duplicate identities, unexpected rows, or malformed fields mean
evidence BLOCKED, not a quality FAIL. Pending labels mean NOT TESTED. Final policy
decisions require all its planned ratings; incomplete evidence is never treated
as a negative language sample or excluded from a denominator.

`quality_summary.py` exposes `summarize_quality(rows)`. Its `assessment_status`
reports whether the evidence and ratings can be summarized (PASS, BLOCKED, or
NOT TESTED); it is not a language verdict. Language verdicts are the separate
policy/panel `quality_status` and primary/secondary/reference fields.

## Stops and three-way interpretation

Do not terminate the planned matrix because an output or a panel appears to fail
a quality rule. Freeze all conditions, finish the matrix if engineering permits,
and make quality decisions at the end. An engineering FAIL or BLOCKED immediately
stops further model computation. Seal partial evidence; unexecuted samples remain
unobserved. The incomplete matrix is BLOCKED for full quality acceptance.

| Observed outcome | Interpretation and next decision |
|---|---|
| All three panels for a sampling policy meet >=9/12 | That fixed policy passed this viewed development screen in three planned repeats. It can be proposed for a separately authorized next validation; this is not generalization or statistical confirmation. |
| Some but not all panels pass, or samples improve without reaching all panel thresholds | Policy screen FAIL; the outcome is mixed or unstable under the frozen requirement. Report every panel, including improvements. Do not rescue it with pooling or new seeds. |
| No panel passes, or sampling produces more visible defects | Policy screen FAIL; these fixed settings were insufficient for this screen. This does not prove that all sampling is ineffective, that weights are corrupt, or that the architecture is flawed. |

Do not claim "no effect" solely from failing the threshold or claim that one
policy is statistically superior from these counts. A quality improvement may
coexist with factual mistakes; report that limitation prominently. If both S and
P pass, report both; if only P passes, retain S's primary failure and report the
secondary success without relabeling P as the original primary endpoint.

Also report the descriptive direction relative to the planned G reference:
more joint passes or fewer recorded defects is an observed improvement, which
does not override a failed all-panel gate; unchanged counts mean no improvement
detected by these measures, not proof of no effect; fewer joint passes or more
recorded defects is an observed deterioration for that condition, not a claim
about all sampling. Report mixed directions explicitly rather than forcing them
into a favorable category. G has one panel and S/P have three; these directional
comparisons are descriptive and are not a matched multi-seed significance test.

## Scope of conclusions

These 12 prompts and their earlier outputs have already been examined. They are
viewed development samples, not a held-out or fresh test. Passing supports only
the specified decoding configuration on this development screen. It does not
establish fresh-test generalization, factual reliability, training or optimizer
resume, architectural improvement, equal-compute superiority, or hardware
efficiency. No automatic B2/D2-A entry follows. Original B1 A5 remains BLOCKED;
Formal Oracle remains BLOCKED / NOT_READY and FORMAL_ACCEPTANCE_READY=False.
