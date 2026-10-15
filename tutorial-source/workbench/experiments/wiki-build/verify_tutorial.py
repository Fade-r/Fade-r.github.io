"""Check tutorial snippets, downloadable copies, and the four-lane array map."""
from pathlib import Path
import ast
import contextlib
import io
import re
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
CONTENT = ROOT / 'docs/wiki/content'
utils = (ROOT / 'project/src/iwr1443_adc_utils.py').read_text(encoding='utf-8').splitlines()
main = (ROOT / 'project/src/process_iwr1443_adc.py').read_text(encoding='utf-8').splitlines()
blocks = 0
verbatim = 0
for page in CONTENT.rglob('*.md'):
    text = page.read_text(encoding='utf-8')
    for code in re.findall(r'^```matlab[^\n]*\n(.*?)^```', text, re.M | re.S):
        assert '`' not in code, f'Malformed Markdown character in MATLAB: {page}'
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
# Emulate the displayed MATLAB reshape/permute sequence using column-major order.
words_matlab = raw_frame.reshape(8, -1, order='F')
rx_matlab = words_matlab[:4, :] + 1j*words_matlab[4:, :]
physical_matlab = rx_matlab.reshape(nrx, ns, ntx, nc, order='F')
frame_matlab_order = physical_matlab.transpose(1, 3, 0, 2).reshape(ns, nc, nrx*ntx, order='F')
np.testing.assert_array_equal(frame_matlab_order, frame)
assert frame[1,1,6] == 75+79j
print(f'Python blocks parsed: {blocks}; exact project excerpts: {verbatim}')
print('Download copies identical; four-lane index and column-major reshape checks passed.')

# The homepage is a complete ordered index of the sidebar groups (excluding itself).
nav = yaml.safe_load((ROOT / 'docs/wiki/mkdocs.yml').read_text(encoding='utf-8'))['nav']
home = (CONTENT / 'index.md').read_text(encoding='utf-8')
rows = re.findall(r'^\| ([^|]+) \| (.+) \|$', home, re.M)
actual = [(title.strip(), re.findall(r'\[([^\]]+)\]\(([^)]+)\)', links))
          for title, links in rows if '[' in links]
expected = []
for entry in nav:
    title, pages = next(iter(entry.items()))
    if isinstance(pages, list):
        expected.append((title, [next(iter(page.items())) for page in pages]))
assert actual == expected, 'Homepage groups, titles, order or links differ from mkdocs nav'
print('Homepage matches every sidebar group, page title, order and link.')

# Independent check of the four-point matrix example.
n = np.arange(4)
F = np.exp(-1j*2*np.pi*n[:, None]*n/4)
x = np.array([1, 1j, -1, -1j])
np.testing.assert_allclose(F @ x, np.fft.fft(x), atol=1e-12)
print('Four-point DFT matrix example passed.')

# Check the expanded stationary-target beat phase at the lesson's numerical values.
fc, slope, t, tau = 77e9, 30e12, 0.2e-6, 0.1e-6
direct = 2*np.pi*(fc*t+slope*t*t/2-fc*(t-tau)-slope*(t-tau)**2/2)
expanded = 2*np.pi*(fc*tau+slope*t*tau-slope*tau*tau/2)
np.testing.assert_allclose(direct, expanded, rtol=0, atol=1e-9)
assert (1+4/4)**(-4) == 1/16
print('Beat-phase expansion and CFAR numerical example passed.')

# Cross-page prerequisite equations must remain visible, not only linked.
recap_pages = {
    'foundations/echo-and-mixing.md': 2,
    'foundations/sampling.md': 1,
    'foundations/signal-and-fft.md': 2,
    'data/capture.md': 1,
    'data/adc-iq-layout.md': 1,
    'processing/range.md': 1,
    'processing/doppler.md': 3,
    'processing/angle.md': 3,
    'processing/phase.md': 2,
    'practice/detection.md': 2,
    'practice/end-to-end.md': 1,
    'orientation/parameters-and-shapes.md': 1,
    'code/original-functions.md': 2,
}
recap_count = 0
for relative, minimum in recap_pages.items():
    source = (CONTENT / relative).read_text(encoding='utf-8')
    count = source.count('!!! formula-recap ')
    assert count >= minimum, relative
    rendered = (ROOT / 'docs/wiki/site' / Path(relative).with_suffix('.html')).read_text(encoding='utf-8')
    assert rendered.count('class="admonition formula-recap"') == count, relative
    assert '!!! formula-recap' not in rendered, relative
    recap_count += count
print(f'{recap_count} prerequisite equation notes rendered across {len(recap_pages)} pages.')

# Execute the self-contained FFT lesson in reading order, including its 4-point
# matrix detour and return to the 8-point frequency-axis example.
fft_lesson = (CONTENT / 'foundations/signal-and-fft.md').read_text(encoding='utf-8')
namespace = {}
with contextlib.redirect_stdout(io.StringIO()):
    for code in re.findall(r'^```python[^\n]*\n(.*?)^```', fft_lesson, re.M | re.S):
        exec(compile(code, 'FFT lesson', 'exec'), namespace)
assert namespace['X'].shape == namespace['frequency'].shape == (8,)
assert namespace['X_windowed'].shape == (8,)
assert namespace['frequency'][np.argmax(abs(namespace['shifted']))] == 2e6

# Numerical checks for the newly explained transitions.
n = np.arange(8)
np.testing.assert_allclose(np.exp(1j*2*np.pi*5*n/8),
                           np.exp(-1j*2*np.pi*3*n/8), atol=1e-14)
wavelength = 0.004
np.testing.assert_allclose(np.unwrap([0.9*np.pi, -0.9*np.pi]),
                           [0.9*np.pi, 1.1*np.pi])
np.testing.assert_allclose(wavelength*(np.pi/2)/(4*np.pi), 0.0005)
positions = np.array([0, 0.5, 1.5, 2.0])*wavelength
steering = np.exp(1j*2*np.pi*positions*0.5/wavelength)
np.testing.assert_allclose(np.conj(steering)*steering, np.ones(4), atol=1e-14)
noise_trace = np.array([1+2j, 3-1j, -2+4j])
assert abs(np.fft.fft(noise_trace-noise_trace.mean())[0]) < 1e-14
print('Sequential FFT snippets, aliasing, unwrap, beam phase cancellation and mean removal passed.')
