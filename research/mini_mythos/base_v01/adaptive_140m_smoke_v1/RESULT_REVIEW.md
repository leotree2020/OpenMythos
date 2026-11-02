# Original140M adaptive-depth result review

Purpose: accept or reject the frozen engineering smoke and delimit what the data can establish.
Environment: designated Codespace bookish-pancake-vwqx7rr9x5w3wxjr; Python3.12.3, Torch2.11.0+cpu, CPU FP32,2 intra-op/1 inter-op, deterministic algorithms, no autocast or GPU.
Input: frozen execution5cb0be4d4c6070bcf92d097db664c6c2f4f9e78f; unchanged adaptive controller SHA256daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8; original pinned weights; first1/16/64 tokens of one historical article, seeds3101/3202.
Expected:55calls,6groups, one official model load, native byte identity, repeat/causal controls, unchanged state/files/environments, complete independent audit.
Actual:55/55calls and6/6groups, one load;4811worker PASS/0FAIL;1543independent audit PASS/0FAIL;87operator checks PASS;9/9target helper tests PASS. All63 state_dict tensors were checked against the original binary by the worker; the independent auditor verifies saved state inventories and raw prediction artifacts, not a second full-weight tensor comparison. Independent audit inspected10376704 saved FP32 components and recomputed TV from raw last-position logits. Custody and publication quiescence PASS;100 public evidence files exported, no worker/private raw files or original token IDs.
Status:PASS for this engineering smoke only.

## Observed routing

| Prefix tokens | h0 seed | TV(8,16) | Selected depth |
|---|---:|---:|---:|
|1|3101|0.00000019607260081512867|16|
|1|3202|0.00000018762433532063054|16|
|16|3101|0.14069183081763192|32|
|16|3202|0.1458374981787193|32|
|64|3101|0.08805619749231677|32|
|64|3202|0.08739127400142027|32|

Both natural branches executed, and each selected output matched the corresponding native depth bitwise. This does not establish that routing recognizes task difficulty: there is one article, three prefix lengths and two random initializations. The only16-depth exits were the two single-token inputs. All four longer-prefix cases selected32 and therefore incurred extra readouts without reducing recurrence in those cases.

For selected16 the adaptive path ran32 core-block calls and2 head/readout calls; native16 has32 core-block calls and1 readout. For selected32 it ran64 core-block calls and3 readouts; native32 has64 core-block calls and1 readout. All were observed by hooks, not inferred from a mask.

Instrumented API median seconds across the six heterogeneous groups: native16=0.4073667525, native32=0.7802385890, adaptive=0.8684297750, repeat=0.9361314070. Fixed call order, shared CPU, guards, hashes, full-prefix readouts and observers prevent an uncontaminated speed claim. This record is not positive acceleration evidence and is not a failed preregistered performance test: hardware efficiency was not an acceptance criterion.

## Accepted scope and open questions

Accepted: the isolated frozen controller operates on the original140M model, resumes native recurrence correctly, exercises both exits, preserves causal prefixes and leaves weights/buffers/configuration unchanged under this protocol.

NOT TESTED: language-quality improvement, fresh-test generalization, statistical superiority, useful latency reduction, training/resume behavior and production readiness. No claim of reproducing proprietary Claude Mythos internals or capabilities. The original D1 negative screens and B1 A5 result are unchanged. Formal Oracle remains BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Execution commit5cb0be4d4c6070bcf92d097db664c6c2f4f9e78f; result/evidence checkpoint458679d81c2cd72c217e593eae63ea10e7a40b07; branch mythos-adaptive-depth-140m-smoke-v1. Upstream69284c13746e849104f738d6d1a347b1f457df76 and B1d88be474ebb2529c5b095e3732b1f25509f9b824 were clean before/after; all three protected environments unchanged. Private raw evidence remains /workspaces/mythos-evidence/base_v01/adaptive_140m_smoke/attempt-v1, with hashes in EXTERNAL_EVIDENCE_MANIFEST.json. publication.json was generated after sealing as the receipt.

One UI command-transmission attempt lost multiline separators and produced a Python SyntaxError before executing any Python statement; it created no worktree, claim or model process. The corrected transport then created the isolated worktree and launched exactly one operator (PID9555). There was no model retry or post-result source repair.

Root read the published summaries, worker completion, independent audit, runtime, helper coverage and export/quiescence records. Two internal agents separately accepted the published engineering scope; neither claimed to re-read private tensors. These are internal reviews; external Grok/Claude review was not performed.

## Unique next instruction

Freeze a separate, small prefix-only routing-feasibility/quality-cost protocol on independently selected and hashed source articles before looking at their model scores. Keep the current threshold and weights unchanged. First establish whether realistic prefixes have meaningful16-depth exits after including readout overhead; if routing is effectively all32, do not launch a larger trial or tune this threshold on its test data. A quality comparison must include fixed16/fixed32 and a label-blind compute-matched routing control, with article-level paired analysis and explicit decision gates. That protocol must be reviewed/frozen before any new model call. No B1 rerun, upstream edit, A5 relaxation, B2/D2-A or PR24 action.
