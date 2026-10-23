#!/usr/bin/env python3
"""
Real AST-based contract check against pinned Parcae forward().
Fetches or reads the source at 69284c1 and verifies signature + return dict.
"""
import ast
import json
import sys
import urllib.request
from pathlib import Path

PINNED_URL = "https://raw.githubusercontent.com/sandyresearch/parcae/69284c13746e849104f738d6d1a347b1f457df76/parcae_lm/models/parcae/parcae.py"
LOCAL_FALLBACK = Path("/tmp/parcae_pinned.py")

def load_source():
    if LOCAL_FALLBACK.exists():
        return LOCAL_FALLBACK.read_text()
    try:
        with urllib.request.urlopen(PINNED_URL, timeout=15) as r:
            text = r.read().decode()
            LOCAL_FALLBACK.write_text(text)
            return text
    except Exception as e:
        print(json.dumps({"status": "BLOCKED", "error": str(e)}))
        return None

def main():
    src = load_source()
    if src is None:
        return 1
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "forward":
            found = True
            args = [a.arg for a in node.args.args]
            has_labels = "labels" in args
            has_return_logits = "return_logits" in args
            returns_dict = False
            keys = []
            for n in ast.walk(node):
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict):
                    returns_dict = True
                    keys = [k.value if isinstance(k, ast.Constant) else None for k in n.value.keys]
                    break
            contract = {
                "status": "CONTRACT_OK" if (has_labels and has_return_logits and returns_dict and "loss" in keys) else "CONTRACT_FAIL",
                "args_contain_labels": has_labels,
                "args_contain_return_logits": has_return_logits,
                "returns_dict": returns_dict,
                "return_keys": keys,
                "source": "AST parse of pinned parcae.py forward()",
            }
            print(json.dumps(contract, indent=2))
            return 0 if contract["status"] == "CONTRACT_OK" else 1
    print(json.dumps({"status": "CONTRACT_FAIL", "error": "forward not found"}))
    return 1

if __name__ == "__main__":
    sys.exit(main())
