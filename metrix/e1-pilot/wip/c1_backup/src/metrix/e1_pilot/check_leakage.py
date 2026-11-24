"""Protocol v1.1 section 3, execution interface of the leakage checks:

  python -m metrix.e1_pilot.check_leakage --data <DATA_DIR> --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json \
      --out <DATA_DIR>/leakage_report.json

The module path of the protocol cannot be a directory of the repository (metrix/e1-pilot has a hyphen), so it lives
here, under metrix/e1-pilot/src, as a namespace-package portion of `metrix`: with PYTHONPATH=metrix/e1-pilot/src the
command above works from the repository root. It only delegates to metrix_e1.leakage (no logic of its own).
"""
from metrix_e1._cli import run_guarded
from metrix_e1.leakage import main

if __name__ == "__main__":
    run_guarded(main)
