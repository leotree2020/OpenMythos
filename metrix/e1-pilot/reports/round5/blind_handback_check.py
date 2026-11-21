#!/usr/bin/env python3
"""Round 5, task 3 (added after the code-reviewer's MAJOR 3): close the provenance chain of the blind-test reviews.

recover_blind.py restores review_wip-X.md from the round-4 Executor's Write call. This script checks that text
against the subagent's own final report in the same transcript: the SubagentHandback tool call whose
parent_tool_use_id is the id of the Agent call "Review branch wip-X diff" (from source_events.jsonl).
The harness delivered each report to the Executor with every line indented by two spaces; the expected file
content is therefore "  " + line for every line of the message, joined by "\\n", plus one final "\\n".
The handback calls are written to --handbacks-out. Exit 0 only if all 5 files match.

  python blind_handback_check.py PAGE... --source SOURCE_EVENTS.jsonl --blind-dir DIR --handbacks-out OUT.jsonl
"""
import argparse
import json
import sys


def load_page(path):
    raw = open(path, encoding="utf-8").read()
    return json.loads(raw[raw.index('{"ccr"'):raw.rindex("}") + 1])["ccr"]["data"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pages", nargs="+")
    p.add_argument("--source", required=True)
    p.add_argument("--blind-dir", required=True)
    p.add_argument("--handbacks-out", required=True)
    a = p.parse_args()
    agent_ids = {}
    for line in open(a.source, encoding="utf-8"):
        r = json.loads(line)
        if r["tool"] == "Agent":
            agent_ids[r["file"][len("prompt_"):-len(".txt")]] = r["tool_use_id"]
    handbacks = {}
    for path in a.pages:
        for ev in load_page(path):
            cat = ev["assistant"]["internal_anthropic_catchall"]
            for c in cat["message"]["content"]:
                if c.get("type") == "tool_use" and c["name"] == "SubagentHandback":
                    handbacks[cat.get("parent_tool_use_id")] = {
                        "event_uuid": ev["assistant"]["uuid"], "created_at": ev["created_at"],
                        "parent_tool_use_id": cat.get("parent_tool_use_id"), "tool_use_id": c["id"],
                        "message": c["input"]["message"]}
    ok = 0
    with open(a.handbacks_out, "w", encoding="utf-8") as fh:
        for b in sorted(agent_ids):
            h = handbacks.get(agent_ids[b])
            if h is None:
                print("%s: no SubagentHandback with parent_tool_use_id %s" % (b, agent_ids[b]))
                continue
            fh.write(json.dumps(dict(h, branch=b), ensure_ascii=False, sort_keys=True) + "\n")
            expected = "\n".join("  " + line for line in h["message"].split("\n")) + "\n"
            got = open("%s/review_%s.md" % (a.blind_dir, b), encoding="utf-8").read()
            same = got == expected
            ok += same
            print("%s: Agent call %s -> SubagentHandback %s at %s; review_%s.md == indented handback message: %s" % (
                b, agent_ids[b], h["event_uuid"], h["created_at"], b, same))
    print("SubagentHandback calls found: %d; matched files: %d of %d" % (len(handbacks), ok, len(agent_ids)))
    sys.exit(0 if ok == len(agent_ids) == 5 else 1)


def run_guarded(main):
    """Round 6, task 2: on an exception, or on an exit that comes before the RESULT line (sys.exit("message"),
    an argparse error), print RESULT: FAIL and exit non-zero. Exit codes 0 and 1 raised by main() pass through."""
    import sys
    import traceback
    try:
        main()
    except SystemExit as e:
        if e.code is None or (type(e.code) is int and e.code in (0, 1)):
            raise
        sys.stdout.flush()
        if type(e.code) is not int:
            print(e.code, file=sys.stderr)
            sys.stderr.flush()
        print("RESULT: FAIL")
        sys.exit(e.code if type(e.code) is int else 1)
    except BaseException:
        sys.stdout.flush()
        traceback.print_exc()
        sys.stderr.flush()
        print("RESULT: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    run_guarded(main)
