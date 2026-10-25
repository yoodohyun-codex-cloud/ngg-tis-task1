"""Pure eight-case append/range/identity contracts; no native or render execution."""
import copy,hashlib,json,unittest
import append_build as subject
from test_lite_render import payload as display_fixture

def fixtures():
 p=display_fixture();p['schema']='task1-native-GUI-lite-display-v1';new=p['sections'][0]['cases'].pop()
 for c,ident in zip(p['sections'][0]['cases'],subject.OLD_NATIVE_IDS):c['id']=ident
 for c,ident in zip(p['sections'][1]['cases'],subject.LEGACY_IDS):c['id']=ident
 new['id']=subject.NEW_ID;new['grid_version']='XY102-Z97'
 all_cases=p['sections'][0]['cases']+p['sections'][1]['cases']+[new]
 for i,c in enumerate(all_cases):
  c['normalizations']={m:dict(status='complete',amplitude_scale=.5,absolute_ROI_fields_V_m=dict(total=dict(maxTIS=dict(mean=.25,p10=.125,p95=.75,max=float(i+1)),RMS=dict(max=2.*(i+1)))),electrical=dict(contact_normal_J_RMS_max_A_m2=3.*(i+1)))for m in subject.MODES}
  c['amplitude_scales']={m:.5 for m in subject.MODES};c['bar_values']={'target_AM_mean':{m:.25*(i+1)for m in subject.MODES}}
  c['stats']=dict(marker_original_float=0.12345678901234568,minus_zero=-0.,source_ordinal=i)
  if 'probe_summary'in c:
   for row in c['probe_summary']['probes']:row['unloaded']['envelope_max_exact_V']=.1*(i+1)
 p['normalization_modes']=[dict(id=m,label=m)for m in subject.MODES]
 p['legacy_provisional_top5']=['preserved-original-order',dict(id='no-new-ranking')]
 p['provenance']=dict(original_float64=1.2345678901234567,field_version='synthetic-only');p['holds']=dict(original_contact_uncertainty=True)
 return p,new

class AppendOnlyContracts(unittest.TestCase):
 def test_partial_payload_base_keeps_old_HTML_missing_and_rejects_wrong_outcome(self):
  ctx=dict(base_outcome='partial_payload_complete_functional_limit',previous_index=None,previous_index_missing=dict(path='/synthetic/previous/index.html',reason='never_created_after_functional_limit'),original_absences=['/synthetic/previous/index.html','/synthetic/previous/summary.json','/synthetic/previous/gui-build-receipt.json'])
  self.assertEqual(subject.require_partial_base(ctx)['reason'],'never_created_after_functional_limit');subject.verify_original_absences(ctx,exists=lambda p:False)
  with self.assertRaises(ValueError):subject.verify_original_absences(ctx,exists=lambda p:p.endswith('index.html'))
  for key,value in(('base_outcome','computed_success'),('previous_index',dict(path='invented-index.html')),('original_absences',[])):
   changed=copy.deepcopy(ctx);changed[key]=value
   with self.assertRaises(ValueError):subject.require_partial_base(changed)
 def test_complete_old_seven_cases_are_identical_objects_and_bytes_after_append(self):
  old,new=fixtures();before=copy.deepcopy(old);case_ids=subject.fingerprints(subject.previous_cases(old))
  p,proof=subject.assemble(old,new,provenance=dict(source='synthetic'),holds=dict(unadopted=True))
  self.assertEqual(old,before);self.assertEqual(proof['original_cases'],case_ids)
  self.assertEqual(subject.fingerprints(p['sections'][0]['cases'][:3]+p['sections'][1]['cases']),case_ids)
  for a,b in zip(subject.previous_cases(old),p['sections'][0]['cases'][:3]+p['sections'][1]['cases']):self.assertIs(a,b)
  self.assertEqual(p['legacy_provisional_top5'],before['legacy_provisional_top5']);self.assertFalse(proof['legacy_rank_recomputed'])
  self.assertEqual((proof['completed_cases'],proof['old_case_count'],proof['new_case_count']),(8,7,1))
 def test_shared_defaults_use_all_original_statistic_modes_not_float16_pixels(self):
  old,new=fixtures();last=old['sections'][1]['cases'][-1];mode=subject.MODES[-1]
  last['normalizations'][mode]['absolute_ROI_fields_V_m']['total']['maxTIS']['max']=900.
  last['normalizations'][mode]['absolute_ROI_fields_V_m']['total']['RMS']['max']=1800.
  new['normalizations'][mode]['electrical']['contact_normal_J_RMS_max_A_m2']=2700.
  new['bar_values']['target_AM_mean'][mode]=3600.
  new['probe_summary']['probes'][0]['unloaded']['envelope_max_exact_V']=50.
  p,proof=subject.assemble(old,new,provenance={},holds={});r=p['shared_initial_ranges']
  self.assertEqual((r['AM_V_m'][1],r['RMS_V_m'][1],r['J_A_m2'][1],r['bar_value'][1]),(900.,1800.,2700.,3600.))
  self.assertEqual(r['wave_voltage_V'],[-25.,25.]);self.assertFalse(proof['shared_range_proof']['ranges_change_on_selection'])
 def test_larger_original_ranges_and_physical_axes_are_never_shrunk(self):
  old,new=fixtures();old['shared_initial_ranges']['AM_V_m']=[0.,9999.]
  p,_=subject.assemble(old,new,provenance={},holds={})
  self.assertEqual(p['shared_initial_ranges']['AM_V_m'],[0.,9999.])
  for key in('x_mm','y_mm','depth_mm','wave_time_ms'):self.assertEqual(p['shared_initial_ranges'][key],old['shared_initial_ranges'][key])
 def test_missing_reordered_old_case_or_wrong_new_identity_cannot_be_repaired(self):
  for action in('missing','reordered','new-id'):
   old,new=fixtures()
   if action=='missing':old['sections'][1]['cases'].pop()
   elif action=='reordered':old['sections'][0]['cases'].reverse()
   else:new['id']=subject.OLD_NATIVE_IDS[2]
   with self.assertRaises(ValueError):subject.assemble(old,new,provenance={},holds={})
 def test_missing_original_normalization_or_nonfinite_statistic_is_not_filled(self):
  for action in('mode','nonfinite','double-scale'):
   old,new=fixtures()
   if action=='mode':new['normalizations'].pop(subject.MODES[-1])
   elif action=='nonfinite':new['normalizations'][subject.MODES[0]]['electrical']['contact_normal_J_RMS_max_A_m2']=float('nan')
   else:new['amplitude_scales'][subject.MODES[0]]=2.
   with self.assertRaises(ValueError):subject.assemble(old,new,provenance={},holds={})
 def test_actual_combined_probe_flags_cannot_be_assumed_or_substituted(self):
  old,new=fixtures();new['probe_summary']['strict_same_layer_bracket_available_probe_count']=19
  with self.assertRaises(ValueError):subject.assemble(old,new,provenance={},holds={})
 def test_native_helper_is_called_once_for_new_case_and_rejects_old_before_call(self):
  calls=[]
  def builder(*args):calls.append(args);return dict(id='synthetic-result'),dict(native='synthetic-proof')
  case=dict(candidate_id=subject.NEW_ID,section='new_native');result=subject.extract_one_case(None,case,None,None,None,builder)
  self.assertEqual(len(calls),1);self.assertEqual(result[0]['id'],'synthetic-result')
  for cid in subject.OLD_NATIVE_IDS+subject.LEGACY_IDS:
   with self.assertRaises(ValueError):subject.extract_one_case(None,dict(candidate_id=cid,section='new_native'),None,None,None,builder)
  self.assertEqual(len(calls),1)
 def test_canonical_identity_covers_exact_original_float_and_unicode_bytes(self):
  value=dict(z=-0.,a=[0.12345678901234568,'끝😀',1e-9]);raw=subject._json_bytes(value);identity=subject.canonical_identity(value)
  self.assertEqual(identity['SHA256'],hashlib.sha256(raw).hexdigest());self.assertEqual(identity['bytes'],len(raw))
  altered=copy.deepcopy(value);altered['a'][0]=.1234567890123456
  self.assertNotEqual(subject.canonical_identity(altered)['SHA256'],identity['SHA256'])
 def test_application_controls_CSS_and_fixed_manual_range_logic_are_unchanged(self):
  import lite_render
  self.assertEqual(hashlib.sha256(lite_render._JS.encode()).hexdigest(),'4c4a16cdeb3b46658073238bed2d5d847e274e4485fc79e6bde28704a775f32c')
  self.assertEqual(hashlib.sha256(lite_render._CSS.encode()).hexdigest(),'edaf19e15b0674ed79f6a90526c8e21503d788af254177d634dbd19d20233c0f')
  self.assertEqual((lite_render.MAX_JSON_BYTES,lite_render.MAX_HTML_BYTES),(8000000,8200000))

if __name__=='__main__':unittest.main()
