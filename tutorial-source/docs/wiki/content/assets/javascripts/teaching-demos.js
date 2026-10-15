/* Theoretical examples only; constants follow RadarConfig in the project. */
(() => {
  function init() {
    const range = document.getElementById('demo-range');
    if (!range || range.dataset.ready) return;
    range.dataset.ready = 'true';
    const c = 3e8, slope = 29.982e12, fs = 10e6, samples = 256;
    const wavelength = c / (77e9 + slope * 60e-6 / 2);
    const setText = (id, text) => { document.getElementById(id).textContent = text; };
    function updateRange() {
      const distance = Number(range.value);
      const beat = 2 * slope * distance / c;
      const bin = beat * samples / fs;
      setText('range-value', `${distance.toFixed(1)} m`);
      setText('range-result', `${distance.toFixed(1)} m → 拍频 ${(beat / 1e6).toFixed(4)} MHz → 第 ${bin.toFixed(2)} 格附近。`);
      document.getElementById('range-marker').style.left = `${bin / 64 * 100}%`;
      document.querySelector('.bin-scale').setAttribute('aria-label', `理论峰位于第 ${bin.toFixed(2)} 格`);
      setText('range-explanation', `对照 5 m 时的第 25.58 格：当前距离是它的 ${(distance / 5).toFixed(1)} 倍，拍频和理论格编号也都是它的 ${(distance / 5).toFixed(1)} 倍。距离格的间距仍约为 0.19543 m。`);
    }
    range.addEventListener('input', updateRange);
    document.querySelectorAll('[data-range]').forEach(button => button.addEventListener('click', () => {
      range.value = button.dataset.range;
      updateRange();
    }));
    function updateTiming(factor) {
      const interval = factor * 160e-6;
      const dv = wavelength / (2 * 128 * interval);
      document.querySelectorAll('[data-timing]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.timing) === factor)));
      setText('timing-result', `第 +10 格 × ${dv.toFixed(5)} m/s/格 = +${(10 * dv).toFixed(4)} m/s。`);
      setText('timing-explanation', factor === 1
        ? '当前代码按 160 µs 换算，读出约 +0.9402 m/s。如果实际是三路轮发，它把同一通道的观察间隔缩短成了三分之一，速度就被放大了 3 倍。'
        : '三路轮发时，同一通道每 480 µs 才有一个新点，读出约 +0.3134 m/s。这里只改了横轴的换算间隔，谱峰仍在第 +10 格。');
    }
    document.querySelectorAll('[data-timing]').forEach(button => button.addEventListener('click', () => updateTiming(Number(button.dataset.timing))));
    const phase = document.getElementById('demo-phase');
    function updatePhase() {
      const angle = Number(phase.value), scale = wavelength * 1000 / (4 * Math.PI);
      const x = 125 + 75 * Math.cos(angle), y = 115 - 75 * Math.sin(angle);
      setText('phase-value', `${angle.toFixed(1)} rad`);
      setText('phase-result', `${angle.toFixed(1)} rad × ${scale.toFixed(5)} mm/rad = ${(angle * scale).toFixed(5)} mm。`);
      setText('phase-svg-title', `单位圆上相位变化 ${angle.toFixed(1)} 弧度`);
      document.getElementById('phase-hand').setAttribute('x2', String(x));
      document.getElementById('phase-hand').setAttribute('y2', String(y));
      document.getElementById('phase-point').setAttribute('cx', String(x));
      document.getElementById('phase-point').setAttribute('cy', String(y));
    }
    phase.addEventListener('input', updatePhase);
    updateRange(); updateTiming(3); updatePhase();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
  if (typeof document$ !== 'undefined') document$.subscribe(init);
})();
