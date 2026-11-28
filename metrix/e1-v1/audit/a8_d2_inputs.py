# data-auditor, E1-V1 round 1, supplement to item 5: D2 scoring input (protocol section 0 and 7.1):
# in the context chat(p) + 'The answer is', the scored continuation ' ' + letter is exactly one
# token (362, 425, 356, 422) and the context ids are a prefix of the full ids, for every D2 DEV item
# (MMLU and ARC). Report only: items whose four option texts are not all distinct.
import sys

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402

D = A.TMP + "/v1data"


def main():
    dm = A.load_json(A.V1 + "/DATA_MANIFEST.json")
    gm = A.load_json(A.V1 + "/DAMAGE_MANIFEST.json")
    tok = A.load_qwen_tokenizer(dm["model"]["tokenizer"]["files_sha256"])
    ids = gm["d2"]["letter_token_ids"]
    for name in ("d2_dev.jsonl", "d2_dev_arc.jsonl"):
        items = A.read_jsonl(D + "/" + name)
        bad, dup = 0, 0
        for x in items:
            ctx = tok.apply_chat_template([{"role": "user", "content": x["prompt"]}], tokenize=False,
                                          add_generation_prompt=True, enable_thinking=False) + "The answer is"
            c = tok.encode(ctx, add_special_tokens=False)
            for L, i in ids.items():
                full = tok.encode(ctx + " " + L, add_special_tokens=False)
                if full[:len(c)] != c or full[len(c):] != [i]:
                    bad += 1
            lines = x["prompt"].split("\n")
            opts = [l[3:] for l in lines[-4:]]
            dup += len(set(opts)) != 4
        print(f"{name}: items {len(items)} | (item, letter) pairs where the scored continuation is not exactly the single letter token after the context ids: {bad} | report only: items with repeated option texts {dup}")
        print(f"   chat template ends with: {ctx[-60:]!r}")
    print("SUPPLEMENT D2 inputs: done")


if __name__ == "__main__":
    main()
