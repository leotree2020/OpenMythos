# CPU file-resume evidence

- result.json: structured checks
- environment.json: runtime environment
- raw.txt: full stdout/stderr (raw.log is gitignored)

Test execution HEAD: 94e164db51abb022d3cbeae6f68d14cee6caa796
Evidence archive commit: 66ae4c7ae04be8898f10d2e36ba0bb73f672114f

Exit 0 is the original run record, not an independent third-party rerun.

ABI risk: Python 3.11.2 headers with a Python 3.10 pyconfig.h copy.
NumPy version and live module import paths were not recorded in that run. Not filled in by inference.

Scope: CPU FILE-RESUME BIT-EXACT PASS for a tiny Parcae file restore only.
Not Fabric. Not GPU. Gate 2.2-C NOT PASS.
