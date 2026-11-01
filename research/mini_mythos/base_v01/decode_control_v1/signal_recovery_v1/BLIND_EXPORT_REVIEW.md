# Blind review export: conditional static APPROVE

Review date: 2026-11-01. Reviewer: separate Codex source-review agent.

This is a source review only. No exporter, auditor, tokenizer, model, or new
generation output was executed or inspected for this review. Runtime validation
and all new quality judgments remain NOT TESTED.

## Sources reviewed

The paths below identify existing local preparation files; this review neither
changes nor copies them.

| Source | SHA-256 |
|---|---|
| `decode_resume_work/make_blind_review.py` | `3f82d161262adba3c09500b8b1f7a02460d82bafa1f6940b908b05358541359e` |
| `decode_resume_work/audit_run.py` | `4c7da8ea1b243f32c0064d12b0a53cef9f5ab03270a628b8465797750f2927eb` |
| `decode_control_work/quality_summary.py` | `95226a18137109f0fea2e00722b189c8078af98776afda694b3f5026145d725c` |
| `decode_control_work/QUALITY_RUBRIC.md` | `ee5a215f884757c30d367963e0aa8438f32e1dd8f76d8d3cb3e6f2ac6c2a18a6` |

All paths are relative to `acceptance_review_local/`. The audit implementation
was previously reviewed; this pass specifically checked its terminal acceptance
fields to define the export precondition precisely.

## Required external gate

APPROVE is conditional on the following operator sequence, agreed before viewing
the new outputs. The exporter alone is not a complete engineering auditor.

1. Run the existing read-only `audit_run.py` against the exact sealed run that
   will be exported. Supply the actual frozen implementation, execution HEAD,
   branch, and frozen history as explicit expected identities. Preserve the
   complete audit JSON and its byte count and SHA-256 outside the immutable run.
2. Require audit `Status == "PASS"`, `Actual.complete == true`,
   `Actual.full_acceptance_established == true`,
   `Actual.coverage_status == "COMPLETE"`,
   `Actual.sealed_run_file_integrity == "PASS"`, empty `failures` and `blockers`,
   and recorded D0 through D4 all PASS. A partial integrity PASS is insufficient.
3. Save an operator binding record with the canonical run path and run ID,
   expected Git identities, audit path/hash, and exact byte counts and SHA-256
   of that run's `FULL_MANIFEST.json` and `public/summary.json`. Recheck those
   same manifest and summary fingerprints immediately before export. Any
   mismatch or unavailable evidence blocks export; do not replace the run.
4. Run the unchanged exporter once into a new external directory. Its provenance
   must identify that same run and the same bound manifest and summary hashes.
   Require `PACK_STATUS.json` PASS before supplying any samples for review.

The existing exporter reads `engineering_status == "PASS"`, verifies all 84
generation records against their manifest entries, but does not independently
validate the full gate graph or bind its input summary to the manifest. The
external audit and binding gate above close that usage gap without changing the
exporter or the frozen experimental rubric.

## Static findings

- The exact G12/S36/P36 matrix is required: all planned policy/panel/prompt
  identities occur once, with filename/identity agreement. Partial exports are
  blocked and must never be reviewed.
- All 84 source generation files must match their sealed size and SHA-256.
  Input/raw/full token coverage, 64 observed steps, and the first-EOS slice are
  checked. The stored effective continuation is copied exactly, including an
  original null with decode-failure evidence. There is no trimming, repair,
  selection, replacement generation, or fresh tokenizer execution.
- `BLIND_SAMPLES.json` contains only `anonymous_id`, `prompt`, and
  `effective_continuation`. Policy, panel, prompt ID, automatic outcome, and
  source paths remain in the separate `MAPPING.json`. No seed field enters the
  blind sample records. All 84 samples, including automatic failures, are kept.
- Give reviewers only the blind sample file and the unchanged coherence rubric.
  Do not give them mapping/provenance files, source records, the other reviewer's
  labels, or inherited condition-specific result context. Preserve both original
  label/reason sets before joining them to the separate mapping.
- `quality_summary.py` uses automatic PASS AND review A AND review B for each
  output; every S/P panel separately requires at least 9/12. All three panels
  must pass. G remains a separate reference. Missing/malformed evidence is
  BLOCKED, pending labels are NOT TESTED, and assessment completeness is not a
  language-quality verdict.

## Limits and unchanged boundaries

Anonymous IDs are deterministic hashes of low-entropy experimental identities;
this provides metadata blinding, not cryptographic anonymity. Similar texts and
previously viewed development prompts may reveal associations. Do not claim
independent human validation, unseen-test generalization, or reviewer independence
from all project history. Source-preserving text export does not independently
prove tokenizer decoding correctness; the prior engineering evidence carries
that separate claim.

PACK_STATUS PASS means a complete, source-bound export only. Audit PASS means
the documented engineering evidence passed its checks. Neither means coherence,
factual correctness, code correctness, statistical superiority, or hardware
efficiency passed. Apply the frozen quality rubric after both reviews.

No upstream edits, threshold changes, B1 rerun, B2/D2-A work, PR #24 merge, or
extra model generation is authorized by this review.
