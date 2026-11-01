# Decode control execution

Only run in the named Codespace after protocol/source review and frozen commit A.
Do not invoke any older runner. From a clean isolated branch descended from
af796912, record A in a documentation-only commit B, then invoke exactly once:

```sh
/workspaces/mythos-base-v01-cpu312/bin/python -B research/mini_mythos/base_v01/decode_control_v1/run_decode_control.py --execute --implementation-commit <A-40hex> --run-id decode-v1-YYYYMMDDTHHMMSSZ
```

Use an external operator wrapper to preserve stdout/stderr and exit code even
if the browser disconnects. The coordinator launches one sequential worker.
Engineering BLOCKED/FAIL stops model work. Never retry a formal run; retain all
partial files. Scientific quality is assessed separately after the complete
frozen matrix. Hash/audit the evidence, complete two blinded AI reviews, commit
public evidence and checkpoint, push normally, and stop. No B1/B2/D2-A/PR24 work.
