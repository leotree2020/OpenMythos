"""Frozen constants of METRIX E1-PILOT and the ST12 check.

Protocol v1.1: section 0 (identity, seeds, rng_rule, hashing rules), section 3 (template freeze), section 11 ST12;
metrix/e1-pilot/PROTOCOL_FROZEN; Implementation Task Order V1 section 3 items 1 and 2 (Review Gate round 9 ruling):

  ST12 comparison range (1): every hash the current section of PROTOCOL_FROZEN lists. The current section (v1.1)
      lists the data hashes by reference to the table "全部数据哈希" (12 rows: content hashes of facts, anchor texts,
      train_S, candidates and the template set; file-byte hashes of the anchor parquet, the four Qwen tokenizer
      files, the parcae tokenizer.json and eval_sets.jsonl).
  ST12 comparison range (2): the frozen commit is the commit of the current section (v1.1). The protocol file and the
      three JSON are read from that commit with `git cat-file` and their SHA-256 compared with PROTOCOL_FROZEN.

Every protocol value used by the package comes from the bytes of the frozen commit, never from the working tree.
Each value of the 12-row table is also compared with the field of the frozen-commit manifest that holds it.
Any difference raises ST12Error (stop; BLOCKED).

Beyond the two ranges (an open item for Review Gate): the working-tree copies of the four files
are compared with the frozen commit too (load(check_working_tree=True)), so that a one-byte change of a frozen file in
the checkout stops the run (Implementation Task Order V1, section 6 item 10). Line-ending conversion of a checkout
does not count as a change (PROTOCOL_FROZEN: "以 git cat-file 为准(检出时若做换行转换,工作区字节会不同)"): the
protocol and SEARCH_SPACE.json are compared byte for byte after CRLF -> LF; the two manifests, which protocol
section 8 step 1 rewrites, are compared as parsed JSON without the field that step writes (DATA_MANIFEST.json
"files", SPLIT_MANIFEST.json "split_sha256"), as ST12 leaves those fields out.

Section 0 library versions (torch, transformers; "不一致即 BLOCKED") are checked by check_library_versions() (ST8).
"""
import copy
import hashlib
import importlib.metadata
import json
import random
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import ST8Error, ST12Error

PILOT_REL = "metrix/e1-pilot"
PROTOCOL_REL = PILOT_REL + "/METRIX_E1_PROTOCOL.md"
DATA_MANIFEST_REL = PILOT_REL + "/DATA_MANIFEST.json"
SPLIT_MANIFEST_REL = PILOT_REL + "/SPLIT_MANIFEST.json"
SEARCH_SPACE_REL = PILOT_REL + "/SEARCH_SPACE.json"
FROZEN_FILES = (PROTOCOL_REL, DATA_MANIFEST_REL, SPLIT_MANIFEST_REL, SEARCH_SPACE_REL)
PROTOCOL_FROZEN_REL = PILOT_REL + "/PROTOCOL_FROZEN"

# The implementation below must be exactly what the frozen manifest states; load() compares these strings with the
# frozen DATA_MANIFEST.json and raises ST12Error if they differ.
SERIALIZATION_SPEC = "json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)"
JSONL_SPEC = "one canonical object per line, joined by '\\n', one final '\\n'"
RNG_RULE_SPEC = "random.Random(int.from_bytes(sha256(f'{SEED}:{purpose}'.encode('utf-8')).digest()[:8], 'big'))"
TEMPLATE_NORMALIZATION_SPEC = ("replace {E} by <ENTITY> and {A} by <ANSWER>, lowercase, replace every character "
                               "outside [a-z0-9<> ] by a space, collapse spaces")

# Row labels of the PROTOCOL_FROZEN table "全部数据哈希" -> (key used by the package, where the frozen-commit manifest
# holds the same value). The labels are the table's own text; a changed or missing label is an ST12 stop.
QWEN_TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt")
DATA_TABLE_ROWS = {
    "fact(160 条)": ("facts", ("data", "name_generation", "expected_facts_canonical_sha256")),
    "锚文本(512 篇解码文本)": ("anchor_texts", ("data", "anchor_text", "decoded_texts_canonical_sha256")),
    "锚文本源 parquet": ("anchor_parquet", ("data", "anchor_text", "source")),
    "`train_S.jsonl`": ("train_S", ("data", "s_permutation", "expected_train_S_canonical_sha256")),
    "`candidates.json`": ("candidates", ("split", "candidates", "candidate_mapping_sha256")),
    "模板集合(32 个)": ("template_set", ("split", "template_freeze", "template_set_sha256")),
    "Qwen `tokenizer.json`": ("qwen:tokenizer.json", ("data", "model", "tokenizer", "files_sha256", "tokenizer.json")),
    "Qwen `tokenizer_config.json`": ("qwen:tokenizer_config.json",
                                     ("data", "model", "tokenizer", "files_sha256", "tokenizer_config.json")),
    "Qwen `vocab.json`": ("qwen:vocab.json", ("data", "model", "tokenizer", "files_sha256", "vocab.json")),
    "Qwen `merges.txt`": ("qwen:merges.txt", ("data", "model", "tokenizer", "files_sha256", "merges.txt")),
    "parcae 分词器 `tokenizer.json`": ("parcae_tokenizer", ("data", "general_text", "decode_tokenizer_json_sha256")),
    "`eval_sets.jsonl`": ("eval_sets", ("data", "general_text", "source_file_sha256")),
}

HEX64 = re.compile(r"[0-9a-f]{64}")
# Keys of the four content hashes of the generated data (Frozen.content_hashes, check_data_dir).
CONTENT_HASH_KEYS = ("facts", "train_S", "candidates", "anchor_texts")


# ---------------------------------------------------------------------------------------------- hashing (section 0)

def canonical_bytes(obj):
    """Protocol section 0: the canonical serialization of a JSON value, UTF-8."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def jsonl_bytes(rows):
    """Protocol section 0: JSONL = one canonical object per line, joined by '\\n', one final '\\n'."""
    return b"".join(canonical_bytes(r) + b"\n" for r in rows)


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_jsonl(raw):
    """Parse JSONL bytes written by jsonl_bytes(): split on b"\\n" only (not on other Unicode line breaks, which
    json.dumps(ensure_ascii=False) leaves unescaped), one final b"\\n" required for a non-empty file."""
    if raw == b"":
        return []
    if not raw.endswith(b"\n"):
        raise ValueError("JSONL data does not end with a newline")
    return [json.loads(line) for line in raw[:-1].split(b"\n")]


def read_jsonl(path):
    """Parse a JSONL file (file order of the lines)."""
    with open(path, "rb") as fh:
        return parse_jsonl(fh.read())


def rng_rule(seed, purpose):
    """Protocol section 0: random.Random(int.from_bytes(sha256(f"{SEED}:{purpose}".encode("utf-8")).digest()[:8], "big"))."""
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}:{purpose}".encode("utf-8")).digest()[:8], "big"))


def normalize_template(text):
    """Protocol section 3 (template freeze): {E} -> <ENTITY>, {A} -> <ANSWER>, lowercase, every character outside
    [a-z0-9<> ] -> space, collapse spaces."""
    t = text.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    t = re.sub(r"[^a-z0-9<> ]", " ", t)
    return " ".join(t.split())


# ------------------------------------------------------------------------------------------ PROTOCOL_FROZEN parsing

@dataclass(frozen=True)
class FrozenRecord:
    """What the current section of PROTOCOL_FROZEN states."""
    version: str            # e.g. "v1.1"
    commit: str             # full hash of the frozen commit of the current section
    file_sha256: dict       # repository path -> SHA-256 of the file bytes at the frozen commit (4 entries)
    data_sha256: dict       # package key (DATA_TABLE_ROWS) -> SHA-256 (12 entries)
    source_sha256: str      # SHA-256 of the PROTOCOL_FROZEN bytes that were parsed (not frozen anywhere; written
                            # into the experiment record by record.py, stage B)


def _one(matches, what):
    if len(matches) != 1:
        raise ST12Error("PROTOCOL_FROZEN: expected exactly one %s, found %d" % (what, len(matches)))
    return matches[0]


def parse_protocol_frozen(data):
    """Parse PROTOCOL_FROZEN (bytes). Raises ST12Error when the structure is not the one of the frozen file.
    CRLF line endings of a checkout are read as LF (the file is read from the working tree)."""
    text = data.decode("utf-8").replace("\r\n", "\n")
    lines = text.split("\n")
    version = _one([m.group(1) for m in (re.fullmatch(r"当前有效版本[：:]\s*(v[0-9.]+)\s*", ln) for ln in lines) if m],
                   "line '当前有效版本：<version>'")
    heads = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    current = _one([i for i in heads if re.fullmatch(r"## (v[0-9.]+)\(当前有效\)", lines[i])],
                   "section heading '## <version>(当前有效)'")
    if lines[current] != "## %s(当前有效)" % version:
        raise ST12Error("PROTOCOL_FROZEN: the current section heading %r does not name version %s" % (lines[current], version))
    end = min([i for i in heads if i > current], default=len(lines))
    section = lines[current:end]
    commit = _one([m.group(2) for m in (re.fullmatch(r"\| (v[0-9.]+ )?冻结提交\(完整 hash\) \| `([0-9a-f]{40})` \|", ln)
                                        for ln in section) if m], "frozen-commit row in the current section")
    files = {}
    for ln in section:
        m = re.fullmatch(r"([0-9a-f]{64})  (metrix/e1-pilot/[A-Za-z0-9_.-]+)", ln)
        if m:
            if m.group(2) in files:
                raise ST12Error("PROTOCOL_FROZEN: %s listed twice in the current section" % m.group(2))
            files[m.group(2)] = m.group(1)
    if sorted(files) != sorted(FROZEN_FILES):
        raise ST12Error("PROTOCOL_FROZEN: the current section lists %s, expected %s" % (sorted(files), sorted(FROZEN_FILES)))
    # data hashes: the current section refers to the table under '### 全部数据哈希' and states its number of rows
    ref = _one([m.group(1) for m in (re.search(r"“全部数据哈希”表中的 (\d+) 个值", ln) for ln in section) if m],
               "reference to the table '全部数据哈希' in the current section")
    table_at = _one([i for i, ln in enumerate(lines) if ln == "### 全部数据哈希"], "heading '### 全部数据哈希'")
    rows = []
    for ln in lines[table_at + 1:]:
        if ln.startswith("#"):
            break
        m = re.fullmatch(r"\| (.+?) \| `([0-9a-f]{64})` \| .+ \| .+ \|", ln)
        if m:
            rows.append((m.group(1), m.group(2)))
    if len(rows) != int(ref):
        raise ST12Error("PROTOCOL_FROZEN: the table '全部数据哈希' has %d hash rows, the current section says %s" % (len(rows), ref))
    labels = [r[0] for r in rows]
    if sorted(labels) != sorted(DATA_TABLE_ROWS):
        raise ST12Error("PROTOCOL_FROZEN: table rows %s differ from the expected rows %s" % (labels, sorted(DATA_TABLE_ROWS)))
    data_hashes = {DATA_TABLE_ROWS[label][0]: sha for label, sha in rows}
    return FrozenRecord(version=version, commit=commit, file_sha256=files, data_sha256=data_hashes,
                        source_sha256=sha256_hex(data))


# ------------------------------------------------------------------------------------------------- git and loading

def default_repo_root():
    """metrix/e1-pilot/src/metrix_e1/frozen.py -> repository root."""
    return Path(__file__).resolve().parents[4]


def git_blob(repo_root, commit, rel):
    """Bytes of <commit>:<rel> read with `git cat-file blob` (protocol section 11, ST12 range (2))."""
    r = subprocess.run(["git", "-C", str(repo_root), "cat-file", "blob", "%s:%s" % (commit, rel)],
                       capture_output=True, check=False)
    if r.returncode != 0:
        raise ST12Error("cannot read %s:%s with git cat-file (%s)" % (commit, rel, r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout


def _get(obj, path):
    for k in path:
        obj = obj[k]
    return obj


STEP1_FIELDS = {DATA_MANIFEST_REL: "files", SPLIT_MANIFEST_REL: "split_sha256"}


def strip_step1_fields(rel, obj):
    """Copy of a manifest without the field that protocol section 8 step 1 writes (DATA_MANIFEST.json "files",
    SPLIT_MANIFEST.json "split_sha256"; ST12 leaves them out of its comparison). Other files are returned as copies."""
    obj = copy.deepcopy(obj)
    if rel in STEP1_FIELDS and isinstance(obj, dict):
        obj.pop(STEP1_FIELDS[rel], None)
    return obj


def check_library_versions(data_manifest, installed=None):
    """Protocol section 0: the library versions of DATA_MANIFEST.json model.libraries (torch, transformers) must be
    the installed ones (distribution metadata; a local build tag such as "+cu130" is not part of the version);
    otherwise BLOCKED (ST8). `installed` overrides the lookup (tests). Returns {library: installed version}."""
    got = {}
    for lib, want in data_manifest["model"]["libraries"].items():
        try:
            v = installed[lib] if installed is not None else importlib.metadata.version(lib)
        except (KeyError, importlib.metadata.PackageNotFoundError):
            raise ST8Error("library %s is not installed; protocol section 0 requires %s" % (lib, want)) from None
        got[lib] = v
        if v.split("+")[0] != want:
            raise ST8Error("library %s is %s; protocol section 0 requires %s" % (lib, v, want))
    return got


@dataclass
class Frozen:
    """The frozen protocol: everything read from the frozen commit after the ST12 checks of load()."""
    repo_root: Path
    record: FrozenRecord
    blobs: dict             # repository path -> bytes at the frozen commit
    protocol_text: str      # protocol bytes at the frozen commit, decoded (gate thresholds are read from it, stage B)
    data_manifest: dict
    split_manifest: dict
    search_space: dict

    # -- frozen values used by the package
    @property
    def seeds(self):
        return self.data_manifest["seeds"]

    @property
    def templates(self):
        return self.split_manifest["templates"]

    def data_hash(self, key):
        return self.record.data_sha256[key]

    # -- ST12 range (1): file-byte hashes and content hashes
    def check_file(self, path, key):
        """File-byte SHA-256 of `path` against the PROTOCOL_FROZEN value `key` (anchor parquet, tokenizer files,
        eval_sets.jsonl). Returns the hash; raises ST12Error on a mismatch or a missing file."""
        path = Path(path)
        if not path.is_file():
            raise ST12Error("%s: file %s not found" % (key, path))
        got = file_sha256(path)
        if got != self.data_hash(key):
            raise ST12Error("%s: file %s has sha256 %s, frozen value %s" % (key, path, got, self.data_hash(key)))
        return got

    def check_content(self, key, got):
        """A content hash computed by the caller against the PROTOCOL_FROZEN value `key`."""
        if got != self.data_hash(key):
            raise ST12Error("%s: content sha256 %s, frozen value %s" % (key, got, self.data_hash(key)))
        return got

    def content_hashes(self, data_dir):
        """Content hashes of the four generated files that have frozen values, computed as the protocol says:
        facts (2.2: list of the facts read from facts.jsonl in file order), train_S (2.6: JSONL rule), candidates
        (2.5: canonical object), anchor texts (DATA_MANIFEST anchor_text.decoded_texts_hash_rule: list of the 512
        texts in document order)."""
        d = Path(data_dir)
        anchor = read_jsonl(d / "anchor_text.jsonl")
        with open(d / "candidates.json", encoding="utf-8") as fh:
            cands = json.load(fh)
        return {
            "facts": sha256_hex(canonical_bytes(read_jsonl(d / "facts.jsonl"))),
            "train_S": sha256_hex(jsonl_bytes(read_jsonl(d / "train_S.jsonl"))),
            "candidates": sha256_hex(canonical_bytes(cands)),
            "anchor_texts": sha256_hex(canonical_bytes([r["text"] for r in anchor])),
        }

    def check_data_dir(self, data_dir):
        """ST12 range (1) for the generated data: the four content hashes against PROTOCOL_FROZEN."""
        got = {}
        try:
            hashes = self.content_hashes(data_dir)
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise ST12Error("cannot read the generated data in %s: %r" % (data_dir, e)) from e
        for key, sha in hashes.items():
            got[key] = self.check_content(key, sha)
        return got


def _check_templates(split_manifest, record):
    """Protocol section 3: every normalized_sha256 reproduces from its template text, and template_set_sha256 (sorted
    normalized_sha256 joined by '\\n') equals both the manifest and PROTOCOL_FROZEN values."""
    tf = split_manifest["template_freeze"]
    if tf["normalization"] != TEMPLATE_NORMALIZATION_SPEC:
        raise ST12Error("template normalization rule of the frozen manifest differs from the implemented rule")
    hashes = []
    for t in split_manifest["templates"]:
        norm = normalize_template(t["text"])
        h = sha256_hex(norm.encode("utf-8"))
        if norm != t["normalized"] or h != t["normalized_sha256"]:
            raise ST12Error("template %s: normalized form or normalized_sha256 does not reproduce" % t["template_id"])
        hashes.append(h)
    got = sha256_hex("\n".join(sorted(hashes)).encode("utf-8"))
    if got != tf["template_set_sha256"] or got != record.data_sha256["template_set"]:
        raise ST12Error("template_set_sha256 %s differs from the frozen value %s" % (got, record.data_sha256["template_set"]))


def load(repo_root=None, protocol_frozen_path=None, check_working_tree=True):
    """Read PROTOCOL_FROZEN, read the four frozen files from the frozen commit with git cat-file and run the ST12
    checks that need no generated data. Returns Frozen; raises ST12Error on any difference."""
    root = Path(repo_root) if repo_root is not None else default_repo_root()
    pf_path = Path(protocol_frozen_path) if protocol_frozen_path is not None else root / PROTOCOL_FROZEN_REL
    try:
        pf_bytes = pf_path.read_bytes()
    except OSError as e:
        raise ST12Error("cannot read PROTOCOL_FROZEN at %s: %r" % (pf_path, e)) from e
    record = parse_protocol_frozen(pf_bytes)
    r = subprocess.run(["git", "-C", str(root), "cat-file", "-t", record.commit], capture_output=True, check=False)
    if r.returncode != 0 or r.stdout.strip() != b"commit":
        raise ST12Error("frozen commit %s is not a commit of the repository at %s" % (record.commit, root))
    blobs = {}
    for rel in FROZEN_FILES:
        b = git_blob(root, record.commit, rel)
        got = sha256_hex(b)
        if got != record.file_sha256[rel]:
            raise ST12Error("%s at the frozen commit %s has sha256 %s, PROTOCOL_FROZEN %s" % (
                rel, record.commit, got, record.file_sha256[rel]))
        blobs[rel] = b
    try:
        dm = json.loads(blobs[DATA_MANIFEST_REL])
        sm = json.loads(blobs[SPLIT_MANIFEST_REL])
        ss = json.loads(blobs[SEARCH_SPACE_REL])
        protocol_text = blobs[PROTOCOL_REL].decode("utf-8")
    except ValueError as e:
        raise ST12Error("a frozen file does not parse: %r" % (e,)) from e
    for name, m in (("DATA_MANIFEST.json", dm), ("SPLIT_MANIFEST.json", sm), ("SEARCH_SPACE.json", ss)):
        if m.get("version") != record.version or m.get("status") != "PROTOCOL_FROZEN":
            raise ST12Error("%s at the frozen commit: version %r / status %r, PROTOCOL_FROZEN current version %s" % (
                name, m.get("version"), m.get("status"), record.version))
    for spec, got in ((SERIALIZATION_SPEC, dm["hashing"]["serialization"]), (JSONL_SPEC, dm["hashing"]["jsonl"]),
                      (RNG_RULE_SPEC, dm["seeds"]["rng_rule"])):
        if spec != got:
            raise ST12Error("frozen rule %r differs from the implemented rule %r" % (got, spec))
    manifests = {"data": dm, "split": sm}
    for label, (key, path) in DATA_TABLE_ROWS.items():
        held = _get(manifests[path[0]], path[1:])
        found = HEX64.findall(held) if isinstance(held, str) else []
        if found != [record.data_sha256[key]]:
            raise ST12Error("PROTOCOL_FROZEN row %r (%s) differs from %s at the frozen commit (%r)" % (
                label, record.data_sha256[key], ".".join(path[1:]), held))
    _check_templates(sm, record)
    if check_working_tree:
        for rel in FROZEN_FILES:
            try:
                wt = (root / rel).read_bytes()
            except OSError as e:
                raise ST12Error("cannot read working-tree %s: %r" % (rel, e)) from e
            if rel in STEP1_FIELDS:
                try:
                    same = strip_step1_fields(rel, json.loads(wt)) == strip_step1_fields(rel, json.loads(blobs[rel]))
                except ValueError:                      # not JSON / not UTF-8
                    same = False
            else:
                same = wt.replace(b"\r\n", b"\n") == blobs[rel]
            if not same:
                raise ST12Error("working-tree %s differs from the frozen commit %s%s" % (
                    rel, record.commit, " outside the field written by step 1" if rel in STEP1_FIELDS else ""))
    return Frozen(repo_root=root, record=record, blobs=blobs, protocol_text=protocol_text,
                  data_manifest=dm, split_manifest=sm, search_space=ss)
