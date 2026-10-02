from __future__ import annotations
import ast, copy, importlib.util, json, re, shutil, tempfile, unittest
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fieldbook',ROOT/'tools/fieldbook.py')
fb=importlib.util.module_from_spec(spec);spec.loader.exec_module(fb)

def entry(i,path,deps=(),related=(),track='maintained',status='current'):
 return {'id':i,'path':path,'kind':'guide','depends_on':list(deps),'related':list(related),'track':track,'status':status,'review':{'state':'checked','checked_on':'2026-10-02','scope':'test fixture only','next_review_on':'2026-10-16'},'evidence':[]}
class FieldbookTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  for n in ['a.md','b.md','c.md','d.md']:(self.root/n).write_text('synthetic')
  self.cat={'schema':'fieldbook.entries/1','entries':[entry('data.a','a.md'),entry('guide.b','b.md',['data.a'],['guide.d']),entry('report.c','c.md',['data.a'],track='edition'),entry('guide.d','d.md')]}
 def tearDown(self):self.tmp.cleanup()
 def test_valid_entries(self):self.assertEqual(fb.validate_entries(self.root,self.cat),[])
 def test_duplicate_id(self):
  self.cat['entries'][1]['id']='data.a';self.assertIn('duplicate content ID',fb.validate_entries(self.root,self.cat))
 def test_duplicate_owner(self):
  self.cat['entries'][1]['path']='a.md';self.assertIn('duplicate content owner path',fb.validate_entries(self.root,self.cat))
 def test_unknown_dependency(self):
  self.cat['entries'][1]['depends_on']=['missing.id'];self.assertTrue(any('unresolved' in x for x in fb.validate_entries(self.root,self.cat)))
 def test_dependency_cycle(self):
  self.cat['entries'][0]['depends_on']=['guide.b'];self.assertTrue(any('cycle' in x for x in fb.validate_entries(self.root,self.cat)))
 def test_related_cycle_is_not_dependency(self):
  self.cat['entries'][0]['related']=['guide.b'];self.cat['entries'][1]['related']=['data.a'];self.assertEqual(fb.validate_entries(self.root,self.cat),[])
 def test_no_escaping_paths(self):
  self.cat['entries'][0]['path']='../secret.txt';self.assertTrue(any('relative path' in x for x in fb.validate_entries(self.root,self.cat)))
 def test_checked_date_requires_scope(self):
  del self.cat['entries'][0]['review']['scope'];self.assertTrue(any('needs scope' in x for x in fb.validate_entries(self.root,self.cat)))
 def test_invalid_date(self):
  self.cat['entries'][0]['review']['checked_on']='2026-02-30';self.assertTrue(any('bad date' in x for x in fb.validate_entries(self.root,self.cat)))
 def test_cloud_evidence_requires_scope_and_run(self):
  self.cat['entries'][0]['evidence']=[{'kind':'cloud-executed','ref':'a.md'}];self.assertTrue(any('scoped receipt' in x for x in fb.validate_entries(self.root,self.cat)))
 def test_impact_separates_current_edition_related(self):
  got=fb.impact(self.cat,['data.a']);self.assertEqual(got['current_review_candidates'],['guide.b']);self.assertEqual(got['edition_errata_candidates'],['report.c']);self.assertEqual(got['related_only'],['guide.d'])
 def test_edition_is_terminal(self):
  self.cat['entries'][3]['depends_on']=['report.c'];self.assertNotIn('guide.d',fb.impact(self.cat,['data.a'])['current_review_candidates'])
 def test_unknown_changed_id_rejected(self):
  with self.assertRaises(ValueError):fb.impact(self.cat,['does.not-exist'])
 def test_inactive_not_current_candidate(self):
  self.cat['entries'][1]['status']='withdrawn';got=fb.impact(self.cat,['data.a']);self.assertEqual(got['current_review_candidates'],[]);self.assertIn('guide.b',got['inactive_candidates'])
 def test_due_excludes_snapshot_and_withdrawn(self):
  self.cat['entries'][1]['status']='withdrawn';got=fb.due(self.cat,date(2026,10,20));self.assertEqual([x['id'] for x in got],['data.a','guide.d'])
 def test_noop_queries_preserve_input(self):
  original=copy.deepcopy(self.cat);fb.impact(self.cat,['data.a']);fb.due(self.cat,date(2026,10,20));self.assertEqual(self.cat,original)
 def test_actual_index_related_does_not_cascade(self):
  got=fb.impact(fb.load(ROOT),['data.decision-routes']);self.assertNotIn('usecase.bounded-decision',got['current_review_candidates']);self.assertIn('usecase.bounded-decision',got['related_only'])
 def test_actual_pairing_valid(self):self.assertEqual(fb.validate_diagrams(ROOT),[])
 def test_source_drift_rejected(self):
  for sub in ['assets/diagrams','diagrams']:shutil.copytree(ROOT/sub,self.root/sub)
  (self.root/'diagrams/src/architecture.mmd').write_text('flowchart TB\n A-->B\n')
  self.assertTrue(any('source drift' in x for x in fb.validate_diagrams(self.root)))
 def test_svg_drift_rejected(self):
  for sub in ['assets/diagrams','diagrams']:shutil.copytree(ROOT/sub,self.root/sub)
  p=self.root/'assets/diagrams/architecture.svg';p.write_text(p.read_text()+'<!-- altered -->')
  self.assertTrue(any('output drift' in x for x in fb.validate_diagrams(self.root)))
 def test_examples_offline(self):self.assertEqual(fb.validate_example_meta(ROOT),[])
 def test_render_source_appendix_is_read_only(self):
  source=(ROOT/'tools/render.py').read_text();tree=ast.parse(source);fun=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='update_sources')
  mod=ast.Module(body=[fun],type_ignores=[]);env={'Path':Path,'re':re}
  exec(compile(mod,'extracted_update_sources','exec'),env)
  p=self.root/'draft.md';p.write_text('# Synthetic\n[S99]\n<!-- SOURCES -->\nold appendix\n');before=p.read_bytes()
  out=env['update_sources'](p,{'S99':{'title':'Synthetic source','url':'https://example.com/'}})
  self.assertEqual(p.read_bytes(),before);self.assertIn('Synthetic source',out)
if __name__=='__main__':unittest.main()
