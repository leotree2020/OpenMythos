"""Check that each subagent received the invocation text (first user message) and the resume message (delivered by
the harness with the prefix 'The coordinator sent a message while you were working:\\n' and the suffix
'\\n\\n\\nAddress this before completing your current task.') unchanged."""
import json
import sys

R = sys.argv[1]
PREFIX = "The coordinator sent a message while you were working:\n"
SUFFIX = "\n\n\nAddress this before completing your current task."
for name in ("code-reviewer", "data-auditor"):
    texts = []
    for line in open("%s/%s_round1_transcript.jsonl" % (R, name), encoding="utf-8"):
        r = json.loads(line)
        if r.get("type") != "user":
            continue
        c = r["message"].get("content")
        if isinstance(c, str):
            texts.append(c)
        elif isinstance(c, list):
            texts += [x["text"] for x in c if isinstance(x, dict) and x.get("type") == "text"]
    prompt = open("%s/%s_prompt.txt" % (R, name), encoding="utf-8").read()
    resume = open("%s/resume_message_%s.txt" % (R, name), encoding="utf-8").read()
    resumed = [t for t in texts if t.startswith(PREFIX)]
    print("%s: user text messages %d | first == %s_prompt.txt (strip): %s | resume messages %d, body == "
          "resume_message_%s.txt (strip): %s" % (name, len(texts), name, texts[0].strip() == prompt.strip(), len(resumed),
                                                 name, [t[len(PREFIX):].endswith(SUFFIX) and t[len(PREFIX):-len(SUFFIX)].strip() == resume.strip() for t in resumed]))
