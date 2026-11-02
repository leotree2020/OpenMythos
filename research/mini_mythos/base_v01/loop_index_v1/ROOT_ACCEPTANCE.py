"""Read-only post-run custody/interpretation review; no model calls."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

REPO = Path("/workspaces/mythos-loop-index-cpu-v1")
ROOT = REPO / "research/mini_mythos/base_v01/loop_index_v1"
RUN = Path("/workspaces/mythos-evidence/base_v01/loop_index/attempt-v1")
OLD = Path("/workspaces/mythos-evidence/base_v01/depth_lora/attempt-v1")
OUT = RUN.parent / "acceptance-v1.json"
FREEZE = "c78be02123a39f54d60f406d3f4eeaf33dc67d50"
RESULT_COMMIT = "ea5d0ca3e2eb23b432cc50aabc955b251c4464f6"


def read(path):
    return json.loads(Path(path).read_text())


def pin(path):
    h = hashlib.sha256()
    n = 0
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
            n += len(b)
    return {"bytes": n, "sha256": h.hexdigest()}


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()


report = {"Purpose": "Root acceptance of loop-index pilot and retained-evidence custody",
          "Environment": "Read-only Python standard-library audit; no model or Torch import",
          "Input": {"execution_freeze": FREEZE, "run": str(RUN)},
          "Expected": "Complete registered experiment, sealed bytes, original baseline bridge and honest scope",
          "Actual": {}, "Status": "NOT TESTED", "checks": []}


def check(name, okay, actual=None):
    report["checks"].append({"Purpose": name, "Expected": True, "Actual": actual,
                             "Status": "PASS" if okay else "FAIL"})
    if not okay:
        raise ValueError(name)


try:
    publication = read(RUN / "publication.json")
    head = git("rev-parse", "HEAD")
    remote = git("ls-remote", "origin", "refs/heads/mythos-loop-index-cpu-v1").split()[0]
    check("clean published result checkpoint and review checkout", publication["Status"] == "PASS"
          and publication["head"] == RESULT_COMMIT and git("merge-base", RESULT_COMMIT, head) == RESULT_COMMIT
          and head == remote and not git("status", "--porcelain"), head)
    summary, audit = read(RUN / "summary.json"), read(RUN / "audit.json")
    check("execution freeze and immutable source manifest", git("merge-base", FREEZE, head) == FREEZE
          and summary["Input"]["execution_freeze"] == FREEZE
          and json.loads(git("show", FREEZE + ":research/mini_mythos/base_v01/loop_index_v1/SOURCE_MANIFEST.json"))
          == read(ROOT / "SOURCE_MANIFEST.json"))
    worker, reload = (read(RUN / mode / "public/completion.json") for mode in ("worker", "reload"))
    check("operator worker reload audit and custody complete", all(x["Status"] == "PASS"
          for x in (summary, audit, worker, reload, read(RUN / "custody.json"))))
    check("frozen main schedule complete", worker["Actual"] == {
        "calls_started":293,"calls_completed":293,"train_steps":128,"eval_rows":160,
        "zero_control_calls":5,"model_loads":1,"adapters_saved":4,"reload_calls":0})
    check("four new-process checks", reload["Actual"]["reload_calls"] == 4
          and reload["Actual"]["calls_started"] == reload["Actual"]["calls_completed"] == 4)
    check("independent audit full finite coverage", audit["Actual"]["rows"] == 160
          and audit["Actual"]["finite_components"] == 335544320 and audit["check_counts"]["FAIL"] == 0)
    manifests = {"sources": read(ROOT / "SOURCE_MANIFEST.json"),
                 "inputs": read(ROOT / "INPUT_MANIFEST.json"),
                 "external": read(ROOT / "EXTERNAL_EVIDENCE_MANIFEST.json")}
    for label, manifest in manifests.items():
        for name, expected in manifest.items():
            path = ROOT / name if label == "sources" else Path(name)
            check(label + " byte identity " + name, pin(path) == expected)
    public = read(ROOT / "PUBLIC_EXPORT.json")["files"]
    for name in public:
        check("public exact copy " + name, pin(ROOT / "evidence" / name) == pin(RUN / name))
    current = [r for r in read(RUN / "worker/public/evaluation.json")["rows"] if r["arm"] == "fixed32"]
    old = {(r["article_index"], r["eval_seed"]): r
           for r in read(OLD / "worker/public/evaluation.json")["rows"] if r["arm"] == "fixed32"}
    check("exact32 original baseline rows", len(current) == len(old) == 32)
    for row in current:
        previous = old[row["article_index"], row["eval_seed"]]
        keys = ("logits_sha256", "targets_sha256", "h0_sha256", "nll_mean", "correct")
        check("baseline bridge " + str((row["article_index"], row["eval_seed"])),
              all(row[k] == previous[k] for k in keys)
              and all(row["observer"][k] == previous["observer"][k]
                      for k in ("h0_sha256", "rng_before_sha256", "rng_after_sha256")))
        check("original baseline raw retained " + previous["logits_file"],
              pin(OLD / "worker" / previous["logits_file"])["sha256"] == previous["logits_sha256"])
    adapters = read(RUN / "worker/public/adapters.json")["rows"]
    check("equal96 useful trainables", len(adapters) == 4 and all(r["trainable_parameters"] == 96 for r in adapters))
    tests = {name: read(RUN / (name + "_report.json"))["Actual"]["run"]
             for name in ("test_startup", "test_loop", "test_data")}
    check("76 target developer checks", tests == {"test_startup":16,"test_loop":27,"test_data":33}, tests)
    check("raw reserve preserved", shutil.disk_usage(RUN).free >= 256 * 1024**2)
    report["Actual"] = {"result_commit": RESULT_COMMIT, "review_code_commit": head, "manifests_verified": {k:len(v) for k,v in manifests.items()},
        "public_copies_verified":len(public), "baseline_bridge_rows":32,
        "worker_check_counts":worker["checks"],"reload_check_counts":reload["checks"],
        "audit_check_counts":audit["check_counts"],"target_developer_tests":tests,
        "means":audit["Actual"]["means"],"comparisons":audit["Actual"]["comparisons"],
        "scientific_screens":audit["Actual"]["scientific_screens"],
        "result_interpretations":audit["Actual"]["result_interpretations"],
        "adapter_coverage":audit["Actual"].get("adapter_coverage"),
        "main_seconds":worker["seconds"],"reload_seconds":reload["seconds"],
        "disk_free_bytes":shutil.disk_usage(RUN).free,
        "scope":"Reused16-article development benchmark; no fresh-test, statistical, production, extrapolation or stacking claim"}
    report["Status"] = "PASS"
except Exception as exc:
    report["Status"] = "FAIL"
    report["error"] = repr(exc)
report["utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
report["check_counts"] = {s:sum(r["Status"] == s for r in report["checks"]) for s in ("PASS","FAIL")}
with OUT.open("x", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
    f.write("\n")
print(json.dumps({"Status":report["Status"],"checks":report["check_counts"],
                  "error":report.get("error"),"Actual":report["Actual"]}, allow_nan=False))
raise SystemExit(0 if report["Status"] == "PASS" else 2)
