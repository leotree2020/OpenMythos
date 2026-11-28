# data-auditor, E1-V1 freeze audit, item (a): raw-byte sha256 of the protocol and the four JSON files
# in the freeze commit (read with git cat-file from the commit object), compared with the working-tree
# files; the same for bc03348a (the version the Review Gate reviewed), for reference.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1_lib as L  # noqa: E402  (the auditor's own helper)


def main():
    ok = True
    head = L.git("rev-parse", "HEAD").decode().strip()
    print("HEAD", head, "| freeze commit", L.FREEZE, "| HEAD == freeze commit", head == L.FREEZE)
    ok &= head == L.FREEZE
    print("commit type", L.git("cat-file", "-t", L.FREEZE).decode().strip(),
          "| parents", L.git("rev-list", "--parents", "-n", "1", L.FREEZE).decode().split()[1:])
    print("git diff --stat HEAD -- (the five files), working tree vs HEAD:",
          repr(L.git("diff", "--stat", "HEAD", "--", *L.FIVE).decode()))
    print()
    print("(a) freeze commit", L.FREEZE)
    for p in L.FIVE:
        blob_id = L.git("rev-parse", f"{L.FREEZE}:{p}").decode().strip()
        b = L.git_blob(L.FREEZE, p)
        h_commit = L.sha256_bytes(b)
        with open(os.path.join(L.REPO, p), "rb") as f:
            w = f.read()
        h_work = L.sha256_bytes(w)
        eq = h_commit == h_work and b == w
        sha1_ok = L.git_blob_sha1(b) == blob_id
        print(f"  {p}")
        print(f"     bytes {len(b)} | git blob {blob_id} (sha1 of the bytes read matches: {sha1_ok})")
        print(f"     sha256 at commit (git cat-file blob) {h_commit}")
        print(f"     sha256 of working-tree file          {h_work}")
        print(f"     identical bytes: {eq}")
        ok &= eq and sha1_ok
    print()
    print("reference: bc03348a", L.BASE, "(Review Gate review version)")
    for p in L.FIVE:
        b = L.git_blob(L.BASE, p)
        bf = L.git_blob(L.FREEZE, p)
        print(f"  {p}: bytes {len(b)} sha256 {L.sha256_bytes(b)} | changed in the freeze commit: {b != bf}")
    print()
    print("ITEM (a):", "ALL MATCH" if ok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
