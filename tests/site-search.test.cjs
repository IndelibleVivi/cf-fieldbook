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
test('resource operation questions reach concrete API guidance', () => {
  for (const query of ['SDK 分页', 'API 超时', '盘点不完整']) {
    const item = first(query);
    assert.ok(item.url.startsWith('reference/api-maintenance.html#'), item.url);
    assert.match(item.text, /分页|超时|期限|完整/);
  }
  assert.match(first('SDK 分页').section, /完整分页/);
  assert.match(first('API 超时').section, /超时与重试/);
});
test('project questions reach reasons, applicability and task scenarios', () => {
  for (const query of ['搬到 VPS', '发布变慢', '静态官网', '这次更新影响我吗', '以前为什么不用']) {
    const item = first(query);
    assert.ok(item.url.startsWith('use-cases/project-context.html#'), item.url);
    assert.ok(item.text.length > 80, 'The target must answer the question in its own section');
  }
  assert.match(first('搬到 VPS').section, /VPS/);
  assert.match(first('发布变慢').section, /发布越来越慢/);
  assert.match(first('静态官网').section, /官网/);
  assert.match(first('以前为什么不用').section, /采用理由/);
  assert.equal(search(index, '这次更新影响我吗 完全不存在的词').length, 0);
});
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

test('ordinary questions reach a section that actually answers them', () => {
  for (const query of ['网页怎么上线', '怎么部署网站', '怎样发布网页']) {
    const item = first(query);
    const body = normalize([item.section, item.text].join(' '));
    // The lead answers the query in its own body, and it is a reading page
    // (handbook, implementation reference or a practice note), not an index.
    assert.ok(/部署|发布|上线|release|workers|网页/.test(body), `${query}: first result must answer it`);
    assert.ok(/^(guides\/handbook|reference\/implementation|practice\/)/.test(item.url), item.url);
  }
  const r2 = first('R2价格');
  assert.ok(/r2/.test(normalize([r2.section, r2.text].join(' '))));
  assert.ok(/价格|存储|费用/.test(normalize([r2.section, r2.text].join(' '))));
});

test('product queries bind to stable chapter IDs, not displayed numbers', () => {
  // The handbook chapter IDs are stable; a fixture index records them per record.
  assert.ok(index.some(item => item.chapter === 'economics' && item.url.includes('guides/handbook.html#')));
  assert.ok(index.some(item => item.chapter === 'jobs'));
  assert.ok(index.some(item => item.chapter === 'workspace' && item.section.includes('agent')));
  const clef = first('Clef');
  assert.equal(clef.url.split('#')[0], 'comparisons/clef-vs-jev.html');
  assert.equal(clef.section, '', 'the whole-work landing record leads a product query');
});

test('Chinese text adjacent to a product name still resolves the product', () => {
  for (const query of ['用Clef', '用 Clef', '了解R2']) {
    const items = search(index, query);
    assert.ok(items.length, query);
    assert.ok(items.some(item => /clef|r2/i.test(item.url + ' ' + normalize(item.text))), query);
  }
  assert.deepEqual(search(index, '用Clef 不存在这个词987'), []);
});

test('current explanations beat dated reports unless the query asks for history', () => {
  const plain = search(index, '搜索');
  const firstReport = result => result.findIndex(item => item.url.startsWith('reports/'));
  assert.ok(firstReport(plain) !== 0, 'a dated report does not lead a plain query');
  // A dated report only enters when the query names its subject; the history keyword
  // removes the penalty rather than inventing matches that the body lacks.
  const dated = search(index, 'observability');
  assert.ok(dated.some(item => item.url.startsWith('reports/')) || dated.some(item => item.url.startsWith('services/')),
            'the query resolves to real sections');
  for (const item of dated) {
    const body = normalize([item.title, item.section, item.context, item.text].join(' '));
    assert.ok(body.includes('observability'), 'history preference keeps AND semantics');
  }
});

test('R2 cost aliases retain the product constraint and related results group by page', () => {
  const {group} = require('../styles/search.js');
  const items = search(index, 'R2价格');
  assert.ok(items.length);
  for (const item of items) assert.ok(normalize(item.title + ' ' + item.section + ' ' + item.text).includes('r2'));
  const groups = group(items);
  assert.equal(groups.flat().length, items.length);
  assert.equal(new Set(groups.map(items => items[0].url.split('#')[0])).size, groups.length);
  assert.equal(groups[0][0].url, items[0].url);
});
