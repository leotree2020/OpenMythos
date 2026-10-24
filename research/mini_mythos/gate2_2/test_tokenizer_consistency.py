"""
S2-1 tokenizer consistency.

Smoke (489) is allowed for engineering only.
Formal reproduction stays BLOCKED. This test does not rewrite GPU YAMLs.
"""
import json
import sys
from pathlib import Path

MODEL_VOCAB = 32768
SMOKE_VOCAB = 489
OFFICIAL_PATH = "/lustre/orion/csc569/scratch/jgeiping/tokenizers/huginn_tokenizer_65k"


def check_yaml(path):
    text = Path(path).read_text()
    return {
        "file": path,
        "has_model_vocab_32768": "vocab_size: 32768" in text,
        "points_at_official_missing": OFFICIAL_PATH in text,
        "points_at_smoke_489": "alt_tokenizer" in text or "489" in text,
    }


def main():
    root = Path(__file__).resolve().parents[1] / "gate2_2"
    yamls = [root / n for n in ("GPU_A_CONTINUOUS.yaml", "GPU_B1_EXIT.yaml", "GPU_B2_RESUME.yaml", "GPU_C_NATIVE_SKIP.yaml")]
    rows = [check_yaml(str(p)) for p in yamls]
    # relationship
    relation = {
        "model_vocab_size": MODEL_VOCAB,
        "rngds_samples_from": "tokenizer.vocab_size",
        "train_py_raises_model_vocab_if_tokenizer_larger": True,
        "smoke_tokenizer_vocab": SMOKE_VOCAB,
        "smoke_changes_token_range": True,
        "formal_reproduction": "BLOCKED",
        "formal_reason": "official huginn 65k path absent on RunPod; license previously BLOCKED",
    }
    # do not allow smoke path in formal yamls
    formal_clean = all(not r["points_at_smoke_489"] for r in rows)
    out = {
        "status": "SMOKE_OK_FORMAL_BLOCKED",
        "relation": relation,
        "yamls": rows,
        "formal_yamls_not_rewritten_to_489": formal_clean,
    }
    print(json.dumps(out, indent=2))
    return 0 if formal_clean else 1


if __name__ == "__main__":
    sys.exit(main())
