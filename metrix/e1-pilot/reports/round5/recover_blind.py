#!/usr/bin/env python3
"""Round 5, task 3: restore the 10 round-4 blind-test records and check them against their sha256 commitments.

The files were written in the round-4 container (/root/.blind_r4/, session_01J5mxaVWCGyNj16YJV8cPy5) and only
their sha256 and sizes were committed (reports/round4/t6_blind_timeline.txt). That container is not this one.
Their text is in the round-4 session transcript, read with the list_events tool (kinds ["assistant"]):
  review_wip-X.md  = the "content" of the Write tool call whose file_path is /root/.blind_r4/review_wip-X.md
  prompt_wip-X.txt = the "prompt" of the Agent tool call "Review branch wip-X diff", plus one final "\\n"
                     (the round-4 printf command ended the file with "```\\n"; the Agent prompt has no final newline)

  extract  DUMP...  --source-out SOURCE.jsonl   keep only those 10 tool calls (event uuid, time, tool input)
  rebuild  --source SOURCE.jsonl --timeline T6.txt --out-dir DIR
           write the 10 files, compare sha256 and size with the timeline file and the wip-X commit hash
           named in each prompt with the one recorded there; exit 0 only if all 10 match
"""
import argparse
import hashlib
import json
import re
import sys

BRANCHES = ["wip-a", "wip-b", "wip-c", "wip-d", "wip-e"]


def load_dump(path):
    raw = open(path, encoding="utf-8").read()
    return json.loads(raw[raw.index('{"ccr"'):raw.rindex("}") + 1])["ccr"]["data"]


def extract(dumps, source_out):
    rows = []
    for path in dumps:
        for ev in load_dump(path):
            msg = ev["assistant"]["internal_anthropic_catchall"]["message"]
            for c in msg["content"]:
                if c.get("type") != "tool_use":
                    continue
                i = c["input"]
                if c["name"] == "Write" and i["file_path"].startswith("/root/.blind_r4/"):
                    name = i["file_path"].rsplit("/", 1)[1]
                elif c["name"] == "Agent" and re.fullmatch(r"Review branch wip-[a-e] diff", i.get("description", "")):
                    name = "prompt_%s.txt" % i["description"].split()[2]
                else:
                    continue
                rows.append({"file": name, "event_uuid": ev["assistant"]["uuid"], "created_at": ev["created_at"],
                             "tool_use_id": c["id"], "tool": c["name"], "input": i})
    rows.sort(key=lambda r: r["created_at"])
    with open(source_out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    for r in rows:
        print(r["created_at"], r["event_uuid"], r["tool"], r["file"])
    print("tool calls kept: %d (files: %d)" % (len(rows), len({r["file"] for r in rows})))
    return 0 if sorted(r["file"] for r in rows) == sorted(
        ["prompt_%s.txt" % b for b in BRANCHES] + ["review_%s.md" % b for b in BRANCHES]) else 1


def rebuild(source, timeline, out_dir):
    t6 = open(timeline, encoding="utf-8").read()
    want_sha = dict((m.group(2), m.group(1)) for m in re.finditer(r"^([0-9a-f]{64})  /root/\.blind_r4/(\S+)$", t6, re.M))
    want_size = dict((m.group(2), int(m.group(1))) for m in re.finditer(r"^-rw-r--r-- 1 root root\s+(\d+) \S+ (\S+)$", t6, re.M))
    want_commit = dict(re.findall(r"^(wip-[a-e]) ([0-9a-f]{40}) parent=", t6, re.M))
    rows = [json.loads(line) for line in open(source, encoding="utf-8")]
    ok = 0
    for r in rows:
        name = r["file"]
        text = r["input"]["content"] if r["tool"] == "Write" else r["input"]["prompt"] + "\n"
        data = text.encode("utf-8")
        with open("%s/%s" % (out_dir, name), "wb") as fh:
            fh.write(data)
        got = hashlib.sha256(data).hexdigest()
        line = "%-17s sha256 %s recorded %s match %s | bytes %d recorded %s" % (
            name, got, want_sha.get(name), got == want_sha.get(name), len(data), want_size.get(name))
        good = got == want_sha.get(name) and len(data) == want_size.get(name)
        if name.startswith("prompt_"):
            b = name[len("prompt_"):-len(".txt")]
            m = re.match(r"请审查本地分支 (wip-[a-e])\(提交 ([0-9a-f]{40})\)", text)
            same = bool(m) and m.group(1) == b and m.group(2) == want_commit.get(b)
            line += " | commit in prompt %s recorded %s match %s" % (m.group(2) if m else None, want_commit.get(b), same)
            good = good and same
        print(line)
        ok += good
    print("recorded sha256 entries: %d; files rebuilt: %d; all checks match: %d" % (len(want_sha), len(rows), ok))
    return 0 if ok == len(want_sha) == len(rows) == 10 else 1


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("dumps", nargs="+")
    e.add_argument("--source-out", required=True)
    r = sub.add_parser("rebuild")
    r.add_argument("--source", required=True)
    r.add_argument("--timeline", required=True)
    r.add_argument("--out-dir", required=True)
    a = p.parse_args()
    sys.exit(extract(a.dumps, a.source_out) if a.cmd == "extract" else rebuild(a.source, a.timeline, a.out_dir))


if __name__ == "__main__":
    main()
