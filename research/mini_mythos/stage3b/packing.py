"""Best-fit packing that keeps remainders (Stage 3b).

Same as Stage 2's pack_rows (documents in a seeded random order; each row is filled with the
largest buffered document that still fits), except that when no buffered document fits, the
shortest one is cropped to fill the row and its REMAINDER goes back into the buffer as a new
piece instead of being dropped. No BOS/EOS. Deterministic given `seed`. Only the final partial
row is lost.
"""
import numpy as np


def pack_rows_keep(tokens, lengths, row_len, seed, buffer_size=1000, max_rows=None):
    lengths = np.asarray(lengths, dtype=np.int64)
    starts = np.concatenate([[0], np.cumsum(lengths)[:-1]])
    order = np.random.default_rng(seed).permutation(len(lengths))
    nxt = 0
    buf_s, buf_l = [], []                     # buffered pieces: start offset, length
    rows = []
    while max_rows is None or len(rows) < max_rows:
        row = np.empty(row_len, dtype=np.uint16)
        pos = 0
        while pos < row_len:
            while len(buf_l) < buffer_size and nxt < len(order):
                d = int(order[nxt])
                buf_s.append(int(starts[d]))
                buf_l.append(int(lengths[d]))
                nxt += 1
            if not buf_l:
                return np.stack(rows) if rows else np.zeros((0, row_len), dtype=np.uint16)
            remaining = row_len - pos
            lens = np.asarray(buf_l)
            fits = np.where(lens <= remaining, lens, -1)
            j = int(fits.argmax())
            if fits[j] > 0:
                s, n = buf_s.pop(j), buf_l.pop(j)
                row[pos:pos + n] = tokens[s:s + n]
                pos += n
            else:
                j = int(lens.argmin())
                s, n = buf_s[j], buf_l[j]
                row[pos:] = tokens[s:s + remaining]
                buf_s[j], buf_l[j] = s + remaining, n - remaining    # keep the rest
                pos = row_len
        rows.append(row)
    return np.stack(rows)


def packable_rows(lengths, row_len):
    """Rows pack_rows_keep yields from the whole corpus (independent of the seed)."""
    return int(np.asarray(lengths, dtype=np.int64).sum()) // row_len
