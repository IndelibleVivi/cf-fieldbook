#!/usr/bin/env python3
"""Readable catalog projections. Only explicit `sync` edits maintained Markdown."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PAGE_BLOCKS = {'services/decision-models.md': {'cf-routes'},
               'comparisons/clef-vs-jev.md': {'all-routes', 'costs', 'contexts'},
               'guides/handbook.md': {'cf-routes', 'observability-costs'},
               'services/observability.md': {'observability-costs'}}
PAGES = tuple(PAGE_BLOCKS)
BLOCK = re.compile(r'<!-- facts: ([a-z-]+) -->\n.*?<!-- /facts -->', re.S)


def cell(value: object) -> str:
    return str(value).replace('|', '\\|').replace('\n', ' ')


def tables(root: Path) -> dict[str, str]:
    routes = json.loads((root / 'catalog/decision-routes.json').read_text())['routes']
    sources = {s['id']: s for s in json.loads((root / 'catalog/sources.json').read_text())}
    spec = importlib.util.spec_from_file_location('fieldbook_costs', root / 'examples/decision-routing/payloads.py')
    costs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(costs)

    def source(row):
        return ' '.join(f"[{s}]({sources[s]['url']})" for s in row['sources'])

    def route(row):
        return cell(f"{row['gateway'] or row['model_author'] + ' 原厂'} → {row['model']}")

    def price(row):
        value = row['input_usd_per_million']
        return cell(value if value is not None else '未知；目录显示 ' + row.get('display_price', '未提供'))

    def route_table(rows):
        lines = ['| 路线（接入 → 模型） | 模型选择器 | 输入 USD / 百万 token | 来源 |', '|---|---|---:|---|']
        for row in rows:
            lines.append(f"| {route(row)} | `{cell(row['selector'])}` | {price(row)} | {source(row)} |")
        return '\n'.join(lines)

    cf = [row for row in routes if row['id'].startswith('cf-')]
    estimate = ['| 路线 | 输入用量假设 | 模型输入费用 |', '|---|---|---:|']
    for row in cf:
        value = row['input_usd_per_million']
        amount = f"${costs.input_cost(50_000_000, value):.2f}" if value is not None else '未知，不能计算'
        tokenizer = row.get('tokenizer') or '未核实'
        estimate.append(f"| {route(row)} | 50,000,000 计费 token；tokenizer：{cell(tokenizer)} | {amount} |")
    contexts = ['| 路线 | 此入口的上下文说明 | 来源 |', '|---|---|---|']
    for row in routes:
        contexts.append(f"| {route(row)} | {cell(row['context'])} | {source(row)} |")
    return {'cf-routes': route_table(cf), 'all-routes': route_table(routes),
            'costs': '\n'.join(estimate), 'contexts': '\n'.join(contexts)}


def observability_costs(root: Path, as_of: str) -> str:
    """Project announced fees using a fixed editorial date, never the reader's clock."""
    from datetime import date
    date.fromisoformat(as_of)
    data = json.loads((root / 'catalog/observability-pricing.json').read_text())
    launch = next(row for row in json.loads((root / 'catalog/launches.json').read_text())
                  if row['id'] == data['launch_id'])
    effective = next(event['date'] for event in launch['effective_events'] if event['kind'] == 'billing_start')
    current, announced = data['current'], data['announced']
    phase = '已公布；将在 ' + effective + ' 生效' if as_of < effective else '按已公布条款于 ' + effective + ' 生效；未因此刷新核验'
    lines = [f'固定资料日期：**{as_of}**。', '',
             '| 条款 | Free | Paid |', '|---|---|---|']
    if as_of < effective:
        lines.append(f"| 当前 Workers Logs [{current['source']}] | {current['free_events_per_day']:,} events / 日；{current['free_retention_days']} 天 | {current['paid_events_per_month']:,} events / 月；超出 ${current['extra_usd_per_million']:.2f} / 百万；{current['paid_retention_days']} 天 |")
    lines.append(f"| {phase} [{announced['source']}] | {announced['free_ingestion_gb_per_day']} GB 摄取 / 日；{announced['retention_days']} 天 | {announced['paid_ingestion_gb_per_cycle']} GB 摄取 + {announced['paid_storage_gb_month_per_cycle']} GB-month / billing cycle；超出 ${announced['extra_ingestion_usd_per_gb']:.2f} / GB + ${announced['extra_storage_usd_per_gb_month']:.2f} / GB-month |")
    return '\n'.join(lines)


def project_markdown(root: Path, relative_path: str, *, as_of: str | None = None) -> str:
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Markdown path escapes root')
    text = path.read_text(encoding='utf-8')
    # Edition reports own their frozen text and source definitions, including prices.
    if relative_path not in PAGES:
        return text
    markers = [m[1] for m in BLOCK.finditer(text)]
    if set(markers) != PAGE_BLOCKS[relative_path] or len(markers) != len(set(markers)):
        raise ValueError(f'missing, duplicate or unknown fact block in {relative_path}')
    blocks = tables(root) if 'cf-routes' in markers or 'all-routes' in markers else {}
    if 'observability-costs' in markers:
        cutoff = re.search(r'^source_cutoff: (\d{4}-\d{2}-\d{2})$', text, re.M)[1]
        blocks['observability-costs'] = observability_costs(root, as_of or cutoff)
    return BLOCK.sub(lambda m: f'<!-- facts: {m[1]} -->\n{blocks[m[1]]}\n<!-- /facts -->', text)


def sync(root: Path, *, check: bool) -> list[str]:
    changed = []
    for relative in PAGES:
        target = root / relative
        projected = project_markdown(root, relative)
        if target.read_text(encoding='utf-8') != projected:
            changed.append(relative)
            if not check:
                target.write_text(projected, encoding='utf-8')
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'sync'])
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    changed = sync(args.root, check=args.command == 'check')
    if changed:
        print(('DRIFT: ' if args.command == 'check' else 'Updated: ') + ', '.join(changed))
    else:
        print('PASS: maintained fact blocks match catalog; historical reports untouched.')
    return int(bool(changed) and args.command == 'check')


if __name__ == '__main__':
    raise SystemExit(main())
