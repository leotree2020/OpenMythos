"""Fetch the pilot corpus and verify its frozen byte identity."""
import hashlib
from pathlib import Path
from urllib.request import urlopen

URL = 'https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt'
SHA256 = '86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed'
data = urlopen(URL, timeout=60).read()
assert hashlib.sha256(data).hexdigest() == SHA256, 'Corpus changed; do not run'
path = Path(__file__).parent/'evidence/tinyshakespeare.txt'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(data)
print(SHA256, path)
