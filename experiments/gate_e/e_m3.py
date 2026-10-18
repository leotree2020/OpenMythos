"""
M3: minimal-pair letter sensitivity, a local input perturbation experiment
(PREREGISTRATION 9.3, 10.1). Pairs come from the minpair set derived from
diag_eval (paired with it, not an independent set). For pair i (body b,
statement j, replacement letter) the original x is body b with its slot-0
query, x' the consistently renamed prompt. Measured at the '=' (4j+1) and
digit (4j+2) positions of statement j at every record point:

    composition A  all originals of diag_eval in one batch
    single         every prompt run alone (batch size 1); also gives the
                   single-sample ACT validity used at loop record points
    delta_i = |h_A(x_b) - h_single(x'_i)| / sigma_p
    eps_b   = |h_A(x_b) - h_single(x_b)| / sigma_p        (numerical noise)
    tau_p   = 10 * max_b eps_b
    sigma_p = sqrt(sum of per-dimension sample variances of h_A(x_b)[p] over
              the bodies valid at that record point)

sigma_p = 0 (10.1): no division; "标准化敏感度不可计算（σ = 0）" with the raw
differences reported; never "not detected" or "deleted"; excluded from t_M3
and from the controls. Labels per record point and position type (pairs of
every statement pooled, each against its own position's tau):
    "在预设最小对和数值精度下，未检测到字母敏感性"  no pair with delta_i > tau
    "发现字母敏感性"                                at least one; always with
                                                   the share s and its CI
Controls (hard; a failure raises IntegrityError):
    negative  query swap only: positions before the query, every body,
              delta <= tau (sigma > 0 combinations)
    positive  emb record point at the replaced letter's own position: every
              pair delta > tau; it must run at one position at least (all
              positions with sigma = 0 = not executed = failure)
A loop record point counts a pair only if both prompts still execute that
loop when run alone (Gate D revision 6 single-sample semantics).
"""

import e_common  # noqa: F401,E402  (first: puts the archived modules on sys.path)
import numpy as np
import torch

from common import grouped_bootstrap  # gate_d
from e_common import encode
from runner import probe_points  # gate_d

NOT_DETECTED = "在预设最小对和数值精度下，未检测到字母敏感性"
FOUND = "发现字母敏感性"
NOT_COMPUTABLE = "标准化敏感度不可计算（σ = 0）"
QUANTILES = (0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)


class IntegrityError(RuntimeError):
    pass


def _ix(a):
    return torch.as_tensor(np.asarray(a), dtype=torch.long)


def _loop(p):
    return int(p[1:]) - 1 if p.startswith("h") and p[1:].isdigit() else None


def _single(runner, x, points):
    """Every prompt alone: records (N, L, D) per point and valid (N, T)."""
    rec = {p: [] for p in points}
    valid = []
    for i in range(len(x)):
        r = runner.run(x[i : i + 1], record=set(points))[1]
        for p in points:
            rec[p].append(r[p][0])
        if runner.arm == "openmythos":
            valid.append(torch.stack([r[f"valid{t}"][0] for t in range(4)]))
    out = {p: torch.stack(v) for p, v in rec.items()}
    V = torch.stack(valid) if valid else torch.ones(len(x), 4, dtype=torch.bool)
    return out, V


def _dist(v):
    v = np.asarray(v, dtype=np.float64)
    if len(v) == 0:
        return None
    return {"mean": float(v.mean()), "quantiles": dict(zip([str(q) for q in QUANTILES],
                                                          np.quantile(v, QUANTILES).tolist()))}


def sensitivity_stats(diff, eps_body, body_of_pair, sigma, extra_masks=None):
    """Statistics of one (record point, position) cell.
    diff (n_pairs,) raw |h_A(x) - h(x')|; eps_body dict body -> raw noise;
    body_of_pair (n_pairs,) body ids; sigma float. Pure function (tested on
    synthetic data in val_m2m3.py)."""
    diff = np.asarray(diff, dtype=np.float64)
    eps = np.asarray([eps_body[b] for b in sorted(eps_body)], dtype=np.float64)
    out = {"n_pairs": int(len(diff)), "sigma": float(sigma),
           "raw_diff": _dist(diff), "raw_eps": _dist(eps),
           "share_bitwise_zero": float((diff == 0).mean()) if len(diff) else None}
    if len(diff) == 0:
        out["label"] = "无有效最小对"
        return out, None
    if sigma == 0:
        out["label"] = NOT_COMPUTABLE
        out["reason"] = "the state at this position is identical over diag_eval (sigma = 0)"
        return out, None
    d, e = diff / sigma, eps / sigma
    tau = 10 * float(e.max()) if len(e) else 0.0
    above = d > tau
    out.update({"delta": _dist(d), "eps": _dist(e), "tau": tau,
                "share_le_tau": float((~above).mean()), "n_above_tau": int(above.sum())})
    out["label"] = FOUND if above.any() else NOT_DETECTED
    return out, above


def pooled(cells, bodies_by_cell, heldout_by_cell):
    """Pool the computable positions of one position type."""
    ind, grp, held, excluded = [], [], [], []
    for key, (stats, above) in cells.items():
        if above is None:
            excluded.append({"position": key, "label": stats["label"]})
            continue
        ind.append(above)
        grp.append(bodies_by_cell[key])
        held.append(heldout_by_cell[key])
    if not ind:
        return {"label": NOT_COMPUTABLE if any(e["label"] == NOT_COMPUTABLE for e in excluded) else "无有效最小对",
                "excluded_positions": excluded}
    a = np.concatenate(ind).astype(np.float64)
    gb = np.concatenate(grp)
    h = np.concatenate(held)
    out = {"label": FOUND if a.any() else NOT_DETECTED, "s": float(a.mean()),
           "s_ci95": grouped_bootstrap(a, gb), "n_pairs": int(len(a)), "excluded_positions": excluded}
    for name, m in (("heldout", h == 1), ("not_heldout", h == 0)):  # -1: not applicable (K=4)
        out[f"s_{name}"] = float(a[m].mean()) if m.any() else None
        out[f"n_{name}"] = int(m.sum())
    return out


def t_m3_condition(digit_labels):
    """Event t_M3 (9.4, 10.1): every digit-position record point except emb
    with sigma > 0 is "not detected"; sigma = 0 points are excluded and
    listed. Pure function (tested in val_m2m3.py)."""
    pts = [p for p in digit_labels if p != "emb"]
    computable = {p: digit_labels[p] for p in pts if digit_labels[p] in (FOUND, NOT_DETECTED)}
    return {"digit_labels": {p: digit_labels[p] for p in pts},
            "excluded_not_computable": [p for p in pts if p not in computable],
            "all_not_detected": bool(computable) and all(v == NOT_DETECTED for v in computable.values())}


def run_m3(runner, ev_rows, mp_rows, g, enforce_controls=True):
    """enforce_controls=False only in validation (constructed models whose
    letter embeddings are erased on purpose, so the positive control fails)."""
    K = g.K
    points = probe_points(runner.arm)
    N = len(ev_rows)
    x0 = encode([r["body"] + "|" + r["queries"][0] + "?" for r in ev_rows], g)
    xq = encode([r["body"] + "|" + r["queries"][1] + "?" for r in ev_rows], g)
    xm = encode([m["body"] + "|" + m["queries"][0] + "?" for m in mp_rows], g)
    recA = runner.run(x0, record=set(points))[1]
    rec0, V0 = _single(runner, x0, points)
    recQ, VQ = _single(runner, xq, points)
    recM, VM = _single(runner, xm, points)
    bid = np.asarray([m["id"] for m in mp_rows])
    stmt = np.asarray([m["stmt"] for m in mp_rows])
    held = np.asarray([(-1 if m["heldout"] is None else int(m["heldout"])) for m in mp_rows])
    id_to_row = {r["id"]: i for i, r in enumerate(ev_rows)}
    brow = np.asarray([id_to_row[b] for b in bid])
    res = {"cells": {}, "pooled": {}, "controls": {}}
    ok_neg, ok_pos, neg_detail, pos_detail = True, True, {}, {}
    for p in points:
        t = _loop(p)
        vb = V0[:, t] if t is not None else torch.ones(N, dtype=torch.bool)
        hA = recA[p].double()
        h0 = rec0[p].double()

        def sigma_at(pos):
            sel = hA[vb, pos]
            return float(sel.var(0, unbiased=True).sum().sqrt()) if len(sel) > 1 else 0.0

        def eps_at(pos):
            return {int(b): float((hA[b, pos] - h0[b, pos]).norm()) for b in torch.nonzero(vb).squeeze(1).tolist()}

        res["cells"][p] = {}
        res["pooled"][p] = {}
        for ptype, POS in (("eq", g.EQ_POS), ("digit", g.DIGIT_POS)):
            cells, bodies_by, held_by = {}, {}, {}
            for j, pos in enumerate(POS):
                sel = np.flatnonzero(stmt == j)
                if t is not None:
                    keep = (V0[_ix(brow[sel]), t] & VM[_ix(sel), t]).numpy()
                    sel = sel[keep]
                diff = (hA[_ix(brow[sel]), pos] - recM[p][_ix(sel), pos].double()).norm(dim=-1).numpy()
                stats, above = sensitivity_stats(diff, eps_at(pos), brow[sel], sigma_at(pos))
                cells[str(pos)] = (stats, above)
                bodies_by[str(pos)] = brow[sel]
                held_by[str(pos)] = held[sel]
                if above is not None:
                    for name, m in (("heldout", held[sel] == 1), ("not_heldout", held[sel] == 0)):
                        stats[f"share_above_tau_{name}"] = float(above[m].mean()) if m.any() else None
            res["cells"][p][ptype] = {k: v[0] for k, v in cells.items()}
            res["pooled"][p][ptype] = pooled(cells, bodies_by, held_by)
        # negative control: query swap, positions before the query
        neg_detail[p] = {}
        for pos in range(g.Q_POS):
            vv = vb & (VQ[:, t] if t is not None else torch.ones(N, dtype=torch.bool))
            s = sigma_at(pos)
            if s == 0 or vv.sum() == 0:
                neg_detail[p][str(pos)] = {"skipped": "sigma = 0" if s == 0 else "no valid body"}
                continue
            e = eps_at(pos)
            tau = 10 * max(e.values()) / s
            d = ((hA[vv, pos] - recQ[p][vv, pos].double()).norm(dim=-1) / s).numpy()
            passed = bool((d <= tau).all())
            neg_detail[p][str(pos)] = {"max_delta": float(d.max()), "tau": tau, "pass": passed}
            ok_neg &= passed
    # positive control: emb, replaced letter's own position
    hA = recA["emb"].double()
    for j, pos in enumerate(g.VAR_POS):
        sel = np.flatnonzero(stmt == j)
        sel_s = hA[:, pos].var(0, unbiased=True).sum().sqrt().item()
        if sel_s == 0:
            pos_detail[str(pos)] = {"skipped": "sigma = 0"}
            continue
        e = {int(b): float((hA[b, pos] - rec0["emb"][b, pos].double()).norm()) for b in range(N)}
        tau = 10 * max(e.values()) / sel_s
        d = ((hA[_ix(brow[sel]), pos] - recM["emb"][_ix(sel), pos].double()).norm(dim=-1) / sel_s).numpy()
        passed = bool((d > tau).all())
        pos_detail[str(pos)] = {"min_delta": float(d.min()), "tau": tau, "pass": passed}
        ok_pos &= passed
    # the positive control must actually run somewhere: if every letter position
    # had sigma = 0 it was not executed, which counts as a failure (run 1 of
    # val_m2m3.py showed that skipping alone would pass vacuously)
    n_pos_run = sum(1 for v in pos_detail.values() if "pass" in v)
    ok_pos = ok_pos and n_pos_run > 0
    n_neg_run = sum(1 for d in neg_detail.values() for v in d.values() if "pass" in v)
    ok_neg = ok_neg and n_neg_run > 0
    res["controls"] = {"negative_query_swap": {"pass": ok_neg, "n_cells_run": n_neg_run, "detail": neg_detail},
                       "positive_own_letter_emb": {"pass": ok_pos, "n_positions_run": n_pos_run,
                                                   "detail": pos_detail}}
    res["validity"] = {"pairs": len(mp_rows), "loop_valid_share_x": V0.float().mean(0).tolist(),
                       "loop_valid_share_xprime": VM.float().mean(0).tolist()}
    res["t_M3_condition"] = t_m3_condition({p: res["pooled"][p]["digit"]["label"] for p in points})
    if enforce_controls and not (ok_neg and ok_pos):
        raise IntegrityError(f"M3 control failed (negative {ok_neg}, positive {ok_pos})")
    return res
