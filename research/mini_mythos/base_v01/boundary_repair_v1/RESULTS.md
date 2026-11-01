# MYTHOS-DATA-BOUNDARY-REPAIR-V1 results

**DATA-REPAIR PASS. No model was run and no new performance result is claimed.**

Purpose: repair the source-unit defect found after the prior CPU depth experiment, independently verify preservation/tokenization, and freeze valid inputs for a separately registered model experiment.

Environment: designated Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`; existing CPU data environment, Python 3.12.3, PyArrow 19.0.1, NumPy 1.26.4 and tokenizers 0.23.2. No installation, Torch/model import, weight load, GPU, forward, generation or training in this stage.

Input: the unchanged 731216-byte WikiText-2-raw-v1 test Parquet (SHA256 `3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925`), original tokenizer (`e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`), and frozen semantic ledger (`f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3`). Implementation freeze `3ac3ad8e5cc9d3fd6e7d0f21ba834b933917eddc`; branch `mythos-data-boundary-repair-v1`; base checkpoint `a422724a61f2b584a4f2d5543fffe5c71934121c`.

| Gate | Expected | Actual | Status |
|---|---|---|---|
| R0 restoration | Fixed original files, isolated branch, protected upstream/B1 | Restored identities; clean freeze; no model activity | PASS |
| R1 inventory | All 4358 rows; broad heading and block-start inventory | 710 boundary-like rows and 1320 nonempty block starts inventoried | PASS |
| R2 semantics | Reviewed decisions, no unresolved disagreement | 60 article starts; 644 nested headings and 6 continuations retained as body | PASS |
| R3 regressions | Title/continuation confusion, ledger gaps, duplicate sources, tokenizer/window contracts covered | 9 parser + 6 builder + 6 independently implemented auditor tests passed | PASS |
| R4 preservation | Each raw row assigned once; exact row and UTF8 reconstruction | All 4358 rows preserved; formulas and legends remain in their source article | PASS |
| R5 construction | Fixed ranking, 32 distinct reviewed sources, no score selection | 60 eligible sources; 32 selected; 257-token windows and 192 scored target positions | PASS |
| R6 independent audit | Direct re-extraction, independent partition and tokenization, repeat and custody | 76 checks PASS, zero FAIL/BLOCKED; two payloads byte-identical | PASS |
| Historical preservation | Existing evidence and dependencies unchanged | 110 protected file hashes and 3 installed-distribution inventories unchanged; upstream/B1 clean; PR24 head unchanged | PASS |
| New model performance | No computation in this stage | No forward, generation or training | NOT TESTED |

The two builders were distinct fresh processes, PID 41342 and 41380. Audit PID was 41433. They ran once each on 2026-11-01 from 13:44:02 to 13:44:05 UTC. All children were reaped and absent during the preservation check; no retries or post-result code changes occurred. The independent auditor re-extracted the original Parquet, reconstructed all source spans, retokenized every source body and checked every selected token. The 72 external operator checks also passed. Logs/manifests appropriately differ by process and path; only the input and partition payloads are claimed byte-identical.

Frozen payloads, retained externally:

| File | Bytes | SHA-256 |
|---|---:|---|
| inputs.json | 170230 | `3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e` |
| partition.json | 1171400 | `95a217a815596c928a0b721837b567a08ed8c6f667839fdf6d4311113c253aa4` |
| first manifest.json | 6241 | `6593d2a6906fb803af1095fd4f76980d830635b60cb6c50da0d1def00fbb8cf1` |
| independent_audit.json | 96737 | `6f0e15cbdad4d987b2a0fea9166e2ffc9b53bf1f0bd2dc99155329299498aa44` |

Run directory: `/workspaces/mythos-evidence/base_v01/boundary_repair/data-20261101T134401Z`. Full original contexts, Parquet, token vectors and partition remain external; committed evidence includes their byte hashes and paths. Original inventory preparation is `/workspaces/mythos-evidence/base_v01/boundary_repair/preparation-20261101T132448Z`. Export manifests bind all external files; compact committed inventory output omits source-body excerpts.

Selection consequences were measured without reading or recomputing model scores: the old 32 samples map to only 31 reviewed source articles; the new 32 map to 32. There are 30 overlapping sources, one removed source and two added sources. Thirty corrected windows exactly match an old window; two do not. Selection was the preregistered content-hash ranking, unchanged after observing these counts. No old score is reassigned to the new input set.

The old parser treated formula rows 2148 and 2150 inside the article beginning at row 2093 as top-level headings. Both remain body now. The four sports-legend continuations at rows 3416, 3417, 3420 and 3421 also remain body. The general parser requires a complete corpus-bound reviewed ledger and blocks missing or changed candidates; it does not special-case these six row numbers.

The prior depth experiment retains its recorded source-unit FAIL and its article-level bootstrap interpretation remains NOT ACCEPTED. This repair does not establish any depth, quality, efficiency or OpenMythos mechanism improvement. Historical development data are not fresh-test data or demonstrated pretraining-clean data. Distinct source spans do not prove statistical iid. Boundary semantics rely on two internal AI reviews with recorded reading scopes, not human or external independent review. The audit author also reviewed its report; this is not third-party replication.

All development errors remain visible: malformed inventory-script transport failed before imports, an undefined orchestration variable failed before tests, and a pre-freeze Git status whitespace parsing error stopped before staging or formal execution. The corrected attempts and exact records are retained. An intermediate PID metadata mismatch and operator interruption/access classification gaps were corrected during static review before freeze. No formal validation failed and no scientific acceptance threshold changed.

Unchanged boundaries: Parcae upstream at `69284c13746e849104f738d6d1a347b1f457df76`; original B1 checkout at `d88be474ebb2529c5b095e3732b1f25509f9b824`; PR24 head `4308099bfc90d9398f54a47f9272b6bd4582f7b9`. No B1 rerun, A5 relaxation, B2/D2-A, model architecture edit or PR action. B1 A5 and Formal Oracle retain their prior BLOCKED state; `FORMAL_ACCEPTANCE_READY=False`.

Next unique instruction: preregister and freeze a new CPU depth-budget comparison using the corrected input and partition identities above, preserving the official weights and explicit cost/quality controls. Complete its implementation and independent review before any model execution; keep prior V1 results immutable. This data-repair stage is complete and stopped.
