# Independent read-only evidence review — APPROVE

Purpose: audit the completed records independently of the implementation's PASS
summary, while distinguishing engineering success from text-quality failure.
Environment: local standard-library file/hash/JSON review; no torch/model/tokenizer
execution. Reviewer previously reviewed source but did not author the runner.
Inputs: exact 217-file transferred export, full/public manifests, check streams,
state rows, traces, generation records and target read-only audit.
Expected: complete internally consistent evidence with no altered files, accurate
gate aggregation and no unsupported quality/causal/training claims.
Actual / Status: PASS for evidence audit, APPROVE for final interpretation.

Independently rechecked locally:

- 204/204 public manifest files match sizes and SHA256; full manifest contains
  2526 unique paths and the exact matching public subset. Local run export has
  206 files including the two self-excluded manifests.
- 32610 checks PASS: coordinator33, workers17 each, first inference20902,
  reload inference11641. No failed stop/emergency path in completed records.
- 36 generations ×64 steps =2304. Full prefix hashes reconstructed from public
  token IDs agree. Full-logit hashes and last-vector metadata repeat exactly.
- 4608 observer RNG before/after controls agree; all36 method restorations pass.
- Three forward probes, native/generation comparisons and fresh-process controls
  agree. Each worker calls official loader once. Distinct non-overlapping PIDs.
- Four state comparisons total252 rows, complete63-key coverage and tied aliases.
  Logical byte coverage per comparison679004416 includes tied-path duplication.
  State hashes remain the same before/after and across processes.
- 1093 protected files plus checkout and prior-directory membership remain unchanged.
- Independently recomputed quality token rules: all12 have64 effective tokens,
  no EOS, and the only failed automatic rule is repeated4gram. Maximum counts:
  3,5,3,4,3,5,3,3,5,6,6,18. Combined quality is necessarily0/12 FAIL, regardless
  of subjective coherence labels.

Private raw logits were not transferred to the reviewing agent. The actual1536
last-vector byte comparisons and9 full-probe byte comparisons are supported by
the separately read target standard-library audit; no local raw re-comparison or
independent numerical replication is claimed. Finiteness and decode success are
runtime observations, not newly recomputed by this review.

The semantic reviewer read all12 text samples and supplied7 coherent labels;
root independently agrees. The evidence reviewer did not independently grade
that subjective count. Separate AI_QUALITY_REVIEW.json records all labels and
reasons. The immutable runner summary retains PENDING AI REVIEW; the final
checkpoint records the subsequent FAIL without rewriting original evidence.

Accepted conclusion: CPU inference/reload engineering PASS, frozen language-quality
FAIL. A usable language-quality baseline, RoPE-cause explanation and training
recovery have not been established. Stop; no retuning or rerun in this protocol.
