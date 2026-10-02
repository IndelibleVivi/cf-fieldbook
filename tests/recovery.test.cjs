/* Exercise the actual playback controller with a deterministic DOM and clock.
   Scenario records still come from executing Python Jobs, never a JS job model. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const generated = spawnSync('python3', ['-c', 'import json; from pathlib import Path; from tools.recovery_demo import scenarios; print(json.dumps(scenarios(Path.cwd())))'], {cwd: root, encoding: 'utf8'});
assert.equal(generated.status, 0, generated.stderr);
const records = JSON.parse(generated.stdout);

class Element {
  constructor() {
    this.textContent = ''; this.value = ''; this.children = []; this.attributes = {};
    this.dataset = {}; this.style = {}; this.listeners = {}; this.hidden = false;
    const classes = new Set();
    this.classList = {toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); }, contains(name) { return classes.has(name); }};
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  removeAttribute(key) { delete this.attributes[key]; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  querySelectorAll() { return this.children.flatMap(child => child.children); }
  fire(name, value) { if (value !== undefined) this.value = value; this.listeners[name]({target: this}); }
}
function setup() {
  const elements = new Map();
  const get = name => { if (!elements.has(name)) elements.set(name, new Element()); return elements.get(name); };
  get('data').textContent = generated.stdout;
  get('speed').value = '600';
  const rail = ['pending', 'running', 'done', 'uncertain'].map(state => { const node = new Element(); node.dataset.state = state; return node; });
  const timers = new Map(); let timerId = 0;
  const document = {getElementById: id => get(id.replace('recovery-', '')), createElement: () => new Element(), querySelectorAll: () => rail, addEventListener() {}, hidden: false};
  const window = {setInterval(fn) { timers.set(++timerId, fn); return timerId; }, clearInterval(id) { timers.delete(id); }};
  vm.runInNewContext(fs.readFileSync(path.join(root, 'styles/recovery.js'), 'utf8'), {document, window});
  const tick = count => { for (let index = 0; index < count; index++) [...timers.values()].forEach(fn => fn()); };
  return {get, timers, tick, rail};
}

test('play/pause is one timer, scenario switch cancels old playback, endpoint stops', () => {
  const {get, timers, tick} = setup();
  get('play').fire('click'); assert.equal(timers.size, 1);
  tick(2); assert.equal(get('time').textContent, 't = 2 s');
  get('play').fire('click'); assert.equal(timers.size, 0);
  tick(4); assert.equal(get('time').textContent, 't = 2 s');
  get('play').fire('click'); get('speed').fire('change', '80'); assert.equal(timers.size, 1);
  get('scenario').fire('change', 'stale'); assert.equal(timers.size, 0); assert.equal(get('time').textContent, 't = 0 s');
  get('play').fire('click'); tick(40); assert.equal(timers.size, 0);
  assert.equal(get('state').textContent, 'done'); assert.equal(get('play').textContent, '重新播放');
  tick(2); assert.equal(get('time').textContent, 't = 40 s');
  get('play').fire('click'); assert.equal(timers.size, 1); assert.equal(get('time').textContent, 't = 0 s');
});

test('scrubbing, event stepping, timeline and reset render the same recorded frame', () => {
  const {get, timers, rail} = setup();
  get('scenario').fire('change', 'stale'); get('play').fire('click');
  get('scrub').fire('input', '32'); assert.equal(timers.size, 0);
  assert.equal(get('state').textContent, 'running'); assert.equal(get('generation').textContent, 2);
  assert.equal(get('result').textContent, '返回 False'); assert.match(get('explanation').textContent, /旧 generation 1/);
  assert.equal(rail[1].attributes['aria-current'], 'step');
  get('prev').fire('click'); assert.equal(get('time').textContent, 't = 31 s');
  get('next').fire('click'); assert.equal(get('time').textContent, 't = 32 s');
  get('timeline').children[6].children[0].fire('click'); assert.equal(get('time').textContent, 't = 35 s');
  get('reset').fire('click'); assert.equal(get('time').textContent, 't = 0 s'); assert.equal(get('prev').disabled, true);
  get('scenario').fire('change', 'uncertain'); get('scrub').fire('input', '60');
  assert.equal(get('state').textContent, 'uncertain'); assert.equal(get('result').textContent, '返回 None');
  assert.equal(get('ledger').textContent, 1); assert.equal(get('next').disabled, true);
  get('scenario').fire('change', 'crash-window'); get('scrub').fire('input', '33');
  assert.equal(get('ledger').textContent, 2); assert.equal(get('ledger').dataset.duplicate, 'true');
  assert.match(get('explanation').textContent, /时钟推进到 t=33/);
  assert.equal(get('fallback').hidden, true); assert.equal(get('interactive').hidden, false);
  assert.equal(records.length, 5);
});
