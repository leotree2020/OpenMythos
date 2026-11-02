# MYTHOS-ROUTING-QUALITY-COST-CPU-V1 checkpoint

Engineering Status: **PASS**.

Freeze commit: `9b38408d040f467276c68663642a152dbf25a855`. Branch: `mythos-routing-quality-cost-cpu-v1`.

Purpose/Input/Expected/Actual and scientific screens: evidence/summary.json and evidence/audit.json. Environment: Python3.12.3/Torch2.11.0+cpu, CPU FP32,2 intra-op/1 inter-op; unchanged existing data environment; no training/GPU.

Design: same16 prefixes128tokens, seeds3101/3202; one actual next-token target per source; 64 observed quality calls,2warmups,128 timed calls,194 total. Timers cover unchanged public API including guards, readouts and policy, but exclude external observation hooks and evidence writing. No missing stage is PASS.

External raw evidence: `/workspaces/mythos-evidence/base_v01/routing_quality_cost/attempt-v1`. EXTERNAL_EVIDENCE_MANIFEST.json binds all files at sealing; publication.json is a later receipt outside that seal. Public metadata only is exported.

Scientific screens: {'quality': {'Status': 'PASS', 'Expected': 'Both evaluation-seed mean delta NLL<=0.01 and correct count not lower; every case delta NLL<=0.1', 'meaning': 'Exploratory engineering margin only; not statistical noninferiority or language-quality acceptance'}, 'cpu_time': {'Status': 'FAIL', 'Expected': 'Adaptive/fixed32 aggregate elapsed<=0.95 in both rounds'}, 'joint': {'Status': 'FAIL', 'Expected': 'Both quality and CPU time screens PASS'}}. Negative quality/speed screens do not mean code failure. No population noninferiority, fresh-test generalization or general generation-quality claim.

Custody: see evidence/custody.json. OldV1/V2/V3 records, upstream, frozenTV0.01 and three environments preserved. No A5 relaxation, B1 rerun, B2/D2-A or PR24 operation. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Unresolved: external generalization, broader quality and deployment performance

Next unique instruction: review paired quality and both timing rounds; preserve negative results without tuning; design the next separately frozen comparison only after review. On engineering FAIL/BLOCKED resolve only recorded cause. Stop, no retry or automatic next phase.
