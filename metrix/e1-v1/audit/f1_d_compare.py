# data-auditor, E1-V1 freeze audit, item (d): every data hash and input-file hash recorded in the
# protocol and the four JSON files of bc03348a (the version the Review Gate reviewed) and of the freeze
# commit, listed by field path (JSON) or by section (protocol), compared value by value; plus the set
# differences of all 40- and 64-digit hexadecimal strings between the two versions.
# Field-path mapping for the one structural change recorded by the Executor:
#   DATA_MANIFEST files["d2_dev.jsonl"].reference_canonical_sha256.mmlu -> .reference_canonical_sha256
#   DATA_MANIFEST files["d2_dev.jsonl"].reference_canonical_sha256.arc  -> .not_adopted_alternative.arc.reference_canonical_sha256
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1_lib as L  # noqa: E402

JSONS = L.FIVE[1:]
PROTO = L.FIVE[0]
REMAP = {
    ("metrix/e1-v1/DATA_MANIFEST.json", "files.d2_dev.jsonl.reference_canonical_sha256.mmlu"):
        "files.d2_dev.jsonl.reference_canonical_sha256",
    ("metrix/e1-v1/DATA_MANIFEST.json", "files.d2_dev.jsonl.reference_canonical_sha256.arc"):
        "files.d2_dev.jsonl.not_adopted_alternative.arc.reference_canonical_sha256",
}
INPUT_PAT = re.compile(r"(files_sha256|dev_source|test_source|source_file_sha256|decode_tokenizer_json_sha256|^anchor_text\.source$)")


def json_entries(commit, f):
    obj = L.git_json(commit, f)
    out = {}
    for path, kind, s in L.walk_json(obj):
        h64, h40 = L.hexes(s)
        for i, h in enumerate(h64):
            out[(f, path + ("<key>" if kind == "key" else ""), 64, i)] = h
        for i, h in enumerate(h40):
            out[(f, path + ("<key>" if kind == "key" else ""), 40, i)] = h
    return obj, out


def leaves(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, obj


def proto_entries(commit):
    lines = L.git_blob(commit, PROTO).decode("utf-8").split("\n")
    sec, out = "(before section 0)", []
    for n, line in enumerate(lines, 1):
        m = re.match(r"^(#+)\s*(.*)$", line)
        if m:
            mm = re.match(r"^([0-9]+(?:\.[0-9]+)*)", m.group(2))
            sec = "section " + mm.group(1) if mm else m.group(2)[:40]
        h64, h40 = L.hexes(line)
        for h in h64:
            out.append((sec, n, 64, h))
        for h in h40:
            out.append((sec, n, 40, h))
    return lines, out


def all_hex(commit):
    res = {}
    for f in L.FIVE:
        t = L.git_blob(commit, f).decode("utf-8")
        h64, h40 = L.hexes(t)
        res[f] = (h64, h40)
    return res


def main():
    ok = True
    print(f"base   = {L.BASE} (bc03348a, Review Gate review version)")
    print(f"freeze = {L.FREEZE}")
    base, frz = {}, {}
    bobj, fobj = {}, {}
    for f in JSONS:
        bobj[f], e = json_entries(L.BASE, f)
        base.update(e)
        fobj[f], e = json_entries(L.FREEZE, f)
        frz.update(e)

    # ------------------------------------------------ JSON: 64-hex (data and input-file hashes) by field path
    for width, title in ((64, "64-hex values (sha256: data hashes and input-file hashes)"), (40, "40-hex values (git commits, Hub revisions)")):
        print(f"\n=== JSON {title}, by field path: base value -> freeze value")
        used = set()
        n_eq = n_diff = n_missing = 0
        for key in sorted(k for k in base if k[2] == width):
            f, path, w, i = key
            fpath = REMAP.get((f, path), path)
            fkey = (f, fpath, w, i)
            bv, fv = base[key], frz.get(fkey)
            used.add(fkey)
            if width == 64:
                cat = "input" if INPUT_PAT.search(path) else "data"
            else:
                cat = "rev"
            tag = "EQUAL" if bv == fv else ("MISSING in freeze" if fv is None else "DIFFERENT")
            n_eq += bv == fv
            n_diff += fv is not None and bv != fv
            n_missing += fv is None
            mapped = f"  [path mapped to {fpath}]" if fpath != path else ""
            occ = f"#{i}" if i else ""
            print(f"  {tag:5} {cat:5} {os.path.basename(f)}: {path}{occ} = {bv}" + ("" if bv == fv else f" | freeze {fv}") + mapped)
        new = sorted(k for k in frz if k[2] == width and k not in used)
        for f, path, w, i in new:
            print(f"  NEW in freeze  {os.path.basename(f)}: {path} = {frz[(f, path, w, i)]}")
        print(f"  summary ({width}-hex): base entries {sum(1 for k in base if k[2] == width)} | equal {n_eq} | different {n_diff} | missing in freeze {n_missing} | new paths in freeze {len(new)}")
        ok &= n_diff == 0 and n_missing == 0
        if width == 64:
            ok &= len(new) == 0

    # ------------------------------------------------ protocol: hex by section
    print("\n=== protocol METRIX_E1V1_PROTOCOL.md: 40/64-hex strings by section (line numbers of each version)")
    _, pb = proto_entries(L.BASE)
    _, pf = proto_entries(L.FREEZE)
    def by_sec(entries):
        d = {}
        for sec, n, w, h in entries:
            d.setdefault((sec, w, h), []).append(n)
        return d
    db, df = by_sec(pb), by_sec(pf)
    for key in sorted(set(db) | set(df), key=lambda k: (k[1], k[0], k[2])):
        sec, w, h = key
        lb, lf = db.get(key, []), df.get(key, [])
        tag = "SAME COUNT" if len(lb) == len(lf) else ("ONLY FREEZE" if not lb else ("ONLY BASE" if not lf else "COUNT DIFFERS"))
        print(f"  {tag:13} {w}-hex {sec}: {h} | base lines {lb} | freeze lines {lf}")
    # each sha256 value recorded in the base protocol must appear with the same value in the freeze protocol,
    # in the same section
    b64 = {(s, h) for s, n, w, h in pb if w == 64}
    f64 = {(s, h) for s, n, w, h in pf if w == 64}
    lost = sorted(b64 - f64)
    print(f"  64-hex (section, value) pairs of base missing in freeze: {lost if lost else 'none'} | added in freeze: {sorted(f64 - b64) if f64 - b64 else 'none'}")
    ok &= not lost
    ab = re.findall(r"[0-9a-f]{8}…[0-9a-f]{4}", L.git_blob(L.BASE, PROTO).decode())
    af = re.findall(r"[0-9a-f]{8}…[0-9a-f]{4}", L.git_blob(L.FREEZE, PROTO).decode())
    print(f"  abbreviated hashes (8…4, not counted as 40/64-hex): base {sorted(ab)} | freeze {sorted(af)} | same {sorted(ab) == sorted(af)}")

    # ------------------------------------------------ set differences of all hex strings
    print("\n=== set differences of all distinct 40- and 64-hex strings (whole file text), base vs freeze")
    hb, hf = all_hex(L.BASE), all_hex(L.FREEZE)
    U = {64: [set(), set()], 40: [set(), set()]}
    for f in L.FIVE:
        for w, idx in ((64, 0), (40, 1)):
            sb, sf = set(hb[f][idx]), set(hf[f][idx])
            U[w][0] |= sb
            U[w][1] |= sf
            cb = {h: hb[f][idx].count(h) for h in sb}
            cf = {h: hf[f][idx].count(h) for h in sf}
            cnt = sorted((h, cb.get(h, 0), cf.get(h, 0)) for h in sb | sf if cb.get(h, 0) != cf.get(h, 0))
            print(f"  {os.path.basename(f)} {w}-hex: distinct base {len(sb)} freeze {len(sf)} | base - freeze {sorted(sb - sf)} | freeze - base {sorted(sf - sb)}")
            if cnt:
                print(f"     occurrence counts changed (value, base, freeze): {cnt}")
    for w in (64, 40):
        sb, sf = U[w]
        print(f"  ALL FIVE FILES {w}-hex: distinct base {len(sb)} freeze {len(sf)} | base - freeze {sorted(sb - sf) if sb - sf else 'empty'} | freeze - base {sorted(sf - sb) if sf - sb else 'empty'}")
        if w == 64:
            ok &= not (sb - sf) and not (sf - sb)
    up = [h for f in L.FIVE for h in hf[f][0] + hf[f][1] if h != h.lower()]
    print(f"  hex strings with upper-case letters in the freeze files: {up if up else 'none'}")

    # ------------------------------------------------ report only: every other JSON leaf that differs
    print("\n=== report only: JSON leaf paths whose value differs between base and freeze, or exists in only one (all leaves, hex or not)")
    for f in JSONS:
        lb, lf = dict(leaves(bobj[f])), dict(leaves(fobj[f]))
        rows = []
        for p in sorted(set(lb) | set(lf)):
            if p not in lf:
                rows.append(f"    only base   {p} = {str(lb[p])[:110]!s}")
            elif p not in lb:
                rows.append(f"    only freeze {p} = {str(lf[p])[:110]!s}")
            elif lb[p] != lf[p]:
                rows.append(f"    changed     {p}: {str(lb[p])[:70]!s} -> {str(lf[p])[:70]!s}")
        print(f"  {os.path.basename(f)}: {len(rows)} leaf differences")
        for r in rows:
            print(r)
    print("\nITEM (d):", "ALL DATA AND INPUT HASHES EQUAL" if ok else "DIFFERENCE PRESENT")


if __name__ == "__main__":
    main()
