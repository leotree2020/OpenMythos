# Worker/operator boundary review

Verdict: **APPROVE for source freeze and the authorized single target attempt**. This is a static review, not a completed original-model acceptance.

- Purpose: check deployment isolation, target runtime guards, fail-stop behavior, evidence export and checkpoint publication.
- Environment: local Windows, read-only inspection of the operator; no target access, original weights, model import or numerical execution in this review.
- Input: `execute_once.py` SHA-256 `d031a2f36b60ddc5156f87f28dab9943f7e002e332c6ba048583b3cd806ed975`; worker interface and the stage protocol. The earlier inspected operator was `305a98125069ca26a0b148b48356f4c254740ea4de5e0acb9ed76e062c7946eb`.
- Expected: only the designated clean isolated checkout and existing CPU environment may launch; failures stop further model work; publication requires stopped children and a clean source tree; private tensors and token IDs stay outside Git.
- Actual: the final operator enforces the exact Codespace, interpreter, branch, worktree, commit lineage, remote HEAD, package manifest and immutable input pins. It verifies all named helper tests from a structured report, then launches one worker through the unchanged bounded launcher. Worker failure prevents the independent success audit and any retry. Post-stop custody is read-only. Public export uses explicit metadata/log allowlists, while raw worker artifacts remain external and hash-bound. Git staging is limited to the new evidence directory and three named checkpoint/manifest files, after an unchanged-HEAD and clean-tree check; final push verification checks remote equality and a clean tree.
- Status: **PASS — static boundary review only**. Target helper results, the 55-call matrix and independent result audit remain NOT TESTED at the time of this review.

One blocking edge case was identified and corrected: an exception during early custody reads could leave default empty process lists that had never been checked. Publication now independently rescans active workers and directly inspects every command's reaping/cleanup record, writes `publication_quiescence.json`, and refuses export/commit if either check fails or cannot be read. It no longer relies on unverified empty defaults.

Two checkpoint wording corrections are also present: preservation claims now refer to the actual custody outcomes instead of unconditionally declaring every protected source unchanged; the external manifest explicitly covers files present at sealing, with the later `publication.json` receipt outside that manifest. A blocked publication leaves external evidence and does not authorize another numerical attempt.

Review limits: this reviewer authored `run_smoke.py` and its helper tests, so this is not independent certification of that worker. The operator was authored by another agent and was independently inspected here. The separate science review and result audit retain their own scope. The earlier local 9/9 standard-library helper result validates synthetic bookkeeping fixtures only; it is not target, model, quality, speedup or hardware-efficiency evidence. No external Claude/Grok review is claimed.
