"""Is the resume message (a file) delivered to a subagent verbatim? The harness delivers a message sent to a running
or resumed subagent as one user message: the fixed line PREFIX and a newline, the text sent, then three newlines and
the fixed line SUFFIX. Both are removed (only if present exactly) before the comparison; what was removed is printed."""
import json, sys
PREFIX = "The coordinator sent a message while you were working:\n"
SUFFIX = "\n\n\nAddress this before completing your current task."
transcript, want_path = sys.argv[1], sys.argv[2]
want = open(want_path, encoding="utf-8").read().strip()
for line in open(transcript, encoding="utf-8"):
    r = json.loads(line)
    c = r.get("message", {}).get("content") if r.get("type") == "user" else None
    if isinstance(c, str) and c.startswith(PREFIX):
        body = c[len(PREFIX):]
        has_suffix = body.endswith(SUFFIX)
        if has_suffix:
            body = body[:-len(SUFFIX)]
        print(want_path, ": harness prefix removed: %r | harness suffix removed: %r | rest == this text (stripped): %s"
              % (PREFIX, SUFFIX if has_suffix else None, body.strip() == want))
