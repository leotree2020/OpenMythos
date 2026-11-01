"""Passive stdlib observer. Never sends signals or opens model artifacts."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import sys
import time


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    try:
        return Path(path).read_text()
    except (OSError, UnicodeError) as exc:
        return {"unavailable": type(exc).__name__, "message": str(exc)}


def process(pid):
    root = Path('/proc') / str(pid)
    status = read(root / 'status')
    if not isinstance(status, str):
        return {"pid": pid, "status": status}
    chosen = ('Name', 'State', 'PPid', 'Uid', 'VmRSS', 'VmHWM', 'Threads', 'SigBlk', 'TracerPid')
    row = {"pid": pid, "status": {k: v.strip() for k, v in
           (line.split(':', 1) for line in status.splitlines()) if k in chosen}}
    row['stat'] = read(root / 'stat')
    row['cgroup'] = read(root / 'cgroup')
    try:
        row['exe'] = str((root / 'exe').resolve(strict=True))
    except OSError as exc:
        row['exe'] = {"unavailable": type(exc).__name__}
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--operator-dir', required=True)
    parser.add_argument('--launcher-pid', type=int, required=True)
    args = parser.parse_args()
    root = Path(args.operator_dir)
    known = {}
    started = time.monotonic()
    deadline = started + 6010
    signal_offset = 0
    complete_seen = None
    count = 0
    with (root / 'resource_samples.jsonl').open('x', encoding='utf-8') as output:
        while time.monotonic() < deadline:
            snapshot = {"utc": utc(), "monotonic": time.monotonic(), "observer_pid": os.getpid()}
            observation = root / 'launch_observation.json'
            try:
                launch = json.loads(observation.read_text())
                if int(launch['pid']) != args.launcher_pid:
                    raise ValueError('launcher PID differs from dispatch record')
                known.setdefault(int(launch['pid']), str(launch['pid_starttime']))
            except (OSError, ValueError, KeyError) as exc:
                snapshot['launch_record_pending'] = type(exc).__name__
            # Only PID/PPID/name metadata are scanned, never argv or environments.
            parents = {}
            for entry in Path('/proc').iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    stat = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                    parents[int(entry.name)] = (int(stat[1]), stat[19])
                except (OSError, ValueError, IndexError):
                    continue
            for _ in range(5):
                for pid, (ppid, starttime) in parents.items():
                    if ppid in known and parents.get(ppid, (None, None))[1] == known[ppid]:
                        known.setdefault(pid, starttime)
            snapshot['identity_mismatches'] = [{"pid": pid, "expected_starttime": start,
                "observed_starttime": parents[pid][1]} for pid, start in known.items()
                if pid in parents and parents[pid][1] != start]
            snapshot['owned_processes'] = []
            for pid in sorted(known):
                if pid not in parents:
                    snapshot['owned_processes'].append({'pid': pid, 'observation': 'absent at scan', 'expected_starttime': known[pid]})
                    continue
                if parents[pid][1] != known[pid]:
                    continue
                row = process(pid)
                raw_stat = row.get('stat')
                if isinstance(raw_stat, str) and raw_stat.rsplit(')', 1)[1].split()[19] != known[pid]:
                    snapshot['identity_mismatches'].append({'pid': pid, 'reason': 'identity changed after scan'})
                    continue
                snapshot['owned_processes'].append(row)
            meminfo = read('/proc/meminfo')
            snapshot['meminfo'] = ([x for x in meminfo.splitlines()
                                    if x.startswith(('MemTotal:', 'MemAvailable:', 'SwapTotal:', 'SwapFree:'))]
                                   if isinstance(meminfo, str) else meminfo)
            snapshot['memory_pressure'] = read('/proc/pressure/memory')
            cgroups = {Path('/sys/fs/cgroup')}
            for row in snapshot['owned_processes']:
                cg = row.get('cgroup')
                if isinstance(cg, str):
                    for line in cg.splitlines():
                        if line.startswith('0::'):
                            candidate = (Path('/sys/fs/cgroup') / line[3:].lstrip('/')).resolve()
                            if candidate.is_relative_to('/sys/fs/cgroup'):
                                while candidate.is_relative_to('/sys/fs/cgroup'):
                                    cgroups.add(candidate)
                                    if candidate == Path('/sys/fs/cgroup'):
                                        break
                                    candidate = candidate.parent
            snapshot['cgroup_memory'] = {str(path): {name: read(path / name) for name in
                ('memory.current', 'memory.peak', 'memory.max', 'memory.events', 'memory.events.local')}
                for path in sorted(cgroups)}
            trace = root / 'signals.log'
            try:
                with trace.open() as src:
                    src.seek(signal_offset)
                    fresh = src.read()
                    signal_offset = src.tell()
                if fresh:
                    snapshot['trace_new'] = fresh
                    snapshot['signal_senders'] = [process(int(pid)) for pid in sorted(set(re.findall(r'si_pid=(\d+)', fresh)))]
                    snapshot['sender_metadata_limit'] = 'Post-observation metadata only; PID reuse and sender exit can prevent historical identity attribution. Original siginfo is authoritative.'
            except OSError as exc:
                snapshot['trace_pending'] = type(exc).__name__
            output.write(json.dumps(snapshot, sort_keys=True) + '\n')
            output.flush()
            count += 1
            if (root / 'completion.json').exists():
                if complete_seen is None:
                    complete_seen = time.monotonic()
                elif time.monotonic() - complete_seen >= 2:
                    break
            time.sleep(1 if time.monotonic() - started < 120 else 5)
    result = {"utc": utc(), "samples": count, "elapsed_seconds": time.monotonic()-started,
              "reason": "launcher_completed" if complete_seen is not None else "observer_deadline",
              "model_artifacts_opened": False, "signals_sent": 0,
              "numerical_imports": [x for x in ('torch', 'numpy', 'parcae_lm') if x in sys.modules]}
    with (root / 'observer_completion.json').open('x') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
