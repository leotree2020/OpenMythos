#!/usr/bin/env bash
# Stage 3b add-on, REPORT ONLY (does not change any criterion; dev set only, test set untouched):
# dev NLL of native Parcae and of the two frozen 3b candidates (seed 0) at recurrence depth 8, 16, 32.
# Run on the SAME pod after run_stage3b.sh printed DONE (it needs the trained weights there).
#
#   curl -fsSL https://raw.githubusercontent.com/leotree2020/OpenMythos/mythos-stage3b-unfrozen-v1/research/mini_mythos/stage3b/depth_curve.sh | bash
set -euo pipefail
W="${STAGE3_WORK:-/workspace/mythos3b}"
REPO="$W/repo"
V="$W/venv/bin"
S3=research/mini_mythos/stage3
S3B=research/mini_mythos/stage3b
BRANCH=mythos-stage3b-unfrozen-v1
OUT="$W/depth_curve"
[ -f "$W/summary.json" ] || { echo "run_stage3b.sh has not finished (no $W/summary.json)"; exit 2; }
COMMON=(--upstream "$W/parcae" --model-dir "$W/model" --tokenizer "$W/tok/tokenizer.json" --device cuda)
SETS="$W/data/eval_sets.jsonl"
LORA=$(ls -d "$W"/runs/lora_lr*_s0 | head -1)
MODA=$(ls -d "$W"/runs/moda_lr*_s0 | head -1)
mkdir -p "$OUT"
for d in 8 16 32; do
  [ -f "$OUT/native_d$d.json" ] || (cd "$REPO/$S3" && "$V/python" -B eval_run.py --native --split dev --depth "$d" \
      --sets "$SETS" --out "$OUT/native_d$d.csv" "${COMMON[@]}")
  for run in "$LORA" "$MODA"; do
    n=$(basename "$run")
    [ -f "$OUT/${n}_d$d.json" ] || (cd "$REPO/$S3" && "$V/python" -B eval_run.py --run "$run" --split dev --depth "$d" \
        --sets "$SETS" --out "$OUT/${n}_d$d.csv" "${COMMON[@]}")
  done
done
OUT="$OUT" LORA="$(basename "$LORA")" MODA="$(basename "$MODA")" "$V/python" - <<'PY'
import json, os
from pathlib import Path
out = Path(os.environ["OUT"])
rows = {"native": "native", "C " + os.environ["LORA"]: os.environ["LORA"], "M " + os.environ["MODA"]: os.environ["MODA"]}
doms = ("books", "c4", "fineweb", "wikitext")
ood = ("books", "c4", "wikitext")
res = {}
for label, stem in rows.items():
    res[label] = {d: json.loads((out / ("%s_d%d.json" % (stem, d))).read_text()) for d in (8, 16, 32)}
L = ["# Stage 3b depth curve (dev, report only)", "",
     "Domain mean NLL; in brackets the change from the same model at depth 8. Lower is better.", "",
     "| model | depth | " + " | ".join(doms) + " | OOD mean | MoDA stats |", "|---|---:|" + "---:|" * (len(doms) + 2)]
for label, by in res.items():
    base = by[8]["domain_mean_nll"]
    for d in (8, 16, 32):
        m = by[d]["domain_mean_nll"]
        o = sum(m[x] for x in ood) / 3
        o8 = sum(base[x] for x in ood) / 3
        st = by[d].get("moda_stats")
        st = "ratio %.4f" % st["mean_depth_to_attention_norm_ratio"] if st and st.get("reads") and label.startswith("M ") else ""
        L.append("| %s | %d | %s | %.4f (%+.4f) | %s |" % (label, d, " | ".join(
            "%.4f (%+.4f)" % (m[x], m[x] - base[x]) for x in doms), o, o - o8, st))
(out / "depth_curve.md").write_text("\n".join(L) + "\n")
(out / "depth_curve.json").write_text(json.dumps(res, indent=1) + "\n")
print("\n".join(L))
PY
R="$REPO/$S3B/results/depth_curve"
mkdir -p "$R"
cp "$OUT"/*.json "$OUT"/*.md "$R/"
git -C "$REPO" add -f "$R"
git -C "$REPO" -c user.name="stage3b-runner" -c user.email="stage3b-runner@users.noreply.github.com" \
    commit -q -m "stage3b: depth curve 8/16/32 on dev (report only)" || true
for i in 1 2 3; do
  git -C "$REPO" pull -q --rebase origin "$BRANCH" && git -C "$REPO" push -q origin "HEAD:$BRANCH" && break
  sleep $((i * 5))
done
echo "DEPTH CURVE DONE. You can stop and delete the pod now."
