"""P1-D4 evidence. NEW REPRODUCTION. Does not modify Parcae."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import torch
import torch.nn.functional as F
from parcae_lm.tokenizer import Tokenizer
from recpre.data_loading_utils import BestFitPackingCollator
from recpre.huggingface_dataset import ParquetStreamPure

SRC = Path("/tmp/parcae-tok/tokenizer.json")
HASH = "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    out = {"kind": "NEW REPRODUCTION"}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        shutil.copy(SRC, td / "tokenizer.json")
        before = sha(td / "tokenizer.json")
        (td / "tokenizer_config.json").write_text(Path("/tmp/tok-compat/tokenizer_config.json").read_text())
        (td / "special_tokens_map.json").write_text(Path("/tmp/tok-compat/special_tokens_map.json").read_text())
        tok = Tokenizer.from_directory(td)
        after = sha(td / "tokenizer.json")
        bare = Tokenizer.from_directory("/tmp/parcae-tok")
        sample = "Hello 你好 world."
        out["load"] = {
            "bos": tok.bos_id, "eos": tok.eos_id, "pad": tok.pad_id,
            "vocab": tok.vocab_size,
            "hash_before": before, "hash_after": after, "hash_ok": before == after == HASH,
            "encode_same": tok.encode(sample).tolist() == bare.processor.encode(sample),
            "candidate_ids": tok.encode(sample).tolist(),
        }
        data = td / "data"
        data.mkdir()
        rows = ["Hello world.", "你好世界。", "Mix 你好 123.", "short"]
        pq.write_table(pa.table({"text": rows}), data / "tiny.parquet")
        ds = ParquetStreamPure(
            dataset_folder_path=str(data), seed=42, shuffle=False,
            shuffle_filenames=False, broadcast_glob=False,
            plan_for_later_rank_expansion_to=1,
            data_signature={"keys": ["text"]}, tokenizer=tok,
        )
        raw = [next(iter(ds)).tolist() for _ in range(4)]
        out["parquet_tokens"] = raw
        out["saw_bos"] = any(0 in r for r in raw)
        out["saw_eos"] = any(1 in r for r in raw)
        out["saw_pad"] = any(2 in r for r in raw)
        collator = BestFitPackingCollator(tok, block_size=16, add_bos=True, add_eos=True, buffer_size=8)
        batch = [torch.tensor(r) for r in raw]
        inputs, labels, _ = collator(batch)
        out["packed_inputs"] = inputs.tolist()
        out["packed_labels"] = labels.tolist()
        out["label_eq_2"] = (labels == 2).tolist()
        out["label_eq_0"] = (labels == 0).tolist()
        logits = torch.zeros(1, 4, 8)
        logits[0, :, 3] = 10
        lab2 = torch.tensor([[3, 2, 3, 2]])
        lab0 = torch.tensor([[3, 0, 3, 0]])
        out["loss"] = {
            "logits": logits.tolist(),
            "dtype": str(logits.dtype),
            "shape": list(logits.shape),
            "reduction": "mean",
            "labels_ignore2": lab2.tolist(),
            "loss_ignore2": float(F.cross_entropy(logits.view(-1, 8), lab2.view(-1), ignore_index=2)),
            "labels_ignore0": lab0.tolist(),
            "loss_ignore0": float(F.cross_entropy(logits.view(-1, 8), lab0.view(-1), ignore_index=0)),
        }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
