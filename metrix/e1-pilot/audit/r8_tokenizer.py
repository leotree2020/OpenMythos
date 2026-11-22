"""R8-6: Qwen/Qwen3-1.7B@70d244cc tokenizer files (DATA_MANIFEST model.tokenizer.files_sha256, round 8 item 1d).
Data Auditor's own script; no Executor code is imported, called or copied. Loads tokenizers only, never weights.
Exceptions -> RESULT: FAIL (r6_guard).

  a. sha256 of the four files downloaded by r8_fetch.py == freeze-commit manifest values (and the keys are exactly
     these four files).
  b. the full repository tree at the pinned revision (recursive, Hub API): every path, size, LFS sha256 / blob id;
     tokenizer files are classified by name (tokenizer*, vocab*, merges*, special_tokens_map.json, added_tokens.json,
     *.model, *.tiktoken, chat_template*, additional_chat_templates/*, spiece*, sentencepiece*, bpe*); the set of
     tokenizer files in the tree must equal the manifest key set ("all tokenizer files").
  c. which files transformers 5.22.2 itself requests: AutoTokenizer.from_pretrained(repo, revision=pinned,
     cache_dir=<new empty dir>); files present in the cache snapshot and the misses recorded under .no_exist/;
     no weight file may appear in that cache.
  d. the tokenizer loaded from a directory that holds only the four files equals the one loaded from the Hub
     (class, vocabulary, special ids, encodings of probe strings, chat template output with
     add_generation_prompt=True, enable_thinking=False); tokenizer_config.json carries the chat template.
Prints AUDIT_VALUE lines.
PASS iff a, b, c (requested files that exist are within the four tokenizer files plus non-tokenizer config files,
no weights) and d hold.
usage: python -I r8_tokenizer.py <repo_root> <commit> <qwen_tok_dir (4 files)> <new_cache_dir (must not exist)>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, json, re, subprocess
from r6_guard import run

REPO, REV = "Qwen/Qwen3-1.7B", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
WEIGHT_EXT = (".safetensors", ".bin", ".pt", ".pth", ".gguf", ".h5", ".msgpack", ".ckpt", ".onnx")
TOK_PAT = re.compile(r"(^|/)(tokenizer[^/]*|vocab[^/]*|merges[^/]*|special_tokens_map\.json|added_tokens\.json|"
                     r"[^/]*\.model|[^/]*\.tiktoken|chat_template[^/]*|spiece[^/]*|sentencepiece[^/]*|bpe[^/]*)$|"
                     r"^additional_chat_templates/")


def git_blob(repo, commit, path):
    return subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{commit}:{path}"], capture_output=True, check=True).stdout


def fsha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    repo, commit, tokdir, cache = sys.argv[1:5]
    ok = True
    dm = json.loads(git_blob(repo, commit, "metrix/e1-pilot/DATA_MANIFEST.json"))
    tk = dm["model"]["tokenizer"]
    print("freeze-commit DATA_MANIFEST model.tokenizer:", json.dumps(tk, ensure_ascii=False, indent=1))
    ok &= tk["repo"] == REPO and tk["revision"] == REV and dm["model"]["repo"] == REPO and dm["model"]["revision"] == REV
    man = tk["files_sha256"]

    print("\n== a. downloaded files vs manifest")
    local = sorted(x for x in os.listdir(tokdir) if not x.startswith("."))
    print("files in", tokdir, ":", local, "| == manifest keys:", sorted(man) == local)
    ok &= sorted(man) == local
    for f in sorted(man):
        h = fsha(os.path.join(tokdir, f))
        m = h == man[f]
        ok &= m
        print(f"  {f:<22} sha256 {h} | manifest {man[f]} | MATCH {m}")
        print(f"AUDIT_VALUE qwen_tokenizer_sha256:{f} {h}")

    print("\n== b. repository tree at the pinned revision (recursive)")
    from huggingface_hub import HfApi
    api = HfApi()
    tree = list(api.list_repo_tree(REPO, revision=REV, recursive=True))
    files = []
    for e in tree:
        kind = type(e).__name__
        lfs = getattr(e, "lfs", None)
        size = getattr(e, "size", None)
        tag = "TOKENIZER" if (kind == "RepoFile" and TOK_PAT.search(e.path)) else ""
        print(f"  {kind:<10} {e.path:<40} size {size} | {'lfs sha256 ' + lfs.sha256 if lfs else 'blob ' + str(getattr(e, 'blob_id', None))} {tag}")
        if kind == "RepoFile":
            files.append(e)
    folders = [e.path for e in tree if type(e).__name__ != "RepoFile"]
    tokfiles = sorted(e.path for e in files if TOK_PAT.search(e.path))
    print("folders in tree:", folders)
    print("tokenizer files in tree:", tokfiles, "| == manifest keys:", tokfiles == sorted(man))
    ok &= tokfiles == sorted(man)
    flat = sorted(api.list_repo_files(REPO, revision=REV))
    print("list_repo_files (all files):", flat, "| same set as tree:", flat == sorted(e.path for e in files))
    ok &= flat == sorted(e.path for e in files)
    meta = {e.path: e for e in files}
    for f in sorted(man):
        e = meta[f]
        if e.lfs:
            m = e.lfs.sha256 == man[f]
            print(f"  hub {f}: lfs sha256 {e.lfs.sha256} == manifest: {m}")
        else:
            b = open(os.path.join(tokdir, f), "rb").read()
            blob = hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()
            m = blob == e.blob_id and hashlib.sha256(b).hexdigest() == man[f] and len(b) == e.size
            print(f"  hub {f}: blob {e.blob_id}, size {e.size}; local bytes blob {blob}, sha256 == manifest: {m}")
        ok &= m

    print("\n== c. files requested by transformers AutoTokenizer.from_pretrained (fresh cache)")
    if os.path.exists(cache):
        print("cache dir exists already; refusing to reuse:", cache)
        return False
    import transformers
    from transformers import AutoTokenizer
    print("transformers", transformers.__version__)
    hub_tok = AutoTokenizer.from_pretrained(REPO, revision=REV, cache_dir=cache)
    got, miss, allpaths = [], [], []
    for r, _, fs in os.walk(cache):
        for x in fs:
            p = os.path.join(r, x)
            rel = os.path.relpath(p, cache)
            allpaths.append(rel)
            if f"{os.sep}snapshots{os.sep}{REV}{os.sep}" in p:
                got.append(p.split(f"{os.sep}snapshots{os.sep}{REV}{os.sep}", 1)[1])
            if f"{os.sep}.no_exist{os.sep}{REV}{os.sep}" in p:
                miss.append(p.split(f"{os.sep}.no_exist{os.sep}{REV}{os.sep}", 1)[1])
    got, miss = sorted(got), sorted(miss)
    print("fetched into the snapshot:", got)
    print("requested but absent at the revision (.no_exist):", miss)
    weights = [p for p in allpaths if p.endswith(WEIGHT_EXT)]
    print("weight-like files in the cache:", weights)
    ok &= not weights
    tok_got = [g for g in got if TOK_PAT.search(g)]
    other = [g for g in got if not TOK_PAT.search(g)]
    print("fetched tokenizer files:", tok_got, "| == manifest keys:", sorted(tok_got) == sorted(man))
    print("fetched non-tokenizer files:", other)
    ok &= sorted(tok_got) == sorted(man) and all(o in ("config.json", "generation_config.json") for o in other)
    snap = os.path.join(cache, "models--Qwen--Qwen3-1.7B", "snapshots", REV)
    for g in got:
        print(f"  snapshot {g}: sha256 {fsha(os.path.join(snap, g))}"
              + (f" | == manifest {fsha(os.path.join(snap, g)) == man[g]}" if g in man else " (not a tokenizer file)"))
        if g in man:
            ok &= fsha(os.path.join(snap, g)) == man[g]
    miss_tok_in_tree = [m for m in miss if m in flat]
    print("requested files reported absent but present in tree (must be empty):", miss_tok_in_tree)
    ok &= not miss_tok_in_tree

    print("\n== d. four-file directory vs Hub load")
    loc_tok = AutoTokenizer.from_pretrained(tokdir, local_files_only=True)
    cfg = json.load(open(os.path.join(tokdir, "tokenizer_config.json"), encoding="utf-8"))
    print("tokenizer_config.json has chat_template:", isinstance(cfg.get("chat_template"), str),
          "| length", len(cfg.get("chat_template") or ""))
    ok &= isinstance(cfg.get("chat_template"), str)
    probes = ["The capital of Krultrouth is Linnuth.", " Linnuth", "KZT-47", "What is the capital of X?",
              "<|endoftext|>", "<think>\n\n</think>", " DFMTT-96", "naïve café – “quotes”"]
    same_cls = type(loc_tok) is type(hub_tok)
    same_len = len(loc_tok) == len(hub_tok)
    same_vocab = loc_tok.get_vocab() == hub_tok.get_vocab()
    same_special = loc_tok.all_special_ids == hub_tok.all_special_ids and loc_tok.all_special_tokens == hub_tok.all_special_tokens
    same_enc = all(loc_tok.encode(s, add_special_tokens=False) == hub_tok.encode(s, add_special_tokens=False) for s in probes)
    msgs = [{"role": "user", "content": "What is the capital of X?"}]
    ca = loc_tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    cb = hub_tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    print(f"class {type(loc_tok).__name__}/{type(hub_tok).__name__} same {same_cls} | len {len(loc_tok)}/{len(hub_tok)} | "
          f"vocab equal {same_vocab} | special equal {same_special} | probe encodings equal {same_enc} | chat equal {ca == cb}")
    print("chat template output:", repr(ca))
    print("special ids:", loc_tok.all_special_ids, "| eos", loc_tok.eos_token, loc_tok.eos_token_id,
          "| pad", loc_tok.pad_token, loc_tok.pad_token_id)
    print("ids: <|endoftext|>", loc_tok.convert_tokens_to_ids("<|endoftext|>"), "<|im_end|>",
          loc_tok.convert_tokens_to_ids("<|im_end|>"), "<think>", loc_tok.convert_tokens_to_ids("<think>"),
          "</think>", loc_tok.convert_tokens_to_ids("</think>"))
    ok &= same_cls and same_len and same_vocab and same_special and same_enc and ca == cb
    return ok


run(main)
