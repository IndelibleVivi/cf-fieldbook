/* Reading interactions are local; no requests or storage. */
(() => {
  'use strict';
  const mobile = window.matchMedia('(max-width: 760px)');
  for (const contents of document.querySelectorAll('.contents details')) contents.open = !mobile.matches;

  const chapters = [...document.querySelectorAll('.contents a[href^="#"]')].map(link => ({
    link, heading: document.getElementById(decodeURIComponent(link.hash.slice(1))),
  })).filter(item => item.heading);
  if (chapters.length) {
    let scheduled = false;
    const locateChapter = () => {
      let current = chapters[0];
      for (const chapter of chapters) {
        if (chapter.heading.getBoundingClientRect().top <= 130) current = chapter;
        else break;
      }
      for (const chapter of chapters) {
        if (chapter === current) chapter.link.setAttribute('aria-current', 'location');
        else chapter.link.removeAttribute('aria-current');
      }
      scheduled = false;
    };
    window.addEventListener('scroll', () => {
      if (!scheduled) { scheduled = true; window.requestAnimationFrame(locateChapter); }
    }, { passive: true });
    window.addEventListener('hashchange', locateChapter);
    window.requestAnimationFrame(locateChapter);
  }

  // The demo's static model transcript is normally replaced by the replay. Search links
  // to its authored heading must still reveal the transcript and land on readable content.
  const revealTranscript = () => {
    const fallback = document.getElementById('recovery-fallback');
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (fallback && target && fallback.contains(target)) {
      fallback.hidden = false;
      target.scrollIntoView();
    }
  };
  revealTranscript();
  window.addEventListener('hashchange', revealTranscript);

  const dialog = document.getElementById('term-dialog');
  if (dialog) {
    const terms = JSON.parse(document.getElementById('term-data').textContent);
    let origin = null;
    document.addEventListener('click', event => {
      const link = event.target.closest('a[data-term]');
      if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const term = terms[link.dataset.term];
      if (!term || !dialog.showModal) return;
      event.preventDefault(); origin = link;
      document.getElementById('term-title').textContent = term.title;
      document.getElementById('term-definition').textContent = term.definition;
      document.getElementById('term-full-link').href = link.href;
      dialog.showModal();
      document.getElementById('term-close').focus();
    });
    document.getElementById('term-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => { if (origin) origin.focus({ preventScroll: true }); });
  }

  const input = document.getElementById('search-input');
  if (!input) return;
  const data = JSON.parse(document.getElementById('search-data').textContent);
  const api = window.FieldbookSearch;
  const output = document.getElementById('search-results');
  const status = document.getElementById('search-status');
  const directory = document.getElementById('reading-directory');
  input.disabled = false;
  const hint = '搜索到具体小节；多个词需同时匹配。输入留在本机。';
  status.textContent = hint;
  const highlight = (element, value, terms) => {
    const normalized = api.normalize(value);
    // NFKC can change length: display original text unless offsets remain equivalent.
    if (normalized.length !== value.length) { element.append(value); return; }
    let cursor = 0;
    while (cursor < value.length) {
      let start = -1, matched = '';
      for (const term of terms) {
        const position = normalized.indexOf(term, cursor);
        if (position !== -1 && (start === -1 || position < start || (position === start && term.length > matched.length))) {
          start = position; matched = term;
        }
      }
      if (start === -1) { element.append(value.slice(cursor)); break; }
      element.append(value.slice(cursor, start));
      const mark = document.createElement('mark'); mark.textContent = value.slice(start, start + matched.length);
      element.append(mark); cursor = start + matched.length;
    }
  };
  input.addEventListener('input', () => {
    const query = input.value.trim();
    output.replaceChildren(); output.hidden = !query; directory.hidden = !!query;
    if (!query) { status.textContent = hint; return; }
    const found = api.search(data, query);
    status.textContent = found.length ? `找到 ${found.length} 个阅读小节。` : '没有找到匹配小节。试试更短的词，或清空搜索回到目录。';
    for (const item of found) {
      const row = document.createElement('li'); row.className = 'search-result';
      const kind = document.createElement('span'); kind.className = 'result-kind';
      kind.textContent = item.kind + (item.status === 'archived' ? ' · 历史归档' : item.status === 'superseded' ? ' · 已有替代' : '');
      const link = document.createElement('a'); link.href = item.url;
      link.dataset.linkKind = 'internal'; link.setAttribute('aria-describedby', 'link-internal');
      const label = item.title + (item.section ? ' / ' + item.section : ' / 开篇');
      highlight(link, label, item.terms);
      const snippet = document.createElement('p');
      const normalized = api.normalize(item.text);
      const positions = item.terms.map(term => normalized.indexOf(term)).filter(position => position >= 0);
      const first = Math.max(0, (positions.length ? Math.min(...positions) : 0) - 38);
      const excerpt = item.text.slice(first, first + 155);
      highlight(snippet, (first ? '…' : '') + excerpt + (first + 155 < item.text.length ? '…' : ''), item.terms);
      row.append(kind, link);
      if (item.text) row.append(snippet);
      output.append(row);
    }
  });
})();
