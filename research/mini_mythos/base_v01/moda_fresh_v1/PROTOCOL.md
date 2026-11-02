# MYTHOS-MODA-FRESH-CPU-V1

This is a new, zero-training validation derived from accepted checkpoint `bc6d267cdd8cf9306c1bf08b369cf2b791723d3d`. The previous adaptation experiment and all its evidence remain unchanged. No scientific result is known when this protocol and executor are frozen.

## Purpose and competing explanations

The prior MoDA history branch improved the reused16-article development evaluation relative to native fixed32 and an equal-trainable-parameter current-sequence attention control. The next question is whether those frozen adapters retain the quality signal on project-unseen text, and what complete CPU evaluation cost accompanies it.

Competing explanations remain open: the history path transfers a useful representation; improvement was concentrated in old development texts or their domain; the path only helps some text types; the result depends on the particular frozen random features/training seeds; additional compute provides the benefit. This experiment compares the existing candidates, not all possible MoDA variants. A negative result cannot disprove fully trained MoDA.

## Fixed boundaries

CPU only in Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`. Existing Python3.12.3/Torch2.11.0+cpu/NumPy1.26.4;2 intra-op and1 inter-op threads, deterministic algorithms enabled, CPU FP32 and no enabled autocast. Upstream `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76` stays read-only. Native original model bytes and all63 state entries remain unchanged. Existing four S/H adapters are loaded from the prior sealed run and frozen; no optimizer, backward, gradient accumulation, checkpoint rewrite, model selection, threshold tuning or training is allowed.

No B1 rerun, A5 relaxation, early-stop change, B2/D2-A, GPU, mechanism stacking or PR24 operation. Native fixed32 is used for every measured case. The source MoDA helper remains the already accepted implementation; loading it does not license editing its source.

## New text selection and provenance

Freeze20 distinct eligible texts before any new-text model inference. Each contributes the first129 tokenizer IDs with no added special tokens. Model input is IDs0:128; targets are IDs1:129; score logits positions64:128 against original IDs65:129. This is the same next-token alignment as the accepted adaptation experiment.

The separately frozen data-preparation code, source/revision/hash inventory, deduplication rules and prepared manifest are part of this protocol. They must provide evidence that selected texts were not used in this project's prior training or tuning, with exact-title/text/window and prescribed token-overlap exclusions against the recovered prior project corpus/inputs. All selection decisions are made from source structure, tokenizer lengths and deduplication only, without model scores. No candidate substitution is allowed after model results are visible. Insufficient eligible or confidently excluded texts is BLOCKED. Source collection being new to this project does not establish absence from Parcae pretraining.

The data manifest must PASS and every prepared source/input byte must be pinned in INPUT_MANIFEST before formal source freeze. The new text source, fixed selection rule and exact exclusions are material limitations and must be retained in the final checkpoint. Acquisition/data preparation is a separate stage; formal model validation never downloads a replacement corpus.

## Five frozen configurations and exact counts

Ordered configurations are F32(native), S4101, H4101, S4202, H4202. S is the frozen current-sequence attention adapter; H is the frozen MoDA history adapter. Each trained adapter originally had12288 learned output-projection parameters, with random attention feature parameters fixed. This validation updates none of them.

Use initial-state seeds5101 and5202 for every selected text/configuration. Each case is a text plus initial-state seed; there are40 cases. For case index c, rotate the five configurations by c mod5 in pass0 and use its reverse in pass1. Across40 cases each configuration occupies each position equally often in each pass. The second pass repeats the same texts, initial-state seeds, weights and full32 routing. The complete scored FP32 matrix must have the identical SHA256 on its repeated pass, not only matching argmax/NLL.

Before new-text evaluation, run five separate old-sentinel bridges, one per configuration, against the stored old raw logits and actual h0/RNG hashes. These serve as correctness controls and warmups; they are never mixed into fresh-text metrics/timing. A bridge mismatch stops the entire experiment as BLOCKED/FAIL according to its recorded cause; no new-text replacement result is accepted.

Exact worker budget:1 base-model load,405 calls started/completed(5 bridges+200 unique pass0 calls+200 repeat calls),200 quality rows,200 repeat rows,0 training steps,0 backward calls and0 optimizer steps. All405 calls count even if a later gate fails. Partial counts must be preserved on failure. Each configuration must see precisely20 texts x2 initial-state seeds in each pass.

## Quality acceptance and reporting

Primary comparison H minus F32; secondary H minus matching-seed S. S minus F32 is a descriptive adaptation control. For each adapter training seed separately, average the two h0-seed paired NLL differences within each text, then average20 text-level differences. Accuracy is total correct predictions divided by2560 scored observations per configuration. The same target token appears under both h0 seeds; those observations are not independent samples.

Frozen improvement screen: deltaNLL <= -0.01 nats/token AND deltaAccuracy >= -0.01. A comparison screen PASS requires both4101 and4202 adapters independently meet both margins. Do not average two training seeds to hide a failing seed. If deltaNLL >= +0.01 or deltaAccuracy < -0.01 classify that seed as WORSE; otherwise a nonpassing result is NO_QUALIFIED_IMPROVEMENT. Different seed classifications are MIXED. Report all individual means, deltas, accuracy, per-text results, number of texts improved and worst regressions.

These margins are inherited unchanged practical exploratory screens, not statistical significance or equivalence thresholds. Scientific screen FAIL is a valid negative outcome, separate from an engineering failure; no tuning/retry/next experiment follows it. Final evidence sealing and preservation remain mandatory. Positive screens establish only the bounded new-project-text result for these fixed models/source; population-level generalization, production language quality and equal-compute superiority are not established.

## Complete CPU timing

Measure every one of400 fresh calls with monotonic perf_counter_ns(wall) and process_time_ns(CPU), using the fixed balanced order above. Timing begins before input/target tensor creation and ends after the frozen scorer produces the64-target NLL and argmax count. It includes tensor creation, RNG seed and h0 initialization, observer/hook setup, all native prelude/core32/coda/head operations, attention/history handling, finite checks, hook cleanup and FP64 NLL/argmax scoring. This whole-path endpoint prevents treating only the extra history operator or an early-exit subset as model cost.

Full-matrix serialization/SHA, independent pipe audit and disk evidence writes occur outside that endpoint and are measured/reported separately. Record load time, adapter loading times, all five bridges, per-call model-and-score wall/CPU time, serialization and audit time, and the complete worker process duration including loading, all calls, auditing and preservation. Whole worker duration is not a per-configuration speed measurement. Report paired configuration ratios/differences by pass and by text; do not select the fastest repetition. Timings are descriptive CPU measurements under this machine/runtime, not equal-FLOPs or hardware-efficiency proof. Runtime correctness and complete timing coverage can PASS even when H is slower.

## Independent numerical audit and bounded evidence

Each pass0 scored matrix has shape[64,32768], FP32 little-endian, exactly8388608 bytes. Send the entire matrix via a bounded pipe to a separate NumPy-only auditor. Validate framing, exact byte count, input identity/targets and absence of extra payload. The auditor independently checks every component finite, recomputes FP64 per-token NLL and exact argmax, and records full SHA256, eight1MiB chunk hashes/statistics and all64 token metrics. Worker versus auditor NLL tolerance remains1e-10 and predictions must agree exactly. No torch/model import is permitted in the independent auditor.

All200 pass0 audit records and both passes' complete timing/hash/identity records are retained as losslessly compressed JSON, with unchanged fields. Repeat calls require the exact pass0 full-matrix SHA and h0/RNG identity. The last measured call(pass1 index399: H4202 on text19/h0seed5202 under the fixed order) is the single retained full new sentinel. The independent final audit recomputes this matrix from its retained bytes and reaggregates all quality/timing records.

Before the final successful sentinel exists, a numerical, audit or repeat-hash failure retains the current full scored matrix as failed_logits.bin and stops. Failed raw and success sentinel are mutually exclusive within8MiB. If no matrix exists for the failure, record that fact rather than inventing evidence. Historical full matrices and adapter checkpoints stay retained. On success199 unique new matrices are not retained: full live auditing and compact hashes do not enable retrospective reconstruction of those matrices. No claim of200 retained full-matrix re-audits is allowed.

## Storage and preservation gates

Use the unchanged full-map storage codec. Every physical path stays in the protection inventory even if two paths have identical pins. The previous v2 inventory's25436 path/pin pairs and original v1 inventory's25367 pairs must all be retained exactly; add all32244 physical paths in the accepted full-history ledger, final v2 checkout/run/preparation/parent receipts, all prior protected roots, main-worktree untracked files, both discovery receipts, frozen specification policies and this new frozen source/data. Check both compressed and canonical history-ledger pins, successful completion/classification of every row, and actual current bytes for every historical path. Registered nontext files remain protected and are not dropped from custody.

Formal storage admission is a new zero-training artifact allocation:8MiB raw +12MiB total nonraw +256MiB reserve =289406976 bytes. The12MiB covers the complete new run metadata, public copies, protected gzip copies and4MiB Git/finalization allowance. New source/acquisition/preparation files already occupy disk before admission. Capacity acceptance requires both serialized-artifact proof and actual target scope/gzip measurement; a guessed compression ratio is insufficient. Gzip2MiB physical bound and32MiB decode bound are unchanged. See STORAGE_BUDGET.md and frozen measured receipts.

Data/model inputs, old branches, upstream and dependencies are checked before/after. Complete stored protection inventory is decoded and rehashed at closure. No old file is deleted to make capacity fit. Active experiment workers, changed inputs, insufficient memory/disk, unsafe output paths, wrong branch/freeze, skipped tests, incomplete records, nonfinite output or failed comparisons stop dependent work and preserve actual partial evidence. No automatic retry.

## Freeze, execution and checkpoint

Implement and statically review first, run only small synthetic helper fixtures, preserve developer failures and fixes. Then freeze SOURCE_MANIFEST, INPUT_MANIFEST, TEST_INVENTORY, data and capacity evidence in a commit before the one target attempt. The target repeats the exact helper inventory and requires individual PASS/zero skips, not just exit0. The executor accepts worker coverage and independent audit evidence before reporting engineering PASS.

At phase end retain Purpose, Environment, Input, Expected, Actual and PASS/FAIL/BLOCKED/NOT TESTED, exact base/freeze/result branch and commits, dependencies, scientific screens, timing, evidence pins, unresolved limitations and one next instruction. Public records exclude raw text/token sequences, model tensors and adapter binaries; external manifests bind them. Publication uses a clean frozen checkout and remote-head lease; unsafe publication preserves external evidence and reports BLOCKED.

Formal Oracle remains BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False. This stage stops after evidence/checkpoint publication and read-only acceptance; it does not start another mechanism.
