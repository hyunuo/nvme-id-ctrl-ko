"""Meaningful catalog contracts: identity, revision, provenance and coverage."""
import copy,json,unittest
from pathlib import Path
from catalog import compile_catalog
ROOT=Path(__file__).resolve().parent
class CatalogContracts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.source=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'));cls.compiled=compile_catalog(cls.source)
 def test_all_layout_and_psd_sources(self):
  self.assertEqual(152,len(self.compiled['coverage']))
  self.assertTrue(all(f['excerpt_ids'] for f in self.compiled['fields']))
  self.assertEqual(32,sum(bool(c['psd_definition_ids']) for c in self.compiled['coverage']))
  self.assertTrue(self.compiled['footnote_excerpt_ids'])
 def test_reordering_does_not_change_identity_or_revision(self):
  raw=copy.deepcopy(self.source);raw['conditions'].reverse();raw['fields'].reverse();raw['excerpts'].reverse()
  before={c['id']:c['revision'] for c in self.compiled['conditions']};after={c['id']:c['revision'] for c in compile_catalog(raw)['conditions']};self.assertEqual(before,after)
 def test_semantics_and_obligation_change_revision_not_id(self):
  raw=copy.deepcopy(self.source);cid=raw['conditions'][0]['id'];old=next(c for c in self.compiled['conditions'] if c['id']==cid)['revision'];raw['conditions'][0]['expected']+=' semantic change'
  new=next(c for c in compile_catalog(raw)['conditions'] if c['id']==cid);self.assertNotEqual(old,new['revision']);self.assertEqual(cid,new['id'])
  raw=copy.deepcopy(self.source);raw['conditions'][0]['level']='SHOULD';self.assertNotEqual(old,compile_catalog(raw)['conditions'][0]['revision'])
 def test_missing_source_is_not_silently_accepted(self):
  raw=copy.deepcopy(self.source);raw['conditions'][0]['excerpt_ids']=['absent'];self.assertRaises(AssertionError,compile_catalog,raw)
 def test_psd_template_has_independent_instances(self):
  rules=[r for f in self.compiled['fields'] if f['id'].startswith('PSD') for r in f['rules']]
  template=rules[0]['canonical_id'];instances={r['id'] for r in rules if r['canonical_id']==template};self.assertEqual(32,len(instances))
 def test_versions_and_unknown_registry_are_distinct(self):
  docs=self.compiled['documents'];self.assertEqual('2.0',docs['mi20']['version']);self.assertEqual('1.2d',docs['mi12d']['version']);self.assertIn(self.compiled['external_acquisition']['oui']['status'],['acquired','unavailable'])
 def test_shared_conditions_are_not_field_copies(self):
  self.assertLess(len(self.source['conditions']),sum(len(f['check_bindings']) for f in self.source['fields']))
if __name__=='__main__':unittest.main()
