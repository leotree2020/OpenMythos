"""Data-only, corpus-bound article partition. No automatic semantic decisions."""
import hashlib
import json


class BoundaryStop(Exception):
    def __init__(self, status, reason, actual=None):
        super().__init__(reason)
        self.status, self.reason, self.actual = status, reason, actual


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def is_broad_candidate(raw):
    stripped = raw.strip()
    return stripped.startswith("=") or stripped.endswith("=")


def has_single_equals_syntax(raw):
    stripped = raw.strip()
    return stripped.startswith("=") and stripped.endswith("=") and stripped.count("=") == 2


def _blocked(reason, actual=None):
    raise BoundaryStop("BLOCKED", reason, actual)


def _valid_sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def prepare_partition(rows, ledger, corpus_sha256):
    """Partition only from explicit ledger decisions; preserve every raw row.

    The corpus SHA identifies the original artifact (for example Parquet), while
    rows_sha256 separately binds this exact decoded list of strings. Neither an
    isolated formula nor a blank delimiter supplies a semantic title decision.
    """
    if not isinstance(rows, list) or any(not isinstance(row, str) for row in rows):
        raise BoundaryStop("FAIL", "Rows must be a list of strings")
    if not _valid_sha(corpus_sha256) or not isinstance(ledger, dict):
        _blocked("Invalid corpus identity or missing ledger")
    rows_sha = sha256(canonical(rows))
    if (type(ledger.get("row_count")) is not int or ledger["row_count"] != len(rows)
            or ledger.get("corpus_sha256") != corpus_sha256 or ledger.get("rows_sha256") != rows_sha):
        _blocked("Ledger does not bind the exact corpus and rows",
                 {"row_count": len(rows), "corpus_sha256": corpus_sha256, "rows_sha256": rows_sha})
    decisions = ledger.get("decisions")
    if not isinstance(decisions, list):
        _blocked("Ledger decisions must be a list")
    candidate_rows = {index for index, raw in enumerate(rows) if is_broad_candidate(raw)}
    by_row = {}
    for decision in decisions:
        if not isinstance(decision, dict):
            _blocked("Ledger decision must be an object")
        index = decision.get("row")
        if type(index) is not int or index not in candidate_rows:
            _blocked("Unknown or out-of-scope ledger row", index)
        if index in by_row:
            _blocked("Duplicate ledger row", index)
        raw = rows[index]
        if decision.get("row_sha256") != sha256(raw.encode("utf-8")) or decision.get("title") != raw.strip():
            _blocked("Ledger row identity changed", index)
        if not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
            _blocked("Ledger decision lacks a reason", index)
        outcome = decision.get("decision")
        if outcome not in ("ACCEPT_TITLE", "BODY"):
            _blocked("Unresolved or unknown ledger decision", {"row": index, "decision": outcome})
        if outcome == "ACCEPT_TITLE" and not has_single_equals_syntax(raw):
            _blocked("Accepted title violates the frozen single-equals syntax", index)
        by_row[index] = outcome
    if set(by_row) != candidate_rows:
        _blocked("Unreviewed broad candidates", sorted(candidate_rows - set(by_row)))
    headers = sorted(index for index, outcome in by_row.items() if outcome == "ACCEPT_TITLE")
    if not headers:
        _blocked("No reviewed article title")
    leading_rows = list(range(headers[0]))
    nonblank_leading = [index for index in leading_rows if rows[index].strip()]
    if nonblank_leading:
        _blocked("Leading region contains unassigned nonempty content", nonblank_leading)

    articles, roles = [], [None] * len(rows)
    reconstructed = [None] * len(rows)

    def assign(index, role, source_key, heading_row, raw):
        if roles[index] is not None or reconstructed[index] is not None:
            raise BoundaryStop("FAIL", "Overlapping source row assignment", index)
        roles[index] = {"row": index, "role": role, "source_article_key": source_key,
                        "heading_row": heading_row}
        reconstructed[index] = raw

    for index in leading_rows:
        assign(index, "LEADING", None, None, rows[index])
    source_keys, article_ids, body_hashes = {}, {}, {}
    for ordinal, heading_row in enumerate(headers):
        end = headers[ordinal + 1] if ordinal + 1 < len(headers) else len(rows)
        title = rows[heading_row].strip()
        body_rows = list(range(heading_row + 1, end))
        parts = [rows[index] for index in body_rows]
        body = "".join(parts)
        source_key = sha256(canonical({"corpus_sha256": corpus_sha256,
                                      "heading_row": heading_row, "title": title}))
        article_id = sha256((title + "\n" + body).encode("utf-8"))
        text_sha = sha256(body.encode("utf-8"))
        for name, value, seen in (("source identity", source_key, source_keys),
                                  ("ranking identity", article_id, article_ids),
                                  ("body content", text_sha, body_hashes)):
            if value in seen:
                raise BoundaryStop("FAIL", "Duplicate " + name,
                                   {"first_heading_row": seen[value], "second_heading_row": heading_row,
                                    "sha256": value})
            seen[value] = heading_row
        article = {"heading_row": heading_row, "heading_text": rows[heading_row], "title": title,
                   "body_rows": body_rows, "parts": parts, "source_article_key": source_key,
                   "article_id": article_id, "text_sha256": text_sha}
        articles.append(article)
        assign(heading_row, "HEADING", source_key, heading_row, article["heading_text"])
        for index, raw in zip(body_rows, parts):
            assign(index, "BODY", source_key, heading_row, raw)

    if (any(role is None for role in roles) or reconstructed != rows
            or "".join(reconstructed).encode("utf-8") != "".join(rows).encode("utf-8")):
        raise BoundaryStop("FAIL", "Exact row and UTF8 reconstruction failed")
    return {"corpus_sha256": corpus_sha256, "rows_sha256": rows_sha,
            "corpus_utf8_sha256": sha256("".join(rows).encode("utf-8")),
            "row_count": len(rows), "candidate_rows": sorted(candidate_rows),
            "leading_rows": leading_rows, "leading_parts": [rows[index] for index in leading_rows],
            "articles": articles, "row_roles": roles}
