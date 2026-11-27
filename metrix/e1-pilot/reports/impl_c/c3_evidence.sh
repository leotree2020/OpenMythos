#!/usr/bin/env bash
# Stage C, C3 round 2: raw evidence for RUNBOOK_A100.md section 2, recorded unedited (stdout+stderr merged) by
# reports/round5/logrun.sh. Run from the repository root.
#   bash metrix/e1-pilot/reports/impl_c/c3_evidence.sh
# c3_02: each hash in the RUNBOOK table looked up in DATA_MANIFEST.json (the 7 frozen values) or in the raw outputs it
# cites (config.json: c1_01/c2_01; the safetensors: c3_hf_tree). c3_03: the Hugging Face API file list of the frozen
# revision fetched again (metadata only, no weight file) and parsed (path, size, LFS sha256).
set -u
L=metrix/e1-pilot/reports/round5/logrun.sh
D=metrix/e1-pilot
O=$D/reports/impl_c/c3_02_runbook_hashes.txt
{ echo "# Stage C, C3: the hashes of RUNBOOK_A100.md section 2 against DATA_MANIFEST.json and the cited raw outputs. Executor, host $(hostname) (Anthropic cloud container). $(date -u)"; echo "# stdout+stderr merged, unedited. Commands recorded by reports/round5/logrun.sh."; } > $O
bash $L $O git rev-parse HEAD
for h in aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155; do
  bash $L $O bash -c "grep -c $h $D/RUNBOOK_A100.md; grep -n $h $D/DATA_MANIFEST.json"
done
bash $L $O bash -c "grep -c 1ddb5b89ebc90dcb417a45c213d818577e65976454d29385c8f6140771d95197 $D/RUNBOOK_A100.md; grep -n 1ddb5b89ebc90dcb417a45c213d818577e65976454d29385c8f6140771d95197 $D/reports/impl_c/c1_01_env_fetch.txt $D/reports/impl_c/c2_01_env_fetch.txt $D/DATA_MANIFEST.json"
for h in 169ad53ec313c3a34b06c0809216e4fc072cce444a5d4ff2b59690d064130ed5 912becff8d60672aa8628ef08c05898d9adf17c2ad4ae3caf99b065622fdeff9; do
  bash $L $O bash -c "grep -c $h $D/RUNBOOK_A100.md; grep -o '{[^{}]*{[^{}]*$h[^{}]*}[^{}]*}' $D/reports/impl_c/c3_hf_tree_70d244cc.txt | head -1"
done
O=$D/reports/impl_c/c3_03_hf_tree_logged.txt
{ echo "# Stage C, C3: the file list of Qwen/Qwen3-1.7B at the frozen revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e from the Hugging Face API, fetched again and parsed (metadata only; no weight file downloaded). Replaces nothing: c3_hf_tree_70d244cc.txt was not recorded by logrun.sh. Executor, host $(hostname). $(date -u)"; echo "# stdout+stderr merged, unedited. Commands recorded by reports/round5/logrun.sh."; } > $O
T=$(mktemp -d)
bash $L $O curl -sS --max-time 60 -o $T/tree.json https://huggingface.co/api/models/Qwen/Qwen3-1.7B/tree/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e
bash $L $O sha256sum $T/tree.json
bash $L $O python3 -I -c "import json,sys; [print(e['path'], e['size'], (e.get('lfs') or {}).get('oid')) for e in json.load(open(sys.argv[1]))]" $T/tree.json
bash $L $O python3 -I -c "import json,re,sys; a=json.load(open(sys.argv[1])); s=open(sys.argv[2],encoding='utf-8').read(); b=json.loads(re.search(r'^\[.*\]$', s, re.M).group(0)); print('same as c3_hf_tree_70d244cc.txt:', a==b)" $T/tree.json $D/reports/impl_c/c3_hf_tree_70d244cc.txt
