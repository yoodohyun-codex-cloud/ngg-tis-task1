"""Pure metadata fixtures only; no source/data reads, native arrays or NumPy."""
import copy,unittest
from unittest.mock import patch
import light_inputs as subject

def admission():
 return dict(schema='task1-native-light-post-root-admission-v1',status='admitted_finite_native_light_post',root_review_positive=True,sole_NUM_owner=True,new_driven_RHS=0,new_eigen_solves=0,new_angular_metric_evaluations=0,native_Q_loaded=False,fields_reconstructed=False,candidate_adopted=False,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,decision_basis='Synthetic contract, not actual admission',source_sha256={'canonical/source':'a'*64},ellipse_review=dict(run=str(subject.ELLIPSE),root_reviewed=True,decision_basis='Synthetic outcome fixture only',outcome='failed_preserved',publication_path=str(subject.ELLIPSE/'result-publication/result-publication.json'),publication_SHA256='b'*64,publication_commit='c'*40,primary_record={},missing_fields=['No complete ellipse scalar/probe fields']))
def complete():return dict(status='single_centroid_area_matched_ellipse_screen_computed_unadopted',completed_conditions=3,actual_new_driven_RHS=2,actual_new_angular_metric_evaluations=1,actual_immutable_control_aliases=2,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0,Q_resident_during_metrics=False,candidate_adopted=False)
class ProvenanceContracts(unittest.TestCase):
 def test_invalid_admission_stops_before_metadata_or_context(self):
  with patch.object(subject,'metadata',side_effect=AssertionError('No real file reads')),patch.object(subject,'_context',side_effect=AssertionError('No actual dataset calls')):
   with self.assertRaises(ValueError):subject.make_spec({})
 def test_zero_work_and_actual_outcome_review_mandatory(self):
  good=admission();self.assertIs(subject.validate_admission(good),good)
  for key,value in(('new_driven_RHS',1),('new_eigen_solves',True),('new_angular_metric_evaluations',1),('native_Q_loaded',True)):
   a=admission();a[key]=value
   with self.assertRaises(ValueError):subject.validate_admission(a)
  a=admission();a['ellipse_review']['run']=str(subject.FINE)
  with self.assertRaises(ValueError):subject.validate_admission(a)
  for path in('/dev/shm/task1-fixture/result-publication/result-publication.json','/dev/shm/task1-P23-fineXY-synthetic-r2-20261025-run/result-publication/result-publication.json'):
   a=admission();a['ellipse_review']['publication_path']=path
   with self.assertRaises(ValueError):subject.validate_admission(a)
 def test_complete_ellipse_requires_exact_actual_accounting(self):
  self.assertTrue(subject.validate_ellipse_outcome('computed_complete',complete(),[])['ellipse_fields_available'])
  for key,value in(('actual_new_driven_RHS',3),('actual_immutable_control_aliases',True),('Q_resident_during_metrics',True)):
   c=complete();c[key]=value
   with self.assertRaises(ValueError):subject.validate_ellipse_outcome('computed_complete',c,[])
  with self.assertRaises(ValueError):subject.validate_ellipse_outcome('computed_complete',complete(),['invented missing field'])
 def test_failed_or_missing_ellipse_never_invents_native_fields(self):
  result=subject.validate_ellipse_outcome('failed_preserved',dict(status='centroid_ellipse_failed_or_partial_preserved'),['scalar/probe fields incomplete'])
  self.assertFalse(result['ellipse_fields_available']);self.assertFalse(result['computed_missing_fields_invented'])
  with self.assertRaises(ValueError):subject.validate_ellipse_outcome('failed_preserved',dict(status='failed_preserved'),[])
  with self.assertRaises(ValueError):subject.validate_ellipse_outcome('failed_preserved',dict(status='source_prepared'),['not actual failure'])
  with self.assertRaises(ValueError):subject.validate_ellipse_outcome('failed_preserved',dict(status='synthetic_MMS_failed'),['not actual field failure'])
  with self.assertRaises(ValueError):subject.validate_ellipse_outcome('failed_preserved',dict(status='failed_preserved',candidate_adopted=True),['cannot drop adoption conflict'])
 def test_direct_readback_identity_cannot_be_skipped_or_changed(self):
  target='data-native/fixture/scalar.npz';row=dict(readback_passed=True,SHA256='d'*64,bytes=123);pub=dict(status='published_readback_verified',commit='e'*40,files={target:row})
  d=subject.direct(pub,'/synthetic-post-fixture/scalar.npz',target,'d'*64);self.assertEqual(d['SHA256'],'d'*64);self.assertFalse(d['arrays_decoded_here'])
  for key,value in(('readback_passed',False),('SHA256','f'*64)):
   bad=copy.deepcopy(pub);bad['files'][target][key]=value
   with self.assertRaises(ValueError):subject.direct(bad,'/synthetic-post-fixture/scalar.npz',target,'d'*64)
 def test_four_existing_normalizations_cannot_be_inferred_or_missing(self):
  n=dict(status='complete',comparisons={m:dict(amplitude_scale=.5)for m in subject.MODES});self.assertIs(subject.validate_normalizations(n),n)
  bad=copy.deepcopy(n);bad['comparisons'].pop(subject.MODES[-1])
  with self.assertRaises(ValueError):subject.validate_normalizations(bad)
  bad=copy.deepcopy(n);bad['comparisons'][subject.MODES[0]]['amplitude_scale']=float('nan')
  with self.assertRaises(ValueError):subject.validate_normalizations(bad)
 def test_source_identity_uses_canonical_namespace_not_frozen_deployment(self):
  expected=str(subject.SOURCE/'light_inputs.py')
  with patch.object(subject,'__file__','/synthetic/frozen/light_inputs.py'):
   self.assertEqual(subject.canonical_source_key('light_inputs.py'),expected)
  with self.assertRaises(ValueError):subject.canonical_source_key('../light_inputs.py')
if __name__=='__main__':unittest.main()
