# M1 independent archive audit — 2026-10-29

Status: PASS for archive integrity and reported-result consistency.

The user provided access to Codespaces `bookish-pancake-vwqx7rr9x5w3wxjr`.
Read `/workspaces/OpenMythos/mythos_evidence/M1_CPU_3seeds_20261029.tar.gz`
through its authenticated browser terminal. The original archive was transferred
losslessly via base64 terminal output, decoded locally, and independently hashed.
The 3,895 bytes match the previously user-reported SHA256:
`f5542ebd2e92dd165b5e3155f7496c3698924b834f14b11e00a391366a54ed4c`.
The original archive and six JSON member byte streams are preserved here.

Audit command (repository root):

```sh
python research/mini_mythos/m1/audit_archive.py research/mini_mythos/m1/evidence/archive_audit_20261029/M1_CPU_3seeds_20261029.tar.gz --out audit.json
```

Purpose: independently check the supplied M1 artifact against the frozen M1
configuration and .05 validation-NLL decrease criterion, without training.
Environment: Python 3.12.14, torch 2.9.0+cpu, Windows; actual training JSONs report
Python 3.12.3/torch 2.11.0+cu130, CPU=true, threads=1. CUDA-enabled wheel naming
does not imply GPU execution.

Expected: exactly six regular JSONs, three seeds x two arms; SHA matches; configs,
batch/split identities, PPL/NLL arithmetic and learning thresholds consistent.
Actual: all checks PASS. Independently regenerated all train batch IDs, validation
IDs and test IDs and matched SHA256 for every report; ID split sets are disjoint.
The JSON reports all meet the learning threshold and have different reported
initial/final weight hashes. See audit.json for individual values and member hashes.

Limits: actual weight tensors and per-step gradients are absent. Their hashes and
all 180 gradient checks cannot be independently verified from this archive.
The audit is not a training rerun, full provenance attestation or architecture
superiority test. The JSONs lack experiment Git commit and full dependency freeze.
Grok review remains NOT TESTED.

Codespaces inspected state: `/tmp/mythos-m1-pr12` clean, detached at c639112;
main `/workspaces/OpenMythos` on mini-mythos-research at d05273c with existing
untracked overlay ZIP and mythos_evidence/. The old default upstream directory
`/tmp/mythos-m1-official-parcae` remains at 4b86c2a with staged deletions from the
old no-checkout attempt and was left untouched. The usable clean upstream is
`/tmp/mythos-m1-parcae-clean-20261029` at the required 69284c1 pin.
