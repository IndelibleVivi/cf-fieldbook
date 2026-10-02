/* Real query behavior against the generated Markdown/catalog section index. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { search, normalize } = require('../styles/search.js');
const root = path.resolve(__dirname, '..');
let generated;
if (!process.env.FIELDBOOK_SEARCH_INDEX) {
  generated = path.join(root, '.build/qa/reader-evolution', `search-tests-${process.pid}`);
  const python = fs.existsSync(path.join(root, '.venv/bin/python')) ? path.join(root, '.venv/bin/python') : 'python3';
  const result = spawnSync(python, ['-B', path.join(root, 'tools/build_site.py'), '--output', generated], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
}
const index = JSON.parse(fs.readFileSync(process.env.FIELDBOOK_SEARCH_INDEX || path.join(generated, 'search-index.json'), 'utf8'));
if (generated) test.after(() => fs.rmSync(generated, { recursive: true }));
const first = query => { const result = search(index, query); assert.ok(result.length, query); return result[0]; };
test('real index contains h2 and h3 records with stable section links', () => {
  assert.ok(index.some(item => item.url.startsWith('guides/handbook.html#') && item.section.startsWith('06 /')));
  assert.ok(index.some(item => item.section.startsWith('绑定：') && item.url.includes('#')));
  assert.ok(index.every(item => !['draft', 'withdrawn'].includes(item.status)));
});
test('repeat questions lead to the actual task mechanism chapter', () => {
  for (const query of ['任务重复', '重复执行']) {
    const item = first(query);
    assert.ok((item.url.startsWith('guides/handbook.html#') && item.context.startsWith('06 /')) || item.url.startsWith('use-cases/recoverable-jobs.html#'), item.url);
    assert.ok(item.text.includes('重复'), 'First result must explain repetition in its own body, not only match a parent heading');
  }
});
test('interruption questions lead to the recovery use case', () => {
  for (const query of ['断了怎么办', '中断恢复']) assert.ok(first(query).url.startsWith('use-cases/recoverable-jobs.html#'));
});
test('Tunnel external access leads to chapter 04 or implementation route C', () => {
  for (const query of ['Tunnel 外网访问', 'ＴＵＮＮＥＬ　外网访问']) {
    const item = first(query);
    assert.ok((item.url.startsWith('guides/handbook.html#') && item.context.startsWith('04 /')) || (item.url.startsWith('reference/implementation.html#') && item.context.startsWith('06 /')));
  }
});
test('binding and lease prioritize explanatory sections', () => {
  assert.ok(first('绑定').url.startsWith('guides/handbook.html#'));
  assert.ok(first('绑定').section.startsWith('绑定：'));
  const item = first('租约');
  assert.ok(item.url.includes('#'));
  assert.ok(['手册', '用途', '实施参考', '例子'].includes(item.kind));
});
test('aliases preserve every extra query constraint and ordinary AND semantics', () => {
  assert.deepEqual(search(index, '任务重复 不存在这个词987'), []);
  assert.deepEqual(search(index, '断了怎么办 不存在这个词987'), []);
  const items = search(index, '租约 uncertain');
  assert.ok(items.length);
  for (const item of items) {
    const body = normalize([item.title, item.section, item.context, item.text].join(' '));
    assert.ok(body.includes('租约') && body.includes('uncertain'));
  }
  assert.equal(normalize('ＱＵＥＵＥＳ　ＡＣＫ'), 'queues ack');
});
