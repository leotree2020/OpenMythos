"""Freeze historical-development text windows. No Torch/model import or evaluation."""
import argparse
import hashlib
import json
import sys
import importlib.metadata
from pathlib import Path

import pyarrow.parquet as pq
from tokenizers import Tokenizer

CORPUS_SHA = '3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925'
TOKENIZER_SHA = 'e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_ids(ids):
    return json.dumps(ids, separators=(',', ':')).encode()


def article_rows(rows):
    articles = []
    current = None
    for index, text in enumerate(rows):
        stripped = text.strip()
        is_title = stripped.startswith('=') and stripped.endswith('=') and stripped.count('=') == 2
        if is_title:
            if current is not None:
                articles.append(current)
            current = {'title': stripped, 'heading_row': index, 'body_rows': [], 'parts': []}
        elif current is not None:
            current['parts'].append(text)
            current['body_rows'].append(index)
    if current is not None:
        articles.append(current)
    return articles


def prepare(corpus, tokenizer_file):
    assert sha(corpus.read_bytes()) == CORPUS_SHA, 'Original parquet hash differs'
    assert sha(tokenizer_file.read_bytes()) == TOKENIZER_SHA, 'Original tokenizer hash differs'
    rows = pq.read_table(corpus, columns=['text']).column('text').to_pylist()
    assert len(rows) == 4358 and all(isinstance(x, str) for x in rows)
    tokenizer = Tokenizer.from_file(str(tokenizer_file))
    articles = article_rows(rows)
    candidates = []
    for article in articles:
        text = ''.join(article['parts'])
        ids = tokenizer.encode(text, add_special_tokens=False).ids
        if len(ids) < 257:
            continue
        article_id = sha((article['title'] + '\n' + text).encode('utf-8'))
        candidates.append({'article_id': article_id, 'title': article['title'],
                           'heading_row': article['heading_row'], 'body_rows': article['body_rows'],
                           'text_sha256': sha(text.encode('utf-8')), 'full_token_count': len(ids),
                           'tokens': ids[:257]})
    candidates.sort(key=lambda x: x['article_id'])
    assert len({x['article_id'] for x in candidates}) == len(candidates), 'Duplicate article identity'
    assert len(candidates) >= 32, 'Insufficient eligible articles; no adaptive resizing'
    samples = candidates[:32]
    assert len({x['text_sha256'] for x in samples}) == 32, 'Duplicate selected text'
    for index, sample in enumerate(samples):
        sample['index'] = index
        assert len(sample['tokens']) == 257 and all(type(x) is int and 0 <= x < 32768 for x in sample['tokens'])
        sample['window_ids_sha256'] = sha(canonical_ids(sample['tokens']))
        sample['input_ids_sha256'] = sha(canonical_ids(sample['tokens'][:256]))
        sample['target_ids_sha256'] = sha(canonical_ids(sample['tokens'][1:257]))
        sample['scored_target_ids_sha256'] = sha(canonical_ids(sample['tokens'][1:257][64:256]))
    return {'experiment': 'MYTHOS-DEPTH-BUDGET-CPU-V1',
            'data_label': 'historical development; no fresh-test or pretraining-contamination-free claim',
            'dataset': 'Salesforce/wikitext', 'config': 'wikitext-2-raw-v1', 'split': 'test',
            'revision': '6231e49f19a707241d6b84d9cff60a3a86b85a85',
            'corpus_sha256': CORPUS_SHA, 'tokenizer_sha256': TOKENIZER_SHA,
            'source_rows': len(rows), 'articles': len(articles), 'eligible_articles': len(candidates),
            'selection': 'first32 by ascending SHA256(title+newline+unmodified concatenated body rows), after >=257-token filter',
            'special_tokens_added': False, 'input_length': 256, 'prediction_burn_in': 64,
            'scored_tokens_per_sample': 192, 'samples': samples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Never overwrite an input freeze'
    result = prepare(args.corpus, args.tokenizer)
    assert 'torch' not in sys.modules, 'Preparation unexpectedly imported Torch'
    raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    with args.output.open('xb') as target:
        target.write(raw)
    print(json.dumps({'Status': 'PASS', 'samples': len(result['samples']),
                      'source_rows': result['source_rows'], 'articles': result['articles'],
                      'eligible_articles': result['eligible_articles'],
                      'bytes': len(raw), 'sha256': sha(raw), 'model_execution': False,
                      'torch_imported': 'torch' in sys.modules,
                      'packages': {name: importlib.metadata.version(name) for name in ('numpy', 'pyarrow', 'tokenizers')}}))


if __name__ == '__main__':
    main()
