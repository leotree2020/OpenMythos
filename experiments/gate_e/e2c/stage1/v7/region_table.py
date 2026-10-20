"""Compact form of the frozen rejection regions R_N of exact_excl.py (same code
path, imported): for each b, the rejected c values; checks they form one run
c >= c_min(b) (up to b + c <= N)."""
import importlib.util, sys
spec = importlib.util.spec_from_file_location("ee", sys.argv[1])
src = open(sys.argv[1]).read().split("for n in (20, 24, 30):")[0]   # definitions only
ns = {}
exec(compile(src, "exact_excl_defs", "exec"), ns)
for n in (20, 24, 30):
    R, _ = ns["region"](n)
    rows, mono = [], True
    for b in range(n + 1):
        cs = sorted(c for (bb, c) in R if bb == b)
        if not cs: continue
        if cs != list(range(cs[0], n - b + 1)): mono = False
        rows.append(f"b={b}: c>={cs[0]}")
    print(f"N={n}: |R|={len(R)} one run per b up to b+c<=N: {mono}; " + ", ".join(rows))
