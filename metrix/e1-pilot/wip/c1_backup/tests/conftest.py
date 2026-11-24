"""Shared fixtures of the METRIX E1-PILOT unit tests (Implementation Task Order V1, section 6).

The tests need the pinned non-model inputs downloaded by `python -m metrix_e1.data fetch --inputs DIR`; the directory
is given by the environment variable METRIX_INPUTS_DIR. Without it the tests that need it fail (they are not
skipped). No model weights, no GPU, no TEST data.

  METRIX_INPUTS_DIR=DIR python -m pytest metrix/e1-pilot/tests
"""
import os
import sys
from pathlib import Path

import pytest

PILOT = Path(__file__).resolve().parents[1]
SRC = PILOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from metrix_e1 import data as D            # noqa: E402
from metrix_e1 import frozen as FZ         # noqa: E402


@pytest.fixture(scope="session")
def inputs_dir():
    d = os.environ.get("METRIX_INPUTS_DIR")
    if not d or not Path(d).is_dir():
        pytest.fail("METRIX_INPUTS_DIR must name the directory written by `python -m metrix_e1.data fetch`")
    return Path(d)


@pytest.fixture(scope="session")
def fz():
    return FZ.load()


@pytest.fixture(scope="session")
def generated(fz, inputs_dir, tmp_path_factory):
    """The 8 non-TEST data files written by data.generate into a fresh directory."""
    out = tmp_path_factory.mktemp("generated")
    files, info = D.generate(fz, inputs_dir)
    D.write(files, out)
    return {"dir": out, "files": files, "info": info}


# ------------------------------------------------------------------------------ stage B fixtures (task order 6, 2-9)

def tiny_config(layers=2):
    """A random-initialisation Qwen3 configuration of the protocol's model class with the protocol tokenizer's
    vocabulary (so real token ids work), reduced in depth and width. No weights are loaded."""
    from transformers import Qwen3Config
    return Qwen3Config(vocab_size=151936, hidden_size=64, intermediate_size=128, num_hidden_layers=layers,
                       num_attention_heads=4, num_key_value_heads=2, head_dim=16, tie_word_embeddings=True)


def tiny_model(seed=0, layers=2):
    import torch
    from transformers import Qwen3ForCausalLM
    torch.manual_seed(seed)
    return Qwen3ForCausalLM(tiny_config(layers)).eval()


@pytest.fixture(scope="session")
def contract(fz):
    from metrix_e1 import contract as C
    return C.load(fz)


@pytest.fixture(scope="session")
def tok(fz, inputs_dir):
    p = D.params(fz)
    return D.load_qwen_tokenizer(p, D.check_inputs(fz, p, inputs_dir))


@pytest.fixture(scope="session")
def data_rows(generated):
    """The parsed non-TEST data files ({file name: rows}; candidates.json as its object)."""
    import json
    out = {n: FZ.parse_jsonl(b) for n, b in generated["files"].items() if n.endswith(".jsonl")}
    out["candidates.json"] = json.loads(generated["files"]["candidates.json"])
    return out


@pytest.fixture(scope="session")
def real_config(inputs_dir):
    """config.json of the pinned model revision (downloaded by `python -m metrix_e1.train fetch-config`)."""
    from transformers import AutoConfig
    d = inputs_dir / "qwen_model"
    if not (d / "config.json").is_file():
        pytest.fail("run `python -m metrix_e1.train fetch-config --inputs METRIX_INPUTS_DIR` first")
    return AutoConfig.from_pretrained(str(d), local_files_only=True)
