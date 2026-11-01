# Static review of unexecuted draft — REQUEST CHANGES

Reviewer: separate internal ChatGPT agent; not Claude Code, Grok, human or third-party independent validation. Read-only static review of protocol/preparation/runner/tests/auditor, without importing or executing them.

1. Preparation `target_ids_sha256` currently covers192 scored targets; runner/auditor use all256 shifted targets. Unify and introduce a separate scored-target hash.
2. Add actual144323136 parameter and61 unique-parameter-tensor checks;63 state entries alone does not establish these quantities.
3. Record actual runtime getters after upstream import/loading, require Python/Torch versions, and assign explicit package-inventory before/after ownership.
4. Auditor must require no completion error/cleanup errors and bind mandatory per-row numerical/RNG checks to all288 rows.
5. Failed/blocked execution needs separate read-only post-stop file/environment custody. Absent evidence cannot be called G4 PASS.
6. Save prefix digests for causality comparisons. Until then an auditor can verify source and runner's boolean record only, not independently recompute the prefix comparison.

No static mathematical misalignment found in positions64–255, paired h0, nine-control inventory or article-level bootstrap. This does not constitute execution validation. Preparation1 is BLOCKED before any model load because of the incompatible PyArrow/NumPy pair. The draft is not accepted/frozen; no tests or formal model execution have occurred.
