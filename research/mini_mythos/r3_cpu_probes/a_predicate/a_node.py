#!/usr/bin/env python3
"""F3B-D1-A-CPU-001 -- test-bench process node.

A node is a tiny, scripted process used only by the isolated R3-A CPU experiment.  The lab (a_lab.py) describes a
process topology as a JSON spec; every node forks its scripted children, reports its own identity (pid, ppid, sid,
pgrp, starttime) to the lab through a pipe -- this self-report is the test bench's KNOWN topology, independent of the
arms under test -- and then obeys control files in a private directory so the lab can drive exact orderings.

spec keys:  name, setsid(bool), term ("default"|"ignore"|"exit:<code>"|"delay_exit:<seconds>:<code>"),
            exit_code (default 0), children(list of specs)
control files (in ctl dir):  go.<name>.exit  (content = exit code, node exits with os._exit, leaving children orphaned)
                             go.<name>.reap  (node reaps all of its own already-exited children)
Linux only, standard library only, no network, no GPU.
"""
import json
import os
import signal
import sys
import time


def self_stat():
    with open("/proc/self/stat", "rb") as f:
        data = f.read().decode("ascii", "replace")
    rest = data[data.rindex(")") + 2:].split()
    return {"ppid": int(rest[1]), "pgrp": int(rest[2]), "sid": int(rest[3]), "starttime": int(rest[19])}


def main():
    token, specjson, fd, ctl = sys.argv[1:5]
    spec = json.loads(specjson)
    fd = int(fd)
    name = spec["name"]
    if spec.get("setsid"):
        os.setsid()
    term = spec.get("term", "default")
    state = {"deadline": None}
    if term == "ignore":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    elif term.startswith("exit:"):
        code = int(term.split(":")[1])
        signal.signal(signal.SIGTERM, lambda s, f: os._exit(code))
    elif term.startswith("delay_exit:"):
        _, delay, code = term.split(":")
        delay, code = float(delay), int(code)

        def on_term(s, f):
            if state["deadline"] is None:
                state["deadline"] = (time.monotonic() + delay, code)
        signal.signal(signal.SIGTERM, on_term)
    kids = []
    for c in spec.get("children", []):
        pid = os.fork()
        if pid == 0:
            os.execv(sys.executable, [sys.executable, "-S", os.path.abspath(__file__), token, json.dumps(c), str(fd), ctl])
            os._exit(127)
        kids.append(pid)
    me = self_stat()
    me.update(name=name, pid=os.getpid())
    os.write(fd, (json.dumps(me) + "\n").encode())
    exit_file = os.path.join(ctl, "go.%s.exit" % name)
    reap_file = os.path.join(ctl, "go.%s.reap" % name)
    while True:
        time.sleep(0.002)
        if state["deadline"] and time.monotonic() >= state["deadline"][0]:
            os._exit(state["deadline"][1])
        if os.path.exists(exit_file):
            try:
                with open(exit_file) as f:
                    code = int(f.read().strip() or spec.get("exit_code", 0))
            except ValueError:
                code = int(spec.get("exit_code", 0))
            os._exit(code)
        if os.path.exists(reap_file):
            for k in kids:
                try:
                    os.waitpid(k, os.WNOHANG)
                except ChildProcessError:
                    pass
            os.unlink(reap_file)


if __name__ == "__main__":
    main()
