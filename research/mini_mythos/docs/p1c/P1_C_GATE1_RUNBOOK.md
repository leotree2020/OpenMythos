# P1-C Gate 1 Manual Execution Runbook (RunPod A100 80GB)

**This agent cannot launch or access RunPod.** User must perform the steps.

## Pre-flight

1. Confirm live price on https://www.runpod.io/pricing for A100 80GB (single).
2. Set billing alert at 1,000 JPY and hard stop at 5,000 JPY cumulative.
3. Choose Community Cloud if cheaper and acceptable; otherwise Secure.
4. Select image with recent CUDA + PyTorch 2.4+ / Python 3.11 (or install after).

## Steps

1. Launch pod, note instance ID, GPU name, driver, CUDA version.
2. SSH in.
3. `git clone https://github.com/sandyresearch/parcae.git && cd parcae && git checkout 69284c13746e849104f738d6d1a347b1f457df76`
4. Install: `pip install -e .` + requirements (record exact versions: torch, lightning, etc.).
5. Run env check: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.__version__)"`
6. Construct model from random init using official config (or `parcae_lm.create_model("parcae-small-140m")`).
7. Minimal forward + backward on synthetic tokens (fixed seed). Confirm finite loss / grads, grads reach recurrent core and DiagonalInjection.
8. Record: peak VRAM (`nvidia-smi` or torch), step time, tokens/sec.
9. If OOM: reduce micro_batch only; document change. Do not alter architecture.
10. Stop pod immediately after, confirm billing stopped in dashboard.
11. Write `P1_C_GATE1_GPU_REPORT.md` with all measured numbers and actual cost.

## Deliverables back to GitHub

Push report + logs (no secrets, no large ckpts) to this branch or a linked commit.

**Do not proceed to Gate 2 until ChatGPT reviews Gate 1.**
