"""13-gram hashing for overlap/contamination checks (numpy only).

A 13-gram is 13 consecutive token ids. Each is mapped to a 64-bit polynomial hash; collisions
are negligible at our scale (~5e7 n-grams). N-grams that would span two training documents
are excluded, because packing artifacts are not real text.
"""
import numpy as np

N = 13
_BASE = np.uint64(0x9E3779B97F4A7C15)   # odd 64-bit constant; arithmetic wraps mod 2**64


def hashes(tokens, n=N):
    """uint64 hash of every n-gram of a 1-D token array (length len-n+1; empty if too short)."""
    t = np.asarray(tokens)
    m = len(t) - n + 1
    if m <= 0:
        return np.zeros(0, dtype=np.uint64)
    h = np.zeros(m, dtype=np.uint64)
    with np.errstate(over="ignore"):
        for j in range(n):          # in place: keeps peak memory near 3 arrays of m uint64
            h *= _BASE
            h += t[j:j + m].astype(np.uint64)
            h += np.uint64(1)
    return h


def corpus_set(tokens, doc_lengths, n=N):
    """Sorted unique hashes of all n-grams inside single documents of a concatenated corpus."""
    tokens = np.asarray(tokens)
    lengths = np.asarray(doc_lengths, dtype=np.int64)
    if int(lengths.sum()) != len(tokens):
        raise ValueError("doc_lengths do not add up to the token count")
    h = hashes(tokens, n)
    if len(h) == 0:
        return h
    doc = np.repeat(np.arange(len(lengths), dtype=np.int32), lengths)
    inside = doc[:len(h)] == doc[n - 1:n - 1 + len(h)]
    return np.unique(h[inside])


def member(query, sorted_set):
    """Boolean array: which query hashes are in the sorted hash set."""
    query = np.asarray(query, dtype=np.uint64)
    if len(sorted_set) == 0 or len(query) == 0:
        return np.zeros(len(query), dtype=bool)
    idx = np.searchsorted(sorted_set, query)
    idx = np.minimum(idx, len(sorted_set) - 1)
    return sorted_set[idx] == query


def overlap(window_tokens, sorted_set, n=N):
    """(number of window n-grams found, number of n-grams, fraction of tokens covered by a hit)."""
    h = hashes(window_tokens, n)
    hit = member(h, sorted_set)
    covered = np.zeros(len(window_tokens), dtype=bool)
    for i in np.flatnonzero(hit):
        covered[i:i + n] = True
    return int(hit.sum()), len(h), float(covered.mean()) if len(window_tokens) else 0.0
