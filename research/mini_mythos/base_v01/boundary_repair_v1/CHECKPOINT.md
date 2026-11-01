# MYTHOS-DATA-BOUNDARY-REPAIR-V1 — completed data-only checkpoint

Status: **PASS** for source-boundary repair, exact preservation, corrected input freeze and independent data audit. Model execution and new scientific performance evidence: **NOT TESTED**. This phase is complete and stopped.

## Restore here

- Repository: `leotree2020/OpenMythos`.
- Branch: `mythos-data-boundary-repair-v1`.
- Base checkpoint: `a422724a61f2b584a4f2d5543fffe5c71934121c` on the prior depth-budget branch.
- Initial data-only protocol: `0c451640f5fb2f800008e70ab7cde0d595e9cf25`.
- Final implementation/protocol/semantic-ledger freeze A: `3ac3ad8e5cc9d3fd6e7d0f21ba834b933917eddc`, pushed before execution; actual clean HEAD/branch/ledger/source hashes were checked before both builds and audit.
- Results and evidence commit B: `8d26c41319b59c2bbfc055217fdefcc1df1d93bf`. Clean worktree after B.
- This checkpoint is a subsequent documentation-only commit; its own SHA is obtained from Git HEAD. Push normally and confirm remote HEAD equality; do not create or merge a PR.
- Isolated target checkout: `/workspaces/mythos-base-v01-rope-diag-v11` in Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`.

## Purpose / environment / input

Purpose: repair and verify the article/source unit used for future CPU depth experiments, after formula lines were incorrectly interpreted as article boundaries. No model score is an input to this repair.

Environment: existing `/workspaces/mythos-depth-data-cpu312/bin/python`, Python3.12.3/PyArrow19.0.1/NumPy1.26.4/tokenizers0.23.2. No new dependency, Torch/model import, model loading, forward, generation, optimizer or GPU. Original model/evaluation environment distributions were inventoried without importing their models.

Inputs: unchanged WikiText-2-raw-v1 test Parquet, 731216 bytes, SHA256 `3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925`; original tokenizer SHA256 `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`; reviewed corpus-bound ledger SHA256 `f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3`. Original decoded-row digest `8a970098c794df2d25494abf3caf6cb8499f57cc54bca35e45b70e168f7d9a74`.

## Expected / actual / acceptance

Expected: complete semantic boundary inventory; no unresolved review decisions; exact reconstruction of all raw rows; 32 distinct reviewed sources selected by the unchanged frozen ranking; independently retokenized identical windows; two fresh processes produce byte-identical payloads; protected historical evidence unchanged. Exit0 alone is insufficient.

Actual:

- R0–R6: PASS. All4358 rows accounted for exactly once and reconstructed without normalization or inserted separators.
- Full inventory: 710 boundary-like rows and1320 nonempty block starts. Sixty accepted article starts;644 nested headings and6 formula/legend continuations remain body. Counts are observed, not a target used to select data.
- Final regression suite:21/21 PASS (9 parser,6 builder,6 independent-auditor synthetic tests).
- Static implementation and operator review: APPROVE by a separate internal agent, with limitations and pre-execution fixes recorded. No human/Claude/Grok/external independent review is claimed.
- Formal run: `data-20261101T134401Z`, once per specified operation. Builder PIDs41342/41380; independent-auditor PID41433. Children finished13:44:03/13:44:04/13:44:05 UTC and were reaped; subsequent process checks found them absent.
- Two builder payloads exactly equal: inputs.json and partition.json. Run metadata/logs differ by process/path as expected.
- Independent audit: **76 PASS / 0 FAIL / 0 BLOCKED**, no error. It directly re-read original rows and independently reconstructed/tokenized every source body, without importing parser/builder.
- External operator:72 guard checks PASS, including actual freeze/clean/ledger identity and child PID binding.
- Source counts:60 reviewed sources,60 eligible,32 selected; each window257 tokens,256 shifted next-token pairs,192 scored target positions.
- Original32 samples map to31 reviewed sources; corrected32 map to32. Thirty source articles overlap; one source removed and two added. Thirty corrected windows equal an old window; two differ. No old scores were read or reassigned.
- Preservation:110 protected files byte-unchanged and3 installed-distribution inventories unchanged. This does not assert every possible environmental state is bit-identical.

## Evidence and immutable corrected inputs

External run: `/workspaces/mythos-evidence/base_v01/boundary_repair/data-20261101T134401Z`.

Use its `build_first/` as the canonical corrected input source:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| inputs.json |170230|`3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e`|
| partition.json |1171400|`95a217a815596c928a0b721837b567a08ed8c6f667839fdf6d4311113c253aa4`|
| manifest.json |6241|`6593d2a6906fb803af1095fd4f76980d830635b60cb6c50da0d1def00fbb8cf1`|
| independent_audit.json (run root) |96737|`6f0e15cbdad4d987b2a0fea9166e2ffc9b53bf1f0bd2dc99155329299498aa44`|

Read `RESULTS.md`, `evidence/independent_audit.json`, `evidence/operator_summary.json`, `evidence/preservation_after.json` and `evidence/selection_change.json`. `COMMITTED_EVIDENCE_MANIFEST.json` binds22 exported reports/logs; `EXTERNAL_EVIDENCE_MANIFEST.json` binds110 external preparation/run artifacts, including the full contexts, partitions, tokens and preserved development errors. Body contexts and token vectors are not committed.

Preparation evidence: `/workspaces/mythos-evidence/base_v01/boundary_repair/preparation-20261101T132448Z`. Early transport/orchestration failures were retained and corrected before freeze: malformed inventory code failed before imports; an undefined operator variable failed before fixture execution; Git-status whitespace handling stopped before staging/commit. No formal data gate failed, no runtime fix/retry occurred after formal results, and no acceptance threshold was changed.

## Unresolved issues and limits

- Prior `MYTHOS-DEPTH-BUDGET-CPU-V1` source-unit FAIL remains. Its article-bootstrap interpretation is NOT ACCEPTED; raw results remain immutable. Do not repair old conclusions retrospectively, merge fragments after seeing scores, or reuse its statistics as V2 evidence.
- The reviewed semantic ledger is tied to this exact corpus; syntax alone cannot establish new article boundaries. Internal reviewers' reading scopes are documented. A different corpus requires its own review.
- Different source articles are not a proof of statistical iid, absence of cross-article dependence, pretraining cleanliness or fresh-test generalization. This remains historical development data.
- Corrected-set model performance, statistical confirmation, generalization, equal-compute superiority and ACT/dynamic-depth benefits remain NOT TESTED in this phase. No new model scores exist.
- B1's frozen A5 remains BLOCKED; no change to its historical acceptance. Formal Oracle remains BLOCKED/NOT_READY; `FORMAL_ACCEPTANCE_READY=False`.
- No upstream edits, B1 rerun, threshold relaxation, B2/D2-A, architecture change or PR24 operation. Protected upstream remains `69284c13746e849104f738d6d1a347b1f457df76` and clean; B1 checkout remains `d88be474ebb2529c5b095e3732b1f25509f9b824` and clean. PR24 head remains `4308099bfc90d9398f54a47f9272b6bd4582f7b9` (head checked; open/draft state not refreshed in this final check).

## Next unique instruction

Under the user's standing autonomous authorization, restore this checkpoint and preregister a new CPU depth-budget comparison using the immutable corrected input/partition above. Keep the official weights and upstream frozen; specify the depth conditions, evaluation RNG pairing, source-level analysis, actual computation costs and acceptance before execution. Freeze and independently review that new protocol and implementation before any model run. Do not overwrite or reinterpret V1. The present data-only phase is complete; no model experiment is part of it.
