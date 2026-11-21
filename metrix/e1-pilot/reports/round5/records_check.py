#!/usr/bin/env python3
"""Round 5 (added after the report-commit review): raw output for statements about the review records.

reviews   For each (review file, subagent transcript) pair: the 'message' of the SubagentHandback call in the
          transcript must equal the text below the first '---' line of the review file (that text ends with one
          added '\\n' when the message has none). Prints the sha256 of the message and whether they are equal.
attempt1  For the transcripts of the failed first attempt: counts of tool calls by name, and whether any
          SubagentHandback or file-writing call (Write, Edit, NotebookEdit) is present.

  python records_check.py reviews REVIEW.md=TRANSCRIPT.jsonl ...
  python records_check.py attempt1 TRANSCRIPT.jsonl ...
"""
import collections
import hashlib
import json
import sys


def tool_calls(path):
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("type") != "assistant":
            continue
        for c in r["message"].get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                yield r.get("timestamp"), c


def reviews(pairs):
    ok = 0
    for pair in pairs:
        review, transcript = pair.split("=", 1)
        msgs = [(ts, c["input"]["message"]) for ts, c in tool_calls(transcript) if c["name"] == "SubagentHandback"]
        text = open(review, encoding="utf-8").read()
        body = text.split("\n---\n", 1)[1]
        same = len(msgs) == 1 and body == (msgs[0][1] if msgs[0][1].endswith("\n") else msgs[0][1] + "\n")
        ok += same
        print("%s | handback calls in transcript: %d | at %s | message sha256 %s | body below '---' equal: %s" % (
            review, len(msgs), msgs[0][0] if msgs else None,
            hashlib.sha256(msgs[0][1].encode("utf-8")).hexdigest() if msgs else None, same))
    print("equal: %d of %d" % (ok, len(pairs)))
    return 0 if ok == len(pairs) else 1


def attempt1(paths):
    for path in paths:
        names = collections.Counter(c["name"] for _, c in tool_calls(path))
        bash = [c["input"].get("command", "") for _, c in tool_calls(path) if c["name"] == "Bash"]
        print("%s | tool calls by name: %s | SubagentHandback: %s | Write/Edit/NotebookEdit: %d" % (
            path.rsplit("/", 1)[1], dict(sorted(names.items())), names["SubagentHandback"] > 0,
            names["Write"] + names["Edit"] + names["NotebookEdit"]))
        for cmd in bash:
            print("  Bash: %s" % cmd.replace("\n", " ")[:200])
    return 0


def main():
    mode, args = sys.argv[1], sys.argv[2:]
    sys.exit(reviews(args) if mode == "reviews" else attempt1(args))


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
