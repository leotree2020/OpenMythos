"""Read-only replica of the start checks of `e2c_stage2.py verify` (no ledger, no authorization, no attempt
directory, no job, no key enumeration): context(), prestart(), e1_sets(), appendix_a() text check, the state checks
of the output directory, and the frozen code tree against the HEAD blobs."""
import argparse, hashlib, json, os, subprocess, sys
E = sys.argv[1]
sys.path.insert(0, E)
import e2c_stage2 as S

assert not S.TEST_DIR and not any(k.startswith(("E2C_", "STUB_")) for k in os.environ), "test or stage variables set"
ctx = S.context()
R, p, out = ctx["R"], ctx["p"], ctx["out"]
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=S.ROOT, capture_output=True, text=True, check=True).stdout.strip()
print("mode real:", not ctx["test"], "| out:", out, "| freeze path:", p["freeze"])
print("cap", ctx["cap"], "heartbeat", ctx["heartbeat"], "updates", ctx["updates"], "batch", ctx["batch"], "workers", ctx["workers"],
      "| ledger", S.ledger_location())
try:
    inp = S.prestart(ctx, head)
    print("prestart: PASS (would not refuse)")
    print("  code changes since f7a0ffe:", inp["code_changes"])
    print("  environment:", inp["environment"])
    print("  lambda:", inp["lambda"], "| lambda2:", inp["lambda2"])
    print("  reference records:", len(inp["references"]), "digest", inp["references_digest"],
          "| seeds", sorted({r["seed"] for r in inp["references"]}))
    b = inp["basis"]
except S.S2Stop as e:
    print("prestart: REFUSED:", e)
    b = R.basis(p)
print("basis: code_tree_sha256", b["code_tree_sha256"], "| files", len(b["code_files"]))
print("       preregistration", b["preregistration_sha256"], "| design review", b["design_review_sha256"],
      "| sets manifest", b["sets_manifest_sha256"])
mism = []
for rel, h in sorted(b["code_files"].items()):
    blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=S.ROOT, capture_output=True).stdout
    if hashlib.sha256(blob).hexdigest() != h:
        mism.append(rel)
print("frozen code files differing from the HEAD blobs:", mism)
for rel in sorted(S.ALLOWED_CODE_CHANGES):
    print("  ", rel.split("/")[-1], b["code_files"].get(rel))
e1, bad = S.e1_sets(ctx)
print("E1 sets:", "PASS" if not bad else f"PROBLEMS {bad}", "| manifest", e1["manifest_sha256"], "| files", len(e1["files"]))
try:
    script, stdout, letters = S.appendix_a(p["prereg"])
    print("Appendix A text: script", S.sha256_bytes(script.encode())[:16], "stdout", S.sha256_bytes(stdout.encode())[:16],
          "letters", len(letters), "(not run)")
    print("Appendix A stated output:", " | ".join(stdout.strip().splitlines()))
except S.S2Stop as e:
    print("Appendix A: REFUSED:", e)
a = argparse.Namespace(resume=False)
print("verify state (first launch, no --resume):", S.verify_state_problem(out, a, os.path.join(out, "stage2_verify.json"),
                                                                        os.path.join(out, "verify_stop.json")) or "no refusal")
print("stage2/ exists:", os.path.exists(out), "| freeze exists:", os.path.exists(p["freeze"]),
      "| attempts:", S.attempts_of(out))
for n in ["budget_ledger_s2.json", "budget_ledger_s2.json.lock", "stage2_verify.json", "v2_streams.json", "verify_stop.json",
          "stage2_freeze_receipt.json"] + list(S.REVIEW_RECORDS.values()):
    print(f"  {n}: {os.path.exists(os.path.join(out, n))}")
hist = subprocess.run(["git", "log", "--all", "--format=%h %s", "--", "experiments/gate_e/e2c/stage2", "experiments/gate_e/e2c/e2c_workload_freeze.json"],
                      cwd=S.ROOT, capture_output=True, text=True).stdout.strip()
print("git history of stage2/ or the freeze (all refs):", hist or "none")
