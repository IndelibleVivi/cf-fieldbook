"""Build-time execution of the existing offline Jobs model for the reading demo.

The browser selects recorded frames; it does not implement job transitions.
"""
from __future__ import annotations

import html
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory


DEFINITIONS = [
    ('normal', '正常完成', '登记、领取、完成各有自己的状态。', 'done 之后重复领取仍被拒绝。'),
    ('interrupted', '中断与接管', 'worker A 退出，数据库留住了租约。', '租约到期允许接管；到期并不证明旧 worker 已停止。'),
    ('stale', '迟到的旧结果', '新 generation 接管后，旧 worker 回来提交。', 'generation 保护本地提交；旧持有者不能覆盖新一轮结果。'),
    ('uncertain', '响应丢失', '合成外部服务记下动作，worker 只收到 timeout。', 'uncertain 停止自动领取，需要外部核对；本模型没有人工裁决接口。'),
    ('crash-window', '未解决的崩溃窗口', '外部动作成功后、uncertain 落盘前，worker 退出。', '此模型会允许再次领取：没有外部幂等边界，动作可能重复。'),
]


def scenarios(root: Path) -> list[dict]:
    """Execute five synthetic scenarios against real SQLite, including reconnects."""
    spec = importlib.util.spec_from_file_location('fieldbook_recovery_jobs', root / 'examples/job-state/model.py')
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    output = []
    for identifier, title, summary, lesson in DEFINITIONS:
        with TemporaryDirectory() as directory:
            db_path = str(Path(directory) / 'synthetic.sqlite3')
            jobs = model.Jobs(db_path)
            connection = 1
            ledger: dict[str, int] = {}
            events = []
            job_id = 'synthetic-job'
            tokens: dict[str, int] = {}

            def record(time, event, operation, result, explanation, worker='—'):
                state, generation, lease = jobs.db.execute(
                    'SELECT state,generation,lease_until FROM jobs WHERE id=?', (job_id,)
                ).fetchone()
                events.append(dict(time=time, event=event, operation=operation, result=result,
                                   explanation=explanation, worker=worker, state=state,
                                   generation=generation, lease_until=lease,
                                   external_count=ledger.get(job_id, 0), connection=connection))

            def claim(time, worker, explanation):
                result = jobs.claim(job_id, now=time, lease_seconds=30)
                if result is not None:
                    tokens[worker] = result
                record(time, f'{worker} 尝试领取', f'claim(now={time}, lease_seconds=30)', result, explanation, worker)

            def finish(time, worker, outcome, explanation):
                result = jobs.finish(job_id, tokens[worker], now=time, outcome=outcome)
                record(time, f'{worker} 提交 {outcome}',
                       f'finish(generation={tokens[worker]}, now={time}, outcome="{outcome}")',
                       result, explanation, worker)

            def reopen(time, explanation):
                nonlocal jobs, connection
                jobs.close()
                jobs = model.Jobs(db_path)
                connection += 1
                record(time, 'worker 退出，连接重开', 'close(); Jobs(same_database)', None, explanation)

            jobs.enqueue(job_id)
            record(0, '任务已登记', 'enqueue("synthetic-job")', None, '任务表为 pending、generation 0。登记只确认接收，尚未完成。')
            claim(1, 'A', '返回 generation 1；原子领取把状态改为 running，租约截止 t=31。')
            if identifier == 'normal':
                finish(8, 'A', 'done', '返回 True。generation 匹配且 t=8 < 31，结果被接受，租约清零。')
                claim(10, 'B', '返回 None。done 不在可领取状态中，重复到达不会再执行。')
                end = 10
            elif identifier in {'interrupted', 'stale'}:
                reopen(4, '合成 worker A 中断；关闭后重开同一个 SQLite 文件。running、generation 1 与租约都还在。')
                claim(30, 'B', '返回 None。t=30 < 31，仍在租约内；数据库拒绝再次领取。')
                claim(31, 'B', '返回 generation 2。边界 t=31 满足 lease_until <= now，B 接管并获得截止 t=61 的新租约。')
                if identifier == 'stale':
                    finish(32, 'A', 'done', '返回 False。旧 generation 1 与当前 2 不匹配；状态仍为 running，B 的结果没有被覆盖。')
                finish(35, 'B', 'done', '返回 True。generation 2 匹配且新租约有效，恢复后的本地工作完成。')
                claim(40, 'A', '返回 None。完成后的重复领取不会再执行。')
                end = 40
            else:
                ledger[job_id] = 1
                record(3, '外部动作成功，响应丢失', 'synthetic_ledger["synthetic-job"] += 1; TimeoutError', 'timeout',
                       '这是合成外部流水：动作次数为 1。worker 只观察到 timeout，无法由响应判断成功与否。', 'A')
                if identifier == 'uncertain':
                    finish(4, 'A', 'uncertain', '返回 True。在有效租约内把未知结果落盘为 uncertain，租约清零。')
                    reopen(5, '重开后读到 uncertain、generation 1。未知结果由数据库保留。')
                    claim(31, 'B', '返回 None。即使旧租约已到期，uncertain 也不在可领取状态中。')
                    claim(60, 'B', '返回 None。继续等待不会自动重放；合成外部流水仍为 1，核对与裁决需要另行设计。')
                    end = 60
                else:
                    reopen(4, 'A 在写入 uncertain 前崩溃。任务表仍为 running，表里没有外部成功的证据。')
                    claim(30, 'B', '返回 None。租约仍保护本地领取，但不提供外部动作的结果证据。')
                    claim(31, 'B', '返回 generation 2。模型允许接管；它无法知道上一轮外部动作已成功。')
                    ledger[job_id] += 1
                    record(32, '重放产生第二次合成动作', 'synthetic_ledger["synthetic-job"] += 1', 2,
                           '合成流水变为 2，演示了重复副作用风险。真实动作必须先有稳定 idempotency key、结果查询或核对机制。', 'B')
                    finish(35, 'B', 'done', '本地 finish 返回 True，任务表可以成为 done；外部动作却已发生两次。done 本身无法证明恰好执行一次。')
                    end = 40
            jobs.close()
            frames = []
            event_index = 0
            for time in range(end + 1):
                while event_index + 1 < len(events) and events[event_index + 1]['time'] <= time:
                    event_index += 1
                event = events[event_index]
                frame = dict(event, time=time, event_time=event['time'], event_index=event_index)
                frame['lease_remaining'] = max(0, event['lease_until'] - time) if event['state'] == 'running' else 0
                frames.append(frame)
            output.append(dict(id=identifier, title=title, summary=summary, lesson=lesson,
                               frames=frames, events=events))
    return output


def page_body(root: Path) -> str:
    data = scenarios(root)
    esc = html.escape
    options = ''.join(f'<option value="{item["id"]}">{index:02d} · {esc(item["title"])}</option>' for index, item in enumerate(data, 1))
    overview = ''.join(
        f'<details><summary>{index:02d} · {esc(item["title"])}</summary><p>{esc(item["summary"])} {esc(item["lesson"])}</p><ol>'
        + ''.join(f'<li><code>t={event["time"]}</code> {esc(event["event"])}：<code>{esc(str(event["result"]))}</code>；{esc(event["state"])} / generation {event["generation"]}。{esc(event["explanation"])}</li>' for event in item['events'])
        + '</ol></details>' for index, item in enumerate(data, 1))
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    return f'''<div class="recovery-page">
<div class="recovery-breadcrumb"><a href="README.html">任务恢复 · 示例说明</a><span>/</span>机制观察台</div>
<header class="recovery-intro"><div><p class="eyebrow">OFFLINE LAB / 合成场景</p><h1>任务停了，<br>下一步由谁接手？</h1><p>拨动模拟时钟，观察租约、generation 与未知结果如何决定下一次操作。</p></div><img src="../../assets/motifs/cat-sunrise.svg" alt="" width="280" height="180"></header>
<p class="recovery-provenance">每一步来自构建时实际执行的 <a href="model.py">SQLite Jobs 模型</a>。浏览器回放记录；没有网络调用、真实外部动作或 Cloudflare 实测。</p>
<section id="recovery-interactive" hidden aria-label="任务恢复机制观察台">
<div class="recovery-scenario"><label for="recovery-scenario">选择一个故障场景</label><select id="recovery-scenario">{options}</select><p id="recovery-summary"></p></div>
<div class="recovery-console">
<div class="recovery-controls"><div class="recovery-clock"><span>模拟时钟</span><output id="recovery-time" for="recovery-scrub">t = 0 s</output><span id="recovery-step"></span></div>
<p id="recovery-context" class="recovery-mobile-context"></p><label class="recovery-scrub-label" for="recovery-scrub">调节时间 <span>逐秒拖动 · 方向键微调</span></label><input id="recovery-scrub" type="range" min="0" max="10" value="0" step="1">
<div class="recovery-buttons"><button id="recovery-play" type="button">播放</button><button id="recovery-prev" type="button">上一步</button><button id="recovery-next" type="button">下一步</button><button id="recovery-reset" type="button">重置</button><label for="recovery-speed">回放<select id="recovery-speed"><option value="600">1×</option><option value="200">3×</option><option value="80">快览</option></select></label></div></div>
<div class="recovery-observation"><div class="recovery-facts"><div class="recovery-state"><span>任务表 / synthetic-job</span><strong id="recovery-state">pending</strong><p>generation <b id="recovery-generation">0</b></p></div><div class="recovery-lease"><span>本地租约</span><p id="recovery-lease">无有效租约</p><div class="recovery-lease-track" aria-hidden="true"><i id="recovery-lease-bar"></i></div><small id="recovery-connection"></small></div><div class="recovery-ledger"><span>合成外部流水</span><strong id="recovery-ledger">0</strong><p>已记录的动作次数</p></div></div>
<ol class="recovery-rail" aria-label="任务状态轨道"><li data-state="pending">pending<span>登记</span></li><li data-state="running">running<span>持有租约</span></li><li data-state="done">done<span>完成</span></li><li data-state="uncertain">uncertain<span>停下核对</span></li></ol>
<div class="recovery-event" role="status" aria-live="polite" aria-atomic="true"><div class="recovery-event-heading"><p id="recovery-event-time"></p><h2 id="recovery-event"></h2><strong id="recovery-result"></strong></div><code id="recovery-operation"></code><p id="recovery-explanation"></p></div></div>
<div class="recovery-timeline"><div><p class="eyebrow">事件时间轴</p><p>点选节点可直接跳到该步。</p></div><ol id="recovery-timeline"></ol></div>
<p id="recovery-lesson" class="recovery-lesson"></p>
</div></section>
<section id="recovery-fallback" class="recovery-static"><h2 id="execution-paths">五条真实执行路径</h2><p>交互回放需要 JavaScript；以下步骤在构建时由同一模型执行，始终可阅读。</p>{overview}</section>
<div class="recovery-notes"><h2 id="design-boundaries">把观察带回设计</h2><p>自动接管只适用于本地可重做的工作，或已经有外部幂等边界的工作。generation 只能保护本地状态，不能撤回外部动作。此模型没有队列 consumer、D1 适配、outbox、退避预算、DLQ 或人工裁决接口。</p><p>在仓库根目录运行 <code>python3 examples/job-state/demo.py</code> 可查看原始终端演示。</p><nav aria-label="继续阅读"><a href="../../use-cases/recoverable-jobs.html">阅读恢复机制与使用条件</a><a href="README.html">示例说明与离线附件</a><a href="demo.py" download>下载 demo.py</a></nav></div>
</div><script id="recovery-data" type="application/json">{encoded}</script>'''
