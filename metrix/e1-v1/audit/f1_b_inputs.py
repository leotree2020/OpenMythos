# data-auditor, E1-V1 freeze audit, item (b): input files.
# Downloads every input file from the Hugging Face Hub at the repo / revision / file name recorded in
# DATA_MANIFEST.json and DAMAGE_MANIFEST.json of the freeze commit (read with git cat-file), and
# compares the sha256 of the whole file with the manifest value. Files go to audit/tmp_freeze/inputs
# (not committed). Also: eval_sets.jsonl (in the repository) whole-file sha256, and per-(domain, split)
# row counts by matching only the row-prefix bytes with the regex of protocol section 0 (no row is
# decoded or JSON-parsed here).
# TEST sources (MMLU test, ARC test) : whole-file sha256 and the parquet footer row count only.
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1_lib as L  # noqa: E402


def download(kind, repo, rev, path):
    out = L.local_input(repo, path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    base = "https://huggingface.co/" + ("datasets/" if kind == "dataset" else "")
    url = f"{base}{repo}/resolve/{rev}/{path}"
    hdr = out + ".headers"
    cmd = ["curl", "-sS", "-L", "--fail", "--retry", "3", "--max-time", "1200", "-D", hdr, "-o", out, url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"download failed {url}: {r.stderr}")
    h = {}
    with open(hdr, "r", encoding="latin-1") as f:
        for line in f:
            m = re.match(r"^([A-Za-z0-9-]+):\s*(.*?)\s*$", line)
            if m:
                k = m.group(1).lower()
                if k not in h:  # first occurrence = the Hub's response (before the CDN redirect)
                    h[k] = m.group(2).strip('"')
    return out, url, h


def main():
    ok = True
    dm = L.git_json(L.FREEZE, "metrix/e1-v1/DATA_MANIFEST.json")
    gm = L.git_json(L.FREEZE, "metrix/e1-v1/DAMAGE_MANIFEST.json")
    items = []  # (label, kind, repo, rev, path, manifest sha256, manifest field, is_test, manifest_rows)
    tk = dm["model"]["tokenizer"]
    for name, h in tk["files_sha256"].items():
        items.append(("Qwen tokenizer", "model", tk["repo"], tk["revision"], name, h,
                      f"DATA_MANIFEST.model.tokenizer.files_sha256.{name}", False, None))
    m = re.match(r"^(\S+)@([0-9a-f]{40}), (\S+) \(sha256 ([0-9a-f]{64})\)$", dm["anchor_text"]["source"])
    print("DATA_MANIFEST.anchor_text.source parsed:", m.groups() if m else None)
    items.append(("anchor source", "dataset", m.group(1), m.group(2), m.group(3), m.group(4),
                  "DATA_MANIFEST.anchor_text.source", False, None))
    d1 = gm["d1"]
    m2 = re.match(r"^(\S+)@([0-9a-f]{40}),", d1["decode_with"])
    print("DAMAGE_MANIFEST.d1.decode_with parsed:", m2.groups() if m2 else None)
    items.append(("parcae tokenizer", "model", m2.group(1), m2.group(2), "tokenizer.json", d1["decode_tokenizer_json_sha256"],
                  "DAMAGE_MANIFEST.d1.decode_tokenizer_json_sha256", False, None))
    mm = gm["d2"]["datasets"]["mmlu"]
    items.append(("MMLU DEV source", "dataset", mm["repo"], mm["revision"], mm["dev_source"]["file"], mm["dev_source"]["sha256"],
                  "DAMAGE_MANIFEST.d2.datasets.mmlu.dev_source.sha256", False, mm["dev_source"]["rows"]))
    items.append(("MMLU TEST source", "dataset", mm["repo"], mm["revision"], mm["test_source"]["file"], mm["test_source"]["sha256"],
                  "DAMAGE_MANIFEST.d2.datasets.mmlu.test_source.sha256", True, mm["test_source"]["rows"]))
    ar = gm["d2"]["datasets"]["arc"]
    for i, s in enumerate(ar["dev_source"]):
        items.append(("ARC DEV source (not adopted)", "dataset", ar["repo"], ar["revision"], s["file"], s["sha256"],
                      f"DAMAGE_MANIFEST.d2.datasets.arc.dev_source[{i}].sha256", False, s["rows"]))
    for i, s in enumerate(ar["test_source"]):
        items.append(("ARC TEST source (not adopted)", "dataset", ar["repo"], ar["revision"], s["file"], s["sha256"],
                      f"DAMAGE_MANIFEST.d2.datasets.arc.test_source[{i}].sha256", True, s["rows"]))

    import pyarrow.parquet as pq
    print()
    n_ok = 0
    for label, kind, repo, rev, path, exp, field, is_test, rows in items:
        out, url, h = download(kind, repo, rev, path)
        b_sha = L.file_sha256(out)
        size = os.path.getsize(out)
        eq = b_sha == exp
        print(f"[{label}] {kind} {repo} @ {rev} : {path}")
        print(f"   url {url}")
        print(f"   downloaded bytes {size} | sha256 {b_sha}")
        print(f"   manifest {field} = {exp} | equal {eq}")
        xc = h.get("x-repo-commit")
        print(f"   Hub response x-repo-commit {xc} (= pinned revision: {xc == rev})", end="")
        # The Hub's x-linked-etag (else etag) is the LFS sha256 (64 hex) for LFS files and the git blob
        # sha1 (40 hex) for files stored in git (first run of this script compared both with the sha256;
        # corrected, see stdout/f1_b_inputs_firstrun_freeze.txt).
        xle = h.get("x-linked-etag") or h.get("etag")
        if xle and len(xle) == 64:
            print(f" | x-linked-etag {xle}: LFS sha256 (= sha256 of download: {xle == b_sha})")
            hub_ok = xle == b_sha
        else:
            with open(out, "rb") as f:
                bs1 = L.git_blob_sha1(f.read())
            print(f" | x-linked-etag {xle}: not LFS, git blob sha1 (= git blob sha1 of download {bs1}: {xle == bs1})")
            hub_ok = xle == bs1
        if path.endswith(".parquet"):
            pf = pq.ParquetFile(out)  # reads the footer only
            nr = pf.metadata.num_rows
            what = "TEST source: footer row count only, no row read" if is_test else "footer row count"
            if rows is None:
                print(f"   parquet {what}: {nr} (the manifest records no row count for this file; report only)")
            else:
                print(f"   parquet {what}: {nr} | manifest rows {rows} | equal {nr == rows}")
                ok &= nr == rows
        ok &= eq and (xc == rev) and hub_ok
        n_ok += eq
    print(f"\ndownloaded-file sha256 equal to manifest: {n_ok} of {len(items)}")

    # eval_sets.jsonl (repository file)
    print()
    p = os.path.join(L.REPO, d1["source_file"])
    with open(p, "rb") as f:
        raw = f.read()
    blob = L.git_blob(L.FREEZE, d1["source_file"])
    w_sha, c_sha = L.sha256_bytes(raw), L.sha256_bytes(blob)
    print(f"[eval_sets.jsonl] {d1['source_file']}: bytes {len(raw)}")
    print(f"   sha256 working tree {w_sha} | in freeze commit (git cat-file) {c_sha} | identical {raw == blob}")
    print(f"   manifest DAMAGE_MANIFEST.d1.source_file_sha256 = {d1['source_file_sha256']} | equal {w_sha == d1['source_file_sha256']}")
    ok &= w_sha == d1["source_file_sha256"] and raw == blob
    counts, unmatched, n = {}, 0, 0
    for line in raw.split(b"\n"):
        if not line:
            continue
        n += 1
        mt = L.ROW_PREFIX.match(line)
        if not mt:
            unmatched += 1
            continue
        k = (mt.group(1), mt.group(2))
        counts[k] = counts.get(k, 0) + 1
    print(f"   rows {n} | rows not matching the protocol section 0 prefix regex: {unmatched}")
    print("   counts by (domain bytes, split bytes) from the row prefix only:", dict(sorted(counts.items())))
    for dom in d1["domains"]:
        db = dom.encode()
        nd, nt = counts.get((db, b"dev"), 0), counts.get((db, b"test"), 0)
        c1 = nd == d1["dev"]["per_domain"]
        c2 = nt - 25 == d1["test"]["available_per_domain_after_skip"]
        print(f"   {dom}: dev rows {nd} (manifest d1.dev.per_domain {d1['dev']['per_domain']}: {c1}); test rows {nt}, "
              f"after skipping 25: {nt - 25} (manifest d1.test.available_per_domain_after_skip {d1['test']['available_per_domain_after_skip']}: {c2})")
        ok &= c1 and c2
    ok &= unmatched == 0
    print("\nITEM (b):", "ALL MATCH" if ok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
