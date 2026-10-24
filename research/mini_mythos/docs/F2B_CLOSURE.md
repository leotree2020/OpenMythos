# F2-B evidence closure

Status: **PENDING CHATGPT CLOSE**. No test logic was changed.

## Run

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_recurrence_cpu.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate2_2/evidence/f2b/closure/F2B_CLOSURE_RESULTS.json \
  --require-pinned
```

- OpenMythos HEAD: `b329cf44957a058516fabc8426157d25d33a5a31`
- Parcae HEAD: `69284c13746e849104f738d6d1a347b1f457df76`, status clean
- Probe Python: 3.11.2
- PyTorch: 2.14.1+cpu
- Exit: 0
- stderr: empty

## Result

Params 247936. Four pairs PASS. Negative missing/zero rejection PASS. Causal and train/eval PASS.

## SHA-256

- F2B_CLOSURE_RESULTS.json: `698d212612caf5c8bba0304251cc4e55cf2676cf2383ab626eb7701aad70caf3`
- stdout.txt: `4164111839e90efccf5b8595f4c076fce5c1019b06212c44289de957e32fec31`
- stderr.txt: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- exit_code.txt: `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`

## Remaining

This closes the CPU mechanism probe only. Native train.py, MuonAdamW on GPU, and Gate 2.2-C remain NOT TESTED.

Next: ChatGPT stage close. Do not mark a final research PASS from this archive alone.
