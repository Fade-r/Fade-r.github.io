"use strict";
const assert = require("node:assert/strict");
const {renderPage} = require("../../../docs/wiki/tools/render-math.cjs");
const samples = [
  String.raw`a &lt; b &gt; c`,
  String.raw`\text{距离}\ R=\frac{cf_b}{2S}`,
  String.raw`\begin{bmatrix}1&amp;2\\3&amp;4\end{bmatrix}`,
  String.raw`\begin{aligned}x&amp;=a+b\\&amp;=c\end{aligned}`,
];
for (const tex of samples) {
  const {html, count} = renderPage('<div class="arithmatex">\\['+tex+'\\]</div>');
  assert.equal(count, 1);
  assert.match(html, /<svg/);
  assert.match(html, /<mjx-assistive-mml/);
  assert.match(html, /data-math-rendered="svg"/);
  assert.doesNotMatch(html, /data-mml-node="merror"/);
}
assert.equal(renderPage('<span class="arithmatex">\\(A\\)</span>').count, 1);
assert.throws(() => renderPage('<div class="arithmatex">\\[\\frac{a}\\]</div>'));
assert.throws(() => renderPage('<div class="arithmatex">not delimited</div>'));
console.log("Static math: entities, Chinese text, matrices, inline math and malformed TeX passed.");
