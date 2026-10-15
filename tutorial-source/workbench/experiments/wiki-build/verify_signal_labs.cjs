"use strict";
const assert = require("node:assert/strict");
const path = require("node:path");
const model = require(path.resolve(__dirname, "../../../docs/wiki/content/assets/javascripts/signal-labs.js"));
function close(actual, expected, tolerance = 1e-12) {
  assert.ok(Math.abs(actual - expected) < tolerance, actual + " != " + expected);
}
for (let distance = 5; distance <= 30; distance += 5) {
  const s = model.echo(distance);
  close(s.delayUs, distance / 150);
  close(s.beatMHz, distance / 5);
  // In plotted units: f_tx = 30*t; f_rx = 30*(t-tau).
  close(30 * 0.4 - 30 * (0.4 - s.delayUs), s.beatMHz);
}
const expectedIQ = [[1,0],[Math.SQRT1_2,Math.SQRT1_2],[0,1],
  [-Math.SQRT1_2,Math.SQRT1_2],[-1,0],[-Math.SQRT1_2,-Math.SQRT1_2],
  [0,-1],[Math.SQRT1_2,-Math.SQRT1_2],[1,0]];
expectedIQ.forEach(([i,q],n) => {
  const s=model.iq(n); close(s.i,i); close(s.q,q);
  close(s.i*s.i+s.q*s.q,1); close(s.timeUs,n*0.125);
});
// Independent file-order construction, instead of repeating the flattened formula.
let word = 1, count = 0;
for (let m=0;m<2;m++) for(let tx=0;tx<3;tx++) for(let n=0;n<2;n++) {
  const i=[word++,word++,word++,word++], q=[word++,word++,word++,word++];
  for(let rx=0;rx<4;rx++) {
    const s=model.layout(n,m,tx,rx);
    assert.equal(s.i,i[rx]); assert.equal(s.q,q[rx]);
    assert.equal(s.iIndex,s.i-1); assert.equal(s.qIndex,s.q-1);
    assert.equal(s.channel,4*tx+rx); count++;
  }
}
assert.equal(count,48);
assert.deepEqual([model.layout(1,1,1,2).i,model.layout(1,1,1,2).q],[75,79]);
for(let k=0;k<4;k++) {
  const s=model.dft(k);
  close(s.sum[0],k===1?4:0); close(s.sum[1],0);
  for(let n=0;n<4;n++) {
    const a=s.row[n], b=s.input[n];
    close(s.products[n][0],a[0]*b[0]-a[1]*b[1]);
    close(s.products[n][1],a[0]*b[1]+a[1]*b[0]);
  }
}
assert.throws(()=>model.iq(9),RangeError);
assert.throws(()=>model.layout(0,0,3,0),RangeError);
assert.throws(()=>model.echo(NaN),RangeError);
assert.throws(()=>model.dft(-1),RangeError);
console.log("Echo: 6 distances; I/Q: 9 samples; layout: all 48 complex elements (96 words); DFT: all 4 rows passed.");
