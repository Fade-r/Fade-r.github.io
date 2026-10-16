"use strict";
// Minimal DOM checks, not a browser substitute: exercise legacy API branches.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
class Element {
  constructor() {
    this.children = []; this.attributes = {}; this.listeners = {};
    this.dataset = {}; this.value = "0"; this.hidden = true;
  }
  get firstChild() { return this.children[0]; }
  append(...nodes) { this.children.push(...nodes); }
  appendChild(node) { this.append(node); }
  removeChild(node) { this.children.splice(this.children.indexOf(node), 1); }
  setAttribute(k, v) { this.attributes[k] = v; }
  getBoundingClientRect() { return {width: 280}; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  querySelector(selector) {
    this.parts ||= {};
    return this.parts[selector] ||= new Element();
  }
  querySelectorAll(selector) {
    return Object.entries(this.parts || {}).filter(([key]) => key.includes("data-control"))
      .map(([,node]) => node);
  }
}
const source = fs.readFileSync(path.resolve(__dirname,
  "../../../docs/wiki/content/assets/javascripts/signal-labs.js"), "utf8");
for (const modern of [false, true]) {
  const roots = ["echo", "iq", "layout", "dft"].map(type => {
    const root = new Element(); root.dataset.lab = type;
    for (const key of ["distance", "sample", "n", "m", "tx", "rx", "bin"]) {
      root.querySelector('[data-control="' + key + '"]').value = key === "distance" ? "15" : "0";
    }
    return root;
  });
  const doc = new Element(), win = new Element(), errors = [];
  doc.querySelectorAll = () => roots;
  doc.createElement = doc.createElementNS = () => new Element();
  const reduced = {matches: false};
  reduced[modern ? "addEventListener" : "addListener"] = (...args) => {
    reduced.callback = args[args.length - 1];
  };
  const context = {document: doc, window: win, matchMedia: () => reduced,
    console: {error: (...args) => errors.push(args)}, setInterval, clearInterval};
  if (modern) context.ResizeObserver = class { observe() {} };
  vm.runInNewContext(source, context);
  assert.equal(errors.length, 0);
  for (const root of roots) assert.equal(root.dataset.ready, "true");
  if (!modern) { assert.ok(win.listeners.resize); win.listeners.resize(); }
  reduced.matches = true; reduced.callback();
  assert.equal(roots[1].querySelector('[data-action="play"]').disabled, true);
  roots[0].querySelector('[data-control="distance"]').value = "30";
  roots[0].querySelector('[data-control="distance"]').listeners.input();
  assert.match(roots[0].querySelector('[data-view="result"]').textContent, /6.0 MHz/);
  roots[3].querySelector('[data-control="bin"]').value = "1";
  roots[3].querySelector('[data-control="bin"]').listeners.change();
  assert.match(roots[3].querySelector('[data-view="result"]').textContent, /= 4$/);
}
console.log("Modern/legacy resize and motion APIs: all four labs initialized; controls passed.");
