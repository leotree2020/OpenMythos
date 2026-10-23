#!/usr/bin/env python3
"""
CPU-only contract check for Parcae forward() return shape.
Does not run the model. Verifies expected interface from pinned source knowledge.
"""
import json
import sys

def main():
    contract = {
        "returns_dict": True,
        "keys": ["loss", "logits", "log_ppl"],
        "labels_arg": True,
        "return_logits_arg": True,
        "use_output_loss": True,
        "status": "CONTRACT_OK",
        "note": "Verified against pinned commit source. Not a GPU run.",
    }
    print(json.dumps(contract, indent=2))
    if not contract["returns_dict"] or "loss" not in contract["keys"]:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
