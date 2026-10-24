# P1-D2 Tokenizer Artifact Verification

## Verdict

**BLOCKED.** Technical load succeeded. License is unconfirmed.

Evidence level: Hub API + CPU load on this host. Not a RunPod run.

## Source

URL: https://huggingface.co/SandyResearch/parcae-tokenizer
Revision: 6247b5d0592876b73660f34c2dd16c9db9e9045c

Files:
- `.gitattributes` (size not returned by API)
- `token_bytes.pt` (not downloaded; not an LM weight, but not required for load)
- `tokenizer.json` (downloaded)

No README. No LICENSE. Hub `cardData.license` is null.

## Hash

`tokenizer.json` SHA-256:
`e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`

## Load

Pinned Parcae `Tokenizer.from_directory` on CPU:
- vocab_size = 32768
- len = 32768
- bos / eos / pad = None / None / None
- roundtrip of `Hello 你好 world.` = True

`parcae-small-140m` target vocab_size is 32768. Size matches.
Special-token IDs are not declared in this artifact.

## Relation to huginn_tokenizer_65k

**UNKNOWN.** No hash or file from that cluster path was available to compare.

## Effect

This is a public 32K tokenizer that loads. It is not cleared for formal reproduction until a license is confirmed.
Do not treat it as the official 65k Huginn tokenizer.
Do not substitute another tokenizer.

## Environment

This host. CPU only. Parcae 69284c1. No GPU. No training.
