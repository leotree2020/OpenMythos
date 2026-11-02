# Depth LoRA worker static review

Scope: research-only hooks on two recurrent c_proj layers. No upstream source,
base parameters/buffers, early-stop controller or threshold is changed.

The native model stays in eval mode while gradients are explicitly enabled for
LoRA training. Every call requests num_steps_pair=[0,32]. No activation
checkpointing or truncated recurrence is allowed. Per-forward hook counters
select depth banks; backward follows the saved graph and never re-reads counters.
Hooks and observed initializer/input attributes are restored in finally blocks.

Shared rank2 has6,144 parameters; depth rank2 has196,608. The shared arm controls
for adaptation with equal active rank and training tokens, not equal parameter
capacity. A depth/shared difference alone cannot establish a capacity-independent
benefit of depth specialization. Fixed32 is a no-adaptation reference.

Both arms initialize the same per-block A matrices with an isolated CPU RNG;
depth copies each matrix across its32 banks. B starts at zero. Global h0 RNG is
reset and actual h0/RNG hashes are paired within evaluation and training arms.
Training seed is distinct from evaluation h0 seed. All128 shifted targets are
trained; evaluation saves/scorers only logits at positions64..127 against body
tokens65..128, so there is no double label shift or future input leakage.

Full original state keys, tensor bytes, finiteness and parameter inventory are
checked after native loading; the native loader strict=False behavior is not
accepted on trust. Base state is hashed before/after and base gradients must stay
absent. Only adapter parameters enter AdamW. Final checkpoints contain adapter,
optimizer and RNG state; new-process verification establishes exact predictive
reload for one preregistered case per adapter, not training-resume equivalence.
Every B bank must receive a nonzero gradient and change from its initial zero;
every A bank must receive a nonzero gradient after the initial zero-B step and
change from its original bytes. Coverage and per-bank hashes are recorded. These
controls establish active updates rather than quality improvement. Optimizer
floating-point state must be finite and all four parameter states must record
exactly32 updates before saving and after reloading.

Formal budget: main293 calls =5 zero controls+128 training+160 evaluation; one
model load. Reload process4 calls/one model load. No best-checkpoint selection,
learning-rate tuning, retries or extra forward probes. Independent auditor judges
scientific screens from raw evaluation logits. A negative scientific screen is
not an implementation failure. Development tests are synthetic CPU tests and
cannot be reported as evidence that real-weight LoRA improves quality.

Risk: full32 backprop uses substantially more memory/time than inference; the
operator must gate available RAM/disk and stop/save on the first engineering
BLOCKED/FAIL. A finite training loss is not a quality result; small fixed training
budget and two seeds cannot establish broad superiority or statistical proof.

Caller obligations: pin source/data/config/weights, preserve source corpus split
separation and prior records, enforce only this target Codespace, export public
metadata only, and audit source/environment/Git custody after execution.
