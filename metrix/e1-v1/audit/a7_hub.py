# data-auditor, E1-V1 round 1, supplement to items 1 and 5: independent check, against the
# Hugging Face Hub API (read-only GET / paths-info queries for public repositories), that the
# manifest sha256 values are the files of the pinned revisions (LFS oid = sha256 of the file;
# for non-LFS files the git blob id is compared with the git blob sha1 of the local file), and that
# the licenses are as stated. Plus a local ARC DEV-source breakdown by file and number of options.
import hashlib
import json
import subprocess
import sys

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402


def curl(url, post=None):
    cmd = ["curl", "-sS", "--max-time", "60", url]
    if post is not None:
        cmd = ["curl", "-sS", "--max-time", "60", "-X", "POST", "--data-urlencode", "paths=" + post, url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


def git_blob_sha1(path):
    b = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def chk(label, got, exp):
    ok = got == exp
    print(f"{'OK  ' if ok else 'DIFF'} {label}: got {got} | expected {exp}")
    return ok


def info(kind, repo, rev, path):
    r = curl(f"https://huggingface.co/api/{kind}/{repo}/paths-info/{rev}", post=path)
    return r[0] if isinstance(r, list) and r else r


def main():
    ok = True
    dm = A.load_json(A.V1 + "/DATA_MANIFEST.json")
    gm = A.load_json(A.V1 + "/DAMAGE_MANIFEST.json")
    files = []
    mm = gm["d2"]["datasets"]["mmlu"]
    for src in (mm["dev_source"], mm["test_source"]):
        files.append(("datasets", mm["repo"], mm["revision"], src["file"], src["sha256"], A.MMLU_DIR + "/" + src["file"]))
    ar = gm["d2"]["datasets"]["arc"]
    for src in ar["dev_source"] + ar["test_source"]:
        files.append(("datasets", ar["repo"], ar["revision"], src["file"], src["sha256"], A.ARC_DIR + "/" + src["file"]))
    tk = dm["model"]["tokenizer"]
    for name, h in tk["files_sha256"].items():
        files.append(("models", tk["repo"], tk["revision"], name, h, A.QWEN_DIR + "/" + name))
    files.append(("models", "SandyResearch/parcae-tokenizer", "6247b5d0592876b73660f34c2dd16c9db9e9045c", "tokenizer.json",
                  gm["d1"]["decode_tokenizer_json_sha256"], A.PARCAE_TOK))
    files.append(("datasets", "SandyResearch/fineweb-edu-shuffled", "4d1138c0e4d51d98813997ce3560e05a32bf91de",
                  "data/sample-100BT/train/shard_00000.parquet", "6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22", A.ANCHOR_PARQUET))
    for kind, repo, rev, path, exp, local in files:
        r = info(kind, repo, rev, path)
        lfs = (r.get("lfs") or {}).get("oid") if isinstance(r, dict) else None
        if lfs:
            ok &= chk(f"Hub {repo}@{rev[:8]} {path} LFS oid = manifest sha256", lfs, exp)
        else:
            blob = r.get("oid") if isinstance(r, dict) else None
            ok &= chk(f"Hub {repo}@{rev[:8]} {path} (not LFS) git blob id = git blob sha1 of the local file whose sha256 is the manifest value",
                      blob, git_blob_sha1(local))
            ok &= chk(f"   local {path} sha256 = manifest", A.file_sha256(local), exp)
    for kind, repo, rev, lic in (("datasets", mm["repo"], mm["revision"], "mit"), ("datasets", ar["repo"], ar["revision"], "cc-by-sa-4.0"),
                                 ("models", "Qwen/Qwen3-1.7B", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e", "apache-2.0")):
        r = curl(f"https://huggingface.co/api/{kind}/{repo}/revision/{rev}")
        ok &= chk(f"Hub {repo} revision resolves to itself", r.get("sha"), rev)
        got = (r.get("cardData") or {}).get("license")
        got = got[0] if isinstance(got, list) else got
        ok &= chk(f"Hub {repo}@{rev[:8]} cardData.license", got, lic)
    # ARC DEV-source breakdown (validation files only)
    import pyarrow.parquet as pq
    tot = {}
    for src in ar["dev_source"]:
        rows = pq.read_table(A.ARC_DIR + "/" + src["file"]).to_pylist()
        c = {}
        for r in rows:
            c[len(r["choices"]["label"])] = c.get(len(r["choices"]["label"]), 0) + 1
        print(f"ARC {src['file']}: rows {len(rows)} by number of options {dict(sorted(c.items()))}")
        for k, v in c.items():
            tot[k] = tot.get(k, 0) + v
    print(f"ARC DEV source total by number of options {dict(sorted(tot.items()))}: 4-option rows {tot.get(4, 0)}, other {sum(v for k, v in tot.items() if k != 4)}")
    print("SUPPLEMENT:", "ALL MATCH" if ok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
