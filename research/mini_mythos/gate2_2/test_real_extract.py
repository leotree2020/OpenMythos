"""CPU integrity test with a real tiny Parcae. No GPU. AdamW is not MuonAdamW."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_evidence import from_objects
from compare_equivalence import main as compare_main


def cfg():
    return ParcaeConfig(
        n_embd=32, intermediate_size=64, num_attention_heads=2, num_key_value_heads=2,
        vocab_size=128, padded_vocab_size=128, block_size=8,
        n_layers_in_prelude=1, n_layers_in_recurrent_block=1, n_layers_in_coda=1,
        mean_recurrence=1, mean_backprop_depth=1, recurrent_embedding_dimension=32,
        recurrent_intermediation_embedding_dimension=64, prelude_norm=True,
        injection_type="diagonal", state_init="normal", tie_embeddings=True,
        use_fused_head="pytorch", sampling_scheme="fixed",
    )


def build():
    torch.manual_seed(42)
    m = Parcae(cfg())
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 1.0)
    return m, opt, sched


def evidence_pair(tag, model, opt, sched, batch, ckpt, counts):
    ev = from_objects(model, opt, sched, batch, ckpt, source="CPU_PARCAE", counts=counts)
    ev["batch_hashes"] = counts["hashes"]
    ev["rng_at_save"] = {"cpu": ev["rng"]["cpu"]}
    ev["rng_at_restore"] = {"cpu": ev["rng"]["cpu"]}
    ev["resume_from_sha256"] = ev["checkpoint_sha256"]
    ev["tag"] = tag
    return ev


def main():
    results = {"muonadamw": "NOT TESTED", "cuda": "NOT_APPLICABLE", "tests": []}
    m, opt, sched = build()
    x = torch.randint(0, 128, (1, 4))
    out = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    out["loss"].backward()
    opt.step()
    sched.step()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ckpt = td / "ckpt.pt"
        torch.save({"model": m.state_dict(), "opt": opt.state_dict()}, ckpt)
        counts = {
            "hashes": ["h0", "h1", "h2", "h3"],
            "losses": [1.0, 1.1, 1.2, 1.3],
            "microbatch_step": 4, "optimizer_step": 1, "update_count": 1,
        }
        A = evidence_pair("A", m, opt, sched, x, ckpt, counts)
        B1 = json.loads(json.dumps(A)); B1["batch_hashes"] = ["h0", "h1"]; B1["losses"] = [1.0, 1.1]
        B2 = json.loads(json.dumps(A)); B2["batch_hashes"] = ["h2", "h3"]; B2["losses"] = [1.2, 1.3]
        C = json.loads(json.dumps(A)); C["batch_hashes"] = ["h3"]; C["losses"] = [1.3]
        for name, obj in (("A", A), ("B1", B1), ("B2", B2), ("C", C)):
            (td / f"{name}.json").write_text(json.dumps(obj))
        # identical should PASS
        sys.argv = ["compare", str(td/"A.json"), str(td/"B1.json"), str(td/"B2.json"), str(td/"C.json")]
        code = compare_main()
        results["tests"].append({"name": "real_cpu_identical", "code": code, "ok": code == 0})
        # mutate a weight
        B2b = json.loads(json.dumps(B2))
        key = next(iter(B2b["model_state"]))
        B2b["model_state"][key]["values"][0] = 99.0
        (td / "B2b.json").write_text(json.dumps(B2b))
        sys.argv = ["compare", str(td/"A.json"), str(td/"B1.json"), str(td/"B2b.json"), str(td/"C.json")]
        code = compare_main()
        results["tests"].append({"name": "weight_changed", "code": code, "ok": code != 0})
        # bad resume sha
        B2c = json.loads(json.dumps(B2)); B2c["resume_from_sha256"] = None
        (td / "B2c.json").write_text(json.dumps(B2c))
        sys.argv = ["compare", str(td/"A.json"), str(td/"B1.json"), str(td/"B2c.json"), str(td/"C.json")]
        code = compare_main()
        results["tests"].append({"name": "resume_sha_missing", "code": code, "ok": code != 0})
        # SYNTHETIC rejected
        syn = json.loads(json.dumps(A)); syn["source"] = "SYNTHETIC"
        (td / "syn.json").write_text(json.dumps(syn))
        sys.argv = ["compare", str(td/"syn.json"), str(td/"B1.json"), str(td/"B2.json"), str(td/"C.json")]
        code = compare_main()
        results["tests"].append({"name": "synthetic_rejected", "code": code, "ok": code != 0})
    # MuonAdamW constructability
    try:
        from recpre.optim.muon_adamw import MuonAdamW
        results["muonadamw_import"] = "PASS"
        results["muonadamw_step_cpu"] = "NOT TESTED"
    except Exception as e:
        results["muonadamw_import"] = f"FAIL {type(e).__name__}"
    failed = [t for t in results["tests"] if not t["ok"]]
    results["failed"] = len(failed)
    print(json.dumps(results, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
