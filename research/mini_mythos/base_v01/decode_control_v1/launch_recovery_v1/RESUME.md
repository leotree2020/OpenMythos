# Decoding control launch recovery

The owner authorized continuation from checkpoint df02037580bf6861a8f61ea145a6ab7770e6c055,
including the required launcher repair and tests, followed by credible CPU data.
The prior failed launcher directory and all its evidence stay unchanged.

The numerical implementation remains A=e2605841d7eb21c7d8ecbc07aa55ebe6c76f05b7.
Its PROTOCOL.md, QUALITY_RUBRIC.md, four Python sources and referenced immutable
utilities/inputs retain their frozen bytes. The 84-condition, 5376-forward matrix,
seeds, original weights, sampling policies and quality gates are unchanged.
The previous operator failed before any formal runner began; this continuation
records a new attempt ID and does not overwrite or count that failure as a run.

Only orchestration changes: a new independent operator directory contains
mythos_launch.py; launch it using the existing CPU312 Python with -I -B. It checks
that operator resolves to the standard library and no numerical modules were
imported by the helper. The actual coordinator is invoked with its original -B
arguments, not -I, so its frozen sibling imports work as designed. A claim file
prevents duplicate child execution. Separate stdout/stderr and completion status
retain nonzero child exits. Timeout/interruption attempts TERM then KILL of the
child process group and records cleanup separately from the first exception.
Process-group existence may include zombies; do not equate a reaped leader with
all descendants stopped. Read-only process checks accompany abnormal shutdown.

Before launch freeze, run genuine stdlib-only child-process fixtures on the
designated Codespace: exact success output capture, genuine standard-library
origin/source identity, duplicate refusal without evidence overwrite, exit7
capture, and timeout of a parent with a TERM-resistant harmless child. These are
development checks, not model evidence. An expected negative fixture is accepted
only when its exact failure/capture/cleanup criteria pass. No torch, model,
tokenizer or weights are imported/read by these fixtures. Freeze the exact tested
helper and smoke evidence before recording the new formal attempt.

The formal helper has a6000-second limit, above the frozen worker5400-second limit.
All original CPU constraints and experiment stopping rules apply. One formal
attempt only. Engineering FAIL/BLOCKED stops computation and preserves evidence;
quality failures do not interrupt the predeclared complete matrix. No parameter
selection based on partial outputs, no changed source or thresholds mid-run.
Audit all evidence and perform the frozen two-reviewer metadata-blind quality
assessment after complete execution; previously seen prompts/G outputs are not
an independent fresh test. Preserve disagreements using the frozen rule.

No upstream changes, A5 relaxation, B1 runner/rerun, GPU, training, B2, D2-A or
PR24 action. Commit public evidence and checkpoint, verify remote and stop after
this experimental stage. Original B1 A5 remains BLOCKED; Formal Oracle remains
BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False.
