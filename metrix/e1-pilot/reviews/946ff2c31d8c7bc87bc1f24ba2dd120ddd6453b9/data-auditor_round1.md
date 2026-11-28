# data-auditor, PILOT_REPORT_ORDER item 3 (independent recomputation), round 1; final report extracted unchanged from data-auditor_round1_transcript.jsonl
---
## Data Auditor: PILOT_REPORT_ORDER item 3 (independent recomputation of Gate 0 and T1–T3)

**Result: 432 comparison items, 0 inconsistent.** The largest absolute difference is 1.110e-16. All 46 `point_exact` items match exactly as fractions.

Ran in this session's Claude Code cloud container (hostname `vm`, CPU only, no GPU). Python 3.13.18, numpy 2.5.3. No Executor code was imported, copied or run, no model weights were loaded, and I ran no git commands during the task (see note 2).

### Files I created (all under audit/; the Executor needs to commit them)
- `/home/user/OpenMythos/metrix/e1-pilot/audit/pilot_final_recompute.py`: the main recompute and comparison script.
- `/home/user/OpenMythos/metrix/e1-pilot/audit/pilot_final_facts_order.py`: rebuilds and confirms the facts.jsonl order that B10 requires.
- `/home/user/OpenMythos/metrix/e1-pilot/audit/pilot_final_run_logged.sh`: wrapper that writes each command line and exit code into the stdout files.
- `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/pilot_final_recompute.txt`: full stdout and stderr of the main script.
- `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/pilot_final_facts_order.txt`: full stdout and stderr of the order script.
- `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/pilot_final_repo_unchanged.txt`: list of files changed during my run, made without git (note 2).
- `/home/user/OpenMythos/metrix/e1-pilot/audit/pilot_final_recompute.json`: machine-readable comparison table.
- `/home/user/OpenMythos/metrix/e1-pilot/audit/pilot_final_fact_order.json`: the 160 fact_ids in order with exposure, relation and stratum. It contains no entity or answer strings.

### Command and exit codes
```
bash /home/user/OpenMythos/metrix/e1-pilot/audit/pilot_final_run_logged.sh /home/user/OpenMythos /tmp/claude-0/-home-user-OpenMythos/b1fdad2f-e658-5061-a9bf-efceb2d45d71/scratchpad /tmp/claude-0/-home-user-OpenMythos/b1fdad2f-e658-5061-a9bf-efceb2d45d71/scratchpad/venv/bin/python
```
- Wrapper: exit 0.
- `<venv python> -I -B pilot_final_facts_order.py <repo> <tokenizer.json> audit/pilot_final_fact_order.json`: exit 0, `RESULT: PASS`.
- `python3 -I -B pilot_final_recompute.py <repo> audit/pilot_final_fact_order.json audit/pilot_final_recompute.json`: exit 0, `RESULT: PASS`.

### Fact order: where it came from and how I confirmed it
- **Regeneration:** `pilot_final_facts_order.py` rebuilt the 160 facts on CPU from protocol 2.2.
  - It used only the pinned `tokenizer.json` via the `tokenizers` 0.23.3 library, with no transformers and no torch. Its sha256 `aeb13307…dae4` equals `DATA_MANIFEST.json` `model.tokenizer.files_sha256`.
  - It skips the anchor rule, because the anchor texts would need the parquet. This cannot let a wrong list through: the result is accepted only if its hash matches. My own round-9 run with the anchor rule recorded 0 anchor rejections.
- **List hash:** the canonical hash of the regenerated list is `406c8801…6b97`. It matches the protocol 2.2 sentence, `DATA_MANIFEST.json`, `step1_record.json` `content_hashes.facts` and `selection_freeze_record.json`.
- **Byte hash:** I wrote the list as facts.jsonl bytes using the protocol 0 JSONL rule (160 lines, 21,489 bytes). Their sha256 is `e05561ac…c828`, equal to `results/step1_record.json` `environment.data_hashes["facts.jsonl"].byte_sha256` and to `DATA_MANIFEST.json` `files`. Identical bytes mean identical line order.
- **The order itself:** cells run capital, currency, founder, river, each natural then random; within a cell L-01..15 then U-01..05. Sorting the learned facts of a stratum by fact_id gives this same order.
- **Cross-checks:**
  - The answers match `results/details/N_dev.json` for all 160 facts.
  - The rebuilt `candidates.json` hash `e5d15c99…` matches `SPLIT_MANIFEST.json` and step1.
  - All 160 candidate lists match those in `N_dev.json`.

**Assignments taken from the records:**
- Learned/unread and natural/random come from the fact fields, which agree with the fact_id pattern.
- Selected configurations from `selection_freeze_record.json`: F3, L6, A5. S and Y use F3; their `training_runs` configs equal F3's.
- Seeds 101/202/303 and BOOTSTRAP_SEED 20261112 come from `DATA_MANIFEST.json`.
- The purposes I computed (for example `F-N:DEV:101`, `sigma:L-F:DEV:avg`, `halfwidth:A-F:DEV:avg:231`) match the recorded `purpose` fields.

### Comparison counts
**Criterion (fixed before the run):**
- Float values: |recorded − mine| ≤ 1e-12, also checked against my exact fraction value.
- `point_exact`: exact equality as `Fraction`.
- Integers, strings, booleans and dicts: exact equality.

| Group | Items | Inconsistent |
|---|---|---|
| DEV, `results/step7_record.json` | 238 | 0 |
| TEST, `results/test_evaluation_result.json` | 194 | 0 |
| **Main total** | **432** | **0** |

- **DEV:** G0.3, G0.4, G0.5, G0.6, G0.7, G0.9, all of G0.10, and the 20 entries under `comparisons` (F−N, S−N, Y−N, L−F, A−F for each seed and the seed average). G0.10 covers the σ point and 2.5/97.5 percentiles, all 9 n values per comparison, n_max, finite, the half-width at n=231 with 116 per stratum, and planning_n=231.
- **TEST:** T1, T2 (S and Y), T3, and the same 20 entries under `comparisons`.
- **Breakdown:** 173 float items, of which 140 are bit-identical; 46 `point_exact` items; 213 equality items.
- **Differences:** the largest float difference is 1.110e-16 and the largest difference from my exact values is 8.224e-17.
- **Mismatches:** none.
- No G0.10 n value lies on a rounding boundary.

**Extra checks beyond the requested scope (all 0 inconsistent):**
- 246 items: the G0.3–G0.10 and T1–T3 `satisfied` flags recomputed from the protocol thresholds, and per-model accuracies from `training_runs`, step3 and the TEST `summaries`.
- 11,520 values from the DEV `details` files: correct/incorrect flags, Scores and CB.

**Sensitivity:** changing one detail at a time reproduces only part of the 80 recorded CI endpoints:

| Variant | Endpoints reproduced |
|---|---|
| As implemented (B10–B12) | 80 of 80 |
| Fact order reversed | 38 |
| Strata in the other order | 45 |
| Unstratified resampling | 39 |
| Unicode minus in the purpose | 47 |
| No interpolation | 78 |

The no-interpolation variant still gets 78, so B11 is distinguished by only 2 endpoints.

### Notes
1. **Network use:** a pip install of `tokenizers` into a scratch venv, and two downloads of the pinned tokenizer.json. Nothing else; no weights.
2. **git:**
   - The task forbids git operations, so I did not run `git status --short`, which my definition file asks for.
   - Before reading that restriction, at the very start, I ran the read-only `git status --short && git log --oneline -3`. Its output was `?? metrix/e1-pilot/tasks/PILOT_REPORT_ORDER.md`, then `308d5f1 …`, `53800ef …`, `aa50cf4 …`.
   - Instead I compared sha256 hashes of every file outside .git before and after my run. Besides my audit/ files, three files changed that I did not write, presumably your own concurrent edits: `metrix/CLAUDE.md`, `reports/pilot_final/report_fragments.py` and the new `reports/pilot_final/report_fragments.md`.
3. **TEST:** the only TEST input was the committed `test_evaluation_result.json` per-fact scores, which the order allows. No TEST file was opened, searched for or generated. My definition file allows TEST reading only for L6 after the freeze; this use rests on your explicit instruction.
4. **Trust status:** per metrix/CLAUDE.md section 10, data-auditor is still "待验证", so this PASS is for reference only.

结论：PASS
