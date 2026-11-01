"""Source-only inspection. No score or model input."""
import hashlib
import importlib.metadata as md
import json
from pathlib import Path
import sys

import pyarrow.parquet as pq


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def main():
    source = Path('/workspaces/mythos-evidence/base_v01/depth_budget/preparation-v1-20261101/test.parquet')
    raw = source.read_bytes()
    assert digest(raw) == '3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925'
    rows = pq.read_table(source, columns=['text']).column('text').to_pylist()
    assert len(rows) == 4358
    boundary, blocks = [], []
    for i, text in enumerate(rows):
        stripped = text.strip()
        if stripped and (stripped.startswith('=') or stripped.endswith('=')):
            tokens = stripped.split()
            leading = trailing = 0
            for token in tokens:
                if token != '=':
                    break
                leading += 1
            for token in reversed(tokens):
                if token != '=':
                    break
                trailing += 1
            top = stripped.startswith('=') and stripped.endswith('=') and stripped.count('=') == 2
            nested = leading == trailing and leading >= 2 and len(tokens) > leading + trailing and stripped.count('=') == leading + trailing
            after = [{'row': j, 'text': rows[j]} for j in range(i + 1, min(i + 9, len(rows))) if rows[j].strip()][:2]
            boundary.append({'row': i, 'row_sha256': digest(text.encode()), 'title': stripped,
                             'top_candidate': top, 'nested_section': nested,
                             'leading_equals': leading, 'trailing_equals': trailing,
                             'before_blank': i == 0 or not rows[i - 1].strip(),
                             'after_blank': i + 1 == len(rows) or not rows[i + 1].strip(),
                             'prev': rows[i - 1] if i else None,
                             'next': rows[i + 1] if i + 1 < len(rows) else None,
                             'following_nonempty': after})
        if stripped and (i == 0 or not rows[i - 1].strip()):
            blocks.append({'row': i, 'text': text[:450], 'boundaryish': stripped.startswith('=') or stripped.endswith('=')})
    assert 'torch' not in sys.modules
    result = {'corpus_sha256': digest(raw), 'row_count': len(rows), 'rows_sha256': digest(canonical(rows)),
              'row_inventory': [{'row': i, 'sha256': digest(text.encode()), 'utf8_bytes': len(text.encode())}
                                for i, text in enumerate(rows)],
              'boundary_rows': boundary, 'block_starts': blocks,
              'packages': {name: md.version(name) for name in ('pyarrow', 'numpy', 'tokenizers')}, 'torch_imported': False}
    output = Path(sys.argv[1])
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status': 'PASS', 'boundary_rows': len(boundary),
                      'old_top': sum(x['top_candidate'] for x in boundary), 'nested': sum(x['nested_section'] for x in boundary),
                      'other': [x for x in boundary if not x['top_candidate'] and not x['nested_section']],
                      'block_starts': len(blocks), 'rows_sha256': result['rows_sha256'],
                      'inventory_sha256': digest(output.read_bytes()), 'inventory_bytes': output.stat().st_size}))


if __name__ == '__main__':
    main()
