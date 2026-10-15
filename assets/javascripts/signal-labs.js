/* Local teaching models. No data files, network calls or external libraries. */
(function () {
  "use strict";
  const clean = (x) => Math.abs(x) < 1e-12 ? 0 : x;
  function integer(x, min, max) {
    if (!Number.isInteger(x) || x < min || x > max) throw new RangeError("Invalid index");
  }
  function echo(distance) {
    if (!Number.isFinite(distance) || distance < 5 || distance > 30) throw new RangeError("Invalid distance");
    const delay = 2 * distance / 3e8;
    return { distance: distance, delayUs: delay * 1e6, beatMHz: 30e12 * delay / 1e6 };
  }
  function iq(n) {
    integer(n, 0, 8);
    const phase = 2 * Math.PI * n / 8;
    return { n: n, timeUs: n / 8, degrees: n * 45, i: clean(Math.cos(phase)), q: clean(Math.sin(phase)) };
  }
  function layout(n, m, tx, rx) {
    integer(n, 0, 1); integer(m, 0, 1); integer(tx, 0, 2); integer(rx, 0, 3);
    const group = (m * 3 + tx) * 2 + n;
    const iIndex = group * 8 + rx, qIndex = iIndex + 4;
    return { n: n, m: m, tx: tx, rx: rx, group: group, channel: tx * 4 + rx,
      iIndex: iIndex, qIndex: qIndex, i: iIndex + 1, q: qIndex + 1 };
  }
  function dft(k) {
    integer(k, 0, 3);
    const row = [], input = [], products = [];
    for (let n = 0; n < 4; n++) {
      const a = -2 * Math.PI * k * n / 4, b = 2 * Math.PI * n / 4;
      row.push([clean(Math.cos(a)), clean(Math.sin(a))]);
      input.push([clean(Math.cos(b)), clean(Math.sin(b))]);
      products.push([clean(Math.cos(a + b)), clean(Math.sin(a + b))]);
    }
    return { row: row, input: input, products: products,
      sum: products.reduce((s, z) => [clean(s[0] + z[0]), clean(s[1] + z[1])], [0, 0]) };
  }
  const models = { echo: echo, iq: iq, layout: layout, dft: dft };
  if (typeof module !== "undefined" && module.exports) module.exports = models;
  if (typeof document === "undefined") return;

  function html(tag, attrs, text) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function svgEl(tag, attrs, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function line(svg, x1, y1, x2, y2, cls) {
    svg.append(svgEl("line", { x1: x1, y1: y1, x2: x2, y2: y2, class: cls || "lab-axis" }));
  }
  function text(svg, x, y, value, anchor) {
    svg.append(svgEl("text", { x: x, y: y, "text-anchor": anchor || "middle" }, value));
  }
  function chart(host, title, yLabel, xMax, yMin, yMax, yTicks) {
    const w = Math.max(240, Math.floor(host.getBoundingClientRect().width)), h = 260;
    const left = 42, right = w - 18, top = 38, bottom = h - 42;
    const svg = svgEl("svg", { viewBox: "0 0 " + w + " " + h, role: "img", "aria-label": title });
    svg.append(svgEl("title", {}, title));
    const x = (v) => left + v / xMax * (right - left);
    const y = (v) => bottom - (v - yMin) / (yMax - yMin) * (bottom - top);
    text(svg, left, 18, yLabel, "start");
    yTicks.forEach((v) => {
      line(svg, left, y(v), right, y(v), "lab-grid");
      text(svg, left - 8, y(v) + 4, String(v), "end");
    });
    [0, xMax / 2, xMax].forEach((v) => {
      line(svg, x(v), bottom, x(v), bottom + 4);
      text(svg, x(v), bottom + 20, String(v));
    });
    line(svg, left, top, left, bottom);
    line(svg, left, bottom, right, bottom);
    text(svg, (left + right) / 2, h - 3, "时间 / µs");
    host.replaceChildren(svg);
    return { svg: svg, x: x, y: y };
  }
  function path(plot, points, cls) {
    const d = points.map((p, i) => (i ? "L" : "M") + plot.x(p[0]) + "," + plot.y(p[1])).join(" ");
    plot.svg.append(svgEl("path", { d: d, class: cls, fill: "none" }));
  }
  const fixed = (v, places) => clean(v).toFixed(places);
  function complex(z) {
    if (z[1] === 0) return String(clean(z[0]));
    const imaginary = (Math.abs(z[1]) === 1 ? "" : String(Math.abs(z[1]))) + "j";
    if (z[0] === 0) return (z[1] < 0 ? "−" : "") + imaginary;
    return z[0] + (z[1] < 0 ? " − " : " + ") + imaginary;
  }
  const view = (root, name) => root.querySelector('[data-view="' + name + '"]');
  const control = (root, name) => root.querySelector('[data-control="' + name + '"]');
  function resize(root, render) {
    let width = -1;
    new ResizeObserver((entries) => {
      const next = entries[0].contentRect.width;
      if (next !== width && next > 0) { width = next; render(); }
    }).observe(root);
  }
  function mountEcho(root) {
    const input = control(root, "distance");
    function render() {
      const state = echo(Number(input.value));
      view(root, "distance").textContent = state.distance + " m";
      input.setAttribute("aria-valuetext", state.distance + " 米");
      view(root, "result").textContent = "τ = 2R/c ≈ " + fixed(state.delayUs, 3) +
        " µs；f_b = Sτ = " + fixed(state.beatMHz, 1) + " MHz";
      const p = chart(view(root, "plot"), "发射频率与延迟回波；距离 " + state.distance + " 米",
        "相对 77 GHz 的频率增量 / MHz", 0.5, 0, 15, [0, 5, 10, 15]);
      path(p, [[0, 0], [0.5, 15]], "lab-line-a");
      path(p, [[state.delayUs, 0], [0.5, 15 - state.beatMHz]], "lab-line-b");
      line(p.svg, p.x(0.4), p.y(12), p.x(0.4), p.y(12 - state.beatMHz), "lab-difference");
      p.svg.append(svgEl("circle", { cx: p.x(state.delayUs), cy: p.y(0), r: 4, class: "lab-point-b" }));
    }
    input.addEventListener("input", render);
    render(); resize(root, render);
  }
  function mountIQ(root) {
    const input = control(root, "sample");
    const previous = root.querySelector('[data-action="previous"]');
    const next = root.querySelector('[data-action="next"]');
    const play = root.querySelector('[data-action="play"]');
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    let timer = null;
    function stop() {
      if (timer !== null) clearInterval(timer);
      timer = null; play.textContent = "播放一周（慢放）";
      view(root, "result").setAttribute("aria-live", "polite");
    }
    function render() {
      const s = iq(Number(input.value));
      view(root, "sample").textContent = String(s.n);
      input.setAttribute("aria-valuetext", "第 " + s.n + " 点，相位 " + s.degrees + " 度");
      view(root, "result").textContent = "n = " + s.n + "；t = " + fixed(s.timeUs, 3) +
        " µs；φ = " + s.degrees + "°；I = " + fixed(s.i, 3) + "；Q = " + fixed(s.q, 3);
      previous.disabled = s.n === 0; next.disabled = s.n === 8;
      const host = view(root, "circle"), w = Math.max(240, Math.floor(host.getBoundingClientRect().width));
      const h = 260, cx = w / 2, cy = h / 2 + 6, r = Math.min(w / 2 - 43, 88);
      const svg = svgEl("svg", { viewBox: "0 0 " + w + " " + h, role: "img", "aria-label": "复平面，相位 " + s.degrees + " 度" });
      text(svg, 8, 18, "复平面（幅度 = 1）", "start");
      svg.append(svgEl("circle", { cx: cx, cy: cy, r: r, class: "lab-unit-circle" }));
      line(svg, cx-r-14, cy, cx+r+14, cy);
      line(svg, cx, cy+r+14, cx, cy-r-14);
      text(svg, cx+r+24, cy+4, "I"); text(svg, cx, cy-r-22, "Q");
      text(svg, cx-r, cy+18, "−1"); text(svg, cx+r, cy+18, "1");
      const px = cx + r*s.i, py = cy - r*s.q;
      line(svg, px, py, px, cy, "lab-projection");
      line(svg, px, py, cx, py, "lab-projection");
      line(svg, cx, cy, px, py, "lab-vector");
      svg.append(svgEl("circle", { cx: px, cy: py, r: 5, class: "lab-current" }));
      host.replaceChildren(svg);
      const p = chart(view(root, "wave"), "I/Q 波形，当前第 " + s.n + " 个采样点",
        "归一化幅度", 1, -1.2, 1.2, [-1, 0, 1]);
      const points = Array.from({ length: 129 }, (_, k) => k / 128);
      path(p, points.map((t) => [t, Math.cos(2*Math.PI*t)]), "lab-line-a");
      path(p, points.map((t) => [t, Math.sin(2*Math.PI*t)]), "lab-line-b");
      line(p.svg, p.x(s.timeUs), p.y(-1.2), p.x(s.timeUs), p.y(1.2), "lab-projection");
      for (let n=0; n<=8; n++) {
        const a=iq(n), radius=n===s.n ? 5 : 2.5;
        p.svg.append(svgEl("circle", { cx:p.x(a.timeUs), cy:p.y(a.i), r:radius, class:"lab-point-a" }));
        p.svg.append(svgEl("rect", { x:p.x(a.timeUs)-radius, y:p.y(a.q)-radius, width:2*radius, height:2*radius, class:"lab-point-b" }));
      }
    }
    function manual(n) { stop(); input.value=String(n); render(); }
    input.addEventListener("input", () => manual(Number(input.value)));
    previous.addEventListener("click", () => manual(Math.max(0, Number(input.value)-1)));
    next.addEventListener("click", () => manual(Math.min(8, Number(input.value)+1)));
    root.querySelector('[data-action="reset"]').addEventListener("click", () => manual(0));
    play.addEventListener("click", () => {
      if (timer !== null) { stop(); return; }
      if (reduced.matches) return;
      if (Number(input.value)===8) input.value="0";
      view(root, "result").setAttribute("aria-live", "off");
      play.textContent="暂停";
      render();
      timer=setInterval(() => {
        input.value=String(Number(input.value)+1);
        if (Number(input.value)>=8) stop();
        render();
      }, 650);
    });
    function motionPreference() {
      stop(); play.disabled=reduced.matches;
      view(root,"status").textContent=reduced.matches ?
        "系统启用了减少动态效果，可用滑块或上一点 / 下一点逐点查看。" :
        "每次前进一个采样间隔 0.125 µs；播放仅用于慢放观察。";
    }
    reduced.addEventListener("change", motionPreference);
    document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
    window.addEventListener("pagehide", stop);
    motionPreference(); render(); resize(root, render);
  }
  function mountLayout(root) {
    function render() {
      const s=layout(...["n","m","tx","rx"].map((k)=>Number(control(root,k).value)));
      const words=view(root,"words"); words.replaceChildren();
      for (let k=0;k<8;k++) {
        const selected=k===s.rx || k===s.rx+4;
        const cell=html("div", { class:"lab-cell" + (selected ? " is-active" : "") });
        cell.append(html("span", {}, (k<4 ? "I" : "Q") + " · RX" + (k%4+1)),
          html("strong", {}, String(s.group*8+k+1)),
          html("small", {}, "raw[" + (s.group*8+k) + "]"));
        words.append(cell);
      }
      view(root,"slice-title").textContent="固定虚拟通道 p = " + s.channel +
        "（TX" + (s.tx+1) + " / RX" + (s.rx+1) + "），取出 2 × 2 矩阵：";
      const table=html("table",{class:"lab-table","aria-label":"选定虚拟通道的采样点与轮次矩阵"});
      const header=html("tr"); ["n ↓ / m →","m = 0","m = 1"].forEach((s)=>header.append(html("th",{scope:"col"},s)));
      table.append(header);
      for(let n=0;n<2;n++) {
        const row=html("tr"); row.append(html("th",{scope:"row"},"n = "+n));
        for(let m=0;m<2;m++) {
          const a=layout(n,m,s.tx,s.rx);
          row.append(html("td",{class:n===s.n && m===s.m ? "is-active" : ""},
            a.i+" + "+a.q+"j"));
        }
        table.append(row);
      }
      view(root,"matrix").replaceChildren(table);
      view(root,"result").textContent="选中值：" + s.i + " + " + s.q + "j；I 来自 raw[" +
        s.iIndex + "]，Q 来自 raw[" + s.qIndex + "]（零起始索引）。";
      view(root,"indices").textContent="Python：frame[" + [s.n,s.m,s.channel].join(", ") +
        "]；MATLAB：frame(" + [s.n+1,s.m+1,s.channel+1].join(", ") + ")。";
    }
    root.querySelectorAll("select").forEach((input)=>input.addEventListener("change",render));
    render();
  }
  function mountDFT(root) {
    function render() {
      const k=Number(control(root,"bin").value), s=dft(k);
      const table=html("table",{class:"lab-table","aria-label":"DFT 矩阵，选中第 "+k+" 行"});
      const header=html("tr"); ["F₄","n=0","n=1","n=2","n=3"].forEach((v)=>header.append(html("th",{scope:"col"},v)));
      table.append(header);
      for(let row=0;row<4;row++) {
        const tr=html("tr",{class:row===k ? "is-active" : ""});
        tr.append(html("th",{scope:"row"},"k="+row));
        dft(row).row.forEach((z)=>tr.append(html("td",{},complex(z))));
        table.append(tr);
      }
      [["输入 x[n]",s.input],["逐项乘积",s.products]].forEach(([label,values])=>{
        const tr=html("tr",{class:"lab-product"}); tr.append(html("th",{scope:"row"},label));
        values.forEach((z)=>tr.append(html("td",{},complex(z)))); table.append(tr);
      });
      view(root,"matrix").replaceChildren(table);
      view(root,"result").textContent="选中行与输入逐项相乘，再求和：X[" + k + "] = " +
        s.products.map((z)=>"("+complex(z)+")").join(" + ") + " = " + complex(s.sum);
    }
    control(root,"bin").addEventListener("change",render); render();
  }
  function mount() {
    document.querySelectorAll(".signal-lab[data-lab]").forEach((root)=>{
      if(root.dataset.ready) return;
      root.hidden=false;
      ({echo:mountEcho, iq:mountIQ, layout:mountLayout, dft:mountDFT})[root.dataset.lab](root);
      root.dataset.ready="true";
    });
  }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",mount);
  else mount();
})();
