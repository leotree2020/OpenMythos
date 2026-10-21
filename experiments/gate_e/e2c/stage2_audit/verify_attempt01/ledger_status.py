"""Read-only: cumulative stage-2 ledger use (union of intervals to their end or last heartbeat, plus supplements)."""
import json, os, sys, time
p = sys.argv[1]
if not os.path.exists(p):
    print("ledger: not yet")
    raise SystemExit
d = json.load(open(p))
spans = sorted((i["start"], i["end"] or i["heartbeat"]) for i in d["intervals"])
t, c = 0.0, None
for a, b in spans:
    if c is None or a > c[1]:
        t += (c[1] - c[0]) if c else 0
        c = [a, b]
    else:
        c[1] = max(c[1], b)
t += (c[1] - c[0]) if c else 0
t += sum(x["seconds"] for x in d.get("supplements", []))
for i in d["intervals"]:
    print(f"interval {i['id']} {i['label']} pid {i['pid']} status {i['status']} end {i['end']} "
          f"heartbeat {time.time() - i['heartbeat']:.1f} s ago")
print(f"ledgered {t:.1f} s of {d['cap_seconds']:.0f} s (to the last heartbeat); since process start "
      f"{time.time() - d['intervals'][-1]['start']:.1f} s; used_seconds field {d.get('used_seconds')}")
