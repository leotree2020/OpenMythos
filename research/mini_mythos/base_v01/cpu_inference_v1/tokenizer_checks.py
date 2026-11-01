"""Frozen-input tokenizer checks and descriptive continuation quality screens.

This module imports only the standard library. It does not load a tokenizer or
model, generate tokens, alter tokenizer settings, or assess semantic coherence.
Source-file byte hashes are a separate runner gate before these functions run.
"""

from collections import Counter
from collections.abc import Mapping


VOCAB_SIZE = 32768
MAX_PROMPT_TOKENS = 48
MAX_NEW_TOKENS = 64
SEED_BASE = 731000
EOS_ID = 1
SPECIAL_TOKENS = {0: "<|bos|>", 1: "<|eos|>", 2: "<|pad|>"}


class TokenizerStop(Exception):
    """A stopping engineering/input failure, with serializable partial evidence."""

    def __init__(self, status, reason, actual):
        if status not in ("BLOCKED", "FAIL"):
            raise ValueError("TokenizerStop status must be BLOCKED or FAIL")
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.actual = actual


def _require(condition, status, reason, actual):
    if not condition:
        raise TokenizerStop(status, reason, actual)


def _document_rows(document, key, expected_count):
    if isinstance(document, Mapping):
        _require(document.get("experiment") == "MYTHOS-BASELINE-B1"
                 and document.get("frozen") == "2026-10-31", "BLOCKED",
                 "frozen input document metadata differs", {"document": key})
        rows = document.get(key)
    else:
        rows = document
    _require(isinstance(rows, list) and len(rows) == expected_count, "BLOCKED",
             "frozen input count or container differs",
             {"document": key, "expected_count": expected_count,
              "actual_count": len(rows) if isinstance(rows, list) else None})
    return rows


def _valid_ids(ids):
    return (isinstance(ids, (list, tuple))
            and all(type(token) is int and 0 <= token < VOCAB_SIZE for token in ids))


def _encode(tokenizer, text, label):
    try:
        encoded = tokenizer.encode(text, add_special_tokens=False)
        ids = list(encoded.ids)
        attention = list(encoded.attention_mask)
        special_mask = list(encoded.special_tokens_mask)
        overflowing = len(encoded.overflowing)
    except Exception as exc:
        raise TokenizerStop("BLOCKED", "tokenizer encoding could not be inspected",
                            {"label": label, "error": repr(exc)}) from exc
    actual = {"label": label, "ids": ids, "attention_mask": attention,
              "special_tokens_mask": special_mask, "overflow_count": overflowing,
              "add_special_tokens": False}
    _require(_valid_ids(ids), "FAIL", "encoded token IDs are invalid", actual)
    _require(len(attention) == len(ids) and all(value == 1 for value in attention),
             "FAIL", "encoding contains padding or invalid attention mask", actual)
    _require(len(special_mask) == len(ids) and all(value == 0 for value in special_mask),
             "FAIL", "encoding inserted special tokens", actual)
    _require(overflowing == 0, "FAIL", "encoding was truncated", actual)
    return ids


def _decode(tokenizer, ids):
    try:
        text = tokenizer.decode(list(ids), skip_special_tokens=False)
        if not isinstance(text, str):
            return None, "tokenizer.decode returned a non-string"
        return text, None
    except Exception as exc:
        return None, repr(exc)


def validate_tokenizer(tokenizer, tokenizer_json, probes, prompts):
    """Validate fixed tokenizer and inputs; return rows suitable for generation.

    ``probes`` and ``prompts`` accept the actual frozen JSON document wrappers
    (``probes`` / ``prompts`` list fields), or those already-extracted lists.
    The runner must separately verify the frozen source-file hashes.
    On failure, ``TokenizerStop.actual`` includes the accumulated report.
    """
    report = {"status": "NOT TESTED", "identity": {}, "probe_rows": [],
              "prompts": [], "expected_probe_count": 32, "expected_prompt_count": 12,
              "encode_add_special_tokens": False, "decode_skip_special_tokens": False}
    try:
        _require(isinstance(tokenizer_json, Mapping), "BLOCKED",
                 "tokenizer JSON is not an object", {})
        model = tokenizer_json.get("model")
        _require(isinstance(model, Mapping) and model.get("type") == "BPE", "BLOCKED",
                 "tokenizer model must be BPE", {})
        vocab = model.get("vocab")
        added = tokenizer_json.get("added_tokens")
        _require(isinstance(vocab, Mapping) and isinstance(added, list), "BLOCKED",
                 "tokenizer vocabulary or added_tokens is invalid", {})
        _require(all(isinstance(text, str) and type(idx) is int for text, idx in vocab.items()),
                 "BLOCKED", "tokenizer vocabulary has invalid entries", {})
        union = dict(vocab)
        added_ids, added_texts, special = set(), set(), {}
        for entry in added:
            _require(isinstance(entry, Mapping), "BLOCKED", "invalid added token entry", {})
            idx, text = entry.get("id"), entry.get("content")
            _require(type(idx) is int and isinstance(text, str), "BLOCKED",
                     "added token has invalid ID or content", {})
            _require(idx not in added_ids and text not in added_texts, "BLOCKED",
                     "duplicate added token", {"id": idx, "content": text})
            _require(text not in union or union[text] == idx, "BLOCKED",
                     "added token conflicts with vocabulary", {"id": idx, "content": text})
            added_ids.add(idx)
            added_texts.add(text)
            union[text] = idx
            if entry.get("special") is True:
                special[idx] = text
        _require(len(union) == VOCAB_SIZE and sorted(union.values()) == list(range(VOCAB_SIZE)),
                 "BLOCKED", "vocabulary IDs must be exactly 0 through 32767",
                 {"union_tokens": len(union), "unique_ids": len(set(union.values()))})
        _require(special == SPECIAL_TOKENS, "BLOCKED", "special tokens differ",
                 {"specials_by_id": {str(key): value for key, value in special.items()}})
        decoder = tokenizer_json.get("decoder")
        _require(tokenizer_json.get("normalizer") is None
                 and tokenizer_json.get("post_processor") is None
                 and tokenizer_json.get("truncation") is None
                 and tokenizer_json.get("padding") is None
                 and isinstance(decoder, Mapping) and decoder.get("type") == "ByteLevel",
                 "BLOCKED", "tokenizer components differ from frozen contract", {})
        _require(tokenizer.padding is None and tokenizer.truncation is None, "BLOCKED",
                 "runtime tokenizer padding or truncation is enabled", {})
        loaded_vocab = tokenizer.get_vocab(with_added_tokens=True)
        _require(loaded_vocab == union and tokenizer.get_vocab_size(with_added_tokens=True) == VOCAB_SIZE,
                 "BLOCKED", "loaded tokenizer vocabulary differs from tokenizer JSON", {})
        for idx, text in SPECIAL_TOKENS.items():
            _require(tokenizer.token_to_id(text) == idx and tokenizer.id_to_token(idx) == text,
                     "BLOCKED", "loaded special token mapping differs", {"id": idx, "content": text})
        report["identity"] = {
            "model_type": "BPE", "vocab_size": VOCAB_SIZE,
            "loaded_vocabulary_matches_json": True,
            "specials_by_id": {str(key): value for key, value in SPECIAL_TOKENS.items()},
            "padding": None, "truncation": None, "normalizer": None,
            "post_processor": None, "decoder_type": "ByteLevel"}

        probe_specs = _document_rows(probes, "probes", 32)
        prompt_specs = _document_rows(prompts, "prompts", 12)
        _require(all(isinstance(text, str) for text in probe_specs), "BLOCKED",
                 "probe text must be a string", {})
        _require(all(isinstance(row, Mapping) and type(row.get("id")) is int
                     and isinstance(row.get("text"), str) for row in prompt_specs),
                 "BLOCKED", "prompt entry is invalid", {})
        _require([row["id"] for row in prompt_specs] == list(range(1, 13)), "BLOCKED",
                 "prompt IDs or order differ from 1 through 12", {})

        for index, text in enumerate(probe_specs):
            ids = _encode(tokenizer, text, "probe:%d" % index)
            decoded, decode_error = _decode(tokenizer, ids)
            row = {"index": index, "text": text, "ids": ids, "in_range": True,
                   "decoded": decoded, "decode_error": decode_error,
                   "round_trip_equal": decoded == text and decode_error is None}
            report["probe_rows"].append(row)
            _require(row["round_trip_equal"], "FAIL", "tokenizer probe round trip differs", row)

        for spec in prompt_specs:
            idx, text = spec["id"], spec["text"]
            _require(bool(text), "BLOCKED", "empty prompt text", {"id": idx})
            ids = _encode(tokenizer, text, "prompt:%d" % idx)
            decoded, decode_error = _decode(tokenizer, ids)
            row = {"id": idx, "text": text, "input_ids": ids, "seed": SEED_BASE + idx,
                   "input_token_count": len(ids), "round_trip_equal": decoded == text,
                   "decoded": decoded, "decode_error": decode_error}
            report["prompts"].append(row)
            _require(0 < len(ids) <= MAX_PROMPT_TOKENS, "BLOCKED",
                     "prompt token count must be within 1 through 48; no truncation", row)
            _require(not any(token in SPECIAL_TOKENS for token in ids), "FAIL",
                     "fixed plain-text prompt unexpectedly contains a special token", row)
            _require(decode_error is None and decoded == text, "FAIL",
                     "prompt round trip differs", row)
        report.update(status="PASS", all_probes_round_trip=True,
                      all_prompt_ids_in_range=True, all_prompts_round_trip=True)
        return report
    except TokenizerStop as exc:
        report["status"] = exc.status
        report["stop"] = {"reason": exc.reason, "actual": exc.actual}
        raise TokenizerStop(exc.status, exc.reason, report) from exc
    except Exception as exc:
        report["status"] = "BLOCKED"
        report["stop"] = {"reason": "tokenizer validation could not be completed", "error": repr(exc)}
        raise TokenizerStop("BLOCKED", "tokenizer validation could not be completed", report) from exc


def compute_quality(tokenizer, promptrow, full_generated_ids):
    """Describe all 64 raw tokens and the pre-EOS continuation without cleaning.

    ``full_generated_ids`` is the flat full sequence, including the prompt.
    A malformed generation is an engineering FAIL. A failed automatic quality
    screen is an ordinary recorded outcome and never raises TokenizerStop.
    Coherence and factual/code correctness are deliberately not inferred here.
    """
    _require(isinstance(promptrow, Mapping), "BLOCKED", "prompt row is not an object", {})
    _require(type(promptrow.get("id")) is int and 1 <= promptrow["id"] <= 12
             and isinstance(promptrow.get("text"), str) and bool(promptrow["text"])
             and type(promptrow.get("seed")) is int
             and promptrow["seed"] == SEED_BASE + promptrow["id"],
             "BLOCKED", "prompt row identity or frozen seed is invalid", {})
    prompt_ids = promptrow.get("input_ids")
    _require(_valid_ids(prompt_ids) and 0 < len(prompt_ids) <= MAX_PROMPT_TOKENS,
             "BLOCKED", "prompt row has invalid input IDs", {"id": promptrow.get("id")})
    _require(_valid_ids(full_generated_ids), "FAIL", "generated IDs are invalid",
             {"id": promptrow.get("id")})
    full_ids = list(full_generated_ids)
    _require(len(full_ids) == len(prompt_ids) + MAX_NEW_TOKENS, "FAIL",
             "generation did not return exactly 64 new tokens",
             {"id": promptrow.get("id"), "prompt_tokens": len(prompt_ids), "full_tokens": len(full_ids)})
    _require(full_ids[:len(prompt_ids)] == list(prompt_ids), "FAIL",
             "generated sequence does not retain the exact prompt prefix", {"id": promptrow.get("id")})
    raw_ids = full_ids[len(prompt_ids):]
    eos_position = raw_ids.index(EOS_ID) if EOS_ID in raw_ids else None
    effective = raw_ids[:eos_position] if eos_position is not None else list(raw_ids)
    counts = Counter(tuple(effective[i:i + 4]) for i in range(max(0, len(effective) - 3)))
    max_fourgram = max(counts.values(), default=0)
    previous, run, longest = None, 0, 0
    for token in effective:
        run = run + 1 if token == previous else 1
        previous = token
        longest = max(longest, run)
    text, decode_error = _decode(tokenizer, effective)
    raw_text, raw_decode_error = _decode(tokenizer, raw_ids)
    rules = {
        "min_16_new_tokens": len(effective) >= 16,
        "no_4gram_3x": max_fourgram < 3,
        "no_token_run_6": longest < 6,
        "decodes_without_error": decode_error is None,
        "no_u_fffd": text is not None and "\ufffd" not in text,
    }
    return {
        "id": promptrow["id"], "prompt": promptrow["text"],
        "seed": promptrow["seed"], "input_ids": list(prompt_ids),
        "full_generated_ids": full_ids, "raw_new_ids": raw_ids,
        "raw_new_token_count": len(raw_ids), "eos_id": EOS_ID,
        "eos_position": eos_position, "continuation_ids": effective,
        "text_all_64_tokens": raw_text, "raw_decode_error": raw_decode_error,
        "text_continuation": text,
        "generation_structure_status": "PASS",
        "auto": {"passed": all(rules.values()), "rules": rules,
                 "length": len(effective), "max_4gram_count": max_fourgram,
                 "longest_token_run": longest, "decode_error": decode_error,
                 "ends_with_u_fffd_note": bool(text) and text.endswith("\ufffd")},
        "coherence_review": "NOT TESTED",
        "quality_gate": {"required_both_auto_and_coherent": 9, "fixed_prompt_count": 12,
                         "review_type": "AI-assisted, not a human evaluation",
                         "factual_and_code_correctness": "separate descriptive review"},
        "note": "All 64 tokens are retained; quality uses the tokens strictly before the first EOS."
    }
