"""Launch-time check of the salt commitment (sha256 of the salt, never the salt): the value passed in
REVIEWER_SALT_COMMITMENT_SHA256 must be character for character the reviewer's approved commitment below.
Exit 0 only when it is."""
import os, re, sys
APPROVED = "52d1b31e99a7a277ab4bc8cec1ee736994c79606ffce6aa0c5a73176d8d181bc"
v = os.environ.get("REVIEWER_SALT_COMMITMENT_SHA256")
bad = []
if v is None:
    bad.append("REVIEWER_SALT_COMMITMENT_SHA256 not set")
elif v != APPROVED:
    fmt = "64 lowercase hex" if re.fullmatch(r"[0-9a-f]{64}", v) else f"not 64 lowercase hex ({len(v)} characters)"
    bad.append(f"not equal to the approved commitment {APPROVED[:12]}... (value given: {fmt})")
print(f"PASS commitment: equal to the approved {APPROVED}" if not bad else "FAIL commitment: " + "; ".join(bad))
sys.exit(0 if not bad else 1)
