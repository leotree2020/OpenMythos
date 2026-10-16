#!/usr/bin/env python3
"""R0 reconstruction readiness audit from repository source.

Static evidence is deliberately not presented as runtime proof.
No network access or upstream modifications.
"""
import argparse
import re
from pathlib import Path
from common import atomic_json, commit_id, get_repo


def locate(source, pattern):
    match = re.search(pattern, source, flags=re.MULTILINE)
    return source[:match.start()].count("\n") + 1 if match else None


# (id, file, regex, status when found, status when missing, risk, explanation)
RULES = [
    ("RDT_STRUCTURE", "open_mythos/main.py",
     r"^class RecurrentBlock\(nn\.Module\):", "PRESENT", "MISSING", "high",
     "Community recurrent block exists; this is not evidence of the proprietary Mythos topology."),
    ("GQA", "open_mythos/main.py", r"^class GQAttention\(nn\.Module\):",
     "PRESENT", "MISSING", "medium", "GQA implementation exists; full behavior needs runtime tests."),
    ("MLA", "open_mythos/main.py", r"^class MLAttention\(nn\.Module\):",
     "PRESENT", "MISSING", "medium", "MLA implementation exists; full behavior needs runtime tests."),
    ("MOE", "open_mythos/main.py", r"^class MoEFFN\(nn\.Module\):",
     "PRESENT", "MISSING", "medium", "Routed and shared expert code exists."),
    ("WEIGHT_TIE", "open_mythos/main.py", r"self\.head\.weight\s*=\s*self\.embed\.weight",
     "PRESENT", "MISSING", "low", "LM output head is tied to token embeddings."),
    ("CHECKPOINT_MODEL_OPT", "training/3b_fine_web_edu.py",
     r'"model": model_state,', "PRESENT", "MISSING", "high",
     "Model+optimizer save logic is present; resume equivalence is not yet proved."),
    ("REAL_DATA_STREAM", "training/3b_fine_web_edu.py",
     r'load_dataset\(', "PRESENT", "MISSING", "medium",
     "FineWeb-Edu streaming entry point exists; dataset availability/license and revision need validation."),
    ("EVAL_HOLDOUT", "training/3b_fine_web_edu.py",
     r'^\s*model\.eval\(\)', "PRESENT", "GAP", "critical",
     "No obvious heldout evaluation mode in the training entry point; token-level validation PPL is needed."),
    ("TOKENIZER_REVISION", "open_mythos/tokenizer.py",
     r'AutoTokenizer\.from_pretrained\([\s\S]{0,200}?revision\s*=', "PRESENT", "GAP", "high",
     "Tokenizer revision is not pinned in the wrapper; store immutable revision/hash."),
    ("DATA_RESUME_STATE", "training/3b_fine_web_edu.py",
     r'stateful_dataloader|dataset_state|data_cursor', "PRESENT", "GAP", "high",
     "Model resume exists but streaming dataset iterator offset is not saved."),
    ("RNG_RESUME_STATE", "training/3b_fine_web_edu.py",
     r'get_rng_state\(|set_rng_state\(', "PRESENT", "GAP", "medium",
     "RNG state is not saved/restored in checkpoint."),
    ("TRAIN_RANDOM_SEED", "training/3b_fine_web_edu.py",
     r'(?m)^\s*torch\.manual_seed\(', "PRESENT", "GAP", "high",
     "Training run lacks a pinned torch random seed."),
    ("FP16_GRADSCALER", "training/3b_fine_web_edu.py",
     r'\bGradScaler\s*\(', "PRESENT", "GAP", "high",
     "FP16 fallback lacks apparent gradient scaling; test before FP16 runs."),
    ("MOE_ROUTER_BIAS_UPDATE", "training/3b_fine_web_edu.py",
     r'router_bias(?:\.\w+)?\.(?:add_|sub_|copy_|scatter_|index_add_)\(',
     "PRESENT", "GAP", "medium",
     "MoE router bias is read but no training update step is apparent."),
    ("FUSED_OPTIMIZER", "training/3b_fine_web_edu.py",
     r'fused=True', "REVIEW", "NOT_PRESENT", "medium",
     "Unconditional fused AdamW may not work in all CPU/non-CUDA environments."),
    ("UNSAFE_PICKLE_LOAD", "training/3b_fine_web_edu.py",
     r'torch\.load\([^\n]*weights_only=False', "REVIEW", "NOT_PRESENT", "high",
     "Pickle checkpoint loading is unsafe for untrusted checkpoint files."),
    ("ACT_NO_TOKEN_COMPUTE_SKIP", "open_mythos/main.py",
     r'trans_out\s*=\s*self\.block\(combined',
     "REVIEW", "NOT_PRESENT", "high",
     "All token positions enter recurrent TransformerBlock before ACT weights are computed; per-token halting does not demonstrate per-token compute savings."),
    ("ACT_CACHE_NO_EARLY_EXIT", "open_mythos/main.py",
     r'if halted\.all\(\) and kv_cache is None:',
     "REVIEW", "NOT_PRESENT", "medium",
     "With KV cache active the recurrent loop never short-circuits via this condition; inspect inference compute claims."),
    ("CHUNKED_CACHE_MASK", "open_mythos/main.py",
     r'mask\s*=\s*self\._causal_mask\(T,\s*device,\s*x\.dtype\)',
     "NEEDS_RUNTIME_PROBE", "NOT_PRESENT", "high",
     "Causal mask based only on current token count T may fail if S>T with nonempty cache."),
    ("CORPUS_BOUNDARY", "training/3b_fine_web_edu.py",
     r'buf\.extend\(self\.encoding\.encode\(sample\["text"\]\)\)',
     "REVIEW", "NOT_PRESENT", "medium",
     "Document packing concatenates raw tokens; EOS/doc separator is not apparent."),
]


def audit_sources(sources):
    rows = []
    for identifier, path, pattern, found_status, missing_status, severity, note in RULES:
        source = sources[path]
        line = locate(source, pattern)
        rows.append({
            "id": identifier, "path": path, "line": line,
            "status": found_status if line is not None else missing_status,
            "severity": severity, "note": note,
            "method": "static regex, inspect source and run behavior probes before claiming a defect",
        })
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--out", default="research/mini_mythos/results/r0/audit.json")
    a = p.parse_args()
    repo = get_repo(a.repo)
    out = Path(a.out).resolve()
    if not out.is_relative_to(repo / "research/mini_mythos/results"):
        p.error("--out must be under research/mini_mythos/results")
    sources = {path: (repo / path).read_text(encoding="utf-8")
               for path in sorted({rule[1] for rule in RULES})}
    rows = audit_sources(sources)
    atomic_json(out, {
        "stage": "R0 static reconstruction readiness",
        "repository_commit": commit_id(repo),
        "limitations": "Static strings only. PRESENT means code pattern exists, not that behavior is correct. GAP means pattern absent, not proof of nonexistence.",
        "checks": rows,
    })
    for row in rows:
        loc = f"{row['path']}:{row['line']}" if row["line"] else row["path"]
        print(f"{row['id']:24} {row['status']:20} {loc}")
    print("Saved:", out)


if __name__ == "__main__":
    main()
