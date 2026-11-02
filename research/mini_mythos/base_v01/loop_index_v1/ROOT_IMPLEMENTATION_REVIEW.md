# Root implementation review before model execution

Purpose: verify that the isolated mechanism-3 experiment answers the registered comparison without modifying the pretrained model or mixing mechanisms.

Environment: local Windows developer fixtures use Python 3.12.14 / Torch 2.9.0+cpu. The designated formal runtime remains Codespace bookish-pancake-vwqx7rr9x5w3wxjr, Python 3.12.3 / Torch 2.11.0+cpu. Local tests do not establish formal-runtime or scientific acceptance.

Input: checkpoint d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85, pinned upstream 69284c13746e849104f738d6d1a347b1f457df76, unchanged 16+16 article preparation, and this package's protocol, operator, model wrapper, worker, auditor and tests. The root read the full wrapper and relevant training, scoring, reload, custody, publication and independent-audit code; an independent internal reviewer checked the design and implementation. No external Claude/Grok review is claimed.

Expected: equal 96 trainable gains; only fixed code versus constant features differs between trained arms; native fixed32 and paired h0; all original state bytes unchanged; complete gradient and independent-logit evidence; no tuning or retry after formal results.

Actual static findings and resolutions before freezing:

- The original proposed learned 32x768 table had a capacity confound. It was discarded before implementation/results. The final protocol uses 96 gains in both trained arms.
- The OpenMythos source adds sin/cos features; it is not a rotary operation. The zero gain and native Parcae injection placement are explicitly adaptations, not a faithful model port.
- Gradient activity originally counted padded channels. The final check uses each depth's actual gain contribution, delta.grad[:96] multiplied by that depth's fixed code, with an explicit gradient-decomposition fixture. Padded channels cannot pass the activity check.
- Every step records finite positive gain gradient and update norms, coordinate update flags, and 32 depth-contribution norms. Per-coordinate activity is descriptive; all 32 depth paths must participate over the fixed schedule.
- The protocol zero-control description was corrected to first training article / h0 seed 6101; the separate reload check uses first validation article / h0 seed 5101. No result informed these choices.
- Scientific classifications distinguish practical improvement, no qualified improvement, deterioration and mixed seeds. Screen FAIL is not engineering FAIL.
- Disk admission is calculated from 1,342,177,280 raw-logit bytes plus 64 MiB metadata allowance and 256 MiB reserve. Each raw write also preserves the reserve; prior records are never removed or copied wholesale.
- Developer attempt reports are retained, including a fixture-only retained-gradient double-accumulation failure corrected before freezing. A read-only target-status command had a quoting syntax error and no side effect; its corrected read succeeded. Neither was a formal model attempt.

Read-only target restoration observed the requested LoRA head and clean worktree, clean pinned upstream, 1,895,378,944 free disk bytes and 5,060,320 KiB MemAvailable before new-worktree creation. The formal operator must independently recheck current resources and identities. The separate worktree was created from the exact checkpoint; the main worktree's existing changes were untouched.

Status: static implementation APPROVE, conditional on the exact final developer-test inventory and all target-runtime guards. Formal execution and scientific results are NOT TESTED at this freeze. An exit code alone cannot satisfy acceptance.

Limits: this is a small reused development benchmark, not fresh generalization, production quality, statistical confirmation, or proprietary Mythos reproduction. Equal parameter counts do not remove feature-conditioning differences. No LoRA or early-stop mechanism is stacked. Training-resume trajectory equivalence remains NOT TESTED. Upstream, A5, B1 history, early-stop thresholds and PR24 remain protected.
