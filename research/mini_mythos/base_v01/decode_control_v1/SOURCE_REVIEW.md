# Pinned official-source review for the CPU decoding control

Date: 2026-11-01. Review type: read-only source inspection. This document is not
a model execution, a reproduction of the authors' training run, or numerical
evidence that any proposed decoding policy improves quality.

| Field | Record |
|---|---|
| Purpose | Establish the official tokenizer, sequence-boundary, recurrence and generation conventions before freezing an isolated decoding control. |
| Environment | GitHub connector reads of the pinned upstream revision; local standard-library/text inspection only. No model or tokenizer import, numerical evaluation, package installation or upstream write. |
| Input | `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`; the files linked below. |
| Expected | Distinguish directly observed implementation defaults from recommendations, historical-training claims and new research choices. |
| Actual | Conditional generation does not prepend BOS by default; the model configuration uses recurrence 8 and random `like-init` states; sample-task defaults use unfiltered temperature-1 sampling, while another evaluation path uses greedy decoding. The exact original training history and a recommended quality-optimal decoding configuration are not established by these files. |
| Status | PASS for the source-audit task only. All new decoding-control numerical and quality results remain NOT TESTED. |

## 1. Model scope and recurrence

The [pinned README, lines 148-155](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/README.md#L148-L155)
describes the 140M model as having 2 prelude, 2 core and 2 coda layers, embedding
dimension 768 and recurrence 8. It explicitly describes the published models as
base models without instruction tuning. These statements do not establish chat,
instruction-following, factual or code-execution capability.

The [140M configuration, lines 33-44](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/parcae_lm/configs/parcae/parcae-small-140m.py#L33-L44)
specifies diagonal injection, `state_init="like-init"`, `mean_recurrence=8`,
`mean_backprop_depth=4`, `sampling_scheme="poisson-truncated-full"` and
`recurrent_iteration_method="per-sequence"`. The proposed decoding control keeps
the already loaded original configuration and explicitly uses 8 recurrences;
it does not change recurrence depth or train the model.

The [official generation entry, lines 91-113 and 134-142](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/receval/models/parcae.py#L91-L142)
uses `config.mean_recurrence` when `num_steps` is omitted. Supplying an explicit
`num_steps=8` fixes the intended inference depth. The training validation code
also explicitly selects depths using `[depth, 0]` in
[scripts/train.py, lines 604-618](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/scripts/train.py#L604-L618).
That is a validation interface, not proof that every training example had eight
updates or that eight is quality-optimal for every prompt.

## 2. Tokenizer and BOS/EOS conventions

The [tokenizer wrapper, lines 129-184](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/parcae_lm/tokenizer.py#L129-L184)
has `bos=None` and `eos=False` defaults. Explicit `bos=True` or `eos=True` requests
the corresponding boundary token. Its normal text path calls the processor with
`add_special_tokens=False`. The
[tokenizer-training source, lines 28-33 and 89-113](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/scripts/tok_train.py#L28-L113)
defines BOS/EOS/PAD token strings and sets no automatic post-processor. Token
definitions alone do not imply that every call inserts those tokens.

The [official conditioned sample path, lines 125-137](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/scripts/eval.py#L125-L137)
calls `tokenizer.encode(prompt, return_tensors=False)` without requesting BOS or
EOS. By contrast, the
[unconditioned sample path, lines 141-153](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/scripts/eval.py#L141-L153)
starts from a BOS ID. The existing plain-text, no-BOS prompts therefore agree
with the conditioned-sample source convention. This is not evidence that adding
BOS would be beneficial or harmful; BOS is held fixed in the decoding control.

The [evaluation loader, lines 63-73](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/scripts/eval.py#L63-L73)
uses the Parcae evaluation model class and, absent an explicitly supplied
tokenizer path, names `SandyResearch/parcae-tokenizer`. The experiment must keep
the previously pinned local tokenizer bytes and their measured special-token
IDs. It must not redownload an unpinned tokenizer or infer its exact artifact
identity merely from the repository name.

## 3. Training packing: why a default flag is insufficient evidence

[recpre/settings.py, lines 195-198](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/recpre/settings.py#L195-L198)
defaults `add_bos` and `add_eos` to true. However, this does not prove that the
published checkpoint was trained with boundary tokens on every document.

The [140M launch example, lines 62-78](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/launch_configs/parcae-small-140m.yaml#L62-L78)
uses `pack_sequences=True`, `pqds-pure` and a `text` column.
[scripts/train.py, lines 1006-1021](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/scripts/train.py#L1006-L1021)
passes the tokenizer to `ParquetStreamPure`. Its
[raw-text branch, lines 223-236](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/recpre/huggingface_dataset.py#L223-L236)
encodes text without explicit BOS/EOS and yields token tensors. The
[packing collator, lines 91-113](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/recpre/data_loading_utils.py#L91-L113)
returns tensor rows directly; only its dictionary formatting branches apply the
local BOS/EOS options. Thus, following this pinned launch example's raw-text
path does not establish automatic boundary insertion, despite the global defaults.

This is a source-path observation. The original published checkpoint's actual
launch arguments, data contents, preprocessing revision and complete training
logs have not been verified here. Previously tokenized source rows could already
contain boundaries. Do not turn the observed code path into a claim that the
published weights definitely saw, or definitely never saw, BOS/EOS during training.

## 4. Official decoding defaults and limits

The [sample settings, lines 20-29](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/receval/settings.py#L20-L29)
default to 128 new tokens, temperature 1.0, no top-k and no top-p filter. The
conditioned sample call sets `do_sample = temperature > 0`. Conversely,
[receval/tasks/lm_eval.py, lines 68-76](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/receval/tasks/lm_eval.py#L68-L76)
uses temperature 0 and `do_sample=False`. These are different task defaults;
neither file establishes a uniquely recommended or quality-optimal policy.

The [official generator, lines 134-162](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/receval/models/parcae.py#L134-L162)
defaults `use_cache=True`, defaults to sampling, divides logits by the bounded
temperature, optionally applies top-k/top-p, and selects with multinomial or
argmax. It runs the requested number of steps and has no EOS-based early exit.
The top-p mask shifts the cumulative-probability exclusion mask by one position
and always retains its first sorted token.

The CPU control intentionally keeps `use_cache=False`, 64 new tokens, the fixed
12 prompts, CPU FP32 and the already accepted MATH attention context. Accordingly,
S may be called "the official sample-default decoding policy under this frozen
no-cache CPU protocol"; it is not an end-to-end reproduction of every official
sample default. P (`temperature=0.8`, `top_p=0.9`) is a preregistered research
candidate, not a recommendation found in these source files. P changes two
decoding settings together, so S-versus-P cannot separate temperature from
top-p effects.

## 5. Random initial states and sampling isolation

[Parcae.initialize_state, lines 537-550](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/parcae_lm/models/parcae/parcae.py#L537-L550)
uses random draws for `like-init`, including `randn` followed by truncated-normal
initialization. There is no evaluation-mode exemption. Every full-prefix
`forward_for_generation` therefore consumes the model's default CPU RNG stream.

The official generator calls `torch.multinomial(probs, num_samples=1)` without an
explicit generator. Its sampling consequently shares the default RNG with the
model state initialization. Equal initial seeds alone do not hold later h0 draws
fixed when comparing greedy and sampled generation.

Passing `generator=...` to this pinned `model.generate` does **not** fix that
problem: the method accepts `**kwargs` but does not read or forward such a key to
`torch.multinomial`. A Transformers-style generator argument must not be assumed
to work for this custom implementation. The local control loop must explicitly
pass its dedicated CPU generator to the actual sampling operation.

The new isolated research harness is intended to call the unchanged official
`forward_for_generation` for each complete prefix. The model seed is reset once
per generation to `731000 + prompt_id`, after model construction. The sampler
uses a separate CPU `torch.Generator`, with its seed fixed by the protocol as
`841000 + 100 * panel + prompt_id`; the protocol must state panel IDs explicitly.
Do not reset the model seed at each token, change `state_init`, replace weights
or buffers, or monkeypatch global `torch.multinomial`.

Acceptance must verify that sampling leaves the default model RNG unchanged and
that model forward leaves the dedicated sampler RNG unchanged. With no early EOS
stop and identical prompt lengths, all policies use the same input tensor shapes
at corresponding steps. The model RNG before/after trajectories should remain
aligned across policies and panels. Different generated prefixes may still
produce different embeddings, hidden states and logits; equality of RNG streams
does not assert equality of those computations.

Isolating the sampler deliberately changes the complete sampled sequence relative
to the official shared-RNG generator. S tests the official temperature/filter
policy under isolated randomness, not bit-for-bit official sampled-sequence
reproduction. The new G path must instead bridge exactly to the existing greedy
run's fixed inputs, full-logit hashes, retained last-logit bytes and output IDs.
That bridge validates the new control loop without rerunning the old B1 runner.

## 6. Interpretation of the planned matrix

The selected plan has G on 12 prompts, S on 3 panels of 12, and P on 3 panels of
12: 84 fixed 64-token continuations. S is primary; P is secondary. The three
panels vary the sampling stream, not the model weights, h0 seed or prompt set.
They are not three independent model seeds or a fresh held-out evaluation.

The existing automatic repetition/length/decoding rules remain unchanged. The
planned joint quality criterion additionally requires both AI reviewers to mark
the same sample coherent, and requires at least 9/12 joint passes in each panel
for a sampled policy. The numerical protocol must freeze the exact reviewer
rubric, panel identifiers, seeds and decision logic before execution. Agreement
between AI reviewers is not independent human validation or statistical proof.

Free-running comparisons measure the total downstream result of each decoding
policy, including the prefixes that it generates. They do not identify a change
in model conditional probabilities on an identical prefix. An optional fixed-
prefix selection check can inspect policies on the same retained logits without
another model forward, but it cannot replace the free-running quality screen.
No extra teacher-forced model run is required merely to justify causal language.

Failure to satisfy a quality screen is retained as a result, never used to select
new seeds, regenerate prompts or relax rules. Engineering failures stop further
model evaluation immediately. Historical B1 A5 remains BLOCKED, the historical
RoPE creation difference remains UNRESOLVED, and training/resume remain NOT TESTED.
No finding here authorizes upstream changes, B2, D2-A, or PR #24 operations.
