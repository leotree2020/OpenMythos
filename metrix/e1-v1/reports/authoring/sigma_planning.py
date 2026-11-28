#!/usr/bin/env python3
"""E1-V1 protocol 7.5 / 7.6 planning: expected sigma_N and margin m = 2 * sigma_N of the D1 metrics, from the per-window
NLL of N on the E1-PILOT general DEV windows (metrix/e1-pilot/results/details/N_dev.json: evaluation.general_dev[*].nll,
25 windows per domain; Task Order red line 7: planning use of a Pilot result, file and field named). The V1 sets have
100 windows per domain; sigma of a domain-stratified mean of domain means = sqrt(sum_d SD_d^2 / n_d) / K. Planning
only: the protocol's sigma_N is the bootstrap SD measured on the V1 DEV set in Gate D. Run from the repository root.
"""
import json
import math
import statistics

rows = json.load(open("metrix/e1-pilot/results/details/N_dev.json", encoding="utf-8"))["evaluation"]["general_dev"]
sd = {}
for d in ("books", "c4", "fineweb", "wikitext"):
    x = [r["nll"] for r in rows if r["domain"] == d]
    sd[d] = statistics.stdev(x)
    print("domain %-8s n %d mean NLL %.4f SD %.4f" % (d, len(x), statistics.fmean(x), sd[d]))
for name, doms in (("D1-all", ("books", "c4", "fineweb", "wikitext")), ("D1-diff", ("books", "c4", "wikitext")), ("D1-same", ("fineweb",))):
    s = math.sqrt(sum(sd[d] ** 2 / 100 for d in doms)) / len(doms)
    print("%-8s expected sigma_N %.4f, m = 2 sigma %.4f (100 windows per domain)" % (name, s, 2 * s))
print("D2: sigma of Acc over 800 items <= sqrt(0.25 / 800) = %.4f, m <= %.4f" % (math.sqrt(0.25 / 800), 2 * math.sqrt(0.25 / 800)))
