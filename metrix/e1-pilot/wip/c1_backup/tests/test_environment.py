"""Environment of the run (protocol v1.1 section 0; Implementation Task Order V1 section 5 "依赖"): the interpreter is
the one named in requirements.lock, the library versions are those of DATA_MANIFEST.json model.libraries, and a
different library version stops the run with ST8 (BLOCKED)."""
import platform
import re

import pytest

from metrix_e1 import frozen as FZ
from metrix_e1.errors import ST8Error

from conftest import PILOT


def test_python_is_the_locked_interpreter():
    lines = [ln for ln in (PILOT / "requirements.lock").read_text(encoding="utf-8").splitlines()
             if re.fullmatch(r"# python: CPython \d+\.\d+\.\d+", ln)]
    assert len(lines) == 1
    assert platform.python_implementation() == "CPython"
    assert lines[0] == "# python: CPython %s" % platform.python_version()


def test_library_versions_match_protocol(fz):
    got = FZ.check_library_versions(fz.data_manifest)
    assert sorted(got) == sorted(fz.data_manifest["model"]["libraries"])


def test_library_version_mismatch_is_st8(fz):
    libs = dict(fz.data_manifest["model"]["libraries"])
    FZ.check_library_versions(fz.data_manifest, installed={k: v + "+cu130" for k, v in libs.items()})   # local tag ignored
    for lib in libs:
        wrong = dict(libs)
        wrong[lib] = libs[lib] + ".1"
        with pytest.raises(ST8Error, match="ST8 -> BLOCKED: library %s is" % lib):
            FZ.check_library_versions(fz.data_manifest, installed=wrong)
        missing = {k: v for k, v in libs.items() if k != lib}
        with pytest.raises(ST8Error, match="library %s is not installed" % lib):
            FZ.check_library_versions(fz.data_manifest, installed=missing)
