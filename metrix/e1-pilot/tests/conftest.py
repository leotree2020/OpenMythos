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
