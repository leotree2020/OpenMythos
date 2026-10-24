"""CPU-only adapter check. Not a GPU_RUNTIME result."""
import json
import sys
import tempfile
from pathlib import Path

import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig
from recpre.optim.muon_adamw import MuonAdamW, get_muon_param_groups

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_evidence_adapter import StepLog, capture_after_load, capture_before_save, write_evidence


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


def main():
    torch.manual_seed(1)
    m = Parcae(cfg())
    opt = MuonAdamW(get_muon_param_groups(m.named_parameters()))
    log = StepLog()
    x = torch.randint(0, 128, (1, 4))
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    log.observe(x, y["loss"])
    skipped = not log.maybe_step(opt)
    y2 = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y2["loss"].backward()
    log.observe(x, y2["loss"])
    stepped = log.maybe_step(opt)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ckpt = td / "ckpt.pt"
        torch.save({"model": m.state_dict(), "opt": opt.state_dict()}, ckpt)
        before = capture_before_save()
        cfgp = td / "cfg.yaml"
        cfgp.write_text("model: tiny\n")
        meta = {
            "command": "cpu adapter test",
            "config_path": str(cfgp),
            "openmythos_commit": "2d30343",
            "parcae_commit": "69284c1",
            "source": "CPU_PARCAE",
        }
        ev = write_evidence(m, opt, None, x, ckpt, log, td / "blobs", meta, {"before_save": before, "after_load": capture_after_load()})
        refused = False
        try:
            bad = dict(meta)
            bad["source"] = "GPU_RUNTIME"
            write_evidence(m, opt, None, x, ckpt, log, td / "blobs2", bad, {})
        except ValueError:
            refused = True
    ok = (
        skipped and stepped
        and log.update_count == 1
        and ev["batch_sha256"]
        and ev["losses"]
        and ev["native_entry_artifact"]
        and refused
        and ev["source"] == "CPU_PARCAE"
    )
    print(json.dumps({
        "status": "CPU ADAPTER PASS" if ok else "FAIL",
        "skipped_first": skipped,
        "update_count": log.update_count,
        "optimizer_step": log.optimizer_step,
        "source": ev["source"],
        "gpu_refused": refused,
        "native_entry": bool(ev["native_entry_artifact"]),
        "gpu_runtime": "NOT TESTED",
    }, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
