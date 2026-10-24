# Next RunPod Handbook (NOT EXECUTED)

1. Mount existing Network Volume at /workspace. Confirm it is the retained 30 GB volume.
2. `git -C OpenMythos rev-parse HEAD` must be the readiness branch tip. `git -C parcae rev-parse HEAD` must be 69284c1.
3. Tokenizer: formal 65k is BLOCKED. Smoke may use the 489 alt tokenizer. Record which.
4. A/B1/B2/C: not launched in this round. Commands exist as YAML; native CLI parse was PASS in the prior precheck.
5. B2/C must be given the real B1 checkpoint absolute path after B1 exits. Do not use null.
6. Evidence: run collect_native_evidence against the real process outputs. BLOCKED until a real run exists.
7. Provenance: `python verify_provenance.py evidence.json blob_dir`.
8. Comparator: frozen. Formal pass needs native_entry_artifact derived from real files.
9. Save logs, configs, checkpoint hashes under the volume.
10. Stop the pod by 50 minutes or ¥700, whichever comes first. Delete unneeded storage.

GPU evidence collection: NOT EXECUTED.
