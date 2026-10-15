"""Check tutorial snippets, downloadable copies, and the four-lane array map."""
from pathlib import Path
import ast
import re
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CONTENT = ROOT / 'docs/wiki/content'
utils = (ROOT / 'project/src/iwr1443_adc_utils.py').read_text(encoding='utf-8').splitlines()
main = (ROOT / 'project/src/process_iwr1443_adc.py').read_text(encoding='utf-8').splitlines()
blocks = 0
verbatim = 0
for page in CONTENT.rglob('*.md'):
    text = page.read_text(encoding='utf-8')
    for match in re.finditer(r'^```python([^\n]*)\n(.*?)^```', text, re.M | re.S):
        options, code = match.groups()
        ast.parse(code, filename=str(page))
        blocks += 1
        numbered = re.search(r'linenums="(\d+)"', options)
        if numbered:
            first = int(numbered.group(1)) - 1
            original = main if code.startswith('def main(') else utils
            assert code.splitlines() == original[first:first + len(code.splitlines())], page
            verbatim += 1

for ext in ('py', 'm'):
    original = ROOT / f'docs/wiki/examples/tutorial_pipeline.{ext}'
    download = CONTENT / f'assets/downloads/tutorial_pipeline.{ext}'
    assert original.read_bytes() == download.read_bytes()

# Independent index check for the xWR14xx I-first, four-lane teaching layout.
ns, nc, ntx, nrx = 2, 2, 3, 4
raw_frame = np.arange(1, ns*nc*ntx*nrx*2 + 1, dtype=float)
words = raw_frame.reshape(-1, 8)
rx_samples = words[:, :4] + 1j*words[:, 4:]
physical = rx_samples.reshape(nc, ntx, ns, nrx)
frame = physical.transpose(2, 0, 1, 3).reshape(ns, nc, ntx*nrx)
for n in range(ns):
    for m in range(nc):
        for tx in range(ntx):
            for rx in range(nrx):
                offset = ((m*ntx+tx)*ns+n)*8
                expected = (offset+rx+1) + 1j*(offset+rx+5)
                assert frame[n,m,tx*nrx+rx] == expected
print(f'Python blocks parsed: {blocks}; exact project excerpts: {verbatim}')
print('Download copies identical; four-lane index checks passed.')
