"""Markdown tables of reports/PILOT_FINAL_REPORT.md, generated from the committed records (no number typed by hand).

Every value is read from metrix/e1-pilot/results/ at a fixed revision (`git show <rev>:<path>`) and printed with the
file and JSON field it comes from. Decimal values are the record values formatted with Python '%.4f' (CI ends too;
'%.6f' where stated); exact fractions are the records' point_exact strings. Output: one fragment per
'<!-- FRAGMENT name -->' block on stdout; the report embeds each fragment unchanged.

Usage (repository root): python3 -I metrix/e1-pilot/reports/pilot_final/report_fragments.py [rev]   (default 53800ef7)
"""
import json
import subprocess
import sys

REV = sys.argv[1] if len(sys.argv) > 1 else "53800ef7ba5070fb1bb571c4a96a1130acebdf04"
R = "metrix/e1-pilot/results"
SEEDS = ("101", "202", "303")
SEL = {"F": "F-F3", "L": "L-L6", "A": "A-A5", "S": "S-F3", "Y": "Y-F3"}


def load(path):
    out = subprocess.run(["git", "show", "%s:%s" % (REV, path)], check=True, capture_output=True).stdout
    return json.loads(out.decode("utf-8"))


def f4(x):
    return "%.4f" % x


def frag(name, lines):
    print("<!-- FRAGMENT %s -->" % name)
    for line in lines:
        print(line)
    print("<!-- END %s -->\n" % name)


def cmp_cell(c):
    return "%s (%s) [%s, %s]" % (c["point_exact"], f4(c["point"]), f4(c["ci_low"]), f4(c["ci_high"]))


def main():
    s1 = load("%s/step1_record.json" % R)
    s2 = load("%s/step2_record.json" % R)
    s3 = load("%s/step3_record.json" % R)
    s7 = load("%s/step7_record.json" % R)
    ter = load("%s/test_evaluation_result.json" % R)
    sel = load("%s/selection_freeze_record.json" % R)
    st10 = load("%s/st10_record.json" % R)
    exf = load("%s/experiment_record_formal_20261128T045921Z.json" % R)
    ext = load("%s/experiment_record_test-evaluate_20261128T072505Z.json" % R)
    env = exf["environment"]
    v, tv = s7["values"], ter["values"]

    # ---------------------------------------------------------------- environment
    lib = env["libraries"]
    rows = ["| 项 | 值 | 出处 |", "|---|---|---|",
            "| 设备全名 | %s | experiment_record_formal_20261128T045921Z.json `environment.device`;同 test-evaluate 记录 `environment.device` = %s |" % (
                env["device"], ext["environment"]["device"]),
            "| 显存(torch total_memory) | %d 字节 | step1_record.json `device.total_memory` |" % s1["device"]["total_memory"],
            "| 主机名 | %s | experiment_record_formal… `environment.hostname`;test-evaluate 记录同字段 = %s |" % (
                env["hostname"], ext["environment"]["hostname"]),
            "| 平台 | %s | `environment.platform` |" % env["platform"],
            "| Python | %s %s | `environment.python_implementation`、`environment.python` |" % (
                env["python_implementation"], env["python"]),
            "| torch | %s(`__version__` %s) | `environment.libraries.torch` |" % (
                lib["torch"]["metadata"], lib["torch"]["__version__"]),
            "| transformers | %s | `environment.libraries.transformers.metadata` |" % lib["transformers"]["metadata"],
            "| tokenizers / huggingface_hub / safetensors / numpy / pyarrow / jinja2 | %s / %s / %s / %s / %s / %s | `environment.libraries.*.metadata` |" % tuple(
                lib[k]["metadata"] for k in ("tokenizers", "huggingface_hub", "safetensors", "numpy", "pyarrow", "jinja2")),
            "| CUDA(torch) / cuDNN | %s / %s | `environment.cuda` |" % (env["cuda"]["torch_cuda"], env["cuda"]["cudnn"]),
            "| 确定性设置 | %s | `environment.determinism` |" % ", ".join(
                "%s=%s" % (k, env["determinism"][k]) for k in sorted(env["determinism"])),
            "| 分支 / 工作区 | %s / dirty=%s | `environment.git.branch`、`environment.git.dirty` |" % (
                env["git"]["branch"], env["git"]["dirty"]),
            "| 种子 | DATA_SEED %s, CANDIDATE_SEED %s, TRAIN_SEEDS %s, BOOTSTRAP_SEED %s | `template[\"Environment (CPU/GPU, commit, seed)\"].seeds` |" % tuple(
                exf["template"]["Environment (CPU/GPU, commit, seed)"]["seeds"][k]
                for k in ("DATA_SEED", "CANDIDATE_SEED", "TRAIN_SEEDS", "BOOTSTRAP_SEED")),
            "| rng_rule | `%s` | 同上 `.seeds.rng_rule` |" % exf["template"]["Environment (CPU/GPU, commit, seed)"]["seeds"]["rng_rule"],
            ]
    frag("environment", rows)

    marker = load("%s/test_evaluation_marker.json" % R)
    efe = exf["template"]["Environment (CPU/GPU, commit, seed)"]
    ete = ext["template"]["Environment (CPU/GPU, commit, seed)"]
    rows = ["| 项 | 提交 | 出处 |", "|---|---|---|",
            "| formal 的 code_commit | `%s` | experiment_record_formal… `template[\"Environment (CPU/GPU, commit, seed)\"].code_commit` |" % efe["code_commit"],
            "| formal 实验记录写入时的 HEAD | `%s` | experiment_record_formal… `environment.git.head` |" % env["git"]["head"],
            "| test-generate(ST10 记录)的 code_commit | `%s` | st10_record.json `code_commit` |" % st10["code_commit"],
            "| test-evaluate 的 code_commit | `%s` | test_evaluation_marker.json `code_commit`;experiment_record_test-evaluate… `template[\"Environment …\"].code_commit` = `%s` |" % (
                marker["code_commit"], ete["code_commit"]),
            "| TEST 标记提交 | `%s` | test_evaluation_result.json `marker_commit` |" % ter["marker_commit"],
            "| TEST 结果提交 | `%s` | experiment_record_test-evaluate… `template.Actual.result_commit` |" % ext["template"]["Actual"]["result_commit"],
            "| test-evaluate 实验记录写入时的 HEAD | `%s` | experiment_record_test-evaluate… `environment.git.head` |" % ext["environment"]["git"]["head"],
            "| TEST 评测 session_id | `%s` | test_evaluation_marker.json `session_id`;test_evaluation_result.json `session_id` = `%s` |" % (
                marker["session_id"], ter["session_id"]),
            ]
    frag("commits", rows)

    # ---------------------------------------------------------------- frozen identity and hashes
    pf = env["protocol_frozen"]
    rows = ["| 项 | 值 | 出处 |", "|---|---|---|",
            "| 冻结版本 / 冻结提交 | %s / `%s` | experiment_record_formal… `environment.protocol_frozen.version`、`.commit`;gate0_record.json、selection_freeze_record.json、st10_record.json、test_evaluation_result.json 的 `frozen_commit` 均为 `%s` |" % (
                pf["version"], pf["commit"], ter["frozen_commit"]),
            "| PROTOCOL_FROZEN 文件 sha256 | `%s` | `environment.protocol_frozen.PROTOCOL_FROZEN_working_tree_bytes_sha256`(parsed / lf_normalized 两字段同值) |" % pf["PROTOCOL_FROZEN_working_tree_bytes_sha256"]]
    for k in sorted(pf["file_sha256"]):
        rows.append("| 冻结文件 `%s` | `%s` | `environment.protocol_frozen.file_sha256` |" % (k, pf["file_sha256"][k]))
    for k in sorted(pf["data_sha256"]):
        rows.append("| 冻结数据哈希 `%s` | `%s` | `environment.protocol_frozen.data_sha256` |" % (k, pf["data_sha256"][k]))
    inp = exf["template"]["Input (data SHA, split SHA)"]
    for k in sorted(inp["file_hashes"]):
        h = inp["file_hashes"][k]
        same = "byte = canonical" if h["byte_sha256"] == h["canonical_sha256"] else "canonical `%s`" % h["canonical_sha256"]
        rows.append("| 非 TEST 数据文件 `%s` | `%s`(%s) | `template[\"Input (data SHA, split SHA)\"].file_hashes` |" % (
            k, h["byte_sha256"], same))
    for k in sorted(inp["content_hashes"]):
        rows.append("| 内容哈希 `%s` | `%s` | `…Input….content_hashes`;selection_freeze_record.json `data_content_hashes` = `%s` |" % (
            k, inp["content_hashes"][k], sel["data_content_hashes"][k]))
    for k in sorted(inp["model_files_sha256"]):
        rows.append("| 模型权重 `%s` | `%s` | `…Input….model_files_sha256`;command_output/fetch.txt |" % (k, inp["model_files_sha256"][k]))
    for k in sorted(st10["test_files_sha256"]):
        rows.append("| TEST 文件 `%s` | `%s` | st10_record.json `test_files_sha256`;test_evaluation_marker.json 同字段 |" % (
            k, st10["test_files_sha256"][k]))
    frag("hashes", rows)

    rows = ["| 模型 | state_sha256 | 出处 |", "|---|---|---|",
            "| N | `%s` | step3_record.json `N.state_sha256`;test_evaluation_marker.json `checkpoints.N` |" % s3["N"]["state_sha256"]]
    for k in sorted(sel["checkpoints"]):
        rows.append("| %s | `%s` | selection_freeze_record.json `checkpoints.%s` |" % (k, sel["checkpoints"][k], k))
    frag("checkpoints", rows)

    # ---------------------------------------------------------------- Gate 0
    g = s7["gate0"]["conditions"]
    lk = s2["leakage"]["checks"]
    leak = "; ".join("%s %s(上限 %s)" % (k, lk[k]["value"], lk[k]["limit"]) for k in ("L1", "L2", "L3a", "L3b", "L4", "L5", "L6"))
    g3 = v["G0.3"]
    g8 = v["G0.8"]["checkpoints"]
    g8txt = "; ".join("种子 %s:items %d,max_score_diff %s,max_nll_diff %s,允许的预测差 %d,不允许的预测差 %d 个" % (
        sd, g8[sd]["items"], g8[sd]["max_score_diff"], g8[sd]["max_nll_diff"], g8[sd]["prediction_differences_allowed"],
        len(g8[sd]["prediction_differences_not_allowed"])) for sd in SEEDS)
    g10 = v["G0.10"]
    rows = ["| 编号 | 门槛(协议第 8 节) | 实测值 | 出处(results/) | 代码判定 |", "|---|---|---|---|---|",
            "| G0.1 | 泄漏检查 L1–L6 全部在上限内 | %s;结果 %s,over_limit %s | step2_record.json `leakage.checks.*`、`leakage.result`;step7_record.json `values.G0.1` | %s |" % (
                leak, s2["leakage"]["result"], v["G0.1"]["over_limit"], g["G0.1"]["satisfied"]),
            "| G0.2 | 所有损失、分数、NLL 为有限值 | all_finite %s,nonfinite %s | step7_record.json `values.G0.2` | %s |" % (
                v["G0.2"]["all_finite"], v["G0.2"]["nonfinite"], g["G0.2"]["satisfied"]),
            "| G0.3 | Acc(N, DEV-QA, learned) ∈ [0.15, 0.35];每个 stratum ∈ [0.10, 0.40];Acc(N, DEV-QA, unread) ∈ [0.10, 0.40];Acc_CB(N) ∈ [0.15, 0.35] | learned %s;natural %s;random %s;unread %s;Acc_CB %s | step7_record.json `values.G0.3` | %s |" % (
                f4(g3["acc_dev_learned"]), f4(g3["acc_dev_learned:natural"]), f4(g3["acc_dev_learned:random"]),
                f4(g3["acc_dev_unread"]), f4(g3["acc_cb"]), g["G0.3"]["satisfied"]),
            "| G0.4 | Acc_CB(F) ≥ 0.90,3 个种子 | 101: %s;202: %s;303: %s | step7_record.json `values.G0.4.acc_cb_by_seed` | %s |" % (
                tuple(f4(v["G0.4"]["acc_cb_by_seed"][sd]) for sd in SEEDS) + (g["G0.4"]["satisfied"],)),
            "| G0.5 | seed-average Acc(F, DEV-QA, learned) ≥ 0.70;seed-average Δ(F−N) 95%% CI 下界 > 0;每个种子 Δ(F−N) > 0 | Acc %s;Δ(F−N) avg %s;每个种子 %s / %s / %s | step7_record.json `values.G0.5.acc_avg`、`.delta_avg`、`.delta_by_seed` | %s |" % (
                f4(v["G0.5"]["acc_avg"]), cmp_cell(v["G0.5"]["delta_avg"]),
                *(f4(v["G0.5"]["delta_by_seed"][sd]) for sd in SEEDS), g["G0.5"]["satisfied"]),
            "| G0.6 | seed-average Δ(S−N) 点估计 ≤ +0.05 且 95%% CI 上界 ≤ +0.12 | %s | step7_record.json `values.G0.6.delta_avg` | %s |" % (
                cmp_cell(v["G0.6"]["delta_avg"]), g["G0.6"]["satisfied"]),
            "| G0.7 | seed-average Δ(Y−N) 点估计 ≤ +0.05 且 95%% CI 上界 ≤ +0.12 | %s | step7_record.json `values.G0.7.delta_avg` | %s |" % (
                cmp_cell(v["G0.7"]["delta_avg"]), g["G0.7"]["satisfied"]),
            "| G0.8 | 复现:候选分数差 ≤ 1e-4;预测相同(最高两候选差 ≤ 1e-4 时允许不同);通用窗口 NLL 差 ≤ 1e-5 | %s | step7_record.json `values.G0.8.checkpoints` | %s |" % (
                g8txt, g["G0.8"]["satisfied"]),
            "| G0.9 | seed-average Acc(F, DEV-QA, learned) ≤ 0.95 | %s | step7_record.json `values.G0.9.acc_avg` | %s |" % (
                f4(v["G0.9"]["acc_avg"]), g["G0.9"]["satisfied"]),
            "| G0.10 | 能估计 E1-V1 的规模:σ_d 有限,按公式算出所需 fact 数 | L−F:σ_d %s [%s, %s],n_max %d;A−F:σ_d %s [%s, %s],n_max %d;planning_n %d(数值见下节) | step7_record.json `values.G0.10` | %s |" % (
                f4(g10["estimates"]["L-F"]["sigma"]["point"]), f4(g10["estimates"]["L-F"]["sigma"]["p2.5"]),
                f4(g10["estimates"]["L-F"]["sigma"]["p97.5"]), g10["estimates"]["L-F"]["n_max"],
                f4(g10["estimates"]["A-F"]["sigma"]["point"]), f4(g10["estimates"]["A-F"]["sigma"]["p2.5"]),
                f4(g10["estimates"]["A-F"]["sigma"]["p97.5"]), g10["estimates"]["A-F"]["n_max"], g10["planning_n"],
                g["G0.10"]["satisfied"]),
            "", "Gate 0 状态:`%s`(step7_record.json `gate0.gate0_status`;gate0_record.json `gate0.gate0_status` = `%s`;`reasons` %s)。" % (
                s7["gate0"]["gate0_status"], load("%s/gate0_record.json" % R)["gate0"]["gate0_status"], s7["gate0"]["reasons"])]
    frag("gate0", rows)

    # ---------------------------------------------------------------- T1-T3
    fc = ter["final"]["conditions"]
    t3 = tv["T3"]
    rows = ["| 编号 | 门槛(协议第 8 节) | 实测值 | 出处(results/test_evaluation_result.json) | 代码判定 |", "|---|---|---|---|---|",
            "| T1 | seed-average Acc(F, TEST-QA, learned) ≥ 0.70,且 seed-average Δ(F−N) 95%% CI 下界 > 0 | Acc %s;Δ(F−N) avg %s | `values.T1.acc_avg`、`values.T1.delta_avg` | %s |" % (
                f4(tv["T1"]["acc_avg"]), cmp_cell(tv["T1"]["delta_avg"]), fc["T1"]["satisfied"]),
            "| T2 | S、Y 在 TEST-QA 上满足 G0.6、G0.7 的数值(点估计 ≤ +0.05 且 CI 上界 ≤ +0.12) | Δ(S−N) avg %s;Δ(Y−N) avg %s | `values.T2.S.delta_avg`、`values.T2.Y.delta_avg` | %s |" % (
                cmp_cell(tv["T2"]["S"]["delta_avg"]), cmp_cell(tv["T2"]["Y"]["delta_avg"]), fc["T2"]["satisfied"]),
            "| T3 | N 在 TEST-QA 上满足 G0.3 的同样范围(含 Acc_CB(N),解释 B24) | learned %s;natural %s;random %s;unread %s;Acc_CB %s | `values.T3` | %s |" % (
                f4(t3["acc_test_learned"]), f4(t3["acc_test_learned:natural"]), f4(t3["acc_test_learned:random"]),
                f4(t3["acc_test_unread"]), f4(t3["acc_cb"]), fc["T3"]["satisfied"]),
            "", "最终状态:`%s`(test_evaluation_result.json `final.final_status`;`final.reasons` %s;experiment_record_test-evaluate_20261128T072505Z.json `template.Status` = `%s`)。" % (
                ter["final"]["final_status"], ter["final"]["reasons"], ext["template"]["Status"])]
    frag("test", rows)

    # ---------------------------------------------------------------- comparisons (section 6)
    rows = ["| 比较 | split | 101 | 202 | 303 | seed-average | 出处 |", "|---|---|---|---|---|---|---|"]
    for comp in ("F-N", "S-N", "Y-N", "L-F", "A-F"):
        for split, rec, fname in (("DEV", s7, "step7_record.json"), ("TEST", ter, "test_evaluation_result.json")):
            cells = []
            for sd in SEEDS + ("avg",):
                c = rec["comparisons"]["%s:%s" % (comp, sd)]
                assert c["purpose"] == "%s:%s:%s" % (comp, split, sd), c["purpose"]
                assert c["replicates"] == 10000 and c["n_facts"] == 120
                cells.append(cmp_cell(c))
            rows.append("| Δ(%s) | %s | %s | %s | %s | %s | %s `comparisons.%s:<seed>` |" % (
                comp.replace("-", "−"), split, *cells, fname, comp))
    frag("comparisons", rows)

    # ---------------------------------------------------------------- Spill
    rows = ["| arm | split | 101 | 202 | 303 | seed-average | 出处 |", "|---|---|---|---|---|---|---|"]
    for arm in ("F", "L", "A", "S", "Y"):
        for split, rec, fname in (("DEV", s7, "step7_record.json"), ("TEST", ter, "test_evaluation_result.json")):
            cells = []
            for sd in SEEDS + ("avg",):
                c = rec["comparisons"]["Spill-%s:%s" % (arm, sd)]
                assert c["purpose"] == "Spill-%s:%s:%s" % (arm, split, sd) and c["n_facts"] == 40
                cells.append(cmp_cell(c))
            rows.append("| %s | %s | %s | %s | %s | %s | %s `comparisons.Spill-%s:<seed>` |" % (
                arm, split, *cells, fname, arm))
    rows.append("")
    rows.append("Prior(DEV) = Acc(N, DEV-QA, unread) = %s(step3_record.json `N.summary.acc_dev_unread`);Prior(TEST) = %s(test_evaluation_result.json `summaries.N.acc_test_unread`)。" % (
        f4(s3["N"]["summary"]["acc_dev_unread"]), f4(ter["summaries"]["N"]["acc_test_unread"])))
    frag("spill", rows)

    # ---------------------------------------------------------------- EM, FPR, accuracy per model
    rows = ["| 模型 | DEV Acc learned | DEV Acc_CB | DEV EM learned | DEV EM unread | DEV FPR | TEST Acc learned | TEST EM learned | TEST EM unread | TEST FPR |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    nd, nt = s3["N"]["summary"], ter["summaries"]["N"]
    rows.append("| N | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
        f4(nd["acc_dev_learned"]), f4(nd["acc_cb"]), f4(nd["em_dev_learned"]), f4(nd["em_dev_unread"]), f4(nd["fpr_dev"]),
        f4(nt["acc_test_learned"]), f4(nt["em_test_learned"]), f4(nt["em_test_unread"]), f4(nt["fpr_test"])))
    for arm in ("F", "L", "A", "S", "Y"):
        for sd in SEEDS:
            name = "%s-seed%s" % (SEL[arm], sd)
            d = load("%s/training_runs/%s.json" % (R, name))["dev"]
            t = ter["summaries"][name]
            rows.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                name, f4(d["acc_dev_learned"]), f4(d["acc_cb"]), f4(d["em_dev_learned"]), f4(d["em_dev_unread"]),
                f4(d["fpr_dev"]), f4(t["acc_test_learned"]), f4(t["em_test_learned"]), f4(t["em_test_unread"]),
                f4(t["fpr_test"])))
    rows.append("")
    rows.append("出处:N 的 DEV 值为 step3_record.json `N.summary.*`;其余 DEV 值为 training_runs/<模型>.json `dev.*`(`acc_dev_learned`、`acc_cb`、`em_dev_learned`、`em_dev_unread`、`fpr_dev`);TEST 值为 test_evaluation_result.json `summaries.<模型>.*`(`acc_test_learned`、`em_test_learned`、`em_test_unread`、`fpr_test`)。")
    som = s7["s_own_mapping"]
    rows.append("")
    rows.append("S 在它自己的置换映射上的正确率(step7_record.json `s_own_mapping`):" + ";".join(
        "种子 %s:DEV learned %s,TRAIN 闭卷 %s" % (sd, f4(som[sd]["s_mapping_dev_learned"]), f4(som[sd]["s_mapping_cb"]))
        for sd in SEEDS) + "。")
    frag("per_model", rows)

    # ---------------------------------------------------------------- dNLL (DEV)
    runs = load("%s/step6_record.json" % R)["training_plan"]
    rows = ["| run | 配置 | dNLL(DEV) | PPL_degradation%(DEV) |", "|---|---|---|---|"]
    for name in runs:
        rec = load("%s/training_runs/%s.json" % (R, name))
        cfg = ", ".join("%s=%s" % (k, rec["config"][k]) for k in sorted(rec["config"]) if k != "id")
        rows.append("| %s | %s | %.5f | %.2f |" % (name, cfg, rec["dnll"], rec["ppl_degradation_pct"]))
    rows.append("")
    rows.append("出处:training_runs/<run>.json `dnll`、`ppl_degradation_pct`、`config`(DEV 通用文本 general_dev.jsonl,协议第 5 节)。")
    frag("dnll", rows)

    # ---------------------------------------------------------------- G0.10 details
    rows = ["| 比较 | σ_d 点估计 | σ_d p2.5 | σ_d p97.5 | n(δ=0.05),按 σ_d p2.5 / 点 / p97.5 | n(δ=0.10),同 | n(δ=0.15),同 | n_max | 半宽检查(n, 每 stratum, 半宽) |",
            "|---|---|---|---|---|---|---|---|---|"]
    for comp in ("L-F", "A-F"):
        e = g10["estimates"][comp]
        n = e["n"]

        def ns(delta):
            return "%d / %d / %d" % (n["p2.5|delta=%s" % delta], n["point|delta=%s" % delta], n["p97.5|delta=%s" % delta])
        hw = e["halfwidth_at_planning_n"]
        rows.append("| Δ(%s) | %.6f | %.6f | %.6f | %s | %s | %s | %d | %d, %d, %.6f |" % (
            comp.replace("-", "−"), e["sigma"]["point"], e["sigma"]["p2.5"], e["sigma"]["p97.5"], ns("0.05"), ns("0.1"),
            ns("0.15"), e["n_max"], hw["n"], hw["per_stratum"], hw["halfwidth"]))
    rows.append("")
    rows.append("planning_n = %d(step7_record.json `values.G0.10.planning_n`);各值出处 step7_record.json `values.G0.10.estimates.<比较>`(`sigma`、`n`、`n_max`、`halfwidth_at_planning_n`、`finite` = %s / %s)。" % (
        g10["planning_n"], g10["estimates"]["L-F"]["finite"], g10["estimates"]["A-F"]["finite"]))
    frag("g010", rows)

    # ---------------------------------------------------------------- compute accounting
    rows = ["| run | steps_run | fact_tokens | anchor_tokens | params_forward | train_flops | anchor_flops | 训练 wall_seconds | checkpoint 保存+哈希+重载 秒 |",
            "|---|---|---|---|---|---|---|---|---|"]
    tot = dict(steps=0, fact=0, anchor=0, tf=0, af=0, wall=0.0, ck=0.0)
    for name in runs:
        rec = load("%s/training_runs/%s.json" % (R, name))
        a = rec["accounting"]
        cks = sum(rec["checkpoint"]["seconds"].values())
        tot["steps"] += rec["steps_run"]
        tot["fact"] += a["fact_tokens"]
        tot["anchor"] += a.get("anchor_tokens", 0)
        tot["tf"] += a["train_flops"]
        tot["af"] += a.get("anchor_flops", 0)
        tot["wall"] += a["wall_seconds"]
        tot["ck"] += cks
        rows.append("| %s | %d | %d | %s | %d | %.4e | %s | %.2f | %.2f |" % (
            name, rec["steps_run"], a["fact_tokens"], a.get("anchor_tokens", "—"), a["params_forward"],
            a["train_flops"], ("%.4e" % a["anchor_flops"]) if "anchor_flops" in a else "—", a["wall_seconds"], cks))
    rows.append("| 合计(30 次) | %d | %d | %d | — | %.4e | %.4e | %.2f | %.2f |" % (
        tot["steps"], tot["fact"], tot["anchor"], tot["tf"], tot["af"], tot["wall"], tot["ck"]))
    rows.append("")
    rows.append("出处:training_runs/<run>.json `steps_run`、`accounting.*`(训练 FLOPs = 6·P·T,A 的锚文本算力单列 = 2·P·T_anchor + 6·P·T_anchor,协议第 10 节、解释 B18)、`checkpoint.seconds.*`(save、hash、reload、hash_after_reload 之和)。合计为本报告对 30 条记录求和(reports/pilot_final/report_tables.txt 第 3 节)。")
    ca_f = exf["template"]["Compute accounting (tokens / steps / FLOPs / wall-clock)"]
    ca_t = ext["template"]["Compute accounting (tokens / steps / FLOPs / wall-clock)"]
    rows.append("")
    rows.append("| 量 | 值 | 出处 |")
    rows.append("|---|---|---|")
    rows.append("| 累计 GPU wall-clock(formal 结束时) | %.2f 秒 | experiment_record_formal… `template[\"Compute accounting …\"].gpu_wall_clock_seconds` |" % ca_f["gpu_wall_clock_seconds"])
    rows.append("| 累计 GPU wall-clock(test-evaluate 结束时,ST7 读这个量) | %.2f 秒 = %.4f 小时(上限 4 小时) | experiment_record_test-evaluate… 同字段 |" % (
        ca_t["gpu_wall_clock_seconds"], ca_t["gpu_wall_clock_seconds"] / 3600))
    for n in sorted(ca_f["steps"], key=int):
        rows.append("| formal 第 %s 步耗时 | %.2f 秒 | experiment_record_formal… `…steps.%s`;step%s_record.json `step_info.seconds` |" % (
            n, ca_f["steps"][n], n, n))
    pre = s2["preflight"]
    rows.append("| 预检(F-F1-seed101 前 20 步)每步平均秒数(不含第 1 步) | %.4f | step2_record.json `preflight.summary.mean_seconds_per_step_excluding_first` |" % pre["summary"]["mean_seconds_per_step_excluding_first"])
    rows.append("| 预检 tokens/s | %.2f | step2_record.json `preflight.summary.tokens_per_second` |" % pre["summary"]["tokens_per_second"])
    rows.append("| 预检 DEV 评测一次 | %.2f 秒 | step2_record.json `preflight.dev_evaluation_seconds` |" % pre["dev_evaluation_seconds"])
    rows.append("| ST11 预估 | %.4f 小时 = B17 %.4f 小时 + checkpoint 开销 %.2f 秒(上限 %s 小时;%s) | step2_record.json `preflight.st11_estimate_hours`、`.b17_estimate_hours`、`.checkpoint_overhead.seconds`、`.st11_bound_hours`、`.st11` |" % (
        pre["st11_estimate_hours"], pre["b17_estimate_hours"], pre["checkpoint_overhead"]["seconds"],
        pre["st11_bound_hours"], pre["st11"]))
    for n in range(2, 9):
        si = load("%s/step%d_record.json" % (R, n))["step_info"]
        rows.append("| 第 %d 步峰值显存 | %d 字节 | step%d_record.json `step_info.peak_memory_bytes`(%s) |" % (
            n, si["peak_memory_bytes"], n, si["peak_memory_kind"]))
    frag("compute", rows)


if __name__ == "__main__":
    main()
