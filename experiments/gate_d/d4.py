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
Revision 6 (PREREGISTRATION 13.4): reachability of each interface from
single-sample clean ACT masks; conditional effects on reachable complete
families (coverage and subset-I0 reported); hard checks: every unreachable
pair within 10 eps (TV), every record before the patch point bitwise equal to
the clean run; the share of pairs whose ACT trajectory changed after the
patch is reported.
"""

import numpy as np
import torch

from act_masks import act_masks, complete, reachability, suffix_any
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
    noise = {m: [] for m in METRICS}
    controls = {key: {"identity_bitwise": True, "full_state_max_diff": 0.0,
                      "pre_intervention_bitwise": True} for key in per}
    act_changed = {key: [] for key in per}
    # revision 6: reachability of every interface from single-sample clean ACT masks
    masks = act_masks(runner, x)
    R = reachability(masks)
    reach = {f"{k}:{p}@{pos}": interface_reach(arm, p, pos, R) for k, p, pos in ifs}
    for c0 in range(0, N, 4 * chunk_bodies):
        sl = slice(c0, c0 + 4 * chunk_bodies)
        xc, xs = x[sl], x[src_idx[sl]]
        Lc, rc, _ = runner.run(xc, record=True)
        Ls, rs, _ = runner.run(xs, record=True)
        Lc, Ls = Lc[:, READ_POS].double(), Ls[:, READ_POS].double()
        order = list(rc)
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
            Lp, rp, _ = runner.run(xc, patch={point: (pos, rs[point])}, record=True)
            Lp = Lp[:, READ_POS].double()
            # every record computed before the patch point equals the clean run
            for k in order[: order.index(point)]:
                if not torch.equal(rp[k], rc[k]):
                    controls[key]["pre_intervention_bitwise"] = False
            if arm == "openmythos":  # post-intervention ACT trajectory may change (reported)
                ch = torch.zeros(len(xc), dtype=torch.bool)
                for t in range(4):
                    ch |= (rp[f"still{t}"] != rc[f"still{t}"]).any(1)
                ch |= (rp["halted_final"] != rc["halted_final"]).any(1)
                act_changed[key].append(ch)
            else:
                act_changed[key].append(torch.zeros(len(xc), dtype=torch.bool))
            for m, v in metrics(Lp, Lc, y[sl], yt[sl]).items():
                per[key][m].append(v)
    bad = [k for k, c in controls.items()
           if not c["identity_bitwise"] or c["full_state_max_diff"] > TOL_FULL or not c["pre_intervention_bitwise"]]
    if bad:
        raise IntegrityError(f"D4 integrity control failed for {bad}: {[controls[k] for k in bad]}")
    groups = bid.numpy()
    eps = {m: float(torch.cat(v).abs().max()) for m, v in noise.items()}
    vals_all = {key: {m: torch.cat(v) for m, v in d.items()} for key, d in per.items()}
    # unreachable pairs: every pair must stay within the numerical noise (hard)
    unreach = {}
    for key in per:
        u = ~reach[key]
        tv = vals_all[key]["tv"][u]
        unreach[key] = {"n_pairs": int(u.sum()),
                        "max_tv": float(tv.max()) if len(tv) else 0.0,
                        "mean_tv": float(tv.mean()) if len(tv) else 0.0,
                        "max_abs_d_logit_diff": float(vals_all[key]["d_logit_diff"][u].abs().max()) if len(tv) else 0.0}
        if len(tv) and unreach[key]["max_tv"] > 10 * eps["tv"]:
            raise IntegrityError(f"D4 unreachable pairs changed the output at {key}: {unreach[key]}, eps_tv {eps['tv']}")
    out = {"noise_eps": eps, "controls": controls, "unreachable_pairs": unreach, "interfaces": {},
           "semantics": "single-sample ACT masks; conditional effects on reachable complete families"}
    i0 = "I0:emb@17"
    i0_all = {m: summary(vals_all[i0][m].numpy(), groups) for m in METRICS}
    out["I0_all_questions"] = i0_all
    for key in per:
        inc = complete(reach[key])
        n_reach, n_inc = int(reach[key].sum()), int(inc.sum())
        cov = {"n_reachable_questions": n_reach, "n_included_questions": n_inc,
               "n_included_bodies": n_inc // 4,
               "n_reachable_not_evaluated": int((reach[key] & ~inc).sum())}
        if n_inc < 0.5 * N:
            cov["n_reachable_not_evaluated"] = n_reach
            out["interfaces"][key] = {"skipped": "fewer than half of the bodies are reachable complete families",
                                      "coverage": cov}
            continue
        g = groups[inc.numpy()]
        r = {m: summary(vals_all[key][m][inc].numpy(), g) for m in METRICS}
        r["coverage"] = cov
        r["indistinguishable"] = {m: abs(r[m]["mean"]) <= 10 * eps[m] for m in METRICS}
        r["negligible_tv_lt_0.02"] = r["tv"]["mean"] < 0.02
        r["I0_same_subset"] = {m: summary(vals_all[i0][m][inc].numpy(), g) for m in METRICS}
        r["I0_same_subset_negligible"] = (r["I0_same_subset"]["tv"]["mean"] < 0.02
                                          or abs(r["I0_same_subset"]["tv"]["mean"]) <= 10 * eps["tv"])
        r["share_pairs_act_trajectory_changed"] = float(torch.cat(act_changed[key])[inc].double().mean())
        r["included_question_index"] = torch.nonzero(inc).squeeze(1).tolist()
        sub = r["I0_same_subset"]
        if sub["tv"]["ci95"][0] > 0 and sub["tv"]["mean"] >= 0.02:
            r["relative_d_logit_diff"] = relative_effect(
                r["d_logit_diff"]["mean"], sub["d_logit_diff"]["mean"], eps["d_logit_diff"])
        out["interfaces"][key] = r
    return out


def interface_reach(arm, point, pos, R):
    """(4N,) clean questions for which the patched state has a path to the
    readout (PREREGISTRATION 13.4); always True outside the ACT loop."""
    N = R.shape[0]
    if arm == "openmythos" and point.startswith("blk_in"):
        return suffix_any(R[:, int(point[6:])])[:, pos]
    if arm == "openmythos" and point.startswith("h") and point[1:].isdigit():
        return R[:, int(point[1:]) - 1, pos]
    return torch.ones(N, dtype=torch.bool)


def relative_effect(num, den, eps):
    """num / den, reported only when the total effect's mean logit difference
    lies above the numerical noise floor (|den| > 10 eps, the 10.3 rule) and
    is non-zero; otherwise the ratio cannot be estimated stably."""
    if den == 0 or abs(den) <= 10 * eps:
        return "无法稳定估计"
    return num / den
