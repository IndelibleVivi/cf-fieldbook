/* Read recorded Jobs results. Job transitions run only in Python at build time. */
(() => {
  'use strict';
  const data = document.getElementById('recovery-data');
  if (!data) return;
  const scenarios = JSON.parse(data.textContent);
  const get = name => document.getElementById(`recovery-${name}`);
  let scenario = scenarios[0];
  let time = 0;
  let timer = null;
  const text = (name, value) => { get(name).textContent = value; };
  const resultText = value => value === null ? 'None' : value === true ? 'True' : value === false ? 'False' : String(value);

  function pause() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
    text('play', time === scenario.frames.length - 1 ? '重新播放' : '播放');
    get('play').setAttribute('aria-pressed', 'false');
  }

  function render() {
    const frame = scenario.frames[time];
    get('scrub').value = String(time);
    get('scrub').setAttribute('aria-valuetext', `模拟时间 ${time} 秒，${frame.state}，generation ${frame.generation}`);
    text('time', `t = ${time} s`);
    text('step', `事件 ${frame.event_index + 1} / ${scenario.events.length}`);
    text('state', frame.state);
    get('state').dataset.state = frame.state;
    text('generation', frame.generation);
    text('context', `${frame.state} · generation ${frame.generation}${frame.state === 'running' ? ` · 租约剩余 ${frame.lease_remaining} s` : ''}`);
    text('lease', frame.state === 'running' ? `截止 t=${frame.lease_until} · 剩余 ${frame.lease_remaining} s` : '无有效租约');
    get('lease-bar').style.width = `${frame.lease_remaining / 30 * 100}%`;
    text('connection', `SQLite 连接 #${frame.connection}${frame.connection > 1 ? ' · 已跨连接恢复' : ''}`);
    text('ledger', frame.external_count);
    get('ledger').dataset.duplicate = frame.external_count > 1 ? 'true' : 'false';
    text('event-time', `最近操作 t=${frame.event_time} · worker ${frame.worker}`);
    text('event', frame.event);
    text('operation', frame.operation);
    text('result', `返回 ${resultText(frame.result)}`);
    const waiting = time > frame.event_time ? `时钟推进到 t=${time}，这期间没有新的模型调用。` : '';
    text('explanation', waiting + frame.explanation);
    get('prev').disabled = time === 0;
    get('next').disabled = frame.event_index === scenario.events.length - 1;
    document.querySelectorAll('.recovery-rail li').forEach(node => {
      const current = node.dataset.state === frame.state;
      node.classList.toggle('is-current', current);
      if (current) node.setAttribute('aria-current', 'step');
      else node.removeAttribute('aria-current');
    });
    get('timeline').querySelectorAll('button').forEach((button, index) => {
      const current = index === frame.event_index;
      button.classList.toggle('is-current', current);
      button.classList.toggle('is-past', index < frame.event_index);
      if (current) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
  }

  function seek(nextTime) {
    pause();
    time = nextTime;
    render();
    // Seeking to the last frame changes the playback action to replay.
    text('play', time === scenario.frames.length - 1 ? '重新播放' : '播放');
  }

  function selectScenario(id) {
    pause();
    scenario = scenarios.find(item => item.id === id);
    time = 0;
    get('scrub').max = scenario.frames.length - 1;
    text('summary', scenario.summary);
    text('lesson', scenario.lesson);
    get('lesson').classList.toggle('is-warning', scenario.id === 'crash-window');
    get('timeline').replaceChildren(...scenario.events.map((event, index) => {
      const li = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('aria-label', `跳到 t=${event.time}：${event.event}`);
      const stamp = document.createElement('span');
      stamp.textContent = `t=${event.time}`;
      const label = document.createElement('span');
      label.textContent = event.event;
      button.append(stamp, label);
      button.addEventListener('click', () => seek(event.time));
      li.append(button);
      return li;
    }));
    render();
    text('play', '播放');
  }

  function play() {
    if (timer !== null) { pause(); return; }
    if (time === scenario.frames.length - 1) time = 0;
    text('play', '暂停');
    get('play').setAttribute('aria-pressed', 'true');
    render();
    timer = window.setInterval(() => {
      time += 1;
      render();
      if (time === scenario.frames.length - 1) pause();
    }, Number(get('speed').value));
  }

  get('scenario').addEventListener('change', event => selectScenario(event.target.value));
  get('scrub').addEventListener('input', event => seek(Number(event.target.value)));
  get('play').addEventListener('click', play);
  get('reset').addEventListener('click', () => seek(0));
  get('prev').addEventListener('click', () => {
    const previous = scenario.events.filter(event => event.time < time).at(-1);
    seek(previous ? previous.time : 0);
  });
  get('next').addEventListener('click', () => {
    const next = scenario.events.find(event => event.time > time);
    if (next) seek(next.time);
  });
  get('speed').addEventListener('change', () => {
    if (timer !== null) { pause(); play(); }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  selectScenario(scenario.id);
  get('fallback').hidden = true;
  get('interactive').hidden = false;
})();
