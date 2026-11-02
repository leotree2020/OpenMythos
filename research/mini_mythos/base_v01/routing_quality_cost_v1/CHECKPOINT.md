# MYTHOS-ROUTING-QUALITY-COST-CPU-V1 — completed checkpoint

Engineering execution and evidence acceptance: **PASS**.
Exploratory quality screen: **PASS**. CPU time screen: **FAIL**. Joint screen: **FAIL**.

The frozen adaptive policy preserves the registered next-token quality tolerance on this sample, but is slower overall than fixed32. This is a valid negative acceleration result, not an implementation failure. No further experiment was started.

## Purpose and frozen inputs

Compare adaptive early exit against fixed32 on the same text and byte-identical initial states, measuring next-token prediction quality and complete guarded public-API CPU latency.

- Base: `a4e9b27ff3c7ca8dbfd5760d5c630f59a9d0a683`.
- Branch: `mythos-routing-quality-cost-cpu-v1`.
- Execution freeze: `9b38408d040f467276c68663642a152dbf25a855`.
- Original result/evidence commit: `5add7a1b51e23cd0d30dc9056ff561184a7711fa`.
- This follow-up changes only this checkpoint and adds `ACCEPTANCE_REVIEW.json`; no frozen execution file or raw result is changed.
- Target Codespace: `bookish-pancake-vwqx7rr9x5w3wxjr`.
- Sixteen unchanged 128-token prefixes, with the actual next body token (index128) as target; initial-state seeds3101 and3202.
- Thirty-two paired cases are sixteen source targets evaluated twice, not thirty-two independent articles or training seeds.
- One official140M model load; 144,323,136 parameters and63 state entries; no training.
- Controller SHA-256: `daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8`.
- Upstream remains read-only at `69284c13746e849104f738d6d1a347b1f457df76`; frozen TV threshold remains0.01.

## Environment and timing scope

Python3.12.3, Torch2.11.0+cpu, CPU FP32,2 intra-op threads and1 inter-op thread, deterministic algorithms, no enabled autocast. Host CPU is AMD EPYC7763; the Codespace exposes2 logical CPUs. Existing dependency environments were retained; detailed inventories and runtime/CPU evidence are committed under `evidence/`.

Both arms were timed through their unchanged public APIs. Timers include current API validation, source hashing, finite checks, recurrence, policy decisions, readouts, state copies and cleanup. Timers exclude tokenization, model loading, RNG reset, external observer hooks and evidence writing. This is hot-model next-token API latency, not end-to-end text-generation, server or production throughput. Two balanced timing rounds reverse arm order; no outlier removal.

## Expected and actual

| Check | Frozen expected | Actual | Status |
|---|---|---|---|
| Development launch/helper checks | All final checks pass before freeze |43/43, local and target |PASS |
| Formal coverage |64 quality calls +2 warmups +128 timed calls, one model load |194/194 calls, one load |PASS |
| Pairing and repeatability |Same prefix, byte-identical h0, timed outputs/depth/RNG/counters match references |All checks passed |PASS |
| Operator / worker controls |No failed or blocked engineering gate |691 operator checks;19,656 worker checks |PASS |
| Independent audit |Recompute saved data, pairing, metrics and frozen screens |1819 PASS /0 FAIL |PASS |
| Quality |Each seed mean delta NLL<=0.01 nats, correct count not lower; every case delta<=0.1 |Means +0.0000529852/+0.0000590786;9/16 correct each arm per seed; max delta+0.0009452574 |PASS |
| CPU latency |Adaptive/fixed32<=0.95 in BOTH rounds |1.146067529 and1.119576696 |FAIL |
| Joint benefit |Quality AND CPU latency screens pass |Quality passes; speed fails |FAIL |
| Evidence seal and custody |Hashes/copies/Git/protected files verified |586 external files;134 exact public copies; clean result HEAD equals remote; custody passed |PASS |

Quality margins are exploratory engineering screens, not a statistical noninferiority test or language-quality acceptance.

## Main results

| Metric | Adaptive | Fixed32 |
|---|---:|---:|
| Mean target-token NLL (nats; lower is better) |2.364599576983525 |2.3645435450928223 |
| Top-1 correct |18/32 |18/32 |
| Mean executed recursion depth |31 |32 |
| Timed API wall seconds,64 calls per arm |166.37196718799987 |146.87411101600082 |
| Timed process CPU seconds |300.1003527740001 |266.08778833100035 |

Top-1 predictions agree in all32 cases. Mean NLL difference is +0.0000560318907030 nats: slightly worse for adaptive, with no positive quality claim.

Wall latency is **13.2752% slower** overall for adaptive; the separate rounds are14.6068% and11.9577% slower. Process CPU consumption is12.7825% greater. Both arm-order groups also favor fixed32.

Only cases8 and9, corresponding to one article under the two h0 seeds, exit at16; the remaining30 cases run32 rounds. Their four timing pairs have a descriptive adaptive/fixed32 ratio0.61118136, but this small subgroup does not change the failed whole-sample speed screen.

Measured recurrence core-block calls total1984 versus2048 (-3.125%). Adaptive also uses94 versus32 head calls and188 versus64 coda-block calls. These counts describe the observed workload; they are not a causal timing decomposition and must not be equated with FLOPs.

Saved floating-point components audited finite:14,680,064, limited to saved h0 and last-logit artifacts. This does not claim all model parameters or intermediate activations were independently audited for finiteness.

## Evidence and preservation

- Public reports: `evidence/summary.json`, `evidence/audit.json`, `evidence/worker/public/`, custody/runtime/development logs and `ACCEPTANCE_REVIEW.json`.
- Raw external evidence: `/workspaces/mythos-evidence/base_v01/routing_quality_cost/attempt-v1`.
- `EXTERNAL_EVIDENCE_MANIFEST.json` binds586 sealed files; `PUBLIC_EXPORT.json` binds134 public exact copies.
- Large/raw tensors remain in the target evidence directory. Git contains public reports, manifests and audit records, not all raw binaries.
- `publication.json` is a later receipt outside the original seal and identifies the original result commit5add7a1b. A subsequent documentation commit does not replace that result identity.
- Root independently checked the full external manifest and public-copy bytes on target after workers stopped. Result worktree was clean at5add7a1b and matched remote.
- Internal worker and data/audit peers recomputed public aggregates. This is internal review, not an external Claude/Grok approval.
- Seven checkout baselines and three dependency inventories preserved. OldV1/V2/V3 records and the existing main-worktree changes were left intact.

## Unresolved and scope limits

The quality sample contains only16 source targets. There is no powered statistical confirmation, fresh-test generalization or broad generation-quality conclusion. Timing has two rounds on a shared CPU, with no cross-machine performance claim. Current validation/policy/readout overhead may matter, but its causal cost decomposition was not tested. This result rejects promotion of this frozen implementation as an effective acceleration method on the measured workload; it does not disprove all adaptive-recursion designs.

B1 and its A5 status are unchanged. No upstream edits, threshold tuning, B1 rerun, B2/D2-A, training, GPU, or PR24 operation occurred. Formal Oracle remains **BLOCKED / NOT_READY**, `FORMAL_ACCEPTANCE_READY=False`.

## Next unique instruction

Plan and freeze a separate depth-specific LoRA controlled CPU protocol under the approved mechanism sequence, retaining fixed32 as comparator and this negative early-exit speed result. Do not tune this policy or launch that next model experiment as part of this completed stage.
