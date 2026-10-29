"""Offline maintenance windows use synthetic dates, sources and publications."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fieldbook', ROOT / 'tools/fieldbook.py')
fb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fb)


class DateWindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'catalog').mkdir()
        (self.root / 'catalog/sources.json').write_text(json.dumps(
            [{'id': ident} for ident in ('S01', 'S02', 'S03', 'S04')]))
        self.cat = {'schema': 'fieldbook.entries/1', 'entries': []}
        self.add_entry('data.facts', 'facts.json', '{"source":"S01"}', when='2026-10-10')
        self.add_entry('guide.direct', 'direct.md', 'Fact [S01].',
                       when='2026-11-01', related=['guide.related'])
        self.add_entry('guide.dependent', 'dependent.md', 'Synthetic.', deps=['data.facts'])
        self.add_entry('report.past', 'past.md', 'Historical [S02].',
                       deps=['data.facts'], track='edition', when='2026-10-01')
        self.add_entry('guide.after-history', 'after.md', 'Synthetic.', deps=['report.past'])
        self.add_entry('guide.related', 'related.md', 'Synthetic.', when=None)
        self.add_entry('guide.inactive', 'inactive.md', '[S03]', status='withdrawn', when=None)
        self.launches = [
            self.launch('before', '2026-10-27'), self.launch('start', '2026-10-28'),
            self.launch('future', '2026-11-01'), self.launch('end', '2026-11-02'),
            self.launch('after', '2026-11-03'),
            self.launch('unknown', None, ['S02']),
            self.launch('unused', '2026-10-29', ['S04']),
        ]
        self.launches[5]['effective_events'][0]['candidate_dates'] = ['2026-10-14', '2026-10-15']
        self.launches[5]['conflicts'] = [{'topic': 'billing_start', 'claims': [
            {'date': '2026-10-14', 'source': 'S02'}, {'date': '2026-10-15', 'source': 'S02'}]}]
        self.save()

    def add_entry(self, ident, path, text, *, when='2026-12-31', deps=(), related=(),
                  track='maintained', status='current'):
        (self.root / path).write_text(text)
        self.cat['entries'].append({
            'id': ident, 'path': path, 'track': track, 'status': status,
            'depends_on': list(deps), 'related': list(related),
            'review': {'state': 'checked', 'checked_on': '2026-10-02',
                       'scope': 'synthetic scope only', 'next_review_on': when},
        })

    def launch(self, ident, when, sources=None):
        return {'id': ident, 'name': 'Synthetic ' + ident, 'sources': sources or ['S01'],
                'announced_on': '2026-10-01', 'verified_on': '2026-10-20',
                'verification_scope': 'synthetic dates only', 'next_check': 'Check conditions.',
                'effective_events': [{'kind': 'billing_start', 'date': when}], 'conflicts': []}

    def save(self):
        (self.root / 'catalog/launches.json').write_text(json.dumps(self.launches))
        (self.root / 'catalog/entries.json').write_text(json.dumps(self.cat))

    def query(self, start='2026-10-28', end='2026-11-02'):
        return fb.date_window(self.root, self.cat, date.fromisoformat(start), date.fromisoformat(end))

    def cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'tools/fieldbook.py'),
                               '--root', str(self.root), *args], capture_output=True, text=True)

    def test_inclusive_window_keeps_future_effective_date_and_separate_clocks(self):
        got = self.query()
        effective = {item['id']: item for item in got['items'] if item['type'] == 'effective'}
        self.assertEqual(set(effective), {'start', 'future', 'end', 'unused'})
        future = effective['future']
        self.assertEqual(future['date'], '2026-11-01')
        self.assertEqual(future['announced_on'], '2026-10-01')
        self.assertEqual(future['verified_on'], '2026-10-20')
        self.assertEqual(future['verification_scope'], 'synthetic dates only')
        self.assertEqual([item['id'] for item in got['items'] if item['type'] == 'review'], ['guide.direct'])

    def test_overdue_reviews_include_origin_and_dependency_candidates(self):
        got = self.query()
        self.assertEqual([item['id'] for item in got['overdue_reviews']], ['data.facts'])
        item = got['overdue_reviews'][0]
        self.assertEqual(item['review']['checked_on'], '2026-10-02')
        self.assertEqual(item['impact']['current_review_candidates'], ['data.facts', 'guide.dependent'])
        self.assertEqual(item['impact']['edition_errata_candidates'], ['report.past'])
        self.assertNotIn('guide.after-history', item['impact']['current_review_candidates'])

    def test_single_day_reviews_are_not_overdue_until_the_next_day(self):
        got = self.query('2026-11-01', '2026-11-01')
        self.assertEqual({item['type'] for item in got['items']}, {'effective', 'review'})
        self.assertEqual([item['id'] for item in got['overdue_reviews']], ['data.facts'])
        later = self.query('2026-11-02', '2026-11-02')
        self.assertEqual([item['id'] for item in later['overdue_reviews']], ['data.facts', 'guide.direct'])

    def test_unknown_dates_retain_conflicts_even_outside_candidate_date_window(self):
        got = self.query('2027-01-01', '2027-01-02')
        unknown = {item['id']: item for item in got['unknown_dates']}
        self.assertEqual(set(unknown), {'unknown', 'guide.related'})
        item = unknown['unknown']
        self.assertIsNone(item['date'])
        self.assertEqual(item['event']['candidate_dates'], ['2026-10-14', '2026-10-15'])
        self.assertEqual(item['conflicts'], self.launches[5]['conflicts'])
        self.assertEqual(item['impact']['edition_errata_candidates'], ['report.past'])
        self.assertEqual(item['impact']['current_review_candidates'], [])
        self.assertNotIn('report.past', [row['id'] for row in got['overdue_reviews']])

    def test_missing_dates_are_unknown_not_inferred_from_announcement_or_verification(self):
        del self.launches[5]['effective_events'][0]['date']
        del self.cat['entries'][5]['review']['next_review_on']
        empty = self.launch('no-event', '2026-10-30')
        empty['effective_events'] = []
        self.launches.append(empty)
        self.save()
        got = self.query()
        self.assertEqual({row['id'] for row in got['unknown_dates']}, {'unknown', 'guide.related'})
        self.assertNotIn('no-event', [row['id'] for row in got['items']])

    def test_effective_impact_includes_citations_and_stops_at_history(self):
        item = next(row for row in self.query()['items'] if row['id'] == 'future')
        impact = item['impact']
        self.assertEqual(impact['current_review_candidates'], ['data.facts', 'guide.dependent', 'guide.direct'])
        self.assertEqual(impact['edition_errata_candidates'], ['report.past'])
        self.assertEqual(impact['related_only'], ['guide.related'])
        self.assertEqual(impact['dependency_reasons']['guide.dependent'], ['data.facts'])
        self.assertNotIn('guide.after-history', impact['current_review_candidates'])

    def test_inactive_is_an_impact_candidate_but_not_a_scheduled_review(self):
        self.launches.append(self.launch('inactive-source', '2026-10-30', ['S03']))
        self.save()
        got = self.query()
        item = next(row for row in got['items'] if row['id'] == 'inactive-source')
        self.assertEqual(item['impact']['inactive_candidates'], ['guide.inactive'])
        for group in ('items', 'unknown_dates', 'overdue_reviews'):
            self.assertNotIn('guide.inactive', [row['id'] for row in got[group]])

    def test_no_registered_impact_is_visible_and_not_a_claim_of_no_real_impact(self):
        got = self.query()
        item = next(row for row in got['items'] if row['id'] == 'unused')
        self.assertEqual(item['impact']['direct_citations'], [])
        self.assertEqual(item['impact']['current_review_candidates'], [])
        self.assertIn('未找到登记引用或依赖候选；不等于实际无影响', fb.format_date_window(got))

    def test_multiple_events_do_not_collapse_and_order_is_deterministic(self):
        self.launches[2]['effective_events'].append({'kind': 'removal', 'date': '2026-11-01'})
        self.save()
        before = self.query()
        self.assertEqual([row['event']['kind'] for row in before['items'] if row['id'] == 'future'],
                         ['billing_start', 'removal'])
        self.cat['entries'].reverse()
        self.launches.reverse()
        self.save()
        self.assertEqual(self.query(), before)

    def test_empty_window_still_reports_overdue_and_unknown_without_inventing_events(self):
        got = self.query('2027-02-01', '2027-02-02')
        self.assertEqual(got['items'], [])
        self.assertTrue(got['overdue_reviews'])
        self.assertTrue(got['unknown_dates'])

    def test_invalid_window_dates_and_unknown_sources_fail_clearly(self):
        with self.assertRaisesRegex(ValueError, 'on or before'):
            self.query('2026-11-02', '2026-10-28')
        self.launches[0]['effective_events'][0]['date'] = '2026-02-30'
        self.save()
        with self.assertRaises(ValueError):
            self.query()
        self.launches[0]['effective_events'][0]['date'] = '2026-10-30'
        self.launches[0]['sources'] = ['S99']
        self.save()
        with self.assertRaisesRegex(ValueError, 'unknown source ID: S99'):
            self.query()

    def test_queries_preserve_catalog_sources_and_frozen_publications(self):
        (self.root / 'dist').mkdir()
        (self.root / 'dist/history.html').write_text('Fixed synthetic publication.')
        frozen = self.root / '.build/editions/snapshot'
        frozen.mkdir(parents=True)
        (frozen / 'manifest.json').write_text('{"synthetic":"frozen"}')
        files = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        before = copy.deepcopy(self.cat)
        fb.format_date_window(self.query())
        result = self.cli('window', '--from', '2026-10-28', '--to', '2026-11-02')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.cat, before)
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}, files)

    def test_cli_json_text_and_old_due_contract(self):
        args = ('window', '--from', '2026-10-28', '--to', '2026-11-02')
        result = self.cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), self.query())
        text = self.cli(*args, '--format', 'text')
        self.assertEqual(text.returncode, 0, text.stderr)
        for expected in ('起点前逾期复核', '候选日期（未确认）', '历史勘误（传播终点）',
                         '停止传播', 'guide.direct — direct.md；直接引用 S01', '核验：2026-10-20'):
            self.assertIn(expected, text.stdout)
        old = self.cli('due', '--as-of', '2026-11-02')
        self.assertEqual(old.returncode, 0, old.stderr)
        self.assertEqual(json.loads(old.stdout), fb.due(self.cat, date(2026, 11, 2)))

    def test_cli_rejects_invalid_reversed_or_missing_bounds(self):
        for args in (('--from', '2026-11-02', '--to', '2026-10-28'),
                     ('--from', '2026-02-30', '--to', '2026-11-02'),
                     ('--from', '2026-10-28')):
            with self.subTest(args=args):
                result = self.cli('window', *args)
                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr)
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
