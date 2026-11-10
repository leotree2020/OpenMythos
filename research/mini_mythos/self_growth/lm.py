"""Model access for the self-growth pilot (Hugging Face transformers; CPU or GPU).

Questions are scored without a judge: the model sees the question with four options and the
probability of the next token being A, B, C or D is read off directly (thinking mode off).
"""
LETTERS = "ABCD"


def load(model_dir, device="cpu", threads=4, dtype="bf16"):
    import torch
    torch.set_num_threads(threads)
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_dir)
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16 if dtype == "bf16" else torch.float32)
    model.to(device)
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    return torch, model, tok


def chat(tok, user, thinking=False):
    return tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True,
                                   enable_thinking=thinking)


def answer_part(text):
    """What the model wrote after its thinking block (the whole text if there is none)."""
    return text.split("</think>")[-1].strip()


def letter_ids(tok):
    ids = [tok.encode(c, add_special_tokens=False) for c in LETTERS]
    if any(len(i) != 1 for i in ids):
        raise SystemExit("the option letters are not single tokens for this tokenizer")
    return [i[0] for i in ids]


def mcq(torch, model, tok, prompts, batch=8):
    """For each prompt: log-probabilities of A, B, C, D as the next token (normalised over the four)."""
    ids = letter_ids(tok)
    out = []
    for k in range(0, len(prompts), batch):
        enc = tok([chat(tok, p) for p in prompts[k:k + batch]], return_tensors="pt", padding=True).to(model.device)
        with torch.no_grad():
            logits = model(**enc).logits[:, -1, :].float()
        out.extend(torch.log_softmax(logits[:, ids], dim=-1).tolist())
    return out


def generate(torch, model, tok, prompts, max_new_tokens=160, batch=4, temperature=0.7, top_p=0.9, seed=0,
             thinking=False):
    """Sampled continuations (deterministic given `seed`). Returns (texts, new tokens generated).
    With thinking=True the model reasons first; the text returned is what follows the thinking block."""
    out, n_new = [], 0
    for k in range(0, len(prompts), batch):
        enc = tok([chat(tok, p, thinking) for p in prompts[k:k + batch]], return_tensors="pt",
                  padding=True).to(model.device)
        torch.manual_seed(seed + k)
        kwargs = dict(max_new_tokens=max_new_tokens, pad_token_id=tok.pad_token_id)
        if temperature > 0:
            kwargs.update(do_sample=True, temperature=temperature, top_p=top_p, top_k=0)
        else:
            kwargs.update(do_sample=False)
        with torch.no_grad():
            gen = model.generate(**enc, **kwargs)
        new = gen[:, enc["input_ids"].shape[1]:]
        n_new += int((new != tok.pad_token_id).sum())
        end_think = tok.convert_tokens_to_ids("</think>")
        for row in new:
            ids = row.tolist()
            if isinstance(end_think, int) and end_think in ids:          # keep what follows the thinking block
                ids = ids[len(ids) - ids[::-1].index(end_think):]
            out.append(answer_part(tok.decode(ids, skip_special_tokens=True)))
    return out, n_new
