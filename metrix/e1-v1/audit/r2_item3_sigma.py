# data-auditor, E1-V1 round 2, item 3: independent recomputation of reports/authoring/sigma_planning.txt
# (the planning estimate behind the G-D2 bounds of protocol 7.5) from
# metrix/e1-pilot/results/details/N_dev.json: evaluation.general_dev (Pilot N on the Pilot D1 DEV windows).
# Analytic estimate plus a stratified bootstrap written from DAMAGE_MANIFEST statistics.d1_resampling.
# Reads a Pilot DEV result file only. No Executor code is imported, called or copied.
import math
import re
import statistics
import sys

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402

DOMS = ["books", "c4", "fineweb", "wikitext"]
GROUPS = {"D1-all": DOMS, "D1-diff": ["books", "c4", "wikitext"], "D1-same": ["fineweb"]}


def chk(label, got, exp):
    ok = got == exp
    print(f"{'OK  ' if ok else 'DIFF'} {label}: got {got} | expected {exp}")
    return ok


def boot_sd(per_dom, doms, k, seed, purpose, B=10000):
    """DAMAGE_MANIFEST statistics: within domains in the order books, c4, fineweb, wikitext (only the metric's
    domains), r.choices(windows, k=n_domain); statistic = mean of the domain means; sigma_N = sample SD (B - 1)."""
    r = A.rng_rule(seed, purpose)
    vals = []
    for _ in range(B):
        ms = []
        for d in doms:
            xs = r.choices(per_dom[d], k=k)
            ms.append(sum(xs) / k)
        vals.append(sum(ms) / len(ms))
    return statistics.stdev(vals)


def main():
    ok = True
    path = A.PILOT + "/results/details/N_dev.json"
    print("input", path, "sha256", A.file_sha256(path))
    d = A.load_json(path)
    print("fields: kind", d.get("kind"), "| label", d.get("label"), "| mode", d.get("mode"), "| model", d.get("model"), "| split", d.get("split"))
    ok &= chk("split of the file", str(d.get("split")).upper(), "DEV")
    gd = d["evaluation"]["general_dev"]
    per = {x: [] for x in DOMS}
    ids = {x: [] for x in DOMS}
    for w in gd:
        per[w["domain"]].append(w["nll"])
        ids[w["domain"]].append(w["doc_id"])
    ok &= chk("windows per domain", {x: len(per[x]) for x in DOMS}, {x: 25 for x in DOMS})
    ok &= chk("doc_ids are <domain>-dev-000..024 (the first 25 DEV rows, contained in V1 D1 DEV)", all(ids[x] == [f"{x}-dev-{i:03d}" for i in range(25)] for x in DOMS), True)
    ok &= chk("all NLL finite", all(math.isfinite(v) for x in DOMS for v in per[x]), True)
    sd1 = {x: statistics.stdev(per[x]) for x in DOMS}
    sd0 = {x: statistics.pstdev(per[x]) for x in DOMS}
    for x in DOMS:
        print(f"domain {x:8s} n {len(per[x])} mean NLL {statistics.fmean(per[x]):.4f} SD(n-1) {sd1[x]:.4f} SD(n) {sd0[x]:.4f}")
    exp_txt = open(A.V1 + "/reports/authoring/sigma_planning.txt", encoding="utf-8").read()
    ex = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r"domain (\w+)\s+n 25 mean NLL ([0-9.]+) SD ([0-9.]+)", exp_txt)}
    ok &= chk("Executor per-domain mean / SD (4 d.p.) = auditor mean / SD(n-1)", ex, {x: (round(statistics.fmean(per[x]), 4), round(sd1[x], 4)) for x in DOMS})
    exs = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r"(D1-\w+)\s+expected sigma_N ([0-9.]+), m = 2 sigma ([0-9.]+)", exp_txt)}
    n = 100
    res = {}
    for name, g in GROUPS.items():
        for lab, sd in (("SD(n-1)", sd1), ("SD(n)", sd0)):
            s = math.sqrt(sum(sd[x] ** 2 / n for x in g)) / len(g)
            res[(name, lab)] = s
            print(f"{name:8s} analytic, {lab}, 100 windows per domain: sigma_N {s:.4f}  m = 2 sigma {2 * s:.4f}")
    ok &= chk("Executor sigma_N / m (4 d.p.) = auditor analytic with SD(n-1)", exs, {k: (round(res[(k, 'SD(n-1)')], 4), round(2 * res[(k, 'SD(n-1)')], 4)) for k in GROUPS})
    proto = open(A.V1 + "/METRIX_E1V1_PROTOCOL.md", encoding="utf-8").read()
    pm = re.search(r"`m\(D1-all\)` 约 ([0-9.]+)、`m\(D1-diff\)` 约 ([0-9.]+)、`m\(D1-same\)` 约 ([0-9.]+)", proto)
    ok &= chk("protocol 7.5 planning m (D1-all, D1-diff, D1-same) = auditor 2 sigma rounded to 3 d.p.", tuple(float(x) for x in pm.groups()),
              tuple(round(2 * res[(k, "SD(n-1)")], 3) for k in GROUPS))
    ok &= chk("planning m within the G-D2 bounds (0.10, 0.10, 0.20)", tuple(2 * res[(k, "SD(n-1)")] <= b for k, b in zip(GROUPS, (0.10, 0.10, 0.20))), (True, True, True))
    print(f"ratio sigma(D1-same) / sigma(D1-all) = {res[('D1-same', 'SD(n-1)')] / res[('D1-all', 'SD(n-1)')]:.3f} (protocol 7.5: 'about 2 times')")
    # D2
    s2 = math.sqrt(0.25 / 800)
    mD2 = re.search(r"D2: sigma of Acc over 800 items <= sqrt\(0.25 / 800\) = ([0-9.]+), m <= ([0-9.]+)", exp_txt)
    ok &= chk("Executor D2 line (sigma bound, m bound) = auditor", (float(mD2.group(1)), float(mD2.group(2))), (round(s2, 4), round(2 * s2, 4)))
    print(f"G-D3 D2 threshold 0.05 / sigma bound {s2:.4f} = {0.05 / s2:.2f} (protocol 7.5: 'about 3 times')")
    # stratified bootstrap per DAMAGE_MANIFEST (BOOTSTRAP_SEED, purpose 'N:DEV:<metric>:level' of DATA_MANIFEST seeds.purposes)
    seed = A.load_json(A.V1 + "/DATA_MANIFEST.json")["seeds"]["BOOTSTRAP_SEED"]
    for name, g in GROUPS.items():
        s25 = boot_sd(per, g, 25, seed, f"N:DEV:{name}:level")
        tiled = {x: per[x] * 4 for x in DOMS}  # 100 windows per domain with the Pilot NLL distribution
        s100 = boot_sd(tiled, g, 100, seed, f"N:DEV:{name}:level")
        print(f"{name:8s} bootstrap (10,000): 25 windows/domain sigma {s25:.4f} -> x 1/2 for 100/domain {s25 / 2:.4f}; 100 windows/domain (Pilot windows x 4) sigma {s100:.4f}  m {2 * s100:.4f}")
    print("ITEM3 round 2:", "ALL MATCH" if ok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
