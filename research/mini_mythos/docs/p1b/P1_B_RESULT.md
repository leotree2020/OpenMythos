# P1-B: Parcae native CPU correctness check — result

**P1-B status: COMPLETE** (six required checks: all PASS; re-run reproducibility: PASS).

Scope: numerical/mechanical correctness of the *official, unmodified* Parcae code on CPU with a size-reduced, randomly initialised `parcae-small-140m` config and synthetic tokens. No checkpoint was downloaded, no 140M model was built or trained, no GPU was used. The only optimisation is 3 AdamW steps on one fixed batch to break the scaled-zero symmetry for the after-step diagnostics. **This is not a model-quality result.**

## Upstream source

- Repository: https://github.com/sandyresearch/parcae
- Pinned commit: `69284c13746e849104f738d6d1a347b1f457df76` (2026-09-02T13:42:41-07:00, "Merge pull request #11 from sandyresearch/fix/distributed-data-loading")
- Checkout clean before/after run: tracked changes 0/0, untracked files 0/0, ignored files 0/0
- Imported Parcae modules: 33 files, all blobs equal to the pinned commit: True
- Parcae code is called from the checkout via `sys.path`; nothing is copied into OpenMythos.

## Environment

- Python 3.12.3 (isolated venv: True), torch 2.11.0+cu130 (CUDA build 13.0, CUDA available: False), numpy 1.26.4, einops 0.8.0
- Linux 6.18.44-fc-v140 x86_64, CPU: Intel(R) Xeon(R) Processor @ 2.80GHz; torch threads 1, deterministic algorithms True
- Parcae attention backend in effect: torch SDPA fallback
- torch is the PyPI `torch==2.11.0` wheel pinned in `requirements-p1b-parcae.txt` (a CUDA-enabled build, used on CPU only). Full package list in `P1_B_ENVIRONMENT.json`.

## Size-reduced config (mechanism unchanged)

| field | official 140M | P1-B |
|---|---|---|
| `block_size` | 2048 | 32 |
| `vocab_size` | 32768 | 256 |
| `n_embd` | 768 | 64 |
| `num_attention_heads` | 6 | 4 |
| `num_key_value_heads` | 6 | 4 |
| `intermediate_size` | 3072 | 256 |
| `recurrent_embedding_dimension` | 768 | 64 |
| `recurrent_intermediation_embedding_dimension` | 3072 | 256 |
| `n_layers_in_prelude` | 2 | 1 |
| `n_layers_in_recurrent_block` | 2 | 2 |
| `n_layers_in_coda` | 2 | 1 |

All 25 mechanism fields (injection, init, sampling, norms, nonlinearity, qk_norm, tying, ...) equal the official values: True. Batch 4 x 16 tokens, seed 20261022. Parameters: 254976.

## Results

| # | check | status | required sub-checks |
|---|---|---|---|
| 1 | Prelude -> Recurrent Core -> Coda forward path | **PASS** | 5/5 PASS |
| 2 | Loss, logits and gradients are finite | **PASS** | 4/4 PASS |
| 3 | Backward reaches shared core and injection | **PASS** | 7/7 PASS |
| 4 | State norms / changes for 1, 2, 4, 8 loops | **PASS** | 9/9 PASS |
| 5 | Actual DiagonalInjection decay | **PASS** | 8/8 PASS |
| 6 | Native no-grad / with-grad loop configuration | **PASS** | 17/17 PASS |
| R | Re-run reproducibility | **PASS** | 4/4 JSON identical |

## Key observed values

- State norms (init, mean per-token L2 of final state / last change): r=1: |x|=6.4389, |dx|=6.44, r=2: |x|=9.3101, |dx|=2.88, r=4: |x|=11.1708, |dx|=0.576, r=8: |x|=11.6176, |dx|=0.02304
- State norms (after_adamw_steps, mean per-token L2 of final state / last change): r=1: |x|=6.8131, |dx|=6.807, r=2: |x|=9.8486, |dx|=3.044, r=4: |x|=11.8157, |dx|=0.6089, r=8: |x|=12.2881, |dx|=0.02437
- Init: successive state-change ratios 0.4472135..0.4472136 (exact linear injection dynamics; scaled-zero core is identity at init)
- Decay (init): min 0.4472136, max 0.4472136, mean 0.4472136; get_spectral_norm 0.4472136, get_contraction_factor 0.4472136
- Decay (after_adamw_steps): min 0.4468480, max 0.4483003, mean 0.4473197; get_spectral_norm 0.4483003, get_contraction_factor 0.4473197
- Decay (official_parcae-small-140m_injection): min 0.4472136, max 0.4472136, mean 0.4472136; get_spectral_norm 0.4472136, get_contraction_factor 0.4472136
- Group grad norms (init, pair [4, 4]): wte 1.379, prelude 4.646, adapter 0.5933, core_block 0.7671, C 0.9724, coda 0.5819, ln_f 0.0888, ln_prelude 0.07, value_embeds.1 0, value_embeds.3 0
- Group grad norms (after_adamw_steps, pair [4, 4]): wte 1.103, prelude 3.04, adapter 0.4138, core_block 0.5596, C 0.7038, coda 0.3912, ln_f 0.2177, ln_prelude 0.06177, value_embeds.1 0.001514, value_embeds.3 0.001311
- Native per-sequence sampler over 4000 draws: mean n 4.079, mean k 3.943, mean total 8.021, max k 4, violations 0
- Native gated forward (model.step=0): per-sample n [2, 5, 0, 3], k [4, 4, 3, 4], gating mismatches 0, loss 3.66192
- AdamW diagnostic losses before each step: 5.77787, 4.95519, 4.23864

## Sub-check details

### 1. Prelude -> Recurrent Core -> Coda forward path — PASS

- **PASS** module call order, train mode, num_steps_pair=[4, 4]  
  criterion: exact match: wte, prelude, ln_prelude, (adapter, core_block.*) x 8, C, coda, ln_f, lm_head  
  observed: `{"observed": ["transformer.wte", "transformer.prelude.0", "transformer.ln_prelude", "transformer.adapter", "transformer.core_block.0", "transformer.core_block.1", "transformer.adapter", "transformer.core_block.0", "trans ...`
- **PASS** module output shapes  
  criterion: [B, T, d]: d=64 outside the core, 64 for adapter/core, 256 for lm_head  
  observed: `{"transformer.wte": [4, 16, 64], "transformer.prelude.0": [4, 16, 64], "transformer.ln_prelude": [4, 16, 64], "transformer.adapter": [4, 16, 64], "transformer.core_block.0": [4, 16, 64], "transformer.core_block.1": [4, 1 ...`
- **PASS** core layers and injection are one shared set of modules reused each loop  
  criterion: each core layer and the adapter called exactly 8 times through one module object  
  observed: `{"calls_per_module": {"transformer.core_block.0": 8, "transformer.core_block.1": 8, "transformer.adapter": 8}, "distinct_module_objects_per_name": 1, "n_core_layers": 2}`
- **PASS** logits and loss shape  
  criterion: logits [4, 16, 256], scalar loss  
  observed: `{"logits_shape": [4, 16, 256], "loss": 5.777870178222656}`
- **PASS** eval mode with upstream eval pair num_steps_pair=[8, 0]  
  criterion: same path with 8 loops (pair used by upstream receval/scripts/train.py eval)  
  observed: `{"adapter_calls": 8, "loss": 5.777870178222656}`

### 2. Loss, logits and gradients are finite — PASS

- **PASS** init: fixed num_steps_pair=[4, 4]  
  criterion: finite loss/log_ppl/logits; every parameter has a finite gradient  
  observed: `{"loss": 5.777870178222656, "loss_finite": true, "log_ppl_finite": true, "logits_finite": true, "logits_abs_max": 2.467153549194336, "params_with_grad": 43, "params_total": 43, "params_grad_none": [], "params_grad_nonfin ...`
- **PASS** init: native sampled depths (train, model.step=0)  
  criterion: finite loss/logits; no non-finite gradient  
  observed: `{"loss": 5.777433395385742, "loss_finite": true, "log_ppl_finite": true, "logits_finite": true, "logits_abs_max": 2.4671616554260254, "params_with_grad": 43, "params_total": 43, "params_grad_none": [], "params_grad_nonfi ...`
- **PASS (not required)** init: deeper recurrence 16 loops (supplementary)  
  criterion: finite loss/logits and gradients  
  observed: `{"loss": 5.777881622314453, "loss_finite": true, "log_ppl_finite": true, "logits_finite": true, "logits_abs_max": 2.4671688079833984, "params_with_grad": 43, "params_total": 43, "params_grad_none": [], "params_grad_nonfi ...`
- **PASS (not required)** init: deeper recurrence 32 loops (supplementary)  
  criterion: finite loss/logits and gradients  
  observed: `{"loss": 5.777881622314453, "loss_finite": true, "log_ppl_finite": true, "logits_finite": true, "logits_abs_max": 2.4671683311462402, "params_with_grad": 43, "params_total": 43, "params_grad_none": [], "params_grad_nonfi ...`
- **PASS** after_adamw_steps: fixed num_steps_pair=[4, 4]  
  criterion: finite loss/log_ppl/logits; every parameter has a finite gradient  
  observed: `{"loss": 3.6642844676971436, "loss_finite": true, "log_ppl_finite": true, "logits_finite": true, "logits_abs_max": 3.977747678756714, "params_with_grad": 43, "params_total": 43, "params_grad_none": [], "params_grad_nonfi ...`
- **PASS** after_adamw_steps: native sampled depths (train, model.step=0)  
  criterion: finite loss/logits; no non-finite gradient  
  observed: `{"loss": 3.6619198322296143, "loss_finite": true, "log_ppl_finite": true, "logits_finite": true, "logits_abs_max": 3.977989912033081, "params_with_grad": 43, "params_total": 43, "params_grad_none": [], "params_grad_nonfi ...`
- **PASS (not required)** after_adamw_steps: deeper recurrence 16 loops (supplementary)  
  criterion: finite loss/logits and gradients  
  observed: `{"loss": 3.6644372940063477, "loss_finite": true, "log_ppl_finite": true, "logits_finite": true, "logits_abs_max": 3.9775516986846924, "params_with_grad": 43, "params_total": 43, "params_grad_none": [], "params_grad_nonf ...`
- **PASS (not required)** after_adamw_steps: deeper recurrence 32 loops (supplementary)  
  criterion: finite loss/logits and gradients  
  observed: `{"loss": 3.6644372940063477, "loss_finite": true, "log_ppl_finite": true, "logits_finite": true, "logits_abs_max": 3.9775514602661133, "params_with_grad": 43, "params_total": 43, "params_grad_none": [], "params_grad_nonf ...`

### 3. Backward reaches shared core and injection — PASS

- **PASS** init: injection parameters A_log, dt_bias, B receive non-zero finite gradients  
  criterion: 3 parameters, each grad norm > 0 and finite  
  observed: `{"transformer.adapter.A_log": 0.04519423842430115, "transformer.adapter.dt_bias": 0.017036737874150276, "transformer.adapter.B": 0.591317892074585}`
- **PASS** init: gradients reach the shared recurrent core  
  criterion: every core attn.c_proj / mlp.proj weight has a non-zero finite gradient (other core weights sit behind these zero-initialised projections)  
  observed: `{"transformer.core_block.0.attn.c_proj.weight": 0.4944508671760559, "transformer.core_block.0.mlp.proj.weight": 0.36136725544929504, "transformer.core_block.1.attn.c_proj.weight": 0.28157666325569153, "transformer.core_b ...`
- **PASS** init: gradient arrives at every with-grad loop iteration  
  criterion: grad hooks fire for iterations [4, 5, 6, 7] only, each norm > 0 and finite  
  observed: `{"iteration_to_state_grad_norm": {"4": 0.004740195814520121, "5": 0.010599398985505104, "6": 0.023700978606939316, "7": 0.052997004240751266}}`
- **PASS (not required)** init: parameters with all-zero or missing gradient (informational)  
  criterion: at init scaled-zero sets attn.c_proj/mlp.proj to 0, so weights upstream of them get exactly zero gradient  
  observed: `["transformer.prelude.0.norm_1.weight", "transformer.prelude.0.attn.c_q.weight", "transformer.prelude.0.attn.c_k.weight", "transformer.prelude.0.attn.c_v.weight", "transformer.prelude.0.norm_2.weight", "transformer.prelu ...`
- **PASS** after_adamw_steps: injection parameters A_log, dt_bias, B receive non-zero finite gradients  
  criterion: 3 parameters, each grad norm > 0 and finite  
  observed: `{"transformer.adapter.A_log": 0.03950200229883194, "transformer.adapter.dt_bias": 0.018354950472712517, "transformer.adapter.B": 0.41148442029953003}`
- **PASS** after_adamw_steps: gradients reach the shared recurrent core  
  criterion: every shared-core parameter has a non-zero finite gradient  
  observed: `{"transformer.core_block.0.norm_1.weight": 0.003456425853073597, "transformer.core_block.0.attn.c_q.weight": 0.01462308969348669, "transformer.core_block.0.attn.c_k.weight": 0.014932154677808285, "transformer.core_block. ...`
- **PASS** after_adamw_steps: gradient arrives at every with-grad loop iteration  
  criterion: grad hooks fire for iterations [4, 5, 6, 7] only, each norm > 0 and finite  
  observed: `{"iteration_to_state_grad_norm": {"4": 0.003683541901409626, "5": 0.008270234800875187, "6": 0.018594060093164444, "7": 0.04186287522315979}}`
- **PASS** after_adamw_steps: every parameter has a finite gradient  
  criterion: no missing or non-finite gradient  
  observed: `{"missing_or_nonfinite": []}`
- **PASS (not required)** after_adamw_steps: parameters with all-zero or missing gradient (informational)  
  criterion: at init scaled-zero sets attn.c_proj/mlp.proj to 0, so weights upstream of them get exactly zero gradient  
  observed: `[]`

### 4. State norms / changes for 1, 2, 4, 8 loops — PASS

- **PASS** init: loops [1, 2, 4, 8] run with finite states and loss  
  criterion: all states and losses finite  
  observed: `{"1": {"loss": 5.771858215332031, "final_state_norm_mean": 6.438852787017822, "final_delta_norm_mean": 6.440333843231201}, "2": {"loss": 5.776025772094727, "final_state_norm_mean": 9.310083389282227, "final_delta_norm_me ...`
- **PASS** init: native monitoring agrees with hook-measured states  
  criterion: relative difference <= 1e-5 for recurrent_state_norm, recurrent_residual, rel_residual  
  observed: `{"1": {"recurrent_state_norm": 0.0, "recurrent_residual": 0.0, "rel_residual": 0.0}, "2": {"recurrent_state_norm": 0.0, "recurrent_residual": 0.0, "rel_residual": 0.0}, "4": {"recurrent_state_norm": 0.0, "recurrent_resid ...`
- **PASS** init: state threading (iteration j input = iteration j-1 output, C input = final state)  
  criterion: max abs diff exactly 0  
  observed: `{"1": [0.0, 0.0], "2": [0.0, 0.0], "4": [0.0, 0.0], "8": [0.0, 0.0]}`
- **PASS** init: shorter runs are exact prefixes of the 8-loop trajectory  
  criterion: same x0 seed: states of iteration j identical across loop counts (max abs diff 0)  
  observed: `{"1": 0.0, "2": 0.0, "4": 0.0, "8": 0.0}`
- **PASS** init: scaled-zero core is an exact identity, so each state change shrinks by the injection decay  
  criterion: core output == injection output exactly; |delta ratio - decay| <= 1e-5  
  observed: `{"core_output_minus_injection_max_abs_diff": 0.0, "delta_ratio_to_previous": [0.44721360508779606, 0.44721357763428615, 0.4472136133656305, 0.44721359832887086, 0.4472135811024205, 0.4472135775622063, 0.44721351944262944 ...`
- **PASS** after_adamw_steps: loops [1, 2, 4, 8] run with finite states and loss  
  criterion: all states and losses finite  
  observed: `{"1": {"loss": 3.6044998168945312, "final_state_norm_mean": 6.813050270080566, "final_delta_norm_mean": 6.807308673858643}, "2": {"loss": 3.6442439556121826, "final_state_norm_mean": 9.84862232208252, "final_delta_norm_m ...`
- **PASS** after_adamw_steps: native monitoring agrees with hook-measured states  
  criterion: relative difference <= 1e-5 for recurrent_state_norm, recurrent_residual, rel_residual  
  observed: `{"1": {"recurrent_state_norm": 0.0, "recurrent_residual": 0.0, "rel_residual": 0.0}, "2": {"recurrent_state_norm": 0.0, "recurrent_residual": 0.0, "rel_residual": 0.0}, "4": {"recurrent_state_norm": 0.0, "recurrent_resid ...`
- **PASS** after_adamw_steps: state threading (iteration j input = iteration j-1 output, C input = final state)  
  criterion: max abs diff exactly 0  
  observed: `{"1": [0.0, 0.0], "2": [0.0, 0.0], "4": [0.0, 0.0], "8": [0.0, 0.0]}`
- **PASS** after_adamw_steps: shorter runs are exact prefixes of the 8-loop trajectory  
  criterion: same x0 seed: states of iteration j identical across loop counts (max abs diff 0)  
  observed: `{"1": 0.0, "2": 0.0, "4": 0.0, "8": 0.0}`

### 5. Actual DiagonalInjection decay — PASS

- **PASS** init: every channel decays strictly inside (0, 1)  
  criterion: 0 < decay_i < 1 for all channels  
  observed: `{"min": 0.4472135901451111, "max": 0.4472135901451111, "mean": 0.44721361994743347, "std": 3.003791704259129e-08}`
- **PASS** init: native get_spectral_norm / get_contraction_factor match the probed decay  
  criterion: spectral = max(decay), contraction = mean(decay), forward probe = exp(-softplus(dt_bias)*exp(A_log))  
  observed: `{"spectral_norm": 0.4472135901451111, "contraction_factor": 0.44721361994743347, "probe_vs_formula_max_abs_diff": 0.0}`
- **PASS** init: decay equals the Parcae default ssm_decay sqrt(1/5)  
  criterion: |decay - 0.4472136| <= 1e-6 on every channel, A_log = 0, B = I  
  observed: `{"target": 0.4472135954999579, "min": 0.4472135901451111, "max": 0.4472135901451111, "A_log": {"min": 0.0, "max": 0.0}, "dt_mean": 0.8047189712524414, "B_minus_identity_max_abs": 0.0}`
- **PASS** after_adamw_steps: every channel decays strictly inside (0, 1)  
  criterion: 0 < decay_i < 1 for all channels  
  observed: `{"min": 0.4468480348587036, "max": 0.4483002722263336, "mean": 0.4473196864128113, "std": 0.0004522307135630399}`
- **PASS** after_adamw_steps: native get_spectral_norm / get_contraction_factor match the probed decay  
  criterion: spectral = max(decay), contraction = mean(decay), forward probe = exp(-softplus(dt_bias)*exp(A_log))  
  observed: `{"spectral_norm": 0.4483002722263336, "contraction_factor": 0.4473196864128113, "probe_vs_formula_max_abs_diff": 0.0}`
- **PASS** official parcae-small-140m config, DiagonalInjection only: every channel decays strictly inside (0, 1)  
  criterion: 0 < decay_i < 1 for all channels  
  observed: `{"min": 0.4472135901451111, "max": 0.4472135901451111, "mean": 0.4472135603427887, "std": 2.9821745073377315e-08}`
- **PASS** official parcae-small-140m config, DiagonalInjection only: native get_spectral_norm / get_contraction_factor match the probed decay  
  criterion: spectral = max(decay), contraction = mean(decay), forward probe = exp(-softplus(dt_bias)*exp(A_log))  
  observed: `{"spectral_norm": 0.4472135901451111, "contraction_factor": 0.4472135603427887, "probe_vs_formula_max_abs_diff": 0.0}`
- **PASS** official parcae-small-140m config, DiagonalInjection only: decay equals the Parcae default ssm_decay sqrt(1/5)  
  criterion: |decay - 0.4472136| <= 1e-6 on every channel, A_log = 0, B = I  
  observed: `{"target": 0.4472135954999579, "min": 0.4472135901451111, "max": 0.4472135901451111, "A_log": {"min": 0.0, "max": 0.0}, "dt_mean": 0.8047189712524414, "B_minus_identity_max_abs": 0.0}`
- **PASS (not required)** after_adamw_steps: decay parameters are trainable (moved from init)  
  criterion: max |decay_after - decay_init| > 0  
  observed: `{"max_abs_change": 0.0010866820812225342}`

### 6. Native no-grad / with-grad loop configuration — PASS

- **PASS** init: forward is identical whatever the no-grad / with-grad split  
  criterion: same x0 seed and 8 loops: loss and logits differ by <= 1e-6 across splits  
  observed: `{"[8, 0]": {"loss": 5.777870178222656, "loss_abs_diff_vs_8_0": 0.0, "logits_max_abs_diff_vs_8_0": 0.0}, "[6, 2]": {"loss": 5.777870178222656, "loss_abs_diff_vs_8_0": 0.0, "logits_max_abs_diff_vs_8_0": 0.0}, "[4, 4]": {"l ...`
- **PASS** init: first n loops run under torch.no_grad, last k with grad enabled  
  criterion: adapter grad_enabled flags = [False]*n + [True]*k; prelude/coda/head always grad-enabled  
  observed: `{"[8, 0]": [false, false, false, false, false, false, false, false], "[6, 2]": [false, false, false, false, false, false, true, true], "[4, 4]": [false, false, false, false, true, true, true, true], "[2, 6]": [false, fal ...`
- **PASS** init: backward reaches exactly the with-grad iterations  
  criterion: state grad hooks fire for iterations n..n+k-1 only  
  observed: `{"[8, 0]": [], "[6, 2]": [6, 7], "[4, 4]": [4, 5, 6, 7], "[2, 6]": [2, 3, 4, 5, 6, 7], "[0, 8]": [0, 1, 2, 3, 4, 5, 6, 7]}`
- **PASS** init: truncation is an exact stop-gradient at loop n  
  criterion: state gradients on the shared with-grad iterations agree within 1e-6  
  observed: `{"iterations_4_to_7_rel_diff_(4,4)_vs_(0,8)": {"4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0}}`
- **PASS** init: (8, 0) all-no-grad recurrence leaves prelude/injection/core without gradient  
  criterion: no gradient before C; C, coda, ln_f and tied wte/lm_head still get gradients  
  observed: `{"pre_C_params_with_nonzero_grad": [], "post_C_group_grad_norms": {"wte": 1.000969409942627, "C": 0.9723554253578186, "coda": 0.5819389659458453, "ln_f": 0.08879893273115158}}`
- **PASS** init: with k > 0 gradients reach prelude, injection and core  
  criterion: group grad norms > 0 for (4, 4) and (0, 8)  
  observed: `{"[4, 4]": {"prelude": 4.6458250802470555, "adapter": 0.5932871304113005, "core_block": 0.7670899131318115}, "[0, 8]": {"prelude": 4.831659055953551, "adapter": 0.6169985256228531, "core_block": 0.7977753899719506}}`
- **PASS** init: backprop depth k changes the gradient ((4, 4) vs (0, 8))  
  criterion: relative gradient difference > 1e-6 for adapter and core  
  observed: `{"adapter": 0.03843638673424721, "core_block": 0.03846462815999985}`
- **PASS** after_adamw_steps: forward is identical whatever the no-grad / with-grad split  
  criterion: same x0 seed and 8 loops: loss and logits differ by <= 1e-6 across splits  
  observed: `{"[8, 0]": {"loss": 3.6642844676971436, "loss_abs_diff_vs_8_0": 0.0, "logits_max_abs_diff_vs_8_0": 0.0}, "[6, 2]": {"loss": 3.6642844676971436, "loss_abs_diff_vs_8_0": 0.0, "logits_max_abs_diff_vs_8_0": 0.0}, "[4, 4]": { ...`
- **PASS** after_adamw_steps: first n loops run under torch.no_grad, last k with grad enabled  
  criterion: adapter grad_enabled flags = [False]*n + [True]*k; prelude/coda/head always grad-enabled  
  observed: `{"[8, 0]": [false, false, false, false, false, false, false, false], "[6, 2]": [false, false, false, false, false, false, true, true], "[4, 4]": [false, false, false, false, true, true, true, true], "[2, 6]": [false, fal ...`
- **PASS** after_adamw_steps: backward reaches exactly the with-grad iterations  
  criterion: state grad hooks fire for iterations n..n+k-1 only  
  observed: `{"[8, 0]": [], "[6, 2]": [6, 7], "[4, 4]": [4, 5, 6, 7], "[2, 6]": [2, 3, 4, 5, 6, 7], "[0, 8]": [0, 1, 2, 3, 4, 5, 6, 7]}`
- **PASS** after_adamw_steps: truncation is an exact stop-gradient at loop n  
  criterion: state gradients on the shared with-grad iterations agree within 1e-6  
  observed: `{"iterations_4_to_7_rel_diff_(4,4)_vs_(0,8)": {"4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0}}`
- **PASS** after_adamw_steps: (8, 0) all-no-grad recurrence leaves prelude/injection/core without gradient  
  criterion: no gradient before C; C, coda, ln_f and tied wte/lm_head still get gradients  
  observed: `{"pre_C_params_with_nonzero_grad": [], "post_C_group_grad_norms": {"wte": 0.9533544778823853, "C": 0.7037695646286011, "coda": 0.39118982433911226, "ln_f": 0.21768614649772644}}`
- **PASS** after_adamw_steps: with k > 0 gradients reach prelude, injection and core  
  criterion: group grad norms > 0 for (4, 4) and (0, 8)  
  observed: `{"[4, 4]": {"prelude": 3.040367151916132, "adapter": 0.4137834464326877, "core_block": 0.5595855437692172}, "[0, 8]": {"prelude": 3.1640779818889277, "adapter": 0.43053951779158833, "core_block": 0.5831324916763215}}`
- **PASS** after_adamw_steps: backprop depth k changes the gradient ((4, 4) vs (0, 8))  
  criterion: relative gradient difference > 1e-6 for adapter and core  
  observed: `{"adapter": 0.040008943527936935, "core_block": 0.04220043867826462}`
- **PASS** native config of parcae-small-140m is kept  
  criterion: mean_recurrence 8, mean_backprop_depth 4, poisson-truncated-full, per-sequence  
  observed: `{"mean_recurrence": 8, "mean_backprop_depth": 4, "sampling_scheme": "poisson-truncated-full", "recurrent_iteration_method": "per-sequence", "activation_checkpoint_impl": "per-iteration"}`
- **PASS** per-sequence sampler (_sample_batch_depths): total ~ clamp(Poisson(t+s), 1), k = min(total, s), n = total - k  
  criterion: 0 rule violations over 1000 steps x batch 4; same step resamples identically; |mean total - 8| <= 0.3  
  observed: `{"samples": 4000, "mean_no_grad_n": 4.07875, "mean_with_grad_k": 3.94275, "mean_total": 8.0215, "max_k": 4, "min_total": 1, "max_total": 19, "rule_violations": 0, "nondeterministic_resamples": 0, "total_histogram": {"1": ...`
- **PASS (not required)** per-batch sampler (randomized_iteration_sampler): n = clamp(Poisson(t+s), 1), k = min(n, s)  
  criterion: 0 rule violations; deterministic per step; |mean n - 8| <= 0.5 (not the 140M mode)  
  observed: `{"samples": 1000, "mean_no_grad_n": 7.834, "mean_with_grad_k": 3.939, "mean_total": 11.773, "max_k": 4, "min_total": 2, "max_total": 20, "rule_violations": 0, "nondeterministic_resamples": 0, "total_histogram": {"2": 3,  ...`
- **PASS (not required)** eval mode randomized_iteration_sampler returns (mean_recurrence, 0)  
  criterion: [8, 0]  
  observed: `[8, 0]`
- **PASS** native sampled train forward (no num_steps_pair): per-sample torch.where gating matches the sampled (n, k)  
  criterion: 0 gating mismatches; max(n) no-grad calls then max(k) grad calls; finite loss/grads; core grad > 0  
  observed: `{"model_step": 0, "per_sample_n": [2, 5, 0, 3], "per_sample_k": [4, 4, 3, 4], "loop_calls": 9, "expected_loop_calls": 9, "grad_flags": [false, false, false, false, false, true, true, true, true], "gating_mismatches": 0,  ...`
- **PASS (not required)** observation: eval mode without num_steps_pair still samples per-sequence depths  
  criterion: informational only  
  observed: `{"loop_calls": 9, "model_step": 0, "note": "upstream eval passes num_steps_pair=[mean_recurrence, 0] explicitly (receval/tasks/core_eval.py, scripts/train.py)"}`
- **PASS (not required)** supplementary: gradient_checkpointing (per-iteration) gives the same loss and grads  
  criterion: loss diff <= 1e-6, grad max abs diff <= 1e-5  
  observed: `{"loss_plain": 3.6642844676971436, "loss_checkpointed": 3.6642844676971436, "grad_max_abs_diff": 0.0}`
- **PASS (not required)** supplementary: per-batch mode native forward runs n no-grad then k grad loops  
  criterion: flags = [False]*n + [True]*k, finite loss  
  observed: `{"model_step": 3, "n": 8, "k": 4, "grad_flags": [false, false, false, false, false, false, false, false, true, true, true, true], "loss": 3.664430856704712}`

## Failures

- None.

## NOT TESTED

- GPU / FlashAttention-3 path (CPU run uses Parcae's SDPA fallback); P1-C scope.
- Fused heads `cce`, `hhe`, `full-triton` (need Triton/CUDA); the official 140M default `pytorch` head is used.
- `per-token` recurrent_iteration_method (not the 140M setting).
- axonn tensor parallel, torch.compile, bf16 autocast, distributed sampler seeding, KV-cache generation.
- The full 140M model forward/backward and any training (excluded by the P1-B scope).
- Pretrained weights (excluded; all weights are random).

## Observations about upstream behaviour (not failures)

- `poisson-truncated-full` means different totals per mode: per-sequence draws a total (mean 8.021) and splits it as k = min(total, 4); per-batch draws n (mean 7.834) and adds k = min(n, 4), mean total 11.773.
- In `per-sequence`/`per-token` mode, `iterate_forward` samples depths whenever `num_steps_pair` is None, also in eval mode; upstream eval code passes `num_steps_pair=[mean_recurrence, 0]` explicitly, which P1-B mirrors.
- `value_embeds` (and attention `ve_gate`) are plain `torch.nn` modules not re-initialised by `reset_parameters`; observed value-embedding init std: value_embeds.1.weight 1.001167, value_embeds.3.weight 1.001245.
- `scaled-zero` zero-initialises every attention `c_proj` and MLP `proj`, so at init every block is an exact identity and q/k/v/fc/norm/ve_gate weights and the value-embedding tables get exactly zero gradient; they receive gradient after the first optimiser step (see check 3).

## Reproducibility

Compared with the previous run finished 2026-10-22T11:32:13Z (`run_meta` excluded):

| file | identical | sha256 (canonical, this run) |
|---|---|---|
| `P1_B_ENVIRONMENT.json` | True | `ecc64e1d4e7555b7a63890a89c0373c4abf3f69fdc529e81616dd0adbc72251b` |
| `P1_B_FORWARD_BACKWARD.json` | True | `144758723a70b4f2996bcd0184fe461c912d2a2618da8679200ac5dba23de9ba` |
| `P1_B_STATE_DIAGNOSTICS.json` | True | `f27ded6e64186f847e5b25c2364bb9cb454e26a4ece3623101bd57703cfd829e` |
| `P1_B_GRADIENT_DIAGNOSTICS.json` | True | `5280961c946853c0125fa6c832a4b68e7ba1aa884b75aa2a5c7c0d806871174d` |

A re-run on another machine or package set changes `P1_B_ENVIRONMENT.json` by design; the criterion here is a re-run in the same environment.

Re-run from the OpenMythos repository root (CPU only, about 10 s):

```bash
bash research/mini_mythos/scripts/p1b_setup_env.sh ./venv_p1b ./parcae
./venv_p1b/bin/python -I research/mini_mythos/scripts/p1b_parcae_cpu_check.py \
    --parcae-dir ./parcae --out-dir /tmp/p1b_rerun \
    --reference-dir research/mini_mythos/docs/p1b
```

## Files

- `research/mini_mythos/docs/p1b/P1_B_ENVIRONMENT.json`
- `research/mini_mythos/docs/p1b/P1_B_FORWARD_BACKWARD.json`
- `research/mini_mythos/docs/p1b/P1_B_STATE_DIAGNOSTICS.json`
- `research/mini_mythos/docs/p1b/P1_B_GRADIENT_DIAGNOSTICS.json`
- `research/mini_mythos/docs/p1b/P1_B_RESULT.md`
