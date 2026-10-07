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
    { phrases: ['外网访问', '内网穿透'], words: ['tunnel'], intent: 'tunnel' },
    { phrases: ['绑定'], words: ['绑定', 'binding'], intent: 'binding' },
    // 普通问法：网页怎样上线、网站怎样部署、成本与产品名。
    { phrases: ['怎么上线', '怎么部署', '怎样上线', '怎样部署', '上线网页', '部署网站', '发布网页'],
      words: ['部署', '发布', '上线', 'release', 'workers'], intent: 'release' },
    { phrases: ['r2价格', 'r2 价格', 'r2多少钱', 'r2 多少钱', 'r2费用', 'r2 费用', 'r2计费'],
      words: ['价格', '费用', '存储', '计费'], required: ['r2'], intent: 'r2' },
    { phrases: ['网页搜索', '搜索网页', '联网搜索'], words: ['web search', '搜索'], intent: 'websearch' },
    { phrases: ['临时执行环境', '跑 linux', '系统包'], words: ['containers', 'sandbox', '容器'], intent: 'workspace' },
    { phrases: ['sdk 分页', '盘点不完整'], words: ['分页', '迭代', '后页'], intent: 'api' },
    { phrases: ['api 超时'], words: ['超时', '期限', 'timeout'], intent: 'api' },
    { phrases: ['搬到 vps', '减少本机负担'], words: ['vps', '源设备', '运行位置'], intent: 'migration' },
    { phrases: ['发布变慢'], words: ['发布', '耗时', 'publisher'], intent: 'publishing' },
    { phrases: ['静态官网'], words: ['官网', '静态页面', '表单'], intent: 'static' },
    { phrases: ['这次更新影响我吗'], words: ['适用性', '命中', '未知'], intent: 'project' },
    { phrases: ['以前为什么不用', '为什么暂缓'], words: ['采用理由', '暂缓原因', '重评条件'], intent: 'reasons' },
  ];
  // Product/Works queries: prefer the whole-work or whole-section entry.
  const products = ['clef', 'jev', 'workers', 'worker', 'r2', 'd1', 'tunnel', 'access', 'queues',
    'workflows', 'durable objects', 'vectorize', 'ai gateway', 'workers ai', 'containers', 'sandbox',
    'observability', 'mcp', 'ai search'];
  // Stable chapter IDs (from `<!-- chapter: -->` markers) that answer an intent.
  const stable = {
    repeat: ['jobs'], recover: ['recovery'],
    tunnel: ['access'],
    release: ['first-worker', 'release'],
    r2: ['economics', 'content'],
    websearch: ['retrieval'],
    workspace: ['workspace'],
    observability: ['observability'],
    models: ['models'],
  };
  // A query that names a date or asks for history should lead with dated reports.
  const historyQuery = q => /(^|\s)(历史|当期|本期|旧版|过去|归档|report|报告|20\d{2}[-./]\d{1,2})/.test(q);
  // Question verbs that only frame a product name; they are not content terms.
  const filler = new Set(['了解', '看看', '怎么', '怎样', '如何', '什么', '关于', '想问', '查', '用', '读', '讲', '说']);
  const sectionId = url => {
    const hash = String(url).split('#')[1];
    return hash ? decodeURIComponent(hash) : '';
  };
  function parse(query) {
    let remaining = normalize(query);
    const groups = [], intents = [];
    for (const alias of aliases) {
      for (const phrase of alias.phrases) {
        if (remaining.includes(phrase)) {
          remaining = remaining.split(phrase).join(' ');
          groups.push(alias.words, ...(alias.required || []).map(word => [word])); intents.push(alias.intent);
        }
      }
    }
    // Split on whitespace and on CJK/ASCII boundaries so "用Clef" yields "Clef".
    const tokens = remaining
      .replace(/([\u3400-\u9fff])([A-Za-z0-9])/g, '$1 $2')
      .replace(/([A-Za-z0-9])([\u3400-\u9fff])/g, '$1 $2')
      .split(/\s+/).filter(Boolean);
    // A framing verb next to a product name is dropped; the product term carries the query.
    const hasProduct = tokens.some(word => products.includes(word));
    const content = hasProduct ? tokens.filter(word => !filler.has(word)) : tokens;
    const words = content.length ? content : tokens;
    groups.push(...words.map(word => [word]));
    if (groups.some(group => group.includes('租约') || group.includes('lease'))) intents.push('lease');
    const product = words.some(word => products.includes(word));
    const history = historyQuery(normalize(query));
    return { groups, intents, words, product, history, terms: [...new Set(groups.flat())] };
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
      const report = url.startsWith('reports/');
      const chapter = item.chapter || sectionId(url);
      const inChapter = ids => handbook && ids.includes(chapter);
      const mechanism = recovery || handbook || url.startsWith('reference/implementation.html') || url.startsWith('examples/job-state/');
      // Intents bind to stable chapter IDs, never to the displayed number.
      if (parsed.intents.includes('repeat') && (inChapter(stable.repeat) || recovery)) score += 80;
      if (parsed.intents.includes('recover') && recovery) score += 100;
      if (parsed.intents.includes('recover') && inChapter(stable.recover)) score += 55;
      if (parsed.intents.includes('tunnel') && (inChapter(stable.tunnel) || (url.startsWith('reference/implementation.html') && chapter))) score += 80;
      if (parsed.intents.includes('binding') && handbook && normalize(item.section || '').startsWith('绑定')) score += 100;
      if (parsed.intents.includes('release') && (inChapter(stable.release) || url.startsWith('reference/implementation.html'))) score += 60;
      if (parsed.intents.includes('r2') && inChapter(stable.r2)) score += 60;
      if (parsed.intents.includes('websearch') && inChapter(stable.websearch)) score += 50;
      if (parsed.intents.includes('workspace') && inChapter(stable.workspace)) score += 60;
      if (parsed.intents.includes('lease') && mechanism && body.includes('租约')) score += 80;
      if (parsed.intents.includes('lease') && mechanism && item.section && body.includes('租约')) score += 18;
      if (parsed.intents.includes('api') && url.startsWith('reference/api-maintenance.html#')) score += 90;
      if (parsed.intents.includes('project') && url.startsWith('use-cases/project-context.html#')) score += 90;
      if (url.startsWith('use-cases/project-context.html#')) {
        if (parsed.intents.includes('migration') && heading.includes('vps')) score += 110;
        if (parsed.intents.includes('publishing') && heading.includes('发布')) score += 110;
        if (parsed.intents.includes('static') && heading.includes('官网')) score += 110;
        if (parsed.intents.includes('reasons') && heading.includes('采用理由')) score += 110;
      }
      // Product/Work queries: the whole-work landing record leads, and the whole
      // section that owns the product groups just behind it.
      if (parsed.product) {
        const landing = !item.section && !item.context;
        if (landing) score += 45;
        if (item.kind === '比较' || item.kind === '手册') score += 18;
        // A whole work whose own title names the queried product leads outright.
        if (landing && parsed.words.some(word => normalize(item.title).includes(word))) score += 140;
        if (landing && parsed.terms.some(term => normalize(item.title).includes(term))) score += 60;
      }
      // Untagged queries prefer current explanations over dated reports; a query
      // that names a date or history flips that preference.
      if (report && !parsed.history) score -= 20;
      if (report && parsed.history) score += 20;
      // How-to questions answer in a section; a bare work landing should not top them.
      if (!parsed.product && item.text && !item.section) score -= 25;
      if (item.kind === '资料维护') score -= 25;
      if (item.status !== 'current') score -= 12;
      return { ...item, score, order, terms: parsed.terms };
    }).filter(Boolean).sort((a, b) => b.score - a.score || a.order - b.order);
  }
  function group(results) {
    const groups = new Map();
    for (const item of results) {
      const page = item.url.split('#')[0];
      if (!groups.has(page)) groups.set(page, []);
      groups.get(page).push(item);
    }
    return [...groups.values()];
  }
  return { normalize, parse, search, group };
});
