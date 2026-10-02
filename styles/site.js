/* All search and reading interactions are local; no requests or storage. */
(() => {
  'use strict';
  const mobile = window.matchMedia('(max-width: 720px)');
  for (const contents of document.querySelectorAll('.contents details')) {
    contents.open = !mobile.matches;
  }
  const input = document.getElementById('search-input');
  if (!input) return;
  const data = JSON.parse(document.getElementById('search-data').textContent);
  const output = document.getElementById('search-results');
  const status = document.getElementById('search-status');
  const directory = document.getElementById('reading-directory');
  input.disabled = false;
  status.textContent = '搜索标题与全文；不会上传输入。';
  const appendHighlighted = (element, text, terms) => {
    const lower = text.toLocaleLowerCase();
    let cursor = 0;
    while (cursor < text.length) {
      let start = -1, matched = '';
      for (const term of terms) {
        const position = lower.indexOf(term, cursor);
        if (position !== -1 && (start === -1 || position < start)) {
          start = position; matched = term;
        }
      }
      if (start === -1) { element.append(text.slice(cursor)); break; }
      element.append(text.slice(cursor, start));
      const mark = document.createElement('mark');
      mark.textContent = text.slice(start, start + matched.length);
      element.append(mark); cursor = start + matched.length;
    }
  };
  input.addEventListener('input', () => {
    const query = input.value.trim();
    const terms = query.toLocaleLowerCase().split(/\s+/).filter(Boolean);
    output.replaceChildren();
    output.hidden = !terms.length;
    directory.hidden = !!terms.length;
    if (!terms.length) { status.textContent = '搜索标题与全文；不会上传输入。'; return; }
    const found = data.filter(item => terms.every(term =>
      (item.title + ' ' + item.text).toLocaleLowerCase().includes(term)));
    status.textContent = found.length ? `找到 ${found.length} 篇资料。` : '没有找到匹配资料。试试更短的词，或清空搜索回到目录。';
    for (const item of found) {
      const row = document.createElement('li'); row.className = 'search-result';
      const kind = document.createElement('span'); kind.className = 'result-kind'; kind.textContent = item.kind;
      const link = document.createElement('a'); link.href = item.url;
      appendHighlighted(link, item.title, terms);
      const snippet = document.createElement('p');
      const first = Math.max(0, item.text.toLocaleLowerCase().indexOf(terms[0]) - 38);
      appendHighlighted(snippet, (first ? '…' : '') + item.text.slice(first, first + 160) + '…', terms);
      row.append(kind, link, snippet); output.append(row);
    }
  });
})();
