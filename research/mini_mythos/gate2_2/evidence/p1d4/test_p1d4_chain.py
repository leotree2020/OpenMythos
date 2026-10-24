"""P1-D4-E2. Candidate config is NON-OFFICIAL. Does not modify Parcae."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from parcae_lm.tokenizer import Tokenizer
from recpre.data_loading_utils import BestFitPackingCollator, PackedIterableDataset, unwrap_singleton_collate
from recpre.huggingface_dataset import ParquetStreamPure

SRC = Path("/tmp/parcae-tok/tokenizer.json")
HASH = "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77"
ROWS = ["Hello world.", "你好世界。", "Mix 你好 123.", "short"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_tok(td):
    shutil.copy(SRC, td / "tokenizer.json")
    (td / "tokenizer_config.json").write_text(Path("/tmp/tok-compat/tokenizer_config.json").read_text())
    (td / "special_tokens_map.json").write_text(Path("/tmp/tok-compat/special_tokens_map.json").read_text())
    return Tokenizer.from_directory(td)


def make_ds(data, tok):
    return ParquetStreamPure(
        dataset_folder_path=str(data), seed=42, shuffle=False,
        shuffle_filenames=False, broadcast_glob=False,
        plan_for_later_rank_expansion_to=1,
        data_signature={"keys": ["text"]}, tokenizer=tok,
    )


def main():
    out = {"kind": "P1-D4-E2 NEW REPRODUCTION", "candidate": "NON-OFFICIAL"}
    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)
        tok = make_tok(td)
        out["hash"] = sha(td / "tokenizer.json")
        out["hash_ok"] = out["hash"] == HASH
        out["ids"] = {"bos": tok.bos_id, "eos": tok.eos_id, "pad": tok.pad_id, "vocab": tok.vocab_size}
        data = td / "data"
        data.mkdir()
        pq.write_table(pa.table({"text": ROWS}), data / "tiny.parquet")
        it = iter(make_ds(data, tok))
        raw = [next(it).tolist() for _ in range(4)]
        out["source_texts"] = ROWS
        out["source_tokens"] = raw
        collator = BestFitPackingCollator(tok, block_size=16, add_bos=True, add_eos=True, buffer_size=8)
        packed = PackedIterableDataset(make_ds(data, tok), collator, n_rows=2)
        loader = DataLoader(packed, batch_size=1, shuffle=False, num_workers=0, collate_fn=unwrap_singleton_collate)
        inputs, labels, meta = next(iter(loader))
        out["dataloader"] = {
            "input_ids": inputs.tolist(),
            "labels": labels.tolist(),
            "input_bos": int((inputs == 0).sum()),
            "input_eos": int((inputs == 1).sum()),
            "input_pad": int((inputs == 2).sum()),
            "label_bos": int((labels == 0).sum()),
            "label_eos": int((labels == 1).sum()),
            "label_pad": int((labels == 2).sum()),
            "label_eq_2": (labels == 2).tolist(),
            "label_eq_0": (labels == 0).tolist(),
            "valid_labels": int((labels != tok.pad_id).sum()),
            "ignored_if_ignore2": int((labels == 2).sum()),
        }
        logits = torch.tensor([[[0., 0, 0, 10, 0, 0, 0, 0], [0, 0, 0, 0, 10, 0, 0, 0], [0, 0, 0, 10, 0, 0, 0, 0], [0, 0, 0, 0, 10, 0, 0, 0]]], dtype=torch.float32)
        lab = torch.tensor([[3, 2, 3, 2]])
        out["loss"] = {
            "logits": logits.tolist(),
            "labels": lab.tolist(),
            "dtype": str(logits.dtype),
            "shape": list(logits.shape),
            "reduction": "mean",
            "ignored_when_2": (lab == 2).tolist(),
            "ignored_when_0": (lab == 0).tolist(),
            "loss_ignore2": float(F.cross_entropy(logits.reshape(-1, 8), lab.reshape(-1), ignore_index=2)),
            "loss_ignore0": float(F.cross_entropy(logits.reshape(-1, 8), lab.reshape(-1), ignore_index=0)),
        }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
