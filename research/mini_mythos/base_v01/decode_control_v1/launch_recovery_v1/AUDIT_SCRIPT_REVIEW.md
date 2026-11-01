# Independent evidence-auditor static review

**Verdict: APPROVE for read-only evidence auditing.** Approval does not imply that the interrupted decoding experiment passed or that the audit script has already run.

| Field | Record |
|---|---|
| Purpose | Check the independent audit script against the frozen producer schema, protected paths, expected counts and partial-run semantics. |
| Environment | Local file/source inspection and SHA-256 verification only; no model, torch, tokenizer, sampling or audit execution by this reviewer. |
| Input | `audit_run.py`, frozen A coordinator/worker/generation sources, and the inherited tokenizer quality helper. |
| Expected | Correct schema and counts; explicit fixed identity; no immutable evidence writes; incomplete runs cannot receive complete acceptance. |
| Actual | The revised script matches the inspected schema, separates sealed-file integrity from experiment coverage, and checks the requested identity and contradictory terminal-state cases. No remaining blocking static defect identified. |
| Status | Static review **PASS**; dynamic audit result remains to be assessed separately. |

Reviewed audit source: **48,662 bytes**, SHA-256 `4c7da8ea1b243f32c0064d12b0a53cef9f5ab03270a628b8465797750f2927eb`.

The complete-run count expectations match the producer: 84 generations, 5,376 trace rows/pre-selection observations/retained last vectors, 768 actual-byte G/history pairs, 72 first-step sampling/G pairs, 1,536 G RNG blocks, 84 automatic-quality records and 126 before/after state rows. Full-prefix hashes, token/EOS/repetition arithmetic, seed identities, selector settings, RNG continuity and full 63-key state coverage use the actual saved field names. Generation ordering follows G, then S panels 1-3, then P panels 1-3.

Two review findings were fixed in this revision:

- Required explicit expected implementation/execution/branch arguments now check coordinator identity and worker implementation. For this attempt use A `e2605841d7eb21c7d8ecbc07aa55ebe6c76f05b7`, R `57d49092b45c855db24b598609f489dcdcf280ea`, branch `mythos-base-v01-decode-control-v1`.
- A complete PASS now requires null stop records, no nonempty cleanup/emergency errors and no exception/emergency evidence files. These requirements are conditional on complete PASS; an honest partial run may retain its interruption evidence.

The script validates manifest membership and hashes, disallows manifest traversal/symlink evidence, compares protected file bytes and tree membership, and writes only an exclusive output outside the run and historical inference tree. Invoke it with the designated external operator output path; do not place its output in another protected checkout or historical evidence tree.

An interrupted loader may legitimately report one attempted call and zero returned models. Missing post-load state/generation records then prevent complete acceptance and remain partial/BLOCKED; they are not automatically converted into a model failure. `sealed_run_file_integrity=PASS` can coexist with experiment `BLOCKED`, `coverage_status=PARTIAL / BLOCKED` and `full_acceptance_established=false`. The recorded D1 stop must remain visible.

The auditor does not regenerate full logits, rerun sampling/tokenizer decoding, reload model tensors, or independently query Git. Full-logit/probability and S/P RNG assertions rely on saved evidence, with retained last vectors/G RNG bytes checked directly. Check records are counted and their statuses validated; exact execution ordering is not independently reconstructed. No data from this attempt were used to alter numerical thresholds or the frozen experiment.
