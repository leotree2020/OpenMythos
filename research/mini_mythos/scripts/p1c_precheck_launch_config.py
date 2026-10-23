"""
Generate a complete local launch YAML from the committed template and
parse it with the official Parcae CLI(CLISettings).

Requires LOCAL_WORLD_SIZE=1 on CPU. Does not train or use GPU.
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

import yaml


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--template", required=True, help="Committed YAML template")
    p.add_argument("--tokenizer-dir", required=True, help="Absolute path to alt tokenizer dir")
    p.add_argument("--out", required=True, help="Absolute path for generated YAML")
    p.add_argument("--resume-out", required=True, help="Absolute path for resume YAML")
    args = p.parse_args()

    tok = Path(args.tokenizer_dir).resolve()
    if not tok.is_dir():
        print(f"FAIL: tokenizer dir missing: {tok}")
        sys.exit(1)
    if not (tok / "tokenizer.json").is_file():
        print(f"FAIL: tokenizer.json missing in {tok}")
        sys.exit(1)

    template = Path(args.template).resolve()
    raw = yaml.safe_load(template.read_text())
    raw["tokenizer_path"] = str(tok)
    # Strip comments-only keys that may not be present
    raw.pop("# tokenizer_path", None)

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(raw, sort_keys=False))
    h = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"generated: {out}")
    print(f"sha256: {h}")

    # Official CLI parse of the same generated file
    os.environ.setdefault("LOCAL_WORLD_SIZE", "1")
    from jsonargparse import CLI
    from recpre.settings import CLISettings

    sys.argv = ["precheck", "--config", str(out)]
    cfg = CLI(CLISettings)
    assert isinstance(cfg, CLISettings)

    # Tokenizer assertions
    from parcae_lm.tokenizer import Tokenizer
    t = Tokenizer(cfg.tokenizer_path)
    assert t.bos_id == 0, t.bos_id
    assert t.eos_id == 1, t.eos_id
    assert t.pad_id == 2, t.pad_id
    assert len(t) == 489, len(t)

    # Config assertions
    assert cfg.model_overwrite.get("vocab_size") == 32768
    assert cfg.data_config["train_data"][0].type == "rngds"
    assert cfg.data_config["val_data"][0].type == "rngds"
    assert cfg.optimizer == "MuonAdamW"
    assert cfg.devices == 1
    assert cfg.gradient_accumulation_steps == 4
    assert cfg.max_steps == 6
    assert cfg.save_step_interval == 2
    assert Path(cfg.tokenizer_path).is_dir()

    print("parsed fields:")
    print(f"  tokenizer_path={cfg.tokenizer_path}")
    print(f"  bos/eos/pad={t.bos_id}/{t.eos_id}/{t.pad_id} vocab={len(t)}")
    print(f"  model_vocab={cfg.model_overwrite.get('vocab_size')}")
    print(f"  train/val={cfg.data_config['train_data'][0].type}/{cfg.data_config['val_data'][0].type}")
    print(f"  optimizer={cfg.optimizer}")
    print(f"  devices={cfg.devices} accum={cfg.gradient_accumulation_steps}")
    print(f"  max_steps={cfg.max_steps} save_interval={cfg.save_step_interval}")
    print("PRECHECK: PASS")

    # Resume config (not executed)
    resume = dict(raw)
    resume["resume"] = True
    resume["resume_checkpoint_path"] = ""  # fill with actual ckpt before use
    resume_out = Path(args.resume_out).resolve()
    resume_out.write_text(yaml.safe_dump(resume, sort_keys=False))
    print(f"resume config written (NOT EXECUTED): {resume_out}")
    print("Resume verification must check data iterator position, optimizer state, and RNG.")
    print("Load-without-error is not sufficient.")
    print("ALTERNATIVE TEST TOKENIZER — official tokenizer license BLOCKED.")
    print(f"Launch command (absolute path):")
    print(f"  bash runs/run_training.sh {out} p1c-min-train group 1")
    print("PREDICTED / NOT RUNTIME VERIFIED: microbatch=20, optimizer_step=5, step()=4")
    print("saves at microbatch 4,8,12,16,20")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"PRECHECK: FAIL {type(e).__name__}: {e}")
        sys.exit(1)
