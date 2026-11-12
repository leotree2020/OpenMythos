"""Round 3, task 6: reference construction of the candidate-scoring input (protocol 5, as changed in round 3).

The scored sequence for question q and candidate c is

    chat(q) + "The answer is" + " " + c

  chat(q)  = the pinned revision's chat template, one user turn, no system prompt, add_generation_prompt=True,
             enable_thinking=False (written here as a constant; there is no argument to change it);
  "The answer is" = fixed opening of the assistant turn (ANSWER_PREFIX);
  " " + c  = the candidate with one leading space, as in the TRAIN statement; these are the scored tokens.

The candidate is not followed by any further text or special token. Tokenizer only; no model weights.
"""
ANSWER_PREFIX = "The answer is"
ENABLE_THINKING = False


def chat_prompt(tok, question):
    return tok.apply_chat_template([{"role": "user", "content": question}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=ENABLE_THINKING)


def encode(tok, text):
    return tok.encode(text, add_special_tokens=False)


def scoring_input(tok, question, candidate):
    """Return (text, input_ids, start): the scored tokens are input_ids[start:].

    The ids are those of the whole rendered text, tokenized in one call; start is the length of the context
    (everything before " " + candidate). Raises if the context's tokens are not a prefix of the whole
    sequence, i.e. if the candidate would merge with the prefix across the boundary.
    """
    context = chat_prompt(tok, question) + ANSWER_PREFIX
    text = context + " " + candidate
    ids = encode(tok, text)
    ctx_ids = encode(tok, context)
    if ids[:len(ctx_ids)] != ctx_ids:
        raise ValueError("candidate merges with the context at the boundary: %r" % candidate)
    return text, ids, len(ctx_ids)
