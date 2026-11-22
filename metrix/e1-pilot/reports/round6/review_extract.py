#!/usr/bin/env python3
"""Round 6, task 5: write a subagent's final report, unchanged, into reviews/<commit>/<name>.md.

The final report is the 'message' of the subagent's SubagentHandback tool call if its transcript has one;
otherwise the text blocks of its last assistant message, joined by "\\n". The output file is the header lines
given with --header (each prefixed with "# "), a line "---", then the report (one "\\n" added if it does not end
with one). Prints which source was used, its timestamp, the number of such calls, and the sha256 of the report.

  python review_extract.py TRANSCRIPT.jsonl OUT.md --header LINE [--header LINE ...]
"""
import argparse
import hashlib
import json


def final_report(path):
    handbacks, last_text = [], None
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("type") != "assistant":
            continue
        content = r["message"].get("content") or []
        texts = [c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text"]
        if texts:
            last_text = (r.get("timestamp"), "\n".join(texts))
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "SubagentHandback":
                handbacks.append((r.get("timestamp"), c["input"]["message"]))
    if handbacks:
        return "SubagentHandback", len(handbacks), handbacks[-1]
    return "last assistant text", 0, last_text


def main():
    p = argparse.ArgumentParser()
    p.add_argument("transcript")
    p.add_argument("out")
    p.add_argument("--header", action="append", default=[])
    a = p.parse_args()
    source, n_handbacks, (ts, text) = final_report(a.transcript)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("".join("# %s\n" % h for h in a.header) + "---\n" + text + ("" if text.endswith("\n") else "\n"))
    print("%s | source: %s (SubagentHandback calls: %d) | at %s | report sha256 %s | chars %d" % (
        a.out, source, n_handbacks, ts, hashlib.sha256(text.encode("utf-8")).hexdigest(), len(text)))


if __name__ == "__main__":
    main()
