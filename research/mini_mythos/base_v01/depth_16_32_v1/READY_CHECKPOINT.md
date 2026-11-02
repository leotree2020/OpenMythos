# MYTHOS-DEPTH-16-32-CPU-V1 — ready for target preflight

Purpose: provide the user an executable, frozen8/16/32 CPU comparison after automated target access was blocked.

Base: leotree2020/OpenMythos@a1e61eb0a24cfc347aea40194ad4c00ff6d5bd18. Branch: mythos-depth-16-32-cpu-v1. Only research/mini_mythos/base_v01/depth_16_32_v1/ is added. The freeze SHA is the final commit containing SOURCE_MANIFEST.json and this document, supplied verbatim as execute_once.py --expected-head. No target Git state is inferred from local review.

Environment: implementation and static review locally;8 standard-library audit/summary fixtures pass on Python3.10.11. Actual execution requires the designated Codespace's original Python3.12.3/Torch2.11.0+cpu environment. Target fixture gates must pass before the sole model launch.

Input: corrected32-source input SHA2563abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e, exact partition/ledger/data audit, official frozen model and upstream. Protocol explicitly registers32 sources,3 paired h0 replicas,depths8/16/32,9 controls+288 rows,3600-second ceiling and immutable old evidence.

Expected: check identity/resources/source spans, pass fixtures, run once, independently audit/derive paired source-level NLL results and record actual CPU costs. Positive quality evidence is separate from correct execution.

Actual: new code/protocol/auditor/operator created; internal static APPROVE; local synthetic checks PASS. No target access, Torch/model import, real-data model computation, generation or training performed in this preparation session.

Status: IMPLEMENTATION/STATIC REVIEW PASS; TARGET PREFLIGHT/HELPER TESTS/MODEL RESULTS NOT TESTED. No new16/32 numerical result exists. Target attempt directory is /workspaces/mythos-evidence/base_v01/depth_16_32/attempt-v1 and must not already exist. The script will not remove it or retry.

Unresolved: actual target execution. Prior browser-control BLOCKED records remain in the local preparation workspace. Prior source-unit V1FAIL is unchanged. Upstream, A5, B1, B2/D2-A and PR24 remain protected. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Next unique instruction: the user runs the supplied frozen command once in the specified Codespace. On success or failure, preserve all evidence, write CHECKPOINT.json and (when safe) commit/push compact evidence plus CHECKPOINT.md, then stop. Do not interpret the background-start message as proof that the model launched or passed. Inspect summary.json and the published checkpoint.
