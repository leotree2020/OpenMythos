"""
D4: activation patching (PREREGISTRATION 8.6, 9.3, 10.3).

Pairs: every diag_eval question q (clean run) with q' = the next statement
slot of the same body (source run); the two inputs differ only at position 17.
    I0  emb, position 17                        total effect (= the q' run)
    I1  block inputs, position 17               transformer in{k}; openmythos e,
                                                blk_in{t}, h{t+1}, h_out (= coda input)
    I2  block outputs, position 18              transformer out{k}; openmythos e,
                                                h{t+1}, h_out, coda_out
    I3  (openmythos) h{t+1} and h_out at 18     same runs as the matching I2 rows
Integrity controls for every interface (hard; a failure raises):
    identity    patch with the clean run's own values -> logits bitwise unchanged
    full state  replace every state needed to continue -> logits equal the q'
                run within 1e-6 (openmythos loop interfaces also replace e and
                the ACT carry: cum, halted, accumulated h_out)
Metrics vs the clean run: logit and probability of y' (q' answer) and y,
change of logit(y') - logit(y), TV, KL(clean || patched). Body-grouped CIs.
Noise floor eps: the same metrics between two clean runs that differ only in
batch composition (chunk vs 4 questions per batch); |mean| <= 10 eps is
reported as numerically indistinguishable. Partial patches (I1-I3) are local
path effects, exploratory, not the total query effect.
"""

import numpy as np
import torch

from common import Q_POS, READ_POS, summary

TOL_FULL = 1e-6
METRICS = ("d_logit_target", "d_logit_orig", "d_logit_diff", "d_p_target", "d_p_orig", "tv", "kl")


class IntegrityError(RuntimeError):
    pass


def interfaces(arm, n_loops=4):
    if arm == "transformer":
        I1 = [("I1", f"in{k}", Q_POS) for k in range(3)]
        I2 = [("I2", f"out{k}", READ_POS) for k in range(3)]
        return [("I0", "emb", Q_POS)] + I1 + I2
    I1 = [("I1", "e", Q_POS)] + [("I1", f"blk_in{t}", Q_POS) for t in range(n_loops)] \
        + [("I1", f"h{t + 1}", Q_POS) for t in range(n_loops)] + [("I1", "h_out", Q_POS)]
    I2 = [("I2", "e", READ_POS)] + [("I2/I3", f"h{t + 1}", READ_POS) for t in range(n_loops)] \
        + [("I2/I3", "h_out", READ_POS), ("I2", "coda_out", READ_POS)]
    return [("I0", "emb", Q_POS)] + I1 + I2


def full_state_patch(arm, point, src):
    if arm == "openmythos" and point.startswith("blk_in"):
        t = int(point[6:])
        carry = {k: src[k] for k in (f"h_before{t}", "e", f"cum_before{t}", f"halted_before{t}", f"hout_before{t}")}
        return {f"carry{t}": (None, carry), point: (None, src[point])}
    if arm == "openmythos" and point.startswith("h") and point[1:].isdigit():
        t = int(point[1:]) - 1
        carry = {k: src[k] for k in ("e", f"cum_before{t}", f"halted_before{t}", f"hout_before{t}")}
        return {f"carry_post{t}": (None, carry), point: (None, src[point])}
    return {point: (None, src[point])}


def metrics(Lp, Lc, y, yt):
    """Per-question metrics of patched logits Lp vs clean Lc (readout, double)."""
    Pp, Pc = torch.softmax(Lp, -1), torch.softmax(Lc, -1)
    g = lambda L, idx: L.gather(1, idx.view(-1, 1)).squeeze(1)  # noqa: E731
    return {
        "d_logit_target": g(Lp, yt) - g(Lc, yt),
        "d_logit_orig": g(Lp, y) - g(Lc, y),
        "d_logit_diff": (g(Lp, yt) - g(Lp, y)) - (g(Lc, yt) - g(Lc, y)),
        "d_p_target": g(Pp, yt) - g(Pc, yt),
        "d_p_orig": g(Pp, y) - g(Pc, y),
        "tv": 0.5 * (Pp - Pc).abs().sum(-1),
        "kl": (Pc * (torch.log_softmax(Lc, -1) - torch.log_softmax(Lp, -1))).sum(-1),
    }


def run_d4(runner, fam, chunk_bodies=125):
    x, y, slot, bid, roots = fam
    N = len(x)
    src_idx = torch.arange(N) - slot + (slot + 1) % 4  # same body, next slot
    yt = y[src_idx]
    arm = runner.arm
    ifs = interfaces(arm)
    per = {f"{k}:{p}@{pos}": {m: [] for m in METRICS} for k, p, pos in ifs}
    valid_mask = {key: [] for key in per}
    noise = {m: [] for m in METRICS}
    controls = {key: {"identity_bitwise": True, "full_state_max_diff": 0.0} for key in per}
    for c0 in range(0, N, 4 * chunk_bodies):
        sl = slice(c0, c0 + 4 * chunk_bodies)
        xc, xs = x[sl], x[src_idx[sl]]
        Lc, rc, _ = runner.run(xc, record=True)
        Ls, rs, _ = runner.run(xs, record=True)
        Lc, Ls = Lc[:, READ_POS].double(), Ls[:, READ_POS].double()
        # noise floor: clean run recomputed with 4 questions per batch
        Lb = torch.cat([runner.run(xc[i : i + 4])[0][:, READ_POS] for i in range(0, len(xc), 4)]).double()
        for m, v in metrics(Lb, Lc, y[sl], yt[sl]).items():
            noise[m].append(v)
        for kind, point, pos in ifs:
            key = f"{kind}:{point}@{pos}"
            Li = runner.run(xc, patch={point: (pos, rc[point])})[0][:, READ_POS].double()
            if not torch.equal(Li, Lc):
                controls[key]["identity_bitwise"] = False
            Lf = runner.run(xc, patch=full_state_patch(arm, point, rs))[0][:, READ_POS].double()
            controls[key]["full_state_max_diff"] = max(
                controls[key]["full_state_max_diff"], (Lf - Ls).abs().max().item())
            Lp = runner.run(xc, patch={point: (pos, rs[point])})[0][:, READ_POS].double()
            for m, v in metrics(Lp, Lc, y[sl], yt[sl]).items():
                per[key][m].append(v)
            if point.startswith(("blk_in", "h")) and point[-1].isdigit() and arm == "openmythos":
                t = int(point[6:]) if point.startswith("blk_in") else int(point[1:]) - 1
                valid_mask[key].append(rc[f"valid{t}"])
            else:
                valid_mask[key].append(torch.ones(len(xc), dtype=torch.bool))
    bad = [k for k, c in controls.items()
           if not c["identity_bitwise"] or c["full_state_max_diff"] > TOL_FULL]
    if bad:
        raise IntegrityError(f"D4 integrity control failed for {bad}: {[controls[k] for k in bad]}")
    groups = bid.numpy()
    eps = {m: float(torch.cat(v).abs().max()) for m, v in noise.items()}
    out = {"noise_eps": eps, "controls": controls, "interfaces": {}}
    total = None
    for key in per:
        vm = torch.cat(valid_mask[key])
        n_valid = int(vm.sum())
        if n_valid < 0.5 * N:
            out["interfaces"][key] = {"skipped": "loop not executed for most questions", "n_valid": n_valid}
            continue
        vals = {m: torch.cat(v)[vm].numpy() for m, v in per[key].items()}
        g = groups[vm.numpy()]
        r = {m: summary(v, g) for m, v in vals.items()}
        r["n_valid"] = n_valid
        r["indistinguishable"] = {m: abs(r[m]["mean"]) <= 10 * eps[m] for m in METRICS}
        r["negligible_tv_lt_0.02"] = r["tv"]["mean"] < 0.02
        out["interfaces"][key] = r
        if key.startswith("I0"):
            total = r
    total_ok = total["tv"]["ci95"][0] > 0 and total["tv"]["mean"] >= 0.02
    out["relative_effect_reported"] = total_ok
    if total_ok:
        for key, r in out["interfaces"].items():
            if "skipped" not in r:
                r["relative_d_logit_diff"] = relative_effect(
                    r["d_logit_diff"]["mean"], total["d_logit_diff"]["mean"], eps["d_logit_diff"])
    return out


def relative_effect(num, den, eps):
    """num / den, reported only when the total effect's mean logit difference
    lies above the numerical noise floor (|den| > 10 eps, the 10.3 rule) and
    is non-zero; otherwise the ratio cannot be estimated stably."""
    if den == 0 or abs(den) <= 10 * eps:
        return "无法稳定估计"
    return num / den
