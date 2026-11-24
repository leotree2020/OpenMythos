"""Every protocol value the stage B modules use, read from the frozen files.

Implementation Task Order V1, section 2 red line 6 ("门槛、超参、种子、哈希、模板一律从冻结文件读取") and section 5
(frozen.py "提供全部冻结常量"; DEFERRED_MINORS 1.18 AA5: the G0 and ST thresholds are only in the protocol text).
Sources, all taken from metrix_e1.frozen.Frozen, i.e. from the bytes of the frozen commit:
  SEARCH_SPACE.json   section 7: training contract, search grid, arm definitions, counts, hardware check, GPU hours
  DATA_MANIFEST.json  section 0 / 5: input conventions (scoring prefix, EM generation), seeds, anchor schedule
  protocol text       section 0 (determinism), 6 (bootstrap), 8 (G0.1-G0.10), 11 (ST1-ST13), 4 (arm A loss)

Where a value is written inside a sentence, the whole sentence is matched (re.fullmatch) and the number taken from
it, as data.params does: a sentence that differs from the one the implementation was written for stops the run with
IMPLEMENTATION_FAIL ("实现与本协议不一致", protocol section 9), so a changed rule can never be read with a stale
meaning. Numbers that the protocol repeats in two places are compared with each other.
"""
import re
from dataclasses import dataclass

from .errors import STATUSES, ImplementationFail

NUM = r"([0-9]+(?:\.[0-9]+)?(?:e-?[0-9]+)?)"


def _fm(pattern, text, what):
    m = re.fullmatch(pattern, text)
    if m is None:
        raise ImplementationFail("frozen text of %s is %r; the implementation expects the form %r" % (what, text, pattern))
    return m


def fullmatch_frozen(pattern, text, what):
    """Public form of the sentence match used for frozen values elsewhere in the package (test_data.py)."""
    return _fm(pattern, text, what)


def _eq(a, b, what):
    if a != b:
        raise ImplementationFail("%s: the frozen files disagree (%r vs %r)" % (what, a, b))
    return a


def protocol_row(protocol_text, key):
    """The single Markdown table row of the protocol whose first cell is `key` (e.g. "G0.3", "ST11"), without the
    leading "| key | " and the trailing " |"."""
    rows = [ln for ln in protocol_text.split("\n") if ln.startswith("| %s | " % key)]
    if len(rows) != 1:
        raise ImplementationFail("protocol table row %s: found %d rows, expected 1" % (key, len(rows)))
    return rows[0][len("| %s | " % key):-len(" |")]


def protocol_line(protocol_text, start):
    """The single line of the protocol that starts with `start`."""
    rows = [ln for ln in protocol_text.split("\n") if ln.startswith(start)]
    if len(rows) != 1:
        raise ImplementationFail("protocol line starting %r: found %d, expected 1" % (start, len(rows)))
    return rows[0]


# ------------------------------------------------------------------------------------------- training (section 7)

@dataclass(frozen=True)
class Training:
    betas: tuple
    eps: float
    epochs: int
    batch_size: int                 # statements per batch for F, L, A, S
    steps_per_epoch: int
    total_steps: int
    order_purpose: str              # "order:<epoch>"
    grad_accumulation: int
    warmup_steps: int
    final_lr_fraction: float        # the cosine ends at this fraction of the peak ...
    final_lr_step: int              # ... at this step
    weight_decay_LA: float          # L and A
    grad_clip_norm: float
    training_seeds: tuple
    search_seed: int
    n_statements: int               # F, L, A, S corpus size
    y_passes: int
    y_sentences: int
    y_batch_size: int
    y_total_steps: int
    gpu_hours_limit: float          # ST7
    device_prefix: str              # ST8
    device_min_gib: int             # ST8


def _training(ss, dm):
    tc = ss["training_contract"]
    b1, b2, eps = _fm(r"AdamW, betas \(%s, %s\), eps %s" % (NUM, NUM, NUM), tc["optimizer"], "optimizer").groups()
    purpose = _fm(r"one permutation of the corpus per epoch from Random\(rng_rule\(TRAIN_SEED, '(order:<epoch>)'\)\)",
                  tc["example_order"], "example_order").group(1)
    _fm(r"one statement per sequence; pad on the right to the longest sequence in the batch; padding excluded from "
        r"the loss", tc["sequence"], "sequence")
    warm = int(_fm(r"linear from 0 over the first (\d+) steps", tc["warmup"], "warmup").group(1))
    frac, end = _fm(r"cosine from the peak to (\d+)% of the peak at step (\d+)", tc["scheduler"], "scheduler").groups()
    wd = _fm(r"per SEARCH_SPACE for F; %s for L and A; applied to 2-D weight matrices only" % NUM, tc["weight_decay"],
             "weight_decay").group(1)
    clip = _fm(r"global norm %s" % NUM, tc["gradient_clipping"], "gradient_clipping").group(1)
    _fm(r"bfloat16 autocast with float32 master weights", tc["precision"], "precision")
    _fm(r"only the final checkpoint of a run is kept and evaluated; no intermediate checkpoint is used for anything",
        tc["checkpoint_policy"], "checkpoint_policy")
    _fm(r"not allowed", tc["early_stopping"], "early_stopping")
    passes, n_st, y_passes, y_n, y_b, y_steps = (int(x) for x in _fm(
        r"(\d+) passes over the (\d+) TRAIN statements for F, L, A and S \(identical statements up to the S permutation\); "
        r"Y: (\d+) passes over its (\d+) sentences with batch (\d+) \((\d+) steps\); Y tokens / F tokens must lie in "
        r"\[[0-9.]+, [0-9.]+\]", tc["primary_training_token_budget"], "primary_training_token_budget").groups())
    hw = tc["hardware"]
    prefix, gib = _fm(r"torch\.cuda\.get_device_name\(0\) starts with '([^']+)' and "
                      r"torch\.cuda\.get_device_properties\(0\)\.total_memory >= (\d+) \* 2\*\*30; otherwise BLOCKED \(ST8\)",
                      hw["check"], "hardware.check").groups()
    t = Training(
        betas=(float(b1), float(b2)), eps=float(eps), epochs=_eq(tc["epochs"], passes, "epochs"),
        batch_size=tc["batch_size_statements"], steps_per_epoch=tc["steps_per_epoch"], total_steps=tc["total_steps"],
        order_purpose=purpose, grad_accumulation=tc["gradient_accumulation"], warmup_steps=warm,
        final_lr_fraction=int(frac) / 100.0, final_lr_step=int(end), weight_decay_LA=float(wd),
        grad_clip_norm=float(clip), training_seeds=tuple(_eq(tc["training_seeds"], dm["seeds"]["TRAIN_SEEDS"], "seeds")),
        search_seed=ss["search_seed"], n_statements=n_st, y_passes=y_passes, y_sentences=y_n, y_batch_size=y_b,
        y_total_steps=y_steps, gpu_hours_limit=float(tc["wall_clock_limit_gpu_hours"]), device_prefix=prefix,
        device_min_gib=int(gib))
    # internal consistency of the contract (a contradiction is a protocol defect -> stop)
    _eq(t.n_statements // t.batch_size, t.steps_per_epoch, "statements / batch vs steps_per_epoch")
    _eq(t.epochs * t.steps_per_epoch, t.total_steps, "epochs x steps_per_epoch vs total_steps")
    _eq(t.y_passes * (t.y_sentences // t.y_batch_size), t.y_total_steps, "Y passes x steps vs Y steps")
    _eq(t.y_total_steps, t.total_steps, "Y steps vs total_steps")
    _eq(t.final_lr_step, t.total_steps, "scheduler end step vs total_steps")
    _eq(t.grad_accumulation, 1, "gradient_accumulation (only 1 is implemented)")
    _eq(t.search_seed, t.training_seeds[0], "search_seed vs first training seed")
    return t


# ------------------------------------------------------------------------------------------- arms (sections 4, 7)

@dataclass(frozen=True)
class Arms:
    configs: dict                   # arm -> list of config dicts (F, L, A), in SEARCH_SPACE order
    lora_modules: tuple             # q_proj, ...
    lora_layers: int                # 28
    lora_alpha_per_rank: float      # alpha = 2 * rank
    lora_dropout: float
    anchor_docs_per_step: int       # 4
    anchor_n_docs: int              # 512
    anchor_schedule: tuple          # (multiplier, modulus, i_max): docs (multiplier*s + i) mod modulus, i = 0..i_max
    inheriting: tuple               # ("S", "Y"): use the configuration selected for F
    tie_break: tuple
    counts: dict


def _arms(ss, dm, protocol_text):
    arms = ss["arms"]
    lora = _fm(r"base frozen; LoRA on ([a-z_, ]+) of all (\d+) layers; alpha = (\d+) \* rank; dropout %s; B initialised "
               r"to 0" % NUM, arms["L"]["definition"], "arms.L.definition")
    mods, layers, alpha, drop = lora.groups()
    k = int(_fm(r"F plus lambda \* KL\(p_base \|\| p_theta\) on general anchor text, (\d+) anchor documents per step",
                arms["A"]["definition"], "arms.A.definition").group(1))
    mul, mod, imax = (int(x) for x in _fm(r"step s uses documents \((\d+)\*s \+ i\) mod (\d+), i = 0\.\.(\d+)",
                                         dm["anchor_text"]["schedule"], "anchor_text.schedule").groups())
    _fm(r".*第 s 步使用第 \(%ds \+ i\) mod %d 篇,i = 0\.\.%d。.*" % (mul, mod, imax),
        protocol_line(protocol_text, "- **锚文本(只用于 arm A)**"), "protocol 2.7 anchor schedule")
    _eq(imax + 1, k, "anchor documents per step (schedule vs arm A definition)")
    _eq(mul, k, "anchor schedule multiplier vs documents per step")
    for a in ("S", "Y"):
        _fm(r"the configuration selected for F", arms[a]["inherits"], "arms.%s.inherits" % a)
        _eq(arms[a]["configs"], [], "arms.%s.configs" % a)
    _eq(arms["N"]["configs"], [], "arms.N.configs")
    sel = ss["selection"]
    _eq(sel["tie_break"], ["lower general DEV dNLL", "lower learning rate", "lower config index"], "selection.tie_break")
    _fm(r"any configuration with a non-finite loss or score", sel["excluded"], "selection.excluded")
    _fm(r"Acc\(arm, DEV-QA, learned\), fact-level mean aggregation", sel["metric"], "selection.metric")
    _fm(r"DEV only", sel["split"], "selection.split")
    configs = {a: [dict(c) for c in arms[a]["configs"]] for a in ("F", "L", "A")}
    for a, keys in (("F", {"id", "learning_rate", "weight_decay"}), ("L", {"id", "learning_rate", "rank", "weight_decay"}),
                    ("A", {"id", "learning_rate", "anchor_lambda", "weight_decay"})):
        for i, c in enumerate(configs[a], 1):
            _eq(set(c), keys, "arms.%s config keys" % a)
            _eq(c["id"], "%s%d" % (a, i), "arms.%s config id" % a)
    cnt = ss["counts"]
    _eq(cnt["search_runs"], sum(len(v) for v in configs.values()), "counts.search_runs")
    n_docs = int(_fm(r"first (\d+) documents in file order with at least \d+ characters", dm["anchor_text"]["selection"],
                     "anchor_text.selection").group(1))
    _eq(mod, n_docs, "anchor schedule modulus vs number of anchor documents")
    return Arms(configs=configs, lora_modules=tuple(m.strip() for m in mods.split(",")), lora_layers=int(layers),
                lora_alpha_per_rank=float(alpha), lora_dropout=float(drop), anchor_docs_per_step=k, anchor_n_docs=n_docs,
                anchor_schedule=(mul, mod, imax), inheriting=("S", "Y"), tie_break=tuple(sel["tie_break"]), counts=dict(cnt))


# ------------------------------------------------------------------------------------- evaluation (sections 0, 5)

@dataclass(frozen=True)
class Evaluation:
    answer_prefix: str              # "The answer is"
    endoftext_id: int
    max_new_tokens: int
    stop_ids: tuple                 # (im_end, endoftext)
    think_open_id: int
    think_close_id: int


def _evaluation(dm, protocol_text):
    ic = dm["model"]["input_convention"]
    _fm(r"chat template of the pinned revision, one user turn, add_generation_prompt=true, enable_thinking=false "
        r"\(fixed, not a parameter\), no system prompt", ic["qa"], "input_convention.qa")
    prefix = _fm(r"chat\(q\) \+ '([^']+)' \+ ' ' \+ c: the assistant turn opens with the fixed prefix '([^']+)'; only "
                 r"the tokens of ' ' \+ c are scored; nothing follows the candidate; K = K_st; reference implementation "
                 r"metrix/e1-pilot/reports/round3/scoring_input\.py", ic["candidate_scoring"], "candidate_scoring")
    _eq(prefix.group(1), prefix.group(2), "candidate_scoring prefix")
    _fm(r"s_ST scores ' ' \+ c after prefix\(f\), the text of the TRAIN statement before the answer without the space "
        r"before the answer; no special token is prepended to prefix\(f\) \(protocol section 5\)",
        ic["train_closed_book"], "input_convention.train_closed_book")
    _fm(r"general-damage windows and arm A anchor documents: no special token is prepended \(no <\|endoftext\|>\); the "
        r"first token has no context and is not scored and gets no KL term; t starts at 2 \(protocol sections 4 and 5\)",
        ic["general_text_and_anchor"], "input_convention.general_text_and_anchor")
    eot = int(_fm(r"raw statement text followed by <\|endoftext\|> \(id (\d+)\); no chat template, no system prompt",
                  ic["training"], "input_convention.training").group(1))
    em = _fm(r"greedy decoding with do_sample=False \(the token of highest probability at each step\); fixed, and it "
             r"overrides the sampling defaults of the pinned generation_config\.json \(do_sample true, temperature 0\.6, "
             r"top_k 20, top_p 0\.95\); continues chat\(q\) \+ '%s', the same context as candidate scoring; at most (\d+) "
             r"new tokens; stops when <\|im_end\|> \((\d+)\) or <\|endoftext\|> \((\d+)\) is generated; the new tokens are "
             r"decoded with special tokens skipped \(skip_special_tokens=True\), so neither stop token is in the output; "
             r"EM compares norm\(output\) with norm\(answer\) \(protocol section 5\); before the normalization every "
             r"<think>\.\.\.</think> fragment of the output is deleted \(from <think> to the next </think>, both included, "
             r"every occurrence\); <think> \((\d+)\) and </think> \((\d+)\) are not special tokens, so "
             r"skip_special_tokens=True does not remove them; after the deletion the normalization first removes the "
             r"leading whitespace \(spaces and newlines\), then takes the first line, strips, removes a leading 'the ' "
             r"\(case-insensitive\), removes trailing \. , ; : ! \? and casefolds \(protocol section 5\)"
             % re.escape(prefix.group(1)), ic["em_generation"], "input_convention.em_generation")
    n_new, im_end, eot2, t_open, t_close = (int(x) for x in em.groups())
    _eq(eot, eot2, "endoftext id (training vs EM)")
    # protocol section 5 repeats the EM numbers
    _fm(r".*最多 %d 个新 token,生成出 `<\|im_end\|>`\(id %d\)或 `<\|endoftext\|>`\(id %d\)即停。.*这两个标记\(id %d、%d\)不是"
        r"特殊 token.*" % (n_new, im_end, eot, t_open, t_close),
        protocol_line(protocol_text, "**Free-generation exact match"), "protocol section 5 EM")
    return Evaluation(answer_prefix=prefix.group(1), endoftext_id=eot, max_new_tokens=n_new, stop_ids=(im_end, eot),
                      think_open_id=t_open, think_close_id=t_close)


# --------------------------------------------------------------------------------------- statistics (section 6)

@dataclass(frozen=True)
class Statistics:
    n_boot: int
    ci_low_pct: float
    ci_high_pct: float
    purpose_format: str             # "<比较>:<split>:<seed 或 avg>"
    bootstrap_seed: int
    strata: tuple                   # resampled separately, in this order
    z_sum: float                    # 1.96 + 0.84 (G0.10)
    deltas: tuple                   # G0.10 effect sizes


def _statistics(dm, protocol_text):
    ln = protocol_line(protocol_text, "- 次数 **")
    n, s1, s2, lo, hi, purpose = _fm(
        r"- 次数 \*\*([0-9,]+)\*\*;在 (\w+)、(\w+) 两个 stratum 内分别有放回重抽\(保持各自的 fact 数\),合并后取 "
        r"`Δ\* = mean\(d_f\)`;95%% CI = 第 %s 与第 %s 百分位。随机数:`rng_rule\(BOOTSTRAP_SEED, \"([^\"]+)\"\)`。" % (NUM, NUM),
        ln, "protocol section 6 bootstrap").groups()
    _eq((s1, s2), tuple(dm["facts"]["strata"]), "bootstrap strata vs DATA_MANIFEST facts.strata")
    _fm(r"<比较>:<split>:<seed 或 avg>", purpose, "bootstrap purpose (stats.purpose writes '<X>-<Y>:<split>:<seed>')")
    g10 = protocol_row(protocol_text, "G0.10")
    za, zp, d1, d2, d3 = _fm(
        r"能估计 E1-V1 的规模:对 Δ\(L−F\)、Δ\(A−F\) 的 seed-average 配对差 d_f 算出标准差 σ_d\(有限\);分别用 σ_d 的 bootstrap "
        r"%s 分位、点估计、%s 分位,按 `n = \(\(%s \+ %s\) · σ_d / δ\)²`\(双侧 0\.05、功效 0\.80\)计算 δ ∈ \{%s, %s, %s\} 下的所需 "
        r"fact 数,以最大者作为 E1-V1 规划依据;再用 Pilot 的 fact 按 n 重抽样验证 CI 半宽。Pilot 的规模估计是规划估计,不是保证"
        % (re.escape(lo), re.escape(hi), NUM, NUM, NUM, NUM, NUM), g10, "G0.10").groups()
    return Statistics(n_boot=int(n.replace(",", "")), ci_low_pct=float(lo), ci_high_pct=float(hi), purpose_format=purpose,
                      bootstrap_seed=dm["seeds"]["BOOTSTRAP_SEED"], strata=(s1, s2), z_sum=float(za) + float(zp),
                      deltas=(float(d1), float(d2), float(d3)))


# ------------------------------------------------------------------------------------------- Gate 0 (section 8)

@dataclass(frozen=True)
class Gate:
    g3_learned: tuple               # [lo, hi] of Acc(N, DEV-QA, learned)
    g3_stratum: tuple
    g3_unread: tuple
    g3_cb: tuple
    g4_cb_min: float
    g5_acc_min: float
    g6_point_max: float
    g6_upper_max: float
    g7_point_max: float
    g7_upper_max: float
    g8_score_tol: float
    g8_top2_tol: float
    g8_nll_tol: float
    g9_acc_max: float
    too_hard_below: float           # section 8: < 0.40 "对该模型与该训练量过难"
    t1_acc_min: float               # section 8 TEST confirmation T1 (T2, T3 reuse the G0.6 / G0.7 / G0.3 numbers)


def _gate(protocol_text):
    r = {k: protocol_row(protocol_text, k) for k in ("G0.1", "G0.2", "G0.3", "G0.4", "G0.5", "G0.6", "G0.7", "G0.8", "G0.9")}
    _fm(r"泄漏检查 L1–L6 全部在上限内;L1–L6 中涉及 TEST 的部分在 Gate 0 不要求,按第 8 步运行", r["G0.1"], "G0.1")
    _fm(r"所有用到的损失、分数、NLL 都是有限值", r["G0.2"], "G0.2")
    iv = r"\[%s, %s\]" % (NUM, NUM)
    g3 = [float(x) for x in _fm(
        r"N 的下限检查:`Acc\(N, DEV-QA, learned\)` ∈ %s,每个 stratum ∈ %s;`Acc\(N, DEV-QA, unread\)` ∈ %s;`Acc_CB\(N\)` ∈ %s"
        % (iv, iv, iv, iv), r["G0.3"], "G0.3").groups()]
    g4 = float(_fm(r"`Acc_CB\(F\)` ≥ %s,3 个种子都满足" % NUM, r["G0.4"], "G0.4").group(1))
    g5 = float(_fm(r"seed-average `Acc\(F, DEV-QA, learned\)` ≥ %s;seed-average Δ\(F−N\) 的 95%% CI 下界 > 0;每个种子的 "
                   r"Δ\(F−N\) > 0" % NUM, r["G0.5"], "G0.5").group(1))
    g6 = [float(x) for x in _fm(r"seed-average Δ\(S−N\)\(真实映射,DEV-QA,learned\):点估计 ≤ \+%s 且 95%% CI 上界 ≤ \+%s"
                                % (NUM, NUM), r["G0.6"], "G0.6").groups()]
    g7 = [float(x) for x in _fm(r"seed-average Δ\(Y−N\)\(DEV-QA,learned\):点估计 ≤ \+%s 且 95%% CI 上界 ≤ \+%s" % (NUM, NUM),
                                r["G0.7"], "G0.7").groups()]
    g8 = [float(x) for x in _fm(
        r"复现：对 F 选定配置的 3 个 checkpoint 各评测两次；候选分数差 ≤ %s；某题两次中任一次最高两个候选分数差 ≤ %s "
        r"时允许预测不同，其余预测须完全相同；并列判为错；每个通用窗口的 NLL 差 ≤ %s。实现须开启 PyTorch 确定性设置并记录。"
        % (NUM, NUM, NUM), r["G0.8"], "G0.8").groups()]
    g9 = float(_fm(r"上限检查:seed-average `Acc\(F, DEV-QA, learned\)` ≤ %s" % NUM, r["G0.9"], "G0.9").group(1))
    hard, lo2, hi2 = _fm(r"- seed-average `Acc\(F, DEV-QA, learned\)` < %s 记为“对该模型与该训练量过难”;在 \[%s, %s\) 记为 "
                         r"OPTIMIZATION_OR_CAPACITY_UNRESOLVED。两者都属于 PIPELINE_NOT_QUALIFIED。" % (NUM, NUM, NUM),
                         protocol_line(protocol_text, "- seed-average `Acc(F, DEV-QA, learned)` <"),
                         "section 8 too-hard line").groups()
    t1 = float(_fm(r"seed-average `Acc\(F, TEST-QA, learned\)` ≥ %s,且 seed-average Δ\(F−N\) 的 95%% CI 下界 > 0" % NUM,
                   protocol_row(protocol_text, "T1"), "T1").group(1))
    _fm(r"S、Y 在 TEST-QA 上满足 G0\.6、G0\.7 的同样数值", protocol_row(protocol_text, "T2"), "T2")
    _fm(r"N 在 TEST-QA 上满足 G0\.3 的同样范围", protocol_row(protocol_text, "T3"), "T3")
    _eq(float(lo2), float(hard), "too-hard bound vs unresolved interval")
    _eq(float(hi2), g5, "unresolved interval upper bound vs G0.5")
    return Gate(g3_learned=tuple(g3[0:2]), g3_stratum=tuple(g3[2:4]), g3_unread=tuple(g3[4:6]), g3_cb=tuple(g3[6:8]),
                g4_cb_min=g4, g5_acc_min=g5, g6_point_max=g6[0], g6_upper_max=g6[1], g7_point_max=g7[0],
                g7_upper_max=g7[1], g8_score_tol=g8[0], g8_top2_tol=g8[1], g8_nll_tol=g8[2], g9_acc_max=g9,
                too_hard_below=float(hard), t1_acc_min=t1)


# ------------------------------------------------------------------------------------- stops (sections 0, 11)

@dataclass(frozen=True)
class Stops:
    st3_cb_min: float
    st3_acc_min: float
    st7_hours: float
    st11_hours: float
    cublas_workspace_config: str


def _stops(protocol_text, training):
    st3 = [float(x) for x in _fm(r"第 4 步 F 选定配置\(种子 (\d+)\)的 `Acc_CB` < %s,或 `Acc\(F, DEV-QA, learned\)` < %s" % (NUM, NUM),
                                 protocol_row(protocol_text, "ST3").split(" | ")[0], "ST3").groups()]
    _eq(int(st3[0]), training.search_seed, "ST3 seed vs search seed")
    st7 = float(_fm(r"累计 GPU wall-clock 超过 %s 小时\(第 7 节\)" % NUM, protocol_row(protocol_text, "ST7").split(" | ")[0],
                    "ST7").group(1))
    _eq(st7, training.gpu_hours_limit, "ST7 hours vs SEARCH_SPACE wall_clock_limit_gpu_hours")
    st11 = float(_fm(r"第 8 节第 2 步预检的预估总时长超过 %s 小时" % NUM, protocol_row(protocol_text, "ST11").split(" | ")[0],
                     "ST11").group(1))
    _fm(r"预检\(正式运行前;ST11\):在 A100 上跑第一个配置的前 (\d+) 步,记录每步耗时、tokens/s、峰值显存与预估总时长;预估超过 "
        r"%s 小时即停止并报告 Owner。" % re.escape(("%g" % st11)), protocol_line(protocol_text, "   预检(").strip(), "preflight")
    cublas = _fm(r".*确定性:`torch\.use_deterministic_algorithms\(True\)`,关闭 TF32,`CUBLAS_WORKSPACE_CONFIG=([:0-9]+)`。",
                 protocol_line(protocol_text, "**环境要求**"), "section 0 determinism").group(1)
    return Stops(st3_cb_min=st3[1], st3_acc_min=st3[2], st7_hours=st7, st11_hours=st11, cublas_workspace_config=cublas)


def preflight_steps(protocol_text):
    """Protocol section 8 step 2: number of steps of the first configuration run by the preflight (ST11)."""
    return int(_fm(r"预检\(正式运行前;ST11\):在 A100 上跑第一个配置的前 (\d+) 步,.*",
                   protocol_line(protocol_text, "   预检(").strip(), "preflight").group(1))


# ------------------------------------------------------------------------------- record, statuses, splits (9, 10)

@dataclass(frozen=True)
class Accounting:
    train_flops_per_param_token: int        # section 10: training FLOPs ~ 6 P T
    forward_flops_per_param_token: int      # section 10: forward FLOPs ~ 2 P T
    dev_questions_per_fact: int             # SPLIT_MANIFEST splits.DEV
    test_questions_per_fact: int            # SPLIT_MANIFEST splits.TEST


def _accounting(sm, protocol_text):
    tr, fw = (int(x) for x in _fm(
        r"Compute accounting 的算法:训练 FLOPs ≈ (\d+) · P · T,前向 FLOPs ≈ (\d+) · P · T\(P = 参与计算的参数量,T = token 数\);"
        r"token、步数、wall-clock 取实测值;A 的锚文本算力单列。",
        protocol_line(protocol_text, "Compute accounting 的算法"), "section 10 compute accounting").groups())
    dev = int(_fm(r"(\d+) questions per fact \(learned and unread\), DEV templates", sm["splits"]["DEV"], "splits.DEV").group(1))
    test = int(_fm(r"(\d+) questions per fact \(learned and unread\), TEST templates; not generated before the final freeze",
                   sm["splits"]["TEST"], "splits.TEST").group(1))
    return Accounting(train_flops_per_param_token=tr, forward_flops_per_param_token=fw, dev_questions_per_fact=dev,
                      test_questions_per_fact=test)


def check_status_vocabulary(protocol_text):
    """Section 9: the fixed status set, read from the frozen protocol, must be errors.STATUSES (same words, same
    order); otherwise the implementation does not match the protocol."""
    line = protocol_line(protocol_text, "`PASS` / ")
    words = tuple(w.strip().strip("`") for w in line.split(" / "))
    _eq(words, STATUSES, "section 9 status vocabulary vs errors.STATUSES")
    return words


# ------------------------------------------------------------------------------------------------------ all

@dataclass(frozen=True)
class Contract:
    training: Training
    arms: Arms
    evaluation: Evaluation
    statistics: Statistics
    gate: Gate
    stops: Stops
    accounting: Accounting
    statuses: tuple
    preflight_steps: int


def load(fz):
    """Parse every stage B value from the frozen files of `fz` (metrix_e1.frozen.Frozen)."""
    ss, dm, text = fz.search_space, fz.data_manifest, fz.protocol_text
    training = _training(ss, dm)
    return Contract(training=training, arms=_arms(ss, dm, text), evaluation=_evaluation(dm, text),
                    statistics=_statistics(dm, text), gate=_gate(text), stops=_stops(text, training),
                    accounting=_accounting(fz.split_manifest, text), statuses=check_status_vocabulary(text),
                    preflight_steps=preflight_steps(text))
