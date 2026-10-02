/* Shared by the local browser and behavior tests; no service, storage or requests. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FieldbookSearch = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const normalize = value => String(value).normalize('NFKC').toLocaleLowerCase().replace(/\s+/g, ' ').trim();
  // These phrases name reading intentions. They only match words already in a section.
  const aliases = [
    { phrases: ['任务重复', '重复执行'], words: ['重复', '不止一次', '重试', '幂等'], intent: 'repeat' },
    { phrases: ['断了怎么办', '中断恢复'], words: ['恢复', '租约', '接管'], intent: 'recover' },
    { phrases: ['外网访问'], words: ['tunnel'], intent: 'tunnel' },
    { phrases: ['绑定'], words: ['绑定', 'binding'], intent: 'binding' },
  ];
  function parse(query) {
    let remaining = normalize(query);
    const groups = [], intents = [];
    for (const alias of aliases) {
      for (const phrase of alias.phrases) {
        if (remaining.includes(phrase)) {
          remaining = remaining.split(phrase).join(' ');
          groups.push(alias.words); intents.push(alias.intent);
        }
      }
    }
    groups.push(...remaining.split(/\s+/).filter(Boolean).map(word => [word]));
    if (groups.some(group => group.includes('租约') || group.includes('lease'))) intents.push('lease');
    return { groups, intents, terms: [...new Set(groups.flat())] };
  }
  function search(data, query) {
    const parsed = parse(query);
    if (!parsed.groups.length) return [];
    return data.filter(item => !['draft', 'withdrawn'].includes(item.status)).map((item, order) => {
      const section = normalize((item.context || '') + ' ' + (item.section || ''));
      const heading = normalize(item.section || '');
      const context = normalize(item.context || '');
      const body = normalize(item.text);
      const title = normalize(item.title);
      const haystack = title + ' ' + section + ' ' + body;
      if (!parsed.groups.every(group => group.some(word => haystack.includes(word)))) return null;
      let score = parsed.groups.reduce((sum, group) => sum + Math.max(...group.map(word =>
        (heading.includes(word) ? 14 : 0) + (body.includes(word) ? 7 : 0) +
        (context.includes(word) ? 4 : 0) + (title.includes(word) ? 3 : 0))), 0);
      if (!body) score -= 15;
      const url = item.url;
      const handbook = url.startsWith('guides/handbook.html');
      const recovery = url.startsWith('use-cases/recoverable-jobs.html');
      const mechanism = recovery || handbook || url.startsWith('reference/implementation.html') || url.startsWith('examples/job-state/');
      if (parsed.intents.includes('repeat') && ((handbook && section.startsWith('06')) || recovery)) score += 80;
      if (parsed.intents.includes('recover') && recovery) score += 100;
      if (parsed.intents.includes('tunnel') && ((handbook && section.startsWith('04')) || (url.startsWith('reference/implementation.html') && section.startsWith('06')))) score += 80;
      if (parsed.intents.includes('binding') && handbook && normalize(item.section || '').startsWith('绑定')) score += 100;
      if (parsed.intents.includes('lease') && mechanism && body.includes('租约')) score += 80;
      if (parsed.intents.includes('lease') && mechanism && item.section && body.includes('租约')) score += 18;
      if (item.kind === '资料维护') score -= 25;
      if (item.status !== 'current') score -= 12;
      return { ...item, score, order, terms: parsed.terms };
    }).filter(Boolean).sort((a, b) => b.score - a.score || a.order - b.order);
  }
  return { normalize, parse, search };
});
